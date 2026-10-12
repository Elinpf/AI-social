"""T278：SERVICE_DELIVERED 最小切片测试（解 t139 矛盾）。

覆盖：① socialize 改发 SERVICE_DELIVERED（不再 PRODUCE{service}、不入库存）；
② inventory-neutral 折叠（重放不改库存）；③ 开关消融（OFF→DROPPED{service_disabled}）；
④ 可见性 participants_only 含 counterparty（受方可见）；⑤ t139 矛盾消解（前后对比）。
"""

from __future__ import annotations

from collections import Counter

from engine.events import EVENT_TYPES, spec
from engine.hooks.production import apply_production
from engine.ledger import Ledger
from engine.replay import apply_event
from engine.rng import Ctx
from engine.state import initial_state, state_hash


def _cfg(**over):
    from engine.runner import default_config
    cfg = default_config()
    if over:
        cfg.setdefault("service_delivered", {}).update(over)
    return cfg


def _state(agents=("A", "B")):
    st = initial_state(1)
    led = Ledger()

    def ap(ev):
        rec = led.append_spec(ev)
        apply_event(st, rec)
        return rec

    total = 0
    for a in agents:
        ap(spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": a, "birth_round": 0}))
        ap(spec(0, 0, "SYSTEM", "INIT_ENDOW", {"agent_id": a, "amount": 10000}))
        total += 10000
    ap(spec(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": total, "reason": "genesis"}))
    return st, led, ap


def _socialize(st, seq=1, rd=1):
    st.event_index[seq] = {"seq": seq, "round": rd, "type": "ACTIVITY_COMPLETED", "phase": 35,
                           "actor": "A",
                           "payload": {"agent_id": "A", "activity_type": "socialize",
                                       "place": "cafe", "participants": ["A", "B"]}}


def test_registered():
    assert "SERVICE_DELIVERED" in EVENT_TYPES


def test_socialize_emits_service_delivered_not_produce():
    st, led, ap = _state()
    _socialize(st)
    outs = apply_production(st, 1, Ctx(1, _cfg(), 1, 4))
    svc = [s for s in outs if s.type == "SERVICE_DELIVERED"]
    assert len(svc) == 1
    p = svc[0].payload
    assert p["agent_id"] == "A" and p["good_id"] == "service" and p["qty"] > 0
    assert p["counterparty"] == "B"                       # 参与者唯一对方
    assert "place" in p and "round" in p
    # 不再 PRODUCE{service}
    assert not [s for s in outs if s.type == "PRODUCE" and s.payload.get("good_id") == "service"]
    # 不入库存
    for s in outs:
        apply_event(st, led.append_spec(s))
    assert st.inventory.get("A", {}).get("service", 0) == 0


def test_service_delivered_is_inventory_neutral_on_replay():
    st, led, ap = _state()
    st.round = 1                                       # 固定 round（apply_event 会推进 round，非库存变化）
    before_hash = state_hash(st)
    inv_before = {k: dict(v) for k, v in st.inventory.items()}
    apply_event(st, led.append_spec(spec(1, 4, "A", "SERVICE_DELIVERED",
                                         {"agent_id": "A", "good_id": "service", "qty": 1000,
                                          "place": "cafe", "counterparty": "B", "round": 1})))
    assert st.inventory == inv_before                 # 库存不变
    assert state_hash(st) == before_hash              # 不改世界状态（noop 折叠）


def test_switch_off_emits_dropped_no_service_event():
    st, led, ap = _state()
    _socialize(st)
    outs = apply_production(st, 1, Ctx(1, _cfg(enabled=False), 1, 4))
    assert not [s for s in outs if s.type == "SERVICE_DELIVERED"]
    assert any(s.type == "DROPPED" and s.payload.get("flag") == "service_disabled" for s in outs)


def test_visibility_counterparty_visible():
    from contracts.visibility import visible
    assert visible("participants_only", "B", "A",
                   {"agent_id": "A", "counterparty": "B"}, "cafe") is True
    assert visible("participants_only", "C", "A",
                   {"agent_id": "A", "counterparty": "B"}, "cafe") is False


def test_t139_contradiction_resolved():
    """t139 矛盾消解：socialize 后 `service` 不进 inventory → life 不会再选它挂 sale → 无 good_not_transferable。"""
    st, led, ap = _state()
    _socialize(st)
    outs = apply_production(st, 1, Ctx(1, _cfg(), 1, 4))
    for s in outs:
        apply_event(st, led.append_spec(s))
    # 库存无 service（矛盾根因消除）
    assert st.inventory.get("A", {}).get("service", 0) == 0
    # 商品守恒：service 不进 ΣPRODUCE（PRODUCE 里无 service）
    c = Counter(r["type"] for r in led.records)
    assert all((r.get("payload") or {}).get("good_id") != "service"
               for r in led.records if r["type"] == "PRODUCE")
    assert c.get("SERVICE_DELIVERED", 0) >= 1
