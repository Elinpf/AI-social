"""R12 · L-7 去重臂（`life/anti_repeat.py`）单测。

四条硬断言（对应本轮预注册口径，见 `reports/R12-l7-dequp.md` §3）：
  A. **默认 OFF 零扰动**：`enabled()` False、`prompt_line()` 空串、`collide()` None、
     提示词与接入前逐字节一致、payload 里不出现 `ctx.dequp`。
  B. **口径镜像不漂移**：`anti_repeat.normalize` 与官方
     `tools/d5/dialogue_metrics.py::normalize_body` 在同一批样例上逐字相同。
  C. **撞车判定与回喂有界**：8-gram 重合才判撞车；重试**最多 1 次**（2 次调用封顶）。
  D. **ON 时单变量**：提示词 = OFF 提示词 + 恰好一处插入；审计字段可读。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from life import anti_repeat as AR
from life import l7_structural as L7S
from life.agent import LifeLayerAgent
from life.llm import LLMResult
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas

CODE_DIR = Path(__file__).resolve().parents[1]
REPO = CODE_DIR.parent
CONFIG = CODE_DIR / "config"
SELF_ID = "P003"
PARTNER_ID = "P002"


class _StubKernel:
    def submit_intent(self, *a, **kw):  # pragma: no cover - 本测试不落事件
        pass


@pytest.fixture(autouse=True)
def _isolate_dequp_arm(monkeypatch):
    """R17 起 L-7 **结构臂**（`life/l7_structural.py`，默认 ON）在 `_dequp_body`
    里接管「生成前约束、不重试」。本文件测的是 DEQUP 臂自身的撞车重试行为，
    必须把结构臂显式关掉才是单变量（与 `test_l7_structural.py` 互不干扰）。
    """
    monkeypatch.setenv(L7S.STRUCT_ENV, "0")
    yield


def _agent(tmp_path: Path) -> LifeLayerAgent:
    personas = load_personas(CONFIG / "personas.json")
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    return LifeLayerAgent(SELF_ID, personas[SELF_ID], _StubKernel(),
                          side_store=SideStore(tmp_path / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peers=sorted(personas),
                          peer_names={k: v.display_name for k, v in personas.items()})


def _official_normalize():
    """从 tools/d5/dialogue_metrics.py 取出官方 normalize_body（不可用则 skip）。"""
    path = REPO / "tools" / "d5" / "dialogue_metrics.py"
    if not path.exists():
        pytest.skip("tools/d5/dialogue_metrics.py 不可用（分支/打包场景）")
    spec = importlib.util.spec_from_file_location("_dm_official", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.normalize_body


def test_env_default_off(monkeypatch):
    """A. 开关默认关。"""
    monkeypatch.delenv(AR.DEQUP_ENV, raising=False)
    assert AR.enabled() is False
    for v in ("1", "true", "YES", " on "):
        monkeypatch.setenv(AR.DEQUP_ENV, v)
        assert AR.enabled() is True
    monkeypatch.setenv(AR.DEQUP_ENV, "0")
    assert AR.enabled() is False


def test_off_prompts_and_payload_untouched(monkeypatch, tmp_path):
    """A. OFF ⇒ 提示词无插入段、payload 无 dequp 键；ON ⇒ 只多一处插入。"""
    monkeypatch.setenv(AR.DEQUP_ENV, "0")
    AR.reset()
    agent = _agent(tmp_path)
    history = [("名2", "早上好。")]
    d_off = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    r_off = agent._reply_prompt(PARTNER_ID, "tpl-1", history)
    assert AR.prompt_line() == ""
    assert "镇上刚有人这么说" not in d_off
    assert "dequp" not in agent._ctx_snapshot(PARTNER_ID, "tpl-1")

    monkeypatch.setenv(AR.DEQUP_ENV, "1")
    AR.reset()
    AR.remember("今天这锅汤我少放了半勺盐。")
    seg = AR.prompt_line()
    assert seg.startswith("\n镇上刚有人这么说")
    d_on = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    r_on = agent._reply_prompt(PARTNER_ID, "tpl-1", history)
    # 单变量：ON = OFF + 恰好一处插入（且与两处插入同串）
    assert d_on.count(seg) == 1 and r_on.count(seg) == 1
    assert d_on.replace(seg, "", 1) == d_off
    assert r_on.replace(seg, "", 1) == r_off
    assert agent._ctx_snapshot(PARTNER_ID, "tpl-1")["dequp"]["v"] == "l7-dequp/1"
    AR.reset()


def test_normalize_mirrors_official():
    """B. 口径镜像：与官方 normalize_body 逐字一致（8-gram 判定不另立口径）。"""
    official = _official_normalize()
    samples = [
        "今天这锅汤我少放了半勺盐，多搁了一小把干贝。",
        "老石啊，你尝尝这个新烤的桂花糕（2026-10-21）……",
        "  Mixed 大小写 ABC 123，带\t制表符  ",
        "“引号”‘单引号’【方括号】[中括号]",
        "",
    ]
    for s in samples:
        assert AR.normalize(s) == official(s), s


def test_collide_requires_8gram_overlap(monkeypatch):
    """C. 8-gram 口径：重合才判撞车，短串（<8 字）不参与判定。"""
    monkeypatch.setenv(AR.DEQUP_ENV, "1")
    AR.reset()
    AR.remember("今天这锅汤我少放了半勺盐，多搁了一小把干贝")
    hit = AR.collide("今天这锅汤我少放了半勺盐，多搁了一小把干贝，鲜得很")
    assert hit is not None and "少放了半勺盐" in hit
    assert AR.collide("我去集市上转了一圈，买了些青菜") is None
    assert AR.collide("短句") is None
    AR.reset()


def test_retry_is_bounded_to_one(monkeypatch, tmp_path):
    """C. 撞车重试最多 1 次：两次都撞 ⇒ 仍只多 1 次调用，最终采纳第二次文本。"""
    monkeypatch.setenv(AR.DEQUP_ENV, "1")
    AR.reset()
    AR.remember("今天这锅汤我少放了半勺盐，多搁了一小把干贝")
    agent = _agent(tmp_path)
    calls = []

    class _FakeLLM:
        def call(self, purpose, prompt, *, model=None, meta=None):
            calls.append({"purpose": purpose, "prompt": prompt, "meta": meta})
            return LLMResult(text="今天这锅汤我少放了半勺盐，多搁了一小把干贝，味儿正好")

    agent.llm = _FakeLLM()
    out = agent._dequp_body("BASE", "今天这锅汤我少放了半勺盐，多搁了一小把干贝，鲜得很", {"a": 1})
    assert len(calls) == 1, "撞车只允许重试一次"
    assert calls[0]["meta"]["dequp_retry"] == 1
    assert "换个说法重说一句" in calls[0]["prompt"]
    assert out.startswith("今天这锅汤我少放了半勺盐")
    AR.reset()


def test_off_means_zero_extra_calls(monkeypatch, tmp_path):
    """A/C. OFF ⇒ 撞车检查与记账都是 no-op，不产生任何额外 LLM 调用。"""
    monkeypatch.setenv(AR.DEQUP_ENV, "0")
    AR.reset()
    agent = _agent(tmp_path)
    calls = []

    class _FakeLLM:
        def call(self, purpose, prompt, *, model=None, meta=None):  # pragma: no cover
            calls.append(1)
            return LLMResult(text="x")

    agent.llm = _FakeLLM()
    body = "今天这锅汤我少放了半勺盐，多搁了一小把干贝"
    assert agent._dequp_body("BASE", body, {}) == body
    assert calls == []
    assert AR.mem_usage("M-P001-000007") == 0
    assert AR.audit()["messages"] == 0
