"""可见性派生 —— **唯一真源**（08 §3.5 R1/R2）。

动机（T264）：可见性曾有三份内联实现（`engine/perceive.py`、`life/visibility.py`、
`orchestration` 适配器），语义漂移已发生。此处收敛为**单一纯函数**，由三处共同调用：
  - 输入只有 `records` + `scope_table`（来自引擎 `config/perception_scope.json`）+ `default_cls`；
  - **零业务依赖、零 LLM、纯函数**（符合 contracts 包"纯类型/工具"边界）。

`OFFER_CREATED` 分档（T137 固化）：`to==[]`→`global`；`to` 非空→`private`（对 `{from,to}` + `to` 名单）。

⚠️ 待 08 核定（不得自选）：`subject_only`/`private` 是否纳入 `payload.subject`、`members` 是否含
`actor==agent_id` 回退。当前暂采 **engine 现行语义**（不含 subject；members 含 actor 回退），
08 定稿后**只改本文件一处**即可全链路一致。已由 kernel-dev 路由 sim-engine-stats-architect。
"""

from __future__ import annotations

_DEFAULT_INITIAL_LOCATION = "residence"


def location_of(records: list, agent_id: str, upto_round: int,
                initial: str = _DEFAULT_INITIAL_LOCATION) -> str:
    """由 PLACE_MOVE/PLACE_ARRIVED 折叠该 agent 的当前位置（确定性）。"""
    loc = initial
    for rec in records:
        if rec["round"] > upto_round:
            break
        if rec["type"] in ("PLACE_MOVE", "PLACE_ARRIVED"):
            p = rec.get("payload", {})
            if p.get("agent_id") == agent_id:
                loc = p.get("to_place") or p.get("place") or loc
    return loc


def visible(cls: str, agent_id: str, actor: str, p: dict, loc: str,
            group_members: dict | None = None) -> bool:
    """单条事件的可见性谓词（纯函数）。"""
    if cls == "global":
        return True
    if cls == "place_local":
        return p.get("place") == loc
    if cls == "private":
        return (agent_id in (p.get("from"), p.get("to"))
                or agent_id in (p.get("to") or [])
                or p.get("agent_id") == agent_id or p.get("observer") == agent_id
                or actor == agent_id)
    if cls == "subject_only":
        return (agent_id in (p.get("agent_id"), p.get("observer"), p.get("from"))
                or actor == agent_id)
    if cls == "participants_only":
        return (agent_id in (p.get("participants") or [])
                or agent_id in (p.get("from"), p.get("to"), actor))
    if cls == "members":
        gid = p.get("group_id")
        gm = (group_members or {}).get(gid, []) if gid is not None else []
        return (agent_id in gm or agent_id in (p.get("members") or [])
                or actor == agent_id)
    return actor == agent_id


def _group_members(records: list, upto_round: int) -> dict:
    """由 GROUP_CREATED/JOINED/LEFT 折叠 `group_id -> [members]`（确定性，供 members 可见性）。"""
    groups: dict[str, list] = {}
    for rec in records:
        if rec["round"] > upto_round:
            break
        t, p = rec["type"], rec.get("payload", {})
        gid = p.get("group_id")
        if t == "GROUP_CREATED" and gid is not None:
            groups[gid] = sorted(p.get("members", []))
        elif t == "GROUP_JOINED" and gid is not None:
            m = groups.setdefault(gid, [])
            if p.get("agent_id") not in m:
                groups[gid] = sorted(m + [p["agent_id"]])
        elif t == "GROUP_LEFT" and gid is not None and gid in groups:
            groups[gid] = [x for x in groups[gid] if x != p.get("agent_id")]
    return groups


def visible_events(records: list, agent_id: str, upto_round: int, *,
                   scope_table: dict, default_cls: str = "place_local",
                   window_rounds: int | None = None,
                   location: str | None = None) -> list:
    """返回 `agent_id` 在 `upto_round` 可**直接感知**的事件（原始 record，保持账本顺序）。"""
    loc = location if location is not None else location_of(records, agent_id, upto_round)
    gmembers = _group_members(records, upto_round)
    out = []
    for rec in records:
        if rec["round"] > upto_round:
            break
        if window_rounds is not None and rec["round"] < upto_round - window_rounds:
            continue
        p = rec.get("payload", {})
        cls = scope_table.get(rec["type"], default_cls)
        if rec["type"] == "OFFER_CREATED":  # T137：定向要约分档
            cls = "global" if not (p.get("to") or []) else "private"
        if visible(cls, agent_id, rec.get("actor", "SYSTEM"), p, loc, gmembers):
            out.append(rec)
    return out
