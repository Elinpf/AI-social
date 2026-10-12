"""T203/T212：「确定性后果」真值口径测试（只读/确定性）。"""

import json

from obs.truth_from_consequences import (
    correct_from_truth, human_sample, truth_from_consequences,
)
from obs.testsupport import build_log


def _log():
    lb = build_log(seed=1, agents=("P001", "P002"))
    # 判定：rel_affinity（P001→P002）
    lb.add(1, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J-P001-P002-rel_affinity-w0",
        "dimension": "rel_affinity", "parties": ["P001", "P002"], "decision": "formed",
        "envelope": {"options": ["formed", "not_formed"]}, "created_round": 1})
    # 后果：窗口内 affinity 达阈 → formed（08 口径：after ≥ θ=20）
    lb.add(2, 35, "P001", "RELATION_CHANGE", {"from": "P001", "to": "P002", "dim": "affinity",
        "before": 0, "after": 20, "cause": "copresence"})
    # 判定：rel_trust，无后果 → 剔除
    lb.add(1, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J-P001-P002-rel_trust-w0",
        "dimension": "rel_trust", "parties": ["P001", "P002"], "decision": "formed",
        "envelope": {"options": ["formed", "not_formed"]}, "created_round": 1})
    # 判定：stance（P001→P002），窗口内有 accept → accept
    lb.add(1, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J-P001-P002-stance-w0",
        "dimension": "stance", "parties": ["P001", "P002"], "decision": "accept",
        "envelope": {"options": ["accept", "reject"]}, "created_round": 1})
    lb.add(3, 4, "P001", "OFFER_ACCEPTED", {"by": "P001", "offer_id": "O-5-P002",
        "terms": {"good_id": "material", "price_mu": 10, "qty": 1}})
    # 判定：affection → 默认剔除
    lb.add(1, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J-P001-P002-affection-w0",
        "dimension": "affection", "parties": ["P001", "P002"], "decision": "high",
        "envelope": {"options": ["high", "low"]}, "created_round": 1})
    return lb.records()


def _pairs():
    return [
        {"judgment_id": "J-P001-P002-rel_affinity-w0", "dimension": "rel_affinity",
         "parties": ["P001", "P002"], "round": 1, "predicted_label": "formed"},
        {"judgment_id": "J-P001-P002-rel_trust-w0", "dimension": "rel_trust",
         "parties": ["P001", "P002"], "round": 1, "predicted_label": "formed"},
        {"judgment_id": "J-P001-P002-stance-w0", "dimension": "stance",
         "parties": ["P001", "P002"], "round": 1, "predicted_label": "accept"},
        {"judgment_id": "J-P001-P002-affection-w0", "dimension": "affection",
         "parties": ["P001", "P002"], "round": 1, "predicted_label": "high"},
    ]


def test_truth_labels_and_exclusion_counts():
    rep = truth_from_consequences(_log(), _pairs(), window=12)
    assert rep["labels"]["J-P001-P002-rel_affinity-w0"] == "formed"
    assert rep["labels"]["J-P001-P002-stance-w0"] == "accept"
    # rel_trust 无后果、affection 无规则 → 均剔除并分类计数
    assert "J-P001-P002-rel_trust-w0" not in rep["labels"]
    assert rep["excluded_by_reason"].get("no_rc_event_in_window") == 1
    assert any("no_affection" in k for k in rep["excluded_by_reason"])
    # 覆盖率逐维
    assert rep["coverage"]["rel_affinity"] == {"n": 1, "included": 1, "excluded": 0}
    assert rep["coverage"]["rel_trust"] == {"n": 1, "included": 0, "excluded": 1}


def test_window_boundary_excludes():
    lb = build_log(seed=2, agents=("P001", "P002"))
    lb.add(1, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J-af", "dimension": "rel_affinity",
        "parties": ["P001", "P002"], "created_round": 1})
    lb.add(20, 35, "P001", "RELATION_CHANGE", {"from": "P001", "to": "P002", "dim": "affinity",
        "before": 0, "after": 1, "cause": "x"})  # 窗口 W=12 之外
    rep = truth_from_consequences(lb.records(),
        [{"judgment_id": "J-af", "dimension": "rel_affinity", "parties": ["P001", "P002"], "round": 1}],
        window=12)
    assert "J-af" not in rep["labels"]


