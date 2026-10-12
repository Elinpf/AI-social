"""T203/T212：校准度量（ECE / 可靠性图 / 分层命中率 / 分差分析）测试。纯函数、确定性。"""

import json

import pytest

from obs.calibration import (
    agreement_rate, calibration_report, expected_calibration_error,
    multiclass_brier, multiclass_logloss, multiclass_report,
    reliability_diagram, score_gap_analysis, tiered_hit_rate,
)


def test_ece_zero_when_perfectly_calibrated():
    # 半数样本 conf=0.5 且正确、半数 conf=0.5 且错 → 每档 acc==conf → ECE=0
    conf = [0.5] * 10
    correct = [True] * 5 + [False] * 5
    assert expected_calibration_error(conf, correct) == 0.0


def test_ece_large_when_overconfident():
    # 全 conf=0.9、全错 → ECE=0.9
    assert expected_calibration_error([0.9] * 8, [False] * 8) == 0.9


def test_ece_empty_is_zero_not_one():
    assert expected_calibration_error([], []) == 0.0


def test_reliability_diagram_bin_edges():
    # c=0.0 → 第 0 档；c=1.0 → 最后一档（含 1.0）
    d = reliability_diagram([0.0, 1.0], [True, False], n_bins=10)
    assert d[0]["count"] == 1 and d[0]["hi"] == 0.1
    assert d[-1]["count"] == 1 and d[-1]["lo"] == 0.9
    # 空档 avg_conf/acc 为 None
    assert d[5]["count"] == 0 and d[5]["avg_conf"] is None and d[5]["acc"] is None


def test_tiered_monotonic_detection():
    # 低档 0/4 正确、高档 4/4 正确 → 单调
    conf = [0.15] * 4 + [0.85] * 4
    correct = [False] * 4 + [True] * 4
    t = tiered_hit_rate(conf, correct)
    assert t["monotonic"] is True
    assert t["bottom_acc"] == 0.0 and t["top_acc"] == 1.0


def test_score_gap_auc_and_threshold():
    # 分差大的对、分差小的错 → AUC=1.0；阈值可分离
    gaps = [3.0, 2.0, 1.0, 0.5]
    correct = [True, True, False, False]
    g = score_gap_analysis(gaps, correct)
    assert g["auc"] == 1.0
    assert g["best_threshold"] == 2.0  # >=2 时准确率 1.0（同分取更小阈值）
    assert g["best_accuracy"] == 1.0


def test_score_gap_auc_direction():
    # 分差小反而更常正确 → AUC 应 < 0.5
    gaps = [0.1, 0.2, 3.0, 4.0]
    correct = [True, True, False, False]
    assert score_gap_analysis(gaps, correct)["auc"] == 0.0


def test_report_gate_allows_when_calibrated():
    conf = [0.5] * 10
    correct = [True] * 5 + [False] * 5
    rep = calibration_report(conf, correct)
    assert rep["ece"] <= 0.05 and rep["confidence_fallback_allowed"] is True
    assert rep["fallback_rule"] == "confidence"


def test_report_gate_denies_when_uncalibrated():
    # 全 conf=0.95 但只 10% 正确 → ECE 大、且非单调 → 禁用置信度回退
    conf = [0.95] * 10
    correct = [True] + [False] * 9
    rep = calibration_report(conf, correct)
    assert rep["ece"] > 0.05
    assert rep["confidence_fallback_allowed"] is False
    assert rep["fallback_rule"].startswith("rule:")


def test_report_score_gap_attached_and_length_guard():
    conf = [0.5] * 4
    correct = [True, True, False, False]
    rep = calibration_report(conf, correct, score_gaps=[3, 2, 1, 0])
    assert "score_gap" in rep and rep["score_gap"]["auc"] == 1.0
    with pytest.raises(ValueError):
        calibration_report(conf, correct, score_gaps=[1, 2])
    with pytest.raises(ValueError):
        calibration_report([0.5], [True, False])


def test_agreement_rate_and_not_calibration():
    # 一致率衡量"判别式 vs 生成式"等价性；与 correct(真值) 无关
    assert agreement_rate(["a", "b", "a"], ["a", "a", "a"]) == round(2 / 3, 6)
    assert agreement_rate([], []) == 0.0
    with pytest.raises(ValueError):
        agreement_rate(["a"], ["a", "b"])


def test_multiclass_brier_and_logloss():
    perfect = [{"true_label": "formed", "label_probs": {"formed": 1.0, "not_formed": 0.0}}]
    assert multiclass_brier(perfect) == 0.0
    assert multiclass_logloss(perfect) == 0.0
    worst = [{"true_label": "formed", "label_probs": {"formed": 0.0, "not_formed": 1.0}}]
    assert multiclass_brier(worst) == 2.0  # (0-1)^2+(1-0)^2
    assert multiclass_logloss(worst) > 10.0  # -ln(clip(0))
    # 跳过 true_label 或 probs 缺失
    rep = multiclass_report([{"true_label": None, "label_probs": {"a": 1.0}},
                             {"true_label": "a"}, {"true_label": "a", "label_probs": {"a": 1.0}}])
    assert rep["n"] == 1 and rep["brier"] == 0.0


def test_deterministic_byte_equal():
    conf = [0.2, 0.4, 0.6, 0.8, 0.9]
    correct = [False, False, True, True, True]
    a = json.dumps(calibration_report(conf, correct, score_gaps=[1, 2, 3, 4, 5]),
                   ensure_ascii=False, sort_keys=True)
    b = json.dumps(calibration_report(conf, correct, score_gaps=[1, 2, 3, 4, 5]),
                   ensure_ascii=False, sort_keys=True)
    assert a == b
