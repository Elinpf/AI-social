# T35 绿灯恢复报告（D1 回滚掩盖的真 bug）

> 作者：kernel-dev ｜ 时间：2026-10-10

## 根因
D1「整回合回滚」本身正确，但它把一处 **life↔内核接口不匹配** 暴露成 SYSTEM_ERROR：

- 我折叠 `RELATION_ENCOUNTER` 时把每 Agent 的 `encounters` 存成**整数计数**；
- life L5 `update_relations` 读的是 **`agents[*]["encounters"][other_agent]` 字典**（`.get(b,0)`）；
- → 从第 1 回合起每回合钩子抛 `AttributeError('int' object has no attribute 'get')`；
- → D1 回滚丢弃本回合缓冲，只落 `SYSTEM_ERROR`，世界 523 事件后停摆，而外层 replay/守恒仍全绿。

## 修复
1. `engine/replay.py`：`RELATION_ENCOUNTER` 折叠为 `encounters = {对方agent: 次数}` 字典；`engine/state.py` 的 `new_agent_dict` 初始 `"encounters": {}`。
2. `tests/test_e2e_integration.py` 导入改指 `orchestration.integration`；`engine/integration.py` 恢复为兼容 shim。
3. `engine/state.py`：`state_hash` 投影剔除可由日志重建的重集合（memory_index/observed/event_index/每 Agent memories/全局 encounters），把 N=10×84 从 36s 降到 28s。

## 三条输出
1) `python -m engine run --life --agents 20 --rounds 84`
   `n_agents=20 rounds=84 events=148133 seconds=208.2 log_bytes=67592630`
   `unknown_event_types=[] chain_ok=True replay_parity=True first_run_equals_replay=True conservation_ok=True`，**SYSTEM_ERROR=0**。
2) `python -m pytest -q` → **111 passed in 22.5s**（含新增 `tests/test_run_health_gate.py`）。
3) `python -m obs gate --log /tmp/hitt_life20.jsonl` → **GATE PASS**（bitwise metrics/census、llm_calls_zero、money_conservation 全 PASS；distribution_regression SKIP=无黄金基线）。

## 事件分布对照
| 事件 | 现 N=3×84 | T34 N=3 | 现 N=10×84 | T34 N=10 |
|---|---|---|---|---|
| 总事件 | 3723 | 1730 | 36185 | 8992 |
| MEMORY_WRITE | 1126 | 318 | 13716 | 2812 |
| OBSERVATION | 1063 | 255 | 13506 | 2602 |
| ACTIVITY_COMPLETED | 63 | 63 | 210 | 210 |
| TIME_MARK | 7 | 7 | 7 | — |
| SYSTEM_ERROR | **0** | 0 | **0** | 0 |

现行量高于 T34：life 已实现 L5 `update_relations`（T34 时为 no-op），现每个共处对**每回合**发 `RELATION_CHANGE`，且它在 `_SALIENT_EVENTS` → 双方各 OBSERVATION+MEMORY_WRITE，放大约 4×/对。**属 life 侧量级设计，非内核塌陷。**

## 新增回归门禁（防"静默停摆"）
`tests/test_run_health_gate.py` 断言：`SYSTEM_ERROR==0`、`TIME_MARK==日边界数`、`TURN_SEAL==rounds`、`MEMORY_WRITE>0`、`OBSERVATION>0`、`ACTIVITY_COMPLETED>0`、事件量 ≥ T34 下界；覆盖 N=3×84、N=10×24、N=20×12。

## 待裁决（非阻塞）
N=20×84 事件 14.8 万 / 208s / 67MB，主因 life L5 每回合对每个共处对发关系事件并被显著化记忆。建议 life 改为"仅首次/超阈/变化时"发，或降观察显著度。

## 附：同类问题复发点（Leader ① 排查结论，2026-10-10 追记）

**现象**：真内核 N=10×84 上 `TAG_EMITTED=0`、`NORM_PROPOSED/ADOPTED/VIOLATED=0`、`GOAL_ACHIEVED=0`、`GOAL_PROGRESS=0`；life 自包含 mini 上非 0。

**根因（内核语义 vs life hook 假设不一致）**：
- 蓝图 §2.3 规定 hook **串行折叠** `state := hook(state).state`；且 L2→L3 依赖（L2 发 `ACTIVITY_STARTED`，L3 据 `current_activity` 判完成）**必须**增量折叠才成立。故内核实现为**逐 hook 即时折叠**（本次修正：原来我把 L1–L7 输出收集完再一起折叠，导致 L7 看不到 L3 的产出）。
- 但 life 的 `_due_completions(state, round)` 读 `agents[*]["current_activity"]`；L3 `settle_activities` 发出 `ACTIVITY_COMPLETED` 后，内核折叠会**清除 `current_activity`**。于是 L4 `apply_needs`（goal progress）与 L7 `emit_tags` 再次调用 `_due_completions` 时得到 **空** → 无 `GOAL_PROGRESS`、无 `TAG_EMITTED` → 连带无 `NORM_*`。
- life 源码注释称"从 current_activity 派生，以对内核批量折叠 hook 输出保持鲁棒"——即 life 假设 **P3.5 输出批量折叠**；这与蓝图的串行折叠契约冲突，且批量折叠会破坏 L2→L3。

**结论/建议（life 侧修，内核不改）**：life 的 L4/L7 不要复用 `_due_completions`（其输入已被 L3 折叠清除），改为读**同回合已折叠的 `ACTIVITY_COMPLETED` 事件**（`LifeState.events_this_round(round_no,"ACTIVITY_COMPLETED")`，已验证可用），或由 L3 产出一份完成清单 memo 供 L4/L7 读。内核保持**逐 hook 串行折叠**（蓝图 §2.3）。

**内核侧已做**：`Engine.phase_life/phase_arbitrate` 改为**逐 hook 即时 emit+折叠**（修复"收集后统一折叠"导致的 hook 间不可见）。该修正本身正确且必需；剩余 0 值由 life 的 `_due_completions` 复用假设触发，待 life 侧调整。

**验证**：`engine run --life` 下 `emit_tags` 在 L7 能看到同回合 `ACTIVITY_COMPLETED=3`（event_index），但 `_due_completions` 因 `current_activity` 已清而返回 0 → `TAG_EMITTED=0`。判定为 life 侧修复项。
