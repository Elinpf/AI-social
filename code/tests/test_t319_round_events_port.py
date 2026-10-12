"""T319: `events_this_round` 走内核只读端口 `round_events`（去全扫）。

验收：① 逐条等价（端口 vs 全扫，seq 升序）② 反向验证（端口被真用 + 无端口时回退）
③ `state_hash` 不变（含 replay parity）。
"""
from __future__ import annotations

from engine.replay import replay_records
from engine.state import state_hash
from life.settlement import LifeState
from orchestration.integration import build_world


def _scan(state, r, t):
    out = [rec for rec in state.event_index.values()
           if rec.get("round") == r and (t is None or rec.get("type") == t)]
    out.sort(key=lambda x: x.get("seq", 0))
    return [x["seq"] for x in out]


def test_round_events_port_matches_full_scan():
    w = build_world(seed=7, n=3)
    eng, adapter = w["engine"], w["adapter"]
    for r in range(8):
        eng.run_round(r)
    st = eng.state
    for r in range(8):
        for t in (None, "ACTIVITY_COMPLETED", "ACTIVITY_STARTED", "MEMORY_WRITE"):
            got = [x["seq"] for x in adapter.round_events(r, (t,) if t else None)]
            assert got == _scan(st, r, t), f"port != scan at round {r} type {t}"
    assert state_hash(replay_records(eng.ledger.records)) == state_hash(st)


def test_events_this_round_uses_port_and_falls_back():
    w = build_world(seed=7, n=2)
    eng = w["engine"]
    for r in range(4):
        eng.run_round(r)
    st = eng.state

    class Fake:
        def round_events(self, r, types=None):
            return [{"seq": -1, "round": 0, "type": "X", "payload": {}}]

    # 端口存在 ⇒ 必须走端口（sentinel 证明未静默回退）
    assert LifeState(st, kernel=Fake()).events_this_round(3, "X")[0]["seq"] == -1
    # 无端口（mini 内核）⇒ 回退全扫，且逐条等价
    got = [x["seq"] for x in LifeState(st).events_this_round(2, "ACTIVITY_COMPLETED")]
    assert got == _scan(st, 2, "ACTIVITY_COMPLETED")
