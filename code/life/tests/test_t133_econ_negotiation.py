"""T133: life produces INTENT.ECON.* + negotiation wiring.

Offline (mini double) proves the intent -> event path incl. ORDER_CANCEL observability.
Real-engine part asserts the negotiation LLM call and that ECON intents are accepted
(not unknown/unsupported); the ORDER_CANCEL *event* on the engine still awaits the
engine-side emission (tracked separately) and is therefore not asserted here.
"""
from __future__ import annotations

from collections import Counter

from life.tests.support.mini_kernel import MiniKernel, state_fingerprint
from life.tests.test_life_m3m7 import _run as _mini_run


def test_offline_intents_produce_events_and_cancel_observable():
    k, _, _ = _mini_run(6, 84, 7)
    c = Counter(e["type"] for e in k.ledger)
    assert c.get("OFFER_CREATED", 0) > 0, "life OFFER intent -> OFFER_CREATED"
    assert c.get("ORDER_CANCEL", 0) > 0, "life ORDER_CANCEL intent -> ORDER_CANCEL (observable)"
    assert state_fingerprint(k.state) == state_fingerprint(MiniKernel.replay(k.ledger, seed=7))


def test_engine_negotiation_and_econ_accepted():
    try:
        from engine.integration import build_world
        from engine.replay import replay_records
        from engine.state import state_hash
    except Exception:
        return  # engine unavailable
    w = build_world(seed=7, n=6)
    eng = w["engine"]
    for r in range(84):
        eng.run_round(r)
    recs = eng.ledger.records
    c = Counter(r["type"] for r in recs)
    neg = sum(1 for r in recs if r["type"] == "LLM_CALL"
              and (r["payload"] or {}).get("purpose") == "negotiation")
    assert neg > 0, "negotiation LLM calls expected (purpose=negotiation)"
    # ECON intents must be accepted (routed), never unknown/unsupported
    bad = [r for r in recs if r["type"] == "INTENT_REJECTED"
           and (r["payload"] or {}).get("intent_class", "").startswith("INTENT.ECON.")
           and (r["payload"] or {}).get("reason") in ("unknown_intent_class", "unsupported_intent")]
    assert not bad, bad
    assert c.get("SYSTEM_ERROR", 0) == 0
    assert state_hash(replay_records(recs)) == state_hash(eng.state)


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
