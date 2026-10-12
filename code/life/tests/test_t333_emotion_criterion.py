"""T333: 情感判据 `criterion ∈ {strict, natural}`（T332 08 口径）—— **合成单测**。

⚠️ 合成场景（贴标签）：纯函数级，验证
  * `strict` ⟺ 现 26 子串逐字节等价（消融基线）；
  * `natural` 容纳隐性表达（扩词表 + 结构信号兜底）；
  * 设不同 `criterion` ⇒ 行为随之变（agent 候选有无）。
"""
from __future__ import annotations

from life import emotion as E
from life.agent import LifeLayerAgent
from life.memory import MemoryNode


def _old_sign(text: str) -> int:
    """现状实现（26 子串、先 POS 后 NEG）—— strict 必须与之逐字节等价。"""
    low = (text or "").lower()
    if any(k in low for k in E.STRICT_POS):
        return 1
    if any(k in low for k in E.STRICT_NEG):
        return -1
    return 0


def test_strict_is_byte_equivalent_to_current_26():
    samples = ["我帮助了朋友", "感到成长", "support from peers", "冲突与挫折",
               "孤独 lonely", "mock::deadbeef（insight 1）", "（看了看天）走了啊",
               "心里踏实", "thanks!", ""]
    for t in samples:
        assert E.emotion_sign(t, criterion="strict") == _old_sign(t), t


def test_natural_accepts_implicit_expression():
    # 显式词表未命中，但含隐性线索 / 结构信号 ⇒ natural 命中，strict 不命中
    assert E.emotion_sign("心里踏实，也就这样了", criterion="strict") == 0
    assert E.emotion_sign("心里踏实，也就这样了", criterion="natural") == 1
    assert E.emotion_sign("（蹲在田埂上）……走了啊。", criterion="strict") == 0
    assert E.emotion_sign("（蹲在田埂上）……走了啊。", criterion="natural") == -1


def test_agent_candidate_depends_on_criterion():
    a = LifeLayerAgent.__new__(LifeLayerAgent)
    a.agent_id = "P1"
    a._drift_streak = {}
    n = MemoryNode(mem_id="M1", agent_id="P1", kind="reflection",
                   text="心里踏实", importance=8, day=0, slot="night", embed=[])
    a.memory = type("M", (), {"nodes": {"M1": n}})()
    import types
    a.kernel = types.SimpleNamespace(submit_intent=lambda aid, it: types.SimpleNamespace(ok=True))

    strict_params = {"persona_drift": {"min_importance": 7, "min_windows": 1, "criterion": "strict"}}
    a._drift_streak = {}
    assert a._reflection_drift_events(strict_params, day=1, slot="night", window=1) == []
    natural_params = {"persona_drift": {"min_importance": 7, "min_windows": 1, "criterion": "natural"}}
    a._drift_streak = {}
    assert len(a._reflection_drift_events(natural_params, day=1, slot="night", window=1)) == 1
