"""T298: 运行期记忆缓存必须对齐权威（账本 `a["memories"]`）。

`sync_from_refs` 是"缓存从日志重建"的入口：权威集之外的节点（如 `FORGET(drop)` 已摘除的）
必须从缓存移除 —— 否则一次性会继续把"已丢弃"的记忆喂给 `plan_forgetting`，与续跑分叉。
"""
from __future__ import annotations

import hashlib

from life.memory import AssociativeMemory, HashEmbeddingModel, SideStore
from life.ports import MemoryRef


def _ref(mem_id, body_ref, embed_ref, kind="observation", imp=5):
    return MemoryRef(mem_id=mem_id, kind=kind, body_ref=body_ref, embed_ref=embed_ref,
                     importance=imp, day=0, slot="morning")


def test_sync_prunes_nodes_outside_authority(tmp_path):
    mem = AssociativeMemory("P1", HashEmbeddingModel(), SideStore(tmp_path, persist_vec=True))
    # two authority memories (commit each before preparing the next → distinct mem_id)
    p1 = mem.prepare_write("observation", "alpha food", 5, 0, "morning", 0)
    mem.commit_write(p1)
    p2 = mem.prepare_write("observation", "beta tool", 5, 0, "morning", 0)
    mem.commit_write(p2)
    refs = {p1["mem_id"]: _ref(p1["mem_id"], p1["body_ref"], p1["embed_ref"]),
            p2["mem_id"]: _ref(p2["mem_id"], p2["body_ref"], p2["embed_ref"])}
    mem.sync_from_refs(list(refs.values()))
    assert set(mem.nodes) == set(refs)
    assert mem._vec_ids and set(mem._vec_ids) <= set(refs)

    # authority drops p2 (FORGET(drop)) -> cache must drop it too
    del refs[p2["mem_id"]]
    mem.sync_from_refs(list(refs.values()))
    assert set(mem.nodes) == {p1["mem_id"]}, "authority-external node must be pruned"
    assert p2["mem_id"] not in mem._vec_ids, "vector index must be synced on prune"

    # retrieval still works after prune
    hits, debug = mem.score_and_rank("alpha food", now_tick=1)
    assert hits and hits[0][0].mem_id == p1["mem_id"]


def test_sync_keeps_nodes_still_in_authority(tmp_path):
    mem = AssociativeMemory("P1", HashEmbeddingModel(), SideStore(tmp_path, persist_vec=True))
    p = mem.prepare_write("observation", "gamma market", 5, 0, "morning", 0)
    mem.commit_write(p)
    mem.sync_from_refs([_ref(p["mem_id"], p["body_ref"], p["embed_ref"])])
    assert set(mem.nodes) == {p["mem_id"]}
