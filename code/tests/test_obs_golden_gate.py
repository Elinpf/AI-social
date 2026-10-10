"""G6 黄金基线 / 事件量-分布回归门禁测试。

背景（Leader 2026-10-10）：一次静默回归——`run --life` 跑完、
`chain_ok/replay_parity/conservation_ok` 全绿，但世界**停摆**（事件量骤降、
`SYSTEM_ERROR`>0、`MEMORY_WRITE`=0、`TIME_MARK`=1），既有门禁全部漏检。
本测试用**故意注入的坏日志**做正向验证，确认 G6 能捕获「跑完但停摆」。
"""

import json
from pathlib import Path

import pytest

from obs import gate, metrics, to_canonical
from obs.golden import (
    compute_baseline, expected_time_marks, auto_match, load_baselines,
)
from obs.reader import ReadOnlyLog
from obs.testsupport import build_log, kernel_shell_log

_V12 = Path(__file__).resolve().parents[2] / "v1.2"
_REF_N3 = _V12 / "e2e_n3_week.jsonl"


def _good_life_log(rounds=84, seed=42, agents=("A000", "A001", "A002")):
    """一份「正常运转」的合成 life 日志（含关键事件族 + 日边界锚点 + seal）。"""
    lb = build_log(seed=seed, agents=agents)
    for r in range(rounds):
        if r % 12 == 0:
            lb.add(r, 35, "SYSTEM", "TIME_MARK", {"round": r, "day": r // 12})
        for a in agents:
            lb.add(r, 35, a, "NEED_UPDATE", {"agent_id": a, "dim": "energy", "after": 50})
            lb.add(r, 35, a, "MEMORY_WRITE", {"agent_id": a, "mem_id": f"m{r}{a}",
                                              "importance": 5})
        if r % 4 == 0:
            lb.add(r, 35, "A000", "ACTIVITY_STARTED", {"agent_id": "A000",
                                                       "activity_type": "work"})
            lb.add(r, 35, "A000", "ACTIVITY_COMPLETED", {"agent_id": "A000",
                                                         "outcome": "done"})
        lb.add(r, 6, "SYSTEM", "TURN_SEAL", {"round": r})
    return lb.records()


def _stalled_log(rounds=84, seed=42, agents=("A000", "A001", "A002")):
    """「跑完但停摆」的坏日志：事件骤降、SYSTEM_ERROR>0、无关键族、TIME_MARK=1。"""
    lb = build_log(seed=seed, agents=agents)
    lb.add(0, 35, "SYSTEM", "TIME_MARK", {"round": 0})
    for r in range(rounds):
        lb.add(r, 6, "SYSTEM", "TURN_SEAL", {"round": r})
        lb.add(r, 6, "SYSTEM", "SYSTEM_ERROR", {"where": "x", "detail": "boom"})
    return lb.records()


def test_expected_time_marks_authoritative():
    # 84 回合 / 12 回合每日 = 7 个日边界（08 §1.2-A：每跨日一条，非每回合一条）
    assert expected_time_marks(84) == 7
    assert expected_time_marks(6) == 1


def test_g6_passes_on_good_log():
    good = _good_life_log()
    baseline = compute_baseline(good, "synthetic_good")
    res = gate.check_distribution(ReadOnlyLog(good), baseline)
    assert res["ok"] is True, res["detail"]["problems"]
    assert "comparison" in res["detail"]


def test_g6_catches_stalled_regression():
    good = _good_life_log()
    baseline = compute_baseline(good, "synthetic_good")
    bad = _stalled_log()
    res = gate.check_distribution(ReadOnlyLog(bad), baseline)
    assert res["ok"] is False
    probs = " | ".join(res["detail"]["problems"])
    assert "事件总量" in probs
    assert "SYSTEM_ERROR" in probs
    assert "TIME_MARK" in probs
    assert "MEMORY_WRITE" in probs
    # 对照表非空
    assert res["detail"]["comparison"]


def test_g6_time_mark_only_one_is_flagged_earliest_signal():
    """TIME_MARK=1（连一次日边界都没跨过）必须被判 FAIL。"""
    good = _good_life_log()
    baseline = compute_baseline(good, "synthetic_good")
    bad = _stalled_log()
    res = gate.check_distribution(ReadOnlyLog(bad), baseline)
    assert any("TIME_MARK" in p for p in res["detail"]["problems"])


def test_g6_in_run_gates_and_auto_match():
    good = _good_life_log()
    baseline = compute_baseline(good, "synthetic_good")
    # auto_match 按 (N, rounds, seed)
    assert auto_match(ReadOnlyLog(good), {"synthetic_good": baseline}) is not None
    res = gate.run_gates(good, baseline=baseline)
    names = {g["name"] for g in res["gates"]}
    assert "distribution_regression" in names
    assert res["ok"] is True


def test_g2_and_g6_share_same_golden_log():
    """G2（字节相等）与 G6（分布）在同一份黄金日志上联合通过。"""
    good = _good_life_log()
    baseline = compute_baseline(good, "synthetic_good")
    log = ReadOnlyLog(good)
    assert to_canonical(metrics(log)) == to_canonical(metrics(log))
    assert gate.check_metrics_bitwise(log)["ok"] is True
    assert gate.check_distribution(log, baseline)["ok"] is True


@pytest.mark.skipif(not _REF_N3.exists(), reason="T34 参照日志不存在")
def test_g6_on_frozen_baseline_reference_log():
    """对 T34 真实参照日志：G6 用冻结基线判 PASS；并验证分布列。"""
    from obs.cli import read_log
    baselines = load_baselines()
    assert "n3_week_seed42" in baselines
    recs = read_log(str(_REF_N3))
    res = gate.check_distribution(ReadOnlyLog(recs), baselines["n3_week_seed42"])
    assert res["ok"] is True, res["detail"]["problems"]
    # 真实参照日志 TIME_MARK=7（权威口径），基线一致
    assert res["detail"]["time_mark_actual"] == 7


def test_g6_growth_passes_collapse_fails():
    """单调友好：事件量增长应通过，塌陷才失败。"""
    good = _good_life_log()
    baseline = compute_baseline(good, "synthetic_good")
    # 造一份事件量约为基线 2× 的“更丰富”日志 → 应 PASS
    bigger = list(good)
    for r in good:
        if r["type"] == "MEMORY_WRITE":
            nr = dict(r); nr["seq"] = -1  # 仅用于计数比较，check_distribution 只看 type
            bigger.append(nr)
    res = gate.check_distribution(ReadOnlyLog(bigger), baseline)
    assert res["ok"] is True, res["detail"]["problems"]
    # 塌陷（坏日志）→ FAIL
    res2 = gate.check_distribution(ReadOnlyLog(_stalled_log()), baseline)
    assert res2["ok"] is False


def test_g6_detail_carries_baseline_feature_set():
    good = _good_life_log()
    baseline = compute_baseline(good, "fs_test", feature_set="T39-life-full")
    bad = _stalled_log()
    res = gate.check_distribution(ReadOnlyLog(bad), baseline)
    assert res["detail"]["baseline_feature_set"] == "T39-life-full"
    assert res["detail"]["baseline_note"]


def test_g7_schema_conformance_pass_on_clean_log():
    good = _good_life_log()
    res = gate.check_schema_conformance(ReadOnlyLog(good))
    assert res["ok"] is True


def test_g7_schema_conformance_fail_with_repro():
    """缺字段 → 阻塞 FAIL，且给出最小复现（seq/type/field + 行号 + 命令）。"""
    lb = build_log(seed=1)
    lb.add(3, 2, "A000", "GOAL_SET", {"agent_id": "A000", "goals": [{"goal_id": "G-1"}]})
    log = ReadOnlyLog(lb.records(), verify=False)
    res = gate.check_schema_conformance(log)
    assert res["ok"] is False
    assert res["detail"]["first"]["type"] == "GOAL_SET"
    assert res["detail"]["first"]["field"] == "goal_id"
    repro = " | ".join(res["detail"]["repro"])
    assert "GOAL_SET" in repro and "缺 goal_id" in repro
    assert "python -m obs census" in repro and "sed -n" in repro


def test_g7_in_run_gates_blocks_on_anomaly():
    lb = build_log(seed=1)
    lb.add(3, 2, "A000", "GOAL_SET", {"agent_id": "A000", "goals": [{"goal_id": "G-1"}]})
    log = ReadOnlyLog(lb.records(), verify=False)
    out = gate.run_gates(log)
    assert out["ok"] is False
    assert any(g["name"] == "schema_conformance" and g["ok"] is False for g in out["gates"])
    # 可用 schema_strict=False 单独关闭该门禁（供正交诊断）
    out2 = gate.run_gates(log, schema_strict=False)
    assert all(g["name"] != "schema_conformance" for g in out2["gates"])
