"""流动性 / 确定性授信 统一接口（T61×T62）。

**职责**：向生命周期与经济层暴露**同一套** per-agent 流动性视图与确定性授信额度：
  `cash / deposits / debt / credit_limit / overdue`（`net_worth` 仅记录，不作判死主判据）。

**约定**（Leader 定，T61）：
  - 判死以**流动性** `L = cash` 为基准；`net_worth = cash + deposits − debt` 仅记录/惩罚触发。
  - 本模块**纯函数、无状态、无 I/O、不调 LLM**：`credit_limit/overdue/debt` 均由
    `state.cash/deposits/loans` 与 `state.event_index` 确定性派生 → 首跑与重放恒一致，
    无需新增 state 字段、无需新增事件类型。
  - 金额一律整数 `mu`；参数经 `resolve_params(ctx)` 单一来源解析（policy 默认 ← policy.economy ← config.economy）。
"""

from __future__ import annotations

from functools import lru_cache

# 计入「有效净流入 I_eff」的收入型 tx（与 obs/antifraud.INCOME_TX_TYPES 一致）
_INCOME_TX_TYPES = ("transfer", "trade")
_EXCLUDE_FLAGS = frozenset({"wash", "cycle", "self", "mule"})

# 内置默认（policy.json 缺失时兜底；否则以 policy 默认值为准）
_BUILTIN = {
    # 税 / UBI / 手续费
    "income_tax_bp": 1000, "wealth_tax_bp": 200, "ubi_mu": 0, "fee_market_bp": 100,
    # 借贷
    "loan_rate_bp": 500, "r_overdue_bp": 500, "k_pen_bp": 5000,
    "loan_ltv_bp": 6000, "loan_max_debt_mu": 10000, "loan_term_rounds": 12,
    "n_overdue": 3, "w_refi": 3, "deposit_rate_bp": 0,
    "negative_worth_penalty_bp": 0,  # 负净值惩罚（bp of |net_worth|/回合；>0 → PENALTY_APPLIED，P1 升级）
    # 反作弊窗口
    "w_wash": 4, "rho_wash_bp": 8000, "l_cycle": 5, "l_hop": 3,
    # 稀缺度（08 §1.2-N / T60）
    "w_scarce": 3, "market_scarce_supply": 8,
    # 流动性 / 授信（T61×T62 共享）
    "liquid_trigger_mu": 200,      # L 低于此 = 不足支付下一回合生存开销（与 T61 判死阈值对齐）
    "liquid_sustain_mu": 600,      # 续命目标：把 L 抬到该值视为可持续（=3×trigger，T61 定）
    "subsistence_mu": 0,           # 除代谢外的最低开销（预留）
    "income_credit_bp": 20000,     # 授信的收入项系数（2× 近窗正 I_eff）
    "w_income_rounds": 12,         # 收入窗
    "w_cool_rounds": 6,            # 坏账后信用冷却（期内存量授信=0）
    "credit_ltv_bp": 6000,         # 抵押项 LTV（默认与 loan_ltv_bp 同）
    "credit_unsecured_base_mu": 0, # 未完全抵押的授信基额（>0 使 debt 可>cash、净值可负；硬受 D_max 约束）
    "min_collateral_mu": 0,        # 最低抵押门槛（默认关；>0 时 cash+deposits 低于此 → 授信=0）
    "mu_floor": 0,                 # 货币总量硬地板（世界级不变量 M ≥ mu_floor）
}


@lru_cache(maxsize=1)
def _policy_defaults() -> dict:
    """config/policy.json 顶层 {name: default}（只读一次，确定性）。失败则空。"""
    try:
        from engine.version import policy_defaults
        return {str(k).lower(): v for k, v in policy_defaults().items()}
    except Exception:
        return {}


