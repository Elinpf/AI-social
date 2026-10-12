"""T288：`body_ref/embed_ref = None` 容忍 + 检索语义（不抛、按既有降级路径计分）。

`MEMORY_CONSOLIDATE` 的派生记忆 `body_ref/embed_ref` 可能为 `None`（引擎折叠）。
本测试定死**三条语义**并实测：
  1. **可被选中**：它仍是 `memory_index` 里的真实记忆，保留为可检索节点；
  2. **怎么计分**：text="" → lexical 降级，relevance=0（query 有 token 时），仍参与
     recency/importance 排名；`vec_available=false`（不静默）；
  3. **可辨识**：靠 `vec_available=false` + `source_event_seq`/kind，不新增字段。
"""
from __future__ import annotations

from life.memory import AssociativeMemory, HashEmbeddingModel, SideStore


def test_read_none_refs_is_tolerated(tmp_path):
    st = SideStore(tmp_path, persist_vec=True)
    assert st.read_body(None) == ""          # 显式 = 无正文
    assert st.read_embed(None) is None       # 显式 = 无向量（触发降级）


def _none_payload(mem, mem_id, importance, tick):
    """A `MEMORY_CONSOLIDATE`-style derived memory with no body/embedding."""
    return {"op": "write", "mem_id": mem_id, "kind": "semantic", "importance": importance,
            "day": 0, "slot": "night", "body_ref": None, "embed_ref": None,
            "refs": [], "source_event_seq": None, "tick": tick}


def test_none_ref_node_retrievable_not_crash(tmp_path):
    mem = AssociativeMemory("P1", HashEmbeddingModel(), SideStore(tmp_path, persist_vec=True))
    real = mem.prepare_write("observation", "food market bread", 5, 0, "morning", 0)
    mem.commit_write(real)
    none_node = mem.commit_write(_none_payload(mem, "M-P1-000001", 5, 0))
    assert none_node.text == "" and none_node.embed == []

    hits, debug = mem.score_and_rank("bread", now_tick=0)   # must not raise
    assert debug["vec_available"] is False                  # None 向量 → 已降级
    assert debug["retrieval_mode"] == "lexical"
    # 无声明的"应该"——实测它是否被选中：
    picked = [n.mem_id for n, _ in hits]
    print("[T288] none-ref node selected in top_k:", none_node.mem_id in picked, "hits=", picked)


def test_none_ref_node_selectable_when_it_dominates(tmp_path):
    """with equal recency but higher importance, the None-ref node CAN be selected
    (proving it is not silently excluded) — its relevance is 0, not a penalty."""
    mem = AssociativeMemory("P1", HashEmbeddingModel(), SideStore(tmp_path, persist_vec=True))
    mem.commit_write(_none_payload(mem, "M-P1-000000", 10, 0))
    for i in range(1, 6):
        mem.commit_write(mem.prepare_write("observation", "ordinary note", 1, 0, "morning", 0))
    hits, _ = mem.score_and_rank("unmatched_query", now_tick=0, top_k=1)
    assert hits and hits[0][0].mem_id == "M-P1-000000"


def test_none_ref_occupancy_number(tmp_path):
    """Synthetic 50/50 mix → report how often a None-ref node takes a top_k slot.

    Leader: leave the NUMBER. If it ever exceeds ~1/3 in a real run, raise it
    separately (no pre-emptive rule).
    """
    mem = AssociativeMemory("P1", HashEmbeddingModel(), SideStore(tmp_path, persist_vec=True))
    # 20 with text, 20 None-ref, same importance/recency
    for i in range(20):
        mem.commit_write(mem.prepare_write("observation", f"food note {i}", 5, 0, "morning", 0))
    for i in range(20):
        mem.commit_write(_none_payload(mem, f"M-P1-{1000 + i:06d}", 5, 0))
    total_slots = 0
    none_slots = 0
    for q in ("food 1", "food 2", "food 3", "market", "note"):
        hits, _ = mem.score_and_rank(q, now_tick=0, top_k=8)
        total_slots += len(hits)
        none_slots += sum(1 for n, _ in hits if n.body_ref is None)
    frac = none_slots / total_slots
    print(f"[T288] None-ref top_k occupancy (synthetic 50/50 mix): {none_slots}/{total_slots} = {frac:.2f}")
    assert frac <= 0.5  # sanity only; the exact number is reported above
