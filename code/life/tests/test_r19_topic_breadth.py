"""R19 话题宽度臂（TB）单测：OFF 逐字节不变 / ON 人话化 + 岔题 / 内容门控双条件。

覆盖五条硬要求：
  1. **OFF（默认）**：提示词与不开启时**完全相同**、payload 不出现 `ctx.topic_breadth`、
     `tag_hints` 不追加任何 tag；
  2. **人话化**：ON 时 `whisper` 这类内部 token 不再出现在提示词里（L-13 的正解）；
  3. **岔题**：ON 且 `turn>=1` 时提示词多出一段「可以顺带把话带到 X」，去掉该段后与 OFF 逐字节相等；
  4. **内容门控（双条件）**：正文命中 shift 关键词才追加 tag；命中 base 关键词则**不**追加；
  5. **确定性**：同一 (agent|thread|round|turn|base) ⇒ 同一岔题指派（可 replay）。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import dialogue_threads as DT
from life import topic_breadth as TB
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.ports import EventView, IntentResult
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"


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
    name = "rec-llm"

    def __init__(self, text: str):
        self.text = text
        self.prompts: list[str] = []

    def call(self, purpose, prompt, *, model=None, meta=None):
        self.prompts.append(prompt)
        return SimpleNamespace(text=self.text)


def _dm_event(topic: str = "whisper", *, tag: str | None = None) -> EventView:
    payload = {"msg_id": "D-4-P007-P003", "msg_uid": "D-4-P007-P003-u1", "from": "P007",
               "to": "P003", "body": "今儿个有点乏。", "refs": [],
               "tag_hints": [tag or topic], "thread_id": "TH-P007-P003-4", "turn_index": 0,
               "reply_to": None, "participants": ["P003", "P007"], "topic": topic,
               "ctx": {"relation": 0, "topic": topic, "mood": "平和"}}
    return EventView(seq=5, round=4, phase=2, actor="P007", type="MSG_DM",
                     payload=payload, place="residence")


def _wv(ev: EventView):
    return SimpleNamespace(round=ev.round, visible_events=[ev], location="cafe",
                           current_activity=None, inventory=(),
                           time=SimpleNamespace(slot="morning", day_of_week=0, day=0))


def _reply(agent, wv, text: str):
    ev = wv.visible_events[0]
    rec = _RecLLM(text)
    agent.llm = rec
    captured: list[dict] = []
    agent.kernel.submit_intent = lambda aid, intent: (captured.append(intent.payload)
                                                      or IntentResult(ok=True, reason=None,
                                                                      event_seqs=()))
    ok = agent._send_reply(wv, ev, DT.DEFAULTS, "day0-morning")
    assert ok is True
    return rec.prompts[0], captured[0]


# ---------------------------------------------------------------- 开关
def test_switch_default_off(monkeypatch):
    monkeypatch.delenv(TB.BREADTH_ENV, raising=False)
    assert TB.enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "on", "yes", " on "])
def test_switch_env_on(monkeypatch, val):
    monkeypatch.setenv(TB.BREADTH_ENV, val)
    assert TB.enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "2", "enable"])
def test_switch_env_off(monkeypatch, val):
    monkeypatch.setenv(TB.BREADTH_ENV, val)
    assert TB.enabled() is False


# ---------------------------------------------------------------- 纯函数
def test_label_humanizes_known_and_passes_unknown():
    assert TB.label("whisper") == "说悄悄话"
    assert TB.label("combat_training") == "练功"
    assert TB.label("unknown_topic_x") == "unknown_topic_x"   # 不臆造、不丢信息
    assert TB.label(None) == ""


def test_plan_deterministic_turn_gate_and_no_transactional_shift():
    a = TB.plan("P003", "TH-P007-P003-4", 12, 1, "skill_practice")
    b = TB.plan("P003", "TH-P007-P003-4", 12, 1, "skill_practice")
    assert a == b
    assert TB.plan("P003", "TH-P007-P003-4", 12, 0, "skill_practice") is None, "turn<1 不岔题"
    assert TB.plan("P003", "TH", 12, 1, None) is None
    # 岔题候选永远不选事务性 tag（否则会从后门改 F-1 闲聊率）
    for base in TB.ADJACENT:
        for i in range(40):
            p = TB.plan("P003", f"TH-{i}", 12, 1 + i % 3, base)
            if p:
                assert p["shift"] not in TB._TRANSACTIONAL, (base, p)


def test_render_contains_shift_label():
    p = {"v": "tb/1", "base": "gift", "shift": "whisper", "turn": 1}
    line = TB.render(p)
    assert "说悄悄话" in line and line.startswith("\n聊着聊着")
    assert TB.render(None) == ""


def test_confirm_dual_condition():
    # 命中 shift 且不命中 base ⇒ True
    assert TB.confirm("捎给你一包点心", "gift", "whisper") is True
    # 命中 shift 也命中 base ⇒ False（本来就在说这个，不算岔过去）
    assert TB.confirm("捎给你一包点心，别声张", "gift", "whisper") is False
    # 两个都不命中 ⇒ False
    assert TB.confirm("今儿天真好", "gift", "whisper") is False
    # 单条件调用（排查用）
    assert TB.confirm("说得我都不好意思了，捎给你吧", "gift") is True


def test_keywords_no_low_information_phrases():
    """门控正则不得含无差别高频短语（board-scout 预警的 9.6% 白送来源）。"""
    banned = ("给你", "听说", "力气", "一定", "拿着", "送去", "教你")  # 「留了一包」是合格短语，故不列 "留了"
    for topic, pat in TB.TOPIC_KEYWORDS.items():
        for b in banned:
            assert b not in pat, f"{topic} 仍含低区分度词 {b}"
        # 每个话题都必须有「典型说法」且该说法确实能被自己的正则命中（自洽性）
        sample = TB.SAMPLE_PHRASES.get(topic)
        assert sample, f"{topic} 缺 SAMPLE_PHRASES"
        import re as _re
        assert _re.search(pat, sample), f"{topic} 的典型说法命中不了自己的正则：{sample}"


# ---------------------------------------------------------------- 接线：OFF / ON
def test_off_path_prompt_and_payload_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv(TB.BREADTH_ENV, raising=False)
    monkeypatch.setenv(TB.LABEL_ENV, "off")   # L-13 补丁：人话化默认 ON，故此处显式回退
    _, agent = _build(tmp_path)
    wv = _wv(_dm_event())
    prompt, payload = _reply(agent, wv, "我这心里也堵着事，先听你说。")
    assert "whisper" in prompt, "OFF 时 topic 仍原样进提示词（逐字节不变）"
    assert "聊着聊着" not in prompt
    assert "topic_breadth" not in (payload.get("ctx") or {})
    assert payload["tag_hints"] == ["whisper"], "OFF 时不得追加任何 tag"


def _first_shifting_turn(agent_id: str = "P003", thread: str = "TH-P007-P003-4",
                         base: str = "whisper") -> int:
    """找一个「会岔题」的 turn（`sha256 % 3 == 0` 的 1/3 条按设计不岔，测试不与之撞车）。"""
    for t in range(1, 12):
        if TB.plan(agent_id, thread, 4, t, base) is not None:
            return t
    raise AssertionError("找不到会岔题的 turn，设计异常")


def test_on_path_humanizes_topic(tmp_path, monkeypatch):
    monkeypatch.delenv(TB.BREADTH_ENV, raising=False)
    monkeypatch.setenv(TB.LABEL_ENV, "off")   # L-13 补丁：基准臂 = 旧字节（原样 token）
    _, agent = _build(tmp_path)
    turn = _first_shifting_turn()
    # 让 _thread_max_turn 返回 turn-1 ⇒ 本条 turn_index = turn（L-7 结构臂与 turn 有关，两臂必须同 turn）
    agent._thread_max_turn = lambda _wv, _tid: turn - 1
    wv = _wv(_dm_event())
    prompt_off, _ = _reply(agent, wv, "嗯。")

    monkeypatch.setenv(TB.BREADTH_ENV, "1")
    monkeypatch.delenv(TB.LABEL_ENV, raising=False)   # 人话化默认 ON
    prompt_on, payload = _reply(agent, wv, "嗯。")
    assert "说悄悄话" in prompt_on, "ON 必须人话化"
    assert "whisper" not in prompt_on, "ON 不得再出现内部 token"
    assert "聊着聊着" in prompt_on, "turn=1 必须给出岔题提示"
    # 只多出「岔题」一段 ⇒ 去掉后与 OFF（把人话换回 token 后）对齐
    idx = prompt_on.index("\n聊着聊着")
    end = prompt_on.index("接着眼前的话说。", idx) + len("接着眼前的话说。")
    stripped = prompt_on[:idx] + prompt_on[end:]
    assert stripped.replace("说悄悄话", "whisper") == prompt_off


def test_on_path_content_gate_appends_tag_only_when_landed(tmp_path, monkeypatch):
    monkeypatch.delenv(TB.BREADTH_ENV, raising=False)
    _, agent = _build(tmp_path)
    wv = _wv(_dm_event(topic="gift", tag="gift"))
    monkeypatch.setenv(TB.BREADTH_ENV, "1")

    # 先看这一条实际会岔到哪
    _, agent.persona  # noqa: B018  (保持对象存活，避免意外回收)
    prompt, payload = _reply(agent, wv, "今儿个天真好，风也软。")
    tb = (payload.get("ctx") or {}).get("topic_breadth")
    assert tb is not None, "ON 时必须有审计键"
    shift = tb["shift"]
    assert payload["tag_hints"] == ["gift"], "正文没落到岔题话题 ⇒ 不得追加 tag"
    assert tb["landed"] is False

    # 构造命中该话题短语的一句（用该话题自己的典型说法，保证「真的落到了」）
    kw = TB.SAMPLE_PHRASES[shift]
    _, agent2 = _build(tmp_path / "b")
    prompt2, payload2 = _reply(agent2, wv, f"说起来，{kw}这事我也有数。")
    tb2 = (payload2.get("ctx") or {}).get("topic_breadth")
    assert tb2["shift"] == shift, "同参数必须同指派（确定性）"
    assert payload2["tag_hints"] == ["gift", shift]
    assert tb2["landed"] is True