def resolve_params(ctx) -> dict:
    """合并：内置默认 < policy 顶层默认 < policy.economy（扁平）< config.economy。键统一小写。"""
    p = dict(_BUILTIN)
    p.update(_policy_defaults())
    cfg = getattr(ctx, "config", None)
    if isinstance(cfg, dict):
        pol = cfg.get("policy")
        if isinstance(pol, dict):
            sec = pol.get("economy")
            if isinstance(sec, dict):
                for k, v in sec.items():
                    if not str(k).startswith("_"):
                        p[str(k).lower()] = v
        econ = cfg.get("economy")
        if isinstance(econ, dict):
            for k, v in econ.items():
                if not str(k).startswith("_"):
                    p[str(k).lower()] = v
    # 容忍内核/topology 侧的裸值 `policy.money_floor_mu`（kernel-dev）→ 归一到 mu_floor
    try:
        mf = (cfg or {}).get("policy", {}).get("money_floor_mu") if isinstance(cfg, dict) else None
        if mf is not None:
            p["mu_floor"] = int(mf)
    except Exception:
        pass
    return p


def bp(value, base) -> int:
    """base * value/10000 向下取整（整数）。"""
    try:
        return (int(base) * int(value)) // 10000
    except Exception:
        return 0


# ------------------------------------------------------------------ 债务 / 逾期
def debt_of(state, aid) -> int:
    """未偿债务本金合计（status ∈ {active, overdue}）。"""
    total = 0
    for loan in state.loans.values():
        if loan.get("borrower") == aid and loan.get("status") in ("active", "overdue"):
            total += int(loan.get("outstanding", 0))
    return total


def overdue_of(state, aid, round_no) -> bool:
    """存在任一未偿且 `due_round < round_no` 的贷款（派生，不落 state）。"""
    for loan in state.loans.values():
        if loan.get("borrower") != aid or loan.get("status") not in ("active", "overdue"):
            continue
        due = int(loan.get("due_round", 0))
        if due and int(round_no) > due:
            return True
    return False


def recent_default_of(state, aid, round_no, params) -> bool:
    """近 `w_cool_rounds` 回合内该 Agent 是否发生坏账（LOAN_DEFAULT）→ 信用降级。"""
    cool = int(params.get("w_cool_rounds", 6))
    idx = getattr(state, "event_index", {}) or {}
    for r in idx.values():
        if r.get("type") != "LOAN_DEFAULT":
            continue
        p = r.get("payload") or {}
        if p.get("borrower") == aid and int(round_no) - int(r.get("round", round_no)) <= cool:
            return True
    return False


# ------------------------------------------------------------------ 收入 / 净值
def recent_income(state, aid, round_no, params) -> int:
    """近 `w_income_rounds` 回合的**正**有效净流入合计（口径同 obs/antifraud.ie_eff）。"""
    window = int(params.get("w_income_rounds", 12))
    idx = getattr(state, "event_index", {}) or {}
    per_round = {}
    for r in idx.values():
        rd = int(r.get("round", -1))
        if rd > int(round_no) or rd < int(round_no) - window:
            continue
        t = r.get("type")
        p = r.get("payload") or {}
        if t == "TRANSFER":
            frm, to, tt = p.get("from"), p.get("to"), p.get("tx_type", "transfer")
        elif t == "MARKET_TRADE":
            frm, to, tt = p.get("buyer"), p.get("seller"), p.get("tx_type", "trade")
        else:
            continue
        if tt not in _INCOME_TX_TYPES:
            continue
        flags = set(p.get("flags") or [])
        if frm == to or (flags & _EXCLUDE_FLAGS):
            continue
        amount = int(p.get("amount", 0))
        d = per_round.setdefault(rd, 0)
        if to == aid:
            d += amount
        if frm == aid:
            d -= amount
        per_round[rd] = d
    return sum(max(0, v) for v in per_round.values())


def net_worth_of(state, aid) -> int:
    """净值（记录/惩罚触发用）：cash + deposits − debt。"""
    try:
        return int(state.net_worth(aid))
    except Exception:
        return int(state.cash.get(aid, 0)) + int(state.deposits.get(aid, 0)) - debt_of(state, aid)


