"""T228b: `SideStore.persist_vec` + 检索降级标记（life 侧）。

覆盖：默认落 `.vec`（行为不变）、关闭不落且 read_embed→None、policy/env 开关、
无向量时检索降级为 lexical 且打 `vec_available=false`/`retrieval_mode` 标记。
"""
from __future__ import annotations

import life.policy as P
from life.memory import AssociativeMemory, HashEmbeddingModel, SideStore


def test_persist_vec_default_on_writes_vec(tmp_path):
    st = SideStore(tmp_path, persist_vec=True)
    _br, vr = st.write("P1", "M1", "hello", [0.1, 0.2])
    assert (tmp_path / "mem" / "P1" / "M1.vec").exists()
    assert st.read_embed(vr) == [0.1, 0.2]


def test_persist_vec_off_skips_vec_and_read_embed_none(tmp_path):
    st = SideStore(tmp_path, persist_vec=False)
    _br, vr = st.write("P1", "M1", "hello", [0.1, 0.2])
    assert (tmp_path / "mem" / "P1" / "M1.txt").exists()      # 正文必留（#10 数据资产）
    assert not (tmp_path / "mem" / "P1" / "M1.vec").exists()  # 向量不落
    assert st.read_embed(vr) is None                          # 显式 None，不抛不静默


def test_policy_switch_default_true_and_override(tmp_path, monkeypatch):
    monkeypatch.delenv("N50_VEC", raising=False)
    P.set_persist_vec(None)
    assert P.persist_vec_enabled() is True
    P.set_persist_vec(False)
    assert P.persist_vec_enabled() is False
    P.set_persist_vec(None)
    monkeypatch.setenv("N50_VEC", "0")
    assert P.persist_vec_enabled() is False
    monkeypatch.setenv("N50_VEC", "1")
    P.set_persist_vec(None)
    assert P.persist_vec_enabled() is True
    P.set_persist_vec(None)


def test_retrieval_degrades_to_lexical_and_marks(tmp_path):
    mem = AssociativeMemory("P1", HashEmbeddingModel(), SideStore(tmp_path, persist_vec=False))
    payload = mem.prepare_write("observation", "hello world party", 5, 0, "morning", 0)
    mem.commit_write(payload)  # read_embed→None → embed=[]（降级输入）
    _hits, debug = mem.score_and_rank("party", now_tick=1)
    assert debug["vec_available"] is False
    assert debug["retrieval_mode"] == "lexical"


def test_retrieval_vector_mode_when_persisted(tmp_path):
    mem = AssociativeMemory("P1", HashEmbeddingModel(), SideStore(tmp_path, persist_vec=True))
    payload = mem.prepare_write("observation", "hello world party", 5, 0, "morning", 0)
    mem.commit_write(payload)
    _hits, debug = mem.score_and_rank("party", now_tick=1)
    assert debug["vec_available"] is True
    assert debug["retrieval_mode"] == "vector"
