"""N-05 · F-3「情绪呼应」**生成侧第一分句线索**闸门单测（不联网、不跑批）。

修的是 CYCLE-34 ON 臂读数暴露的生成侧瓶颈（`echo_msgs=107` / `verify_has_cue=7` /
`verify_ack_then_switch=66`）：不是呼应强度不够，而是**第一分句没接住**，应一声就转话题。
本轮**不加 echo 强度**（触发口径/阈值/强度一条没动），只加一道**最多重写一次**的生成后闸门。

覆盖四件事：
  A. **判据是纯函数**：`need_rewrite` / `rewrite_ok` / `rewrite_line` 确定性、可复算、
     不给现成句式、不要求模型输出标记。
  B. **闸门真的落在链路上**：ON 臂第一遍不合格 ⇒ 多一次 LLM 调用、正文被替换、
     `ctx.echo.verify.rewrite.accepted is True`、替换后 `has_cue is True`。
  C. **不劣于修正前**：重写仍不合格 ⇒ **保留原文**（`accepted False`）；第一遍就合格
     ⇒ **不多一次调用**。
  D. **OFF 臂逐字节不变**：未设 `HITT_DIALOGUE_EMOTION_ECHO` 时整段闸门不执行
     （LLM 只调用一次、提示词等于基线、payload 无 `echo` 键）——两臂可在同一 sha 配对。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from life import dialogue_threads as DT
from life import emotion_echo as EE
from life.ports import IntentResult
from life.tests.test_f3_echo_struct_r31 import (NEG_TEXT, NEUTRAL_TEXT, _build,
                                                _dm_event, _wv)

#: 第一遍：应一声就转话题（`ack_then_switch`，CYCLE-34 里 66 条的主体形态）
ACK_THEN_SWITCH = "嗯，那我先去地里把垄翻完。"
#: 第一遍：只复述事实，没有回应线索（`has_cue=False`）
NO_CUE = "你今天也去集市了吗。"
#: 合格第一分句（有指称 + 有回应线索）
GOOD = "你先别急，累就坐下歇一会儿，我陪你。"


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    EE.set_override(None)
    monkeypatch.delenv(EE.ECHO_ENV, raising=False)
    EE.reload()
    yield
    EE.set_override(None)
    EE.reload()



@pytest.fixture()
def raw_clause():
    """R32 消融口：把这组用例钉在 **R31/N-05 原来的 raw 第一分句口径**上（逐字节回归）。

    R32 把「第一分句」改成「第一个实质分句」（跳过单独成段的应声/称呼，见
    `emotion_echo.content_first_clause`）。本文件这些用例瞄准的是 N-05 闸门本身
    （"应一声就转话题"要触发重写），其样本台词是按 raw 口径构造的 ⇒ 显式钉回 raw，
    保证 N-05 的既有行为被原样回归；content 口径的覆盖在
    `test_f3_r32_content_clause.py`。
    """
    EE.set_override({**EE.load_params(), "enabled": True, "content_clause": False})
    yield
    EE.set_override(None)


class _SeqLLM:
    """确定性 LLM 替身：按调用次序返回给定台词，并记录每条提示词（不联网、不随机）。"""

    name = "seq-llm"

    def __init__(self, *texts: str):
        self.texts = list(texts) or [GOOD]
        self.prompts: list[str] = []
        self.metas: list[dict] = []

    def call(self, purpose, prompt, *, model=None, meta=None):
        self.prompts.append(prompt)
        self.metas.append(dict(meta or {}))
        i = min(len(self.prompts) - 1, len(self.texts) - 1)
        return SimpleNamespace(text=self.texts[i])


def _run(agent, ev, llm: _SeqLLM) -> dict:
    agent.llm = llm
    captured: list[dict] = []
    agent.kernel.submit_intent = lambda aid, intent: (
        captured.append(intent.payload)
        or IntentResult(ok=True, reason=None, event_seqs=()))
    ok = agent._send_reply(_wv(ev), ev, DT.DEFAULTS, "day0-morning")
    assert ok is True
    return captured[0]


def _plan() -> dict:
    p = EE.load_params()
    p["enabled"] = True
    plan = EE.plan("低落", NEG_TEXT, p)
    assert plan is not None
    plan["name"] = "阿禾"
    return plan


# ---------------------------------------------------------------- A 判据是纯函数
def test_need_rewrite_and_rewrite_ok_are_pure_predicates(raw_clause):
    plan = _plan()
    bad_ack = EE.verify(ACK_THEN_SWITCH, plan)
    bad_cue = EE.verify(NO_CUE, plan)
    good = EE.verify(GOOD, plan)

    assert bad_ack["ack_then_switch"] is True and bad_ack["has_cue"] is False
    assert EE.need_rewrite(bad_ack) is True, "应一声就转话题 ⇒ 必须触发重写"
    assert EE.need_rewrite(bad_cue) is True, "第一分句无线索 ⇒ 必须触发重写"
    assert EE.need_rewrite(good) is False, "第一遍就合格 ⇒ 不许重写（省一次调用）"
    assert EE.need_rewrite(None) is True

    assert EE.rewrite_ok(good) is True
    assert EE.rewrite_ok(bad_ack) is False and EE.rewrite_ok(bad_cue) is False
    assert EE.rewrite_ok(None) is False


def test_rewrite_line_is_structural_not_a_ready_made_sentence(raw_clause):
    plan = _plan()
    line = EE.rewrite_line(plan, EE.verify(ACK_THEN_SWITCH, plan))
    assert "【情绪呼应·第一分句重写】" in line
    assert "只应了一声就转到自己的事上" in line, "失败原因要说清（确定性翻译）"
    assert "上一条的第一分句：「嗯」" in line
    for must in ("1) 第一分句就接住阿禾这份情绪", "2) 第一分句里要有对阿禾的指称",
                 "3) 应声词最多三个字"):
        assert must in line, f"缺结构要求：{must}"
    # 不给现成句式、不要求输出标记
    assert "例如" not in line and "比方说" not in line
    assert "只输出台词本身" in line
    assert EE.rewrite_line(None, None) == ""


def test_prompt_line_gains_cue_word_requirement():
    """提示词侧的配套小改：硬要求 1 明确要第一分句出现回应情绪的字眼。"""
    plan = _plan()
    block = EE.prompt_line(plan, "阿禾")
    assert "第一分句里要出现一个表露情绪回应的字眼" in block
    assert "例如" not in block and "比方说" not in block, "仍不得给现成句式"


# ---------------------------------------------------------------- B 闸门落在链路上
def test_on_ack_then_switch_is_rewritten_once(tmp_path, monkeypatch, raw_clause):
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    _kernel, agent = _build(tmp_path)
    llm = _SeqLLM(ACK_THEN_SWITCH, GOOD)
    payload = _run(agent, _dm_event(NEG_TEXT, "低落"), llm)

    assert len(llm.prompts) == 2, "第一遍不合格 ⇒ 恰好重写一次（不多不少）"
    assert "【情绪呼应·第一分句重写】" in llm.prompts[1]
    assert llm.metas[1].get("echo_rewrite") == 1, "重写调用要可记账（obs llm-cost 可分辨）"
    assert payload["body"] == GOOD, "重写结果合格 ⇒ 替换正文"

    ver = payload["ctx"]["echo"]["verify"]
    assert ver["has_cue"] is True and ver["ack_then_switch"] is False
    rw = ver["rewrite"]
    assert rw["attempted"] is True and rw["accepted"] is True
    assert rw["before"] == {"has_cue": False, "ack_then_switch": True}
    assert rw["after"] == {"has_cue": True, "ack_then_switch": False}


def test_on_good_first_pass_makes_no_extra_call(tmp_path, monkeypatch):
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    _kernel, agent = _build(tmp_path)
    llm = _SeqLLM(GOOD)
    payload = _run(agent, _dm_event(NEG_TEXT, "低落"), llm)

    assert len(llm.prompts) == 1, "已经合格就不许多花一次调用"
    assert payload["body"] == GOOD
    ver = payload["ctx"]["echo"]["verify"]
    assert ver["has_cue"] is True and "rewrite" not in ver


# ---------------------------------------------------------------- C 不劣于修正前
def test_on_rewrite_still_bad_keeps_original_body(tmp_path, monkeypatch, raw_clause):
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    _kernel, agent = _build(tmp_path)
    llm = _SeqLLM(NO_CUE, ACK_THEN_SWITCH)      # 两次都不合格
    payload = _run(agent, _dm_event(NEG_TEXT, "低落"), llm)

    assert len(llm.prompts) == 2, "只允许重写一次（不许循环追问）"
    assert payload["body"] == NO_CUE, "重写更差 ⇒ 必须回退原文，结果不劣于修正前"
    rw = payload["ctx"]["echo"]["verify"]["rewrite"]
    assert rw["attempted"] is True and rw["accepted"] is False
    assert rw["after"] == {"has_cue": False, "ack_then_switch": True}


def test_on_empty_rewrite_keeps_original_body(tmp_path, monkeypatch, raw_clause):
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    _kernel, agent = _build(tmp_path)
    llm = _SeqLLM(ACK_THEN_SWITCH, "")
    payload = _run(agent, _dm_event(NEG_TEXT, "低落"), llm)

    assert payload["body"] == ACK_THEN_SWITCH
    rw = payload["ctx"]["echo"]["verify"]["rewrite"]
    assert rw == {"attempted": False, "accepted": False,
                  "before": {"has_cue": False, "ack_then_switch": True},
                  "after": None}


def test_cue_repair_false_disables_the_gate(tmp_path, monkeypatch):
    """消融口：`cue_repair=false` ⇒ ON 臂也退回 R31 行为（不重写、不多调用）。"""
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    EE.set_override({**EE.load_params(), "cue_repair": False})
    _kernel, agent = _build(tmp_path)
    llm = _SeqLLM(ACK_THEN_SWITCH, GOOD)
    payload = _run(agent, _dm_event(NEG_TEXT, "低落"), llm)

    assert len(llm.prompts) == 1
    assert payload["body"] == ACK_THEN_SWITCH
    assert "rewrite" not in payload["ctx"]["echo"]["verify"]


# ---------------------------------------------------------------- D OFF 臂逐字节不变
def test_off_arm_never_enters_the_gate(tmp_path):
    _kernel, agent = _build(tmp_path)
    ev = _dm_event(NEG_TEXT, "低落")
    llm = _SeqLLM(ACK_THEN_SWITCH, GOOD)
    payload = _run(agent, ev, llm)

    assert EE.enabled() is False
    assert len(llm.prompts) == 1, "OFF 臂不许多一次 LLM 调用"
    assert payload["body"] == ACK_THEN_SWITCH
    assert "echo" not in payload["ctx"], "OFF 臂 payload 不许出现 ctx.echo"
    assert "【情绪呼应" not in llm.prompts[0]

    history = agent._thread_history(_wv(ev), ev.payload["thread_id"], DT.DEFAULTS)
    baseline = agent._reply_prompt("P007", "闲聊", history, DT.DEFAULTS, wv=_wv(ev))
    assert llm.prompts[0] == baseline, "OFF 臂提示词必须与基线逐字节一致"


def test_off_arm_gate_entries_are_never_touched(tmp_path, monkeypatch):
    """OFF 臂最强证据：把闸门两个入口打成「一调用就炸」，回复链路仍跑通。"""
    def _boom(*_a, **_k):
        raise AssertionError("OFF 臂不应调用 N-05 闸门")

    monkeypatch.setattr(EE, "need_rewrite", _boom)
    monkeypatch.setattr(EE, "rewrite_line", _boom)
    _kernel, agent = _build(tmp_path)
    llm = _SeqLLM(ACK_THEN_SWITCH, GOOD)
    payload = _run(agent, _dm_event(NEG_TEXT, "低落"), llm)
    assert len(llm.prompts) == 1 and payload["body"] == ACK_THEN_SWITCH
    assert "echo" not in payload["ctx"]


def test_on_but_no_evidence_still_makes_one_call(tmp_path, monkeypatch):
    """ON 但对方那句没有情绪证据（证据门控挡掉）⇒ 无计划 ⇒ 闸门同样不执行。"""
    monkeypatch.setenv(EE.ECHO_ENV, "1")
    EE.reload()
    _kernel, agent = _build(tmp_path)
    llm = _SeqLLM(ACK_THEN_SWITCH, GOOD)
    payload = _run(agent, _dm_event(NEUTRAL_TEXT, "低落"), llm)

    assert len(llm.prompts) == 1
    assert "echo" not in payload["ctx"]