# ------------------------------------------------------------------ 授信额度
def credit_limit(state, aid, round_no, params) -> int:
    """确定性授信上限（可借额度）。

    `limit = min(D_max − debt, ⌊LTV·(cash⁺+deposits)⌋ + unsecured_base + ⌊k_income·max(0,近窗正I_eff)⌋)`
    - **无抵押且无收入且无 unsecured → 0**；`debt ≥ D_max` → 0（硬上限）；
    - `overdue` 或近 `w_cool` 回合内有坏账 → 0（**信用降级**）；
    - `unsecured_base`（`credit_unsecured_base_mu`）为**未完全抵押成分**：使 `debt` 可 > `cash`，
      从而「`net_worth<0` 且 `L≥trigger` 仍 alive」可达（用户要「可有负资产」）；仍受 `D_max` 硬约束。
    - 非真 Agent / dead / terminated → 0。
    """
    a = state.agents.get(aid)
    if a is None or aid in ("MARKET", "BANK", "WORLD", "SYSTEM"):
        return 0
    if a.get("status") in ("dead", "terminated"):
        return 0
    d_max = int(params.get("loan_max_debt_mu", 0))
    if d_max <= 0:
        return 0
    debt = debt_of(state, aid)
    headroom = d_max - debt
    if headroom <= 0:
        return 0
    if overdue_of(state, aid, round_no) or recent_default_of(state, aid, round_no, params):
        return 0
    ltv = int(params.get("credit_ltv_bp", params.get("loan_ltv_bp", 0)))
    cash = max(0, int(state.cash.get(aid, 0)))
    deposits = max(0, int(state.deposits.get(aid, 0)))
    if cash + deposits < int(params.get("min_collateral_mu", 0)):
        return 0                                       # 无抵押 → 借不到
    asset_cap = bp(ltv, cash + deposits)
    unsecured = int(params.get("credit_unsecured_base_mu", 0))  # 未完全抵押成分（仍受 D_max 硬上限）
    income_cap = bp(int(params.get("income_credit_bp", 0)),
                    max(0, recent_income(state, aid, round_no, params)))
    limit = asset_cap + unsecured + income_cap
    return max(0, min(limit, headroom))


def can_borrow(state, aid, round_no, params) -> bool:
    """能否获得**新增流动性**（= 放贷的**确切**准入，lifecycle 直接消费）。

    `L = cash < liquid_trigger_mu` 且 `无存量未偿` 且 `无 overdue` 且 `credit_limit > 0`。
    说明：此定义含「已低于生存阈值」；lifecycle 判死 = `L<trigger 且 not can_borrow`。
    放贷落地后 `debt>0` → `can_borrow` 变 False（下一回合须视作「已用掉授信」）。
    """
    cash = int(state.cash.get(aid, 0))
    if cash >= int(params.get("liquid_trigger_mu", 0)):
        return False
    if debt_of(state, aid) > 0:
        return False
    if overdue_of(state, aid, round_no):
        return False
    return credit_limit(state, aid, round_no, params) > 0


def liquidity(state, aid, round_no, params) -> dict:
    """生命周期/经济层共用的 per-agent 流动性视图。`L = cash`。"""
    cash = int(state.cash.get(aid, 0))
    deposits = int(state.deposits.get(aid, 0))
    debt = debt_of(state, aid)
    return {
        "agent_id": aid,
        "cash": cash,
        "L": cash,                       # 判死基准：可动用流动性
        "deposits": deposits,
        "debt": debt,
        "credit_limit": credit_limit(state, aid, round_no, params),
        "can_borrow": can_borrow(state, aid, round_no, params),
        "overdue": overdue_of(state, aid, round_no),
        "net_worth": net_worth_of(state, aid),  # 仅记录
    }


__all__ = [
    "resolve_params", "bp", "debt_of", "overdue_of", "recent_default_of",
    "recent_income", "net_worth_of", "credit_limit", "can_borrow", "liquidity",
]
