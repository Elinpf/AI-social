"""层间接口 IF-1~IF-7 + IF-2b/IF-2c 的 Protocol（蓝图 §2.1，B1）。

仅声明签名；具体实现分别在 kernel / life / emergence / freeze / narrative。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import (
    AgentId, AuditPayload, Event, Intent, IntentResult, JudgmentRequest, Round, WorldView,
)


@runtime_checkable
class ReadOnlyLog(Protocol):
    """只读账本句柄（IF-4 / kernel.ledger 的只读面）。"""
    def records(self) -> list: ...


@runtime_checkable
class KernelHandle(Protocol):
    """下层可见的内核句柄（唯一写入请求通道的入口）。"""
    def current_round(self) -> int: ...
    def emit_specs(self, specs: list) -> list: ...


@runtime_checkable
class KernelPort(Protocol):
    """IF-1/IF-2：生活层依赖的窄接口（由内核适配器实现）。"""
    def perceive(self, agent_id: AgentId) -> WorldView: ...
    def submit_intent(self, agent_id: AgentId, intent: Intent) -> IntentResult: ...
    def current_round(self) -> int: ...
    def derive_time(self, round_no: int | None = None): ...


@runtime_checkable
class FreezePort(Protocol):
    """冻结层出口（IF-2b / IF-2c）。"""
    def submit_judgment(self, agent_id: AgentId, req: JudgmentRequest, *, engine) -> Event: ...
    def submit_audit(self, payload: AuditPayload, *, engine) -> int: ...
    def get_frozen_judgment(self, judgment_id: str, *, log: ReadOnlyLog) -> str | int: ...
