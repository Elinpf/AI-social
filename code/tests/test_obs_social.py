"""T105：v2 社会面板指标（metrics.social.*）测试。

覆盖 network / group_heat / issues / institutions 四块 + F 类 social_soft 单列；
断言 D 类、两次重算字节相等、llm_judged_metric_count==0。
"""

from obs import metrics, to_canonical
from obs.metrics_social import social_metrics, social_soft
from obs.testsupport import build_log


def _social_log():
    lb = build_log(seed=7, agents=("P001", "P002", "P003"))
    lb.add(1, 3, "P001", "MSG_DM", {"msg_id": "D1", "from": "P001", "to": "P002",
                                    "visibility": "private", "refs": []})
    lb.add(1, 3, "P002", "MSG_DM", {"msg_id": "D2", "from": "P002", "to": "P001",
                                    "visibility": "private", "refs": ["D1"]})
    lb.add(2, 3, "P001", "MSG_PUBLIC", {"msg_id": "PUB1", "from": "P001",
                                        "refs": [], "scope": "global", "place": None})
    lb.add(2, 3, "P003", "MSG_PUBLIC", {"msg_id": "PUB2", "from": "P003",
                                        "refs": ["PUB1"], "scope": "global", "place": None})
    lb.add(2, 35, "SYSTEM", "GROUP_CREATED", {"group_id": "G1",
                                              "members": ["P001", "P002"], "kind": "guild"})
    lb.add(3, 3, "P001", "MSG_GROUP", {"msg_id": "G1m", "from": "P001", "group_id": "G1",
                                       "refs": []})
    lb.add(3, 3, "P002", "MSG_GROUP", {"msg_id": "G2m", "from": "P002", "group_id": "G1",
                                       "refs": []})
    lb.add(3, 35, "P003", "TAG_EMITTED", {"agent_id": "P003", "tag": "labor",
                                          "valence": 1, "source_msg_id": None})
    lb.add(4, 35, "P001", "TAG_EMITTED", {"agent_id": "P001", "tag": "labor", "valence": -1})
    lb.add(4, 35, "P002", "NORM_PROPOSED", {"norm_id": "N1", "proposer": "P002",
                                            "support_count": 2, "threshold": 2})
    lb.add(4, 35, "SYSTEM", "NORM_ADOPTED", {"norm_id": "N1", "adopters": ["P001", "P002"]})
    lb.add(4, 3, "P001", "VOTE_CAST", {"vote_id": "V1", "norm_id": "N1",
                                       "agent_id": "P001", "choice": "yes", "support_count": 2})
    lb.add(5, 35, "P003", "PUBLIC_REACTION", {"reaction_id": "R1", "agent_id": "P003",
                                              "target": {"kind": "agent", "ref": "P001"},
                                              "kind": "boycott", "topic_tag": "labor"})
    lb.add(5, 2, "P001", "OFFER_CREATED", {"offer_id": "O1", "from": "P001", "to": ["P002"],
                                           "kind": "job", "terms": {"wage_mu": 100}})
    lb.add(6, 3, "P001", "CONTRACT_CREATED", {"contract_id": "C1", "kind": "EMPLOYMENT",
                                              "parties": ["P001", "P002"], "terms": {},
                                              "enforceable": True, "rule_ref": "x"})
    lb.add(7, 35, "SYSTEM", "CONTRACT_FULFILLED", {"contract_id": "C1", "round": 7, "by": "P002"})
    lb.add(8, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J1", "dimension": "respect_score",
                                          "decision": 4, "frozen": True, "model": "m",
                                          "context_digest": "sha256:x", "parties": ["P002"]})
    return lb.records()


def test_social_metrics_structure():
    s = social_metrics(_social_log())
    assert set(s) >= {"network", "group_heat", "issues", "institutions",
                      "llm_judged_metric_count"}
    assert s["llm_judged_metric_count"] == 0
    # network：DM(P001↔P002) + GROUP(P001→P002 与 P002→P001) + PUBLIC ref(P001→P003)
    assert s["network"]["channel_counts"] == {"DM": 2, "PUBLIC": 2, "GROUP": 2}
    assert s["network"]["comm_directed_edges"] >= 3
    assert s["network"]["n_groups"] == 1
    assert s["network"]["org_size_dist"] == [2]
    # group_heat
    assert s["group_heat"]["n_msg_group"] == 2
    assert s["group_heat"]["active_groups"] == 1
    assert s["group_heat"]["per_group"]["G1"]["msg_count"] == 2
    # issues
    assert s["issues"]["by_tag"]["labor"]["freq"] == 2
    assert s["issues"]["reaction_counts"] == {"boycott": 1}
    assert s["issues"]["boycott_pairs"] == [["P003", "agent", "P001"]]
    # institutions
    inst = s["institutions"]
    assert inst["n_groups"] == 1 and inst["group_kinds"] == {"guild": 1}
    assert inst["norm_proposed"] == 1 and inst["norm_adopted"] == 1
    assert inst["n_contracts"] == 1 and inst["contract_kinds"] == {"EMPLOYMENT": 1}
    assert inst["employment_contracts"] == 1 and inst["contract_fulfillment_rate"] == 1.0
    assert inst["n_votes"] == 1


def test_social_bitwise_equal_and_in_metrics_snapshot():
    recs = _social_log()
    assert to_canonical(social_metrics(recs)) == to_canonical(social_metrics(recs))
    m = metrics(recs)["metrics"]
    assert "social" in m and "social_soft" in m
    assert m["social"]["llm_judged_metric_count"] == 0
    assert m["social_soft"]["contains_llm_judgment"] is True  # F 类单列
    # 整快照字节相等
    assert to_canonical(metrics(recs)) == to_canonical(metrics(recs))


def test_social_soft_is_f_class():
    ss = social_soft(_social_log())
    assert ss["basis"] == "F" and ss["source"] == "frozen_llm"
    assert ss["respect"] == {"4": 1}


def test_norm_coverage_distinct_from_adoption_rate_and_zero_safe():
    """防'假绿'：norm_coverage（去重采纳者/存活）≠ adoption_success_rate（adopted/proposed）；分母0→0.0。"""
    from obs.metrics_social import social_metrics
    # 4 agents；proposed=2、adopted=1（仅 P001 采纳）→ success=0.5、coverage=0.25
    lb = build_log(seed=1, agents=("P001", "P002", "P003", "P004"))
    lb.add(1, 35, "P001", "NORM_PROPOSED", {"norm_id": "N1", "proposer": "P001", "support_count": 1})
    lb.add(1, 35, "P001", "NORM_PROPOSED", {"norm_id": "N2", "proposer": "P001", "support_count": 1})
    lb.add(2, 35, "SYSTEM", "NORM_ADOPTED", {"norm_id": "N1", "adopters": ["P001"]})
    inst = social_metrics(lb.records())["institutions"]
    assert inst["adoption_success_rate"] == 0.5      # 1/2
    assert inst["norm_coverage"] == 0.25             # 1/4（去重存活采纳者 / 存活）
    assert inst["norm_coverage"] != inst["adoption_success_rate"]
    # 分母为 0：无提案/无采纳 → 两者均 0.0（绝不默认 1.0）
    lb2 = build_log(seed=1)
    inst2 = social_metrics(lb2.records())["institutions"]
    assert inst2["adoption_success_rate"] == 0.0
    assert inst2["norm_coverage"] == 0.0
