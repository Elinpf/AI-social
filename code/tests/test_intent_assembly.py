"""T235/T228：INTENT->事件 装配契约——透传既定 additive 字段 + 未知键不静默丢弃。"""

from life.ports import Intent
from orchestration.integration import build_world


def _open(eng, r):
    eng.state.round = r
    eng.ctx = eng.ctx.at(r, 0)
    eng.arbiter.discard()


def test_memory_retrieve_passthrough_vec_fields():
    w = build_world(seed=7, n=3); eng = w["engine"]; ad = w["adapter"]
    A = sorted(w["personas"])[0]
    _open(eng, 1)
    res = ad.submit_intent(A, Intent("INTENT.MEMORY", A, {
        "op": "retrieve", "query_id": "q1", "top_k": 3,
        "selected_mem_ids": [], "scores": [], "weights": {}, "tie_order": [],
        "vec_available": False, "retrieval_mode": "lexical", "query_digest": "emb-v1"}))
    assert res.ok
    eng.state, _ = eng.arbiter.commit(eng.state)
    mr = next(r for r in eng.ledger.records if r["type"] == "MEMORY_RETRIEVE")
    assert mr["payload"]["vec_available"] is False          # T228 关闭判据：字段真的到达事件
    assert mr["payload"]["retrieval_mode"] == "lexical"
    assert mr["payload"]["query_digest"] == "emb-v1"


def test_unknown_intent_key_not_silently_dropped():
    w = build_world(seed=7, n=3); eng = w["engine"]; ad = w["adapter"]
    A = sorted(w["personas"])[0]
    _open(eng, 1)
    assert ad.submit_intent(A, Intent("INTENT.MEMORY", A, {
        "op": "retrieve", "query_id": "q1", "top_k": 3, "selected_mem_ids": [],
        "scores": [], "weights": {}, "tie_order": [], "bogus_extra_key": 123})).ok
    eng.state, _ = eng.arbiter.commit(eng.state)
    dropped = [r for r in eng.ledger.records
               if r["type"] == "DROPPED" and r["payload"].get("reason") == "unknown_intent_field"]
    assert dropped and "bogus_extra_key" in dropped[0]["payload"]["keys"]
