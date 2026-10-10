"""Offline demo: run a single agent in an (almost) empty town for N rounds.

    cd code && python -m life.run_demo [rounds] [seed]

Prints a event census + a peek at the ledger, to eyeball that the life layer runs
end-to-end with zero network / zero LLM dependency.
"""
from __future__ import annotations

import sys
import tempfile
from collections import Counter
from pathlib import Path

from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel, state_fingerprint

CODE_DIR = Path(__file__).resolve().parents[1]
CONFIG = CODE_DIR / "config"


def build(seed: int, tmp: Path):
    import json
    places = {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}
    personas = load_personas(CONFIG / "personas.json")
    kernel = MiniKernel(seed=seed, places=places)
    side = SideStore(tmp / "side")
    embed = HashEmbeddingModel()
    agents = {}
    for pid in sorted(personas):
        p = personas[pid]
        kernel._emit("AGENT_BORN", {"agent_id": pid, "home_place": p.home_place,
                                    "needs_init": p.needs_init}, phase=0, actor="SYSTEM")
    for pid in sorted(personas):
        agents[pid] = LifeLayerAgent(pid, personas[pid], kernel, side_store=side,
                                     embedding=embed, places=places)
    return kernel, agents


def main() -> None:
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    with tempfile.TemporaryDirectory() as d:
        kernel, agents = build(seed, Path(d))
        for _ in range(rounds):
            kernel.tick(agents)
        census = Counter(e["type"] for e in kernel.ledger)
        print(f"seed={seed} rounds={rounds} events={len(kernel.ledger)} "
              f"embedded_model={HashEmbeddingModel.version}")
        for t, n in sorted(census.items()):
            print(f"  {t:<24} {n}")
        print("--- sample ledger ---")
        for e in kernel.ledger[:8]:
            print(f"  #{e['seq']:<4} r{e['round']:<3} ph{e['phase']:<3} {e['type']:<20} "
                  f"{e['actor']:<6} {e['payload']}")
        # replay parity
        fp_run = state_fingerprint(kernel.state)
        replayed = MiniKernel.replay(kernel.ledger, seed=seed)
        fp_replay = state_fingerprint(replayed)
        print("replay parity:", "OK" if fp_run == fp_replay else "MISMATCH")


if __name__ == "__main__":
    main()
