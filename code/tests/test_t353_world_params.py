"""T353：`WorldParams` 可重建派生视图（纯函数）+ 三保底 + 端口。"""

import os

os.environ.setdefault("N50_VEC", "0")

from engine.world_params import world_params  # noqa: E402


def _ev(kind, start, end, place=None, params=None, directed=True, ref="D-1"):
    return {"type": "WORLD_GROUP_EVENT", "round": start, "actor": "DIRECTOR", "payload": {
        "kind": kind, "start_round": start, "end_round": end, "directed": directed,
        "directive_ref": ref, "scope": {"place": place} if place else {},
        "params": params or {}}}


def test_empty_when_no_events():
    assert world_params([], 5, None) == {"activity_weight": {}, "resource_factor_bp": {},
                                         "market_scarcity_bp": {}, "active": []}


def test_festival_activity_weight_within_window():
    recs = [_ev("festival", 3, 6, place="hall", params={"capacity": 40})]
    for t in (2, 6):
        assert world_params(recs, t, None)["activity_weight"] == {}      # [start,end) 外
    for t in (3, 4, 5):
        assert world_params(recs, t, None)["activity_weight"] == {"hall": 40}
        assert world_params(recs, t, None)["active"] == ["D-1"]


def test_supply_shock_and_scarcity():
    recs = [_ev("supply_shock", 0, 3, place="farm", params={"amp_bp": 3000}),
            _ev("tension", 0, 2, params={"scarcity_bp": 2000, "good_id": "food"})]
    wp = world_params(recs, 1, None)
    assert wp["resource_factor_bp"] == {"farm": -3000}
    assert wp["market_scarcity_bp"] == {"food": 2000}


def test_directed_required():
    recs = [_ev("festival", 0, 3, place="hall", params={"capacity": 40}, directed=False)]
    assert world_params(recs, 1, None)["activity_weight"] == {}          # 保底(a)


def test_propagate_toggle_off():
    recs = [_ev("festival", 0, 3, place="hall", params={"capacity": 40})]
    cfg = {"world_director": {"propagate": {"enabled": False}}}
    assert world_params(recs, 1, cfg)["activity_weight"] == {}           # 可消融


def test_adapter_port():
    from orchestration.integration import build_world
    w = build_world(seed=42, n=3)
    eng = w["engine"]
    for r in range(6):
        eng.run_round(r)
    wp = w["adapter"].world_params(eng.state.round)
    assert set(wp) == {"activity_weight", "resource_factor_bp", "market_scarcity_bp", "active"}
