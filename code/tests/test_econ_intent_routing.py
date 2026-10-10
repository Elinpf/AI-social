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


def _commit(eng):
    eng.state, _ = eng.arbiter.commit(eng.state)


_ECON_QUEUED = [INTENT_ECON_ORDER_PLACE, INTENT_ECON_ORDER_CANCEL, INTENT_ECON_TRANSFER,
                INTENT_ECON_LOAN_APPLY, INTENT_ECON_TRADE]


def _payload_for(cls, other):
    if cls == INTENT_ECON_OFFER:
        return {"act": "create", "kind": "sale", "to": [other], "terms": {"price_mu": 7}}
    if cls == INTENT_ECON_CONTRACT_SIGN:
        return {"offer_id": "o1"}
    return {"counterparty": other}


def test_all_econ_intents_routed_not_unsupported():
    w = build_world(seed=7, n=3); ad = w["adapter"]; eng = w["engine"]
    pids = sorted(w["personas"]); a, b = pids[0], pids[1]
    _open(eng, 1)
    for cls in _ECON:
        res = ad.submit_intent(a, Intent(cls, a, _payload_for(cls, b)))
        assert res.ok is True, f"{cls}: {res.reason}"
        assert res.reason != "unsupported_intent"
    # 入队类（order/transfer/loan/trade）进 pending_intents
    classes = {it["intent_class"] for it in eng.state.pending_intents}
    assert set(_ECON_QUEUED) <= classes
    # 封装类（offer/contract_sign）直接产事件，不入队
    assert INTENT_ECON_OFFER not in classes and INTENT_ECON_CONTRACT_SIGN not in classes


def test_offer_intent_encapsulated_to_events():
    w = build_world(seed=7, n=3); ad = w["adapter"]; eng = w["engine"]
    pids = sorted(w["personas"]); a, b = pids[0], pids[1]
    _open(eng, 1)
    assert ad.submit_intent(a, Intent(INTENT_ECON_OFFER, a,
                                      {"act": "create", "kind": "EMPLOYMENT", "to": [b],
                                       "terms": {"price_mu": 9}})).ok
    _commit(eng)
    oc = [r for r in eng.ledger.records if r["type"] == "OFFER_CREATED"]
    assert oc and oc[0]["phase"] == 2 and oc[0]["payload"]["from"] == a
    assert oc[0]["payload"]["terms"] == {"price_mu": 9}  # 价自 terms 原样
    # accept -> OFFER_ACCEPTED；CONTRACT_SIGN -> CONTRACT_CREATED
    _open(eng, 2)
    assert ad.submit_intent(b, Intent(INTENT_ECON_OFFER, b,
                                      {"act": "accept", "offer_id": oc[0]["payload"]["offer_id"],
                                       "terms": oc[0]["payload"]["terms"]})).ok
    assert ad.submit_intent(b, Intent(INTENT_ECON_CONTRACT_SIGN, b,
                                      {"offer_id": oc[0]["payload"]["offer_id"]})).ok
    _commit(eng)
    types = [r["type"] for r in eng.ledger.records]
    assert "OFFER_ACCEPTED" in types and "CONTRACT_CREATED" in types


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
    # 撤单可观测：ORDER_CANCEL 事件，或 econ 的 DROPPED{no_order_book}（该取舍由 Leader 裁）
    observed = (any(r["type"] == "ORDER_CANCEL" for r in recs)
                or any(r["type"] == "DROPPED"
                       and r["payload"].get("reason") == "no_order_book" for r in recs))
    assert observed, "撤单无任何可观测出口"
    # 不再有 unsupported_intent
    assert not any(r["type"] == "INTENT_REJECTED"
                   and r["payload"].get("reason") == "unsupported_intent" for r in recs)

