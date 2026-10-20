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

# T264 步骤⑤：**组合根注入**的增量索引（方案 C）。按 `id(records)` 绑定，避免多世界串扰；
# 未注册时回退到纯全扫（默认行为不变）。
_INDEXES: dict[int, object] = {}


def register_index(records: list, fn) -> None:
    """注册某账本对象的可见性索引（`fn(agent_id, upto, *, window_rounds, location)`）。"""
    _INDEXES[id(records)] = fn


def unregister_index(records: list) -> None:
    _INDEXES.pop(id(records), None)


def clear_indexes() -> None:
    _INDEXES.clear()


def location_of(records: list, agent_id: str, upto_round: int,
                initial: str = "residence") -> str:
    return _loc(records, agent_id, upto_round, initial)


def visible_events(records, agent_id: str, upto_round: int,
                   window_rounds: int | None = None, *, location: str | None = None,
                   world_event_window: bool = False) -> list:
    """Return the events `agent_id` can directly perceive（单一真源；有索引则走索引）。

    T330：`records` 可为 **list**（账本）或 **dict**（`state.event_index`，`{seq: rec}`）；
    索引 provider 按**传入对象的 `id`** 命中（故调用方须传**稳定对象**，勿每次新建 list）。
    """
    fn = _INDEXES.get(id(records))
    if fn is not None:
        return fn(agent_id, upto_round, window_rounds=window_rounds, location=location,
                  world_event_window=world_event_window)
    recs = list(records.values()) if isinstance(records, dict) else records
    return _ve(recs, agent_id, upto_round,
               scope_table=C.PERCEPTION_SCOPE, default_cls=C.DEFAULT_VISIBILITY,
               window_rounds=window_rounds, location=location,
               place_local_actor_fallback=C.PLACE_LOCAL_ACTOR_FALLBACK,
               world_event_window=world_event_window)
