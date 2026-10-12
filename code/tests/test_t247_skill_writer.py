"""T247: `SKILL_OUTPUT.output_ref` 正文 writer port（life 侧 `SideStore`）。

覆盖：写入路径与 `output_ref`（`side://skill/<aid>/<skill_id>`，与 `life/settlement.py`
一字对齐）、读回、开关默认 true + override + env；关时由调用方不写（writer 本身不判开关）。
"""
from __future__ import annotations

import life.policy as P
from life.memory import SideStore


def test_skill_ref_matches_settlement_output_ref():
    # settlement: f"side://skill/{aid}/{skill_id}"
    assert SideStore.skill_ref("P001", "general") == "side://skill/P001/general"


def test_write_and_read_skill_body(tmp_path):
    st = SideStore(tmp_path, persist_vec=True)
    ref = st.write_skill("P001", "general", "练习：今日在作坊打了三件木器。")
    assert ref == "side://skill/P001/general"
    p = tmp_path / "skill" / "P001" / "general"
    assert p.exists()                                   # 路径与 ref 一字对齐（无扩展名）
    assert st.read_skill(ref) == "练习：今日在作坊打了三件木器。"


def test_skill_persist_switch_default_true_and_override(monkeypatch):
    monkeypatch.delenv("N50_SKILL_BODY", raising=False)
    P.set_skill_persist(None)
    assert P.skill_persist_enabled() is True            # 默认 true=行为不变
    P.set_skill_persist(False)
    assert P.skill_persist_enabled() is False
    P.set_skill_persist(None)
    monkeypatch.setenv("N50_SKILL_BODY", "0")
    assert P.skill_persist_enabled() is False
    P.set_skill_persist(None)                           # 复位
