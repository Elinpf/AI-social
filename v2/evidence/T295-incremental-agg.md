# T295：`event_index` 读路径优化（增量聚合）—— 等价对拍 + 实测

**日期** 2026-10-13 · **作者** kernel-dev · **依据** T285 spike `41c60d7` + 08 §5.9
**scope**：读路径优化（增量聚合）；**不动事件顺序/判定/`state_hash`**；验收 = **增量表 == 全表扫 逐条等价**。

## 1. 设计

- **派生累加器**（不入 `state_hash`、不进 `restore()`；可由日志重建）：
  - `state.events_by_round[round][type] -> [seq]`（seq 升序）
  - `state.seqs_by_type[type] -> [seq]`
- **累加点（唯一）**：`replay.apply_event`（`arbiter.emit` 经此、`replay_records` 经此）——
  与 `event_index` **同点写入、同 seq**，故累加器**镜像 `event_index`（含本回合 pending）**。
- **读取**：`engine/event_acc.py`（`recs_of_round/recs_of_type/recs_of_types/…`），保持 seq 全序、顺序不变。
- **信任/自愈**：`state.acc_trusted`（Engine / `replay_records` 产出 = True）；**非可信状态（单测直接注入/覆盖 `event_index`）每次读取时重建**（等价全表扫）。

## 2. 已改造消费点（cProfile 热点）

`scheduling.daily_token_usage/daily_judge_calls` · `econ._round_ie_eff` · `lifecycle._events_of_round/_distress_series_all/_flagged_inflow_map` · `liquidity.recent_default_of/recent_income` · `exchange._offer_chain/_expire_offers/_active_contracts` · `production._labor_completions/_skill_level` · `wake._history`。
（`contracts.visibility.*` 已在 **T264** 覆盖。）

## 3. 逐条对拍（验收核心）

`tests/test_t295_event_index_acc.py`：
- **daily_token_usage / daily_judge_calls**（逐 day）与参考全扫逐条相等 ✓
- **econ._round_ie_eff**（逐 round × agent）与参考全扫相等 ✓
- **lifecycle._events_of_round**（逐 round，含 types 过滤）与参考全扫（seq 升序）相等 ✓
- **live == replay 累加器**（`events_by_round` 与 `seqs_by_type` 双侧齐）✓
- **`state_hash` 不变**（清空派生表前后相等）✓
- **反向验证**：把累加器改成**自洽但错误**（删一条 seq）⇒ 消费点输出随之改变（测试对坏输入变红）✓

`code/tests` 全量：**499 passed**。

## 4. 历史回读时间实测（N=10×24，13,041 事件）

对 `daily_token_usage + daily_judge_calls + recent_default_of + recent_income` 各 20 次：

| | 耗时 |
|---|---|
| 累加器（可信） | **0.046 s** |
| 强制全扫（`acc_trusted=False`） | **2.139 s** |
| **加速** | **≈ 46.5×** |

## 5. 与 T276 / T285 的对齐

- 累加器**可重建** ⇒ **续跑由 `replay` 恢复，不进 `restore()`**（08 §5.9）✓。
- **不新增 config 键、不改指纹** ⇒ **T300 重冻不必等 T295**（若后续加键会显式标注 + 通知 obs）。

## 6. 未做（诚实边界）

- `wake.compute_wake_set` 主循环（按 `seq>floor` 跨全历史扫描）**未改造**（结构不同）——遗留项，后续可基于 `events_by_round` 从 `floor` 回合起迭代。
- `life/settlement.py::events_this_round` 属 **life 侧**（跨文件），未动；如需可另与 life 协调。
