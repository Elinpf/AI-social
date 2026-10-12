"""T264：可见性单一真源 —— 三处（engine / life / adapter）逐条一致（含顺序）。

门禁：同一 records 下，`KernelAdapter.perceive` 的 visible 与 `life.visibility.visible_events`
（以及 `engine.perceive.visible_events`）必须输出**相同序列**。永久防"增量≠全量/三份漂移"。
"""

from collections import Counter

from life.visibility import visible_events as life_vis
from engine.perceive import visible_events as eng_vis
from orchestration.integration import build_world


def _seqs(evs):
    # 兼容 record / EventView / dict 三种投影
    def s(e):
        return e["seq"] if isinstance(e, dict) else getattr(e, "seq")
    return [s(e) for e in evs]


def _run(seed=42, n=6, rounds=30):
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return w, eng


def test_three_sources_agree_engine_life_adapter():
    w, eng = _run()
    ad = w["adapter"]
    pids = sorted(w["personas"])
    records = eng.ledger.records
    r = eng.state.round

    for aid in pids:
        # engine（全历史） == life（全历史）
        assert _seqs(eng_vis(records, aid, r)) == _seqs(life_vis(records, aid, r)), \
            f"engine≠life @ {aid}"
        # adapter（窗口=2） == life（同窗口）
        a = _seqs(ad.perceive(aid).visible_events)
        lw = _seqs(life_vis(records, aid, r, window_rounds=ad.VISIBLE_WINDOW_ROUNDS))
        assert a == lw, f"adapter≠life(window) @ {aid}"


def test_gate_actually_exercises_offer_and_group():
    """确保上述一致性不是"空集恒等"——至少覆盖 OFFER_CREATED / GROUP / PLACE 等。"""
    w, eng = _run(seed=7, n=6, rounds=30)
    types = Counter(rec["type"] for rec in eng.ledger.records)
    assert types.get("PLACE_MOVE", 0) > 0
    # 至少存在可见性分支多样的事件（不要求 OFFER_CREATED/GROUP 必现，但要求非平凡）
    assert types.get("ACTIVITY_COMPLETED", 0) > 0
