"""T239：世界 AI 导演 v1 —— 判定树 R1-R6 / 剂量曲线 / 消融 / 事件与溯源。"""

from engine.world_director import DOSE_CURVES, resolve_dose, validate_directive
from orchestration.integration import build_world

CFG = {
    "enabled": True, "dose_curve": "conservative", "K_warn": 3,
    "mechanisms": {"wd.festival": {"kind": "festival", "enabled": True,
                                   "dose": {"prob_bp": 10000, "capacity": 40, "slots": 3}}},
}


def _draft(**over):
    d = {"mechanism_id": "wd.festival", "kind": "festival", "scope": {"level": "place"},
         "params": {}, "dose": {}, "dose_curve": "conservative",
         "issued_round": 5, "effective_from_round": 5, "directed": True}
    d.update(over)
    return d


def test_r1_r6_decision_tree():
    assert validate_directive(_draft(), CFG)["ok"] is True
    assert validate_directive(_draft(params={"target_agent": "A"}), CFG)["reason"] == "targets_individual"   # R1/R2/R6
    assert validate_directive(_draft(params={"amount_mu": 5}), CFG)["reason"] == "contains_hard_kernel_number"  # R5
    assert validate_directive(_draft(directed=False), CFG)["reason"] == "no_directed_marker"                   # R3
    assert validate_directive(_draft(effective_from_round=4), CFG)["reason"] == "rewrites_past"                # R4(c)
    assert validate_directive(_draft(mechanism_id="nope"), CFG)["reason"] == "invalid_mechanism"
    assert validate_directive(_draft(dose_curve="nope"), CFG)["reason"] == "dose_curve_unknown"
    # WD-D1：agents 级规模 < K → warn，非拒绝
    w = validate_directive(_draft(scope={"level": "agents", "agents": ["A"]}), CFG)
    assert w["ok"] is True and w["severity"] == "warn"


def test_dose_curves_differ():
    cons = resolve_dose({**CFG, "dose_curve": "conservative"}, "wd.festival")["prob_bp"]
    aggr = resolve_dose({**CFG, "dose_curve": "aggressive"}, "wd.festival")["prob_bp"]
    assert aggr > cons
    assert set(DOSE_CURVES) == {"conservative", "moderate", "aggressive"}


def _run(wd_cfg, seed=7, n=3, rounds=6):
    from engine.runner import default_config
    cfg = default_config()
    cfg["world_director"] = wd_cfg
    w = build_world(seed=seed, n=n, config=cfg)
    e = w["engine"]
    for r in range(rounds):
        e.run_round(r)
    return e


def test_ablation_off_zero_events():
    e = _run({"enabled": False, "mechanisms": {}})
    WD = {"WORLD_DIRECTIVE", "WORLD_GROUP_EVENT", "WORLD_DIRECTIVE_REJECTED"}
    wd = [r for r in e.ledger.records if r["type"] in WD]
    assert wd == []                                     # 保底 (b)：关 → 0 事件


def test_enabled_emits_directed_and_traceable():
    e = _run(CFG)
    directs = [r for r in e.ledger.records if r["type"] == "WORLD_DIRECTIVE"]
    groups = [r for r in e.ledger.records if r["type"] == "WORLD_GROUP_EVENT"]
    assert directs and groups                           # 保底 (a)：有 directed 事件
    assert all(r["payload"].get("directed") is True for r in directs + groups)
    assert all(r["actor"] == "DIRECTOR" for r in directs + groups)
    # 可审计：每条 GROUP_EVENT 的 directive_ref 溯源到一条 DIRECTIVE
    d_ids = {r["payload"]["directive_id"] for r in directs}
    assert all(r["payload"]["directive_ref"] in d_ids for r in groups)
    # 保底 (c)：只对未来
    assert all(r["payload"]["effective_from_round"] >= r["payload"]["issued_round"] for r in directs)
    # replay 遇新事件不报错
    from engine.replay import replay_records
    from engine.state import state_hash
    assert state_hash(replay_records(e.ledger.records)) == state_hash(e.state)
