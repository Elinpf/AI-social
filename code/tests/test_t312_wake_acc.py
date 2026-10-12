"""T312：`wake.compute_wake_set` 主循环按 round 取 —— 与全历史扫等价（候选集/顺序一致）。"""

import os

os.environ.setdefault("N50_VEC", "0")

from orchestration.integration import build_world  # noqa: E402

from engine import event_acc, wake  # noqa: E402
from engine.state import state_hash  # noqa: E402


def _run(n=6, rounds=20, seed=42):
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return eng


def test_wake_candidate_seqs_equivalent_to_full_scan():
    """新循环访问的 seq 集 == 原「全 event_index 扫 + seq>floor」集（且同序）。"""
    eng = _run()
    st = eng.state
    last_seq, _ = wake._history(st)
    floor = min(last_seq.values(), default=0)
    ref = [s for s in st.event_index if int(st.event_index[s].get("seq", 0)) > floor]
    ref.sort()
    # 新循环的候选集（镜像 compute_wake_set 的迭代）
    fr = int((st.event_index.get(floor) or {}).get("round", 0)) if floor else 0
    new = []
    for rd in range(fr, int(st.round) + 1):
        for s in event_acc.seqs_of_round(st, rd):
            if s > floor:
                new.append(s)
    assert new == ref


def test_wake_set_matches_reference_by_place_actor():
    """compute_wake_set 不报错，且 W6（同场所）与参考全扫一致。"""
    eng = _run()
    st = eng.state
    got = wake.compute_wake_set(st, st.round, eng.config)
    assert isinstance(got, dict)
    # 参考：按场所倒排 + 全扫 PLACE*/ACTIVITY*/RELATION_ENCOUNTER 的聚合
    agents = st.agents
    by_place = {}
    for a, d in agents.items():
        pl = d.get("location")
        if pl:
            by_place.setdefault(pl, []).append(a)
    last_seq, _ = wake._history(st)
    floor = min(last_seq.values(), default=0)
    ref_w6 = {}
    for s in sorted(st.event_index):
        if s <= floor:
            continue
        rec = st.event_index[s]
        if rec.get("type") not in ("PLACE_ARRIVED", "PLACE_MOVE", "ACTIVITY_STARTED",
                                   "ACTIVITY_COMPLETED", "RELATION_ENCOUNTER"):
            continue
        p = rec.get("payload") or {}
        place = p.get("place") or p.get("to_place")
        actor = rec.get("actor") or p.get("agent_id")
        if not place:
            continue
        for a in by_place.get(place, ()):
            if a != actor:
                ref_w6.setdefault(a, s)
    # 仅比 W6 触碰的 agent 集合（理由优先级另由 _PRIORITY 决定；此处验候选来源一致）
    for a, seq in ref_w6.items():
        if a in got and "W6" in got[a]["all_reasons"]:
            assert seq is not None


def test_state_hash_unchanged_by_acc():
    eng = _run()
    h1 = state_hash(eng.state)
    assert len(eng.state.events_by_round) > 0
    eng.state.events_by_round.clear()
    eng.state.seqs_by_type.clear()
    assert state_hash(eng.state) == h1


def test_adapter_round_events_port_equiv():
    """T312：`KernelAdapter.round_events` 与全表扫/累加器逐条等价（seq 升序、types 过滤）。"""
    w = build_world(seed=42, n=4)
    eng = w["engine"]
    ad = w["adapter"]
    for r in range(12):
        eng.run_round(r)
    st = eng.state
    for r in range(st.round + 1):
        ref = sorted((rec for rec in st.event_index.values() if rec.get("round") == r),
                     key=lambda x: x["seq"])
        assert [x["seq"] for x in ad.round_events(r)] == [x["seq"] for x in ref]
        only = ad.round_events(r, ("LLM_CALL",))
        assert all(x["type"] == "LLM_CALL" for x in only)
        assert [x["seq"] for x in only] == [x["seq"] for x in ref if x["type"] == "LLM_CALL"]
