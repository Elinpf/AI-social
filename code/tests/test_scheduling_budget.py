"""T215：M6 预算/可观测降级 + M4 分时调度。"""

from collections import Counter

from engine import scheduling
from engine.replay import apply_event, replay_records
from engine.state import initial_state, state_hash
from orchestration.integration import build_world

_TIME = {"ROUNDS_PER_SLOT": 3, "SLOTS_PER_DAY": ["m", "a", "e", "n"],
         "DAYS_PER_WEEK": 7, "DAY_TYPES": ["workday"] * 5 + ["weekend"] * 2}


def _cfg(budget=1000, judge_cap=100, kc=2):
    return {"time_config": dict(_TIME),
            "policy": {"llm_budget": {"enabled": True, "daily_token_budget": budget,
                                      "max_concurrency_kc": kc, "judge_daily_cap": judge_cap,
                                      "l1_ratio_bp": 8000, "l2_ratio_bp": 10000, "l3_ratio_bp": 15000}}}


def _state_with(tokens, judge_calls=0):
    st = initial_state(1)
    seq = 0

    def add(tin, tout, purpose):
        nonlocal seq
        st.event_index[seq] = {"seq": seq, "round": 0, "type": "LLM_CALL",
                               "payload": {"tokens_in": tin, "tokens_out": tout, "purpose": purpose}}
        seq += 1
    add(tokens, 0, "plan")
    for _ in range(judge_calls):
        add(0, 0, "judge")
    return st


def test_degrade_levels_by_ratio():
    cfg = _cfg(budget=1000)
    assert scheduling.degrade_level(_state_with(799), 0, cfg) == 0
    assert scheduling.degrade_level(_state_with(800), 0, cfg) == 1     # ≥80%
    assert scheduling.degrade_level(_state_with(1000), 0, cfg) == 2    # ≥100%
    assert scheduling.degrade_level(_state_with(1500), 0, cfg) == 3    # ≥150%


def test_degrade_level_judge_cap():
    cfg = _cfg(budget=10_000_000, judge_cap=3)
    assert scheduling.degrade_level(_state_with(0, judge_calls=4), 0, cfg) == 2  # judge 超 cap → 至少 L2


def test_degrade_specs_emit_on_rise_and_fold():
    cfg = _cfg(budget=1000)
    st = _state_with(850)
    specs = scheduling.degrade_specs(st, 0, cfg)
    assert len(specs) == 1 and specs[0].type == "DEGRADE" and specs[0].payload["level"] == 1
    # 折叠后 state.budget_level 升到 1；再调用不重复发（不可静默、也不刷屏）
    apply_event(st, {"seq": 999, "round": 0, "type": "DEGRADE", "payload": specs[0].payload})
    assert st.budget_level == 1
    assert scheduling.degrade_specs(st, 0, cfg) == []


def test_scheduler_caps_peak_and_is_deterministic():
    agents = ["A", "B", "C", "D", "E"]
    pri = {"A": 5, "B": 1, "C": 1, "D": 1, "E": 1}
    r1 = scheduling.schedule_llm_agents(agents, 7, 2, priority=lambda x: pri[x])
    r2 = scheduling.schedule_llm_agents(agents, 7, 2, priority=lambda x: pri[x])
    assert r1 == r2                       # 确定性
    assert len(r1) == 2                   # 峰值 ≤ Kc
    assert "A" in r1                       # 关键路径优先（高 priority）


def test_skip_is_listable_and_conservative():
    # 无维度表 → L3 也**不跳过**（保守：不悄悄砍判定）
    assert scheduling.should_skip_judgment("mentor_relation", 3, _cfg()) is False
    cfg = {"policy": {"llm_budget": {"enabled": True,
                                     "critical_dimensions": ["deal", "mentorship"]}}}
    assert scheduling.should_skip_judgment("deal", 3, cfg) is False      # critical 保留
    assert scheduling.should_skip_judgment("reputation", 3, cfg) is True # 非 critical 跳过
    assert scheduling.should_skip_judgment("reputation", 2, cfg) is False  # L2 不跳
    s = scheduling.skip_spec(5, "reputation", ["P2", "P1"])
    assert s.payload["skipped"] == [{"dimension": "reputation",
                                     "parties": ["P1", "P2"], "round": 5}]  # 可列


def test_authoritative_critical_dimensions_and_exact_match():
    """life 发布的 critical_dimensions（4 个，精确匹配；rel_respect ≠ respect）。"""
    from engine.runner import load_config
    crit = scheduling.critical_dimensions(load_config())
    assert crit == {"weekly_focus", "rel_affinity", "rel_trust", "rel_respect"}
    cfg = load_config()
    assert scheduling.should_skip_judgment("rel_respect", 3, cfg) is False  # 保留
    assert scheduling.should_skip_judgment("respect", 3, cfg) is True      # 不同维度 → 跳过
    assert scheduling.should_skip_judgment("rel_familiarity", 3, cfg) is True
    # importance 走单独键（默认 critical_importance=true → 不跳）
    assert scheduling.should_skip_importance(3, cfg) is False
    assert scheduling.should_skip_importance(3, {"policy": {"llm_budget": {"enabled": True,
                                                                            "critical_importance": False}}}) is True


