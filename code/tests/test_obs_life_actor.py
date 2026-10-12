"""obs.life._agent_of：非 Agent actor（SYSTEM/OBSERVER/DIRECTOR/...）不得被当成 Agent（T238）。"""

from obs.life import _agent_of


def test_agent_of_prefers_payload_agent_id():
    assert _agent_of({"actor": "DIRECTOR", "payload": {"agent_id": "P001"}}) == "P001"


def test_agent_of_excludes_non_agent_actors():
    for a in ("SYSTEM", "OBSERVER", "DIRECTOR", "WORLD", "MARKET", "BANK", "TAX_POOL"):
        assert _agent_of({"actor": a, "payload": {}}) is None


def test_agent_of_returns_real_actor():
    assert _agent_of({"actor": "P007", "payload": {}}) == "P007"
