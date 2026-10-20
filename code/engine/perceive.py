"""IF-1 perceive：为单个 Agent 构造只读 WorldView（无副作用）。

确定性、无 LLM；visible_events 依据 PERCEPTION_SCOPE（config）+ location(agent,t) 重算。
骨架实现覆盖基础 visibility_class；记忆链/一阶「听说」等由 life/obs 层扩展。
"""

from __future__ import annotations

import json
from pathlib import Path

from .time import derive_time

_PERCEPTION_SCOPE_PATH = Path(__file__).resolve().parents[1] / "config" / "perception_scope.json"
_PERCEPTION_SCOPE_CACHE: dict | None = None


def load_perception_scope(config_dir=None) -> dict:
    """严格加载（单一来源 `config/perception_scope.json`；缺失/版本不匹配 → 抛错）。

    返回 {'version','default_visibility_class','scope'}；无静默回退。
    """
    from . import version
    scope, default_cls, ver = version.load_perception_scope(config_dir)
    return {"version": ver, "default_visibility_class": default_cls, "scope": scope}


def _load_time_flags(config: dict | None = None) -> dict:
    """T354：`config/time.json` 开关（ongoing 默认 true）。

    T355 修复：**优先读传入的运行时 config**（`config["time"]["ongoing"]["enabled"]`），
    缺省回退文件 —— 否则经 config 覆盖的消融在 inline/mini 路径会被**静默丢弃**。
    """
    if isinstance(config, dict):
        t = config.get("time") or {}
        og = t.get("ongoing") or {}
        if "enabled" in og:
            return {"ongoing_enabled": bool(og["enabled"])}
    from . import version
    try:
        return version.load_time_flags()
    except Exception:
        return {"ongoing_enabled": True}


def location_of(records: list, agent_id: str, upto_round: int) -> str:
    """由 PLACE_MOVE/PLACE_ARRIVED 折叠当前位置，默认 residence。"""
    loc = "residence"
    for rec in records:
        if rec["round"] > upto_round:
            break
        if rec["type"] in ("PLACE_MOVE", "PLACE_ARRIVED"):
            p = rec.get("payload", {})
            if p.get("agent_id") == agent_id:
                loc = p.get("to_place") or p.get("place") or loc
    return loc


def visible_events(records: list, agent_id: str, upto_round: int, config: dict | None = None) -> list:
    """T264：选择委托**唯一真源** `contracts.visibility`；仍返回 dict 投影（保持本模块对外契约）。"""
    from contracts.visibility import visible_events as _ve
    from . import version
    scope = load_perception_scope()
    recs = _ve(records, agent_id, upto_round,
               scope_table=scope.get("scope", {}),
               default_cls=scope.get("default_visibility_class", "place_local"),
               place_local_actor_fallback=version.load_visibility_flags().get(
                   "place_local_actor_fallback", False),
               world_event_window=world_event_window_enabled(config))
    return [{
        "seq": r["seq"], "round": r["round"], "phase": r["phase"],
        "actor": r["actor"], "type": r["type"],
        "payload": r.get("payload", {}), "place": r.get("payload", {}).get("place"),
    } for r in recs]


def world_event_window_enabled(config: dict | None) -> bool:
    """D8：世界事件 `[start,end)` 时间窗裁剪开关（`config["world_awareness"]`；默认 False）。

    缺省/缺失 ⇒ False（= 基线 2090287 行为等价，世界事件对已登记可见类仍永久可见）。
    """
    wa = (config or {}).get("world_awareness") or {}
    try:
        return bool(wa.get("world_window_enabled", False))
    except Exception:
        return False


def current_activity(records: list, agent_id: str, upto_round: int) -> dict | None:
    """T354 期②：该 agent 当前进行中的活动（**纯派生**）。

    = 最近一条 `ACTIVITY_STARTED`（本人发起）之后**无对应 `ACTIVITY_COMPLETED`**；
    返回 `{"activity_type":..., "place":...}`（无 ⇒ None）。**不新增真相源、不入 state_hash**。
    """
    act = None
    for rec in records:
        if rec["round"] > upto_round:
            break
        t = rec["type"]
        if t not in ("ACTIVITY_STARTED", "ACTIVITY_COMPLETED"):
            continue
        p = rec.get("payload", {})
        if p.get("agent_id") != agent_id and rec.get("actor") != agent_id:
            continue
        act = ({"activity_type": p.get("activity_type"), "place": p.get("place")}
               if t == "ACTIVITY_STARTED" else None)
    return act


def memory_refs(records: list, agent_id: str, upto_round: int) -> list:
    """从 MEMORY_WRITE 折叠该 Agent 的记忆引用（body 正文在侧存储）。"""
    refs = []
    for rec in records:
        if rec["round"] > upto_round:
            break
        if rec["type"] == "MEMORY_WRITE" and rec.get("payload", {}).get("agent_id") == agent_id:
            p = rec["payload"]
            refs.append({
                "mem_id": p.get("mem_id"), "kind": p.get("kind"),
                "body_ref": p.get("body_ref"), "embed_ref": p.get("embed_ref"),
                "importance": p.get("importance"), "day": p.get("day"), "slot": p.get("slot"),
                "subject": p.get("subject"), "source_event_seq": p.get("source_event_seq"),
            })
    return refs


def perceive(state, agent_id: str, records: list, config: dict | None = None) -> dict:
    """IF-1：返回 WorldView（纯只读）。"""
    if agent_id not in state.agents:
        raise KeyError(f"未知 agent: {agent_id}")
    tcfg = None
    if isinstance(config, dict):
        tcfg = config.get("time_config")
    return {
        "agent_id": agent_id,
        "round": state.round,
        "time": derive_time(state.round, tcfg),
        "status": state.agents[agent_id].get("status"),
        "location": location_of(records, agent_id, state.round),
        "cash": int(state.cash.get(agent_id, 0)),
        "net_worth": state.net_worth(agent_id),
        "visible_events": visible_events(records, agent_id, state.round, config),
        "memory_refs": memory_refs(records, agent_id, state.round),
        # T354 期②：进行中活动（纯派生；off ⇒ None）
        "current_activity": current_activity(records, agent_id, state.round)
        if _load_time_flags(config).get("ongoing_enabled", True) else None,
    }
