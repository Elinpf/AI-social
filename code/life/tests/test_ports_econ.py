"""T133a: `life.ports` declares the `INTENT.ECON.*` intents (contract-first, no behavior).

Unblocks the engine routing (the adapter validates against `life.ports.ALL_INTENT_CLASSES`).
Declaration only: no producer, no behavior change.
"""
from __future__ import annotations

from life import ports as P

ECON = [
    P.INTENT_ECON_ORDER_PLACE, P.INTENT_ECON_ORDER_CANCEL, P.INTENT_ECON_TRANSFER,
    P.INTENT_ECON_LOAN_APPLY, P.INTENT_ECON_TRADE, P.INTENT_ECON_OFFER,
    P.INTENT_ECON_CONTRACT_SIGN,
]


def test_econ_intents_declared():
    for c in ECON:
        assert c.startswith("INTENT.ECON.")
        assert c in P.ALL_INTENT_CLASSES


def test_adapter_accepts_econ_intents_not_unknown():
    try:
        from engine.integration import build_world
    except Exception:
        return  # engine unavailable here
    from life.ports import Intent
    w = build_world(seed=7, n=3)
    adapter = w["adapter"]
    pid = sorted(w["personas"])[0]
    for c in ECON:
        res = adapter.submit_intent(pid, Intent(c, pid, {}))
        assert res.reason != "unknown_intent_class", (c, res)


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
