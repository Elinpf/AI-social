"""T62：流动性 / 确定性授信 统一接口（engine/liquidity.py）测试。

覆盖：债务/逾期派生、credit_limit 规则（无抵押→0、overdue/坏账→0）、can_borrow 准入、
liquidity 视图字段（cash/deposits/debt/credit_limit/overdue/net_worth）。
"""

from __future__ import annotations

from engine import liquidity as liq
from engine.events import spec
from engine.ledger import Ledger
from engine.replay import apply_event
from engine.state import initial_state


def _st(agents=("A", "B"), endow=10000, seed=1):
    st = initial_state(seed)
    led = Ledger()
    total = 0

    def ap(ev):
        rec = led.append_spec(ev)
        apply_event(st, rec)
        return rec

    for a in agents:
        ap(spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": a, "birth_round": 0}))
        ap(spec(0, 0, "SYSTEM", "INIT_ENDOW", {"agent_id": a, "amount": endow}))
        total += endow
    ap(spec(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": total, "reason": "genesis"}))
    return st, led, ap


_P = {"loan_max_debt_mu": 10000, "credit_ltv_bp": 6000, "loan_ltv_bp": 6000,
      "income_credit_bp": 20000, "w_income_rounds": 12, "w_cool_rounds": 6,
      "liquid_trigger_mu": 200, "liquid_sustain_mu": 600}


def test_debt_and_overdue_derived():
    st, led, ap = _st()
    ap(spec(0, 0, "SYSTEM", "LOAN_ISSUED", {
        "loan_id": "L1", "lender": None, "borrower": "A", "principal": 1000,
        "outstanding": 1000, "rate_bp": 500, "due_round": 5}))
    assert liq.debt_of(st, "A") == 1000
    assert liq.overdue_of(st, "A", 4) is False
    assert liq.overdue_of(st, "A", 6) is True
    assert liq.debt_of(st, "B") == 0


def test_credit_limit_rules():
    st, led, ap = _st()
    # 有抵押（现金 10000）→ 额度 = LTV 0.6 × 10000 = 6000，且 ≤ D_max 10000
    assert liq.credit_limit(st, "A", 1, _P) == 6000
    # 无抵押无收入 → 0（另一账户掏空）
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "B", "amount": 10000}))
    assert liq.credit_limit(st, "B", 1, _P) == 0


def test_credit_limit_zero_on_overdue_and_recent_default():
    st, led, ap = _st()
    ap(spec(0, 0, "SYSTEM", "LOAN_ISSUED", {
        "loan_id": "L1", "lender": None, "borrower": "A", "principal": 1000,
        "outstanding": 1000, "rate_bp": 500, "due_round": 2}))
    assert liq.credit_limit(st, "A", 3, _P) == 0        # overdue → 0
    # 坏账后冷却 → 0
    st2, led2, ap2 = _st()
    ap2(spec(0, 0, "SYSTEM", "LOAN_DEFAULT", {"loan_id": "L2", "borrower": "A",
                                              "outstanding": 500}))
    assert liq.credit_limit(st2, "A", 3, _P) == 0
    assert liq.recent_default_of(st2, "A", 3, _P) is True


def test_can_borrow_requires_low_liquidity_and_credit():
    st, led, ap = _st()
    # L 高（10000）→ 不需借，can_borrow=False
    assert liq.can_borrow(st, "A", 1, _P) is False
    # L 低于 trigger 且有抵押 → True
    ap(spec(0, 0, "SYSTEM", "DEPOSIT", {"agent_id": "A", "amount": 4000}))
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "A", "amount": 5900}))  # cash 100
    assert st.cash["A"] == 100 and st.deposits["A"] == 4000
    assert liq.credit_limit(st, "A", 1, _P) > 0
    assert liq.can_borrow(st, "A", 1, _P) is True
    # 已有存量未偿 → False
    ap(spec(0, 0, "SYSTEM", "LOAN_ISSUED", {
        "loan_id": "L9", "lender": None, "borrower": "A", "principal": 10,
        "outstanding": 10, "rate_bp": 500, "due_round": 100}))
    assert liq.can_borrow(st, "A", 1, _P) is False


def test_liquidity_view_fields():
    st, led, ap = _st()
    v = liq.liquidity(st, "A", 1, _P)
    assert set(v) >= {"cash", "L", "deposits", "debt", "credit_limit",
                      "can_borrow", "overdue", "net_worth"}
    assert v["L"] == v["cash"] == 10000
    assert v["net_worth"] == 10000
    assert v["debt"] == 0 and v["overdue"] is False
