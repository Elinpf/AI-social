"""T91：apply_production hook 测试（商品族事件）。

若内核尚未注册 `PRODUCE` 等事件类型（kernel-dev 接线中），本模块整体 skip；
注册后自动生效。
"""

from __future__ import annotations

import pytest

from engine.events import EVENT_TYPES, spec
from engine.hooks.production import apply_production
from engine.ledger import Ledger
from engine.replay import apply_event
from engine.rng import Ctx
from engine.state import initial_state

pytestmark = pytest.mark.skipif(
    "PRODUCE" not in EVENT_TYPES,
    reason="商品族事件类型未注册（等 kernel-dev 接线）",
)


def _cfg(**over):
    from engine.runner import default_config
    cfg = default_config()
    cfg["production"] = over
    return cfg


def _state(agents=("A",), endow=10000):
    st = initial_state(1)
    led = Ledger()

    def ap(ev):
        rec = led.append_spec(ev)
        apply_event(st, rec)
        return rec

    total = 0
    for a in agents:
        ap(spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": a, "birth_round": 0}))
        ap(spec(0, 0, "SYSTEM", "INIT_ENDOW", {"agent_id": a, "amount": endow}))
        total += endow
    if total:
        ap(spec(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": total, "reason": "genesis"}))
    return st, led


def _inject_activity(st, seq, round_no, aid, activity_type, place="farmland"):
    st.event_index[seq] = {"seq": seq, "round": round_no, "type": "ACTIVITY_COMPLETED",
                           "actor": aid, "phase": 35,
                           "payload": {"agent_id": aid, "activity_type": activity_type,
                                       "place": place}}


def _by(specs, t):
    return [s for s in specs if s.type == t]


def test_no_labor_activity_no_events():
    st, led = _state()
    outs = apply_production(st, 1, Ctx(1, _cfg(), 1, 4))
    assert outs == []


def test_work_produces_food_and_material():
    st, led = _state()
    _inject_activity(st, 100, 1, "A", "work")
    outs = apply_production(st, 1, Ctx(1, _cfg(), 1, 4))
    prods = {s.payload["good_id"]: s.payload for s in _by(outs, "PRODUCE")}
    assert "food" in prods and prods["food"]["qty"] > 0
    assert "material" in prods and prods["material"]["qty"] > 0
    for s in _by(outs, "PRODUCE"):
        for k in ("agent_id", "good_id", "qty", "place", "recipe", "skill_level"):
            assert k in s.payload
    # 生存消费 food≥1
    eats = [s for s in _by(outs, "CONSUME") if s.payload.get("purpose") == "eat"]
    assert eats and eats[0].payload["qty"] >= 1000   # milli 单位（1 单位）


def test_tool_production_consumes_material():
    st, led = _state()
    # 预置 material 作为投入
    st.inventory.setdefault("A", {})["material"] = 5000   # milli 单位（=5 单位）
    _inject_activity(st, 101, 1, "A", "skill_practice", place="workshop")
    outs = apply_production(st, 1, Ctx(1, _cfg(), 1, 4))
    inputs = [s for s in _by(outs, "CONSUME") if s.payload.get("purpose") == "input"]
    assert inputs and inputs[0].payload["good_id"] == "material"
    assert _by(outs, "PRODUCE")  # 至少产出 tool


def test_depreciation_and_overflow():
    st, led = _state()
    st.inventory.setdefault("A", {})["tool"] = 10000      # milli 单位（=10 单位）
    _inject_activity(st, 102, 1, "A", "work")
    outs = apply_production(st, 1, Ctx(1, _cfg(depreciate_bp=200), 1, 4))
    dep = _by(outs, "DEPRECIATE")
    assert dep and dep[0].payload["asset_id"] == "tool" and dep[0].payload["delta_mu"] == 200
    # cap=1 → food 溢出
    st2, _ = _state()
    _inject_activity(st2, 103, 1, "A", "work")
    outs2 = apply_production(st2, 1, Ctx(1, _cfg(cap_milli=1), 1, 4))
    # work 先产 food(qty=2) 但 cap=1 → 溢出 1
    assert _by(outs2, "PRODUCE_OVERFLOW")


def test_deterministic_same_inputs_same_events():
    st1, _ = _state()
    st2, _ = _state()
    _inject_activity(st1, 200, 3, "A", "work")
    _inject_activity(st2, 200, 3, "A", "work")
    a = apply_production(st1, 3, Ctx(7, _cfg(), 3, 4))
    b = apply_production(st2, 3, Ctx(7, _cfg(), 3, 4))
    ja = [(s.type, tuple(sorted(s.payload.items()))) for s in a]
    jb = [(s.type, tuple(sorted(s.payload.items()))) for s in b]
    assert ja == jb
