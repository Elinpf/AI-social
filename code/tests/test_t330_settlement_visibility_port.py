"""T330：settlement 可见性走 T264 索引端口 —— 端口产出 == 全扫（含 settlement 产出等价）。

硬要求：先证等价（逐条）后改；不自行改语义。
"""

import os

os.environ.setdefault("N50_VEC", "0")

from orchestration.integration import build_world  # noqa: E402

import life.visibility as LV  # noqa: E402
from contracts.visibility import visible_events as _ve  # noqa: E402
from engine.perceive import load_perception_scope  # noqa: E402
from engine.version import load_visibility_flags  # noqa: E402


def _scope():
    s = load_perception_scope()
    plaf = load_visibility_flags().get("place_local_actor_fallback", False)
    return s.get("scope", {}), s.get("default_visibility_class", "place_local"), plaf


def _ref_fullscan(state, aid, r):
    sc, dc, plaf = _scope()
    return _ve(list(state.event_index.values()), aid, r, scope_table=sc, default_cls=dc,
               place_local_actor_fallback=plaf)


def _run(seed=42, n=4, rounds=12):
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return eng


def test_provider_hits_index_dict():
    """T330：life 侧传 `state.event_index`（dict）时应命中 provider（不再全扫）。"""
    eng = _run()
    st = eng.state
    assert id(st.event_index) in LV._INDEXES, "state.event_index 未注册 provider"
    # provider 命中路径 == 全扫逐条（seq 序一致）
    for r in range(st.round + 1):
        for aid in sorted(st.agents):
            got = [x["seq"] for x in LV.visible_events(st.event_index, aid, r)]
            ref = [x["seq"] for x in _ref_fullscan(st, aid, r)]
            assert got == ref, (aid, r)


def test_provider_equiv_multi_seed():
    for seed in (1, 7, 42):
        eng = _run(seed=seed, n=6, rounds=10)
        st = eng.state
        for r in range(st.round + 1):
            for aid in sorted(st.agents):
                assert ([x["seq"] for x in LV.visible_events(st.event_index, aid, r)] ==
                        [x["seq"] for x in _ref_fullscan(st, aid, r)])


def test_settlement_write_memories_equiv_provider_vs_fallback():
    """settlement.write_memories 产出（OBSERVATION 的 target_event_seq 集）在"走 provider"与
    "强制全扫"两种条件下必须逐条相同。"""
    from life.settlement import write_memories
    from engine.rng import Ctx
    eng = _run(seed=42, n=4, rounds=12)
    st = eng.state
    cfg = eng.config
    # provider 路径（当前默认：dict 已注册）
    saved = dict(LV._INDEXES)
    out_provider = []
    out_fallback = []
    for r in range(1, st.round + 1):
        ctx = Ctx(eng.seed, cfg, r, 35)
        out_provider.append([(e.payload["observer"], e.payload["target_event_seq"])
                             for e in write_memories(st, r, ctx)])
    # 强制全扫：清空 provider
    LV.clear_indexes()
    for r in range(1, st.round + 1):
        ctx = Ctx(eng.seed, cfg, r, 35)
        out_fallback.append([(e.payload["observer"], e.payload["target_event_seq"])
                             for e in write_memories(st, r, ctx)])
    LV._INDEXES.update(saved)
    assert out_provider == out_fallback


def test_state_hash_same_provider_vs_fallback():
    """同种子：走 provider 与强制全扫（清空索引）⇒ 最终 `state_hash` 必须相同。"""
    from engine.state import state_hash
    h_provider = state_hash(_run(seed=42, n=6, rounds=12).state)
    saved = dict(LV._INDEXES)
    LV.clear_indexes()                     # 强制全扫
    try:
        h_fallback = state_hash(_run(seed=42, n=6, rounds=12).state)
    finally:
        LV._INDEXES.update(saved)
    assert h_provider == h_fallback