def test_schedule_skip_is_visible():
    cfg = _cfg()
    cfg["policy"]["llm_budget"]["schedule_enabled"] = True
    cfg["policy"]["llm_budget"]["max_concurrency_kc"] = 1
    st = initial_state(1)
    for a in ("A", "B", "C"):
        st.ensure_agent(a)
    sp = scheduling.schedule_skip_spec(st, 2, cfg)
    assert sp is not None and sp.payload["action"] == "schedule_skip"
    assert len(sp.payload["skipped_agents"]) == 2  # 3 agents, Kc=1 → 2 未许可（不静默）


def test_adapter_should_skip_judgment_gate():
    w = build_world(seed=7, n=3); ad = w["adapter"]; eng = w["engine"]
    eng.config["policy"]["llm_budget"]["critical_dimensions"] = ["deal"]
    eng.state.budget_level = 3
    eng.state.round = 1; eng.ctx = eng.ctx.at(1, 0); eng.arbiter.discard()
    assert ad.should_skip_judgment("reputation", ["P001"]) is True     # 非 critical → 跳
    assert ad.should_skip_judgment("deal", ["P001"]) is False          # critical → 保留
    eng.state, _ = eng.arbiter.commit(eng.state)
    d = [r for r in eng.ledger.records if r["type"] == "DEGRADE"
         and r["payload"].get("action") == "skip_judgment"]
    assert d and d[0]["payload"]["skipped"][0]["dimension"] == "reputation"


def test_note_skip_emits_listable_degrade():
    """life 跳过判定 → 引擎发可列 DEGRADE（ADR-08，入本回合缓冲）。"""
    w = build_world(seed=7, n=3); ad = w["adapter"]; eng = w["engine"]
    eng.state.round = 1; eng.ctx = eng.ctx.at(1, 0); eng.arbiter.discard()
    ad.note_skip("rel_familiarity", ["P002", "P001"])
    eng.state, _ = eng.arbiter.commit(eng.state)
    d = [r for r in eng.ledger.records if r["type"] == "DEGRADE"]
    assert d and d[0]["payload"]["action"] == "skip_judgment"
    assert d[0]["payload"]["skipped"] == [{"dimension": "rel_familiarity",
                                           "parties": ["P001", "P002"], "round": 1}]


def test_llm_permit_default_all_and_capped_when_enabled():
    w = build_world(seed=7, n=10); ad = w["adapter"]; eng = w["engine"]
    pids = sorted(w["personas"])
    # 默认 schedule_enabled=false → 全许可（行为与现状一致）
    assert all(ad.perceive(a).llm_permit for a in pids)
    # 开 M4 → 本轮许可 ≤ Kc
    eng.config["policy"]["llm_budget"]["schedule_enabled"] = True
    eng.config["policy"]["llm_budget"]["max_concurrency_kc"] = 3
    ad._permit_round = None
    assert sum(ad.perceive(a).llm_permit for a in pids) == 3


def test_degrade_on_off_controlled_diff_n10():
    """(b) 同 seed 开/关降级各跑 N=10：差异必须**可解释**（此处应仅多出 DEGRADE 标记）。"""
    from engine.runner import load_config

    w_off = build_world(seed=7, n=10)
    e_off = w_off["engine"]
    for r in range(12):
        e_off.run_round(r)
    c_off = Counter(rec["type"] for rec in e_off.ledger.records)
    assert c_off.get("DEGRADE", 0) == 0

    cfg_on = load_config()
    cfg_on["policy"]["llm_budget"]["daily_token_budget"] = 1  # 极低预算 → 立即降级
    w_on = build_world(seed=7, n=10, config=cfg_on)
    e_on = w_on["engine"]
    for r in range(12):
        e_on.run_round(r)
    c_on = Counter(rec["type"] for rec in e_on.ledger.records)
    assert c_on.get("DEGRADE", 0) >= 1

    # 除 DEGRADE 外，其余事件计数一致 → 差异 100% 可归因于「降级标记」本身
    for t in set(c_off) | set(c_on):
        if t == "DEGRADE":
            continue
        assert c_off.get(t, 0) == c_on.get(t, 0), f"{t}: off={c_off.get(t,0)} on={c_on.get(t,0)}"


def test_non_degraded_path_unchanged_n10():
    """不降级路径行为与现状一致：预算充足时 DEGRADE=0，无 SYSTEM_ERROR。"""
    w = build_world(seed=7, n=10); eng = w["engine"]
    assert eng.config["policy"]["llm_budget"]["daily_token_budget"] >= 1_000_000
    for r in range(12):
        eng.run_round(r)
    c = Counter(rec["type"] for rec in eng.ledger.records)
    assert c.get("DEGRADE", 0) == 0
    assert c.get("SYSTEM_ERROR", 0) == 0
    assert eng.llm_budget_level == 0
    # 重放一致（Fork B 虽放开逐位，但同日志折叠仍应一致）
    assert state_hash(replay_records(eng.ledger.records, verify=False, verify_seals=False)) \
        == state_hash(eng.state)
