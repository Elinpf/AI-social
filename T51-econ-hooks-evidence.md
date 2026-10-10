# T51 · Phase 4.1–4.3 经济 hook 实现与验收证据

> 作者：econ-dev ｜ 日期：2026-10-10 ｜ 交付物：`code/engine/hooks/econ.py`（+ `code/tests/test_econ_hooks.py`、`code/scripts/run_econ_acceptance.py`）

## 0. 交付与状态

- **实现**：`code/engine/hooks/econ.py`
  - 4.1 `settle_market`：消费 life 层 `resource_intents`（`ACTIVITY_COMPLETED`）与 `pending_intents`（`INTENT.ECON.*`）；
    原子转账 / 成交、手续费 50% 税池 + 50% 销毁、反作弊 flags 打标、拒绝自成交。
  - 4.2 `settle_obligations`：到期/逾期判定、计息（`INTEREST_CHARGED`）、续命贷发放（确定性信贷规则）、
    坏账核销（`LOAN_DEFAULT`）、存款（`DEPOSIT`/`WITHDRAW`）、存款利息（默认关）。
  - 4.3 `apply_tax`：内部子序 **铸币判定 → 收入税 → 财富税 → UBI**；对 `max(0,I_eff)` 计征；系统项不计入 `I_eff`。
  - 总开关 `economy.enabled`（T58 消融）：`config['policy']['economy']['enabled']`（默认 **true**）/ runtime `config['economy']['enabled']` 优先。
- **测试**：`code/tests/test_econ_hooks.py`（16 项）；全仓 `pytest -q` = **219 passed**。
- **证据脚本**：`code/scripts/run_econ_acceptance.py`。
- **状态**：T51 完成；`MARKET_TRADE.scarcity_index` 已按 T60 登记填入。

## 1. 验收（实测）

命令：`python scripts/run_econ_acceptance.py --n 20 --rounds 84 --seed 42 --ubi 100 [--metabolism 100]`

### Run B —— 经济 + 生命周期（`lifecycle.enabled=true, METABOLISM_MU=100`）：**6 类经济事件全部 >0**

| 事件 | 计数 |
|---|---|
| `TRANSFER` | **27** |
| `MARKET_TRADE` | **21** |
| `DEPOSIT` | **19** |
| `TAX_LEVIED` | **44** |
| `UBI_PAID` | **284** |
| `INTEREST_CHARGED` | **66** |
| （辅助）`LOAN_ISSUED` / `LOAN_DEFAULT` / `METABOLISM` | 19 / 1 / 1680 |

- 守恒：`conservation_ok=true`（`minted 202890 − burned 168000 = supply 34890`），`ECONOMY_INVARIANT_VIOLATION=0`
- `SYSTEM_ERROR=0`；`replay` 逐位一致（`first_run_equals_replay=true`，两次重放哈希相等）
- obs 口径：`n_transfers=48`、`transfer_volume=4800`、`gini_cash_final=0.104`、`n_active_loans=18`、`outstanding_principal=2798`、`tax_pool_final=0`
- 事件总量 123248；`AGENT_DIED=0`/`AGENT_REVIVED=0`（本档 84 回合未触发判死，故未走到复活）

### Run A —— 仅经济（`lifecycle.enabled=false`）：5 类经济事件 >0，`INTEREST_CHARGED=0`（无放贷，符合预期）

| 事件 | 计数 |
|---|---|
| `TRANSFER` / `MARKET_TRADE` / `DEPOSIT` | 27 / 21 / 19 |
| `TAX_LEVIED` / `UBI_PAID` | 44 / 121 |
| `INTEREST_CHARGED` | 0（无贷款） |

守恒 `ok`（`minted 200000 − burned 0 = supply 200000`）、`SYSTEM_ERROR=0`、`replay` 一致。

> `INTEREST_CHARGED` 需「先有贷款」；贷款来自 4.2 续命贷（触发条件 `E<θ_warn`），而 `E` 下滑依赖 4.4 代谢。
> 故 **`INTEREST_CHARGED>0` 是经济×生命周期的联调项**：经济开关开、代谢关时其为 0 属机制正确（无贷款则无利息）。

## 2. 关键实现口径

