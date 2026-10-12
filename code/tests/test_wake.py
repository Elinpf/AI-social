"""T265：个体决策节拍（唤醒集 W1–W10 + DECIDE 门控）单元/集成测试。

覆盖：
- 开关默认 off → 行为不变、不发 WAKE/IDLE；
- 各触发器（W1 定时 / W2 消息 / W6 共处）确定性；
- 开: on 时发 WAKE/IDLE、重放一致、守恒、无未注册事件。
"""

from __future__ import annotations

from engine import wake
from engine.state import WorldState, new_agent_dict

_TI = {
    "ROUNDS_PER_SLOT": 3,
    "SLOTS_PER_DAY": ["morning", "afternoon", "evening", "night"],
    "DAYS_PER_WEEK": 7,
    "DAY_TYPES": ["workday"] * 5 + ["weekend"] * 2,
    "TIME_UNIT": 1000,
}


def _cfg(enabled=True, triggers=None, cadence=12):
    tr = {w: True for w in wake.W_REASONS}
    if triggers:
        tr.update(triggers)
    return {"time_config": _TI, "policy": {"wake": {
        "enabled": enabled, "base_cadence_rounds": cadence, "triggers": tr}}}


def _state(agents=("A", "B", "C"), loc="plaza"):
    s = WorldState(seed=1)
    for a in agents:
        s.agents[a] = new_agent_dict(a, location=loc)
    return s


def test_disabled_returns_empty_and_config():
    s = _state()
    assert wake.enabled(_cfg(enabled=False)) is False
    assert wake.compute_wake_set(s, 0, _cfg(enabled=False)) == {}


def test_w1_cadence_wakes_all_when_never_woken():
    s = _state()
    # round=1：非周相位起点（避免 W9 抢主因）且无历史 → W1 定时兜底
    ws = wake.compute_wake_set(s, 1, _cfg(cadence=12))
    assert set(ws) == {"A", "B", "C"}
    assert ws["A"]["reason"] == "W1"
    assert ws["A"]["source_event_seq"] is None


def test_w9_week_phase_wakes_all_at_week_start():
    s = _state()
    ws = wake.compute_wake_set(s, 0, _cfg())
    assert set(ws) == {"A", "B", "C"}
    assert ws["A"]["reason"] == "W9"


def test_w2_dm_wakes_only_recipient():
    s = _state()
    s.event_index[1] = {"seq": 1, "round": 0, "type": "MSG_DM", "actor": "A",
                        "payload": {"from": "A", "to": "B"}}
    ws = wake.compute_wake_set(s, 1, _cfg(triggers={"W1": False}))
    assert "B" in ws and ws["B"]["reason"] == "W2"
    assert ws["B"]["source_event_seq"] == 1
    assert "C" not in ws


def test_w6_cohabit_wakes_others_at_place_not_actor():
    s = _state(("A", "B", "C"))
    s.event_index[2] = {"seq": 2, "round": 0, "type": "PLACE_ARRIVED", "actor": "A",
                        "payload": {"agent_id": "A", "place": "plaza"}}
    ws = wake.compute_wake_set(s, 1, _cfg(triggers={"W1": False}))
    assert set(ws) == {"B", "C"}
    assert ws["B"]["reason"] == "W6"


def test_priority_picks_highest():
    s = _state(("A", "B"))
    # B 同时收到 STATE_CHANGE(near_death)=W3 与 MSG_DM=W2 -> 主因取 W3
    s.event_index[1] = {"seq": 1, "round": 0, "type": "STATE_CHANGE", "actor": "SYSTEM",
                        "payload": {"agent_id": "B", "to": "near_death"}}
    s.event_index[2] = {"seq": 2, "round": 0, "type": "MSG_DM", "actor": "A",
                        "payload": {"from": "A", "to": "B"}}
    ws = wake.compute_wake_set(s, 1, _cfg(triggers={"W1": False}))
    assert ws["B"]["reason"] == "W3"
    assert "W2" in ws["B"]["all_reasons"]


# ---- 集成：开关 on/off 对照 ----

def _engine_with_steppers(enabled, only=None):
    from engine.kernel import Engine
    from engine.runner import default_config
    cfg = default_config()
    cfg["policy"]["wake"]["enabled"] = bool(enabled)
    if only is not None:
        tr = {w: False for w in wake.W_REASONS}
        tr[only] = True
        cfg["policy"]["wake"]["triggers"] = tr
    eng = Engine(1, cfg)
    eng.genesis({a: {"home_place": "plaza"} for a in ("A", "B", "C")})

    class _S:
        def __init__(self, aid):
            self.agent_id = aid
            self.n = 0

        def step(self):
            self.n += 1

    ss = [_S(a) for a in ("A", "B", "C")]
    eng.agent_steppers = ss
    return eng, ss


def test_gate_closed_when_no_trigger_fires():
    # 所有触发器关 → 无人唤醒 → 无人 step（门控生效）
    eng, ss = _engine_with_steppers(True, only="W2")  # round0 无 W2 事件
    eng.run_round(0)
    assert [s.n for s in ss] == [0, 0, 0]


def test_gate_open_when_w1_fires():
    eng, ss = _engine_with_steppers(True, only="W1")  # 无历史 → W1 兜底，round=1（非周相位）
    eng.run_round(1)
    assert [s.n for s in ss] == [1, 1, 1]


def test_gate_off_when_disabled_all_step():
    eng, ss = _engine_with_steppers(False)  # 关 → 行为不变，全员 step
    eng.run_round(1)
    assert [s.n for s in ss] == [1, 1, 1]


def test_e2e_wake_disabled_default_no_wake_events():
    from orchestration.integration import run_e2e
    rep = run_e2e(seed=42, rounds=8, n=3)  # 默认 policy.wake.enabled=false
    assert "WAKE" not in rep["event_types"]
    assert "IDLE" not in rep["event_types"]


def test_e2e_wake_enabled_emits_and_gates():
    from orchestration.integration import run_e2e
    from engine.runner import default_config
    cfg = default_config()
    cfg["policy"]["wake"]["enabled"] = True
    rep = run_e2e(seed=42, rounds=8, n=3, config=cfg)
    assert "WAKE" in rep["event_types"] and "IDLE" in rep["event_types"]
    assert rep["unknown_event_types"] == []
    assert rep["replay_parity"] is True
    assert rep["first_run_equals_replay"] is True
    assert rep["conservation_ok"] is True
