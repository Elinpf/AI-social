"""守恒校验骨架测试。"""

from engine import conservation
from engine.arbiter import Arbiter
from engine.constants import PHASE_ARBITRATE
from engine.events import spec
from engine.ledger import Ledger
from engine.state import initial_state, money_total, state_hash
from engine.replay import apply_event


def _apply(state, ledger, ev):
    rec = ledger.append_spec(ev)
    return apply_event(state, rec)


def test_genesis_conserves_money():
    from engine.runner import run
    res = run(seed=1, rounds=3)
    st = res["final_state"]
    assert money_total(st) == st.money_minted_total - st.money_burned_total
    assert conservation.check_conservation(st) == []


def test_transfer_metabolism_conserve():
    st = initial_state(1)
    led = Ledger()
    _apply(st, led, spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": "A", "birth_round": 0}))
    _apply(st, led, spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": "B", "birth_round": 0}))
    _apply(st, led, spec(0, 0, "SYSTEM", "INIT_ENDOW", {"agent_id": "A", "amount": 100}))
    _apply(st, led, spec(0, 0, "SYSTEM", "INIT_ENDOW", {"agent_id": "B", "amount": 100}))
    _apply(st, led, spec(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": 200, "reason": "genesis"}))
    assert conservation.check_conservation(st) == []
    # 转账（含手续费销毁）
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "TRANSFER",
                          {"tx_id": "t1", "from": "A", "to": "B", "amount": 30, "fee": 5}))
    assert st.cash["A"] == 100 - 30 - 5
    assert st.cash["B"] == 100 + 30
    assert conservation.check_conservation(st) == []


def test_violation_detected():
    st = initial_state(1)
    st.ensure_agent("A")
    st.cash["A"] = 50  # 无对应 minted
    viols = conservation.check_conservation(st)
    assert len(viols) == 1
    assert viols[0]["code"] == "ECONOMY_INVARIANT_VIOLATION"


def test_unknown_event_type_raises():
    import pytest
    st = initial_state(1)
    with pytest.raises(KeyError):
        apply_event(st, {"seq": 0, "round": 0, "phase": 0, "actor": "S",
                         "type": "NOT_A_TYPE", "payload": {}, "hash": "x", "prev_hash": "y"})
