"""Phase 4.4–4.8 生命周期（T61：流动性判据）单元测试。

覆盖：开关、代谢产出、滞回连续计数、复活闭环、终态不可逆、安全阀打标、非法迁移报错、
判死，以及「净值<0 但 L 充足 → 仍存活」的流动性判据本质。
"""

from __future__ import annotations

import collections

import pytest

from engine import conservation
from engine.constants import PHASE_ARBITRATE
from engine.hooks import lifecycle as L
from engine.kernel import Engine
from engine.rng import Ctx
from engine.runner import default_config
from engine.state import initial_state, state_hash
from engine.replay import replay_records


# ------------------------------------------------------------------ helpers
def _ctx(cfg, round_no=0):
    return Ctx(int(cfg.get("seed", 0)), cfg, round_no, PHASE_ARBITRATE)


def _mkstate(agents, events):
    """agents = {aid: (status, cash, death_round)}；events 注入 event_index。"""
    st = initial_state(seed=1)
    for aid, (status, cash, dr) in agents.items():
        st.ensure_agent(aid)
        st.cash[aid] = int(cash)
        st.agents[aid]["status"] = status
        st.agents[aid]["death_round"] = dr
    st.event_index = {}
    for i, rec in enumerate(events):
        rec = dict(rec)
        rec.setdefault("seq", i)
        st.event_index[rec["seq"]] = rec
    return st


def _met(round_no, aid, liquid, distress, c=0):
    return {"round": round_no, "type": "METABOLISM",
            "payload": {"agent_id": aid, "amount": 200, "liquid": liquid,
                        "distress": distress, "count_c": c}}


def _types(specs):
    return [s.type for s in specs]


# ------------------------------------------------------------------ 开关
def test_switch_off_no_metabolism():
    cfg = default_config()
    cfg["lifecycle"] = {"ENABLED": False}
    eng = Engine(7, cfg)
    eng.run(10)
    c = collections.Counter(r["type"] for r in eng.ledger.records)
    assert c.get("METABOLISM", 0) == 0
    assert c.get("SYSTEM_ERROR", 0) == 0


def test_switch_on_by_runtime_override():
    cfg = default_config()
    cfg["lifecycle"] = {"ENABLED": True}
    eng = Engine(7, cfg)
    eng.run(5)
    c = collections.Counter(r["type"] for r in eng.ledger.records)
    assert c["METABOLISM"] > 0
    met = [r for r in eng.ledger.records if r["type"] == "METABOLISM"]
    assert all("liquid" in r["payload"] and "distress" in r["payload"] for r in met)


# ------------------------------------------------------------------ 滞回/计数
def test_count_from_flags_hysteresis():
    sustain = 600
    assert L._count_from_flags({0: {"d": True, "L": -100}}, None, sustain) == 1
    assert L._count_from_flags({k: {"d": True, "L": -100} for k in range(3)}, None, sustain) == 3
    # L≥sustain → 清零
    assert L._count_from_flags({0: {"d": True, "L": -100}, 1: {"d": True, "L": -100},
                                2: {"d": False, "L": 1000}}, None, sustain) == 0
    # 滞回：可支付/可贷（d=False, L<sustain）只递减，不清零
    assert L._count_from_flags({0: {"d": True, "L": -100}, 1: {"d": False, "L": 100}},
                               None, sustain) == 0


def test_negative_net_worth_but_liquid_is_alive():
    """流动性判据本质：净值<0 但 L 充足 → 仍存活（判死只看 L）。"""
    cfg = default_config()
    aid = "A"
    st = _mkstate({aid: ("alive", 1000, None)}, [_met(0, aid, 1000, False)])
    st.loans["loan:A:0"] = {"borrower": aid, "outstanding": 5000, "status": "active",
                            "due_round": 999}
    assert st.net_worth(aid) < 0          # 净值 < 0
    assert L._liquid(st, aid) == 1000     # L 充足
    assert not [s for s in L.check_lifecycle(st, 0, _ctx(cfg, 0))
                if s.payload["to"] in ("near_death", "dead")]
    assert L.check_death(st, 0, _ctx(cfg, 0)) == []


