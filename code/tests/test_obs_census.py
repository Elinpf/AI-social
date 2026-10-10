"""事件普查报告测试（15-event-census-spec）。

- 报告结构（原子频次 / 20 类语义命中 / 未命中 / 覆盖度 / 复现）；
- 异常前置校验硬报错（未知类型 / 缺字段 / 锚点悬空）；
- 合成日志的语义命中。
"""

import copy

import pytest

from obs import census_report
from obs.atomic import preflight, coverage, CensusError
from obs.reader import ReadOnlyLog
from obs.testsupport import build_log
from engine.ledger import Ledger


def _rich_log():
    lb = build_log(seed=42, agents=("A000", "A001", "A002"))
    R, PH = 0, 0
    # E16 场所移动
    lb.add(1, 35, "A000", "PLACE_MOVE", {"agent_id": "A000", "to_place": "hall"})
    # E10 技能练习 + E1 师徒（需 ≥2 次 mentorship 活动 + 技能级差 + familiarity）
    lb.add(2, 35, "A000", "SKILL_PRACTICE", {"agent_id": "A000", "skill_id": "craft"})
    lb.add(2, 35, "A001", "SKILL_PRACTICE", {"agent_id": "A001", "skill_id": "craft"})
    lb.add(3, 35, "A000", "SKILL_LEVEL_UP", {"agent_id": "A000", "skill_id": "craft",
                                             "level_before": 1, "level_after": 5})
    lb.add(3, 35, "A001", "SKILL_LEVEL_UP", {"agent_id": "A001", "skill_id": "craft",
                                             "level_before": 1, "level_after": 2})
    # familiarity
    lb.add(4, 35, "A000", "RELATION_CHANGE", {"from": "A000", "to": "A001",
                                              "dim": "affinity", "before": 0, "after": 60})
    lb.add(5, 35, "A001", "RELATION_CHANGE", {"from": "A001", "to": "A000",
                                              "dim": "affinity", "before": 0, "after": 30})
    for i in range(2):
        lb.add(5 + i, 35, "A000", "ACTIVITY_COMPLETED",
               {"agent_id": "A000", "activity_type": "mentorship",
                "participants": ["A000", "A001"], "template": "mentorship"})
    # E2 gift
    lb.add(6, 35, "A000", "TRANSFER", {"from": "A000", "to": "A001", "amount": 10,
                                       "reason": "gift"})
    # E6 whisper
    lb.add(7, 3, "A001", "MSG_DM", {"from": "A001", "to": "A000", "visibility": "private"})
    # E5 saving
    lb.add(8, 4, "A000", "DEPOSIT", {"agent_id": "A000", "amount": 5})
    # E8 scoring
    lb.add(9, 35, "SYSTEM", "SCORE_POSTED", {"contest_id": "c1", "score": 3})
    lb.add(9, 35, "SYSTEM", "RANKING_EMITTED", {"contest_id": "c1"})
    # E3 combat
    lb.add(10, 35, "A001", "ACTIVITY_STARTED", {"agent_id": "A001",
                                                "activity_type": "combat_training"})
    lb.add(10, 35, "SYSTEM", "CONFLICT_RESOLVED", {"conflict_id": "x", "winner": "A001",
                                                   "rule_ref": "training"})
    # E17 conflict
    lb.add(11, 35, "SYSTEM", "CONFLICT_STARTED", {"conflict_id": "x", "parties": ["A001", "A002"]})
    lb.add(11, 35, "SYSTEM", "CONFLICT_RESOLVED", {"conflict_id": "x", "winner": "A001"})
    # E13 norm
    lb.add(12, 35, "A000", "NORM_PROPOSED", {"norm_id": "n1", "proposer": "A000",
                                             "support_count": 2})
    lb.add(12, 35, "SYSTEM", "NORM_ADOPTED", {"norm_id": "n1", "adopters": ["A000", "A001"]})
    # E15 counter
    lb.add(13, 3, "A001", "OFFER_COUNTERED", {"offer_id": "o1", "by": "A001", "round_no": 1})
    # E14 academic
    lb.add(14, 35, "A000", "ACTIVITY_COMPLETED",
           {"agent_id": "A000", "activity_type": "academic_collab",
            "participants": ["A000", "A002"], "template": "academic_collab"})
    # E18 relation accept
    lb.add(15, 35, "A000", "RELATION_CHANGE", {"from": "A000", "to": "A002",
                                               "dim": "affinity", "before": 0, "after": 70})
    # E19 icebreak: encounter + msg（新相识对，遭遇时 familiarity < ε）
    lb.add(16, 35, "SYSTEM", "RELATION_ENCOUNTER", {"a": "A001", "b": "A002"})
    lb.add(16, 3, "A001", "MSG_PUBLIC", {"from": "A001", "to": "A002", "refs": []})
    # E9 scarcity（scarcity_index 0–100，θ_scarce=50，08 §1.2-N）
    lb.add(17, 35, "A001", "MARKET_TRADE", {"buyer": "A001", "seller": "A000",
                                            "amount": 3, "scarcity_index": 90})
    # E7 burnout
    lb.add(18, 35, "A002", "NEED_UPDATE", {"agent_id": "A002", "dim": "energy",
                                           "after": 5})
    lb.add(19, 35, "A002", "NEED_UPDATE", {"agent_id": "A002", "dim": "energy",
                                           "after": 5})
    # E20 maintenance (gap > D_maint=84)
    lb.add(100, 35, "A000", "RELATION_CHANGE", {"from": "A000", "to": "A001",
                                                "dim": "affinity", "before": 60,
                                                "after": 40})
    return lb.records()


