# T296 · 只读取证：native 续跑 `MEMORY_FORGET` 分歧（`seed=9/n=2/150` kill@89）

> 作者：art-director（claimant，**只做只读半**）｜ 2026-10-12 ｜ **未改任何 `code/`**
> 上游清单：`v2/refs/T296-native-resume-divergence-attribution.md`（sim-system-architect，**rev2 `14cf206`**）
> 复现：`tools/t271/verify_native_resume.sh`（真 orchestration / mock provider）——**已稳定复现不一致**：
> `resumed=b3ae4c56…2a69cc` vs `oneshot=eecade7e…253b6c`（脚本门禁 PASS；逐字节 **PROBE 不一致** 如实打印）。

---

## 0. 结论（一句话）

**归属 = life 侧（不是 engine）：进程内记忆缓存 `self.memory.nodes` 是「只增不减」——`MEMORY_FORGET(drop)` 后不摘除；而 `restore()` 从**权威** `a["memories"]` 重建，于是续跑路径**正确地把"已 drop 的记忆"排除在外**，一次性路径**仍把它们喂给 `plan_forgetting`**。**

**分歧 = 纯"输入集合成员差"，且差集精确等于「r90 前已 drop 的 74 条」；两路对"交集内每条记忆"的判定 100% 一致。** 故这**不是引擎折叠差异**，也**不是** `is_protected` 分支（本分歧在 `merge/drop` 非保护分支）。

---

## 1. 复现事实

| 项 | 值 |
|---|---|
| 配置 | `seed=9 / agents=2 / rounds=150`（nightly kill@89） |
| 一次性（ref.jsonl） | MEMORY_FORGET(P001) = **3019** 条 |
| 续跑（n1b.jsonl） | MEMORY_FORGET(P001) = **2649** 条 |
| **其它 MEMORY_*** | **完全相同**：WRITE 1267 / RETRIEVE 300 / REFLECT 20 / CONSOLIDATE 47 |
| 前缀 | rounds 0–89 **逐字节一致**（探针）；首个分歧 **round 93** |

> ⇒ **只有"遗忘决策"分岔**，读/写/反思/固化的路径完全一致。

## 2. round 90：**权威集两路完全相同**（排除引擎折叠差异）

按 `engine/replay.py` 折叠（`WRITE` 追加 `a["memories"]`+`memory_index`；`FORGET drop` 从两处摘除；`merge` 只标 `forgotten_level`；`RETRIEVE` 更新**同一 dict** 的 `last_access/access_count`；`CONSOLIDATE/REFLECT` 追加产物）：

| @round90（P001） | ref.jsonl | n1b.jsonl |
|---|---|---|
| **权威集大小**（`a["memories"]`） | **343** | **343** |
| `M-000003 / M-000004` | auth=**None**，**r45 已 drop** | auth=**None**，**r45 已 drop** |
| `M-000005 / 000006 / 000008 / 000010` | 均在 auth（同 subject/importance/last） | 同左 |
| `by_subject` 计数 diff | — | **无差异** |

> ⇒ **round90 的日志可重建权威状态两路一致** ⇒ 差异**不在 engine**。

## 3. round 93：分歧**只是"成员差"，不是"判定差"**

| @round93（P001） | ref.jsonl | n1b.jsonl |
|---|---|---|
| FORGET 条数 | **349** | **275** |
| `only-in-n1b`（续跑独有） | — | **[]（空）** |
| `only-in-ref`（一次性独有） | **74 条** | — |
| **交集内 `level/reason/retention` 不一致** | **0 处** | **0 处** |
| 这 74 条 = "r<90 已被 drop"的集合 | **74/74 命中**（全在） | **0**（全无） |

> **★ 决定性**：续跑集合是**一次性集合的子集**；两者对**共同记忆**判定**完全一致**；**唯一差 = 74 条"已 drop 但仍在一次性缓存里"的记忆**。

## 4. 指纹：一次性**重复遗忘已删记忆**

`M-000003`（r45 已 drop）的 FORGET 轨迹：

- **一次性**：`[r45,57,69,81,93,…,141]` **每 12 回合重复 drop**（共 9 次 drop + 1 demote）→ **它一直在缓存里，被反复当候选**；
- **续跑**：`[r45,57,69,81]` 后**停止**（r90 重建后不含它，不再成候选）。

> 与「只增不减缓存」完全吻合：一次性缓存永不含"删除"，续跑 `restore()` 重建后不含。

## 5. 归属判定（对 rev2 候选清单）

- **候选 (2)（`memory_index` 与 `a["memories"]` 非同对象）→ 证伪**（life 已核 + 本取证交集判定一致佐证）✓；
- **候选 (2′)（T244 前向态 `_slept_days/_persona_state/…` 未进 `restore()`）→ 本取证不支持为本因**：若前向态分岔，`SLEEP` 路径/`CONSOLIDATE`/`REFLECT` 计数与"交集判定"应变 —— 实测**全一致**、**交集 0 处不一致**，**分歧仅在同一批"已 drop"记忆的成员差**；
- **实际根因（本取证坐实）= 候选 (3) 变体：`self.memory.nodes`「只增不减」 vs 权威集** → `restore()`（正确地）按权威重建，暴露该不一致。

**判定：`restore()` 不是"缺口"（它按权威重建是对的）；真正的缺口是 life 的"运行期缓存与权威集不保持同步"（只加不删）。** 一次性与续跑**从两端逼近同一权威**，只有缓存侧不对称 ⇒ 事件流分岔。

## 6. 最小修法方向（**属 life，另任务；本文只给方向，不实施**）

- **(首选)** 让 life 缓存**对齐权威**：`AssociativeMemory.sync_from_refs` 或遗忘处理后**裁剪不在权威 refs 中的节点**（`MEMORY_FORGET(drop)` 时同步移除 `self.memory.nodes[mid]`）；
- **(或)** `_maybe_sleep_window`/固化/遗忘的**输入**从 `self.memory.nodes` 改用**权威** `wv.memory_refs`（单一真源）。
- **两法都属"让运行期与权威一致"**，**不动语义、不做有界化**（符合硬约束）。

## 7. 验收对照（供 life 修复任务）

- 同配置（`seed=9/n=2/150`）**逐字节一致**；`tools/t271/verify_native_resume.sh` **PROBE ok**；
- 回归：`MEMORY_FORGET` 计数两路相等、`only-in-ref` 差集消除。

## 8. 诚实标注 / 边界

- 本取证为**只读**（解析日志折叠，未跑改码）；**未改 `code/`**。
- **未验证**：life 侧 `self.memory.nodes` 的**确切增删点**（本次由**行为指纹**推断，读码级确认交 life-layer-dev；persona-life-designer 已给 `memory.py` 全文件无 `pop/del/remove` 的读码证据）。
- 探针在**批期外**运行；`ref/n1b/warm.jsonl` 存于 `/root/t271/runs/nr/`（临时）。

---
*（T296 只读取证结束 — art-director）*
