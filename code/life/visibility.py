"""Visibility — a single pure reimplementation of `visible_events()` (08 §3.5 R1/R2).

The engine owns the canonical PERCEPTION_SCOPE config; the life layer reads the same
table (via `constants.PERCEPTION_SCOPE`) so perception and relation updates never use
LLM judgement for visibility (T26/T27 discipline). This helper is used by the
test-double kernel and mirrors `engine.perceive.visible_events`.
"""
from __future__ import annotations

from . import constants as C


def location_of(records: list, agent_id: str, upto_round: int,
                initial: str = "residence") -> str:
    loc = initial
    for rec in records:
        if rec["round"] > upto_round:
            break
        if rec["type"] in ("PLACE_MOVE", "PLACE_ARRIVED"):
            p = rec.get("payload", {})
            if p.get("agent_id") == agent_id:
                loc = p.get("to_place") or p.get("place") or loc
    return loc


def _visible(cls: str, agent_id: str, actor: str, p: dict, loc: str) -> bool:
    if cls == "global":
        return True
    if cls == "place_local":
        return p.get("place") == loc
    if cls in ("subject_only", "private"):
        return (p.get("agent_id") == agent_id or p.get("observer") == agent_id
                or p.get("subject") == agent_id or actor == agent_id)
    if cls == "participants_only":
        return (agent_id in (p.get("participants") or [])
                or agent_id in (p.get("from"), p.get("to"), actor))
    if cls == "members":
        return agent_id in (p.get("members") or [])
    return actor == agent_id


def visible_events(records: list, agent_id: str, upto_round: int,
                   window_rounds: int | None = None, *, location: str | None = None) -> list:
    """Return the events `agent_id` can directly perceive, per PERCEPTION_SCOPE."""
    loc = location if location is not None else location_of(records, agent_id, upto_round)
    out = []
    for rec in records:
        if rec["round"] > upto_round:
            break
        if window_rounds is not None and rec["round"] < upto_round - window_rounds:
            continue
        cls = C.PERCEPTION_SCOPE.get(rec["type"], C.DEFAULT_VISIBILITY)
        p = rec.get("payload", {})
        if _visible(cls, agent_id, rec.get("actor", "SYSTEM"), p, loc):
            out.append(rec)
    return out
