"""LLM 成本报告测试（obs.llmcost）。"""

import json

from obs.llmcost import llm_cost_from_records, freeze_cache_cost
from obs.testsupport import build_log


def test_llm_cost_from_records_groups_by_purpose():
    lb = build_log(seed=1)
    lb.add(1, 2, "A000", "LLM_CALL", {"purpose": "plan", "tokens_in": 10, "tokens_out": 20,
                                      "model": "m", "tier": "t1", "cached": False,
                                      "degraded": False})
    lb.add(2, 2, "A000", "LLM_CALL", {"purpose": "plan", "tokens_in": 5, "tokens_out": 7})
    lb.add(2, 2, "A001", "LLM_CALL", {"purpose": "dialogue", "tokens_in": 3, "tokens_out": 4})
    lb.add(3, 2, "A001", "LLM_JUDGMENT", {"judgment_id": "j1", "decision": "x",
                                          "frozen": True, "dimension": "satisfaction"})
    out = llm_cost_from_records(lb.records())["total"]
    assert out["calls"] == 3
    assert out["tokens_in"] == 18 and out["tokens_out"] == 31
    by = llm_cost_from_records(lb.records())["by_purpose"]
    assert by["plan"] == {"calls": 2, "tokens_in": 15, "tokens_out": 27,
                          "cached": 0, "degraded": 0, "thinking": 0}
    jd = llm_cost_from_records(lb.records())["llm_judgment_by_dimension"]
    assert jd == {"satisfaction": 1}


def test_freeze_cache_cost_reads_dir(tmp_path):
    d = tmp_path / "freeze_cache" / "responses"
    d.mkdir(parents=True)
    for i, (ti, to, prov, tier) in enumerate([(10, 20, "openai_compat", "t1"),
                                              (3, 4, "openai_compat", "t2"),
                                              (1, 1, "mock-1", "t0")]):
        (d / f"sha256:{i}.json").write_text(json.dumps(
            {"tokens_in": ti, "tokens_out": to, "provider": prov, "tier": tier,
             "thinking": tier == "t2", "degraded": False}), encoding="utf-8")
    out = freeze_cache_cost(tmp_path / "freeze_cache")
    assert out["total"]["responses_cached"] == 3
    assert out["total"]["tokens_in"] == 14 and out["total"]["tokens_out"] == 25
    assert out["by_provider"]["openai_compat"]["tokens_total"] == 37
    assert out["by_tier"]["t2"] == 1


def test_freeze_cache_cost_empty_dir(tmp_path):
    out = freeze_cache_cost(tmp_path / "nope")
    assert out["total"]["responses_cached"] == 0


def test_check_provider_guard_blocks_mock_contamination():
    """缓存污染防护：真 LLM 计划必须校验 provider，禁止 mock 混入。"""
    from obs.llmcost import check_provider, llm_cost_from_records
    # 全部真 provider → PASS
    lb = build_log(seed=1)
    lb.add(1, 2, "A000", "LLM_CALL", {"purpose": "plan", "provider": "openai_compat",
                                      "tokens_in": 1, "tokens_out": 2})
    cost = llm_cost_from_records(lb.records())
    assert check_provider(cost, "openai_compat")["ok"] is True
    # mock 混入 → FAIL
    lb.add(2, 2, "A000", "LLM_CALL", {"purpose": "plan", "provider": "mock",
                                      "tokens_in": 1, "tokens_out": 2})
    cost2 = llm_cost_from_records(lb.records())
    g = check_provider(cost2, "openai_compat")
    assert g["ok"] is False and any("mock" in p for p in g["problems"])
    # 预期 provider 计数为 0 → FAIL
    g2 = check_provider(cost2, "azure")
    assert g2["ok"] is False
