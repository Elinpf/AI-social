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


def test_real_exchange_settled_end_to_end():
    """真成交：OFFER_ACCEPTED(kind=sale) → EXCHANGE_SETTLED，双边 inventory/cash 移动 + 守恒 + replay parity。"""
    from engine import production as P
    from engine.constants import PHASE_COMMUNICATE
    from engine.hooks.exchange import apply_exchange
    from life.ports import INTENT_ECON_OFFER, Intent
    from orchestration.integration import build_world

    w = build_world(seed=7, n=3); eng = w["engine"]; ad = w["adapter"]
    pids = sorted(w["personas"]); A, B = pids[0], pids[1]
    eng.state.round = 1; eng.ctx = eng.ctx.at(1, 0); eng.arbiter.discard()

    # 卖方 A 备货（PRODUCE，qty 单位=milli），并发定向出售要约 A→[B]
    eng.emit_specs([spec(1, PHASE_COMMUNICATE, A, "PRODUCE",
                         {"agent_id": A, "good_id": "food", "qty": 10 * P.MILLI})])
    assert ad.submit_intent(A, Intent(INTENT_ECON_OFFER, A,
                                      {"act": "create", "kind": "sale", "to": [B],
                                       "terms": {"good_id": "food", "price_mu": 5, "qty": 2}})).ok
    eng.state, _ = eng.arbiter.commit(eng.state)
    oid = next(r["payload"]["offer_id"] for r in eng.ledger.records if r["type"] == "OFFER_CREATED")
    # B 应约
    assert ad.submit_intent(B, Intent(INTENT_ECON_OFFER, B,
                                      {"act": "accept", "offer_id": oid,
                                       "terms": {"good_id": "food", "price_mu": 5, "qty": 2}})).ok
    eng.state, _ = eng.arbiter.commit(eng.state)

    inv_a0 = eng.state.inventory.get(A, {}).get("food", 0)
    inv_b0 = eng.state.inventory.get(B, {}).get("food", 0)
    cash_a0, cash_b0 = eng.state.cash.get(A, 0), eng.state.cash.get(B, 0)

    # 4.1 交换原语：(B) OFFER_ACCEPTED 单源结算
    specs = apply_exchange(eng.state, 1, eng.ctx)
    eng.state, _ = eng.arbiter.emit(eng.state, specs)
    eng.state, _ = eng.arbiter.commit(eng.state)

    assert any(r["type"] == "EXCHANGE_SETTLED" for r in eng.ledger.records)
    assert eng.state.inventory[A]["food"] == inv_a0 - 2 * P.MILLI
    assert eng.state.inventory[B].get("food", 0) == inv_b0 + 2 * P.MILLI
    assert eng.state.cash[A] - cash_a0 == 5 * 2   # 价来自 terms（5×2 mu）
    assert eng.state.cash[B] - cash_b0 == -(5 * 2)
    assert conservation.check_all(eng.state) == []
    assert state_hash(replay_records(eng.ledger.records)) == state_hash(eng.state)


def test_offer_created_visibility_by_to():
    """① 关键契约：OFFER_CREATED 定向（to 非空）-> private 仅名单可见；广播（to==[]）-> global。"""
    from life.ports import INTENT_ECON_OFFER, Intent
    from orchestration.integration import build_world

    w = build_world(seed=7, n=3); eng = w["engine"]; ad = w["adapter"]
    pids = sorted(w["personas"]); A, B, C = pids

    def vis_ids(aid):
        return {ev.payload.get("offer_id") for ev in ad.perceive(aid).visible_events
                if ev.type == "OFFER_CREATED"}

    eng.state.round = 1; eng.ctx = eng.ctx.at(1, 0); eng.arbiter.discard()
    assert ad.submit_intent(A, Intent(INTENT_ECON_OFFER, A,
                                      {"act": "create", "kind": "sale", "to": [B],
                                       "terms": {"good_id": "food", "price_mu": 5, "qty": 1}})).ok
    eng.state, _ = eng.arbiter.commit(eng.state)
    oid_d = next(r["payload"]["offer_id"] for r in eng.ledger.records if r["type"] == "OFFER_CREATED")
    # 定向：A/B 可见，C 不可见
    assert oid_d in vis_ids(A) and oid_d in vis_ids(B)
    assert oid_d not in vis_ids(C), "定向要约不得全局可见（制度性缺陷）"

    # 广播 to==[] -> global：全体可见
    eng.state.round = 2; eng.ctx = eng.ctx.at(2, 0); eng.arbiter.discard()
    assert ad.submit_intent(A, Intent(INTENT_ECON_OFFER, A,
                                      {"act": "create", "kind": "sale", "to": [],
                                       "terms": {"good_id": "food", "price_mu": 5, "qty": 1}})).ok
    eng.state, _ = eng.arbiter.commit(eng.state)
    oid_b = next(r["payload"]["offer_id"] for r in eng.ledger.records
                 if r["type"] == "OFFER_CREATED" and r["round"] == 2)
    for aid in (A, B, C):
        assert oid_b in vis_ids(aid), f"广播要约应对 {aid} 可见"


def test_contracts_are_audit_only():
    st = initial_state(1); led = Ledger(); _seed(st, led)
    before = state_hash(st)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "SYSTEM", "CONTRACT_CREATED",
                         {"contract_id": "c1", "parties": ["A", "B"]}))
    _apply(st, led, spec(0, PHASE_ARBITRATE, "SYSTEM", "CONTRACT_FULFILLED",
                         {"contract_id": "c1"}))
    assert state_hash(st) == before  # 契约事件不改世界状态（审计）
