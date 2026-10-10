"""Acceptance tests for the life-layer skeleton (T31).

Run:  cd code && python -m life.tests.test_skeleton

Covers the three acceptance criteria:
  ① a single agent runs a full round in an empty world and emits legal events
  ② memory writes/retrievals go through the log and the run is replayable
  ③ there is no side channel that writes world state (GuardedKernel proves the
     agent only ever calls IF-1 perceive / IF-2 submit_intent)
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel, state_fingerprint

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"

MONEY_EVENTS = {  # the life layer must never mint/emit these (rule L-2/P7)
    "TRANSFER", "MARKET_TRADE", "TAX_LEVIED", "UBI_PAID", "METABOLISM",
    "PENALTY_APPLIED", "MONEY_MINTED", "MONEY_BURNED", "LOAN_ISSUED", "LOAN_REPAY",
}


class GuardedKernel:
    """Wrap a kernel but expose ONLY the port surface. Any other attribute access
    (e.g. touching `.state`, `.ledger`) raises — proving no side-channel writes.

    We deliberately do NOT inherit `KernelPort` here: a Protocol's method stubs are
    real functions returning None, which would shadow `__getattr__`.
    """

    ALLOWED = ("perceive", "submit_intent", "current_round", "derive_time")

    def __init__(self, inner) -> None:
        object.__setattr__(self, "_inner", inner)

    def perceive(self, agent_id):
        return object.__getattribute__(self, "_inner").perceive(agent_id)

    def submit_intent(self, agent_id, intent):
        return object.__getattribute__(self, "_inner").submit_intent(agent_id, intent)

    def current_round(self):
        return object.__getattribute__(self, "_inner").current_round()

    def derive_time(self, round_no):
        return object.__getattribute__(self, "_inner").derive_time(round_no)

    def __getattr__(self, name: str):
        raise AssertionError(f"life layer touched non-port kernel attribute: {name!r}")


def _load_places() -> dict:
    return {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}


def _build(seed: int = 7, tmp: Path = None, persona_ids=("P003",)):
    tmp = tmp or Path(tempfile.mkdtemp())
    places = _load_places()
    personas = load_personas(CONFIG / "personas.json")
    kernel = MiniKernel(seed=seed, places=places)
    side = SideStore(tmp / "side")
    embed = HashEmbeddingModel()
    selected = {pid: personas[pid] for pid in persona_ids}
    for pid in sorted(selected):
        p = selected[pid]
        kernel._emit("AGENT_BORN", {"agent_id": pid, "home_place": p.home_place,
                                    "needs_init": p.needs_init}, phase=0, actor="SYSTEM")
    agents = {pid: LifeLayerAgent(pid, p, kernel, side_store=side, embedding=embed,
                                  places=places, peers=sorted(selected)) for pid, p in sorted(selected.items())}
    return kernel, agents


def _run(rounds: int, seed: int = 7, persona_ids=("P003",)):
    with tempfile.TemporaryDirectory() as d:
        kernel, agents = _build(seed, Path(d), persona_ids)
        for _ in range(rounds):
            kernel.tick(agents)
        return kernel, agents


# ---- ① single agent, one round, legal events --------------------------------
def test_one_round_emits_legal_events():
    kernel, _ = _run(rounds=1)
    types = [e["type"] for e in kernel.ledger]
    assert "AGENT_BORN" in types
    assert "SCHEDULE_PLANNED" in types, "weekly plan should be emitted on PLAN phase"
    assert "PLACE_MOVE" in types and "PLACE_ARRIVED" in types, "agent should move to work place"
    assert "ACTIVITY_STARTED" in types, "settlement L2 should start the due activity"
    assert "TIME_MARK" in types, "day boundary anchor expected at round 0"
    # no money events leaked from the life layer
    assert not (set(types) & MONEY_EVENTS), f"life layer emitted money events: {set(types) & MONEY_EVENTS}"
    # ledger is a valid hash chain
    kernel_rounds = kernel.turn_seals
    assert 0 in kernel_rounds
    MiniKernel.replay(kernel.ledger, seed=kernel.seed)  # raises if chain/hash broken


def test_activity_completes_and_needs_update():
    kernel, _ = _run(rounds=6)
    types = [e["type"] for e in kernel.ledger]
    assert "ACTIVITY_COMPLETED" in types, "work activity should complete within a few ticks"
    assert "NEED_UPDATE" in types, "deterministic need decay/satisfaction expected"


# ---- ② memory goes through the log and is replayable ------------------------
def test_memory_write_retrieve_logged_and_replayable():
    kernel, _ = _run(rounds=13)
    types = [e["type"] for e in kernel.ledger]
    assert "MEMORY_WRITE" in types, "observations should be written to the log"
    assert "MEMORY_RETRIEVE" in types, "retrieval hits must be logged (C4)"

    # every MEMORY_WRITE stores refs (never the body) — 06 §3.2 / AR-C4
    for e in kernel.ledger:
        if e["type"] == "MEMORY_WRITE":
            assert e["payload"]["body_ref"].startswith("side://mem/")
            assert e["payload"]["embed_ref"].startswith("side://mem/")
            assert "text" not in e["payload"]

    # retrieval selection is fully recorded (replay must not recompute embeddings)
    for e in kernel.ledger:
        if e["type"] == "MEMORY_RETRIEVE":
            assert len(e["payload"]["selected_mem_ids"]) == len(e["payload"]["scores"])
            assert e["payload"]["weights"]["w_rec"] >= 0

    fp_run = state_fingerprint(kernel.state)
    replayed = MiniKernel.replay(kernel.ledger, seed=kernel.seed)
    fp_replay = state_fingerprint(replayed)
    assert fp_run == fp_replay, "replay(log) must reproduce the state bit-for-bit"


# ---- ③ no side channel that writes world state ------------------------------
def test_no_world_state_bypass():
    with tempfile.TemporaryDirectory() as d:
        places = _load_places()
        personas = load_personas(CONFIG / "personas.json")
        inner = MiniKernel(seed=11, places=places)
        p = personas["P003"]
        inner._emit("AGENT_BORN", {"agent_id": "P003", "home_place": p.home_place,
                                   "needs_init": p.needs_init}, phase=0, actor="SYSTEM")
        guard = GuardedKernel(inner)
        agent = LifeLayerAgent("P003", p, guard, side_store=SideStore(Path(d) / "side"),
                               embedding=HashEmbeddingModel(), places=places)
        agents = {"P003": agent}
        # GuardedKernel raises AssertionError the moment the agent touches anything
        # other than the four port methods.
        for _ in range(8):
            inner.tick(agents)


def test_persona_derived_params_deterministic():
    personas = load_personas(CONFIG / "personas.json")
    a = personas["P003"]
    b = load_personas(CONFIG / "personas.json")["P003"]
    assert (a.work_ethic, a.social_initiative, a.risk_appetite, a.saving_propensity) == \
           (b.work_ethic, b.social_initiative, b.risk_appetite, b.saving_propensity)
    assert 0.0 <= a.work_ethic <= 1.0
    assert a.compressed_profile("security").startswith("青溪镇·阿禾")


def test_embedding_version_is_single_sourced_strict():
    from life.memory import HashEmbeddingModel, load_embedding_version
    import json as _json
    cfg = _json.loads((CONFIG / "engine_version.json").read_text(encoding="utf-8"))
    # single source: life reads the same id as config
    assert HashEmbeddingModel.version == cfg["embedding"]["model"]
    # strict: a config without embedding.model -> hard error (no silent fallback)
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "engine_version.json"
        bad.write_text(_json.dumps({"schema_version": "x"}), encoding="utf-8")
        try:
            load_embedding_version(bad)
            raise AssertionError("expected RuntimeError on missing embedding.model")
        except RuntimeError:
            pass


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
