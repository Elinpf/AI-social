"""D2.10 端到端（life 级、无 LLM、无跑批）：**公开场合接话**真的落到 `reply_to` 非空。

用 `mini_kernel` + 真 `LifeLayerAgent`（沿用 `test_t224_agent_wiring.py` 的装配方式），
只把 `llm.call` 与 `kernel.submit_intent` 换成 test-double ⇒ 不动世界、不调模型、确定性。

钉住三件事：
1. **开关开 + 同场** ⇒ `_communicate` 走「接话」分支：`scope=global`、`reply_to=被接的 msg_uid`、
   `thread_id` 沿用发起线程、`turn_index = 1`、`participants` 含发起人与我；
2. **开关关** ⇒ 完全不走接话（回到「发起新对话」或不发声），且 `reply_to` 不会是公开话的 uid；
3. **不同场 ⇒ 不接**（同场判据真的在起作用，而不是「只要开就接」）。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import public_reply as PR
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"
PUB_UID = "42:53"


def _places() -> dict:
    return {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}


def _agent(tmp: Path, monkeypatch, me: str = "P003"):
    places = _places()
    persona = load_personas(CONFIG / "personas.json")[me]
    kernel = MiniKernel(seed=7, places=places)
    agent = LifeLayerAgent(me, persona, kernel, side_store=SideStore(tmp / "side"),
                           embedding=HashEmbeddingModel(), places=places)
    sent: list = []
    kernel.submit_intent = lambda aid, intent: (sent.append(intent),
                                                SimpleNamespace(ok=True, reason=""))[1]
    agent.llm.call = lambda *a, **k: SimpleNamespace(text="嗯，我也这么想。")
    agent._plan_slots = {f"day0-{s}": {"place": "cafe", "activity_type": "work"}
                         for s in ("morning", "afternoon", "evening", "night")}
    return agent, sent


def _payload(body: str = "作者", place: str = "cafe") -> dict:
    return {"author": "P002", "msg_id": "P-0-0", "msg_uid": PUB_UID, "body": body,
            "participants": ["P002"], "place_ctx": place, "place": None,
            "thread_id": "TH-P002-PUB-0-0", "turn_index": 0, "reply_to": None,
            "topic": "skill_practice", "tag_hints": ["skill_practice"],
            "ctx": {"topic": "skill_practice", "mood": "平和", "relation": 0,
                    "need": {"social": 45}, "trigger": "skill_practice", "initiator": "P002"}}


def _wv(round_no: int = 0, day: int = 0, slot: str = "morning", events=()):
    return SimpleNamespace(round=round_no, time=SimpleNamespace(day_of_week=day, slot=slot),
                           visible_events=list(events), memory_refs={}, cash=10 ** 6)


def _pub_event(payload: dict, round_no: int = 0):
    return SimpleNamespace(type="MSG_PUBLIC", payload=payload, round=round_no,
                           actor=payload["author"], seq=1, hash="sha256:x")


def _social(sent):
    return [i for i in sent if i.intent_class.upper().endswith("SOCIAL")]


# ---------------------------------------------------------------- 1) 开 + 同场
def test_on_same_place_reply_carries_reply_to(tmp_path, monkeypatch):
    monkeypatch.setenv(PR.ENV, "1")
    agent, sent = _agent(tmp_path, monkeypatch)
    agent._communicate(_wv(events=[_pub_event(_payload())]))
    soc = _social(sent)
    assert soc, "开关开 + 同场 ⇒ 应产生一次社交意图（接话）"
    p = soc[-1].payload
    assert p["reply_to"] == PUB_UID, p
    assert p["scope"] == "global", p
    assert p["thread_id"] == "TH-P002-PUB-0-0"
    assert p["turn_index"] == 1
    assert set(p["participants"]) == {"P002", "P003"}


# ---------------------------------------------------------------- 2) 关 ⇒ 不接
def test_off_does_not_reply_to_public(tmp_path, monkeypatch):
    monkeypatch.delenv(PR.ENV, raising=False)
    agent, sent = _agent(tmp_path, monkeypatch)
    agent._communicate(_wv(events=[_pub_event(_payload())]))
    for i in _social(sent):
        assert i.payload.get("reply_to") != PUB_UID, i.payload


# ---------------------------------------------------------------- 3) 开但不同场
def test_on_different_place_no_reply(tmp_path, monkeypatch):
    monkeypatch.setenv(PR.ENV, "1")
    agent, sent = _agent(tmp_path, monkeypatch)
    agent._communicate(_wv(events=[_pub_event(_payload(place="market"))]))
    for i in _social(sent):
        assert i.payload.get("reply_to") != PUB_UID, i.payload


# ------------------------------- 4) DM 路径逐字节等价（②③ 的不回归证据）
def _dm_event():
    p = {"from": "P002", "to": "P003", "msg_id": "D-0-0", "msg_uid": "42:60",
         "body": "去不去集市？", "participants": ["P002", "P003"], "place": "cafe",
         "thread_id": "TH-P002-P003-0", "turn_index": 0, "reply_to": None,
         "topic": "gift", "tag_hints": ["gift"],
         "ctx": {"topic": "gift", "mood": "平和", "relation": 0,
                 "need": {"social": 45}, "trigger": "gift", "initiator": "P002"}}
    return SimpleNamespace(type="MSG_DM", payload=p, round=0, actor="P002", seq=1,
                           hash="sha256:y")


def _dm_reply_payload(tmp_path, monkeypatch, on: bool) -> dict:
    if on:
        monkeypatch.setenv(PR.ENV, "1")
    else:
        monkeypatch.delenv(PR.ENV, raising=False)
    agent, sent = _agent(tmp_path, monkeypatch)
    agent._communicate(_wv(events=[_dm_event()]))
    soc = _social(sent)
    assert soc, "DM 线程必须照旧接话（不回归）"
    return soc[-1].payload


def test_dm_reply_payload_identical_on_vs_off(tmp_path, monkeypatch):
    """DM 回话在开关开/关下**逐键相同** ⇒ 本臂不改 DM 路径（S-4 指针覆盖不会掉）。"""
    off = _dm_reply_payload(tmp_path / "off", monkeypatch, on=False)
    on = _dm_reply_payload(tmp_path / "on", monkeypatch, on=True)
    assert off == on, {k: (off.get(k), on.get(k)) for k in set(off) | set(on)
                       if off.get(k) != on.get(k)}
    assert off["reply_to"] == "42:60" and off["scope"] == "private"
