"""T231: 确定性 `GOAL_ABANDON{reason="stalled"}` 钩子（life L4）。

口径（Leader + engine/kernel 裁决）：**周 REVIEW 边界**时，`status=active` 且**本周
`progress` 增量为 0**（本周窗口内无 `GOAL_PROGRESS`）的目标 → 发 `GOAL_ABANDON`。
派生自既有确定性规则，不为凑事件强发；停滞周为 0 → 允许 0 事件。

覆盖：停滞→发；有推进→不发；已达成→不发；非周边界→不发；reason/可审计字段完整。
"""
from __future__ import annotations

from life import settlement as S

WEEK_ROUNDS = 84  # 7 天 * 4 slot * 3 round


class _Ctx:
    def derive_time(self, round_no: int) -> dict:
        return {"day": 0, "slot": "night", "day_type": "weekend"}

    def rng(self, stream_id, seq, n):  # not used by L4
        return [0] * n


def _state(goals, *, progress_events=()):
    return {
        "round": 83,
        "agents": {"P1": {"needs": {}, "goals": goals}},
        "event_index": {i: r for i, r in enumerate(progress_events)},
        "relations": {},
    }


def _abandons(evs):
    return [e for e in evs if e.type == "GOAL_ABANDON"]


def test_stalled_goal_is_abandoned_at_week_boundary():
    st = _state({"G-P1-0000": {"goal_id": "G-P1-0000", "kind": "mastery",
                               "status": "active", "progress": 0.0}})
    evs = S.apply_needs(st, WEEK_ROUNDS - 1, _Ctx())  # round 83 = 周末
    ab = _abandons(evs)
    assert len(ab) == 1
    p = ab[0].payload
    assert p["reason"] == "stalled" and p["goal_id"] == "G-P1-0000"
    assert p["progress_at_abandon"] == 0.0 and p["week"] == 0  # 可审计


def test_progressed_goal_not_abandoned():
    st = _state(
        {"G-P1-0000": {"goal_id": "G-P1-0000", "kind": "mastery",
                       "status": "active", "progress": 0.3}},
        progress_events=[{"type": "GOAL_PROGRESS", "round": 5, "seq": 1,
                          "payload": {"agent_id": "P1", "goal_id": "G-P1-0000",
                                      "before": 0.0, "after": 0.3}}],
    )
    assert _abandons(S.apply_needs(st, WEEK_ROUNDS - 1, _Ctx())) == []


def test_achieved_goal_not_abandoned():
    st = _state({"G-P1-0000": {"goal_id": "G-P1-0000", "kind": "mastery",
                               "status": "achieved", "progress": 1.0}})
    assert _abandons(S.apply_needs(st, WEEK_ROUNDS - 1, _Ctx())) == []


def test_prior_week_progress_does_not_count():
    # GOAL_PROGRESS 在上一周窗口内 → 本周仍判定停滞（增量=0）
    st = _state(
        {"G-P1-0000": {"goal_id": "G-P1-0000", "kind": "mastery",
                       "status": "active", "progress": 0.25}},
        progress_events=[{"type": "GOAL_PROGRESS", "round": -1, "seq": 1,
                          "payload": {"agent_id": "P1", "goal_id": "G-P1-0000"}}],
    )
    ab = _abandons(S.apply_needs(st, 2 * WEEK_ROUNDS - 1, _Ctx()))  # week 1 末
    # 上一周(round<84)的推进不计入本周(84..167) → 停滞
    assert len(ab) == 1 and ab[0].payload["week"] == 1


def test_no_abandon_off_boundary():
    st = _state({"G-P1-0000": {"goal_id": "G-P1-0000", "kind": "mastery",
                               "status": "active", "progress": 0.0}})
    assert _abandons(S.apply_needs(st, 10, _Ctx())) == []
