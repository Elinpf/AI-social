"""Visibility — a single pure reimplementation of `visible_events()` (08 §3.5 R1/R2).

The engine owns the canonical PERCEPTION_SCOPE config; the life layer reads the same
table (via `constants.PERCEPTION_SCOPE`) so perception and relation updates never use
LLM judgement for visibility (T26/T27 discipline). This helper is used by the
test-double kernel and mirrors `engine.perceive.visible_events`.
"""
from __future__ import annotations

from . import constants as C
# T264：委托**唯一真源** `contracts.visibility`（与 engine/adapter 同源，杜绝漂移）
from contracts.visibility import location_of as _loc, visible_events as _ve


def location_of(records: list, agent_id: str, upto_round: int,
                initial: str = "residence") -> str:
    return _loc(records, agent_id, upto_round, initial)


def visible_events(records: list, agent_id: str, upto_round: int,
                   window_rounds: int | None = None, *, location: str | None = None) -> list:
    """Return the events `agent_id` can directly perceive, per PERCEPTION_SCOPE（单一真源）。"""
    return _ve(records, agent_id, upto_round,
               scope_table=C.PERCEPTION_SCOPE, default_cls=C.DEFAULT_VISIBILITY,
               window_rounds=window_rounds, location=location)
