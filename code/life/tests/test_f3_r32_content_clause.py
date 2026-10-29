"""R32 · F-3「第一分句」判定口径（`content_clause`）单测（不联网、不跑批）。

修的是 CYCLE-34 采纳漏斗暴露的**最大一级丢失**（`tools/metrics/f3_funnel.py`，
证据 `v2/evidence/cycle36_f3_funnel/funnel_on_pre_r32.json`）：

    ON 臂 `echo_msgs=107` → `verify.adopted=7`（6.54%）。
    107 条里 **62 条的第一段就是一个「嗯」/「哎」**、**30 条是一个单独的称呼**；
    旧口径「第一个逗号之前 = 第一分句」⇒ 这 92 条的第一分句里不可能出现线索词。
    其中 **44 条**把线索词放在紧跟其后的第一个实质分句里（"嗯，你压腿压得高兴就好"）。

覆盖四件事：
  A. **纯函数**：`segments()` / `is_vocative_segment()` / `content_first_clause()` 确定性、
     宁可不跳也不误跳（不含线索词/指称、≤5 字、与对方显示名互为子串才算称呼）。
  B. **口径切换可回归**：`content_clause=False` ⇒ `verify()` 与 R31 逐字段一致
     （`first_clause == first_clause_raw`），`adopted` 回到旧值。
  C. **内容分句口径下的判定**：应声/称呼前缀不再吞掉线索词；`need_rewrite()` 随之更准
     （同一句不再被误判为"必须重写"，省掉一次无谓 LLM 调用）。
  D. **OFF 臂逐字节不变**：未设 `HITT_DIALOGUE_EMOTION_ECHO` ⇒ 提示词等于基线、payload 无 `echo`。
"""
from __future__ import annotations

import pytest

from life import dialogue_threads as DT
from life import emotion_echo as EE
from life.tests.test_f3_echo_struct_r31 import (NEG_TEXT, _build, _dm_event, _reply, _wv)

#: CYCLE-34 ON 臂里的真实样本（`msg_uid=42:2141`，raw 口径 first_clause 只有「嗯」）
ACK_OPEN = "嗯，你压腿压得高兴就好。我这儿正把上月那沓对账单摊在柜台上。"
#: 同上一条：第一段是**单独的称呼**（`msg_uid=42:1198`，raw 口径 first_clause = 「巧儿」）
NAME_OPEN = "巧儿，你拿废木条练榫头，我听着就踏实。我来搭把手。"
#: 第一段就是实质内容（两种口径应当一致）
PLAIN = "你这话听着就累，先坐下歇会儿。"


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    EE.set_override(None)
    monkeypatch.delenv(EE.ECHO_ENV, raising=False)
    EE.reload()
    yield
    EE.set_override(None)
    EE.reload()


def _plan(name: str = "月牙") -> dict:
    p = EE.load_params()
    p["enabled"] = True
    plan = EE.plan("低落", NEG_TEXT, p)
    assert plan is not None
    plan["name"] = name
    return plan


def _mode(content: bool):
    EE.set_override({**EE.load_params(), "enabled": True, "content_clause": content})


# ---------------------------------------------------------------- A 纯函数
def test_segments_is_deterministic_and_drops_empty():
    assert EE.segments("嗯，你先歇会儿。我这就去。") == ["嗯", "你先歇会儿", "我这就去"]
    assert EE.segments("") == [] and EE.segments("   ") == []
    assert EE.segments("嗯，你先歇会儿。") == EE.segments("  嗯，你先歇会儿。  ")


