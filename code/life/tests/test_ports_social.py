"""T100 contract test: `life.ports` declares `INTENT.SOCIAL` (no behavior change).

Run: cd code && python -m life.tests.test_ports_social  (or via pytest)
"""
from __future__ import annotations

from life import ports as P


def test_intent_social_declared():
    assert P.INTENT_SOCIAL == "INTENT.SOCIAL"
    assert P.INTENT_SOCIAL in P.ALL_INTENT_CLASSES
    assert set(P.SOCIAL_SCOPES) == {"private", "place_group", "global"}


def test_adapter_accepts_intent_social_not_unknown():
    """The engine adapter must no longer reject INTENT.SOCIAL as unknown_intent_class."""
    try:
        from engine.integration import build_world
    except Exception:
        return  # engine not available in this context
    from life.ports import Intent
    w = build_world(seed=7, n=3)
    adapter = w["adapter"]
    pid = sorted(w["personas"])[0]
    res = adapter.submit_intent(pid, Intent(P.INTENT_SOCIAL, pid, {
        "scope": "private", "to": sorted(w["personas"])[1], "body": "hi",
        "refs": [], "tag_hints": []}))
    # accept (ok) or a *specific* validation reason, but NEVER unknown_intent_class
    assert res.reason != "unknown_intent_class", res


def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {t.__name__}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
