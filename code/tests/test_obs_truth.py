"""T212：确定性后果真值（obs/truth.py）测试。纯函数、确定性。"""

import json

from obs.testsupport import build_log
from obs.truth import truth_from_consequences


def _j(lb, jid, dim, decision, r, parties=("A000", "A001")):
    lb.add(r, 2, "SYSTEM", "LLM_JUDGMENT", {
        "judgment_id": jid, "dimension": dim, "parties": list(parties),
        "decision": decision, "created_round": r})


def _rc(lb, frm, to, dim, before, after, r):
    lb.add(r, 2, frm, "RELATION_CHANGE", {"from": frm, "to": to, "dim": dim,
                                          "before": before, "after": after})


def test_stance_accept_from_positive_change():
    lb = build_log(seed=1, agents=("A000", "A001"))
    _j(lb, "J1", "stance", "accept", 1)
    _rc(lb, "A000", "A001", "affinity", 0, 3, 2)
    e = truth_from_consequences(lb.records())["by_judgment_id"]["J1"]
    assert e["defined"] is True and e["true_label"] == "accept"


def test_stance_reject_from_negative_change():
    lb = build_log(seed=2, agents=("A000", "A001"))
    _j(lb, "J2", "stance", "reject", 1)
    _rc(lb, "A000", "A001", "trust", 5, 2, 2)
    e = truth_from_consequences(lb.records())["by_judgment_id"]["J2"]
    assert e["true_label"] == "reject"


def test_undefined_when_no_consequence():
    lb = build_log(seed=3, agents=("A000", "A001"))
    _j(lb, "J3", "stance", "accept", 1)
    e = truth_from_consequences(lb.records())["by_judgment_id"]["J3"]
    assert e["true_label"] is None and e["defined"] is False


def test_window_excludes_far_events():
    lb = build_log(seed=6, agents=("A000", "A001"))
    _j(lb, "J6", "stance", "accept", 1)
    _rc(lb, "A000", "A001", "affinity", 0, 3, 50)   # 窗口=12 之外
    assert truth_from_consequences(lb.records(), window=12)["by_judgment_id"]["J6"]["true_label"] is None


def test_affection_uncovered_coverage_counted():
    lb = build_log(seed=4, agents=("A000", "A001"))
    _j(lb, "J4", "affection", "high", 1)
    out = truth_from_consequences(lb.records())
    assert out["by_judgment_id"]["J4"]["true_label"] is None
    assert out["coverage"]["affection"] == {"n": 1, "defined": 0, "undefined": 1}


def test_rel_affinity_formed_threshold():
    lb = build_log(seed=5, agents=("A000", "A001"))
    _j(lb, "J5", "rel_affinity", "formed", 1)
    _rc(lb, "A000", "A001", "affinity", 0, 3, 2)
    out = truth_from_consequences(lb.records(), afford_thresh=3)
    assert out["by_judgment_id"]["J5"]["true_label"] == "formed"


def test_pair_is_order_insensitive():
    lb = build_log(seed=7, agents=("A000", "A001"))
    _j(lb, "J7", "stance", "accept", 1, parties=("A001", "A000"))
    _rc(lb, "A000", "A001", "affinity", 0, 2, 2)
    assert truth_from_consequences(lb.records())["by_judgment_id"]["J7"]["true_label"] == "accept"


def test_deterministic_byte_equal():
    lb = build_log(seed=8, agents=("A000", "A001"))
    _j(lb, "J8", "stance", "accept", 1)
    _rc(lb, "A000", "A001", "affinity", 0, 3, 2)
    recs = lb.records()
    a = json.dumps(truth_from_consequences(recs), ensure_ascii=False, sort_keys=True)
    b = json.dumps(truth_from_consequences(recs), ensure_ascii=False, sort_keys=True)
    assert a == b