def test_content_first_clause_skips_ack_and_vocative_prefix():
    assert EE.content_first_clause(ACK_OPEN) == "你压腿压得高兴就好"
    assert EE.content_first_clause(NAME_OPEN, "巧儿") == "你拿废木条练榫头"
    # 连跳两段：应声 + 称呼
    assert EE.content_first_clause("哎，巧儿，你先别急。", "巧儿") == "你先别急"
    # 第一段就是实质内容 ⇒ 不动
    assert EE.content_first_clause(PLAIN) == "你这话听着就累"
    # 空正文 ⇒ 空串；整段只有一个应声 ⇒ 原样返回（函数总返回非空串，避免调用方踩空）
    assert EE.content_first_clause("") == ""
    assert EE.content_first_clause("嗯") == "嗯"


def test_vocative_detector_does_not_swallow_content():
    """宁可不跳也不误跳：含线索词 / 含指称 / 过长 / 名字对不上 ⇒ 都不算称呼。"""
    assert EE.is_vocative_segment("巧儿", "巧儿") is True
    assert EE.is_vocative_segment("陈医", "陈医") is True
    assert EE.is_vocative_segment("金先生", "金先生") is True
    assert EE.is_vocative_segment("你先歇会儿", "巧儿") is False, "含指称 ⇒ 不是称呼"
    assert EE.is_vocative_segment("别难过", "巧儿") is False, "含线索词 ⇒ 不是称呼"
    assert EE.is_vocative_segment("巧儿你听我说", "巧儿") is False, "过长 ⇒ 不是称呼"
    assert EE.is_vocative_segment("阿禾", "巧儿") is False, "与对方显示名无关 ⇒ 不是称呼"
    assert EE.is_vocative_segment("巧儿", None) is False, "无显示名 ⇒ 只跳过应声"


# ---------------------------------------------------------------- B 口径可回归
def test_raw_mode_is_field_for_field_identical_to_r31():
    plan = _plan()
    _mode(False)
    try:
        for body in (ACK_OPEN, NAME_OPEN, PLAIN, ""):
            v = EE.verify(body, plan)
            assert v["clause_mode"] == "raw"
            assert v["first_clause"] == v["first_clause_raw"], "raw 口径下两键必须同值"
            # 旧口径的核心判据：第一个逗号之前
            assert v["first_clause"] == EE.first_clause(body)
    finally:
        EE.set_override(None)


def test_raw_mode_reproduces_cycle34_reading():
    """复算 CYCLE-34 的两条真实样本：raw 口径下 has_cue=False（这正是 7/107 的来源）。"""
    plan = _plan("月牙")
    _mode(False)
    try:
        assert EE.verify(ACK_OPEN, plan)["has_cue"] is False
        assert EE.verify(ACK_OPEN, plan)["adopted"] is False
        assert EE.verify(NAME_OPEN, _plan("巧儿"))["has_cue"] is False
    finally:
        EE.set_override(None)


# ---------------------------------------------------------------- C 内容分句口径
def test_content_mode_recovers_echo_hidden_behind_ack():
    plan = _plan("月牙")
    _mode(True)
    try:
        v = EE.verify(ACK_OPEN, plan)
        assert v["clause_mode"] == "content"
        assert v["first_clause"] == "你压腿压得高兴就好"
        assert v["first_clause_raw"] == "嗯"
        assert v["has_ref"] is True and v["has_cue"] is True
        assert v["ack_then_switch"] is False and v["adopted"] is True
    finally:
        EE.set_override(None)


def test_content_mode_still_rejects_real_switch():
    """跳过应声 ≠ 放宽：应声之后的实质分句若真的没接住，仍然判不合格。"""
    plan = _plan("阿禾")
    _mode(True)
    try:
        v = EE.verify("嗯，那我先去地里把垄翻完。", plan)
        assert v["first_clause"] == "那我先去地里把垄翻完"
        assert v["has_cue"] is False and v["adopted"] is False
        assert EE.need_rewrite(v) is True, "真的没接住 ⇒ 仍要重写"
    finally:
        EE.set_override(None)