# ------------------------------------------------------------------ 复活
def test_revival_closure_within_window():
    cfg = default_config()
    aid = "A"
    st = _mkstate({aid: ("dead", 10000, 10)}, [])       # L≥sustain，窗内(2<6)
    specs = L.resolve_revival(st, 12, _ctx(cfg, 12))
    t = _types(specs)
    assert "AGENT_REVIVED" in t and "REVIVE_FEE_PAID" in t
    sc = [s for s in specs if s.type == "STATE_CHANGE"][0]
    assert (sc.payload["from"], sc.payload["to"]) == ("dead", "revived")
    ev = [{"round": 12, "type": "AGENT_REVIVED", "payload": {"agent_id": aid}}]
    st2 = _mkstate({aid: ("revived", 10000, None)}, ev)
    assert L.check_lifecycle(st2, 13, _ctx(cfg, 13)) == []       # 冷却内保持
    out = L.check_lifecycle(st2, 12 + 5, _ctx(cfg, 12 + 5))
    assert [s.payload["to"] for s in out if s.type == "STATE_CHANGE"] == ["alive"]


def test_no_revival_illiquid_or_out_of_window():
    cfg = default_config()
    assert L.resolve_revival(_mkstate({"A": ("dead", 100, 10)}, []), 11, _ctx(cfg, 11)) == []
    assert L.resolve_revival(_mkstate({"A": ("dead", 10000, 0)}, []), 6, _ctx(cfg, 6)) == []


# ------------------------------------------------------------------ 判死 / 终态
def test_death_trigger_and_terminated_irreversible():
    cfg = default_config()
    aid = "A"
    events = [_met(0, aid, -100, True, 1), _met(1, aid, -100, True, 2), _met(2, aid, -100, True, 3)]
    st = _mkstate({aid: ("near_death", -200, None)}, events)
    out = L.check_death(st, 2, _ctx(cfg, 2))
    assert "AGENT_DIED" in _types(out)
    sc = [s for s in out if s.type == "STATE_CHANGE"][0]
    assert (sc.payload["from"], sc.payload["to"]) == ("near_death", "dead")
    st_d = _mkstate({aid: ("dead", -200, 0)}, events)
    out2 = L.check_death(st_d, 6, _ctx(cfg, 6))
    assert ("dead", "terminated") in [(s.payload.get("from"), s.payload.get("to"))
                                      for s in out2 if s.type == "STATE_CHANGE"]
    st_t = _mkstate({aid: ("terminated", 10000, 0)}, [])
    assert L.check_lifecycle(st_t, 50, _ctx(cfg, 50)) == []
    assert L.check_death(st_t, 50, _ctx(cfg, 50)) == []
    assert L.resolve_revival(st_t, 50, _ctx(cfg, 50)) == []


def test_illegal_transition_raises():
    for frm, to in (("terminated", "alive"), ("dead", "alive"), ("alive", "revived")):
        with pytest.raises(ValueError):
            L._assert_legal_edge(frm, to)
    L._assert_legal_edge("dead", "revived")
    L._assert_legal_edge("revived", "alive")


# ------------------------------------------------------------------ 安全阀
def test_safety_valve_switch_and_flag():
    cfg = default_config()
    agents = {f"A{i}": (("terminated" if i < 6 else "alive"), 10000, 0) for i in range(10)}
    st = _mkstate(agents, [])
    out = L.check_death(st, 5, _ctx(cfg, 5))
    mint = [s for s in out if s.type == "MONEY_MINTED"]
    assert mint and mint[0].payload.get("reason") == "rescue"
    assert any(s.type == "INIT_ENDOW" and s.payload.get("flag") == "rescue" for s in out)
    cfg_off = default_config()
    cfg_off["lifecycle"] = {"ENABLED": True, "SAFETY_ENABLED": False}
    assert not [s for s in L.check_death(st, 5, _ctx(cfg_off, 5)) if s.type == "MONEY_MINTED"]


def test_death_burst_pauses_kill():
    cfg = default_config()
    aid = "A"
    events = [_met(0, aid, -100, True, 1), _met(1, aid, -100, True, 2), _met(2, aid, -100, True, 3),
              {"round": 2, "type": "AGENT_DIED", "payload": {"agent_id": "X"}},
              {"round": 2, "type": "AGENT_DIED", "payload": {"agent_id": "Y"}},
              {"round": 2, "type": "AGENT_DIED", "payload": {"agent_id": "Z"}}]
    st = _mkstate({aid: ("near_death", -200, None)}, events)
    assert L.check_death(st, 3, _ctx(cfg, 3)) == []      # W_pause 窗口内暂停
    assert "AGENT_DIED" in _types(L.check_death(st, 5, _ctx(cfg, 5)))