def test_census_report_structure():
    rep = census_report(_rich_log())
    assert rep["schema_version"] == "1.1"
    assert rep["N"] == 3
    assert len(rep["semantic_hits"]) == 20
    assert set(rep["semantic_hits"]) == set(rep["semantic_order"])
    assert "atomic_freq" in rep and "coverage" in rep
    assert rep["reproducibility"]["same_log_bitwise"] is True
    assert rep["reproducibility"]["llm_judged_metric_count"] == 0
    # 覆盖度：无未知类型
    assert rep["coverage"]["unknown_types_seen"] == []


def test_census_bitwise_equal():
    from obs import to_canonical
    recs = _rich_log()
    assert to_canonical(census_report(recs)) == to_canonical(census_report(recs))


def test_census_hits_expected_semantic_events():
    rep = census_report(_rich_log())
    hits = {k for k, v in rep["semantic_hits"].items() if v["hit"]}
    for e in ("E1_mentorship", "E2_gift_giving", "E3_combat_training",
              "E5_saving_money", "E6_whispered_comm", "E7_emotion_burnout",
              "E8_diff_scoring", "E9_scarcity_buy", "E10_skill_practice",
              "E13_group_proposal", "E14_academic_collab", "E15_counter_propose",
              "E16_select_location", "E17_power_conflict", "E18_rel_acceptance",
              "E19_ice_breaking", "E20_rel_maintenance"):
        assert e in hits, f"{e} 未命中"


def test_preflight_unknown_type_hard_error():
    recs = _rich_log()
    recs = copy.deepcopy(recs)
    recs[3]["type"] = "NOT_REGISTERED"
    with pytest.raises(CensusError):
        preflight(ReadOnlyLog(recs, verify=False))


def test_preflight_missing_field_hard_error():
    lb = build_log(seed=1)
    lb.add(1, 35, "A000", "RELATION_CHANGE", {"from": "A000", "to": "A001"})  # 缺 dim/after
    with pytest.raises(CensusError):
        preflight(ReadOnlyLog(lb.records(), verify=False))


def test_preflight_dangling_observation_anchor():
    lb = build_log(seed=1)
    lb.add(1, 35, "A000", "OBSERVATION", {"observer": "A001", "target_event_seq": 99999})
    with pytest.raises(CensusError):
        preflight(ReadOnlyLog(lb.records(), verify=False))


