"""T115: `policy.social.enabled` one-stop switch (integration via real engine).

on (default)  -> social voice present (MSG_* > 0, dialogue LLM calls > 0)
off           -> whole channel short-circuited at generation side: MSG_DM/PUBLIC/GROUP
                 + GROUP_CREATED == 0, dialogue calls == 0, and quota/dedup NOT reached;
                 replay bit-identical, SYSTEM_ERROR == 0.
"""
from __future__ import annotations

from collections import Counter

from life.policy import set_social_enabled


def _run(n: int = 6, rounds: int = 40, seed: int = 7):
    from engine.integration import build_world
    from engine.replay import replay_records
    from engine.state import state_hash
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    recs = eng.ledger.records
    return eng, recs, state_hash(replay_records(recs)) == state_hash(eng.state)


def _counts(recs):
    c = Counter(r["type"] for r in recs)
    dlg = sum(1 for r in recs if r["type"] == "LLM_CALL"
              and (r["payload"] or {}).get("purpose") == "dialogue")
    rj = Counter((r["payload"] or {}).get("reason") for r in recs if r["type"] == "INTENT_REJECTED")
    dr = Counter((r["payload"] or {}).get("reason") for r in recs if r["type"] == "DROPPED")
    return c, dlg, rj, dr


def test_social_default_on_present():
    set_social_enabled(True)
    try:
        _, recs, replay = _run()
    finally:
        set_social_enabled(None)
    c, dlg, _, _ = _counts(recs)
    assert c.get("MSG_DM", 0) > 0, "on: DM should exist"
    assert c.get("MSG_PUBLIC", 0) + c.get("MSG_GROUP", 0) > 0, "on: public/group should exist"
    assert dlg > 0, "on: dialogue LLM calls expected"
    assert replay is True


def test_social_off_fully_isolated():
    set_social_enabled(False)
    try:
        eng, recs, replay = _run()
    finally:
        set_social_enabled(None)
    c, dlg, rj, dr = _counts(recs)
    # channels + group creation all zero
    assert c.get("MSG_DM", 0) == 0
    assert c.get("MSG_PUBLIC", 0) == 0
    assert c.get("MSG_GROUP", 0) == 0
    assert c.get("GROUP_CREATED", 0) == 0
    # cost zero + channel logic not even reached
    assert dlg == 0, "off: no dialogue LLM calls"
    assert rj.get("quota_agent", 0) == 0
    assert dr.get("quota", 0) == 0 and dr.get("dup", 0) == 0
    # determinism / integrity intact
    assert c.get("SYSTEM_ERROR", 0) == 0
    assert replay is True


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
