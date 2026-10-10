# T62 · 4.2 续命贷改为「流动性供给 + 确定性授信」实现与验收证据

> 作者：econ-dev ｜ 更新：2026-10-10（依 Leader 采纳的 canonical 档刷新） ｜ 交付：`code/engine/liquidity.py`（新增）、`code/engine/hooks/econ.py`（4.2 改造）、`code/tests/test_liquidity.py`、`code/tests/test_econ_hooks.py`

## 0. 交付与统一接口（T61×T62）

- **新增 `engine/liquidity.py`（纯函数、无状态、可重放）** 作为 econ×lifecycle 统一接口：
  `debt_of / overdue_of / recent_default_of / recent_income / net_worth_of / credit_limit / can_borrow / liquidity`。
  视图 `liquidity(state,aid,t,params) -> {cash, L, deposits, debt, credit_limit, can_borrow, overdue, net_worth}`
  （`L = cash` 为判死基准；`net_worth` 仅记录）。**不新增 state 字段、不新增事件类型**。
- **参数单一来源**：`policy.economy`（`resolve_params` 读 policy 顶层默认 ← policy.economy ← config.economy）。
- **4.2 `settle_obligations`**：计息（`INTEREST_CHARGED`，含逾期罚息）→ 逾期超 `n_overdue` 落 `LOAN_DEFAULT`
  + `PENALTY_APPLIED(kind=bad_debt_forfeit)`；**负净值惩罚** `PENALTY_APPLIED(kind=negative_worth)`（P1 升级）；
  对 `can_borrow` 的 Agent 发放续命贷 `LOAN_ISSUED`（`lender=None` 世界银行系统发行，**cash↑ debt↑、净值不变**，会计诚实）。
- **确定性授信规则**（非 LLM）：
  `credit_limit = min(D_max − debt, ⌊LTV·(cash⁺+deposits)⌋ + unsecured_base + ⌊k_income·max(0,近窗正I_eff)⌋)`；
  无抵押且无收入（且 `unsecured_base=0`）→0；`overdue`/近 `w_cool` 坏账→0（信用降级）；`D_max` 硬上限。
- **放贷确切准入 `can_borrow`** = `L<trigger` 且无存量未偿 且无 `overdue` 且 `credit_limit>0`（lifecycle 直接消费）。
- **不做补贴型续命贷**（不用补贴/减免抬净值）。

## 1. 验收（实测，rule-based N=20×84, seed=42；**canonical 档**）

**canonical 参数**（Leader 采纳 lifecycle-dev 基线；已写入 `config/policy.json`）：
`economy`: `enabled=true`、`liquid_trigger_mu=250`、`liquid_sustain_mu=600`、`credit_unsecured_base_mu=0`、
`credit_ltv_bp=6000`、`income_credit_bp=20000`、`negative_worth_penalty_bp=100`；
`lifecycle`: `metabolism_mu=140`、`ubi_mu=0`。

| 指标 | 值 |
|---|---|
| `LOAN_ISSUED` | **20** |
| `LOAN_DEFAULT` | **7** |
| `INTEREST_CHARGED` | **270** |
| `PENALTY_APPLIED` | **2** |
| `AGENT_DIED` / `AGENT_REVIVED` | 20 / **10** |
| 经济族 | `TRANSFER=27`、`MARKET_TRADE=21`、`DEPOSIT=19`、`TAX_LEVIED=44`（`UBI_PAID=0`，canonical ubi=0） |

- **三类路径并存（错峰）**：
  - **借债续命存活**：`borrowed_alive = [P009, P012–P020]`（10 人，借到钱后 84 回合仍存活）。
  - **借不到（新增流动性耗尽）→死**：`borrowed_died = 10` 人（贷款后 `debt>0` ⇒ `can_borrow=False`，L 耗尽判死）。
  - **复活**：`AGENT_REVIVED=10`（冻结窗内 L 回升到 `sustain` 复活）。
  - 终局 **存活 10 / 死亡 10**（Leader 目标「多数存活、少数死亡、有复活」达成），非 1/19、非 20/0。
- **错峰死亡**：`death_rounds = [60,66,66,69,70,70,70,70,70,70,73,…,76]`（非同时雪崩）。
- **「净值<0 且存活」**：`status ∉ {dead,terminated}` 口径下 `neg_networth_alive_rounds = [69,71,72,75,78,79,80,81]`（用户要「可有负资产」已达成；lifecycle 侧另报 78 agent·回合）。
- `SYSTEM_ERROR=0`、`ECONOMY_INVARIANT_VIOLATION=0`、守恒成立、`replay` 逐位一致（首跑==重放，两次重放哈希相等）。
- `pytest -q` = **227 passed**；`make lexicon-gate` = **通过**。

> 过程记录：曾试 `credit_unsecured_base_mu=5000`（A/A'）——未采用（Leader 采 lifecycle 基线 `unsecured=0`）；
> 该档下 `net_worth<0 且 alive` 亦可达；canonical（unsecured=0）下依旧可达（利息/代谢把 `cash` 压低至 `<debt` 仍 `≥trigger`），故无需未抵押额度。

## 2. 单元测试

- `tests/test_liquidity.py`（5）：债务/逾期派生、`credit_limit` 规则（无抵押→0、overdue/坏账冷却→0）、`can_borrow` 准入、`liquidity` 视图字段。
- `tests/test_econ_hooks.py`（21）：续命贷发放→次回合计息、**无抵押→借不到**、**坏账→`LOAN_DEFAULT`+`PENALTY_APPLIED`**、**负净值→`PENALTY_APPLIED`**、**未抵押授信→`net_worth<0 且 alive` 可达**、原子性/守恒/自成交/UBI 不计 I_eff/开关等。

## 3. 结论 / 冻结状态

- 与 lifecycle(T61) 统一接口已冻结：`L=cash` 判死、`can_borrow` 为放贷确切准入、`net_worth` 仅记录。
- canonical 档下确定性授信 + 续命贷同时产出「借债续命存活 / 借不到→死 / 复活」三类路径与错峰死亡，
  并有「净值<0 且存活」实证；不做补贴型续命贷，会计诚实（`cash↑ debt↑`）。
- `credit_unsecured_base_mu` / `negative_worth_penalty_bp` / `min_collateral_mu` 作为可调键保留
  （canonical 取 `0 / 100 / 0`）；engine 侧冻结，后续如需消融/放量再调 config。
