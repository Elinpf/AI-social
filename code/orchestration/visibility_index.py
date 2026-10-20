"""T264 步骤⑤：`visible_events` 增量索引（组合根构建，端口注入）。

设计（Leader 裁决 = 方案 C）：
  - **纯谓词**在 `contracts.visibility`（唯一真源，无状态）；本模块只做**取候选**的**有状态派生缓存**。
  - **不入 `state_hash`**：从日志派生的**可重建**缓存（replay 应重建它，不依赖它）。
  - 每条候选**最终仍经 `contracts.visibility.visible()` 过滤** → **逐字节不变**（候选=**超集**）。

防"陈旧缓存 = silently wrong"：
  - 候选取**保守超集**（宁可多、不可漏），真相由谓词裁决；
  - `rebuild(records)`（清空重建）/ `sync(records)`（追加尾部）；
  - 位置：`loc_timeline[agent]=[(round,place)]`（有序，O(小)）；
  - 群成员：`group_events` 增量折（按 `upto` as-of，O(群事件)）。
"""

from __future__ import annotations

from contracts.visibility import visible as _visible
from contracts.visibility import world_event_in_window as _wew
from contracts.visibility import WORLD_EVENT_TYPES as _WORLD_TYPES


class VisibilityIndex:
    def __init__(self, scope_table: dict, default_cls: str = "place_local"):
        self.scope_table = scope_table
        self.default_cls = default_cls
        self.records: list = []                 # 已 ingest 账本（顺序=账本序）
        self.by_key: dict = {}                  # (field,value)->list[rec]
        self.by_place: dict = {}                # place->list[rec]
        self.members_cls: list = []             # class==members 记录（少；整体作超集候选）
        self.global_cls: list = []              # class==global 记录（对全体可见）
        self.loc_timeline: dict = {}            # agent->[(round, place)]（有序）
        self.places_seen: dict = {}             # agent->set(place)
        self.group_events: list = []            # (round, gid, op, agent, members)
        self._n = 0

    # ---- 分类（仅用于取候选；最终裁决仍在 contracts.visible）----
    def _class(self, rec: dict) -> str:
        p = rec.get("payload", {})
        if rec["type"] == "OFFER_CREATED":
            return "global" if not (p.get("to") or []) else "private"
        return self.scope_table.get(rec["type"], self.default_cls)

    def _ingest_one(self, rec: dict) -> None:
        self.records.append(rec)
        p = rec.get("payload", {})
        t, actor = rec["type"], rec.get("actor", "SYSTEM")
        if t in ("PLACE_MOVE", "PLACE_ARRIVED"):
            aid = p.get("agent_id")
            place = p.get("to_place") or p.get("place")
            if isinstance(aid, str) and isinstance(place, str):
                self.loc_timeline.setdefault(aid, []).append((rec["round"], place))
                self.places_seen.setdefault(aid, set()).add(place)
        elif t in ("GROUP_CREATED", "GROUP_JOINED", "GROUP_LEFT"):
            op = {"GROUP_CREATED": "c", "GROUP_JOINED": "j", "GROUP_LEFT": "l"}[t]
            self.group_events.append((rec["round"], p.get("group_id"), op, p.get("agent_id"),
                                      tuple(sorted(p.get("members", []))) if t == "GROUP_CREATED" else None))
        cls = self._class(rec)
        if cls == "global":
            self.global_cls.append(rec)
        elif cls == "place_local":
            ph = p.get("place")
            if isinstance(ph, str):
                self.by_place.setdefault(ph, []).append(rec)
        elif cls == "members":
            self.members_cls.append(rec)
        for field in ("agent_id", "observer", "from", "actor"):
            v = actor if field == "actor" else p.get(field)
            if isinstance(v, str):
                self.by_key.setdefault((field, v), []).append(rec)
        for v in (p.get("to") if isinstance(p.get("to"), list) else [p.get("to")]):
            if isinstance(v, str):
                self.by_key.setdefault(("to", v), []).append(rec)
        for v in (p.get("participants") or []):
            if isinstance(v, str):
                self.by_key.setdefault(("participants", v), []).append(rec)
        v = p.get("counterparty")   # T278：participants_only 纳入 counterparty（service 受方可见）
        if isinstance(v, str):
            self.by_key.setdefault(("counterparty", v), []).append(rec)
        self._n += 1

    # ---- 同步 / 重建 ----
    def sync(self, records: list) -> None:
        n = len(records)
        if n < self._n:
            self.rebuild(records)
            return
        for rec in records[self._n:]:
            self._ingest_one(rec)

    def rebuild(self, records: list) -> None:
        self.__init__(self.scope_table, self.default_cls)
        for rec in records:
            self._ingest_one(rec)

    # ---- as-of 派生量 ----
    def _loc_at(self, agent_id: str, upto: int, initial: str = "residence") -> str:
        loc = initial
        for rnd, place in self.loc_timeline.get(agent_id, ()):
            if rnd <= upto:
                loc = place
            else:
                break
        return loc

    def _gm_upto(self, upto: int) -> dict:
        groups: dict = {}
        for rnd, gid, op, agent, members in self.group_events:
            if rnd > upto:
                break
            if gid is None:
                continue
            if op == "c":
                groups[gid] = list(members or [])
            elif op == "j":
                m = groups.setdefault(gid, [])
                if agent not in m:
                    groups[gid] = sorted(m + [agent])
            elif op == "l" and gid in groups:
                groups[gid] = [x for x in groups[gid] if x != agent]
        return groups

    # ---- 查询 ----
    def _candidates(self, agent_id: str) -> list:
        cand = []
        for field in ("agent_id", "observer", "from", "actor", "to", "participants", "counterparty"):
            cand.extend(self.by_key.get((field, agent_id), []))
        cand.extend(self.members_cls)
        cand.extend(self.global_cls)
        places = set(self.places_seen.get(agent_id, set())) | {"residence"}
        for pl in places:
            cand.extend(self.by_place.get(pl, []))
        seen, uniq = set(), []
        for r in sorted(cand, key=lambda r: r["seq"]):
            if r["seq"] not in seen:
                seen.add(r["seq"])
                uniq.append(r)
        return uniq

    def visible(self, agent_id: str, upto_round: int, *,
                window_rounds: int | None = None, location: str | None = None,
                place_local_actor_fallback: bool = False,
                world_event_window: bool = False) -> list:
        loc = location if location is not None else self._loc_at(agent_id, upto_round)
        gmembers = self._gm_upto(upto_round)
        out = []
        for rec in self._candidates(agent_id):
            if rec["round"] > upto_round:
                continue
            if window_rounds is not None and rec["round"] < upto_round - window_rounds:
                continue
            # D8：世界事件按 [start,end) 裁剪（默认关 = 基线行为等价）
            if world_event_window and rec["type"] in _WORLD_TYPES \
                    and not _wew(rec, upto_round):
                continue
            if _visible(self._class(rec), agent_id, rec.get("actor", "SYSTEM"),
                        rec.get("payload", {}), loc, gmembers, place_local_actor_fallback):
                out.append(rec)
        return out
