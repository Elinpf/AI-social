"""R31 · F-3「情绪呼应」**结构化硬约束**臂单测（不依赖 LLM、不依赖跑批）。

覆盖任务书要求的四件事：
  A. **开关语义**：默认 OFF；`1/true/on/yes` 开、其余关；`require_text_evidence`
     默认 True（只认对方那句话本身的证据），置 False 可复现 R14 旧口径（消融）。
  B. **情绪命中（证据门控）**：仅处境标签（`source=mood`）不产；对方那句有情绪词才产；
     门控与阈值是两道独立闸门（都过才产）。
  C. **结构标记生成**：`prompt_line` 产出的是结构化块（情绪标注 / 证据原话 / 三条硬要求 /
     回应形态），且**不含现成句式**、**要求模型不要抄标记**；`verify()` 生成后自检可复算。
  D. **L-7 不退化**：回应形态按 sha256 确定性轮转且分布均匀（无单形态主导）；
     L-7 结构臂（默认 ON）开启时本模块**让位**（不下发形态，避免两条结构约束打架）；
     OFF 路径与 HEAD 逐字节一致（提示词不加字、payload 不多键）。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import dialogue_threads as DT
from life import emotion_echo as EE
from life import l7_structural as L7S
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.ports import EventView, IntentResult
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"

#: 有语面情绪证据的对方台词（`emotion.emotion_sign` → −1）
NEG_TEXT = "今天真是累，心里挺委屈"
#: 正向证据（`emotion.emotion_sign` → +1，命中 NATURAL_POS/STRICT_POS）
POS_TEXT = "你这话说得我心里踏实，真感谢你"
#: 无语面证据（只在 ctx.mood 里有处境标签）
NEUTRAL_TEXT = "灶上还温着粥，你吃了吗"


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    EE.set_override(None)
    monkeypatch.delenv(EE.ECHO_ENV, raising=False)
    monkeypatch.delenv(L7S.STRUCT_ENV, raising=False)
    EE.reload()
    yield
    EE.set_override(None)
    EE.reload()


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


def _reply(agent, ev: EventView, text: str = "你先歇会儿，我陪你坐一会儿。"):
    rec = _RecLLM(text)
    agent.llm = rec
    captured: list[dict] = []
    agent.kernel.submit_intent = lambda aid, intent: (captured.append(intent.payload)
                                                      or IntentResult(ok=True, reason=None,
                                                                      event_seqs=()))
    ok = agent._send_reply(_wv(ev), ev, DT.DEFAULTS, "day0-morning")
    assert ok is True
    return rec.prompts[0], captured[0]


# ---------------------------------------------------------------- A 开关语义
def test_switch_default_off():
    assert EE.enabled() is False
    assert EE.load_params()["enabled"] is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", " on ", "yes"])
def test_switch_env_on_values(monkeypatch, val):
    monkeypatch.setenv(EE.ECHO_ENV, val)
    EE.reload()
    assert EE.enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "true1", "onn"])
def test_switch_env_off_values(monkeypatch, val):
    monkeypatch.setenv(EE.ECHO_ENV, val)
    EE.reload()
    assert EE.enabled() is False, f"{val!r} 不是开值，必须落到 OFF（防拼错当开）"


def test_require_text_evidence_default_true_in_config_file():
    raw = json.loads((CONFIG / "emotion_echo.json").read_text(encoding="utf-8"))
    assert raw["enabled"] is False, "默认必须 OFF（不改变既有行为）"
    assert raw["require_text_evidence"] is True, "R31 默认收紧触发口径"
    assert raw["form_rotation"] is True


# ---------------------------------------------------------------- B 情绪命中（证据门控）
def test_mood_only_is_gated_off_by_default():
    p = EE.load_params()
    p["enabled"] = True
    assert p["require_text_evidence"] is True
    assert EE.plan("低落", NEUTRAL_TEXT, p) is None, "仅处境标签（source=mood）不得触发"
    assert EE.plan("低落", "", p) is None


def test_text_evidence_still_produces():
    p = EE.load_params()
    p["enabled"] = True
    plan = EE.plan("低落", NEG_TEXT, p)
    assert plan is not None
    assert plan["sign"] == -1 and plan["source"] in ("text", "text+mood")
    assert plan["evidence"] == NEG_TEXT
    plan_pos = EE.plan("平和", POS_TEXT, p)
    assert plan_pos is not None and plan_pos["sign"] == 1 and plan_pos["kind"] == "cheer"


def test_gate_off_restores_r14_behaviour():
    """消融：require_text_evidence=False ⇒ 仅处境标签也触发（= R14 f3/1 口径）。"""
    p = EE.load_params()
    p["enabled"], p["require_text_evidence"] = True, False
    plan = EE.plan("低落", NEUTRAL_TEXT, p)
    assert plan is not None and plan["source"] == "mood"


def test_gate_and_threshold_are_two_independent_doors():
    p = EE.load_params()
    p["enabled"], p["min_intensity"] = True, 100     # 阈值高到必挡
    assert EE.plan("低落", NEG_TEXT, p) is None
    p["min_intensity"] = 30                          # 阈值放行后，门控仍在
    assert EE.plan("低落", NEG_TEXT, p) is not None
    assert EE.plan("低落", NEUTRAL_TEXT, p) is None


# ---------------------------------------------------------------- C 结构块 + 生成后自检
def test_prompt_block_is_structured_not_prose():
    p = EE.load_params()
    p["enabled"] = True
    plan = EE.plan("低落", NEG_TEXT, p)
    block = EE.prompt_line(plan, "阿禾")
    # 结构化的四个部件
    assert "【情绪呼应·本条硬约束】" in block
    assert "情绪标注：" in block and "阿禾" in block
    assert "证据（阿禾原话）：「今天真是累，心里挺委屈」" in block
    for must in ("1) 第一分句先接住", "2) 第一分句里要出现对阿禾的指称", "3) 可以先应一声"):
        assert must in block, f"缺硬要求：{must}"
    # 不许把标记抄进台词（防 L-13 内部 token 泄漏）
    assert "不要把「情绪标注」「证据」这些字" in block
    # **不给现成句式**：不出现 R14 那句散文式要求，也不出现"例如/比方说"
    assert "先接住这份情绪再说自己的事" not in block
    assert "例如" not in block and "比方说" not in block


def test_prompt_block_empty_without_plan():
    assert EE.prompt_line(None) == ""
    assert EE.audit(None) is None


def test_evidence_quote_is_truncated_and_clean():
    assert EE.evidence_quote("  你\n这话说得好  ") == "你这话说得好"
    long = "啊" * 40
    q = EE.evidence_quote(long, limit=10)
    assert len(q) == 11 and q.endswith("…")


def test_verify_adopted_case():
    p = EE.load_params()
    p["enabled"] = True
    plan = EE.plan("低落", NEG_TEXT, p)
    plan["name"] = "阿禾"
    v = EE.verify("你这话听着就累，先坐下歇会儿。", plan)
    assert v["first_clause"] == "你这话听着就累"
    assert v["has_ref"] is True and v["has_cue"] is True
    assert v["adopted"] is True


def test_verify_rejects_self_centred_and_ack_only_cases():
    p = EE.load_params()
    p["enabled"] = True
    plan = EE.plan("低落", NEG_TEXT, p)
    plan["name"] = "阿禾"
    self_centred = EE.verify("我今儿也累得够呛，地还没锄完。", plan)
    assert self_centred["has_ref"] is False and self_centred["adopted"] is False
    ack_only = EE.verify("嗯，那你先忙。", plan)
    assert ack_only["ack_then_switch"] is True and ack_only["adopted"] is False
    no_cue = EE.verify("你今天去地里了没。", plan)
    assert no_cue["has_ref"] is True and no_cue["has_cue"] is False and no_cue["adopted"] is False


def test_verify_does_not_modify_body_or_need_llm():
    body = "你这话听着就累，先坐下歇会儿。"
    p = EE.load_params()
    p["enabled"] = True
    plan = EE.plan("低落", NEG_TEXT, p)
    before = dict(plan)
    EE.verify(body, plan)
    assert plan == before, "verify 必须是纯函数：不得改计划"
    assert body == "你这话听着就累，先坐下歇会儿。"


# ---------------------------------------------------------------- D L-7 不退化 + 形态轮转
def test_form_rotation_is_deterministic_and_uniform():
    """同一入参恒等；64 个不同轮次的指派不得让任一形态占比 > 40%（防单句式收敛）。"""
    vals = [EE.assign_form("P003", f"TH-P00{i % 4}-P003-{i}", i % 7, i) for i in range(64)]
    assert vals == [EE.assign_form("P003", f"TH-P00{i % 4}-P003-{i}", i % 7, i)
                    for i in range(64)], "必须确定性（同入参同结果）"
    from collections import Counter
    c = Counter(vals)
    assert len(c) == len(EE.ECHO_FORMS), f"5 种形态都要用到，实际 {c}"
    assert max(c.values()) / 64 <= 0.40, f"单形态占比过高，可能造成句式收敛：{c}"


def test_form_assigned_only_when_l7_disabled(tmp_path, monkeypatch):
    """L-7 结构臂（默认 ON）已指派开口方式 ⇒ 本模块让位：不下发形态、audit.form=None。"""
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    agent_kernel, agent = _build(tmp_path)
    prompt_on, payload_on = _reply(agent, _dm_event(NEG_TEXT, "低落"))
    assert "回应形态" not in prompt_on
    assert payload_on["ctx"]["echo"]["form"] is None

    # 关掉 L-7 结构臂 ⇒ 形态由本模块按 sha256 指派，且出现在提示词里
    monkeypatch.setenv(L7S.STRUCT_ENV, "0")
    kernel2, agent2 = _build(tmp_path / "nol7")
    prompt2, payload2 = _reply(agent2, _dm_event(NEG_TEXT, "低落"))
    assert "回应形态" in prompt2
    form = payload2["ctx"]["echo"]["form"]
    assert form in [f[0] for f in EE.ECHO_FORMS]
    # 形态随 (agent, thread, turn, round) 变化，不是写死的一句
    expected = EE.ECHO_FORMS[EE.assign_form("P003", "TH-P007-P003-4", 1, 4)][0]
    assert form == expected


# ---------------------------------------------------------------- E 接线 + OFF 逐字节一致
def test_off_path_byte_identical_and_no_structure(tmp_path):
    kernel, agent = _build(tmp_path)
    ev = _dm_event(NEG_TEXT, "低落")
    prompt_off, payload_off = _reply(agent, ev)

    assert "echo" not in payload_off["ctx"]
    assert "【情绪呼应" not in prompt_off
    history = agent._thread_history(_wv(ev), ev.payload["thread_id"], DT.DEFAULTS)
    baseline = agent._reply_prompt("P007", "闲聊", history, DT.DEFAULTS, wv=_wv(ev))
    assert prompt_off == baseline, "OFF（默认）必须与 HEAD 逐字节一致"


def test_on_path_block_goes_after_history_and_records_verify(tmp_path, monkeypatch):
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    kernel, agent = _build(tmp_path)
    ev = _dm_event(NEG_TEXT, "低落")
    prompt_on, payload_on = _reply(agent, ev)

    a = payload_on["ctx"]["echo"]
    assert a["v"] == EE.VERSION == "f3/2"
    assert a["prompted"] is True and a["source"] in ("text", "text+mood")
    assert "verify" in a, "R31 必须写入生成后确定性自检"
    assert a["verify"]["v"] == "f3-verify/1"
    assert a["verify"]["adopted"] is True            # 固定替身台词「你先歇会儿…」含指称+线索
    # 结构块位置：在「刚才的对话」之后（尾部约束区），而不是对话正文之前
    assert prompt_on.index("刚才的对话") < prompt_on.index("【情绪呼应·本条硬约束】")
    # ON = OFF + 恰好一段插入
    off_prompt = prompt_on.replace(EE.prompt_line(agent._echo_plan, "阿禾"), "")
    history = agent._thread_history(_wv(ev), ev.payload["thread_id"], DT.DEFAULTS)
    baseline = agent._reply_prompt("P007", "闲聊", history, DT.DEFAULTS, wv=_wv(ev))
    assert off_prompt == baseline


def test_on_path_neutral_text_produces_nothing(tmp_path, monkeypatch):
    """ON 但对方只是日常话（无情绪证据）⇒ 不产键、不加字（宁缺毋滥，R31 的核心动机）。"""
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    kernel, agent = _build(tmp_path)
    prompt_on, payload_on = _reply(agent, _dm_event(NEUTRAL_TEXT, "低落"))
    assert "echo" not in payload_on["ctx"]
    assert "【情绪呼应" not in prompt_on
