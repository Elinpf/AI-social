"""T133: life produces INTENT.ECON.OFFER (+ negotiation) — engine-based, no stub.

Order-book path (ORDER_PLACE/ORDER_CANCEL) is deferred to its own wave, so it is
NOT asserted here (no half-state: we never emit a cancel without a place).
"""
from __future__ import annotations

from collections import Counter


def _run(n: int = 6, rounds: int = 84, seed: int = 7):
    from engine.integration import build_world
    from engine.replay import replay_records
    from engine.state import state_hash
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    recs = eng.ledger.records
    return recs, state_hash(replay_records(recs)) == state_hash(eng.state)


def test_life_offer_and_negotiation():
    recs, replay = _run()
    c = Counter(r["type"] for r in recs)
    neg = sum(1 for r in recs if r["type"] == "LLM_CALL"
              and (r["payload"] or {}).get("purpose") == "negotiation")
    assert neg > 0, "negotiation LLM calls expected (purpose=negotiation)"
    # life's public-board OFFER_CREATED intent (to=[]) must surface as OFFER_CREATED{to=[]}
    broadcast = [r for r in recs if r["type"] == "OFFER_CREATED"
                 and not (r["payload"] or {}).get("to")]
    assert broadcast, "life INTENT.ECON.OFFER(create,to=[]) should produce OFFER_CREATED"
    # ECON intents must be routed (never unknown/unsupported)
    bad = [r for r in recs if r["type"] == "INTENT_REJECTED"
           and (r["payload"] or {}).get("intent_class", "").startswith("INTENT.ECON.")
           and (r["payload"] or {}).get("reason") in ("unknown_intent_class", "unsupported_intent")]
    assert not bad, bad
    assert c.get("SYSTEM_ERROR", 0) == 0
    assert replay is True


def test_no_cancel_without_place():
    """Guard the ruling: life must not emit a cancel without ever placing an order."""
    recs, _ = _run()
    c = Counter(r["type"] for r in recs)
    assert c.get("ORDER_PLACE", 0) == 0 and c.get("ORDER_CANCEL", 0) == 0, \
        "no order-book half-state (place/cancel deferred to its own wave)"


def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t(); print(f"PASS  {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1; print(f"FAIL  {t.__name__}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
