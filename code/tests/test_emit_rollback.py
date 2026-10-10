"""D1 验证：emit 缓冲 / P6 唯一 append / 整回合回滚（蓝图 §1.4、T35-D1）。

断言：在 P4 注入异常（或守恒失败）后——
  - 本回合事件（含 P2 的 LLM_CALL）**不在日志**；
  - 仅落 SYSTEM_ERROR / ECONOMY_INVARIANT_VIOLATION（自身必落）；
  - 世界状态**不变**。
"""

from engine.constants import PHASE_ARBITRATE, PHASE_DECIDE
from engine.events import spec
from engine.kernel import Engine
from engine.runner import default_config
from engine.state import state_hash


class _LlmCallStepper:
    """在 P2 DECIDE 注入一条 LLM_CALL（模拟冻结层经 IF-2c 提交，入本回合缓冲）。"""

    agent_id = "ZX"

    def __init__(self, engine):
        self.engine = engine

    def step(self):
        self.engine.emit_specs([spec(
            self.engine.state.round, PHASE_DECIDE, "ZX", "LLM_CALL",
            {"agent_id": "ZX", "tier": "t1", "model": "mock", "tokens_in": 1,
             "tokens_out": 1, "trigger": "plan", "purpose": "plan", "degraded": False})])


def _round0_types(engine, n0):
    return [r["type"] for r in engine.ledger.records[n0:]]


def test_p4_exception_rolls_back_whole_round():
    from engine.hooks import register_phase4_hook
    from engine.hooks.econ import settle_market as orig

    def _boom(state, round_no, ctx):
        raise RuntimeError("injected P4 failure")

    engine = Engine(seed=1, config=default_config())
    engine.genesis()
    engine.agent_steppers = [_LlmCallStepper(engine)]

    before = state_hash(engine.state)
    n0 = len(engine.ledger.records)

    register_phase4_hook("settle_market", _boom)
    try:
        engine.run_round(0)
    finally:
        register_phase4_hook("settle_market", orig)

    types = _round0_types(engine, n0)
    assert "LLM_CALL" not in types, "P2 的 LLM_CALL 必须随回合回滚被丢弃"
    assert types.count("SYSTEM_ERROR") == 1
    assert "TURN_SEAL" in types                     # 封条仍落，链可续
    assert state_hash(engine.state) == before        # 世界状态不变


def test_conservation_failure_rolls_back_and_audits():
    from engine.hooks import register_phase4_hook
    from engine.hooks.econ import settle_market as orig

    def _mint(state, round_no, ctx):
        # 只增 money_minted_total 不动 cash -> 破坏守恒 -> 触发回滚
        return [spec(round_no, PHASE_ARBITRATE, "SYSTEM", "MONEY_MINTED",
                     {"amount": 100, "reason": "injected"})]

    engine = Engine(seed=1, config=default_config())
    engine.genesis()
    engine.agent_steppers = [_LlmCallStepper(engine)]

    before = state_hash(engine.state)
    n0 = len(engine.ledger.records)

    register_phase4_hook("settle_market", _mint)
    try:
        engine.run_round(0)
    finally:
        register_phase4_hook("settle_market", orig)

    types = _round0_types(engine, n0)
    assert "MONEY_MINTED" not in types               # 破坏守恒的事件被回滚
    assert "LLM_CALL" not in types
    assert types.count("ECONOMY_INVARIANT_VIOLATION") >= 1
    assert state_hash(engine.state) == before


def test_success_round_appends_buffer_at_p6():
    """正常回合：缓冲事件在 P6 一次性落盘（可在日志中看到且 seq 连续）。"""
    engine = Engine(seed=1, config=default_config())
    engine.genesis()
    engine.agent_steppers = [_LlmCallStepper(engine)]
    n0 = len(engine.ledger.records)
    engine.run_round(0)
    types = _round0_types(engine, n0)
    assert "LLM_CALL" in types
    seqs = [r["seq"] for r in engine.ledger.records[n0:]]
    assert seqs == list(range(n0, n0 + len(seqs)))   # seq 严格连续
