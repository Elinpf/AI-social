# T298 · round92 复核检查清单（art-director，**只读准备**）

> 用途：life 落 T298 后，**独立复核** round93 分岔究竟是 **① 缓存裁剪仍不对** 还是 **② 睡眠/人格前向态(T244)使 `mems` 不同**。
> 原则：**实现者不自证**；本清单只读、不碰 `code/`。
> 正在进行：life 产"原始数据"（round92 两路 `self.memory.nodes` + 喂 `plan_forgetting` 的 `mems`）。

---

## 0. 已知线索（读码，只读）

- **`8d4c8b9` 只改了 `AssociativeMemory.sync_from_refs`**：裁剪"不在本次 refs 中的节点"（+`_drop_node`）。
- ⚠️ **`sync_from_refs` 只在 `restore()`（续跑）被调用** ⇒ **运行期 live 路径（一次性跑）在 `MEMORY_FORGET(drop)` 时仍不摘除节点** ⇒ 一次性缓存**仍是"超集"**。
- ⇒ **先验倾向 = ①**（裁剪只覆盖了 restore 侧，未覆盖 live 侧）。**但以 round92 dump 为准，不预设。**

---

## 1. 需要的输入（life 交）

1. round92 **两路 `self.memory.nodes`**：`mem_id` 集 + 每节点字段（`kind/subject/importance/last_access/access_count/reflected`）。
2. round92 **两路喂给 `plan_forgetting` 的 `mems`**（即 `_maybe_sleep_window` 的输入 list）。
3. （可选）两路的 `_slept_days / _persona_state / _persona_p0 / _drift_streak`。
4. （可选）两路的新日志（用于我侧独立折叠出**权威集**）。

---

## 2. ★ 判别方法（先做"集合"，再做"字段"）

### 2.1 先用日志折叠出**权威集@round92**（我侧独立算，不依赖 life dump）
按 `engine/replay.py` 折叠 ≤round92：`WRITE` 加、`FORGET drop` 删、`CONSOLIDATE/REFLECT` 加产物 → 得 `AUTH92`。

### 2.2 三集合对齐
| 集合 | 期望（若 ①） | 期望（若 ②） |
|---|---|---|
| `resumed.nodes` vs `AUTH92` | **相等** | 可能**不等**（缺/多 live 记忆，或字段不同） |
| `oneshot.nodes` vs `AUTH92` | **超集**，且 `oneshot \ AUTH92` **= "≤92 已 drop" 集合** | 差集**不是**纯"已 drop" |
| `mems` 与各自 `nodes` | 一致 | 可能不一致 |

**判读**：
- **`oneshot ⊃ AUTH92` 且差集恰等于"已 drop"、`resumed == AUTH92`** ⇒ **①**（裁剪只差 live 侧）。
- **`resumed` 相对 `AUTH92` 有缺/字段不同** ⇒ **②**（或 restore 仍有缺口）。

### 2.3 交集字段逐条（排除字段级分岔）
对 `resumed.nodes ∩ oneshot.nodes` 比较：`last_access / access_count / subject / importance / kind / reflected`。
- **全等** ⇒ 非字段/recency 分岔 → 排除候选(2)/取回史。
- **有不等** ⇒ 指向**前向态/取回史**（②/相关）。

### 2.4 事件级"前向态分岔"旁证（排除 ②）
比较两路日志 **≤round92** 的：`SLEEP_STARTED/COMPLETED`、`PERSONA_DRIFT`、`MEMORY_CONSOLIDATE`、`MEMORY_REFLECT`、`MEMORY_RETRIEVE` 的**条数与产出的 `produced_mem_id` 集**。
- **全一致** ⇒ 睡眠/反思/人格路径未分岔 ⇒ **排除 ②**。
- **有差异** ⇒ ② 可能要查 `_slept_days/_persona_state/_drift_streak`。

### 2.5 关键"成员差"指纹（复现旧结论形状）
r93 两路 `MEMORY_FORGET`：`only-in-?`、交集 `level/reason/retention` 不一致数、差的 mem 是否**恰为"≤92 已 drop"**。
- 若"差的仍 = 已 drop 集" ⇒ **①**（只是这次 live 侧仍未修）。

---

## 3. 判读表（结论 → 下一步）

| 观测 | 结论 | 含义 |
|---|---|---|
| `oneshot ⊃ AUTH92`（差=已 drop）、`resumed==AUTH92`、交集字段全等 | **①** | `8d4c8b9` 只修了 restore 侧；**live 侧（`FORGET(drop)` 时）仍未摘除缓存** → 需在**运行期遗忘生效处**同步 `_drop_node`，或 `plan_forgetting` 输入改用**权威 `memory_refs`** |
| `resumed` 与 `AUTH92` 有缺/字段不等 | **②**/restore 缺口 | 前向态或 restore 字段补全不到位 |
| 两路 `<92` 的 SLEEP/PERSONA/REFLECT 事件不同 | **②** | `_slept_days/_persona_state/_drift_streak` 未重建 |

---

## 4. 边界

- **只读复核**：不改 `code/`；不碰 `config/*.json`；不碰 `t271-t292`；停 unit 只用显式名。
- **验收不可降级**：目标配置 `seed=9/n2/150, kill@89` **逐字节一致** + `verify_native_resume.sh` PASS。

---
*（T298 复核检查清单 — art-director；只读准备，待 life dump 落盘后执行）*
