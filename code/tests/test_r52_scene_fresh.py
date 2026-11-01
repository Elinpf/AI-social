# -*- coding: utf-8 -*-
"""R52 / B-8：处境锚「取值时点」修复（`HITT_SCENE_FRESH`）单测。

覆盖：
  1. **OFF 逐字节等价**：`LIFE_PROMPT_SCENE=1` + `HITT_SCENE_FRESH` 不设 ⇒ 指纹等于
     改动前本机实测冻结 sha（改一个空格/一个词即红）。
  2. **ON 只差场所那一段**：把 ON 行里的场所名换回快照场所名 ⇒ 逐字节回到 OFF 行。
  3. **ON 取实时场所/活动**：`ctx.scene.place` == 实时场所、`place_src == "live"`。
  4. **无移动时不产生任何差异**：快照场所 == 实时场所 ⇒ ON 提示词与 OFF 逐字节相同。
  5. **重取失败 → 回退快照**（不编造、不抛异常、不写 `place_src`）。
  6. **单变量边界**：`LIFE_PROMPT_SCENE` 关时 `HITT_SCENE_FRESH=1` 不得单独生效。
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.ports import TimeCoord, WorldView

CODE = Path(__file__).resolve().parents[1]
CONFIG = CODE / "config"
SLOT, ROUND = "afternoon", 7

#: 改动前（commit 029bb5c 树）本机实测冻结指纹：OFF 态必须逐字节相等
FROZEN_OFF = {
    "no_move": {
        "dialogue": "be1baf74f6d8cc96d0c2dacd2281bc7e510c98a483c9bcce06e9dc5777c975af",
        "reply": "882c0cce9ce374d4a9767ca779b593d09303e26febb36f2a2cea610823672a62",
        "ctx": "96f76ba0f994765555be391fa38d6485343504fed420b2e41214423b78a23c7b",
    },
    "stale": {
        "dialogue": "f0f21607e15ad3cfd1b403580c501dc025908367de7365a09bb9e85ec57ecb40",
        "reply": "3a33c540e4c96e6f0652ffedeb354ad4916967b61b7d8a4dd3484a28783bdb8b",
        "ctx": "b53fed1095b12727f2d36992dcb740a3b4da5395948604b2a344c61dbc48c470",
    },
    "stale_no_act": {
        "dialogue": "6831abf350b0239cf354a841aac47ad5ebe53e538044c116ec6fd3e6b226acc3",
        "reply": "a9691965be431f0c63fc88736346a65ae634249e54c9ff627701a50737cfa719",
        "ctx": "b1afba0ac032154e0962cc6b314c5f156b117d8254d953a776046a92e8ded185",
    },
}

FIXTURES = {
    "no_move": ("residence", "residence", "self_care"),
    "stale": ("residence", "library", "learn"),
    "stale_no_act": ("residence", "library", None),
}


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _time_coord() -> TimeCoord:
    return TimeCoord(week=1, day=3, day_of_week=1, day_type="workday", slot=SLOT, tick_in_slot=0)


def _wv(place: str, activity: str | None) -> WorldView:
    return WorldView(agent_id="P001", round=ROUND, time=_time_coord(), status="alive",
                     location=place, cash=100, net_worth=100,
                     current_activity=({"activity_type": activity, "place": place}
                                       if activity else None))


class _Kernel:
    def __init__(self, live_place: str, live_activity: str | None, boom: bool = False):
        self.live_place, self.live_activity, self.boom = live_place, live_activity, boom
        self.calls = 0

    def perceive(self, agent_id):
        self.calls += 1
        if self.boom:
            raise RuntimeError("perceive boom")
        return _wv(self.live_place, self.live_activity)

    def submit_intent(self, *a, **kw):  # pragma: no cover
        pass


def _agent(tmp_path: Path, kernel: _Kernel) -> LifeLayerAgent:
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    persona = load_personas(CONFIG / "personas.json")["P001"]
    ag = LifeLayerAgent("P001", persona, kernel, side_store=SideStore(tmp_path / "side"),
                        embedding=HashEmbeddingModel(), places=places,
                        peers=["P001", "P002"], peer_names={"P001": "沈砚", "P002": "赵四"})
    ag.needs = {"satiety": 55, "energy": 60, "social": 58,
                "esteem": 62, "mastery": 57, "leisure": 50}
    return ag


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("LIFE_PROMPT_SCENE", "1")
    monkeypatch.setenv("LIFE_PROMPT_NARRATION", "0")
    monkeypatch.delenv("HITT_SCENE_FRESH", raising=False)


def _prompts(ag, wv):
    d = ag._dialogue_prompt("tpl-1", ["P001", "P002"], wv=wv)
    r = ag._reply_prompt("P002", "tpl-1", [("赵四", "早上好。"), ("沈砚", "早啊。")], wv=wv)
    return d, r


# ---- 1. OFF 逐字节等价（改动前冻结指纹） ----------------------------------
@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_off_byte_identical_to_pre_change(tmp_path, name):
    snap, live, act = FIXTURES[name]
    ag = _agent(tmp_path, _Kernel(live, act))
    wv = _wv(snap, act)
    d, r = _prompts(ag, wv)
    ctx = ag._ctx_snapshot("P002", "tpl-1")
    frozen = FROZEN_OFF[name]
    assert _sha(d) == frozen["dialogue"], f"{name}: dialogue prompt 与改动前不一致"
    assert _sha(r) == frozen["reply"], f"{name}: reply prompt 与改动前不一致"
    assert _sha(json.dumps(ctx, ensure_ascii=False, sort_keys=True)) == frozen["ctx"]
    # OFF 态不得出现 R52 审计键
    assert "place_src" not in (ctx.get("scene") or {})
    # OFF 态刻意不读实时状态（取值路径未触达 perceive）
    assert ag.kernel.calls == 0


# ---- 2/3. ON 只差场所那一段 + 取实时场所/活动 ------------------------------
def test_on_differs_only_in_place_segment(tmp_path, monkeypatch):
    monkeypatch.setenv("HITT_SCENE_FRESH", "1")
    ag = _agent(tmp_path, _Kernel("library", "learn"))
    wv = _wv("residence", "learn")
    line_on = ag._scene_line(wv)
    audit_on = dict(ag._scene)
    monkeypatch.delenv("HITT_SCENE_FRESH")
    ag2 = _agent(tmp_path, _Kernel("library", "learn"))
    line_off = ag2._scene_line(wv)
    assert line_on != line_off
    assert "图书馆" in line_on and "住宅" not in line_on
    # 把 ON 行里的场所名换回快照场所名 ⇒ 逐字节回到 OFF 行
    assert line_on.replace("你在图书馆", "你在住宅") == line_off
    # 审计字段
    assert audit_on["place"] == "library"
    assert audit_on["place_src"] == "live"


def test_on_also_refreshes_activity(tmp_path, monkeypatch):
    """活动也按实时取：快照说 work、实时说 learn ⇒ 行里出现 learn 的措辞。"""
    monkeypatch.setenv("HITT_SCENE_FRESH", "1")
    ag = _agent(tmp_path, _Kernel("workshop", "learn"))
    wv = _wv("workshop", "work")
    line = ag._scene_line(wv)
    assert ag._scene["activity"] == "learn"
    assert "看" in line or "学" in line or "书" in line


# ---- 4. 无移动 ⇒ 无任何差异 ----------------------------------------------
def test_on_no_move_prompt_identical(tmp_path, monkeypatch):
    monkeypatch.setenv("HITT_SCENE_FRESH", "1")
    ag = _agent(tmp_path, _Kernel("residence", "self_care"))
    d_on, r_on = _prompts(ag, _wv("residence", "self_care"))
    monkeypatch.delenv("HITT_SCENE_FRESH")
    ag2 = _agent(tmp_path, _Kernel("residence", "self_care"))
    d_off, r_off = _prompts(ag2, _wv("residence", "self_care"))
    assert (d_on, r_on) == (d_off, r_off)


# ---- 5. 重取失败 ⇒ 回退快照 ---------------------------------------------
def test_on_perceive_failure_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("HITT_SCENE_FRESH", "1")
    ag_fail = _agent(tmp_path, _Kernel("library", "learn", boom=True))
    line_fail = ag_fail._scene_line(_wv("residence", "learn"))
    audit_fail = dict(ag_fail._scene)
    monkeypatch.delenv("HITT_SCENE_FRESH")
    ag_off = _agent(tmp_path, _Kernel("library", "learn"))
    line_off = ag_off._scene_line(_wv("residence", "learn"))
    assert line_fail == line_off          # 回退到快照，不编造
    assert audit_fail["place"] == "residence"
    assert "place_src" not in audit_fail


# ---- 6. 单变量边界：SCENE 关 ⇒ FRESH 不得单独生效 ------------------------
def test_fresh_without_scene_is_noop(tmp_path, monkeypatch):
    monkeypatch.delenv("LIFE_PROMPT_SCENE", raising=False)
    monkeypatch.setenv("HITT_SCENE_FRESH", "1")
    ag = _agent(tmp_path, _Kernel("library", "learn"))
    assert ag._scene_line(_wv("residence", "learn")) == ""
    assert ag._scene is None
    assert ag.kernel.calls == 0
