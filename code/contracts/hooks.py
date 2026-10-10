"""中央裁决器 hook 契约（蓝图 §2.3，B1）。

hook 是纯函数：`hook(state, round, ctx) -> Delta`；内核只持本 Protocol，
life hook 由 orchestration/注册表依赖倒置注入（内核不 import life）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Ctx(Protocol):
    """传入每个 hook 的上下文；唯一随机源。"""
    seed: int
    round: int
    time_cfg: dict
    config: dict

    def rng(self, stream_id: str, seq: int, n: int) -> list[int]: ...
    def derive_time(self, round_no: int) -> dict: ...


@dataclass
class Delta:
    """hook 返回：新 state + 产出的 events + 待结算意图。"""
    state: Any
    events: list = field(default_factory=list)
    pending_intents: list = field(default_factory=list)


class HookFn(Protocol):
    def __call__(self, state: Any, round_no: int, ctx: Any) -> list: ...
