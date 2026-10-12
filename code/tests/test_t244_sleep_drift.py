"""T244: `_maybe_sleep_window` 两处接线（life/agent.py）。

1) `forget` 意图透传 `protected`/`protection_reason`（真装配下不再丢保护标记）；
2) `drift_events` 来源：由既有反思产出**有界**候选 —— 覆盖「抖动 vs 真漂移」的持久化门槛、
   情感门（无语义不发）、以及幅度夹紧（≤delta_max）。
"""
from __future__ import annotations

import types

from life.agent import LifeLayerAgent
from life.memory import MemoryNode


def _agent(nodes):
    a = LifeLayerAgent.__new__(LifeLayerAgent)
    a.agent_id = "P1"
    a._drift_streak = {}
    a.memory = types.SimpleNamespace(nodes={n.mem_id: n for n in nodes})
    # T323: 发射 PERSONA_DRIFT_CANDIDATE 需 kernel（stub 只需吞掉 intent）
    a.kernel = types.SimpleNamespace(
        submit_intent=lambda aid, intent: types.SimpleNamespace(ok=True))
    return a


def _mem(mid, text, imp=7, kind="reflection"):
    return MemoryNode(mem_id=mid, agent_id="P1", kind=kind, text=text, importance=imp,
                      day=0, slot="night", embed=[])


PARAMS = {"persona_drift": {"delta_max": 1, "min_windows": 2, "min_importance": 7}}


def test_drift_requires_persistence_not_single_window_jitter():
    a = _agent([_mem("M1", "我在这段旅程中感到成长")])
    assert a._reflection_drift_events(PARAMS, day=1, slot="night", window=1) == []   # 单窗 = 抖动，不发
    ev2 = a._reflection_drift_events(PARAMS, day=2, slot="night", window=2)          # 连续第 2 窗 = 真漂移
    assert len(ev2) == 1 and ev2[0]["dim"] in __import__("life.persona_drift", fromlist=["BIG5_DIMS"]).BIG5_DIMS
    assert ev2[0]["delta"] in (1, -1) and ev2[0]["cause_mem_id"] == "M1"
    assert a._reflection_drift_events(PARAMS, day=3, slot="night", window=3) == []   # 发出后清零 → 不连发


def test_drift_ignores_low_importance_and_contentless():
    a = _agent([_mem("M2", "我在这段旅程中感到成长", imp=6)])   # 低于门槛
    assert a._reflection_drift_events(PARAMS, day=1, slot="night", window=1) == []
    assert a._reflection_drift_events(PARAMS, day=2, slot="night", window=2) == []
    b = _agent([_mem("M3", "mock::deadbeef（insight 1）")])     # 无语义 → 不发
    assert b._reflection_drift_events(PARAMS, day=1, slot="night", window=1) == []
    assert b._reflection_drift_events(PARAMS, day=2, slot="night", window=2) == []


def test_drift_bounded_by_delta_max():
    p = {"persona_drift": {"delta_max": 1, "min_windows": 1, "min_importance": 7}}
    a = _agent([_mem("M4", "冲突与挫折")])                      # 负向
    ev = a._reflection_drift_events(p, day=1, slot="night", window=1)
    assert len(ev) == 1 and ev[0]["delta"] == -1               # |delta| == delta_max
