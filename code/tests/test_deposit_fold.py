"""DEPOSIT/WITHDRAW 折叠（内核 replay）与 obs 口径一致（08 §1.2 L / T14-C3）。"""

from engine import conservation
from engine.constants import PHASE_ARBITRATE
from engine.events import spec
from engine.ledger import Ledger
from engine.replay import apply_event
from engine.state import initial_state


def _apply(state, ledger, ev):
    return apply_event(state, ledger.append_spec(ev))


def _seed_agent(state, ledger):
    _apply(state, ledger, spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": "A", "birth_round": 0}))
    _apply(state, ledger, spec(0, 0, "SYSTEM", "INIT_ENDOW", {"agent_id": "A", "amount": 100}))
    _apply(state, ledger, spec(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": 100, "reason": "genesis"}))


def test_deposit_moves_cash_to_deposits():
    st = initial_state(1)
    led = Ledger()
    _seed_agent(st, led)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "DEPOSIT", {"agent_id": "A", "amount": 30}))
    assert st.cash["A"] == 70
    assert st.deposits["A"] == 30
    assert conservation.check_conservation(st) == []  # 科目转移不改总量


def test_withdraw_moves_deposits_to_cash():
    st = initial_state(1)
    led = Ledger()
    _seed_agent(st, led)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "DEPOSIT", {"agent_id": "A", "amount": 30}))
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "WITHDRAW", {"agent_id": "A", "amount": 10}))
    assert st.cash["A"] == 80
    assert st.deposits["A"] == 20
    assert conservation.check_conservation(st) == []


def test_deposit_withdraw_not_noop():
    # 回归：二者不得再是 no-op（此前在 _NOOP_TYPES 里）
    st = initial_state(1)
    led = Ledger()
    _seed_agent(st, led)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "DEPOSIT", {"agent_id": "A", "amount": 40}))
    assert st.deposits.get("A", 0) == 40
