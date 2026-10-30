"""D9i 旁白通道臂（`LIFE_PROMPT_NARRATION`）单测。

验收口径（v2/refs/D9i-prereg-narration-toggle.md 硬约束 1/2/3）：
  1. **env 未设 / =0 ⇒ prompt 与改动前逐字节等价**：用改动前基线（commit b2d81ea）实测的
     两条 prompt 的 sha256 常量做断言（GOLDEN_*）；同一输入、同一装配路径。
  2. **单变量**：env=1 时，两条 prompt 与 OFF 版本**只在收尾指令这一段**不同
     （把该段换掉后逐字节相等），其余文本完全相同。
  3. **ON 的语义边界**：允许成对括号的动作/神态/眼前景，但明确仍禁止心理独白/旁白叙事。

复算命令（在仓库根、code/ 在 sys.path）：
    python3 -m pytest code/life/tests/test_narration_toggle.py -q
或手工复算 sha256：
    python3 tools/d9i/prompt_sha_probe.py            # 打印 OFF/ON 两条 prompt 的 sha256
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import dialogue_threads as DT
from life.agent import (
    NARRATION_ENV,
    LifeLayerAgent,
    narration_enabled,
    narration_tail,
)
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"

#: 改动前基线（commit b2d81ea）实测：同输入下 `_dialogue_prompt` / `_reply_prompt` 的 sha256
GOLDEN_INITIATE_SHA256 = "e3101a7c7b5b1432ca09bee788f925b1a4927c34a1611a658a06d8e5dab9ddf3"
GOLDEN_REPLY_SHA256 = "c5148cb59997b5b2ec98ab115e936080a24c132e76a3ac5162394d653a0a55d7"

OFF_INITIATE_TAIL = "\n只写台词本身（一句家常话）：不要用括号、方括号或星号写动作、神态或心理旁白，不要解释也不要总结；用口语短句，别反复用同一句口头禅。"
OFF_REPLY_TAIL = "\n只写台词本身（接着刚才的话往下说一句）：不要用括号、方括号或星号写动作、神态或心理旁白，不要解释也不要总结；用口语短句，别反复用同一句口头禅。"


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
    return agent


def _wv():
    return SimpleNamespace(round=12, visible_events=[], location="market",
                           current_activity={"activity_type": "trade", "place": "market"},
                           inventory=(), time=SimpleNamespace(slot="evening",
                                                              day_of_week=3, day=3))


def _prompts(tmp: Path):
    agent = _build(tmp)
    cfg = dict(DT.DEFAULTS)
    history = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=_wv()),
            agent._reply_prompt("P007", "rel_maintain", history, cfg, wv=_wv(), turn=1))


@pytest.fixture()
def tmp_side(tmp_path):
    return tmp_path


def test_env_unset_uses_config_default(tmp_side, monkeypatch):
    """ROUND1 默认化：env **未设** ⇒ 走配置默认值（`prompt.narration.enabled=true`）⇒ 两条 prompt 为 ON 臂。

    默认化前这里是「env 未设 = 与基线逐字节等价」；该断言已下移为
    `test_env_explicit_zero_is_byte_identical_to_baseline`（默认化后只有显式 `=0` 才是禁旁白）。
    """
    monkeypatch.delenv(NARRATION_ENV, raising=False)
    p_init, p_reply = _prompts(tmp_side)
    assert p_init.endswith(narration_tail("initiate"))
    assert p_reply.endswith(narration_tail("reply"))
    assert narration_tail("initiate") != OFF_INITIATE_TAIL
    assert narration_tail("reply") != OFF_REPLY_TAIL


def test_env_explicit_zero_is_byte_identical_to_baseline(tmp_side, monkeypatch):
    """硬约束 2（默认化后仍成立）：显式 `LIFE_PROMPT_NARRATION=0` ⇒ 与改动前逐字节等价。"""
    monkeypatch.setenv(NARRATION_ENV, "0")
    p_init, p_reply = _prompts(tmp_side)
    assert hashlib.sha256(p_init.encode()).hexdigest() == GOLDEN_INITIATE_SHA256
    assert hashlib.sha256(p_reply.encode()).hexdigest() == GOLDEN_REPLY_SHA256
    # 收尾指令仍是原字面量
    assert p_init.endswith(OFF_INITIATE_TAIL)
    assert p_reply.endswith(OFF_REPLY_TAIL)


@pytest.mark.parametrize("val", ["0", "", "false", "off", "2"])
def test_env_zero_is_byte_identical_to_baseline(tmp_side, monkeypatch, val):
    """硬约束 2：env=0（及其它非真值，含显式空串）⇒ 仍与改动前逐字节一致。"""
    monkeypatch.setenv(NARRATION_ENV, val)
    p_init, p_reply = _prompts(tmp_side)
    assert hashlib.sha256(p_init.encode()).hexdigest() == GOLDEN_INITIATE_SHA256
    assert hashlib.sha256(p_reply.encode()).hexdigest() == GOLDEN_REPLY_SHA256


def test_env_one_allows_narration_only_in_tail(tmp_side, monkeypatch):
    """硬约束 3：env=1 ⇒ 只换收尾指令这一段（单变量），且允许成对括号、仍禁心理独白/旁白叙事。"""
    monkeypatch.setenv(NARRATION_ENV, "0")
    off_init, off_reply = _prompts(tmp_side)

    monkeypatch.setenv(NARRATION_ENV, "1")
    on_init, on_reply = _prompts(tmp_side)

    # (a) 单变量：把 OFF 的收尾指令替换成 ON 的，应与 ON 逐字节相等
    assert narration_tail("initiate") != OFF_INITIATE_TAIL
    assert on_init == off_init[: -len(OFF_INITIATE_TAIL)] + narration_tail("initiate")
    assert on_reply == off_reply[: -len(OFF_REPLY_TAIL)] + narration_tail("reply")

    # (b) 除收尾指令外，前缀逐字节相同
    assert on_init[: -len(narration_tail("initiate"))] == off_init[: -len(OFF_INITIATE_TAIL)]
    assert on_reply[: -len(narration_tail("reply"))] == off_reply[: -len(OFF_REPLY_TAIL)]

    # (c) 语义边界：放开成对括号的动作/神态/眼前景，但仍明确禁心理独白/旁白叙事
    for tail in (narration_tail("initiate"), narration_tail("reply")):
        assert "成对" in tail and "（）" in tail
        assert "动作" in tail and ("神态" in tail or "景" in tail)
        assert "不要写心理独白或旁白叙事" in tail
        # 不再整体禁止括号
        assert "不要用括号" not in tail


def test_narration_enabled_parsing(monkeypatch):
    """开关解析：真值 {1,true,yes,on} 开；其余**已设**值（含 0 / 空串）关；未设 ⇒ 配置默认（本轮为开）。"""
    for v in ["1", "true", "TRUE", "yes", "On", " 1 "]:
        monkeypatch.setenv(NARRATION_ENV, v)
        assert narration_enabled() is True
    for v in ["0", "", "false", "off", "no", "2", "enabled"]:
        monkeypatch.setenv(NARRATION_ENV, v)
        assert narration_enabled() is False
    # ROUND1 默认化：未设不再是"关"，而是回落配置文件（`prompt.narration.enabled=true`）
    monkeypatch.delenv(NARRATION_ENV, raising=False)
    from life.agent import narration_config_default
    assert narration_config_default() is True
    assert narration_enabled() is True