# ------------------------------------------------------------------ 端到端
def test_death_pressure_end_to_end():
    cfg = default_config()
    cfg["genesis"] = {"agent_count": 20, "initial_endowment_mu": 500}
    cfg["lifecycle"] = {"ENABLED": True}
    eng = Engine(2026, cfg)
    eng.run(30)
    recs = eng.ledger.records
    c = collections.Counter(r["type"] for r in recs)
    assert c["METABOLISM"] > 0 and c["STATE_CHANGE"] > 0 and c["AGENT_DIED"] > 0
    assert c["SYSTEM_ERROR"] == 0
    pairs = {(r["payload"].get("from"), r["payload"].get("to"))
             for r in recs if r["type"] == "STATE_CHANGE"}
    assert ("near_death", "dead") in pairs
    assert conservation.check_conservation(eng.state, cfg) == []
    assert state_hash(replay_records(recs, verify_seals=True)) == state_hash(eng.state)


# ============================================ T91-P1：世界预算销毁（M≥μ_floor）
def _lc(**over):
    cfg = default_config()
    cfg["lifecycle"] = {"ENABLED": True, **over}
    return cfg


def _fold(st, specs):
    from engine.ledger import Ledger
    from engine.replay import apply_event
    led = Ledger()
    for s in specs:
        apply_event(st, led.append_spec(s))
    return st


def test_world_budget_allows_negative_cash():
    """世界预算：世界别处有货币时，个体现金可至负（不钳个体）。"""
    from engine.state import money_total
    st = _mkstate({"A": ("alive", 0, None), "B": ("alive", 10000, None)}, [])
    ctx = _ctx(_lc(), 0)
    m = int(L._cfg(ctx)["METABOLISM_MU"])
    m0 = money_total(st)                                    # = 10000，budget=10000
    specs = L.apply_metabolism(st, 0, ctx)
    a = [s for s in specs if s.payload["agent_id"] == "A"][0]
    assert a.payload["amount"] == m                         # 预算充足 → 足额销毁
    assert a.payload["liquid"] == -m                        # 个体现金变为负（欠账）
    _fold(st, specs)
    assert money_total(st) == m0 - 2 * m                    # 两个账户各销毁 m，M 减少 2m
    assert money_total(st) >= 0


def test_world_budget_clamped_keeps_M_nonneg():
    """预算 = max(0, M−μ_floor)：M 不足时钳制销毁，M 不穿地板(0)。"""
    from engine.constants import PHASE_ARBITRATE as _P
    from engine.events import spec as _spec
    from engine.state import money_total
    st = _mkstate({"A": ("alive", 100, None), "B": ("alive", 0, None)}, [])
    cfg = _lc()
    floor = L._mu_floor(_ctx(cfg, 0), L._cfg(_ctx(cfg, 0)))
    assert floor == 0
    specs = L.apply_metabolism(st, 0, _ctx(cfg, 0))
    total = sum(s.payload["amount"] for s in specs)
    assert total == 100                                     # 只销毁世界真实存在的 100
    # 被预算钳制者打 flag=floor
    assert any("floor" in (s.payload.get("flags") or []) for s in specs)
    _fold(st, specs)
    assert money_total(st) == 0                             # M 恰好触地板，不为负


def test_pure_metabolism_death_reachable_and_M_nonneg():
    """纯代谢（无经济输入）下：现金可至负 → 判死可达；全程 M ≥ μ_floor。"""
    from engine.state import money_total
    cfg = _lc()
    cfg["genesis"] = {"agent_count": 3, "initial_endowment_mu": 500}
    eng = Engine(2026, cfg)
    eng.genesis()
    for r in range(12):
        eng.run_round(r)
        assert money_total(eng.state) >= 0                 # M 恒不穿地板
    recs = eng.ledger.records
    c = collections.Counter(r["type"] for r in recs)
    assert c["METABOLISM"] > 0 and c["STATE_CHANGE"] > 0 and c["AGENT_DIED"] > 0
    assert c["SYSTEM_ERROR"] == 0
    assert any((r["payload"].get("liquid", 0) < 0)
               for r in recs if r["type"] == "METABOLISM")  # 个体现金确曾至负
    assert conservation.check_conservation(eng.state, cfg) == []
    assert state_hash(replay_records(recs, verify_seals=True)) == state_hash(eng.state)
