"""T268: shared immutable source hub — storage de-dup **without** changing
information boundaries or per-agent memory sets.

Guards the two hard constraints from the Leader:
  1. sharing is *storage*, not *visibility* — each agent's resolvable refs are
     still exactly the ones ITS OWN MEMORY_WRITE produced;
  2. the read API stays per-agent (no cross-agent resolution entry point).
"""
from __future__ import annotations

import hashlib

from life.memory import AssociativeMemory, HashEmbeddingModel, SideStore


class _Side(SideStore):
    pass


def test_write_shared_dedups_identical_text(tmp_path):
    st = SideStore(tmp_path, persist_vec=True)
    r1 = st.write_shared("X 在广场 开始 干活。", [0.1, 0.2])
    r2 = st.write_shared("X 在广场 开始 干活。", [0.1, 0.2])
    assert r1 == r2
    h = hashlib.sha256("X 在广场 开始 干活。".encode()).hexdigest()
    assert r1[0] == f"side://src/{h}.txt"
    # one shared blob on disk, not two copies
    assert len(list((tmp_path / "src").glob("*.txt"))) == 1


def test_shared_read_returns_same_object(tmp_path):
    st = SideStore(tmp_path, persist_vec=True)
    br, vr = st.write_shared("same body", [0.3, 0.4])
    assert st.read_body(br) is st.read_body(br)      # cached, shared object
    assert st.read_embed(vr) is st.read_embed(vr)


def test_vector_mode_preserved_with_shared_store(tmp_path):
    mem = AssociativeMemory("P1", HashEmbeddingModel(), SideStore(tmp_path, persist_vec=True))
    payload = mem.prepare_write("observation", "hello world party", 5, 0, "morning", 0)
    mem.commit_write(payload)
    _hits, debug = mem.score_and_rank("party", now_tick=1)
    assert debug["vec_available"] is True and debug["retrieval_mode"] == "vector"


# NOTE: engine-level assertions (per-agent ref subset / real sharing) live in
# `code/tests/test_t268_shared_source_engine.py` — the life package is not
# allowed to import `orchestration` (see .importlinter).
