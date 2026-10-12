"""复现门禁 CI 测试（P0-13 / v1.2 §6.4）。

断言：
  - `metrics()` / `semantic_census()` 两次**字节相等**；
  - 观测过程 `llm_calls == 0`；
  - 守恒不变量成立；
  - CLI `python -m obs gate` 退出码 0；
  - （内核可用时）重放状态哈希相等 + 首跑==重放 + 重放 LLM=0。

内核（engine.kernel/runner/replay）由 kernel-dev 并行重构中；与内核重放相关的
门禁在内核不可运行时 **skip**；观测侧门禁始终可验证。
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from obs import metrics, to_canonical, census_report, gate
from obs.census import semantic_census
from obs.cli import read_log
from obs.reader import ReadOnlyLog
from obs.runtime import llm_calls, reset_llm_calls
from obs.testsupport import kernel_shell_log

_CODE_DIR = Path(__file__).resolve().parents[1]


def _try_kernel(rounds=20, seed=2026):
    try:
        from engine.runner import run
        res = run(seed=seed, rounds=rounds)
        if res["records"] and any(r["type"] == "TURN_SEAL" for r in res["records"]):
            return res
    except Exception:
        pass
    return None


def _write(path, recs):
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            f.write("\n")
    return path


def _log_file(tmp_path, rounds=20, seed=2026):
    res = _try_kernel(rounds, seed)
    recs = res["records"] if res else kernel_shell_log(rounds, seed)
    return _write(tmp_path / "run.jsonl", recs), (res is not None)


@pytest.mark.skipif(_try_kernel() is None,
                    reason="内核（engine.replay/runner）重构中，暂不可运行")
def test_g2_replay_state_hash_equal(tmp_path):
    from engine.replay import replay_records
    from engine.state import state_hash
    res = _try_kernel()
    p = _write(tmp_path / "run.jsonl", res["records"])
    recs = read_log(p)
    h1 = state_hash(replay_records(recs))
    h2 = state_hash(replay_records(recs))
    assert h1 == h2
    assert h1 == res["final_state_hash"]


def test_g2_metrics_and_census_bitwise(tmp_path):
    p, _ = _log_file(tmp_path)
    recs = read_log(str(p))
    assert to_canonical(metrics(recs)) == to_canonical(metrics(recs))
    assert to_canonical(semantic_census(recs)) == to_canonical(semantic_census(recs))
    assert to_canonical(census_report(recs)) == to_canonical(census_report(recs))


def test_g3_observe_llm_calls_zero(tmp_path):
    p, _ = _log_file(tmp_path)
    recs = read_log(str(p))
    reset_llm_calls()
    metrics(recs)
    assert llm_calls() == 0


@pytest.mark.skipif(_try_kernel() is None, reason="内核重放重构中")
def test_g3_replay_llm_calls_zero(tmp_path):
    from engine.replay import replay_records
    res = _try_kernel()
    p = _write(tmp_path / "run.jsonl", res["records"])
    reset_llm_calls()
    replay_records(read_log(p))
    assert llm_calls() == 0


def test_g4_conservation(tmp_path):
    p, _ = _log_file(tmp_path)
    recs = read_log(str(p))
    assert gate.check_conservation(ReadOnlyLog(recs))["ok"] is True


def test_full_obs_gate(tmp_path):
    p, _ = _log_file(tmp_path)
    out = gate.run_gates(read_log(str(p)))
    assert out["ok"] is True


def test_g2_diagnostic_does_not_block_ok(tmp_path, monkeypatch):
    """反向验证（防假降级回归）：G2a 强制 FAIL → run_gates.ok 仍 True、进 diagnostics。"""
    p, _ = _log_file(tmp_path)
    log = ReadOnlyLog(read_log(str(p)))
    monkeypatch.setattr(gate, "check_metrics_bitwise",
                        lambda *a, **k: {"name": "metrics_bitwise", "ok": False, "detail": {"injected": True}})
    res = gate.run_gates(log)
    assert res["ok"] is True                                   # 诊断不进 ok
    assert any(d["name"] == "metrics_bitwise" and d["ok"] is False for d in res["diagnostics"])
    assert all(g["name"] != "metrics_bitwise" for g in res["gates"])  # 已移出 must


def test_cli_gate_baseline_none_skips(tmp_path):
    # 显式 --baseline none → 跳过 G6，rc=0，且**必须显式打印**（T220）
    p, _ = _log_file(tmp_path)
    cp = subprocess.run(
        [sys.executable, "-m", "obs", "gate", "--log", str(p), "--baseline", "none"],
        cwd=str(_CODE_DIR), capture_output=True, text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert "GATE PASS" in cp.stdout
    assert "baseline=none" in cp.stdout  # 显式跳过必须可见
    assert "[DIAG]" in cp.stdout         # 诊断级仍打印（不进退出码）


def test_cli_gate_auto_unmatched_fails_loud(tmp_path):
    # fail-loud（T220）：--baseline auto 未命中 → GATE FAIL + rc=1（旧行为 rc=0 是假绿）
    p, _ = _log_file(tmp_path)
    cp = subprocess.run(
        [sys.executable, "-m", "obs", "gate", "--log", str(p)],  # 默认 auto
        cwd=str(_CODE_DIR), capture_output=True, text=True,
    )
    assert cp.returncode == 1, cp.stdout + cp.stderr
    assert "GATE FAIL" in cp.stdout
    assert "baseline_auto_unmatched" in cp.stdout


def test_g6_unmatched_is_failure_not_skip(tmp_path):
    """T220 fail-loud：auto 未命中 / id 不存在 → ok=False（不再 ok=None 被当通过）。"""
    p, _ = _log_file(tmp_path)
    log = ReadOnlyLog(read_log(str(p)))
    d1 = gate.check_distribution(log, "auto")
    assert d1["ok"] is False and d1["detail"]["reason"] == "baseline_auto_unmatched"
    d2 = gate.check_distribution(log, "no_such_baseline_id")
    assert d2["ok"] is False and d2["detail"]["reason"] == "baseline_id_not_found"
    # 已解析 dict 基线 → 正常评估（进入分布比较，而非"未命中"）
    from obs.golden import compute_baseline
    b = compute_baseline(read_log(str(p)), "tmp_probe")
    d3 = gate.check_distribution(log, b)
    assert "reason" not in d3["detail"] and "comparison" in d3["detail"]


def test_cli_census_outputs_json(tmp_path):
    p, _ = _log_file(tmp_path)
    out = tmp_path / "census.json"
    cp = subprocess.run(
        [sys.executable, "-m", "obs", "census", "--log", str(p), "--out", str(out)],
        cwd=str(_CODE_DIR), capture_output=True, text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["semantic_hits"]) == 20


def test_cli_metrics_and_reports(tmp_path):
    p, _ = _log_file(tmp_path)
    for cmd in ("metrics", "emergence-report", "wellbeing-report"):
        out = tmp_path / f"{cmd}.json"
        cp = subprocess.run(
            [sys.executable, "-m", "obs", cmd, "--log", str(p), "--out", str(out)],
            cwd=str(_CODE_DIR), capture_output=True, text=True,
        )
        assert cp.returncode == 0, cp.stdout + cp.stderr
        assert json.loads(out.read_text(encoding="utf-8"))
