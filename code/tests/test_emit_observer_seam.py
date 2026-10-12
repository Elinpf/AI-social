"""T253：内核通用「emit 后监听」扩展点（read-only / run-only / replay 不回调）验证。

四条硬约束的实测：
  1) read-only —— 回调收到的是已提交事件的**拷贝**，改它不动账本；
  2) run-only —— `run_round` 的 P6 append 后回调；**replay_records 不回调**；
  3) 行为中性 —— 注册/不注册、有无回调 → 事件日志**逐条一致**；
  4) engine 不认识 life —— 只提供注册+触发（结构上以本测试的纯回调兑现）。
另测：回滚/异常路径**不**回调（观察者只看"已真正落盘的世界事件"）。
"""

from engine.canon import canonical_json
from engine.constants import PHASE_ARBITRATE
from engine.events import spec
from engine.kernel import Engine
from engine.replay import replay_records
from engine.runner import default_config


def _make_engine(seed=1):
    e = Engine(seed=seed, config=default_config())
    e.genesis()
    return e


def _digest(records):
    return [canonical_json(r) for r in records]


def test_run_triggers_observer_and_matches_ledger():
    """run：每回合 P6 后回调，收到的事件 == 该回合落盘事件。"""
    e = _make_engine()
    calls = []
    e.register_emit_observer(lambda recs: calls.append(recs))

    n0 = len(e.ledger.records)
    e.run_round(0)
    # 回调拿到本回合在 P6 commit 的世界事件（**不含**之后 _seal 追加的 TURN_SEAL）
    committed = [r for r in e.ledger.records[n0:] if r["type"] != "TURN_SEAL"]
    assert len(calls) == 1
    assert _digest(calls[0]) == _digest(committed)
    assert "TURN_SEAL" not in {r["type"] for r in calls[0]}
    assert {r["type"] for r in calls[0]}  # 非空


def test_replay_does_not_trigger_observer():
    """replay：replay_records 不经 run_round → 回调**一次都不触发**。"""
    e = _make_engine()
    e.run_round(0)
    e.run_round(1)
    records = list(e.ledger.records)

    calls = []
    e.register_emit_observer(lambda recs: calls.append(recs))
    # 重放同一日志
    replay_records(records, verify=True)
    assert calls == [], "replay 不得触发 emit 观察者"


def test_behavior_neutral_on_off():
    """行为中性：注册回调 vs 不注册 → 日志逐条字节一致。"""
    e_on = _make_engine()
    seen = []
    e_on.register_emit_observer(lambda recs: seen.append(len(recs)))
    for r in range(3):
        e_on.run_round(r)

    e_off = _make_engine()
    for r in range(3):
        e_off.run_round(r)

    assert _digest(e_on.ledger.records) == _digest(e_off.ledger.records)
    assert seen, "有注册时回调应被触发（对照组非空）"


def test_observer_is_read_only_copy():
    """read-only：观察者原地改收到的记录，不影响账本。"""
    e = _make_engine()

    def _mutate(recs):
        for r in recs:
            r["type"] = "TAMPERED"
            r["seq"] = -1
            if isinstance(r.get("payload"), dict):
                r["payload"]["injected"] = True

    e.register_emit_observer(_mutate)
    e.run_round(0)
    assert all(r["type"] != "TAMPERED" for r in e.ledger.records)
    assert all(r["seq"] >= 0 for r in e.ledger.records)


def test_rollback_round_does_not_notify():
    """回滚/异常路径不回调（观察者只看已落盘事件）。"""
    from engine.hooks import register_phase4_hook
    from engine.hooks.econ import settle_market as orig

    def _boom(state, round_no, ctx):
        raise RuntimeError("injected P4 failure")

    e = _make_engine()
    calls = []
    e.register_emit_observer(lambda recs: calls.append(recs))
    n0 = len(e.ledger.records)

    register_phase4_hook("settle_market", _boom)
    try:
        e.run_round(0)
    finally:
        register_phase4_hook("settle_market", orig)

    assert calls == [], "回滚回合不得回调"
    # 但 SYSTEM_ERROR/TURN_SEAL 仍落盘（链可续）——由 _direct_append，不经观察者
    assert "SYSTEM_ERROR" in [r["type"] for r in e.ledger.records[n0:]]


def test_unregister_stops_callback():
    e = _make_engine()
    calls = []
    fn = lambda recs: calls.append(recs)  # noqa: E731
    e.register_emit_observer(fn)
    e.register_emit_observer(fn)          # 重复注册去重
    e.unregister_emit_observer(fn)
    e.run_round(0)
    assert calls == []
