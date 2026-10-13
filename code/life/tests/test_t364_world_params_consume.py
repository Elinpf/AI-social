"""T364: life 侧消费 `world_params`（D3 口径②）—— 轻量单元（不起引擎/不跑 LLM）。

验证：经端口读、三档计数（纯观测）、`activity_weight` 有界影响 `_activity_for`、`dose=0/空 ⇒ 恒等`。
"""
from __future__ import annotations

from types import SimpleNamespace

from life.agent import LifeLayerAgent


def _agent(places, wp):
    a = LifeLayerAgent.__new__(LifeLayerAgent)
    a.agent_id = "P1"
    a._wp_reads = 0
    a._wp_nonempty = 0
    a._wp_changed_choice = 0
    a._wp_last = None
    a.places = places
    a._plan_slots = {}
    a.kernel = SimpleNamespace(world_params=lambda r: wp)
    a._current_goal = lambda: ""
    return a


def _places():
    return {"hall": {"open_slots": ["afternoon"], "affordances": ["socialize"]},
            "park": {"open_slots": ["afternoon"], "affordances": ["socialize"]},
            "residence": {"open_slots": ["afternoon"], "affordances": ["self_care"]}}


def _wv():
    return SimpleNamespace(round=3, location="residence",
                           time=SimpleNamespace(day_type="weekend", slot="afternoon",
                                                day_of_week=6))


def test_port_off_is_identity_and_counts_zero_nonempty():
    a = _agent(_places(), {"activity_weight": {}, "resource_factor_bp": {},
                           "market_scarcity_bp": {}, "active": []})
    a._read_world_params(_wv())
    atype, place = a._activity_for(_wv())
    assert a._wp_reads == 1 and a._wp_nonempty == 0 and a._wp_changed_choice == 0
    assert place == "plaza"          # weekend afternoon 基线 = socialize@park（无世界层影响）


def test_weighted_place_changes_choice_and_counts():
    a = _agent(_places(), {"activity_weight": {"hall": 40}, "resource_factor_bp": {},
                           "market_scarcity_bp": {}, "active": ["D-x-festival"]})
    a._read_world_params(_wv())
    atype, place = a._activity_for(_wv())
    assert a._wp_nonempty == 1 and a._wp_changed_choice == 1
    assert atype == "socialize" and place == "hall"   # 被吸引到高权重且合法的 hall


def test_weight_ignored_when_place_illegal_for_activity():
    a = _agent(_places(), {"activity_weight": {"residence": 99}, "resource_factor_bp": {},
                           "market_scarcity_bp": {}, "active": ["D-y"]})
    a._read_world_params(_wv())
    atype, place = a._activity_for(_wv())
    # residence 不 afford socialize ⇒ 不改变选择（有界）
    assert a._wp_changed_choice == 0 and place == "plaza"
