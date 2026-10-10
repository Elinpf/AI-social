"""证据包构建器测试（T42）。

验证：四类报告 JSON+Markdown、gate.txt、summary.json、README.md 全部落盘；
摘要字段齐全；metrics 字节相等；门禁（含 G6）纳入。
"""

import json

from obs.evidence import build_evidence
from obs.golden import compute_baseline
from obs.testsupport import build_log


def _life_like_log(rounds=24, seed=42, agents=("A000", "A001", "A002")):
    lb = build_log(seed=seed, agents=agents)
    for r in range(rounds):
        if r % 12 == 0:
            lb.add(r, 35, "SYSTEM", "TIME_MARK", {"round": r})
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


def _write(path, recs):
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            f.write("\n")
    return path


def test_build_evidence_writes_all_files(tmp_path):
    log_p = _write(tmp_path / "run.jsonl", _life_like_log())
    out = tmp_path / "evidence"
    summary = build_evidence(log_p, out, baseline=None,
                             notes=["N=20 待主干恢复后补"])
    for name in ("metrics.json", "metrics.md", "census_report.json", "census_report.md",
                 "emergence_report.json", "emergence_report.md",
                 "wellbeing_report.json", "wellbeing_report.md",
                 "gate.txt", "summary.json", "README.md"):
        assert (out / name).exists(), name
    assert summary["n_events"] > 0
    assert summary["metrics_bitwise_equal"] is True
    assert summary["chain_ok"] is True
    # README 含重现命令
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "python -m orchestration run" in readme
    assert "python -m obs evidence" in readme
    # 备注落到 README
    assert "N=20 待主干恢复后补" in readme


def test_build_evidence_includes_g6_when_baseline_given(tmp_path):
    recs = _life_like_log()
    baseline = compute_baseline(recs, "tmp_life")
    log_p = _write(tmp_path / "run.jsonl", recs)
    out = tmp_path / "ev"
    build_evidence(log_p, out, baseline=baseline)
    gate_txt = (out / "gate.txt").read_text(encoding="utf-8")
    assert "distribution_regression" in gate_txt
    assert "GATE PASS" in gate_txt


def test_evidence_reports_byte_equal(tmp_path):
    log_p = _write(tmp_path / "run.jsonl", _life_like_log())
    out1, out2 = tmp_path / "e1", tmp_path / "e2"
    build_evidence(log_p, out1, baseline=None)
    build_evidence(log_p, out2, baseline=None)
    for name in ("metrics.json", "census_report.json", "emergence_report.json",
                 "wellbeing_report.json"):
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes(), name
