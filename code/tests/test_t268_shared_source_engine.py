"""T268 engine-level guards (live in code/tests: they import orchestration).

Constraint 1+2 (Leader): sharing is *storage*, not *visibility* — each agent's
resolvable refs are exactly the ones ITS OWN MEMORY_WRITE produced, and the
per-agent memory set is unchanged.
"""
from __future__ import annotations


def _run_engine(n=4, rounds=8, seed=7):
    from orchestration.integration import build_world
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return w, eng


def test_per_agent_refs_subset_of_own_writes():
    w, eng = _run_engine()
    by_agent: dict[str, set] = {}
    for rec in eng.ledger.records:
        if rec["type"] == "MEMORY_WRITE":
            by_agent.setdefault(rec["payload"]["agent_id"], set()).add(rec["payload"]["body_ref"])
    for a in w["agents"]:
        own = {node.body_ref for node in a.memory.nodes.values()}
        assert own <= by_agent.get(a.agent_id, set()), f"{a.agent_id} references a foreign ref"
        assert own == by_agent.get(a.agent_id, set())  # memory set == its own writes


def test_shared_refs_are_really_shared_across_agents():
    _w, eng = _run_engine()
    refs = [rec["payload"]["body_ref"] for rec in eng.ledger.records
            if rec["type"] == "MEMORY_WRITE"]
    assert len(refs) > len(set(refs)), "no sharing detected at all"
