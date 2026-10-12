"""T265-adjacent perf guards for `memory.score_and_rank` (Leader-approved ①/②/④).

The optimisations (cached norms ①, relevance cache ④, optional numpy batch dot ②)
must be **ranking-preserving**: for the same query the ordered (mem_id, score)
list must be byte-for-byte identical to the pre-change algorithm (full scan +
`cosine`), including the total-order tie-break. This test pins that contract.

It is deliberately engine-free and fast (~200 nodes) so it runs in any suite.
"""
from __future__ import annotations

import random

from life.memory import AssociativeMemory, HashEmbeddingModel, MemoryNode, _tokenize, cosine


class _NoSide:  # nodes are built directly; side storage is never touched
    pass


def _reference_rank(mem, query_text, now_tick, top_k):
    """The exact pre-change algorithm (no caches, plain `cosine`)."""
    p = mem.params
    w = {"w_rec": p["w_rec"], "w_imp": p["w_imp"], "w_rel": p["w_rel"]}
    decay = p["decay"]
    q = mem.embedding.embed(query_text)
    qt = set(_tokenize(query_text))
    scored = []
    for node in mem.nodes.values():
        recency = decay ** max(0, now_tick - node.last_access)
        imp = node.importance / 10.0
        if node.embed:
            rel = cosine(q, node.embed)
        else:
            nt = set(_tokenize(node.text))
            rel = (len(qt & nt) / len(qt)) if qt else 0.0
        scored.append((node, w["w_rec"] * recency + w["w_imp"] * imp + w["w_rel"] * rel))
    scored.sort(key=lambda t: (-t[1], -t[0].last_access, t[0].mem_id))
    return [(n.mem_id, s) for n, s in scored[:top_k]]


def _build(n=200, seed=7):
    rng = random.Random(seed)
    emb = HashEmbeddingModel()
    mem = AssociativeMemory("A1", emb, _NoSide())
    prev = None
    for i in range(n):
        # every 4th node duplicates the previous vector -> forces exact ties,
        # which is exactly where a naive rewrite would reorder results.
        if i % 4 == 3 and prev is not None:
            vec = list(prev)
        else:
            vec = [rng.uniform(-1, 1) for _ in range(64)]
        prev = vec
        node = MemoryNode(
            mem_id=f"M-A1-{i:06d}", agent_id="A1", kind="observation",
            text=f"note {i} food {i % 7}", importance=rng.randint(1, 10),
            day=i // 8, slot="midday", embed=vec, last_access=rng.randint(0, 200),
        )
        mem.nodes[node.mem_id] = node
        mem._register(node)
    return mem


def test_rank_identical_to_reference_including_ties():
    mem = _build()
    queries = [f"food {k}" for k in range(7)] + ["note 3", "", "tool market"]
    for qtext in queries:
        got, _ = mem.score_and_rank(qtext, 200)
        got = [(n.mem_id, s) for n, s in got]
        exp = _reference_rank(mem, qtext, 200, mem.params["top_k"])
        # exact float equality AND exact order (tie-break included)
        assert got == exp, f"ranking drifted for query {qtext!r}"


def test_cache_does_not_change_repeated_query():
    mem = _build()
    q = "food 3"
    first = [(n.mem_id, s) for n, s in mem.score_and_rank(q, 200)[0]]
    second = [(n.mem_id, s) for n, s in mem.score_and_rank(q, 200)[0]]
    assert first == second
