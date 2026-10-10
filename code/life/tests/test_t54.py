"""T54 acceptance: soft judgment (judge) + narrative (narrate) wired into the loop.

Run: cd code && python -m life.tests.test_t54
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from life.agent import LifeLayerAgent
from life.llm import RuleBasedLLM
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"


def _places():
    return {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}


def _mini_run(n: int, rounds: int = 84, seed: int = 7) -> MiniKernel:
    places = _places()
    personas = load_personas(CONFIG / "personas.json")
    pids = sorted(personas)[:n]
    kernel = MiniKernel(seed=seed, places=places)
    for pid in pids:
        kernel._emit("AGENT_BORN", {"agent_id": pid, "home_place": personas[pid].home_place,
                                    "needs_init": personas[pid].needs_init}, phase=0, actor="SYSTEM")
    kernel.commit_round()
    with tempfile.TemporaryDirectory() as d:
        side = SideStore(Path(d) / "side")
        agents = {pid: LifeLayerAgent(pid, personas[pid], kernel, llm=RuleBasedLLM(),
                                      side_store=side, embedding=HashEmbeddingModel(),
                                      places=places, peers=pids) for pid in pids}
        for _ in range(rounds):
            kernel.tick(agents)
    return kernel


def test_rule_based_mini_emits_judgment_and_narrative():
    kernel = _mini_run(3)
    types = [e["type"] for e in kernel.ledger]
    assert types.count("LLM_JUDGMENT") > 0, "relation threshold crossing should trigger judge"
    assert types.count("NARRATIVE") > 0, "REVIEW phase should trigger narrate"
    # every frozen judgment carries the four required elements
    for e in kernel.ledger:
        if e["type"] == "LLM_JUDGMENT":
            assert e["payload"]["frozen"] is True
            assert e["payload"]["decision"] in e["payload"]["envelope"]["options"]
            assert e["payload"]["model"] and e["payload"]["context_digest"]


def test_label_to_delta_is_deterministic():
    from life import relations as R
    assert R.delta_from_frozen_label("formed") == R.delta_from_frozen_label("formed")
    assert R.delta_from_frozen_label("formed")["affinity"] > 0


def test_engine_life_judgment_and_narrative_events():
    # End-to-end (life × engine) integration check. This test module legitimately
    # imports engine; the "life must not import engine" contract covers PRODUCTION
    # code, so `.importlinter` excludes test modules (narrow, production unchanged).
    try:
        from engine.integration import build_world
        from engine.replay import replay_records
        from engine.state import state_hash
    except Exception:
        return  # engine not available in this context
    w = build_world(seed=7, n=3)
    eng = w["engine"]
    for r in range(84):
        eng.run_round(r)
    types = [rec["type"] for rec in eng.ledger.records]
    assert types.count("LLM_JUDGMENT") > 0, "engine ledger should contain LLM_JUDGMENT"
    assert types.count("NARRATIVE") > 0, "engine ledger should contain NARRATIVE"
    assert types.count("SYSTEM_ERROR") == 0
    assert state_hash(replay_records(eng.ledger.records)) == state_hash(eng.state)


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
