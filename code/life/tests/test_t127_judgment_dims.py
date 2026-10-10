"""T127: extra LLM_JUDGMENT dimensions (stance / respect / affection).

Lights up two cards without any fallback:
  * `rel-acceptance`  <- stance can flip (accept <-> reject for the same pair)
  * `diff-scoring`    <- respect/affection can diverge (背向) for the same pair
Frozen path only: RNG picks the branch, LLM fills the label, decision frozen in the
log (replay reads it back). No new non-determinism.
"""
from __future__ import annotations

from collections import Counter, defaultdict


def _run(weeks: int = 2, n: int = 6, seed: int = 7):
    from engine.integration import build_world
    from engine.replay import replay_records
    from engine.state import state_hash
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(weeks * 84):
        eng.run_round(r)
    recs = eng.ledger.records
    return recs, state_hash(replay_records(recs)) == state_hash(eng.state)


def _judgments(recs):
    return [r["payload"] for r in recs if r["type"] == "LLM_JUDGMENT"]


def test_new_dimensions_present_and_existing_intact():
    recs, replay = _run()
    dims = Counter(j["dimension"] for j in _judgments(recs))
    for d in ("stance", "respect", "affection"):
        assert dims.get(d, 0) > 0, f"dimension {d} should be produced"
    # existing dimensions not broken
    for d in ("weekly_focus", "rel_affinity", "rel_familiarity"):
        assert dims.get(d, 0) > 0, f"existing dimension {d} broken"
    # frozen four elements present
    for j in _judgments(recs):
        assert j.get("frozen") is True and j.get("model") and j.get("context_digest")
        assert j.get("decision") in (j.get("envelope") or {}).get("options", [])
    assert replay is True


def test_stance_can_flip():
    recs, _ = _run()
    seq = defaultdict(list)
    for j in _judgments(recs):
        if j["dimension"] == "stance":
            seq[tuple(sorted(j.get("parties") or []))].append(j["decision"])
    flips = [k for k, v in seq.items() if {"accept", "reject"} <= set(v)]
    assert flips, "at least one (agent,peer) should flip stance accept<->reject"


def test_respect_affection_can_diverge():
    recs, _ = _run()
    labels = defaultdict(dict)
    for j in _judgments(recs):
        if j["dimension"] in ("respect", "affection"):
            labels[tuple(sorted(j.get("parties") or []))][j["dimension"]] = j["decision"]
    divergent = [k for k, v in labels.items()
                 if v.get("respect") and v.get("affection") and v["respect"] != v["affection"]]
    assert divergent, "at least one pair should have respect/affection divergent (背向)"


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
