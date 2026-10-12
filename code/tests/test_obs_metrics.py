"""观测层指标测试：20 回合日志 → 全量指标 + 字节复现 + llm_calls==0。

验收①「对内核 20 回合日志能算出全部指标并输出报告」
验收②「同一日志两次指标字节相等」

说明：内核（engine.kernel/runner）由 kernel-dev 并行重构中；本测试优先使用
真实内核日志，若内核当前不可运行则回退到与其**同格式**的「内核外壳」合成日志
（`obs.testsupport.kernel_shell_log`，仅依赖稳定的 `engine.ledger` 哈希链契约），
以保证观测层交付始终可验证。真实内核日志的专用测试见
`test_kernel_runner_log_if_available`。
"""

import json

import pytest

from obs import metrics, emergence_report, wellbeing_report, to_canonical, gate
from obs.econ import econ_metrics
from obs.reader import ReadOnlyLog
from obs.runtime import llm_calls, note_llm_call, reset_llm_calls
from obs.testsupport import kernel_shell_log


def _try_kernel(rounds=20, seed=12345):
    try:
        from engine.runner import run
        res = run(seed=seed, rounds=rounds)
        recs = res["records"]
        if recs and any(r["type"] == "TURN_SEAL" for r in recs):
            return recs
    except Exception:
        pass
    return None


def kernel_log(rounds=20, seed=12345):
    return _try_kernel(rounds, seed) or kernel_shell_log(rounds, seed)


def test_metrics_on_kernel_20_rounds_all_namespaces():
    recs = kernel_log()
    snap = metrics(recs)
    m = snap["metrics"]
    for ns in ("econ", "lifecycle", "life", "emergence", "emergence_soft",
               "wellbeing", "wellbeing_soft"):
        assert ns in m, ns
    # D 类核心指标：llm_judged_metric_count == 0
    assert m["emergence"]["llm_judged_metric_count"] == 0
    assert m["wellbeing"]["llm_judged_metric_count"] == 0


def test_metrics_bitwise_equal_twice():
    recs = kernel_log()
    a = to_canonical(metrics(recs))
    b = to_canonical(metrics(recs))
    assert a == b
    assert json.loads(a)  # 合法 JSON


def test_reports_render_on_kernel_log():
    recs = kernel_log()
    emg = emergence_report(recs)
    wb = wellbeing_report(recs)
    assert emg["report"] == "emergence"
    assert len(emg["semantic_hits"]) == 20
    assert wb["report"] == "wellbeing"
    assert "summary" in wb["wellbeing"]
    # 两个报告均字节可复现
    assert to_canonical(emergence_report(recs)) == to_canonical(emergence_report(recs))
    assert to_canonical(wellbeing_report(recs)) == to_canonical(wellbeing_report(recs))


def test_llm_calls_zero_during_metrics():
    recs = kernel_log()
    reset_llm_calls()
    metrics(recs)
    assert llm_calls() == 0
    # 即便外部“接线”了 LLM 计数，观测计算也不改它
    reset_llm_calls()
    note_llm_call()
    before = llm_calls()
    metrics(recs)
    assert llm_calls() == before


def test_econ_metrics_matches_kernel_state():
    """K 类经济口径与内核 state 对拍（防口径漂移）。内核不可用时以折叠自洽校验。"""
    recs = _try_kernel(10, 7)
    if recs is not None:
        from engine.runner import run
        from engine.state import money_total
        res = run(seed=7, rounds=10)
        eco = econ_metrics(res["records"])
        st = res["final_state"]
        assert eco["money_supply_final"] == money_total(st)
        assert eco["money_minted_total"] == st.money_minted_total
        assert eco["money_burned_total"] == st.money_burned_total
    else:
        assert econ_metrics(kernel_shell_log(10, 7))["conservation_ok"] is True


def test_obs_gate_on_kernel_log():
    recs = kernel_log()
    res = gate.run_gates(recs)
    assert res["ok"] is True
    names = {g["name"] for g in res["gates"]}
    assert {"llm_calls_zero", "money_conservation"} <= names          # must 级
    diag = {d["name"] for d in res["diagnostics"]}
    assert {"metrics_bitwise_equal", "census_bitwise_equal"} <= diag  # G2a/G2b 已降诊断（Fork B）


def test_readonly_log_verifies_chain():
    recs = kernel_log()
    log = ReadOnlyLog(recs)
    assert log.chain_ok is True
    assert log.seed() == 12345


@pytest.mark.skipif(_try_kernel() is None,
                    reason="内核（engine.kernel/runner）重构中，暂不可运行")
def test_kernel_runner_log_if_available():
    recs = _try_kernel()
    assert recs is not None
    assert sum(1 for r in recs if r["type"] == "TURN_SEAL") == 20
    assert to_canonical(metrics(recs)) == to_canonical(metrics(recs))
