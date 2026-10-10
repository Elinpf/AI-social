"""T60：E9（稀缺交易）判定口径 —— MARKET_TRADE.scarcity_index（08 §1.2-N）。

scarcity_index 为 0–100 整数；obs census E9 命中当且仅当
`scarcity_index is not None and value >= theta_scarce`（默认 θ=50）。
缺失=未知 → 保守不计。
"""

import copy

import pytest

from obs.census import semantic_census
from obs import to_canonical
from obs.runtime import llm_calls, reset_llm_calls
from obs.testsupport import build_log


def _log_with(trades):
    lb = build_log(seed=7, agents=("A000", "A001"))
    r = 1
    for payload in trades:
        lb.add(r, 35, "A001", "MARKET_TRADE", payload)
        r += 1
    return lb.records()


def _e9(records, **params_override):
    from obs.params import DEFAULT_PARAMS
    p = DEFAULT_PARAMS.emergence
    if params_override:
        import dataclasses
        p = dataclasses.replace(p, **params_override)
    census = semantic_census(records, p)
    return census["semantic_hits"]["E9_scarcity_buy"]


def test_e9_hits_when_at_or_above_threshold():
    recs = _log_with([{"buyer": "A001", "seller": "A000", "amount": 3, "scarcity_index": 90}])
    e9 = _e9(recs)
    assert e9["hit"] is True and e9["count"] == 1


def test_e9_threshold_boundary_inclusive():
    recs = _log_with([{"buyer": "A001", "seller": "A000", "amount": 3, "scarcity_index": 50}])
    assert _e9(recs)["hit"] is True           # == θ 计入
    recs2 = _log_with([{"buyer": "A001", "seller": "A000", "amount": 3, "scarcity_index": 49}])
    assert _e9(recs2)["hit"] is False         # < θ 不计


def test_e9_missing_index_not_counted():
    recs = _log_with([{"buyer": "A001", "seller": "A000", "amount": 3}])
    assert _e9(recs)["hit"] is False          # 缺失=未知 -> 保守不计


def test_e9_zero_index_not_counted():
    recs = _log_with([{"buyer": "A001", "seller": "A000", "amount": 3, "scarcity_index": 0}])
    assert _e9(recs)["hit"] is False          # 0=极充裕


def test_e9_param_override_changes_threshold():
    recs = _log_with([{"buyer": "A001", "seller": "A000", "amount": 3, "scarcity_index": 60}])
    assert _e9(recs)["hit"] is True
    assert _e9(recs, theta_scarce=80.0)["hit"] is False


def test_e9_deterministic_and_llm_zero():
    recs = _log_with([
        {"buyer": "A001", "seller": "A000", "amount": 3, "scarcity_index": 90},
        {"buyer": "A000", "seller": "A001", "amount": 4, "scarcity_index": 10},
    ])
    reset_llm_calls()
    a = to_canonical(semantic_census(copy.deepcopy(recs)))
    b = to_canonical(semantic_census(copy.deepcopy(recs)))
    assert a == b
    assert llm_calls() == 0