def test_negative_label_when_event_without_positive():
    lb = build_log(seed=3, agents=("P001", "P002"))
    lb.add(1, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J-x", "dimension": "respect",
        "parties": ["P001", "P002"], "created_round": 1})
    # 窗口内 respect 事件但 Δ<=0 → low
    lb.add(2, 35, "P001", "RELATION_CHANGE", {"from": "P001", "to": "P002", "dim": "respect",
        "before": 3, "after": 2, "cause": "x"})
    rep = truth_from_consequences(lb.records(),
        [{"judgment_id": "J-x", "dimension": "respect", "parties": ["P001", "P002"], "round": 1}])
    assert rep["labels"]["J-x"] == "low"


def test_round_looked_up_from_log_when_missing():
    rep = truth_from_consequences(_log(),
        [{"judgment_id": "J-P001-P002-rel_affinity-w0", "dimension": "rel_affinity",
          "parties": ["P001", "P002"]}], window=12)  # 不给 round → 从日志反查
    assert rep["labels"]["J-P001-P002-rel_affinity-w0"] == "formed"


def test_correct_from_truth_and_sample():
    rep = truth_from_consequences(_log(), _pairs(), window=12)
    ids, corr = correct_from_truth(_pairs(), rep["labels"])
    assert len(ids) == 2 and all(corr)  # affinity formed==formed, stance accept==accept
    assert human_sample(["b", "a", "c", "d"], cap=2) == ["a", "c"]
    assert rep["human_sample"] == sorted(rep["labels"])


def test_theta_semantics_and_override():
    # 08 口径：after ≥ θ(默认20) ⇒ formed；以下调 θ 可改判
    lb = build_log(seed=9, agents=("P001", "P002"))
    lb.add(1, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J-a", "dimension": "rel_affinity",
        "parties": ["P001", "P002"], "created_round": 1})
    lb.add(2, 35, "P001", "RELATION_CHANGE", {"from": "P001", "to": "P002", "dim": "affinity",
        "before": 0, "after": 3})
    pairs = [{"judgment_id": "J-a", "dimension": "rel_affinity", "parties": ["P001", "P002"], "round": 1}]
    assert truth_from_consequences(lb.records(), pairs)["labels"]["J-a"] == "not_formed"
    assert truth_from_consequences(lb.records(), pairs,
                                   dim_thresholds={"rel_affinity": 3})["labels"]["J-a"] == "formed"


def test_vocab_families_rel_vs_plain():
    # rel_respect → formed 族；respect → high/low 族（不得归一）
    lb = build_log(seed=10, agents=("P001", "P002"))
    lb.add(1, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J-rr", "dimension": "rel_respect",
        "parties": ["P001", "P002"], "created_round": 1})
    lb.add(1, 2, "P001", "LLM_JUDGMENT", {"judgment_id": "J-r", "dimension": "respect",
        "parties": ["P001", "P002"], "created_round": 1})
    lb.add(2, 35, "P001", "RELATION_CHANGE", {"from": "P001", "to": "P002", "dim": "respect",
        "before": 0, "after": 25})
    pairs = [{"judgment_id": "J-rr", "dimension": "rel_respect", "parties": ["P001", "P002"], "round": 1},
             {"judgment_id": "J-r", "dimension": "respect", "parties": ["P001", "P002"], "round": 1}]
    lab = truth_from_consequences(lb.records(), pairs)["labels"]
    assert lab["J-rr"] == "formed"
    assert lab["J-r"] == "high"


def test_deterministic_byte_equal():
    a = json.dumps(truth_from_consequences(_log(), _pairs()), sort_keys=True)
    b = json.dumps(truth_from_consequences(_log(), _pairs()), sort_keys=True)
    assert a == b
