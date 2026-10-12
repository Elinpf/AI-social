"""基础数据模型（蓝图 §2.0/§2.1，B1）。纯 dataclass，零业务依赖。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# ---- 基础别名（v1/03 §2.1）----
AgentId = str
Round = int
Mu = int
Phase = int  # 0..6 与 35（=Phase 3.5 LIFE）


@dataclass(frozen=True)
class Event:
    """事件外壳（v1 §6.1 + 08 §1.1）。"""
    seq: int
    round: Round
    phase: Phase
    actor: str            # AgentId | "SYSTEM" | "OBSERVER" | "DIRECTOR"
    type: str
    payload: dict
    mono_ts: int
    prev_hash: str
    hash: str


@dataclass(frozen=True)
class TurnSeal:
    """每回合封条（蓝图 §3.2；不进主链，避免自指）。"""
    round: Round
    first_seq: int
    last_seq: int
    round_hash: str
    prev_seal_hash: str


@dataclass(frozen=True)
class TimeCoord:
    week: int
    day: int
    day_of_week: int
    day_type: str
    slot: str
    tick_in_slot: int


@dataclass(frozen=True)
class EventView:
    seq: int
    round: Round
    phase: Phase
    actor: str
    type: str
    payload: dict
    place: str | None = None


@dataclass(frozen=True)
class MemoryRef:
    mem_id: str
    kind: str
    body_ref: str
    embed_ref: str
    importance: int
    day: int
    slot: str
    subject: str | None = None
    source_event_seq: int | None = None
    last_access: int = 0
    access_count: int = 0


@dataclass(frozen=True)
class WorldView:
    """IF-1 返回（反泄漏：只含决策时点可见信息）。"""
    agent_id: AgentId
    round: Round
    time: TimeCoord
    status: str
    location: str
    cash: Mu
    net_worth: Mu
    visible_events: tuple = ()
    memory_refs: tuple = ()
    inbox: tuple = ()


@dataclass(frozen=True)
class Intent:
    """IF-2 载荷（08 §4.2 分类）。"""
    intent_class: str
    agent_id: AgentId
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IntentResult:
    ok: bool
    reason: str | None = None
    event_seqs: tuple = ()


@dataclass(frozen=True)
class JudgmentRequest:
    """IF-2b 载荷（08 §1.2 I）。"""
    dimension: str
    parties: list = field(default_factory=list)
    question_ref: str = ""
    envelope: dict = field(default_factory=dict)
    context_ref: str | None = None


@dataclass(frozen=True)
class AuditPayload:
    """IF-2c 载荷（蓝图 §2.2.1）。kind ∈ {LLM_CALL, LLM_JUDGMENT, NARRATIVE}。"""
    kind: Literal["LLM_CALL", "LLM_JUDGMENT", "NARRATIVE"]
    actor: str
    phase: Phase
    body: dict = field(default_factory=dict)
