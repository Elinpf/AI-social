"""T264 步骤⑤：增量索引 —— 逐字节不变 + 陈旧/重建一致性。"""

from contracts.visibility import visible_events as ve
from orchestration.integration import build_world
from orchestration.visibility_index import VisibilityIndex


def test_index_equals_fullscan_bytes():
    """增量索引输出 == 全量重扫（window 与 full 两种），逐条一致含顺序。"""
    w = build_world(seed=42, n=6); eng = w["engine"]; ad = w["adapter"]
    idx = VisibilityIndex(ad._scope_table, ad._default_cls)
    for r in range(20):
        eng.run_round(r)
        idx.sync(eng.ledger.records)
        for aid in sorted(eng.state.agents):
            loc = eng.state.agents[aid].get("location", "residence")
            a = [x["seq"] for x in idx.visible(aid, r, window_rounds=2, location=loc)]
            b = [x["seq"] for x in ve(eng.ledger.records, aid, r, scope_table=ad._scope_table,
                                      default_cls=ad._default_cls, window_rounds=2, location=loc)]
            assert a == b, f"window diff @ r={r} {aid}"
            c = [x["seq"] for x in idx.visible(aid, r)]
            d = [x["seq"] for x in ve(eng.ledger.records, aid, r, scope_table=ad._scope_table,
                                      default_cls=ad._default_cls)]
            assert c == d, f"full diff @ r={r} {aid}"


def test_index_sync_equals_rebuild():
    """陈旧风险：增量 sync 的结果必须 == 从零 rebuild（防漏更新）。"""
    w = build_world(seed=7, n=4); eng = w["engine"]; ad = w["adapter"]
    idx = VisibilityIndex(ad._scope_table, ad._default_cls)
    for r in range(15):
        eng.run_round(r)
        idx.sync(eng.ledger.records)
    r = eng.state.round
    fresh = VisibilityIndex(ad._scope_table, ad._default_cls)
    fresh.rebuild(eng.ledger.records)
    for aid in sorted(eng.state.agents):
        assert [x["seq"] for x in idx.visible(aid, r)] == [x["seq"] for x in fresh.visible(aid, r)]


def test_adapter_perceive_uses_index_equivalently():
    w = build_world(seed=42, n=6); eng = w["engine"]; ad = w["adapter"]
    for r in range(12):
        eng.run_round(r)
    for aid in sorted(eng.state.agents):
        a = [e.seq for e in ad.perceive(aid).visible_events]
        loc = eng.state.agents[aid].get("location", "residence")
        b = [x["seq"] for x in ve(eng.ledger.records, aid, eng.state.round,
                                  scope_table=ad._scope_table, default_cls=ad._default_cls,
                                  window_rounds=ad.VISIBLE_WINDOW_ROUNDS, location=loc)]
        assert a == b, f"adapter≠fullscan @ {aid}"


def test_index_not_in_state_hash():
    """索引是派生缓存，不入 state_hash。"""
    w = build_world(seed=3, n=3); eng = w["engine"]; ad = w["adapter"]
    from engine.state import state_hash
    for r in range(6):
        eng.run_round(r)
    h1 = state_hash(eng.state)
    ad.visibility_query(sorted(eng.state.agents)[0], eng.state.round)  # 触发索引构建
    h2 = state_hash(eng.state)
    assert h1 == h2
