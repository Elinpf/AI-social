"""T247: emit-observer 端口（`life/side_emit.py`）单测。

覆盖：SKILL_OUTPUT → 写 side 正文（路径与 output_ref 对齐）；关开关 → 不写；
非 SKILL_OUTPUT 忽略；read-only（不改传入记录）。
"""
from __future__ import annotations

import life.policy as P
from life.side_emit import make_emit_observer


def _rec(aid="P001", sid="general", q=2):
    return {"type": "SKILL_OUTPUT", "round": 5, "actor": aid,
            "payload": {"agent_id": aid, "skill_id": sid,
                        "output_ref": f"side://skill/{aid}/{sid}", "quality": q,
                        "day": 0, "slot": "morning"}}


def test_observer_writes_skill_body(tmp_path, monkeypatch):
    monkeypatch.delenv("N50_SKILL_BODY", raising=False)
    P.set_skill_persist(None)
    obs = make_emit_observer(tmp_path)
    obs([_rec()])
    p = tmp_path / "skill" / "P001" / "general"
    assert p.exists()
    assert "general" in p.read_text(encoding="utf-8")
    P.set_skill_persist(None)


def test_observer_off_writes_nothing(tmp_path):
    P.set_skill_persist(False)
    obs = make_emit_observer(tmp_path)
    obs([_rec()])
    assert not (tmp_path / "skill").exists()        # 关开关 → 不落文件
    P.set_skill_persist(None)


def test_observer_ignores_non_skill_and_is_readonly(tmp_path, monkeypatch):
    monkeypatch.delenv("N50_SKILL_BODY", raising=False)
    P.set_skill_persist(None)
    obs = make_emit_observer(tmp_path)
    recs = [{"type": "MEMORY_WRITE", "payload": {"agent_id": "P001"}}]
    before = [dict(r) for r in recs]
    obs(recs)
    assert recs == before                            # read-only：未改事件
    assert not (tmp_path / "skill").exists()
    P.set_skill_persist(None)
