# T296 · 只读归因：native 续跑在 `seed9/n2/150`(kill@89) round 93 起 `MEMORY_FORGET` 分歧

> 作者：sim-system-architect ｜ 2026-10-12 ｜ **只读诊断（未改 code、未跑批）**
> 用途：**art-director 的复现取证检查清单** + life-layer-dev 的修复起点
> 上游：T292 `T292-native-resume-verify.json`（`28862a4`）；T276/T288（续跑/逐字节）；Leader 裁定（22:23）
> 标注：**【事实】**=有证据；**【假设】**=未验证；**【待定】**
> ⚠️ 我**不接 T296 本体**（Leader 裁定：life 修、art 取证）；本文件=我的部分（只读归因）。

---

## 1. 【事实】现象（T292 探针）

- 配置 `seed=9 / agents=2 / rounds=150 / flush-every=5`，**kill@89**。
- 前缀（rounds 0–89）**逐字节一致** ✓；**分歧自 round 93 起**：
  - **续跑**：`MEMORY_FORGET` 选 `level=merge mem_id=M-P001-000005`
  - **一次性**：`level=drop mem_id=M-P001-000003`
- 已排除：冷/热缓存差异（预热后仍复现）、随机性（同 sha 稳定）。
- ⇒ round 90 恢复后的世界/记忆态与一次性跑**有细微差异**，**4 回合后暴露**。

---

## 2. 【假设】四候选（按怀疑度排序）+ **排除推理**

> **总方向**：`restore()`（`life/agent.py:126`）的镜像重建不完美（**与 T276 同源**）。

### 候选 (1) `emo` / `referenced_by_reflection` 不在账本记忆 ref
- **依据**：`MEMORY_WRITE` 折叠的 ref（`replay.py:331-344`）与 `MemoryRef`/`sync_from_refs`（`life/memory.py:336`）**都不带** `emo`、`referenced_by_reflection`；而 `forgetting.is_protected`（`life/forgetting.py:4-21`）**用**它们。
- ⇒ 一次性跑用**活节点**（有这两个字段）、续跑用**重建节点**（缺）→ `is_protected` 可能不同。
- ⚠️ **主动排除**：**本分歧是 `merge` vs `drop`，两者都在"非保护"分支**（`forgetting.py:41-46`；保护记忆只会 `keep/demote`）⇒ **候选 (1) 不是本分歧的直接原因**（但仍是真缺口，值得一并记录）。

### 候选 (2) ★ `access_count` / `last_access` 重建口径（**最可疑**）
- **依据**：
  - 一次性跑：节点字段由 `touch()`（`memory.py:521` 更新**活对象** `node.access_count/last_access`）**+** `MEMORY_RETRIEVE` 折叠（`replay.py:345-351` 更新 `state.memory_index.get(mid)` 的 ref）**双路径**更新。
  - 续跑：`restore()` 只从 `a["memories"]` 的 ref 经 `sync_from_refs` 重建。
- **关键检查点**：**`MEMORY_RETRIEVE` 折叠更新的 `memory_index[mid]` 与 `MEMORY_WRITE` 折叠塞进 `a["memories"]` 的，是否同一个 dict 对象**？
  - 若**同一对象** ⇒ 更新互见，restore 读到正确值（**分歧不在此**）。
  - 若**不同对象**（如 `a["memories"]` 存副本、`memory_index` 存另一份） ⇒ restore 读到**陈旧** `last_access/access_count` → `forgetting.classify` 的 `dt = round - last`（`forgetting.py:30-32`）偏差 → `retention_permille` 偏差 → **恰在 round 93 跨 `theta_forget`** ⇒ 解释"merge vs drop"。
- **优先级**：**最高**（与现象量级/时点最吻合）。

### 候选 (3) `_unreflected_importance` 与 `reflected` 回填不全
- **依据**：`restore()`（`life/agent.py:51-64`）**只**从 `MEMORY_REFLECT.triggered_by_mem_ids` 回填 `nd.reflected=True`，再重算 `_unreflected_importance`。
- ⇒ 若某节点的 `reflected` 未被 `triggered_by_mem_ids` 覆盖（例如反思产物/多轮），重建后 `reflected` 与一次性不同 → 影响**反思**触发；**间接**改变记忆**新增/合并**，从而在后续 round 改变 `has_sibling`/记忆集 → 可解释"不同 mem_id 被选"。

### 候选 (4) `written_round` 回退字段
- **依据**：`classify` 取 `last = mem.get("last_access", mem.get("written_round", 0))`（`forgetting.py:30`）。若重建路径**未设** `written_round` 而某节点又无 `last_access`，回退值与一次性不同 → `dt` 偏差。

---

## 3. 【核验法】一次小跑即可判定（art-director 取证用）

**在 round 90（恢复点）**，两条路径各 dump 目标记忆的**判定输入**并 diff：

对 `P001` 的 `M-P001-000003` 与 `M-P001-000005`，逐字段打印：
```
mem_id, last_access, access_count, written_round, subject, importance,
emo, referenced_by_reflection, kind, has_sibling(该 subject 的兄弟数)
```
- **对比对象**：`续跑(restore 后) 的 plan_forgetting 输入` **vs** `一次性(round90) 的 plan_forgetting 输入`。
- **判定**：
  - 若 `last_access`/`access_count` **不一致** ⇒ **候选 (2) 成立**（→ 查 `memory_index` 与 `a["memories"]` **是否同一对象**）。
  - 若 `subject`/`has_sibling` **不一致** ⇒ 候选 (3)（记忆集因反思差异分叉）。
  - 若 `emo`/`referenced_by_reflection` 不一致但**不影响本分支**（merge/drop 非保护）⇒ 记录为**次生缺口**（候选 1）。
- **最小取证**：只需 `seed9/n2`、跑到 round 90 附近；**批期不做**；`>N=20` 先报 Leader + 内存上限。

---

## 4. 【待定】修法方向（life，交 life-layer-dev；**原样重建、不做有界化**）

1. **确认对象同一性**：让 `MEMORY_RETRIEVE` 折叠更新**与 `a["memories"]` 同一对象**（或 restore 时从 `memory_index` 取值），消除陈旧读。
2. **补字段**：若确需，`MemoryRef`/`sync_from_refs`/`restore()` 补 `written_round`（及必要时的 `emo`/`referenced_by_reflection`），**只做原样重建**。
3. **reflected 回填**：核对 `MEMORY_REFLECT` 之外是否还有置 `reflected` 的路径。
4. **验收**：该配置（`seed9/n2/150`, kill@89）也**逐字节一致** + `tools/t271/verify_native_resume.sh` PASS。

---

## 5. 边界与不做

- **本文件只读归因**；不复现、不修码（Leader 裁定：life 修 / art 取证）。
- **不把"逐字节一致"降级**（不可放宽验收）。
- **批期不动世界层**（当前有批在跑，宿主内存紧张）。

---

*（T296 只读归因结束 — sim-system-architect；4 候选 + 排除理由 + 核验法；未验证处已标）*
