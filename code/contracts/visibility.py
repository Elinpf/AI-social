"""可见性派生 —— **唯一真源**（**契约归属：IF-1** 的可执行语义；08 §3.5 R1/R2）。

动机（T264）：可见性曾有三份内联实现（`engine/perceive.py`、`life/visibility.py`、
`orchestration` 适配器），语义漂移已发生。此处收敛为**单一纯函数**，由三处共同调用：
  - 输入只有 `records` + `scope_table`（来自引擎 `config/perception_scope.json`）+ `default_cls`；
  - **零业务依赖、零 LLM、纯函数**（符合 contracts 包"纯类型/工具"边界）。

`OFFER_CREATED` 分档（T137 固化）：`to==[]`→`global`；`to` 非空→`private`（对 `{from,to}` + `to` 名单）。

⚠️ 08 已定稿（T266，`v2/refs/visibility-semantics-08.md` §8–§10）：
  - D2：`subject_only`/`private` **不含** `payload.subject`；D3：`members` **含** `actor==agent_id` 回退。
  - G3：`subject_only` 的 `from` 子句**从未生效（dead，n20_week 命中 0）** → 已删（等价简化）。
  - G1：`place_local` 增 `actor==agent_id` 回退，开关 `place_local_actor_fallback`（默认 `false`=行为不变）。
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
            group_members: dict | None = None,
            place_local_actor_fallback: bool = False) -> bool:
    """单条事件的可见性谓词（纯函数）。

    `place_local_actor_fallback`（G1，默认 False）：为 True 时 `place_local` 增 `actor==agent_id`
    回退（`place` 未知/不等但 actor 本人 → 可见）；开关进 `engine_version` 指纹。
    """
    if cls == "global":
        return True
    if cls == "place_local":
        return p.get("place") == loc or (place_local_actor_fallback and actor == agent_id)
    if cls == "private":
        return (agent_id in (p.get("from"), p.get("to"))
                or agent_id in (p.get("to") or [])
                or p.get("agent_id") == agent_id or p.get("observer") == agent_id
                or actor == agent_id)
    if cls == "subject_only":
        # G3：删去 dead 的 `from` 子句（08 §9）
        return (agent_id in (p.get("agent_id"), p.get("observer"))
                or actor == agent_id)
    if cls == "participants_only":
        return (agent_id in (p.get("participants") or [])
                or agent_id in (p.get("from"), p.get("to"), actor)
                # T278：一等当事人字段 `counterparty`（SERVICE_DELIVERED 受方需可见；08 §1.2 V）
                or (p.get("counterparty") is not None and agent_id == p.get("counterparty")))
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
                   location: str | None = None,
                   place_local_actor_fallback: bool = False) -> list:
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
        if visible(cls, agent_id, rec.get("actor", "SYSTEM"), p, loc, gmembers,
                   place_local_actor_fallback):
            out.append(rec)
    return out
