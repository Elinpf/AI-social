"""T221c: life 侧 M6 降级 gate（`llm_permit` / `should_skip_judgment`）。

口径：**默认关 = 行为不变**（llm_permit 缺省 True；critical-only 在 budget level<3 或
无 critical_dimensions 表时不跳）。跳过由**内核/adapter 侧**落可列 `DEGRADE`，life 只读布尔。
"""
from __future__ import annotations

import types

from life.agent import LifeLayerAgent
from life import degrade


class _WV:
    pass


def _agent(kernel):
    a = LifeLayerAgent.__new__(LifeLayerAgent)  # 只测 gate 方法，不跑主循环
    a.kernel = kernel
    return a


def test_llm_permit_default_true_when_absent():
    a = _agent(types.SimpleNamespace())
    assert a._llm_ok(_WV()) is True            # 无 llm_permit 属性 → 默认 True（行为不变）


def test_llm_permit_false_blocks_and_skips_judge():
    a = _agent(types.SimpleNamespace())
    wv = _WV()
    wv.llm_permit = False
    assert a._llm_ok(wv) is False
    assert a._judge_skip(wv, "weekly_focus", []) is True   # M4 未许可 → 一律跳


def test_judge_skip_uses_kernel_gate():
    a = _agent(types.SimpleNamespace(
        should_skip_judgment=lambda d, p: d != "weekly_focus"))
    assert a._judge_skip(_WV(), "weekly_focus", []) is False   # critical → 不跳
    assert a._judge_skip(_WV(), "rel_trust", []) is True       # 非 critical → 跳


def test_judge_skip_conservative_when_kernel_lacks_method():
    a = _agent(types.SimpleNamespace())        # 旧内核，无 gate
    assert a._judge_skip(_WV(), "rel_trust", []) is False      # 保守：不跳


def test_degrade_helper_missing_kernel_is_noop():
    assert degrade.should_skip_judgment(types.SimpleNamespace(), "rel_trust", []) is False


def test_degrade_helper_exception_is_conservative():
    class _Boom:
        def should_skip_judgment(self, d, p):
            raise RuntimeError("boom")
    assert degrade.should_skip_judgment(_Boom(), "rel_trust", []) is False  # 失败偏保守


def test_engine_gate_off_by_default_level0():
    # 真实内核 gate：budget level=0（默认）→ 不跳（即使维度非 critical）
    from engine import scheduling
    cfg = {"policy": {"llm_budget": {"critical_dimensions": ["weekly_focus"]}}}
    assert scheduling.should_skip_judgment("rel_trust", 0, cfg) is False
    assert scheduling.should_skip_judgment("rel_trust", 3, cfg) is True    # L3 才降级
    assert scheduling.should_skip_judgment("weekly_focus", 3, cfg) is False
