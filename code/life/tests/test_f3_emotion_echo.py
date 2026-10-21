"""F-3「情绪呼应」（empathic echo）单测：OFF 路径不生效 / ON 路径生效。

覆盖两条硬要求：
  1. **OFF（默认）路径逐字节不变**：不产 `ctx.echo` 键、提示词不多一个字；
  2. **ON 路径生效**：判定（语面极性 > 处境情绪）+ 强度确定性推导 + 提示词插入 + 审计字段。
判定与强度全部纯函数（不调 LLM）；接线点在 `LifeLayerAgent._send_reply`。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import dialogue_threads as DT
from life import emotion_echo as EE
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.ports import EventView, IntentResult
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"


# ---------------------------------------------------------------- fixtures
@pytest.fixture(autouse=True)
def _reset_config_cache():
    """每个用例前后清缓存/覆盖，避免相邻用例互相污染（env 与 json 两条来源）。"""
    EE.set_override(None)
    yield
    EE.set_override(None)


def _places() -> dict:
    return {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}


def _build(tmp: Path):
    places = _places()
    personas = load_personas(CONFIG / "personas.json")
    persona = personas["P003"]
    kernel = MiniKernel(seed=7, places=places)
    kernel._emit("AGENT_BORN", {"agent_id": "P003", "home_place": persona.home_place,
                                "needs_init": persona.needs_init}, phase=0, actor="SYSTEM")
    kernel._emit("AGENT_BORN", {"agent_id": "P007",
                                "home_place": personas["P007"].home_place,
                                "needs_init": personas["P007"].needs_init},
                 phase=0, actor="SYSTEM")
    agent = LifeLayerAgent("P003", persona, kernel, side_store=SideStore(tmp / "side"),
                           embedding=HashEmbeddingModel(), places=places,
                           peer_names={"P007": "阿禾"})
    return kernel, agent


class _RecLLM:
    """确定性 LLM 替身：记录提示词，固定返回一句话（不联网、不随机）。"""

    name = "rec-llm"

    def __init__(self, text: str = "你先歇会儿，我陪你坐一会儿。"):
        self.text = text
        self.prompts: list[str] = []

    def call(self, purpose, prompt, *, model=None, meta=None):
        self.prompts.append(prompt)
        return SimpleNamespace(text=self.text)


def _dm_event(body: str, mood: str | None, *, seq: int = 5, round_no: int = 4) -> EventView:
    payload = {"msg_id": "D-4-P007-P003", "msg_uid": "D-4-P007-P003-u1", "from": "P007",
               "to": "P003", "body": body, "refs": [], "tag_hints": ["chat"],
               "thread_id": "TH-P007-P003-4", "turn_index": 0, "reply_to": None,
               "participants": ["P003", "P007"], "topic": "闲聊",
               "ctx": {"relation": 0, "topic": "闲聊"}}
    if mood is not None:
        payload["ctx"]["mood"] = mood
    return EventView(seq=seq, round=round_no, phase=2, actor="P007", type="MSG_DM",
                     payload=payload, place="residence")


def _wv(ev: EventView):
    return SimpleNamespace(round=ev.round, visible_events=[ev],
                           time=SimpleNamespace(slot="morning", day_of_week=0, day=0))


def _reply(agent, ev: EventView):
    """跑一次 `_send_reply`，返回 (提示词, 提交的 INTENT.SOCIAL payload)。"""
    rec = _RecLLM()
    agent.llm = rec
    captured: list[dict] = []
    agent.kernel.submit_intent = lambda aid, intent: (captured.append(intent.payload)
                                                      or IntentResult(ok=True, reason=None,
                                                                      event_seqs=()))
    ok = agent._send_reply(_wv(ev), ev, DT.DEFAULTS, "day0-morning")
    assert ok is True
    assert len(rec.prompts) == 1
    assert len(captured) == 1
    return rec.prompts[0], captured[0]


# ---------------------------------------------------------------- 开关语义
def test_switch_default_off(monkeypatch):
    monkeypatch.delenv(EE.ECHO_ENV, raising=False)
    EE.reload()
    assert EE.enabled() is False, "默认必须 OFF"
    assert EE.load_params()["enabled"] is False
    assert EE.plan("低落", "心里挺委屈") is None


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "on", "yes", " on "])
def test_switch_env_on_values(monkeypatch, val):
    monkeypatch.setenv(EE.ECHO_ENV, val)
    EE.reload()
    assert EE.enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "2", "enable"])
def test_switch_env_off_values(monkeypatch, val):
    """**空串与拼错的值都算关**（不允许"看着像开"的值意外打开机制）。"""
    monkeypatch.setenv(EE.ECHO_ENV, val)
    EE.reload()
    assert EE.enabled() is False


def test_json_default_is_false_in_config_file():
    data = json.loads((CONFIG / "emotion_echo.json").read_text(encoding="utf-8"))
    assert data["enabled"] is False


# ---------------------------------------------------------------- 判定（纯函数）
def test_detect_mood_only_deterministic():
    p = EE.load_params()
    d1 = EE.detect("低落", "", p)
    d2 = EE.detect("低落", "", p)
    assert d1 == d2, "同一入参必须给出同一结论（确定性）"
    assert d1["sign"] == -1 and d1["source"] == "mood" and d1["kind"] == "soothe"
    assert d1["intensity"] == EE.MOOD_PROFILE["低落"][1]


def test_detect_text_overrides_mood_polarity():
    """语面极性优先：对方说「心里挺委屈」，即使 ctx.mood 缺失/平和，也判负向。"""
    p = EE.load_params()
    d = EE.detect("平和", "今天真是累，心里挺委屈", p)
    assert d["sign"] == -1
    assert d["source"] == "text"           # 平和严重度 0 ⇒ 不带 mood 加成
    assert d["intensity"] == p["text_hit_intensity"]


def test_detect_text_plus_mood_bonus_is_integer_and_clamped():
    p = EE.load_params()
    d = EE.detect("孤单", "心里挺委屈", p)
    assert d["source"] == "text+mood"
    assert d["intensity"] == p["text_hit_intensity"] + EE.MOOD_PROFILE["孤单"][1] // p["mood_bonus_div"]
    assert 0 <= d["intensity"] <= 100


def test_detect_neutral_yields_no_echo():
    p = EE.load_params()
    p["enabled"] = True
    d = EE.detect("平和", "灶上还温着粥", p)
    assert d["sign"] == 0 and d["kind"] == "none"
    assert EE.plan("平和", "灶上还温着粥", p) is None


def test_min_intensity_gates_plan():
    p = EE.load_params()
    p["enabled"], p["min_intensity"] = True, 100
    assert EE.plan("浮躁", "", p) is None, "强度 40 < 阈值 100 ⇒ 不呼应"
    p["min_intensity"] = 30
    assert EE.plan("浮躁", "", p) is not None


def test_tier_cuts_are_text_only():
    p = EE.load_params()
    assert EE.tier_of(29, p["tier_cuts"]) == "轻"
    assert EE.tier_of(45, p["tier_cuts"]) == "明显"
    assert EE.tier_of(70, p["tier_cuts"]) == "很强"


def test_prompt_line_empty_without_plan():
    assert EE.prompt_line(None) == ""
    assert EE.audit(None) is None


# ---------------------------------------------------------------- OFF 路径（字节级不变）
def test_off_path_prompt_and_payload_byte_identical(tmp_path, monkeypatch):
    monkeypatch.delenv(EE.ECHO_ENV, raising=False)
    EE.reload()
    kernel, agent = _build(tmp_path)
    ev = _dm_event("今天真是累，心里挺委屈", "低落")

    prompt_off, payload_off = _reply(agent, ev)

    # ① 不追加任何键（ctx 里既不出现 echo，其它键也不变）
    assert "echo" not in payload_off["ctx"]
    # ② 提示词与「根本没有本机制」时逐字节相同（同一 agent 重算，不带 echo_line）
    history = agent._thread_history(_wv(ev), ev.payload["thread_id"], DT.DEFAULTS)
    baseline = agent._reply_prompt("P007", "闲聊", history, DT.DEFAULTS, wv=_wv(ev))
    assert prompt_off == baseline
    assert "接住" not in prompt_off


def test_off_path_other_switches_do_not_leak(tmp_path, monkeypatch):
    """env 拼错/置 0 也必须落到 OFF 路径（防"看着像开"）。"""
    for val in ("0", "off", "", "true1"):
        monkeypatch.setenv(EE.ECHO_ENV, val)
        EE.reload()
        kernel, agent = _build(tmp_path / val.replace("/", "_") or "empty")
        ev = _dm_event("心里挺委屈", "低落")
        prompt, payload = _reply(agent, ev)
        assert "echo" not in payload["ctx"]
        assert "接住" not in prompt


# ---------------------------------------------------------------- ON 路径（生效）
def test_on_path_injects_prompt_and_audit(tmp_path, monkeypatch):
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    kernel, agent = _build(tmp_path)
    ev = _dm_event("今天真是累，心里挺委屈", "低落")

    prompt_on, payload_on = _reply(agent, ev)

    # ① 提示词里确实多了那句处境提示（含对方显示名，不给现成句式）
    assert "接住这份情绪" in prompt_on
    assert "阿禾" in prompt_on
    # ② 审计键存在且可复算
    a = payload_on["ctx"]["echo"]
    assert a["v"] == EE.VERSION
    assert a["sign"] == -1 and a["kind"] == "soothe" and a["prompted"] is True
    expected = EE.detect("低落", "今天真是累，心里挺委屈", EE.load_params())
    assert a["intensity"] == expected["intensity"]
    assert a["tier"] == expected["tier"]
    # ③ 与 OFF 提示词的关系：ON = OFF + 插入那一段（其余段落不变）
    off_prompt = prompt_on.replace(EE.prompt_line(expected, "阿禾"), "")
    history = agent._thread_history(_wv(ev), ev.payload["thread_id"], DT.DEFAULTS)
    baseline = agent._reply_prompt("P007", "闲聊", history, DT.DEFAULTS, wv=_wv(ev))
    assert off_prompt == baseline


def test_on_path_no_key_when_neutral(tmp_path, monkeypatch):
    """ON 但对方没情绪（平和的日常话）⇒ 仍不产键、不加字（宁缺毋滥）。"""
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    kernel, agent = _build(tmp_path)
    ev = _dm_event("灶上还温着粥，你吃了吗", None)
    prompt, payload = _reply(agent, ev)
    assert "echo" not in payload["ctx"]
    assert "接住这份情绪" not in prompt


def test_on_path_does_not_touch_other_payload_keys(tmp_path, monkeypatch):
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    kernel, agent = _build(tmp_path)
    ev = _dm_event("心里挺委屈", "低落")
    _, on_payload = _reply(agent, ev)

    monkeypatch.delenv(EE.ECHO_ENV, raising=False)
    EE.reload()
    kernel2, agent2 = _build(tmp_path / "off")
    ev2 = _dm_event("心里挺委屈", "低落")
    _, off_payload = _reply(agent2, ev2)

    assert set(on_payload) == set(off_payload), "顶层键集合必须完全不增不减"
    assert set(on_payload["ctx"]) - set(off_payload["ctx"]) == {"echo"}, "只允许 ctx 内**追加**一个键"
    assert {k: v for k, v in on_payload.items() if k != "ctx"} == {
        k: v for k, v in off_payload.items() if k != "ctx"}
    assert {k: v for k, v in on_payload["ctx"].items() if k != "echo"} == {
        k: v for k, v in off_payload["ctx"].items() if k != "echo"}
