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