def test_coverage_registered_unused_reported():
    lb = build_log(seed=1)
    cov = coverage(ReadOnlyLog(lb.records()))
    assert cov["atomic_types_registered"] >= 60
    assert "TRANSFER" in cov["atomic_registered_unused"]
    assert cov["unknown_types_seen"] == []


def test_soft_llm_judgment_separated_from_gates():
    """F 类：冻结 LLM 判定单列 emergence_soft，llm_judged_metric_count 仍为 0，且 llm_calls==0。"""
    from obs import metrics, to_canonical
    from obs.runtime import llm_calls, reset_llm_calls
    lb = build_log(seed=3)
    lb.add(1, 2, "A000", "LLM_JUDGMENT",
           {"judgment_id": "j1", "decision": "accept", "model": "m",
            "context_digest": "sha256:abc", "frozen": True,
            "dimension": "friendship_label", "parties": ["A000", "A001"],
            "question_ref": "q1", "envelope": {}})
    lb.add(1, 2, "A000", "LLM_JUDGMENT",
           {"judgment_id": "j2", "decision": 4, "model": "m",
            "context_digest": "sha256:def", "frozen": True,
            "dimension": "satisfaction", "parties": ["A000"],
            "question_ref": "q2", "envelope": {}})
    recs = lb.records()
    reset_llm_calls()
    snap = metrics(recs)
    assert llm_calls() == 0
    assert snap["metrics"]["emergence"]["llm_judged_metric_count"] == 0   # 门禁指标不含 F
    assert snap["metrics"]["emergence_soft"]["contains_llm_judgment"] is True
    assert snap["metrics"]["wellbeing_soft"]["contains_llm_judgment"] is True
    # F 值只读冻结、字节可复现
    assert to_canonical(metrics(recs)) == to_canonical(metrics(recs))


def test_census_preflight_passes_on_llm_judgment_log():
    lb = build_log(seed=3)
    lb.add(1, 2, "A000", "LLM_JUDGMENT",
           {"judgment_id": "j1", "decision": "accept", "frozen": True})
    preflight(ReadOnlyLog(lb.records()))  # 不抛错


def test_preflight_nonstrict_records_missing_field_and_census_still_works():
    """非严格模式：缺字段降级为异常记录，普查仍产出（供证据包如实记录）。"""
    from obs.atomic import preflight
    from obs import census_report
    lb = build_log(seed=1)
    # 模拟真实日志里 GOAL_SET 采用批/嵌套形态（缺顶层 goal_id）
    lb.add(1, 2, "A000", "GOAL_SET",
           {"agent_id": "A000", "goals": [{"goal_id": "G-1", "kind": "security"}]})
    recs = lb.records()
    anoms = preflight(ReadOnlyLog(recs), strict=False)
    assert any(a["type"] == "GOAL_SET" and a["field"] == "goal_id" for a in anoms)
    rep = census_report(recs, strict=False)
    assert rep["preflight_ok"] is False
    assert rep["preflight_anomalies"]
    assert len(rep["semantic_hits"]) == 20
    # 严格模式仍硬报错（规格要求）
    with pytest.raises(CensusError):
        census_report(recs, strict=True)


def test_obs_handles_list_valued_actor_fields():
    """回归：OFFER_CREATED.to 为列表（08 §1.2-K to[]）时，obs 不应崩溃。"""
    from obs import census_report, metrics, to_canonical
    from obs.folds import agents
    lb = build_log(seed=1)
    lb.add(5, 3, "A000", "OFFER_CREATED",
           {"offer_id": "o1", "from": "A000", "to": ["A001", "A002"], "kind": "job"})
    recs = lb.records()
    assert "A001" in agents(recs) and "A002" in agents(recs)
    # metrics / census / gate 均不应抛异常且字节可复现
    assert to_canonical(metrics(recs)) == to_canonical(metrics(recs))
    assert to_canonical(census_report(recs)) == to_canonical(census_report(recs))
