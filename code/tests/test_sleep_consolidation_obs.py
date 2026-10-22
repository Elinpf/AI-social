"""R18：睡眠—固化两条观测断点的回归测试（零 LLM 调用）。

① `MEMORY_CONSOLIDATE` 的 `text` 必须到达事件 payload（修前落 `unknown_intent_field`）；
② `SLEEP_COMPLETED` 必须带上本次睡眠窗的人格指纹/漂移三字段（修前恒 null）。

两者都走真实 `agent → intent → 裁决器 → 事件` 路径。
"""

from life.ports import Intent, MemoryRef, TimeCoord, WorldView
from orchestration.integration import build_world


def _open(eng, r):
    eng.state.round = r
    eng.ctx = eng.ctx.at(r, 0)
    eng.arbiter.discard()


def test_consolidate_text_reaches_event_payload():
    w = build_world(seed=7, n=3)
    eng, ad = w["engine"], w["adapter"]
    A = sorted(w["personas"])[0]
    _open(eng, 1)
    assert ad.submit_intent(A, Intent("INTENT.MEMORY", A, {
        "op": "consolidate", "subject": "MARKET",
        "source_mem_ids": ["M-T-1", "M-T-2"],
        "produced_mem_id": f"M-{A}-SM-MARKET",
        "text": "关于MARKET的印象（由2条经历聚合）",
        "day": 0, "slot": "night"})).ok
    eng.state, _ = eng.arbiter.commit(eng.state)

    cons = [r for r in eng.ledger.records if r["type"] == "MEMORY_CONSOLIDATE"]
    assert cons, "未产出 MEMORY_CONSOLIDATE"
    assert cons[-1]["payload"]["text"] == "关于MARKET的印象（由2条经历聚合）"
    dropped = [r for r in eng.ledger.records
               if r["type"] == "DROPPED"
               and (r.get("payload") or {}).get("reason") == "unknown_intent_field"
               and (r.get("payload") or {}).get("type") == "MEMORY_CONSOLIDATE"]
    assert dropped == [], f"CONSOLIDATE.text 仍落 unknown_intent_field: {dropped}"


def test_sleep_end_carries_persona_drift_fields():
    w = build_world(seed=7, n=3)
    eng, ag = w["engine"], w["agents"][0]
    aid = ag.agent_id
    refs = tuple(MemoryRef(mem_id=f"M-{aid}-T{i}", kind="observation",
                           body_ref=None, embed_ref=None, importance=3,
                           day=0, slot="day", subject="MARKET",
                           last_access=1, access_count=1) for i in range(4))
    ag.memory.sync_from_refs(refs)

    _open(eng, 9)                             # night 落在 round%12==9
    wv = WorldView(agent_id=aid, round=9,
                   time=TimeCoord(week=0, day=0, day_of_week=0, day_type="workday",
                                  slot="night", tick_in_slot=3),
                   status="alive", location="residence", cash=0, net_worth=0,
                   memory_refs=refs)
    ag._maybe_sleep_window(wv)
    eng.state, _ = eng.arbiter.commit(eng.state)

    sleep = [r for r in eng.ledger.records if r["type"] == "SLEEP_COMPLETED"]
    assert sleep, "未产出 SLEEP_COMPLETED"
    p = sleep[-1]["payload"]
    assert p["pf0"], "SLEEP_COMPLETED.pf0 为 null"
    assert p["pf_t"], "SLEEP_COMPLETED.pf_t 为 null"
    assert p["drift_permille"] is not None, "SLEEP_COMPLETED.drift_permille 为 null"
