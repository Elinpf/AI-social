"""R51 臂 · 「需求的人话化 + 紧迫门控」**单变量**单测。

被测：`code/life/agent.py::_mood_line()`（+ `_ctx_snapshot()` 的 additive 审计键）。

五条硬断言（对应 `reports/R51-prereg-need-speech-20261101.md` §1/§3.4-U5）：

  A. **开关默认关**：不设 env ⇒ False；`1/true/yes/on` ⇒ True；其它值 ⇒ False。
  B. **OFF 逐字节等价**（本条是 U5 的证据来源，提示词不落盘，只能在这里证）：
     - 与**改前逻辑**逐字重构的基线 `_mood_line` 对比，两条装配点
       `_dialogue_prompt` / `_reply_prompt` 全部逐字节相等；
     - 与**改动前本机实测的 prompt sha256 冻结值**（`v2/evidence/r51-need-speech/prompt_hashes_pre_change.json`，
       由 `tools/r51/prompt_hash_probe.py` 在 `61850ba` 上跑出）逐一相等 —— 改一个空格这条就红。
  C. **ON 是单变量**：把 ON 提示词里的那一段（情绪+需求）换回 OFF 的同一段即得 OFF 提示词，
     既有段落（persona/场景/对象/收尾指令）一个字节不动。
  D. **门控正确**：`val >= 40` ⇒ 需求整段不出现（提示词与"没有需求"完全一致）；`val < 40` ⇒ 出现，
     且**机器口径 `dim=val` 不出现在提示词里**。
  E. **审计键**：OFF ⇒ `ctx` 无 `need_speech` 键、`ctx` sha256 与改前冻结值相等；
     ON ⇒ 键出现且 `injected` 与 D 的判定一致。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from life import dialogue_threads as DT
from life.agent import (NEED_SPEECH_ENV, NEED_SPEECH_FALLBACK, NEED_SPEECH_PHRASES,
                        NEED_SPEECH_URGENT, LifeLayerAgent, need_speech_enabled)
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas

CODE_DIR = Path(__file__).resolve().parents[1]
CONFIG = CODE_DIR / "config"

SELF_ID = "P001"
PARTNER_ID = "P002"

#: 旁白通道钉死（与 `prompt_hash_probe.py` 同口径）：只量 `_mood_line()` 这一处
NARRATION_ENV = "LIFE_PROMPT_NARRATION"

#: 三组固定 needs 夹具（与 `tools/r51/prompt_hash_probe.py` **逐字相同**）
NEEDS_FIXTURES = {
    "urgent": {"satiety": 12, "energy": 55, "social": 60, "esteem": 62, "mastery": 58, "leisure": 51},
    "noise": {"satiety": 52, "energy": 55, "social": 60, "esteem": 62, "mastery": 58, "leisure": 51},
    "empty": {},
}

#: 改动前（sha `61850ba` 之前的树，`code_sha=61850ba`）实测的提示词 / ctx 指纹，**冻结不得改**
#: 来源：`v2/evidence/r51-need-speech/prompt_hashes_pre_change.json`
FROZEN_FINGERPRINTS = {
    "urgent": {"dialogue": "57223672301fca9e25ca53d7b4fb34fa977b5a1505287a483d3575623cb21e62",
               "reply": "4faaa73c0c9d209e348bb9e0fecf3b6bf8ebfbd9905ca2fc6dcb54042ccb4abe",
               "ctx": "d7bfa4052946f35c08dfd17f9ecd931d215014363b02563b6ade483a70d96adf"},
    "noise": {"dialogue": "60b1aa5b317df4840d298ddb91f4a482bfa8b02a322dc24226b10336e8c0a03a",
              "reply": "9727cca7a278975d9252e880f984ee7f6a89d23b7d9f43060725931e06b313c5",
              "ctx": "28cf542d2d2efeb9884df20bdffba4f954289b87be6d804542b46ad2c34f10bf"},
    "empty": {"dialogue": "4c191eaea179a10ad654efdd31471a3cd48faa173b49fd4052cf0e607bbefed8",
              "reply": "413f5c38f4282fea2ed0c82998f4656f24af5eba074cb787cfdc20e4a39fb454",
              "ctx": "762258b2d7d18ae5025f3e0f6fb1ea5dd5c36e8833b999ecc612753ae774befd"},
}


@pytest.fixture(autouse=True)
def _pin_env(monkeypatch):
    monkeypatch.setenv(NARRATION_ENV, "0")
    monkeypatch.delenv(NEED_SPEECH_ENV, raising=False)


class _StubKernel:
    def submit_intent(self, *a, **kw):  # pragma: no cover
        pass


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _agent(tmp_path: Path) -> LifeLayerAgent:
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    persona = load_personas(CONFIG / "personas.json")[SELF_ID]
    return LifeLayerAgent(SELF_ID, persona, _StubKernel(),
                          side_store=SideStore(tmp_path / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peers=[SELF_ID, PARTNER_ID],
                          peer_names={SELF_ID: "沈砚", PARTNER_ID: "赵四"})


#: 提示词里"情绪 + 需求"那一段（以「情绪：」起、到句号止）——用于单变量替换断言
MOOD_SEG_RE = re.compile(r"情绪：[^。]*")


def _seg(prompt: str) -> str:
    m = MOOD_SEG_RE.search(prompt)
    return m.group(0) if m else ""


def _render(tmp_path: Path, needs: dict) -> dict:
    agent = _agent(tmp_path)
    agent.needs = dict(needs)
    history = [("赵四", "早上好。"), ("沈砚", "早啊。")]
    d = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    r = agent._reply_prompt(PARTNER_ID, "tpl-1", history)
    ctx = agent._ctx_snapshot(PARTNER_ID, "tpl-1")
    return {"agent": agent, "dialogue": d, "reply": r,
            "ctx": ctx, "ctx_sha": _sha(json.dumps(ctx, ensure_ascii=False, sort_keys=True)),
            "mood_line": agent._mood_line(),
            "seg_dialogue": _seg(d), "seg_reply": _seg(r)}


def _baseline_mood_line(agent: LifeLayerAgent) -> str:
    """**改前逻辑的逐字重构**（`git show 82bdb3f:code/life/agent.py` 的 `_mood_line`）。"""
    mood = DT.mood_label(agent.needs)
    need = DT.scarcest_need(agent.needs)
    if need:
        dim, val = next(iter(need.items()))
        return f"情绪：{mood}；最紧的需求：{dim}={val}"
    return f"情绪：{mood}"


# --------------------------------------------------------------------------- A
def test_switch_default_off(monkeypatch):
    """A. 开关默认关；真值集与既有臂一致。"""
    assert need_speech_enabled() is False
    for v in ("1", "true", "YES", " on "):
        monkeypatch.setenv(NEED_SPEECH_ENV, v)
        assert need_speech_enabled() is True
    monkeypatch.setenv(NEED_SPEECH_ENV, "0")
    assert need_speech_enabled() is False


# --------------------------------------------------------------------------- B
@pytest.mark.parametrize("name", sorted(NEEDS_FIXTURES))
def test_off_is_byte_identical_to_baseline_logic(tmp_path, name):
    """B-1. OFF 与"改前逻辑逐字重构"的两条装配点逐字节相等。"""
    needs = NEEDS_FIXTURES[name]
    off = _render(tmp_path, needs)
    agent = off["agent"]
    # 把 `_mood_line` 换成改前逻辑（实例级替换，不动源码），其余装配表达式原样复用
    agent._mood_line = lambda: _baseline_mood_line(agent)
    history = [("赵四", "早上好。"), ("沈砚", "早啊。")]
    base_d = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    base_r = agent._reply_prompt(PARTNER_ID, "tpl-1", history)
    assert off["dialogue"] == base_d, f"OFF 态 _dialogue_prompt 与改前不再逐字节一致（{name}）"
    assert off["reply"] == base_r, f"OFF 态 _reply_prompt 与改前不再逐字节一致（{name}）"


@pytest.mark.parametrize("name", sorted(NEEDS_FIXTURES))
def test_off_matches_frozen_pre_change_fingerprints(tmp_path, name):
    """B-2. OFF 的提示词/ctx sha256 == 改动前本机实测冻结值（改一个空格即红）。"""
    off = _render(tmp_path, NEEDS_FIXTURES[name])
    frozen = FROZEN_FINGERPRINTS[name]
    assert _sha(off["dialogue"]) == frozen["dialogue"]
    assert _sha(off["reply"]) == frozen["reply"]
    assert off["ctx_sha"] == frozen["ctx"]
    assert "need_speech" not in off["ctx"]


# --------------------------------------------------------------------------- C / D
@pytest.mark.parametrize("name", sorted(NEEDS_FIXTURES))
def test_on_diff_is_only_the_need_segment(tmp_path, monkeypatch, name):
    """C/D. ON 相对 OFF 的差异**只**是"情绪 + 需求"这一段；门控方向正确。"""
    needs = NEEDS_FIXTURES[name]
    off = _render(tmp_path, needs)
    monkeypatch.setenv(NEED_SPEECH_ENV, "1")
    on = _render(tmp_path, needs)

    # 单变量核心：把 ON 里那一段换回 OFF 的那一段 ⇒ 逐字节回到 OFF 的提示词
    assert on["dialogue"].replace(on["seg_dialogue"], off["seg_dialogue"], 1) == off["dialogue"]
    assert on["reply"].replace(on["seg_reply"], off["seg_reply"], 1) == off["reply"]

    seg_on = on["seg_dialogue"]
    val = next(iter(DT.scarcest_need(needs).values())) if needs else None
    if not needs:
        assert seg_on == off["seg_dialogue"] == f"情绪：{DT.mood_label(needs)}"
    elif val >= NEED_SPEECH_URGENT:
        # 不紧迫 ⇒ 整段不出现（只剩情绪），且机器口径不出现
        assert seg_on == f"情绪：{DT.mood_label(needs)}"
        assert "最紧的需求" not in seg_on
    else:
        # 真紧迫 ⇒ 出现人话，机器口径 dim=val 不进提示词
        dim = next(iter(DT.scarcest_need(needs)))
        assert "最紧的需求" not in seg_on
        assert f"{dim}={val}" not in seg_on
        assert seg_on.startswith("情绪：")
        assert any(p in seg_on for p in NEED_SPEECH_PHRASES[dim])


def test_on_noise_prompt_equals_no_need_prompt(tmp_path, monkeypatch):
    """D. 结构性证据：ON 且需求不紧迫时，提示词与"根本没有需求"逐字节相同。"""
    monkeypatch.setenv(NEED_SPEECH_ENV, "1")
    noise = _render(tmp_path, NEEDS_FIXTURES["noise"])
    empty = _render(tmp_path, NEEDS_FIXTURES["empty"])
    assert noise["dialogue"] == empty["dialogue"]
    assert noise["reply"] == empty["reply"]


def test_on_unknown_dim_uses_fallback_without_machine_fields(tmp_path, monkeypatch):
    """D. 词表外维度：走人话兜底，不吐 `dim=val`。"""
    monkeypatch.setenv(NEED_SPEECH_ENV, "1")
    needs = {d: 90 for d in ("satiety", "social", "esteem", "mastery", "leisure")}
    needs["energy"] = 5
    agent = _agent(tmp_path)
    agent.needs = needs
    # 用一个人造维度替换（模拟 vocabulary 缺项）
    agent.needs = {"unknown_dim": 5}
    line = agent._mood_line()
    assert NEED_SPEECH_FALLBACK in line
    assert "unknown_dim=5" not in line and "unknown_dim" not in line


# --------------------------------------------------------------------------- E
def test_audit_key_matches_gate(tmp_path, monkeypatch):
    """E. OFF ⇒ 无 `need_speech` 键；ON ⇒ 键在且 `injected` 与门控一致。"""
    for name in ("urgent", "noise", "empty"):
        needs = NEEDS_FIXTURES[name]
        off = _render(tmp_path, needs)
        assert "need_speech" not in off["ctx"], f"OFF 臂不得写审计键（{name}）"

    monkeypatch.setenv(NEED_SPEECH_ENV, "1")
    for name in ("urgent", "noise", "empty"):
        needs = NEEDS_FIXTURES[name]
        on = _render(tmp_path, needs)
        if not needs:
            assert "need_speech" not in on["ctx"], "无需求时不应写审计键"
            continue
        ns = on["ctx"]["need_speech"]
        dim, val = next(iter(DT.scarcest_need(needs).items()))
        assert ns == {"dim": dim, "value": int(val), "injected": int(val) < NEED_SPEECH_URGENT}


def test_phrases_have_no_machine_fields_and_rotate(tmp_path, monkeypatch):
    """短语表自身：无英文维名/裸数值；轮换确定性（同输入两次同序列）。"""
    dims = ("satiety", "energy", "social", "esteem", "mastery", "leisure")
    for dim, phrases in NEED_SPEECH_PHRASES.items():
        assert dim in dims
        assert len(phrases) == 3
        for p in phrases:
            assert p.strip() == p and p
            assert "=" not in p and not any(ch.isdigit() for ch in p)
            assert dim not in p
    monkeypatch.setenv(NEED_SPEECH_ENV, "1")

    def seq() -> list:
        agent = _agent(tmp_path)
        agent.needs = dict(NEEDS_FIXTURES["urgent"])
        return [agent._mood_line() for _ in range(6)]

    a, b = seq(), seq()
    assert a == b, "轮换必须确定性（同 run 可复现）"
    assert len(set(a)) == 3, f"3 条短语应轮换出现，实际：{a}"