def test_need_rewrite_stops_firing_on_structural_false_positive():
    """同一句：raw 口径误判「必须重写」（会白花一次 LLM），content 口径不再误判。"""
    plan = _plan("月牙")
    _mode(False)
    try:
        assert EE.need_rewrite(EE.verify(ACK_OPEN, plan)) is True
    finally:
        EE.set_override(None)
    _mode(True)
    try:
        assert EE.need_rewrite(EE.verify(ACK_OPEN, plan)) is False
    finally:
        EE.set_override(None)


def test_verify_declares_its_schema_and_mode():
    plan = _plan()
    v = EE.verify(PLAIN, plan)
    assert v["v"] == "f3-verify/2"
    assert v["clause_mode"] in ("content", "raw")
    assert "first_clause_raw" in v


# ---------------------------------------------------------------- 提示词口径同步
def test_prompt_line_states_the_definition_in_content_mode_only():
    plan = _plan("阿禾")
    _mode(True)
    try:
        block = EE.prompt_line(plan, "阿禾")
    finally:
        EE.set_override(None)
    assert "第一个有实质内容的分句" in block
    assert "都不算第一分句" in block

    _mode(False)
    try:
        block_raw = EE.prompt_line(plan, "阿禾")
    finally:
        EE.set_override(None)
    assert "第一个有实质内容的分句" not in block_raw, "消融口径下提示词不得多字"
    assert block_raw != block


def test_prompt_line_is_empty_without_plan():
    assert EE.prompt_line(None) == ""
    assert EE.prompt_line(None, "阿禾") == ""


# ---------------------------------------------------------------- D OFF 臂逐字节不变
def test_off_arm_is_byte_identical(tmp_path):
    _kernel, agent = _build(tmp_path)
    ev = _dm_event(NEG_TEXT, "低落")
    prompt_off, payload_off = _reply(agent, ev)

    assert EE.enabled() is False
    assert "echo" not in payload_off["ctx"]
    assert "【情绪呼应" not in prompt_off
    history = agent._thread_history(_wv(ev), ev.payload["thread_id"], DT.DEFAULTS)
    baseline = agent._reply_prompt("P007", "闲聊", history, DT.DEFAULTS, wv=_wv(ev))
    assert prompt_off == baseline, "OFF（默认）必须与接入前逐字节一致"

# ---------------------------------------------------------------- env 消融口（两臂同树）
@pytest.mark.parametrize("val,expect", [
    ("1", True), ("true", True), ("TRUE", True), ("on", True), ("Yes", True),
    ("0", False), ("false", False), ("off", False), ("no", False),
    ("", False), ("enable", False),
])
def test_content_clause_env_escape_hatch(monkeypatch, val, expect):
    """`HITT_ECHO_CONTENT_CLAUSE`：{1,true,on,yes}（大小写不敏感）→ 开；其它任何取值 → 关。"""
    monkeypatch.setenv(EE.CONTENT_CLAUSE_ENV, val)
    EE.reload()
    assert EE.load_params()["content_clause"] is expect


def test_content_clause_env_unset_keeps_default_true(monkeypatch):
    """未设 env ⇒ **不动默认值**（True），既有臂语义不变。"""
    monkeypatch.delenv(EE.CONTENT_CLAUSE_ENV, raising=False)
    EE.reload()
    assert EE.DEFAULTS["content_clause"] is True
    assert EE.load_params()["content_clause"] is True


def test_content_clause_env_is_independent_of_echo_env(monkeypatch):
    """两个 env 互不牵连：只设口径口不会把 echo 打开，只设 echo 口也不会关掉口径。"""
    monkeypatch.delenv(EE.ECHO_ENV, raising=False)
    monkeypatch.setenv(EE.CONTENT_CLAUSE_ENV, "1")
    EE.reload()
    p = EE.load_params()
    assert p["content_clause"] is True and p["enabled"] is False

    monkeypatch.delenv(EE.CONTENT_CLAUSE_ENV, raising=False)
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    p = EE.load_params()
    assert p["enabled"] is True and p["content_clause"] is True
