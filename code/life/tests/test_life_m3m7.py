"""T39 acceptance tests: M3 relations, M7 goals/needs, and L5-L7 settlement.

Run:  cd code && python -m life.tests.test_life_m3m7
Also collected by pytest.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from life import constants as C
from life import goals as G
from life import relations as R
from life import settlement as S
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.settlement import PHASE35_HOOKS
from life.tests.support.mini_kernel import MiniKernel, state_fingerprint

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"

KNOWN_TYPES = {
    "AGENT_BORN", "INIT_ENDOW", "MONEY_MINTED", "WORLD_INIT",
    "TIME_MARK", "PLACE_MOVE", "PLACE_ARRIVED", "SCHEDULE_PLANNED", "SCHEDULE_REVISED",
    "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "ACTIVITY_INTERRUPTED",
    "NEED_UPDATE", "GOAL_SET", "GOAL_PROGRESS", "GOAL_ACHIEVED", "GOAL_ABANDON",
    "RELATION_CHANGE", "RELATION_ENCOUNTER", "MEMORY_WRITE", "MEMORY_RETRIEVE", "MEMORY_REFLECT",
    # T244：睡眠离线窗 / 遗忘 / 整合 / 人格漂移（08 §1.2 S；默认已开）
    "SLEEP_STARTED", "SLEEP_COMPLETED", "MEMORY_CONSOLIDATE", "MEMORY_FORGET", "PERSONA_DRIFT",
    "OBSERVATION", "SEED_EVENT", "TAG_EMITTED", "ROLE_CHANGE",
    "NORM_PROPOSED", "NORM_ADOPTED", "NORM_VIOLATED", "LLM_JUDGMENT", "NARRATIVE",
    "INTENT_REJECTED", "TURN_SEAL", "SYSTEM_ERROR",
    # template-driven (T49/T45)
    "SKILL_PRACTICE", "SKILL_LEVEL_UP", "SKILL_OUTPUT",
    "SCORE_POSTED", "RANKING_EMITTED", "CONFLICT_STARTED", "CONFLICT_RESOLVED",
    "DEPOSIT", "WITHDRAW", "INTEREST_PAID", "STATE_CHANGE", "AGENT_REVIVED",
    "GROUP_CREATED", "GROUP_JOINED", "GROUP_LEFT",
    "OFFER_CREATED", "OFFER_ACCEPTED", "OFFER_REJECTED", "OFFER_COUNTERED", "OFFER_EXPIRED",
    # econ (v1)
    "TRANSFER", "MARKET_TRADE", "TAX_LEVIED", "UBI_PAID", "METABOLISM", "AGENT_DIED",
    "LOAN_ISSUED", "LOAN_REPAY", "INTEREST_CHARGED", "PENALTY_APPLIED", "REVIVE_FEE_PAID",
    "MONEY_BURNED", "MSG_PUBLIC", "MSG_DM", "MSG_GROUP", "LLM_CALL",
    "ECONOMY_INVARIANT_VIOLATION", "DROPPED",
}


def _places():
    return {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}


def _build(seed: int, n: int, tmp: Path):
    places = _places()
    personas = load_personas(CONFIG / "personas.json")
    pids = sorted(personas)[:n]
    chosen = {pid: personas[pid] for pid in pids}
    kernel = MiniKernel(seed=seed, places=places)
    for pid in pids:
        p = chosen[pid]
        kernel._emit("AGENT_BORN", {"agent_id": pid, "home_place": p.home_place,
                                    "needs_init": p.needs_init}, phase=0, actor="SYSTEM")
    kernel.commit_round()
    side = SideStore(tmp / "side")
    embed = HashEmbeddingModel()
    agents = {pid: LifeLayerAgent(pid, chosen[pid], kernel, side_store=side, embedding=embed,
                                  places=places, peers=pids) for pid in pids}
    return kernel, agents, chosen


def _run(n: int, rounds: int, seed: int = 7):
    with tempfile.TemporaryDirectory() as d:
        kernel, agents, chosen = _build(seed, n, Path(d))
        for _ in range(rounds):
            kernel.tick(agents)
        return kernel, agents, chosen


# ---- M3: deterministic relation algebra (unit) ------------------------------
def test_relation_update_is_deterministic_and_clamped():
    d1 = R.rel_delta("trade_success", current={}, amount=100)
    d2 = R.rel_delta("trade_success", current={}, amount=100)
    assert d1 == d2 and d1["trust"] > 0
    # transfer_rescue is the recipient's view
    r = R.rel_delta("transfer_rescue")
    assert r["affinity"] == R.RELATION_COEF["k_rescue"] and r["trust"] == R.RELATION_COEF["k_t2"]
    # clamp: push affinity far past the cap
    rel = {"affinity": 95}
    R.apply_delta(rel, {"affinity": 1000})
    assert rel["affinity"] == 100
    # per-cause magnitude cap Δ_max
    assert abs(R.rel_delta("chat", current={"affinity": 1}, duration=999)["affinity"]) <= C.RELATION_DELTA_MAX


def test_qualitative_change_rng_branch_then_freeze():
    env = R.soft_judgment_envelope("mentor_relation", before=0, after=60)
    assert env["options"] == ["formed", "not_formed"]
    j = R.freeze_judgment("J-1", "mentor_relation", ["P001", "P002"], env, "formed",
                          context_digest="sha256:x", model="rule-based-v1")
    assert j["frozen"] is True and j["decision"] in env["options"]
    assert R.delta_from_frozen_label("formed")["affinity"] > 0
    try:
        R.freeze_judgment("J-2", "x", [], env, "bogus", "d", "m")
        raise AssertionError("branch outside envelope must be rejected")
    except ValueError:
        pass


# ---- M7: goals + needs (unit + integration) ---------------------------------
def test_goal_progress_deterministic():
    g = G.Goal(goal_id="G", agent_id="P", kind="mastery", layer="growth")
    p1 = G.advance(G.Goal(**{**g.as_dict(), "progress": 0.0}), "learn")
    p2 = G.advance(G.Goal(**{**g.as_dict(), "progress": 0.0}), "learn")
    assert p1 == p2 > 0.0
    assert G.advance(g, "rest") == 0.0            # non-matching activity


def test_goals_and_needs_events_emitted():
    kernel, _, _ = _run(n=2, rounds=6)
    types = [e["type"] for e in kernel.ledger]
    assert "GOAL_SET" in types, "weekly PLAN should seed goals"
    assert "GOAL_PROGRESS" in types, "activities should advance goals"
    assert "NEED_UPDATE" in types, "needs decay/satisfaction expected"
    # goals persisted into state (folded)
    assert any(kernel.state["agents"][a]["goals"] for a in kernel.state["agents"])


# ---- M3 + L5 integration: encounters/relations + replay ---------------------
def test_encounters_and_relation_change_replayable():
    kernel, _, _ = _run(n=3, rounds=84)
    types = [e["type"] for e in kernel.ledger]
    assert "RELATION_ENCOUNTER" in types, "co-located agents should be recorded"
    assert "RELATION_CHANGE" in types, "familiarity/affinity should move deterministically"
    fp = state_fingerprint(kernel.state)
    rp = state_fingerprint(MiniKernel.replay(kernel.ledger, seed=kernel.seed))
    assert fp == rp, "relation/goal state must survive replay bit-for-bit"
    assert kernel.state["relations"], "relations must be folded into state"


# ---- L5/L6/L7 not empty + no unregistered event types -----------------------
def test_l5_l6_l7_nonempty_and_legal():
    # L5: two agents co-located -> encounter + relation change
    st = {"round": 5, "agents": {"A": {"location": "plaza", "encounters": {}},
                                 "B": {"location": "plaza", "encounters": {}}},
          "relations": {}, "event_index": {}, "seen_pairs": set()}
    l5 = S.update_relations(st, 5, _ctx())
    assert any(e.type == "RELATION_ENCOUNTER" for e in l5)
    assert any(e.type == "RELATION_CHANGE" for e in l5)

    # L6: a global significant event forces an OBSERVATION for a visible agent
    st6 = {"round": 5, "agents": {"A": {"location": "plaza", "observed_event_seqs": []}},
           "event_index": {1: {"seq": 1, "round": 5, "phase": 35, "actor": "SYSTEM",
                               "type": "AGENT_DIED", "payload": {"agent_id": "Z"}}}}
    l6 = S.write_memories(st6, 5, _ctx())
    assert any(e.type == "OBSERVATION" for e in l6)

    # L7: completed activities emit tags; 3 same-scope/topic emitters adopt a norm.
    #     (L7 reads the SAME-ROUND ACTIVITY_COMPLETED events, folded by serial L3.)
    st7 = {"round": 5, "agents": {a: {"location": "plaza"} for a in ("A", "B", "C")},
           "norms": {}, "tags": {}, "event_index": {
               i: {"seq": i, "round": 5, "actor": ag, "type": "ACTIVITY_COMPLETED",
                   "payload": {"agent_id": ag, "activity_type": "work", "place": "plaza"}}
               for i, ag in enumerate(("A", "B", "C"), start=1)}}
    l7 = S.emit_tags(st7, 5, _ctx())
    assert any(e.type == "TAG_EMITTED" for e in l7)
    assert any(e.type == "NORM_PROPOSED" for e in l7) and any(e.type == "NORM_ADOPTED" for e in l7)


def test_events_all_registered_and_no_bypass_n3():
    kernel, agents, _ = _run(n=3, rounds=20)
    unknown = sorted({e["type"] for e in kernel.ledger if e["type"] not in KNOWN_TYPES})
    assert not unknown, f"unregistered event types: {unknown}"
    # every L1..L7 hook is a callable (no longer stubs returning None)
    for name, fn in PHASE35_HOOKS.items():
        assert callable(fn)


class _CtxStub:
    def derive_time(self, round_no):
        return C.derive_time(round_no)

    def rng(self, stream_id, seq, n):
        from life.util import draw
        return draw(0, stream_id, seq, 0, n)


def _ctx():
    return _CtxStub()


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
