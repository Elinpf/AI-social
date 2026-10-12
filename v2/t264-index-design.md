# T264 步骤⑤：`visible_events` 增量索引 —— 设计 + 放置裁决请求

> 作者：kernel-dev ｜ 2026-10-12 ｜ 状态：**设计（未实现）**，等放置裁决

## 0. 目标与硬约束
- 目标：消灭 `visible_events` 的 **per-agent 全量重扫**（当前 O(N × 总事件)），降为「预分桶 + 逐 agent 只碰候选桶」。
- **谓词语义仍唯一真源**：索引**只改变"如何取候选"**，判定仍调 `contracts/visibility.py::visible()`。验收 = **逐字节不变**（同日志输出序列完全一致，含 `PERCEPTION_SCOPE` 结果）。

## 1. 核心矛盾（为何需裁决"放置"）
- 索引是**跨调用缓存（有状态）**：需按 `(records 前缀, round)` 缓存"按 scope 预分桶 + location 时间线"。
- 但 `contracts/` 刚立**边界条款**：**只许零依赖纯类型/协议 + 契约级纯判定规则（无状态）** → **索引不能放 `contracts/`**。
- 且 `life` **不得 import `engine`** → 索引也不能放 `engine/` 再由 life 用。

## 2. 放置选项
- **(A) 调用方各自缓存**（`life/visibility.py`、`engine/perceive.py`、`adapter` 各持一份）：零结构变更，但**又回到"多处实现"**（正是 T264 要消灭的漂移源）→ **不推荐**。
- **(B) 新增中立模块**（如 `code/visibility_index/`）：一份带缓存的索引实现，life/engine/orchestration 均可 import（不违反"life 不 import engine"）。
  - 代价：**新增一个一级域 + 一条 import-linter 规则**（与 leader 先前"为一个模块新增一级域成本大于收益"的取向相反，但这是**有状态缓存**，性质不同）。
- **(C) 组合根构建 + 注入**：`orchestration` 每回合构建索引，经 `KernelPort`/进程内句柄注入给 life 的 L6 与 adapter；`contracts` 只提供**纯分桶函数**（无状态）。
  - 关键：life 的 L6 `write_memories` 目前直接调 `life.visibility.visible_events(records,...)`；需改为**使用注入的索引句柄**（life 侧小改，属可对齐）。

**我的倾向**：**(C)**（分层最干净：contracts 纯、索引在组合根、life 不依赖 engine）或 **(B)**（若希望索引也可被非 orchestration 的调用方复用）。

## 3. 逐字节不变的做法（无论 A/B/C）
- 预分桶：`global` / `place_local:<place>` / `subject_only:<agent>` / `private:<agent>` / `members:<group>` / `participants_only`。
- 逐 agent 取：`global ∪ place_local(agent.loc(t)) ∪ subject_only(agent) ∪ private(agent) ∪ members(groups(agent)) ∪ participants(agent)` 的并集，**按 `seq` 升序归并**，再对每条调 `contracts.visible()` 过滤（保持账本顺序 → 输出与原全扫逐字节一致）。
- location 时间线：由 `PLACE_MOVE/ARRIVED` 增量维护 `agent → [(round, place)]`，`loc(t)` 二分。

## 4. 复杂度
- 原：每 (agent, round) O(E_total) → 总 O(N·R·E_total)。
- 新：预分桶 O(E_total)（每回合增量追加）+ 每 (agent,round) 只遍历**候选并集**（≈ 全局 + 本人相关）→ 总 ≈ O(E_total + N·R·|candidates_window|)。
- 与 T263 估算一致（~8.6e8 → ~1.7e7）。

## 5. 待裁决
- **放置选 (B) 还是 (C)？** 选 (C) 需 life 侧配合一处（L6 用注入索引）——我会与 life-layer-dev 对齐。
- **G2（补 scope 表）** 待 `sim-engine-stats-architect` 给权威 `event_type→class` 清单（另函）。
- **G1/G3** 改语义 → 待裁，不在本步。
