"""回归门禁：「世界真的在运转」——防止 D1 回滚把 bug 掩盖成全绿。

背景：D1 引入「整回合回滚」后，若某 hook 每回合抛异常，本回合事件会被丢弃、
只留 SYSTEM_ERROR，而外层 replay/守恒门禁仍全绿——静默失效。本门禁断言
**结构不变量 + 事件量下界**，比"能跑完"更能暴露停摆。

参照：T34 基线 N=3×84≈1730、N=10×84≈8992 事件（当时 life 的 update_relations
为 no-op）；life 实现 L5 后事件量上升，故下界取 T34 值以**防塌陷**，不设上界。
"""

from collections import Counter

from orchestration.integration import build_world

ROUNDS_PER_DAY = 12  # ROUNDS_PER_SLOT(3) * SLOTS_PER_DAY(4)


def _run(n: int, rounds: int, seed: int = 42):
    world = build_world(seed=seed, n=n)
    engine = world["engine"]
    for r in range(rounds):
        engine.run_round(r)
    return engine, Counter(rec["type"] for rec in engine.ledger.records)


def test_world_actually_runs_n3_week():
    engine, c = _run(3, 84)
    assert c.get("SYSTEM_ERROR", 0) == 0, "存在 SYSTEM_ERROR：回合被回滚，世界停摆"
    assert c.get("TIME_MARK", 0) == (84 - 1) // ROUNDS_PER_DAY + 1  # 7：日边界锚点
    assert c.get("MEMORY_WRITE", 0) > 0
    assert c.get("OBSERVATION", 0) > 0
    assert c.get("ACTIVITY_COMPLETED", 0) > 0
    assert c.get("TURN_SEAL", 0) == 84
    assert sum(c.values()) >= 1730, f"事件量塌陷：{sum(c.values())} < T34 下界 1730"


def test_world_actually_runs_n10_short():
    engine, c = _run(10, 24)
    assert c.get("SYSTEM_ERROR", 0) == 0
    assert c.get("MEMORY_WRITE", 0) > 0
    assert c.get("ACTIVITY_STARTED", 0) > 0
    assert sum(c.values()) >= 1500, f"事件量塌陷：{sum(c.values())}"


def test_no_system_error_on_larger_population():
    """更大规模短跑：SYSTEM_ERROR 必须为 0（防接口不匹配型静默失效）。"""
    engine, c = _run(20, 12)
    assert c.get("SYSTEM_ERROR", 0) == 0
    assert c.get("RELATION_ENCOUNTER", 0) >= 0
    assert sum(c.values()) > 0