| 项 | 口径 | 依据 |
|---|---|---|
| 单位 | 整数 `mu`（1 CR=100 mu），禁浮点 | D0-1 |
| 手续费 | 销毁半额走 `TRANSFER/MARKET_TRADE.fee`（折叠器 `burned+=fee`）；税池半额走 `TAX_LEVIED(kind="fee")`（不入 I_eff/基础流速） | v1/03 §5.6、§1.5 |
| 系统对手方 | `seller="MARKET"` 为世界市场账户，首次出现即 `STATE_CHANGE→terminated`（移出存活集，不被 4.6/4.8 当真人） | 与 kernel-dev 约定 |
| 续命贷 | `lender=None`（世界银行）→ 系统发行；仅 `E<θ_warn` 且无存量债务者；`principal≤min(L_max,D_max,θ_warn−E)`；利率 `r=r_base+k_pen·max(0,−E)/E0` | v1/02 §3.1、§4 |
| 收入税基 | `max(0,I_eff)`，`I_eff` 口径与 `obs/antifraud.ie_eff` 一致（仅 `transfer/trade`，排除 self/wash/cycle/mule 与系统项） | v1/02 §5.2 |
| UBI | 税池发放、不足按比例缩放（**不铸币**）、确定性最大余数分配；系统项不计入 `I_eff` | v1/01 §5.2、v1/02 §1.4 |
| 铸币判定 | 4.3 首子序保留**判定接口**；既有 `MONEY_MINTED` 折叠器只增计数不落账户，单独 emit 必破守恒，故当前不触发（无 drains 时 `M≈M_target`），待内核提供可守恒铸币折叠后启用 | v1/03 §1.3 |
| `scarcity_index` | 按 T60（08 §1.2-N）填：整数 0–100，`=clamp(0,100,100−min(100,⌊100·stock/demand⌋))`，stock=市场名义存量（config `market_scarce_supply`）、demand=近 `W_scarce` 回合 scarce_buy 计数+本笔 | T60 |
| 原子性 | 每笔转账/成交先校验资金（含手续费）再 emit；不足→`DROPPED`，无半记账；跨笔失败逐笔降级不拖垮回合 | v1/01 §3.3 |

## 3. 单元测试覆盖（`tests/test_econ_hooks.py`）

`gift→TRANSFER` / `deposit→DEPOSIT` / `buy→MARKET_TRADE`（含手续费分流守恒、`scarcity_index` 0–100）、
**原子性**（余额不足不半记账）、**自转账/自成交拒绝**、**pending ECON.TRANSFER 只消费一次**、
**订单簿同回合即时交叉 + 拒绝自成交**、**flags 打标**（self/wash/cycle）、
**续命贷发放 → 次回合计息**、**收入税对 I_eff 计征且 UBI 不计入 I_eff**、**UBI 按池缩放不铸币**、
**财富税阈值**、**hooks 不直写账**、**内核级整回合守恒 + 重放一致**、**`economy.enabled=false` 全跳过**。

## 4. 开放问题 / 卡点（请 leader 裁决）

1. **续命贷 ≠ 复活（净值口径冲突，重要）**：`net_worth = cash + deposits − 债务`，借款时 `cash+`、`debt+` 相抵，
   **放贷不改善 `E`、且 `LOAN_ISSUED` 不计入 `I_eff`**；故 4.2 续命贷**无法单独把 `dead` Agent 抬到 `E≥θ_recover`**。
   现值复活依赖 **world rescue**（lifecycle 4.3：`INIT_ENDOW`+`flag=rescue`，直接抬 `E`）或**他人有效转入**。
   → 若要求「续命贷能复活」，需裁决改为「救助型续命贷」（补贴/减免，直接抬 E 或记 `I_eff`）；否则保留现状并在方案中写明。
2. **利息对超负余额的累积**：深负账户仍按 `outstanding` 全额计息（现金可为负），极端档（`m=200`）下 `tax_pool` 与负现金放大。
   建议 4.2 增「利息以可用现金为上限 / 逾期并入本金」口径之一（需裁决，涉及折叠器）。
3. **E2（gift）/E9（稀缺买）在自然运行未命中**：E2 因 `affinity≥50` 前置在 84 回合内不可达（life/planner，T49 范围）；
   E9 因 `scarcity_index` 本档恒 <50（供需代理默认）；均为 life/schema 侧，非 4.1 缺陷。
4. **`DEPOSIT/WITHDRAW` 内核折叠**：原在 `_NOOP_TYPES`，与 `obs/econ.fold_economy` 口径不一致；
   已由 kernel-dev 补齐真实折叠器（`tests/test_deposit_fold.py`），本轮已对齐。
