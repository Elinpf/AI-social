"""T361: `LLM_CALL` 调用主体归属（T360 登记）——`agent_id` 从 `meta` 提升为一等字段。

口径（唯一准 = `v1.1/08 §1.2 G-lg` / T360）：`LLM_CALL.agent_id` 可选；
取值 ∈ AgentId ∪ {SYSTEM, DIRECTOR, OBSERVER}；**缺省（不写键）= 未归属 UNATTRIBUTED**；`actor` 不改。
"""
from __future__ import annotations

import tempfile
from dataclasses import replace

from freeze import EventLog, FreezeConfig, LLMClient, MockProvider, Mode, Tier
from freeze.events import llm_call_payload


def _client(tmp: str, mode=Mode.RUN) -> LLMClient:
    return LLMClient(FreezeConfig(engine_version="v1.1+test", mode=mode, cache_dir=tmp),
                     provider=MockProvider(), event_log=EventLog())


def test_agent_id_lifted_from_meta():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        c.complete(purpose="reflect", system="s", user="u",
                   tier=Tier.T1, meta={"agent_id": "P001", "round": 3})
        p = c.event_log.of_type("LLM_CALL")[-1]["payload"]
        assert p["agent_id"] == "P001"
        # actor 不改（审计桥"发射者"语义）
        assert c.event_log.of_type("LLM_CALL")[-1]["actor"] == "SYSTEM"


def test_unattributed_when_no_agent_id_key_absent():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        # 无 meta
        c.complete(purpose="dialogue", system="s", user="u1", tier=Tier.T1)
        p1 = c.event_log.of_type("LLM_CALL")[-1]["payload"]
        assert "agent_id" not in p1, "缺省=未归属：不得写入该键（不伪装成某人）"
        # meta 无 agent_id
        c.complete(purpose="dialogue", system="s", user="u2", tier=Tier.T1,
                   meta={"round": 1})
        p2 = c.event_log.of_type("LLM_CALL")[-1]["payload"]
        assert "agent_id" not in p2


def test_nonresident_subject_not_a_resident():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        c.complete(purpose="describe", system="s", user="u", tier=Tier.T1,
                   meta={"agent_id": "DIRECTOR"})
        p = c.event_log.of_type("LLM_CALL")[-1]["payload"]
        assert p["agent_id"] == "DIRECTOR"


def test_payload_helper_optional_agent_id():
    base = dict(purpose="plan", model="m", engine_version="ev", prompt_hash="ph",
                cache_key="k", tier="T1", priority="normal", degraded=False, cached=False,
                tokens_in=1, tokens_out=1, cost_units=1, provider="mock")
    # 不给 agent_id → 键不存在（旧日志兼容）
    assert "agent_id" not in llm_call_payload(**base)
    # 给出 → 键存在
    assert llm_call_payload(**base, agent_id="P007")["agent_id"] == "P007"


def test_replay_reparses_payload_without_agent_id():
    """旧日志（payload 无 agent_id）仍可被正常"解析/使用"（此处以读回断言）。"""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        c.complete(purpose="importance", system="s", user="u", tier=Tier.T1)
        rec = c.event_log.of_type("LLM_CALL")[-1]
        # 模拟"旧日志"：删掉 agent_id 键（本就不存在）
        assert "agent_id" not in rec["payload"]
        # 消费方守卫式读取不应抛错
        assert rec["payload"].get("agent_id") is None
