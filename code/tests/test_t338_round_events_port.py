"""T338：`settlement.events_this_round` 端口真生效（不静默回退）+ 等价 + 可观测。"""

import os

os.environ.setdefault("N50_VEC", "0")

from orchestration.integration import build_world  # noqa: E402

from life import settlement as S  # noqa: E402
from life.settlement import LifeState  # noqa: E402
from engine.rng import Ctx  # noqa: E402
from engine.state import state_hash  # noqa: E402


def _run(n=4, rounds=12, seed=42):
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return w, eng


def test_port_resolves_via_ctx_kernel_and_no_fallback():
    """引擎运行中：ctx.kernel 已注入 ⇒ 端口命中，fallback 计数为 0。"""
    S.reset_port_fallback_count()
    w, eng = _run()
    st = eng.state
    ctx = Ctx(eng.seed, eng.config, st.round, 35, kernel=w["adapter"])
    ls = LifeState(st, kernel=ctx)
    ref = sorted((r for r in st.event_index.values() if r.get("round") == st.round),
                 key=lambda x: x["seq"])
    got = ls.events_this_round(st.round)
    assert [x["seq"] for x in got] == [x["seq"] for x in ref]
    assert S.port_fallback_count() == 0


def test_port_equiv_fullscan_multi_round():
    w, eng = _run(seed=7, n=6, rounds=12)
    st = eng.state
    for r in range(st.round + 1):
        ctx = Ctx(eng.seed, eng.config, r, 35, kernel=w["adapter"])
        ls = LifeState(st, kernel=ctx)
        ref = sorted((x for x in st.event_index.values() if x.get("round") == r),
                     key=lambda x: x["seq"])
        assert [x["seq"] for x in ls.events_this_round(r)] == [x["seq"] for x in ref]
        only = ls.events_this_round(r, "ACTIVITY_COMPLETED")
        assert all(x["type"] == "ACTIVITY_COMPLETED" for x in only)
        assert [x["seq"] for x in only] == [x["seq"] for x in ref if x["type"] == "ACTIVITY_COMPLETED"]


def test_reverse_no_port_counts_fallback():
    """反向验证：无端口（ctx.kernel=None）⇒ 回退全扫，且计数 + 告警一次。"""
    _, eng = _run(rounds=4)
    st = eng.state
    S.reset_port_fallback_count()
    ctx = Ctx(eng.seed, eng.config, st.round, 35)  # kernel=None
    ls = LifeState(st, kernel=ctx)
    ls.events_this_round(st.round)
    ls.events_this_round(0)
    assert S.port_fallback_count() == 2


def _run_no_port(n=6, rounds=12, seed=3):
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    eng.kernel = None  # 跑前清空 ⇒ life 走全扫回退
    for r in range(rounds):
        eng.run_round(r)
    return w, eng


def test_state_hash_same_with_and_without_port():
    """端口只改读路径：有端口 vs 无端口（全扫回退）两跑，最终 state_hash 相同。"""
    _, e1 = _run(seed=3, n=6, rounds=12)
    _, e2 = _run_no_port(seed=3, n=6, rounds=12)
    assert state_hash(e1.state) == state_hash(e2.state)
