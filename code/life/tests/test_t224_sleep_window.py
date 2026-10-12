"""T224 睡眠离线窗口（sleep_window）单元测试 —— 固化 / 遗忘 / 人格漂移 的挂载点。

验证：默认关=空计划；开=产出固化/遗忘/漂移事件；保护记忆**只降级**；无 LLM。
"""
from __future__ import annotations

from life import sleep_window as S


def _params(enabled: bool = True) -> dict:
    p = S.load_params()
    p["sleep"]["enabled"] = enabled
    p["forgetting"]["enabled"] = enabled
    return p


def _mem(mem_id: str, **kw) -> dict:
    base = {"mem_id": mem_id, "kind": "observation", "importance": 2, "last_access": 0,
            "access_count": 0, "subject": None, "emo": 0, "consolidated": False}
    base.update(kw)
    return base


def _anchor() -> dict:
    return {"persona_id": "P003",
            "personality_big5": {d: 50 for d in ("openness", "conscientiousness",
                                                 "extraversion", "agreeableness", "neuroticism")},
            "values": {"security": 65}, "skills": []}


def test_default_config_is_disabled():
    p = S.load_params()          # 读 code/config/life_v2.json
    assert p["sleep"]["enabled"] is False
    assert p["forgetting"]["enabled"] is False
    out = S.run_sleep_window("P003", [_mem("M1")], 100, p, day=7, slot="night")
    assert out["consolidate"] == [] and out["forget"] == [] and out["events"] == []


def test_enabled_emits_consolidate_and_forget_events():
    p = _params(True)
    mems = [_mem("M1", subject="P007", last_access=9999),
            _mem("M2", subject="P007", last_access=9999),
            _mem("M3", importance=1, subject=None, last_access=0)]
    out = S.run_sleep_window("P003", mems, round_no=100_000, params=p, day=3, slot="night")
    types = [e["type"] for e in out["events"]]
    assert "MEMORY_CONSOLIDATE" in types          # P007 有 2 条 → 固化
    assert "MEMORY_FORGET" in types               # M3 老化 → 遗忘
    assert out["consolidate"][0]["subject"] == "P007"


def test_protected_memory_only_demoted_in_events():
    """硬要求：保护记忆在睡眠窗口事件里**只出现 demote**。"""
    p = _params(True)
    mems = [_mem("M-KEEP", importance=9, subject="P007", last_access=0),
            _mem("M-SIB", importance=9, subject="P007", last_access=0),
            _mem("M-DROP", importance=1, subject=None, last_access=0)]
    out = S.run_sleep_window("P003", mems, round_no=100_000, params=p, day=3, slot="night")
    forget = {e["payload"]["mem_id"]: e["payload"] for e in out["events"]
              if e["type"] == "MEMORY_FORGET"}
    assert forget["M-KEEP"]["level"] == "demote"
    assert forget["M-KEEP"]["level"] not in ("merge", "drop")
    assert forget["M-DROP"]["level"] == "drop"


def test_persona_section_present_and_bounded():
    p = _params(True)
    a = _anchor()
    st = dict(a["personality_big5"])
    out = S.run_sleep_window("P003", [], 100, p, day=0, slot="night",
                             anchor=a, p_state=st, p0=dict(st),
                             drift_events=[{"dim": "openness", "delta": 1,
                                            "cause_mem_id": "M-1"}])
    assert out["persona"] is not None
    assert out["persona"]["within_bounds"] is True
    assert any(e["type"] == "PERSONA_DRIFT" for e in out["events"])


def test_no_llm_dependency():
    """睡眠窗口/遗忘/漂移均不得依赖 LLM 模块（不新增决策类调用）。"""
    import inspect
    src = inspect.getsource(S) + inspect.getsource(__import__("life.forgetting", fromlist=["x"])) \
        + inspect.getsource(__import__("life.persona_drift", fromlist=["x"]))
    assert "import llm" not in src and "from .llm" not in src and ".llm." not in src
