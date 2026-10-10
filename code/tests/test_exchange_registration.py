"""T131 内核侧：交易/契约事件注册 + EXCHANGE_SETTLED 零和折叠 + fail-loud。"""

import pytest

import engine.hooks as H
from engine import conservation
from engine.constants import PHASE_ARBITRATE
from engine.events import EVENT_TYPES, spec
from engine.ledger import Ledger
from engine.replay import apply_event, replay_records
from engine.state import initial_state, state_hash


def _apply(state, led, ev):
    return apply_event(state, led.append_spec(ev))


def _seed(state, led):
    _apply(state, led, spec(0, 0, "SYSTEM", "WORLD_INIT", {"seed": 1}))
    for a in ("A", "B"):
        _apply(state, led, spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": a, "birth_round": 0}))
    _apply(state, led, spec(0, 0, "SYSTEM", "INIT_ENDOW", {"agent_id": "A", "amount": 100}))
    _apply(state, led, spec(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": 100, "reason": "g"}))


def test_t131_events_registered():
    for t in ("EXCHANGE_SETTLED", "CONTRACT_CREATED", "CONTRACT_FULFILLED",
              "CONTRACT_VIOLATED", "CONTRACT_EXPIRED"):
        assert t in EVENT_TYPES


def test_exchange_settled_zero_sum_fold():
    st = initial_state(1); led = Ledger(); _seed(st, led)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "PRODUCE",
                         {"agent_id": "A", "good_id": "food", "qty": 10}))
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "EXCHANGE_SETTLED", {
        "parties": ["A", "B"],
        "legs": {"goods": [{"from": "A", "to": "B", "good_id": "food", "qty": 4}],
                 "money": [{"from": "A", "to": "B", "mu": 30}]}}))
    assert st.inventory["A"]["food"] == 6 and st.inventory["B"]["food"] == 4
    assert st.cash["A"] == 70 and st.cash["B"] == 30
    # 零和：货币守恒 + 商品守恒均成立；minted/burned 不变
    assert st.money_minted_total == 100 and st.money_burned_total == 0
    assert conservation.check_all(st) == []
    assert state_hash(replay_records(led.records)) == state_hash(st)


def test_exchange_fail_loud_three_states(monkeypatch):
    monkeypatch.setattr(H, "EXCHANGE_HOOK_AVAILABLE", False)
    monkeypatch.setattr(H, "EXCHANGE_HOOK_ERROR", "simulated")
    cfg_both = {"policy": {"economy": {"enabled": True}, "exchange": {"enabled": True}}}
    with pytest.raises(RuntimeError):
        H.assert_exchange_available(cfg_both)
    # exchange off -> 不 raise
    H.assert_exchange_available({"policy": {"economy": {"enabled": True},
                                            "exchange": {"enabled": False}}})
    # economy off -> 允许 no-op
    H.assert_exchange_available({"policy": {"economy": {"enabled": False}}})


def test_contracts_are_audit_only():
    st = initial_state(1); led = Ledger(); _seed(st, led)
    before = state_hash(st)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "SYSTEM", "CONTRACT_CREATED",
                         {"contract_id": "c1", "parties": ["A", "B"]}))
    _apply(st, led, spec(0, PHASE_ARBITRATE, "SYSTEM", "CONTRACT_FULFILLED",
                         {"contract_id": "c1"}))
    assert state_hash(st) == before  # 契约事件不改世界状态（审计）
