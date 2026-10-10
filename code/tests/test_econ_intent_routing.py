"""T133：INTENT.ECON.* 经 adapter 正确路由（不再 unsupported_intent），入 pending_intents。"""

from life.ports import (
    INTENT_ECON_CONTRACT_SIGN, INTENT_ECON_LOAN_APPLY, INTENT_ECON_OFFER,
    INTENT_ECON_ORDER_CANCEL, INTENT_ECON_ORDER_PLACE, INTENT_ECON_TRADE,
    INTENT_ECON_TRANSFER, Intent,
)
from orchestration.integration import build_world

_ECON = [INTENT_ECON_ORDER_PLACE, INTENT_ECON_ORDER_CANCEL, INTENT_ECON_TRANSFER,
         INTENT_ECON_LOAN_APPLY, INTENT_ECON_TRADE, INTENT_ECON_OFFER,
         INTENT_ECON_CONTRACT_SIGN]


def _open(eng, r):
    eng.state.round = r
    eng.ctx = eng.ctx.at(r, 0)
    eng.arbiter.discard()


def test_all_econ_intents_routed_not_unsupported():
    w = build_world(seed=7, n=3); ad = w["adapter"]; eng = w["engine"]
    pids = sorted(w["personas"]); a, b = pids[0], pids[1]
    _open(eng, 1)
    for cls in _ECON:
        res = ad.submit_intent(a, Intent(cls, a, {"counterparty": b}))
        assert res.ok is True, f"{cls}: {res.reason}"
        assert res.reason != "unsupported_intent"
    classes = {it["intent_class"] for it in eng.state.pending_intents}
    assert set(_ECON) <= classes


def test_trade_intent_queued_for_apply_exchange():
    w = build_world(seed=7, n=3); ad = w["adapter"]; eng = w["engine"]
    pids = sorted(w["personas"]); a, b = pids[0], pids[1]
    _open(eng, 1)
    res = ad.submit_intent(a, Intent(INTENT_ECON_TRADE, a, {
        "counterparty": b, "give": [{"mu": 10}], "take": [{"good": "food", "qty": 1}]}))
    assert res.ok
    queued = [it for it in eng.state.pending_intents if it["intent_class"] == INTENT_ECON_TRADE]
    assert queued and queued[0]["agent_id"] == a and queued[0]["payload"]["counterparty"] == b


def test_unknown_econ_class_still_rejected():
    w = build_world(seed=7, n=3); ad = w["adapter"]; eng = w["engine"]
    a = sorted(w["personas"])[0]
    _open(eng, 1)
    res = ad.submit_intent(a, Intent("INTENT.ECON.BOGUS", a, {}))
    assert res.ok is False and res.reason == "unknown_intent_class"


def test_econ_intent_end_to_end_observable_event():
    """端到端：life 产 ECON 意图 → engine 4.x 消费 → 可观测事件（非 unsupported）。"""
    w = build_world(seed=7, n=3); ad = w["adapter"]; eng = w["engine"]
    pids = sorted(w["personas"]); a, b = pids[0], pids[1]
    _open(eng, 1)
    assert ad.submit_intent(a, Intent(INTENT_ECON_ORDER_CANCEL, a, {"order_id": "o1"})).ok
    assert ad.submit_intent(a, Intent(INTENT_ECON_TRANSFER, a,
                                      {"to": b, "amount_mu": 100, "reason": "gift"})).ok
    eng.run_round(1)
    recs = eng.ledger.records
    # ORDER_CANCEL 有事件出口（撤单可观测）
    assert any(r["type"] == "DROPPED" and r["payload"].get("reason") == "no_order_book"
               for r in recs)
    # 4.x 确有消费（TRANSFER 或相应 DROPPED）
    assert any(r["round"] == 1 and r["type"] in ("TRANSFER", "DROPPED") for r in recs)
    # 不再有 unsupported_intent
    assert not any(r["type"] == "INTENT_REJECTED"
                   and r["payload"].get("reason") == "unsupported_intent" for r in recs)

