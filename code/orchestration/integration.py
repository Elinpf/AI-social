"""engine × life 交接层：IF-1/IF-2 适配、Phase 3.5 注册、端到端装配。

职责（T34 端到端联调，T35 迁入 orchestration 组合根）：
  - `KernelAdapter`：把真内核包装成 `life.ports.KernelPort`（perceive/submit_intent/
    current_round/derive_time），使 life 层在**真内核**上运行（不再用 test-double）。
  - `register_life_hooks`：把 `life.settlement` 的 L1–L7 注入内核 Phase 3.5 注册表。
  - `build_world` / `run_e2e`：从 config/personas.json 载入 N 个 Agent，跑指定回合。

纪律：本模块属 `orchestration` 组合根（唯一同时 import engine 与 life 的层）；
`engine` 核心与 `life` 均不互相 import（import-linter 强制）。
life 层不能直写状态：submit_intent 一律经内核中央裁决器 Arbiter 入本回合缓冲。
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path

from engine.constants import PHASE_DECIDE, PHASE_LIFE
from engine.events import EVENT_TYPES, spec
from engine.kernel import Engine
from engine.runner import default_config, write_log
from engine.state import state_hash

_CODE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = _CODE_DIR / "config"


def _load_social_cfg() -> dict:
    """v2 社会层配额/去重（config/social.json，纳入 engine_version 指纹）。"""
    try:
        return json.loads((CONFIG_DIR / "social.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------- config loaders
def load_places(path: str | Path | None = None) -> dict:
    p = Path(path) if path else (CONFIG_DIR / "places.json")
    raw = json.loads(Path(p).read_text(encoding="utf-8"))
    items = raw["places"] if isinstance(raw, dict) and "places" in raw else raw
    return {it["place_id"]: it for it in items}


def load_life_personas(path: str | Path | None = None) -> dict:
    """返回 {persona_id: Persona}（life.persona.Persona）。"""
    from life.persona import load_personas
    p = Path(path) if path else (CONFIG_DIR / "personas.json")
    return load_personas(p)


# 10 类角色的最小集（00 §2.5），用于规模测试时确定性补足 persona
_ROLE_CYCLE = ["farmer", "craftsman", "cook", "merchant", "healer",
               "teacher", "public_servant", "banker", "artist", "student"]


def expand_personas(base: dict, n: int, *, seed: int = 0) -> dict:
    """若 base 不足 n 个，用确定性 RNG 合成补足到 n（仅供规模测试；不改 life 配置）。"""
    from life.constants import NEED_DIMS
    from life.persona import Persona
    from engine.rng import draw_u64

    out = dict(base)
    have = len(out)
    for i in range(have, n):
        role = _ROLE_CYCLE[i % len(_ROLE_CYCLE)]
        pid = f"PS{i:03d}"
        r = draw_u64(int(seed), "persona", i, 0, 6 + len(NEED_DIMS))
        b5 = {"openness": 30 + r[0] % 61, "conscientiousness": 30 + r[1] % 61,
              "extraversion": 30 + r[2] % 61, "agreeableness": 30 + r[3] % 61,
              "neuroticism": 30 + r[4] % 61}
        vals = {"self_direction": 40 + r[5] % 41, "benevolence": 40 + r[5] % 41,
                "achievement": 40 + r[5] % 41, "security": 40 + r[5] % 41}
        needs = {d: 40 + r[6 + k] % 51 for k, d in enumerate(NEED_DIMS)}
        out[pid] = Persona(
            persona_id=pid, display_name=f"青溪镇·居民{i:03d}", age=20 + i % 45,
            role_id=role, home_place="residence", personality_big5=b5, values=vals,
            skills=[], background=f"角色 {role} 的居民（规模测试合成）。",
            goal_tendencies=[{"kind": "security", "weight": 0.5}], needs_init=needs,
            speech_style={"tone": "plain", "verbosity": "short"},
        )
    return out


# ---------------------------------------------------------------- KernelPort 适配
class KernelAdapter:
    """把真内核 Engine 包装成 life.ports.KernelPort（IF-1 / IF-2）。"""

    VISIBLE_WINDOW_ROUNDS = 2

    def __init__(self, engine: Engine, places: dict):
        self.engine = engine
        self.places = places or {}
        import life.constants as C
        self._C = C
        # PERCEPTION_SCOPE 以引擎 config 为 canonical 真源；life 常量仅作回退
        try:
            from engine.perceive import load_perception_scope
            self._scope_table = load_perception_scope().get("scope", {})
        except Exception:
            self._scope_table = {}
        self._social = _load_social_cfg()
        self._permit_round = None
        self._permits = None  # None=未启用（全许可）；set=本回合允许调 LLM 的 agent

    # ---- 只读辅助 ----
    def current_round(self) -> int:
        return self.engine.state.round

    def derive_time(self, round_no: int | None = None):
        from life.ports import TimeCoord
        return TimeCoord.from_dict(self.engine.derive_time(round_no))

    def _visibility(self, etype: str) -> str:
        if etype in self._scope_table:
            return self._scope_table[etype]
        return self._C.PERCEPTION_SCOPE.get(etype, self._C.DEFAULT_VISIBILITY)

    # ---- IF-1 perceive ----
    def perceive(self, agent_id: str):
        from life.ports import EventView, MemoryRef, WorldView
        st = self.engine.state
        a = st.ensure_agent(agent_id)
        r = st.round
        loc = a.get("location", "residence")
        visible = []
        for ev in self.engine.ledger.records:
            if ev["round"] < r - self.VISIBLE_WINDOW_ROUNDS:
                continue
            p = ev.get("payload", {})
            vis = self._visibility(ev["type"])
            # 定向要约分档（关键契约）：OFFER_CREATED.to==[] -> global（广播）；to 非空 -> private（仅名单可见）
            if ev["type"] == "OFFER_CREATED":
                vis = "global" if not (p.get("to") or []) else "private"
            if vis == "global":
                ok = True
            elif vis == "place_local":
                ok = (p.get("place") == loc)
            elif vis == "private":
                ok = (agent_id in (p.get("from"), p.get("to"))
                      or agent_id in (p.get("to") or [])
                      or p.get("agent_id") == agent_id
                      or p.get("observer") == agent_id or ev.get("actor") == agent_id)
            elif vis == "subject_only":
                ok = (p.get("agent_id") == agent_id or p.get("observer") == agent_id
                      or ev.get("actor") == agent_id)
            elif vis == "participants_only":
                ok = agent_id in (p.get("participants") or []) or agent_id in (
                    p.get("from"), p.get("to"), ev.get("actor"))
            elif vis == "members":
                gid = p.get("group_id")
                ok = gid is not None and agent_id in self._members(gid)
            else:
                ok = (ev.get("actor") == agent_id)
            if not ok:
                continue
            visible.append(EventView(seq=ev["seq"], round=ev["round"], phase=ev["phase"],
                                     actor=ev["actor"], type=ev["type"], payload=p,
                                     place=p.get("place")))
        memrefs = tuple(MemoryRef(
            mem_id=m["mem_id"], kind=m["kind"], body_ref=m["body_ref"], embed_ref=m["embed_ref"],
            importance=int(m["importance"]), day=int(m["day"]), slot=m["slot"],
            subject=m.get("subject"), source_event_seq=m.get("source_event_seq"),
            last_access=int(m.get("last_access", 0)), access_count=int(m.get("access_count", 0)),
        ) for m in a.get("memories", []))
        # 自有库存（仅本人可见）：按 good_id 升序、qty>0
        inv = tuple((g, int(q)) for g, q in sorted(st.inventory.get(agent_id, {}).items())
                    if int(q) > 0)
        from engine import production as _P
        tg = tuple(g for g, _q in inv if _P.is_transferable(g))  # 可转让自有 goods（供 life 选货）
        permits = self._llm_permits(r)
        permit = True if permits is None else (agent_id in permits)  # M4：默认全许可
        # 注：不暴露 p_ref_mu（Leader 口径：不给 agent 世界定价锚；p_ref 仅用于统计/铸币）；
        #     成交价只由 OFFER_ACCEPTED.terms 决定。
        return WorldView(
            agent_id=agent_id, round=r, time=self.derive_time(r),
            status=a.get("status", "alive"), location=loc,
            cash=int(st.cash.get(agent_id, 0)), net_worth=st.net_worth(agent_id),
            visible_events=tuple(visible), memory_refs=memrefs,
            inventory=inv, transferable_goods=tg, llm_permit=permit,
        )

    # ---- 落账辅助（唯一经 Arbiter；D1：入本回合缓冲，P6 落盘）----
    def _emit(self, etype: str, payload: dict, *, phase: int, actor: str) -> int:
        ev = spec(self.engine.state.round, phase, actor, etype, payload)
        seqs = self.engine.emit_specs([ev])
        return seqs[0]

    def _reject(self, agent_id: str, intent, reason: str):
        from life.ports import IntentResult
        self._emit("INTENT_REJECTED", {
            "agent_id": agent_id, "intent_class": intent.intent_class,
            "reason": reason, "requested": intent.payload}, phase=PHASE_LIFE, actor=agent_id)
        return IntentResult(ok=False, reason=reason, event_seqs=())

    # ---- IF-2 submit_intent ----
    def submit_intent(self, agent_id: str, intent):
        from life.ports import ALL_INTENT_CLASSES, IntentResult
        legal = set(ALL_INTENT_CLASSES) | {"INTENT.SOCIAL"}
        if intent.intent_class not in legal:
            return self._reject(agent_id, intent, "unknown_intent_class")
        # v2 经济意图（T133）：统一入 `state.pending_intents`，由 4.1/4.2 hook 消费
        if intent.intent_class.startswith("INTENT.ECON."):
            return self._do_econ(agent_id, intent)
        handler = getattr(self, "_do_" + intent.intent_class.split(".", 1)[1].lower(), None)
        if handler is None:
            return self._reject(agent_id, intent, "unsupported_intent")
        result = handler(agent_id, intent.payload)
        if result is None:
            return self._reject(agent_id, intent, "invalid_payload")
        return result

    def _t(self):
        return self.engine.derive_time(self.engine.state.round)

    def _do_plan(self, agent_id, p):
        from life.ports import IntentResult
        slots = p.get("slots")
        if not slots:
            return None
        for s in slots:
            if s.get("place") not in self.places:
                return None
            if s.get("activity_type") not in self._C.ACTIVITY_TYPES:
                return None
        seq = self._emit("SCHEDULE_PLANNED", {
            "agent_id": agent_id, "horizon": p.get("horizon", "week"),
            "week": p.get("week"), "slots": slots}, phase=PHASE_DECIDE, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    def _do_goal(self, agent_id, p):
        """M7 目标设定（T39/T42）：op="set" -> 每个 goal 一条**扁平** GOAL_SET（08 §1.2-C）。"""
        from life.ports import IntentResult
        if p.get("op") != "set":
            return None
        goals = p.get("goals")
        if not goals:
            return None
        seen = set()
        for g in goals:
            gid = g.get("goal_id")
            if not gid or gid in seen or g.get("kind") is None:
                return None
            seen.add(gid)
        seqs = []
        for g in goals:
            payload = {
                "goal_id": g["goal_id"], "agent_id": agent_id, "kind": g["kind"],
                "layer": g.get("layer"), "priority": g.get("priority"),
                "description_ref": g.get("description_ref", g.get("description")),
                "target_metric": g.get("target_metric"),
                "deadline_week": g.get("deadline_week"),
            }
            seqs.append(self._emit("GOAL_SET", payload, phase=PHASE_DECIDE, actor=agent_id))
        return IntentResult(ok=True, event_seqs=tuple(seqs))

    def _do_move(self, agent_id, p):
        from life.ports import IntentResult
        to_place = p.get("to_place")
        pspec = self.places.get(to_place)
        if pspec is None:
            return None
        t = self._t()
        open_slots = pspec.get("open_slots", ["morning", "afternoon", "evening", "night"])
        if t["slot"] not in open_slots:
            return None
        a = self.engine.state.ensure_agent(agent_id)
        from_place = a.get("location", "residence")
        if from_place == to_place:
            return IntentResult(ok=True, event_seqs=())
        s1 = self._emit("PLACE_MOVE", {"agent_id": agent_id, "from_place": from_place,
                                       "to_place": to_place, "travel_ticks": 1,
                                       "day": t["day"], "slot": t["slot"]},
                        phase=PHASE_LIFE, actor=agent_id)
        s2 = self._emit("PLACE_ARRIVED", {"agent_id": agent_id, "place": to_place,
                                          "day": t["day"], "slot": t["slot"]},
                        phase=PHASE_LIFE, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(s1, s2))

    def _do_activity(self, agent_id, p):
        from life.ports import IntentResult
        atype, place, slot_id = p.get("activity_type"), p.get("place"), p.get("slot_id")
        if atype not in self._C.ACTIVITY_TYPES or place not in self.places or not slot_id:
            return None
        t = self._t()
        seq = self._emit("ACTIVITY_STARTED", {
            "activity_id": p.get("activity_id", f"ACT-{agent_id}-{slot_id}"),
            "agent_id": agent_id, "activity_type": atype, "place": place, "slot_id": slot_id,
            "start_tick": self.engine.state.round,
            "participants": p.get("participants", [agent_id]),
            "day": t["day"], "slot": t["slot"]}, phase=PHASE_LIFE, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    def _do_memory(self, agent_id, p):
        from life.ports import IntentResult
        op = p.get("op")
        st = self.engine.state
        if op == "write":
            mid = p.get("mem_id")
            if not mid or mid in st.memory_index:  # append-only (L5)
                return None
            if not p.get("body_ref") or not p.get("embed_ref"):
                return None
            seq = self._emit("MEMORY_WRITE", {
                "mem_id": mid, "agent_id": agent_id, "kind": p["kind"],
                "importance": int(p["importance"]), "day": int(p["day"]), "slot": p["slot"],
                "subject": p.get("subject"), "body_ref": p["body_ref"],
                "embed_ref": p["embed_ref"], "source_event_seq": p.get("source_event_seq")},
                phase=PHASE_LIFE, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        if op == "retrieve":
            seq = self._emit("MEMORY_RETRIEVE", {
                "agent_id": agent_id, "query_id": p["query_id"], "top_k": p["top_k"],
                "selected_mem_ids": p["selected_mem_ids"], "scores": p["scores"],
                "weights": p["weights"], "tie_order": p["tie_order"]},
                phase=PHASE_DECIDE, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        if op == "reflect":
            seq = self._emit("MEMORY_REFLECT", {
                "agent_id": agent_id, "triggered_by_mem_ids": p["triggered_by_mem_ids"],
                "importance_sum": p["importance_sum"], "produced_mem_id": p["produced_mem_id"]},
                phase=PHASE_LIFE, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        return None

    def _do_observe(self, agent_id, p):
        from life.ports import IntentResult
        target = p.get("target_event_seq")
        if target is None or target not in self.engine.state.event_index:  # L6 anchor
            return None
        t = self._t()
        seq = self._emit("OBSERVATION", {"observer": agent_id, "target_event_seq": target,
                                         "salience": p.get("salience", 0),
                                         "day": t["day"], "slot": t["slot"]},
                         phase=PHASE_LIFE, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    def _do_relation(self, agent_id, p):
        from life.ports import IntentResult
        dim = p.get("dim")
        if dim not in self._C.RELATION_DIMS:
            return None
        lo, hi = self._C.RELATION_RANGE[dim]
        after = max(lo, min(hi, int(p.get("after", 0))))
        seq = self._emit("RELATION_CHANGE", {"from": agent_id, "to": p.get("to"), "dim": dim,
                                             "before": p.get("before", 0), "after": after,
                                             "cause": p.get("cause", ""),
                                             "cause_event_seq": p.get("cause_event_seq")},
                         phase=PHASE_LIFE, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    # ---- v2 经济意图（T133/T135）：OFFER_CREATED/CONTRACT_SIGN 于 phase2 封装事件；其余入队交 4.x ----
    def _do_econ(self, agent_id, intent):
        cls = intent.intent_class
        p = intent.payload or {}
        if cls == "INTENT.ECON.OFFER":
            return self._do_offer(agent_id, p)
        if cls == "INTENT.ECON.CONTRACT_SIGN":
            return self._do_contract_sign(agent_id, p)
        from life.ports import IntentResult
        from engine import intents as _intents
        res = _intents.submit_intent(self.engine, agent_id, {
            "intent_class": cls, "payload": p})
        return IntentResult(ok=bool(res.get("ok")), reason=res.get("reason"),
                            event_seqs=tuple(res.get("event_seqs", ()) or ()))

    def _do_offer(self, agent_id, p):
        """`INTENT.ECON.OFFER` → `OFFER_CREATED/COUNTERED/ACCEPTED/REJECTED`（phase 2/3）。"""
        from life.ports import IntentResult
        r = self.engine.state.round
        act = p.get("act")
        terms = p.get("terms")  # 价格自 terms 原样，不预设
        if act == "create":
            offer_id = p.get("offer_id") or f"O-{r}-{agent_id}"
            seq = self._emit("OFFER_CREATED", {
                "offer_id": offer_id, "from": agent_id, "to": list(p.get("to") or []),
                "kind": p.get("kind"), "terms": terms, "round_no": r},
                phase=PHASE_DECIDE, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        oid = p.get("offer_id")
        if act not in ("counter", "accept", "reject") or not oid:
            return self._reject_reason(agent_id, "INTENT.ECON.OFFER", "invalid_payload", p)
        if act == "counter":
            ev, pay = "OFFER_COUNTERED", {"offer_id": oid, "by": agent_id,
                                          "new_terms": terms, "round_no": r}
        elif act == "accept":
            ev, pay = "OFFER_ACCEPTED", {"offer_id": oid, "by": agent_id, "terms": terms}
        else:
            ev, pay = "OFFER_REJECTED", {"offer_id": oid, "by": agent_id,
                                         "reason": p.get("reason", "")}
        seq = self._emit(ev, pay, phase=PHASE_DECIDE, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    def _do_contract_sign(self, agent_id, p):
        """`INTENT.ECON.CONTRACT_SIGN{offer_id}` → `CONTRACT_CREATED`（phase 2/3）。"""
        from life.ports import IntentResult
        oid = p.get("offer_id")
        if not oid:
            return self._reject_reason(agent_id, "INTENT.ECON.CONTRACT_SIGN", "missing_offer_id", p)
        r = self.engine.state.round
        cid = p.get("contract_id") or f"C-{r}-{oid}"
        seq = self._emit("CONTRACT_CREATED", {
            "contract_id": cid, "offer_id": oid, "parties": p.get("parties"),
            "terms": p.get("terms"), "kind": p.get("kind"), "round_no": r},
            phase=PHASE_DECIDE, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    # ---- M4 分时调度：本回合 LLM 许可集（仅 schedule_enabled 时启用）----
    def _llm_permits(self, round_no: int):
        cfg = (self.engine.config.get("policy", {}) or {}).get("llm_budget", {}) or {}
        if not cfg.get("schedule_enabled", False):
            return None  # 未启用 → 全许可（行为与现状一致）
        if self._permit_round == round_no:
            return self._permits
        st = self.engine.state

        def pri(aid):
            return {"near_death": 3, "warning": 2, "revived": 1}.get(
                st.agents.get(aid, {}).get("status"), 0)
        self._permits = set(self.engine.schedule_llm(sorted(st.agents), round_no, priority=pri))
        self._permit_round = round_no
        return self._permits

    def note_skip(self, dimension, parties) -> int:
        """M6 可列：life 跳过一个判定时调用 → 内核发 `DEGRADE{action:"skip_judgment"}`（ADR-08）。"""
        from engine.scheduling import skip_spec
        seqs = self.engine.emit_specs([skip_spec(self.engine.state.round, dimension, parties)])
        return seqs[0] if seqs else -1

    def should_skip_judgment(self, dimension, parties) -> bool:
        """critical-only 逐判定 gate（T221 消费）：判跳则**内核侧落可列 DEGRADE** 并返回 True。

        life 在 `soft.judge(...)` 前调用；True → 不发起调用。life 不 import engine。
        """
        from engine import scheduling
        if scheduling.should_skip_judgment(dimension, self.engine.llm_budget_level, self.engine.config):
            self.note_skip(dimension, parties)
            return True
        return False

    # ---- v2 社会层：三通道 MSG（T97）----
    def _members(self, group_id: str) -> list:
        return list(self.engine.state.groups.get(group_id, {}).get("members", []))

    def _round_msgs(self, etype: str) -> list:
        r = self.engine.state.round
        return [rec for rec in self.engine.state.event_index.values()
                if rec.get("round") == r and rec.get("type") == etype]

    def _reject_reason(self, agent_id, intent_class, reason, requested):
        from life.ports import IntentResult
        self._emit("INTENT_REJECTED", {
            "agent_id": agent_id, "intent_class": intent_class,
            "reason": reason, "requested": requested}, phase=PHASE_LIFE, actor=agent_id)
        return IntentResult(ok=False, reason=reason, event_seqs=())

    def _body_hash(self, author: str, body: str) -> str:
        from engine.canon import hash_obj
        return hash_obj({"author": author, "body": body})

    def _do_social(self, agent_id, p):
        """v2：把 INTENT.SOCIAL 封装为 MSG_DM(PRIVATE)/MSG_PUBLIC(GLOBAL)/MSG_GROUP(MEMBERS)。

        scope（主口径，T100）：private | place_group | global；兼容 channel 别名
        （dm→private / public→global / group→place_group）。可见性只用 PERCEPTION_SCOPE。
        配额/去重按 config/social.json（v2/02 §1.3）；守 ADR-08（入本回合缓冲）。
        """
        from life.ports import IntentResult
        from engine.constants import PHASE_COMMUNICATE

        st = self.engine.state
        r = st.round
        caps = (self._social or {}).get("caps", {})
        cap_dm = int(caps.get("dm_per_agent_per_round", 3))
        cap_pub_a = int(caps.get("public_per_agent_per_round", 2))
        cap_pub_g = int(caps.get("public_global_per_round", 20))
        cap_grp_a = int(caps.get("group_per_agent_per_group_per_round", 3))
        cap_grp_g = int(caps.get("group_global_per_group_per_round", 20))

        # scope 归一（含 channel 别名）
        scope = p.get("scope")
        if scope is None:
            scope = {"dm": "private", "public": "global", "group": "place_group"}.get(p.get("channel"))
        scope_to_etype = {"private": "MSG_DM", "global": "MSG_PUBLIC", "place_group": "MSG_GROUP"}
        if scope not in scope_to_etype:
            return self._reject_reason(agent_id, "INTENT.SOCIAL", "unknown_channel", p)
        etype = scope_to_etype[scope]

        body = p.get("body") or ""
        body_ref = p.get("body_ref")
        if not body and not body_ref:
            return self._reject_reason(agent_id, "INTENT.SOCIAL", "empty_body", p)
        refs = list(p.get("refs") or [])
        tags = list(p.get("tag_hints") or [])
        t = self._t()

        # 去重：(author, body_hash) 同一时段（slot）内已存在同 channel 消息 -> 折叠 + DROPPED{dup}
        if body:
            bh = self._body_hash(agent_id, body)
            for rec in self._round_msgs(etype):
                pl = rec["payload"]
                author = pl.get("from") or pl.get("author")
                if author == agent_id and pl.get("slot") == t["slot"] \
                        and self._body_hash(author, pl.get("body", "")) == bh:
                    seq = self._emit("DROPPED", {"type": etype, "reason": "dup",
                                                 "author": agent_id, "day": t["day"], "slot": t["slot"]},
                                     phase=PHASE_COMMUNICATE, actor=agent_id)
                    return IntentResult(ok=False, reason="dup", event_seqs=(seq,))

        # 校验 + 配额
        if scope == "private":
            to = p.get("to")
            if not to or to not in st.agents:
                return self._reject_reason(agent_id, "INTENT.SOCIAL", "recipient_not_alive", p)
            if st.agents[to].get("status") in ("dead", "terminated"):
                return self._reject_reason(agent_id, "INTENT.SOCIAL", "recipient_not_alive", p)
            n = sum(1 for rec in self._round_msgs("MSG_DM")
                    if rec["payload"].get("from") == agent_id)
            if n >= cap_dm:
                return self._reject_reason(agent_id, "INTENT.SOCIAL", "quota_agent", p)
            place = st.agents.get(agent_id, {}).get("location", "residence")
            payload = {"msg_id": f"D-{r}-{n}", "from": agent_id, "to": to,
                       "body": body, "body_ref": body_ref, "refs": refs, "tag_hints": tags,
                       "place": place, "day": t["day"], "slot": t["slot"]}
        elif scope == "global":
            n_a = sum(1 for rec in self._round_msgs("MSG_PUBLIC")
                      if rec["payload"].get("author") == agent_id)
            if n_a >= cap_pub_a:
                return self._reject_reason(agent_id, "INTENT.SOCIAL", "quota_agent", p)
            n_g = len(self._round_msgs("MSG_PUBLIC"))
            if n_g >= cap_pub_g:  # 全局超限 -> 确定性截断 + DROPPED{quota}
                seq = self._emit("DROPPED", {"type": "MSG_PUBLIC", "reason": "quota",
                                             "author": agent_id, "day": t["day"], "slot": t["slot"]},
                                 phase=PHASE_COMMUNICATE, actor=agent_id)
                return IntentResult(ok=False, reason="quota_global", event_seqs=(seq,))
            payload = {"msg_id": f"P-{r}-{n_g}", "author": agent_id, "topic": p.get("topic"),
                       "body": body, "body_ref": body_ref, "refs": refs, "tag_hints": tags,
                       "place": None, "scope": "global", "day": t["day"], "slot": t["slot"]}
        else:  # place_group
            gid = p.get("group_id")
            if not gid or gid not in st.groups:
                return self._reject_reason(agent_id, "INTENT.SOCIAL", "not_group_member", p)
            if agent_id not in self._members(gid):
                return self._reject_reason(agent_id, "INTENT.SOCIAL", "not_group_member", p)
            n_a = sum(1 for rec in self._round_msgs("MSG_GROUP")
                      if rec["payload"].get("from") == agent_id
                      and rec["payload"].get("group_id") == gid)
            if n_a >= cap_grp_a:
                return self._reject_reason(agent_id, "INTENT.SOCIAL", "quota_agent", p)
            n_g = sum(1 for rec in self._round_msgs("MSG_GROUP")
                      if rec["payload"].get("group_id") == gid)
            if n_g >= cap_grp_g:
                seq = self._emit("DROPPED", {"type": "MSG_GROUP", "reason": "quota", "group_id": gid,
                                             "author": agent_id, "day": t["day"], "slot": t["slot"]},
                                 phase=PHASE_COMMUNICATE, actor=agent_id)
                return IntentResult(ok=False, reason="quota_global", event_seqs=(seq,))
            place = st.agents.get(agent_id, {}).get("location", "residence")
            payload = {"msg_id": f"G-{gid}-{r}-{n_g}", "group_id": gid, "from": agent_id,
                       "body": body, "body_ref": body_ref, "refs": refs, "tag_hints": tags,
                       "place": place, "day": t["day"], "slot": t["slot"]}

        seq = self._emit(etype, payload, phase=PHASE_COMMUNICATE, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))


# ---------------------------------------------------------------- 装配
def register_life_hooks() -> None:
    """把 life.settlement 的 L1–L7 注入内核 Phase 3.5 注册表。"""
    from life.settlement import register_into
    from engine.hooks import register_phase35_hook
    register_into(register_phase35_hook)


def _load_llm_config() -> dict:
    p = CONFIG_DIR / "llm.json"
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _default_llm(cache_dir: str | None = None, engine=None):
    """构造 life 层 LLM 客户端。

    - 默认＝冻结层 FreezeLLM + **离线 MockProvider**（零网络，测试/门禁安全）；
    - 真 provider 需**显式 opt-in**：`HITT_LLM_PROVIDER=openai_compat` 且端点可用；
      thinking 策略按 purpose/tier 由 `config/llm.json` 集中裁决（纳入 engine_version 指纹）；
    - **密钥只从 env `LLM_API_KEY` 读取，绝不入库/入日志**；
    - **IF-2c 审计桥（T53）**：若 freeze `LLMClient` 支持可选 `audit_sink` 参数，
      则传入回调把 `LLM_CALL/LLM_JUDGMENT/NARRATIVE` 经 `engine.emit_specs` 入本回合缓冲
      （→ P6 唯一 append，遵守 ADR-08；仅首跑触发，replay 不触发）。
    """
    import inspect
    import os
    llm_cfg = _load_llm_config()
    th = llm_cfg.get("thinking", {})
    try:
        from freeze.client import FreezeLLM
        from freeze.config import FreezeConfig, Mode, ThinkingPolicy
        from freeze.llm_client import LLMClient
        from freeze.events import EventLog
        from freeze.providers import MockProvider, OpenAICompatProvider
        from engine import version

        mode = Mode(os.environ.get("FREEZE_MODE", Mode.RUN.value))
        policy = ThinkingPolicy(
            default=bool(th.get("default", False)),
            true_purposes=frozenset(th.get("true_purposes", ["judge", "narrate", "describe"])),
            true_tiers=frozenset(th.get("true_tiers", ["t2"])),
        )
        fcfg = FreezeConfig(
            engine_version=version.compute_fingerprint(),
            mode=mode,
            cache_dir=cache_dir or tempfile.mkdtemp(prefix="hitt_freeze_"),
            thinking_policy=policy,
        )
        provider = MockProvider()
        if os.environ.get("HITT_LLM_PROVIDER") == "openai_compat":
            endpoint = os.environ.get("LLM_ENDPOINT", llm_cfg.get("endpoint", "")).strip()
            model = os.environ.get("LLM_MODEL", llm_cfg.get("model", "")).strip()
            api_key = os.environ.get("LLM_API_KEY", "")  # 仅内存使用，禁止落盘
            if endpoint and model:
                provider = OpenAICompatProvider(endpoint, api_key=api_key, model=model)

        kwargs = {"provider": provider, "event_log": EventLog(time_unit=fcfg.time_unit)}
        # IF-2c 审计桥：仅当 freeze 支持 audit_sink 时接入（向后兼容，inert otherwise）
        if engine is not None and "audit_sink" in inspect.signature(LLMClient.__init__).parameters:
            kwargs["audit_sink"] = _make_audit_sink(engine)
        client = LLMClient(fcfg, **kwargs)
        return FreezeLLM(client)
    except Exception:
        from life.llm import RuleBasedLLM
        return RuleBasedLLM()


def _make_audit_sink(engine):
    """IF-2c：把 freeze 的审计/判定载荷入内核本回合缓冲（P6 唯一 append）。

    **round 以内核权威 `engine.state.round` 为准**（忽略外部传入的默认 0）——否则
    `apply_event` 会把 `state.round` 置 0，污染本回合 `TURN_SEAL.state_hash` 与重放。
    """
    from engine.events import spec

    def _sink(kind: str, payload: dict, round_no: int, phase: int) -> int:
        r = int(engine.state.round)                    # 内核权威当前回合
        ph = int(phase) if phase else 0
        seqs = engine.emit_specs([spec(r, ph, "SYSTEM", kind, payload)])
        return seqs[0] if seqs else -1

    return _sink


def build_world(seed: int, config: dict | None = None, *, n: int | None = None,
                personas_path=None, places_path=None, side_root=None, llm=None,
                endow: int | None = None):
    """装配真内核 + life 层。返回 {engine, adapter, agents, personas, places, side_root}。"""
    from life.agent import LifeLayerAgent
    from life.memory import HashEmbeddingModel, SideStore

    config = config or default_config()
    if endow is not None:
        config.setdefault("genesis", {})["initial_endowment_mu"] = int(endow)
    places = load_places(places_path)
    personas_all = load_life_personas(personas_path)
    if n and n > len(personas_all):
        personas_all = expand_personas(personas_all, n, seed=seed)
    pids = sorted(personas_all)[:n] if n else sorted(personas_all)
    personas = {pid: personas_all[pid] for pid in pids}

    engine = Engine(seed, config)
    register_life_hooks()
    persona_gen = {pid: {"home_place": personas[pid].home_place,
                         "needs_init": personas[pid].needs_init} for pid in pids}
    engine.genesis(persona_gen)

    adapter = KernelAdapter(engine, places)
    if side_root is None:
        side_root = tempfile.mkdtemp(prefix="hitt_side_")
    if llm is None:
        llm = _default_llm(cache_dir=str(Path(side_root) / "freeze_cache"), engine=engine)
    side = SideStore(side_root)
    embed = HashEmbeddingModel()
    agents = [LifeLayerAgent(pid, personas[pid], adapter, llm=llm,
                             side_store=side, embedding=embed, places=places,
                             peers=pids)
              for pid in pids]
    engine.agent_steppers = agents
    return {"engine": engine, "adapter": adapter, "agents": agents,
            "personas": personas, "places": places, "side_root": side_root}


def run_e2e(seed: int = 42, rounds: int = 84, n: int = 3, config: dict | None = None,
            *, out_path=None, side_root=None, personas_path=None, places_path=None,
            llm=None, cleanup_side: bool = True) -> dict:
    """在真内核上跑 N 个 Agent 共 `rounds` 回合，返回端到端证据。"""
    world = build_world(seed, config, n=n, personas_path=personas_path,
                        places_path=places_path, side_root=side_root, llm=llm)
    engine = world["engine"]
    side_root = world["side_root"]
    t0 = time.perf_counter()
    for r in range(int(rounds)):
        engine.run_round(r)
    elapsed = time.perf_counter() - t0

    records = engine.ledger.records
    chain_ok, chain_err = engine.ledger.verify_chain()
    final_hash = state_hash(engine.state)

    from engine.replay import replay_records
    fp = getattr(engine, "fingerprint", None)
    # 第一次重放**校验 turn_seal**（防 T55 类静默污染）；第二次作 parity 伙伴
    r1 = state_hash(replay_records(records, verify=True, verify_seals=True, expected_fingerprint=fp))
    r2 = state_hash(replay_records(records, verify=True, verify_seals=False, expected_fingerprint=fp))

    from engine import conservation
    viols = conservation.check_conservation(engine.state, engine.config)
    unknown = sorted({rec["type"] for rec in records if rec["type"] not in EVENT_TYPES})

    if out_path:
        write_log(records, out_path)
    # log_bytes 与落盘文件口径一致：规范 JSON（键排序、紧凑分隔）+ 每行 '\n'
    from engine.canon import canonical_json
    log_bytes = sum(len(canonical_json(rec).encode("utf-8")) + 1 for rec in records)

    report = {
        "seed": seed, "rounds": int(rounds), "n_agents": len(world["agents"]),
        "events": len(records),
        "event_types": sorted({rec["type"] for rec in records}),
        "unknown_event_types": unknown,
        "chain_ok": chain_ok, "chain_error": chain_err,
        "final_state_hash": final_hash,
        "replay_hash_1": r1, "replay_hash_2": r2,
        "replay_parity": (r1 == r2),
        "seals_ok": True,  # r1 已以 verify_seals=True 校验通过（否则上面会抛错）
        "first_run_equals_replay": (r1 == final_hash),
        "conservation_ok": (len(viols) == 0), "conservation_violations": viols,
        "seconds": round(elapsed, 4),
        "log_bytes": log_bytes,
        "log_path": str(out_path) if out_path else None,
    }
    if cleanup_side and side_root and str(side_root).startswith(tempfile.gettempdir()):
        shutil.rmtree(side_root, ignore_errors=True)
    return report
