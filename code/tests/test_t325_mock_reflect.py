"""T325: mock 反思文本保真度（可读 + 含情绪词）⇒ `PERSONA_DRIFT` 在 mock 下可 e2e 触发。

⚠️ 保真度声明：本测试只证明**装置（mock）**能产出含情绪词的反思文本；**mock 可触发 ≠ 真世界可触发**
（T326 实测：真 LLM 下 26 词表命中 0/63，主根因是判据太窄，属 T332/T333）。
"""
from __future__ import annotations

import types

from freeze.providers import MockProvider
from life.agent import LifeLayerAgent
from life.memory import MemoryNode

_KWS = tuple(LifeLayerAgent._DRIFT_POS) + tuple(LifeLayerAgent._DRIFT_NEG)


def _reflect_text(p: MockProvider, i: int) -> str:
    return p.complete(system="你是青溪镇居民，请反思",
                      user=f"第{i}天反思：回顾今天", extra={"purpose": "reflect"}).text


def test_mock_reflect_contains_emotion_keywords():
    p = MockProvider()
    for i in range(12):
        t = _reflect_text(p, i)
        assert not t.startswith("mock::"), f"应可读、非纯哈希：{t!r}"
        low = t.lower()
        assert any(k in low for k in _KWS), f"应含情感词：{t!r}"


def test_mock_reflect_deterministic():
    p1, p2 = MockProvider(), MockProvider()
    assert _reflect_text(p1, 3) == _reflect_text(p2, 3)


def test_non_nl_purpose_unchanged():
    """非自然语言用途（如 importance）保持原 `mock::<hash>` 行为（最小改动面）。"""
    p = MockProvider()
    t = p.complete(system="s", user="u", extra={"purpose": "importance"}).text
    assert t.startswith("mock::")


def test_soft_judge_options_still_respected():
    """软判定 options 分支不受影响：仍确定性 ∈ options。"""
    p = MockProvider()
    t = p.complete(system="s", user="u",
                   extra={"purpose": "judge", "options": ["formed", "not_formed"]}).text
    assert t in ("formed", "not_formed")


def _agent(nodes):
    a = LifeLayerAgent.__new__(LifeLayerAgent)
    a.agent_id = "P1"
    a._drift_streak = {}
    a.memory = types.SimpleNamespace(nodes={n.mem_id: n for n in nodes})
    a.kernel = types.SimpleNamespace(
        submit_intent=lambda aid, intent: types.SimpleNamespace(ok=True))
    return a


def test_persona_drift_e2e_triggerable_with_mock_reflect():
    """两个连续窗口的 mock 反思文本 ⇒ `_reflection_drift_events` 发 `PERSONA_DRIFT`。"""
    p = MockProvider()
    params = {"persona_drift": {"delta_max": 1, "min_windows": 2, "min_importance": 7}}

    def nodes(win: int):
        out = []
        for i in range(3):
            text = f"{_reflect_text(p, win * 10 + i)}（insight {i + 1}）"
            out.append(MemoryNode(mem_id=f"M-w{win}-{i}", agent_id="P1", kind="reflection",
                                  text=text, importance=6 + i, day=win, slot="night", embed=[]))
        return out

    a = _agent(nodes(1) + nodes(2))
    assert a._reflection_drift_events(params, day=1, slot="night", window=1) == []  # 单窗不发
    evs = a._reflection_drift_events(params, day=2, slot="night", window=2)
    assert len(evs) >= 1, "含情绪词的 mock 反思应在第 2 窗触发 PERSONA_DRIFT"
    from life.persona_drift import BIG5_DIMS

    for e in evs:
        assert e["dim"] in BIG5_DIMS
        assert e["delta"] in (1, -1) and e["cause_mem_id"]
