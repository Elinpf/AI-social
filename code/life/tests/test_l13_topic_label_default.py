"""L-13 补丁单测：人话化**默认生效** + `LIFE_PROMPT_TOPIC_LABEL=off` 逐字节回退。

L-13（内部 token 泄漏）的成因：`agent._topic_label` 只在话题宽度臂
（`LIFE_PROMPT_TOPIC_BREADTH`，默认 OFF）打开时才把模板 id 换成人话，
所以默认跑批时 `whisper` / `combat_training` 这类内部 token 被直接递给模型。

补丁语义（本文件逐条钉死）：
  1. **默认（env 未设）**：`_topic_label` 无条件走 `TB.label`，20 个 `template_id`
     **全部**人话化，返回值里不含任何 ASCII 下划线形式的内部 token；
  2. **回退（`LIFE_PROMPT_TOPIC_LABEL=off`）**：逐字节复刻旧实现
     `TB.label(topic) if TB.enabled() else (topic or "")`
     ⇒ 宽度臂默认关闭时返回**原字符串**，可与默认臂做同树 OFF/ON 对照；
  3. **词表覆盖**：`TOPIC_LABELS` 覆盖 `code/config/activity_templates.json` 的全部
     `template_id`（补上唯一缺口 `burnout_event`）；
  4. **提示词级别**：默认臂提示词出现人话、不出现 token；回退臂提示词与「旧实现」
     生成的提示词**逐字节相等**（不是"看起来差不多"）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from life import topic_breadth as TB
from life.agent import LifeLayerAgent
from life.tests.test_r19_topic_breadth import _build, _dm_event, _reply, _wv

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"

#: 「ASCII 下划线形式的内部 token」判据（与 tools/d5/verify_l13.py 同一正则）
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]*")


def _template_ids() -> list[str]:
    data = json.loads((CONFIG / "activity_templates.json").read_text(encoding="utf-8"))
    return [t["template_id"] for t in data["templates"]]


def _agentless() -> LifeLayerAgent:
    """只调 `_topic_label`（纯函数，只读 TB）⇒ 不构造完整 agent 也行。"""
    return object.__new__(LifeLayerAgent)


def _legacy_topic_label(topic):
    """改造前的原实现，逐字节照抄（回退臂必须与它相等）。"""
    return TB.label(topic) if TB.enabled() else (topic or "")


# ---------------------------------------------------------------- 开关语义
@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(TB.BREADTH_ENV, raising=False)
    monkeypatch.delenv(TB.LABEL_ENV, raising=False)


def test_label_on_by_default():
    assert TB.label_enabled() is True, "人话化必须默认生效（L-13 的正解）"


@pytest.mark.parametrize("val", ["off", "0", "false", "no", "OFF", " off ", "False"])
def test_label_env_off(monkeypatch, val):
    monkeypatch.setenv(TB.LABEL_ENV, val)
    assert TB.label_enabled() is False


@pytest.mark.parametrize("val", ["on", "1", "true", "yes", "", "garbage", "enable"])
def test_label_env_on(monkeypatch, val):
    monkeypatch.setenv(TB.LABEL_ENV, val)
    assert TB.label_enabled() is True, "只有显式 off/0/false/no 才回退"


def test_label_env_independent_of_breadth(monkeypatch):
    """两把开关互相独立：宽度臂开不开都不影响人话化默认值。"""
    for breadth in ("", "1"):
        if breadth:
            monkeypatch.setenv(TB.BREADTH_ENV, breadth)
        else:
            monkeypatch.delenv(TB.BREADTH_ENV, raising=False)
        assert TB.label_enabled() is True


# ---------------------------------------------------------------- 默认臂：全量覆盖 + 无 token
def test_default_mode_humanizes_all_templates_without_tokens():
    agent = _agentless()
    ids = _template_ids()
    assert len(ids) == 20
    for tid in ids:
        out = agent._topic_label(tid)
        assert out != tid, f"{tid} 未被映射（覆盖缺口）"
        assert not TOKEN_RE.search(out), f"{tid} → {out!r} 仍含 ASCII 内部 token"
        assert tid not in out, f"{tid} 原字符串仍出现在人话里：{out!r}"


def test_default_mode_unknown_id_and_empty_pass_through():
    agent = _agentless()
    assert agent._topic_label("future_topic_v9") == "future_topic_v9", "未知 id 原样返回，不臆造"
    assert agent._topic_label("") == ""
    assert agent._topic_label(None) == ""


def test_topic_labels_cover_activity_templates():
    ids = set(_template_ids())
    missing = sorted(ids - set(TB.TOPIC_LABELS))
    assert missing == [], f"TOPIC_LABELS 仍缺 {missing}"
    assert "burnout_event" in TB.TOPIC_LABELS, "本轮补的缺口必须真的补上"
    for tid, label in TB.TOPIC_LABELS.items():
        assert label and not TOKEN_RE.search(label), f"{tid} 的人话含内部 token：{label!r}"


# ---------------------------------------------------------------- 回退臂：字节等价
@pytest.mark.parametrize("breadth", [None, "1"])
def test_off_mode_byte_equals_legacy(monkeypatch, breadth):
    if breadth:
        monkeypatch.setenv(TB.BREADTH_ENV, breadth)
    monkeypatch.setenv(TB.LABEL_ENV, "off")
    agent = _agentless()
    cases = _template_ids() + ["future_topic_v9", "", None]
    for t in cases:
        new = agent._topic_label(t)
        old = _legacy_topic_label(t)
        assert new == old, f"回退臂与旧实现不等：{t!r} new={new!r} old={old!r}"


def test_off_mode_with_breadth_off_returns_raw_string(monkeypatch):
    """宽度臂默认关闭 + 人话化回退 ⇒ 返回原字符串（旧跑批的真实行为）。"""
    monkeypatch.setenv(TB.LABEL_ENV, "off")
    agent = _agentless()
    for tid in _template_ids():
        assert agent._topic_label(tid) == tid


# ---------------------------------------------------------------- 提示词级（接线）
def test_prompt_default_humanized(tmp_path):
    _, agent = _build(tmp_path)
    prompt, payload = _reply(agent, _wv(_dm_event()), "我这心里也堵着事，先听你说。")
    assert "说悄悄话" in prompt, "默认臂提示词必须人话化"
    assert "whisper" not in prompt, "默认臂提示词不得再出现内部 token"
    assert "聊着聊着" not in prompt, "人话化与岔题臂无关：默认不岔题"
    assert payload["tag_hints"] == ["whisper"], "本补丁不动 tag_hints（不刷指标）"
    assert "topic_breadth" not in (payload.get("ctx") or {})


def test_prompt_off_mode_byte_equals_legacy_prompt(tmp_path, monkeypatch):
    """回退臂提示词与「旧实现」提示词逐字节相等（不是近似）。"""
    monkeypatch.setenv(TB.LABEL_ENV, "off")
    _, agent_off = _build(tmp_path / "off")
    prompt_off, _ = _reply(agent_off, _wv(_dm_event()), "我这心里也堵着事，先听你说。")
    assert "whisper" in prompt_off

    _, agent_legacy = _build(tmp_path / "legacy")
    agent_legacy._topic_label = lambda topic: (topic or "")   # 旧实现（宽度臂关闭）
    prompt_legacy, _ = _reply(agent_legacy, _wv(_dm_event()), "我这心里也堵着事，先听你说。")

    assert prompt_off == prompt_legacy, "回退臂必须与旧提示词逐字节相同"
