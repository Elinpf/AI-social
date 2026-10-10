# T91 预备：纯内核已完成 + 两处跨模块「最小改法」报告

> 作者：econ-dev ｜ 2026-10-10 ｜ 状态：等 T90；本文件为**方案报告**（待 Leader/lifecycle-dev/kernel-dev 对齐后再动共享代码）

## 0. 已完成（schema 无关，纯函数，已测）

- 新增 `code/engine/production.py`：生产函数（定点，`qty=⌊base×技能(1+0.1lv)×resource×(1+tool)⌋`）、
  资源丰度（`draw_u64` 确定性抖动）、库存增删/上限溢出、配方投入门（`can_produce`）、折旧、
  **`M≥0` 销毁地板 `burn_floor`**、兜底铸币 `fallback_mint`、最小市场参考价带宽 `market_ref_band`。
- 新增 `code/tests/test_production.py`（9 项，全绿）：定点正确性、因子限幅、资源确定性、库存溢出/原子出库、
  配方门、折旧 floor、连续销毁 `M≥0`、兜底铸币上限、参考价带宽。
- **未触碰**：事件注册（events.py）、折叠（replay.py）、PHASE4 链、state 字段。

## 1. `M(t)≥0` 最小改法报告（econ×lifecycle×kernel）

**问题（canonical B2_N20）**：`M` 于 r72 起穿负至 −9,620。根因：销毁通道（`METABOLISM` 等）**无地板**，
在账户/总量耗尽后仍继续扣，`METABOLISM` 折叠 `cash[aid]-=amt; burned+=amt` 使 `cash` 变负；
`conservation` 用的是**代数恒等式**（`minted−burned==Σcash+Σdeposits+pool+reserve`），不约束 `M≥0` 的物理意义。

**最小改法（按「只扣可得部分」，不新增事件、主要不改折叠器）**：
1) **销毁点 emit 时按可得量钳制**（在各自 hook 内，不动折叠器）：
   - `METABOLISM`（lifecycle 4.4）：`amt = min(m, max(0, cash[aid]))`（不得把 `cash` 扣成负）；
   - `INTEREST_CHARGED`（econ 4.2）：`amt = min(interest, max(0, cash[borrower]))`（我改）；
   - `PENALTY_APPLIED`（lifecycle 4.5 + econ 4.2 坏账罚没）：`amt = min(fine, max(0, cash))`；
   - `TRANSFER/MARKET_TRADE` 的 `fee`（econ 4.1）：emit 前已校验付款方足额（已满足）；
   - `UBI_PAID`（econ 4.3）：已按税池缩放（`tax_pool` 不穿负）；`INTEREST_PAID`（若启用）：钳到 `bank_reserve`。
   - `LOAN_DEFAULT` 折叠器只改台账、**不动现金**（当前设计），不涉 `M`。
2) **兜底不变量（kernel 侧，安全网）**：`engine/conservation.check_all` 增加 `money_supply(state) ≥ mu_floor(默认0)`
   校验；不成立 → 沿用「整回合回滚 + `ECONOMY_INVARIANT_VIOLATION`」。
3) **保底「总量地板」**（C 层）：`apply_metabolism` 在 `M(t) < μ_floor` 时**暂停销毁**（用 `burn_floor` 已能保证），
   打 `flag=floor`；**不铸币**。

**为何是「最小」**：折叠器（`replay.py`）与事件类型**均不改**；改动集中在 3 个销毁 hook 的 emit 钳制（lifecycle 2 处 + econ 2 处）
与 1 处守恒断言（kernel）。**请确认**：① 认可「emit 钳制 + 守恒断言」路线，还是要走「折叠器内置地板」（需 kernel 改 fold）；
② `μ_floor` 默认 0 是否够（是否要留一点正地板）。

**跨模块落点**：lifecycle-dev（4.4/4.5 钳制）、kernel-dev（conservation 断言）、econ-dev（4.2 钳制）。**我先不动共享代码**。

## 2. `apply_production` 接入方案（待 T90 后接事件）

- **新 hook** `engine/hooks/production.py::apply_production(state, round_no, ctx)`（纯函数、`spec()` 产事件）。
- **挂载点**：`PHASE4_CHAIN` **首项（4.1 前）**——理由：生产先更新**商品库存**，4.1 市场再基于新库存撮合，4.2/4.3 再动货币；
  全程 Phase4 全序不变（只插一项，不改既有相对序）。→ **需 kernel-dev 改 `engine/hooks/__init__.py` 的 `PHASE4_CHAIN`**（一处）。
- **生产触发（life↔econ 边界，需 life-layer-dev 对齐）**：建议 life 层劳动/活动产出 `INTENT.PRODUCE{good_id, place}`（或由我在
  4.1 前读取本回合 `ACTIVITY_COMPLETED` 的劳动类 activity→good 的**确定性映射**）。请 Leader 裁：走新 intent 还是复用 activity。
- **库存载体**：`state.inventory`（`(owner_id, good_id)->qty`）。由 kernel-dev 在 `replay.py` 为 4 个商品族事件加折叠器
  （`PRODUCE +qty(溢出扣)、CONSUME -qty、DEPRECIATE -loss、PRODUCE_OVERFLOW 仅记录`），并决定 `inventory` 是否入 `state_hash`
  （建议**入**，商品是权威状态；或与 `memory_index` 同列为「可由日志重建」而排除）。
- **双账本守恒**：`engine/conservation.check_all` 增加**商品式** `ΣPRODUCE == ΣCONSUME + Σ库存 + Σ溢出 + Σ折旧耗损`
  （kernel-dev；口径与 obs 一致）。
- **保底最小市场**：`MARKET` 账户按 `market_ref_band(p_ref)` 买卖必需品（带宽内），**不强制成交价**；打 `flag`。

**请确认/分派**：① PHASE4 插入点（4.1 前）与 `inventory` 是否入 `state_hash`；② 生产触发走新 `INTENT.PRODUCE` 还是复用 activity；
③ 商品式守恒与 `M≥0` 断言由 kernel-dev 落；④ T90 完成后我立即认领 T91 并按此接线。
