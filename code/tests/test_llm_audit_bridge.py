"""T53：IF-2c 审计桥——freeze 的 LLM_CALL 入引擎账本 + 重放零调用。

前提：freeze `LLMClient` 支持可选 `audit_sink`（T53）；orchestration 接线把它接到
`engine.emit_specs`（本回合缓冲 → P6 唯一 append）。
"""

from collections import Counter

from engine.replay import replay_records
from engine.state import state_hash
from orchestration.integration import build_world


def _run(n: int, rounds: int, seed: int = 42):
    world = build_world(seed=seed, n=n)
    engine = world["engine"]
    for r in range(rounds):
        engine.run_round(r)
    return engine, Counter(rec["type"] for rec in engine.ledger.records)


def test_llm_call_audited_into_engine_ledger():
    """IF-2c 桥生效：LLM_CALL 出现在**引擎账本**（不再只在 freeze 私有 EventLog）。"""
    engine, c = _run(3, 6)
    assert c.get("LLM_CALL", 0) > 0, "审计桥未生效：LLM_CALL 未入引擎账本"
    assert c.get("SYSTEM_ERROR", 0) == 0


def test_replay_is_llm_free_and_parity():
    """重放只折叠日志：两次重放 == 首跑；且重放不产生新事件（日志条数不变）。"""
    engine, c = _run(3, 6)
    n0 = len(engine.ledger.records)
    s1 = replay_records(engine.ledger.records)
    s2 = replay_records(engine.ledger.records)
    assert state_hash(s1) == state_hash(s2) == state_hash(engine.state)
    assert len(engine.ledger.records) == n0  # 重放不追加事件


def test_llm_call_payload_has_model_and_tier():
    engine, c = _run(3, 6)
    calls = [r for r in engine.ledger.records if r["type"] == "LLM_CALL"]
    assert calls
    p = calls[0]["payload"]
    assert "model" in p and "tier" in p
    assert "api_key" not in p and "key" not in {k.lower() for k in p}  # 密钥绝不入日志


def test_llm_call_rounds_valid_and_verify_pass():
    """T55 回归：LLM_CALL 带合法真实回合，且 verify（重放）PASS。"""
    engine, c = _run(3, 84)
    calls = [r for r in engine.ledger.records if r["type"] == "LLM_CALL"]
    assert calls
    assert all(0 <= r["round"] <= 83 for r in calls)          # 回合合法
    assert len({r["round"] for r in calls}) > 1               # 回合确实前进（非全 0 污染）
    # 关键：重放两次状态哈希 == 首跑（TURN_SEAL 一致，verify PASS）
    assert state_hash(replay_records(engine.ledger.records)) == state_hash(engine.state)


def test_round_never_regresses_on_stale_event():
    """防回退：即使来一条 stale round 的事件，world round 不得回退。"""
    from engine.state import initial_state
    from engine.replay import apply_event
    st = initial_state(1)
    st.round = 5
    apply_event(st, {"seq": 0, "round": 0, "phase": 2, "actor": "SYSTEM",
                     "type": "LLM_CALL", "payload": {}, "mono_ts": 0,
                     "prev_hash": "x", "hash": "y"})
    assert st.round == 5  # 不被回退到 0

