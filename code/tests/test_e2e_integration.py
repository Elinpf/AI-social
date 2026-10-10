"""端到端联调测试（T34）：真内核 × 生活层（× 冻结层）。

覆盖五项端到端证据：
  ① 事件均合法（无未注册类型）
  ② 无直写旁路（life 不经 Arbiter 改不了状态）
  ③ replay(log) 两次状态哈希相等
  ④ 守恒不变量成立
  ⑤ 规模/耗时/体积记录
"""

from orchestration.integration import build_world, run_e2e
from engine.state import state_hash


REQUIRED_RECORD_KEYS = {"seq", "round", "phase", "actor", "type", "payload",
                        "mono_ts", "prev_hash", "hash"}


def test_week_n3_all_gates():
    """① ② ③ ④：N=3 跑满 84 回合（1 模拟周），全部端到端证据通过。"""
    rep = run_e2e(seed=42, rounds=84, n=3)
    assert rep["events"] > 0
    assert rep["unknown_event_types"] == []          # ① 事件合法
    assert rep["chain_ok"] is True
    assert rep["replay_parity"] is True              # ③ 重放两次哈希相等
    assert rep["first_run_equals_replay"] is True    # 首跑 == 重放（P2）
    assert rep["conservation_ok"] is True            # ④ 守恒
    assert rep["conservation_violations"] == []


def test_n10_scale_runs():
    """⑤ N=10 可扩展（跑 24 回合，全部门禁通过）。"""
    rep = run_e2e(seed=42, rounds=24, n=10)
    assert rep["n_agents"] == 10
    assert rep["unknown_event_types"] == []
    assert rep["chain_ok"] and rep["replay_parity"] and rep["conservation_ok"]


def test_no_direct_write_bypass():
    """② life 的 L1–L7 hook 是纯函数：直接调用不改状态（无旁路写）。"""
    world = build_world(seed=7, n=3)
    engine = world["engine"]
    from life.settlement import PHASE35_HOOKS
    ctx = engine.ctx.at(3, 35)
    for name, fn in PHASE35_HOOKS.items():
        before = state_hash(engine.state)
        fn(engine.state, 3, ctx)  # 只允许返回 specs，不许改 state
        assert state_hash(engine.state) == before, f"hook {name} 直写了状态（旁路！）"


def test_log_records_have_kernel_shell():
    """日志外壳字段与前端/观测读取格式一致。"""
    rep = run_e2e(seed=42, rounds=8, n=3)
    # run_e2e 返回的 records 未保留，这里重新跑一次取日志
    from orchestration.integration import build_world
    world = build_world(seed=42, n=3)
    eng = world["engine"]
    for r in range(8):
        eng.run_round(r)
    for rec in eng.ledger.records:
        assert REQUIRED_RECORD_KEYS <= set(rec.keys())


def test_adapter_is_kernel_port():
    """KernelAdapter 满足 life.ports.KernelPort 协议。"""
    from life.ports import KernelPort
    world = build_world(seed=1, n=3)
    assert isinstance(world["adapter"], KernelPort)


def test_phase35_hooks_registered_in_order():
    from engine.hooks import phase35_order
    assert phase35_order() == ["advance_time", "resolve_schedule", "settle_activities",
                               "apply_needs", "update_relations", "write_memories", "emit_tags"]
