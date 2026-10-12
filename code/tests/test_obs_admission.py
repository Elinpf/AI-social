"""T212：M2b 准入报告（合法率/token比/延迟比）测试。只读/确定性。"""

import json

from obs.admission import (
    admission_report, flag_rate, judge_method_rates, latency_p50, legal_rate, token_totals,
)


def test_judge_method_rates_and_inert():
    recs = [
        {"type": "LLM_JUDGMENT", "payload": {"dimension": "stance", "decision": "accept", "method": "discriminative"}},
        {"type": "LLM_JUDGMENT", "payload": {"dimension": "stance", "decision": "undecidable", "method": "rule"}},
        {"type": "LLM_JUDGMENT", "payload": {"dimension": "stance", "decision": "reject", "method": "discriminative"}},
        {"type": "LLM_JUDGMENT", "payload": {"dimension": "mentor_relation", "decision": "high", "method": "discriminative"}},
        {"type": "OTHER", "payload": {"dimension": "stance"}},  # 非 LLM_JUDGMENT，忽略
    ]
    r = judge_method_rates(recs)
    assert r["stance"]["n"] == 3
    assert r["stance"]["escape_rate"] == round(1 / 3, 6)      # 1 undecidable
    assert r["stance"]["fallback_rate"] == round(1 / 3, 6)    # 1 非 discriminative
    assert r["stance"]["inert"] is False
    assert r["mentor_relation"]["inert"] is True              # 登记但无调用点 → 单列


def test_flag_rate():
    recs = [{"escaped": True}, {"escaped": False}, {"escaped": True}, {}]
    assert flag_rate(recs, "escaped") == round(2 / 3, 6)  # {} 缺字段不计入
    assert flag_rate([], "escaped") is None


def _recs():
    return [
        {"A": {"legal": True, "tokens_in": 10, "tokens_out": 40, "reasoning_tokens": 5, "latency_s": 1.0},
         "B": {"legal": True, "tokens_in": 5, "tokens_out": 3, "reasoning_tokens": 0, "latency_s": 0.2}},
        {"A": {"legal": True, "tokens_in": 20, "tokens_out": 60, "reasoning_tokens": 8, "latency_s": 3.0},
         "B": {"legal": False, "tokens_in": 6, "tokens_out": 4, "reasoning_tokens": 0, "latency_s": 0.4}},
    ]


def test_legal_rate_and_tokens():
    recs = _recs()
    assert legal_rate(recs, "A") == 1.0
    assert legal_rate(recs, "B") == 0.5
    ta = token_totals(recs, "A")
    assert ta["tokens_total"] == 130 and ta["reasoning_tokens"] == 13
    tb = token_totals(recs, "B")
    assert tb["tokens_total"] == 18


def test_latency_p50_odd_even():
    assert latency_p50([{"B": {"latency_s": 1}}, {"B": {"latency_s": 3}}, {"B": {"latency_s": 2}}], "B") == 2.0
    assert latency_p50([{"B": {"latency_s": 1}}, {"B": {"latency_s": 3}}], "B") == 2.0


def test_admission_report_ratios_and_determinism():
    recs = _recs()
    rep = admission_report(recs)
    assert rep["legal_rate"]["B"] == 0.5
    assert rep["tokens"]["ratio_B_over_A"] == round(18 / 130, 6)
    assert rep["latency_p50_s"]["B"] == round((0.2 + 0.4) / 2, 6)
    a = json.dumps(rep, sort_keys=True)
    b = json.dumps(admission_report(_recs()), sort_keys=True)
    assert a == b


def test_missing_fields_yield_none():
    assert legal_rate([], "A") is None
    assert latency_p50([], "A") is None
    assert admission_report([])["tokens"]["ratio_B_over_A"] is None
