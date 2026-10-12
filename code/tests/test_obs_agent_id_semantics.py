"""T248：`agent_id` 可含非 Agent 主体（MARKET）—— obs 聚合侧止血的双向反向验证。

复用 `contracts.actors` 单一真源；非 Agent 不得进"居民"级聚合。
"""

from contracts.actors import is_agent_actor
from obs.census import semantic_census
from obs.life import need_metrics
from obs.testsupport import build_log


def test_is_agent_actor_guards():
    assert is_agent_actor("P001") and is_agent_actor("A000")
    for x in ("MARKET", "SYSTEM", "OBSERVER", "DIRECTOR", "WORLD", "BANK", "TAX_POOL", "", None):
        assert not is_agent_actor(x)


def test_need_metrics_excludes_non_agent_keeps_agent():
    lb = build_log(seed=1, agents=("A000", "A001"))
    lb.add(1, 2, "MARKET", "NEED_UPDATE", {"agent_id": "MARKET", "dim": "energy", "after": 10})
    lb.add(1, 2, "A000", "NEED_UPDATE", {"agent_id": "A000", "dim": "energy", "after": 80})
    m = need_metrics(lb.records())
    # 反向验证①：非 Agent（MARKET）不进聚合 → energy 只反映 A000
    assert m["dims"]["energy"]["mean"] == 80.0
    assert m["dims"]["energy"]["min"] == 80.0
    assert m["dims"]["energy"]["max"] == 80.0
    # 反向验证②：真 Agent 照进
    assert m["n_need_updates"] == 1
    # 泄漏计数可见
    assert m["n_need_updates_non_agent_excluded"] == 1


def test_need_metrics_all_agents_pass():
    lb = build_log(seed=2, agents=("A000", "A001"))
    lb.add(1, 2, "A000", "NEED_UPDATE", {"agent_id": "A000", "dim": "social", "after": 40})
    lb.add(1, 2, "A001", "NEED_UPDATE", {"agent_id": "A001", "dim": "social", "after": 60})
    m = need_metrics(lb.records())
    assert m["dims"]["social"]["mean"] == 50.0
    assert m["n_need_updates_non_agent_excluded"] == 0


def test_census_e7_excludes_non_agent_state_change():
    lb = build_log(seed=3, agents=("A000", "A001"))
    lb.add(1, 2, "MARKET", "STATE_CHANGE", {"agent_id": "MARKET", "to": "exhausted"})
    lb.add(1, 2, "A000", "STATE_CHANGE", {"agent_id": "A000", "to": "exhausted"})
    e7 = semantic_census(lb.records())["semantic_hits"]["E7_emotion_burnout"]
    # 只有真 Agent A000 计入；MARKET 不计
    assert e7["participants"] == 1 and e7["count"] == 1


def test_census_e7_market_only_is_no_hit():
    lb = build_log(seed=4, agents=("A000",))
    lb.add(1, 2, "MARKET", "STATE_CHANGE", {"agent_id": "MARKET", "to": "exhausted"})
    e7 = semantic_census(lb.records())["semantic_hits"]["E7_emotion_burnout"]
    assert e7["hit"] is False and e7["participants"] == 0
