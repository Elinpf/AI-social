"""Minimal deterministic kernel TEST-DOUBLE (implements `life.ports.KernelPort`).

NOT the production kernel (that is `engine/`). A self-contained stand-in so the life
layer can be validated independently. It mirrors the real kernel's:
  * append-only ledger + SHA-256 hash chain + turn_seal (v1 §6.1)
  * ADR-08 emit discipline: events go to a per-round pending buffer; P6 COMMIT is
    the sole append point (state is folded incrementally so later hooks see effects)
  * IF-1 perceive / IF-2 submit_intent incl. INTENT_REJECTED (08 §1.2 H)
  * Phase 3.5 L1..L7 from `life.settlement` (08 §2)
  * folding of RELATION_*/GOAL_*/TAG_EMITTED/NORM_* into state (T39)
  * replay(log) = reduce(apply_event, InitialState) (v1 §6.2)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from life import constants as C
from life.ports import (  # noqa: E402
    ALL_INTENT_CLASSES, EventView, Intent, IntentResult, KernelPort, MemoryRef, TimeCoord, WorldView,
)
from life.settlement import PHASE35_HOOKS, Ctx, EventSpec  # noqa: E402
from life.util import canonical_hash  # noqa: E402
from life.visibility import visible_events  # noqa: E402

GENESIS_HASH = "sha256:" + "0" * 64
TIME_UNIT = 1000
VISIBLE_WINDOW_ROUNDS = 2
DEFAULT_ACTIVITY_DURATION = C.TIME_CONFIG["ROUNDS_PER_SLOT"]


class _KernelCtx(Ctx):
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    def derive_time(self, round_no: int) -> dict:
        return C.derive_time(round_no, self.cfg)

    def rng(self, stream_id: str, seq: int, n: int) -> list[int]:
        from life.util import draw
        return draw(self.cfg.get("_seed", 0), stream_id, seq, 0, n)


def initial_state(seed: int) -> dict:
    return {"round": 0, "seed": seed, "agents": {}, "memory_index": {}, "event_index": {},
            "observed": {}, "rejected": [], "relations": {}, "encounters": [], "tags": {},
            "norms": {}, "judgments": {}, "groups": {}, "messages": []}


def _agent(state: dict, aid: str) -> dict:
    return state["agents"].setdefault(aid, {
        "location": "residence", "status": "alive", "schedule": [], "started_slots": [],
        "current_activity": None, "needs": {}, "memories": [], "observed_event_seqs": [],
        "encounters": {}, "goals": {}})


def apply_event(state: dict, ev: dict) -> None:
    t, p = ev["type"], ev["payload"]
    state["event_index"][ev["seq"]] = ev
    if t == "AGENT_BORN":
        a = _agent(state, p["agent_id"])
        a["location"] = p.get("home_place", "residence")
        a["needs"] = dict(p.get("needs_init", {}))
        state["observed"].setdefault(p["agent_id"], set())
    elif t == "SCHEDULE_PLANNED":
        a = _agent(state, p["agent_id"])
        a["schedule"] = list(p["slots"])
        a["started_slots"] = []
    elif t == "ACTIVITY_STARTED":
        a = _agent(state, p["agent_id"])
        a["started_slots"].append(p["slot_id"])
        a["current_activity"] = {"activity_id": p["activity_id"], "activity_type": p["activity_type"],
                                 "place": p["place"], "slot_id": p["slot_id"],
                                 "start_tick": p["start_tick"],
                                 "duration_ticks": p.get("duration_ticks", DEFAULT_ACTIVITY_DURATION)}
    elif t == "ACTIVITY_COMPLETED":
        _agent(state, p["agent_id"])["current_activity"] = None
    elif t == "NEED_UPDATE":
        _agent(state, p["agent_id"])["needs"][p["dim"]] = p["after"]
    elif t == "PLACE_MOVE":
        _agent(state, p["agent_id"])["location"] = p["to_place"]
    elif t == "PLACE_ARRIVED":
        _agent(state, p["agent_id"])["location"] = p["place"]
    elif t == "MEMORY_WRITE":
        a = _agent(state, p["agent_id"])
        ref = {"mem_id": p["mem_id"], "kind": p["kind"], "body_ref": p["body_ref"],
               "embed_ref": p["embed_ref"], "importance": p["importance"], "day": p["day"],
               "slot": p["slot"], "subject": p.get("subject"),
               "source_event_seq": p.get("source_event_seq"), "last_access": ev["round"],
               "access_count": 0}
        a["memories"].append(ref)
        state["memory_index"][p["mem_id"]] = ref
    elif t == "MEMORY_RETRIEVE":
        for mid in p.get("selected_mem_ids", []):
            ref = state["memory_index"].get(mid)
            if ref:
                ref["last_access"] = ev["round"]
                ref["access_count"] += 1
    elif t == "OBSERVATION":
        state["observed"].setdefault(p["observer"], set()).add(p["target_event_seq"])
        _agent(state, p["observer"])["observed_event_seqs"].append(p["target_event_seq"])
    elif t == "RELATION_CHANGE":
        dims = state["relations"].setdefault(p["from"], {}).setdefault(p["to"], {})
        dims[p["dim"]] = p["after"]
    elif t == "RELATION_ENCOUNTER":
        state["encounters"].append({"a": p["a"], "b": p["b"], "place": p["place"],
                                    "day": p["day"], "slot": p["slot"],
                                    "duration_ticks": p.get("duration_ticks", 0)})
        for x, y in ((p["a"], p["b"]), (p["b"], p["a"])):
            enc = _agent(state, x).setdefault("encounters", {})
            enc[y] = int(enc.get(y, 0)) + 1
    elif t == "GOAL_SET":
        a = _agent(state, p["agent_id"])
        a.setdefault("goals", {})[p["goal_id"]] = {
            "goal_id": p["goal_id"], "agent_id": p["agent_id"], "kind": p.get("kind"),
            "layer": p.get("layer"), "priority": p.get("priority", 0.5), "progress": 0.0,
            "status": "active", "target_metric": p.get("target_metric"),
            "description_ref": p.get("description_ref"), "deadline_week": p.get("deadline_week")}
    elif t == "GOAL_PROGRESS":
        g = _agent(state, p["agent_id"]).get("goals", {}).get(p["goal_id"])
        if g:
            g["progress"] = p["after"]
    elif t == "GOAL_ACHIEVED":
        g = _agent(state, p["agent_id"]).get("goals", {}).get(p["goal_id"])
        if g:
            g["status"] = "done"
    elif t == "GOAL_ABANDON":
        g = _agent(state, p["agent_id"]).get("goals", {}).get(p["goal_id"])
        if g:
            g["status"] = "abandoned"
    elif t == "TAG_EMITTED":
        state["tags"][p["tag"]] = int(state["tags"].get(p["tag"], 0)) + 1
    elif t == "NORM_PROPOSED":
        state["norms"][p["norm_id"]] = {"norm_id": p["norm_id"], "rule_ref": p["rule_ref"],
                                        "proposer": p["proposer"], "support_count": p["support_count"],
                                        "threshold": p["threshold"], "status": "proposed",
                                        "adopters": [], "day": p.get("day"), "violations": 0}
    elif t == "NORM_ADOPTED":
        n = state["norms"].setdefault(p["norm_id"], {"norm_id": p["norm_id"]})
        n.update({"status": "adopted", "adopters": p.get("adopters", []),
                  "adopted_day": p.get("adopted_day"), "rule_ref": n.get("rule_ref")})
    elif t == "NORM_VIOLATED":
        n = state["norms"].setdefault(p["norm_id"], {"norm_id": p["norm_id"]})
        n["violations"] = int(n.get("violations", 0)) + 1
    elif t == "INTENT_REJECTED":
        state["rejected"].append({"agent_id": p["agent_id"], "intent_class": p["intent_class"],
                                  "reason": p["reason"]})
    elif t == "LLM_JUDGMENT":
        state.setdefault("judgments", {})[p["judgment_id"]] = p.get("decision")
    elif t == "GROUP_CREATED":
        state.setdefault("groups", {})[p["group_id"]] = list(p.get("members", []))
    elif t in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
        state.setdefault("messages", []).append(
            {"type": t, "from": p.get("from") or p.get("author"), "to": p.get("to"),
             "group_id": p.get("group_id"), "body": p.get("body"), "refs": list(p.get("refs") or [])})
    # NARRATIVE: pure output, identity fold (affects_state=false)


def state_fingerprint(state: dict) -> dict:
    agents = {}
    for aid in sorted(state["agents"]):
        a = state["agents"][aid]
        agents[aid] = {
            "location": a["location"], "status": a["status"],
            "started_slots": sorted(a["started_slots"]),
            "needs": {k: a["needs"][k] for k in sorted(a["needs"])},
            "schedule": sorted(a["schedule"], key=lambda s: s["slot_id"]),
            "current_activity": a["current_activity"],
            "goals": {k: dict(a.get("goals", {})[k]) for k in sorted(a.get("goals", {}))},
            "encounters": {k: a.get("encounters", {})[k] for k in sorted(a.get("encounters", {}))},
            "memories": sorted([{"mem_id": m["mem_id"], "kind": m["kind"],
                                 "importance": m["importance"], "last_access": m["last_access"],
                                 "access_count": m["access_count"]} for m in a["memories"]],
                               key=lambda m: m["mem_id"]),
            "observed": sorted(set(a["observed_event_seqs"])),
        }
    return {"agents": agents, "relations": state["relations"], "encounters": state["encounters"],
            "tags": state["tags"], "norms": state["norms"], "rejected": state["rejected"],
            "judgments": state.get("judgments", {}), "groups": state.get("groups", {}),
            "messages": sorted(state.get("messages", []),
                               key=lambda m: (m["type"], str(m["from"]), str(m["to"]), str(m["body"])))}


class MiniKernel(KernelPort):
    def __init__(self, seed: int = 42, *, places: dict | None = None,
                 config: dict | None = None) -> None:
        self.seed = seed
        self.places = places or {}
        self.cfg = dict(C.TIME_CONFIG)
        self.cfg["_seed"] = seed
        self.ctx = _KernelCtx(self.cfg)
        self.state = initial_state(seed)
        self.ledger: list[dict] = []
        self._pending: list[dict] = []
        self.hooks = dict(PHASE35_HOOKS)
        self.turn_seals: dict[int, str] = {}

    # ---- ledger primitives (IF-3, ADR-08) --------------------------------
    def _emit(self, etype: str, payload: dict, *, phase: int, actor: str) -> int:
        seq = len(self.ledger) + len(self._pending)
        rec = {"seq": seq, "round": self.state["round"], "phase": phase, "actor": actor,
               "type": etype, "payload": payload,
               "mono_ts": self.state["round"] * TIME_UNIT + seq,
               "prev_hash": "PENDING", "hash": "PENDING"}
        apply_event(self.state, rec)          # incremental fold for later hooks
        self._pending.append(rec)
        return seq

    def commit_round(self) -> None:
        for rec in self._pending:
            prev = self.ledger[-1]["hash"] if self.ledger else GENESIS_HASH
            rec["prev_hash"] = prev
            rec["hash"] = "sha256:" + canonical_hash({k: v for k, v in rec.items() if k != "hash"})
            self.ledger.append(rec)
        self._pending = []

    def turn_seal(self, round_no: int) -> str:
        evs = [e for e in self.ledger if e["round"] == round_no]
        seal = "sha256:" + canonical_hash({"round": round_no, "hashes": [e["hash"] for e in evs]})
        self.turn_seals[round_no] = seal
        return seal

    # ---- IF-1 perceive ----------------------------------------------------
    def derive_time(self, round_no: int) -> TimeCoord:
        return TimeCoord.from_dict(self.ctx.derive_time(round_no))

    def current_round(self) -> int:
        return self.state["round"]

    def submit_audit(self, kind: str, payload: dict, *, actor: str = "SYSTEM",
                     phase: int = 35) -> int:
        """IF-2c audit bridge (test-double): emit LLM_JUDGMENT / NARRATIVE locally."""
        return self._emit(kind, payload, phase=phase, actor=actor)

    def perceive(self, agent_id: str) -> WorldView:
        a = _agent(self.state, agent_id)
        r = self.state["round"]
        recs = visible_events(self.ledger, agent_id, r, VISIBLE_WINDOW_ROUNDS,
                              location=a["location"])
        visible = [EventView(seq=e["seq"], round=e["round"], phase=e["phase"], actor=e["actor"],
                             type=e["type"], payload=e["payload"],
                             place=e["payload"].get("place")) for e in recs]
        memrefs = tuple(MemoryRef(
            mem_id=m["mem_id"], kind=m["kind"], body_ref=m["body_ref"], embed_ref=m["embed_ref"],
            importance=m["importance"], day=m["day"], slot=m["slot"], subject=m["subject"],
            source_event_seq=m["source_event_seq"], last_access=m["last_access"],
            access_count=m["access_count"]) for m in a["memories"])
        return WorldView(agent_id=agent_id, round=r, time=self.derive_time(r), status=a["status"],
                         location=a["location"], cash=0, net_worth=0,
                         visible_events=tuple(visible), memory_refs=memrefs)

    # ---- IF-2 submit_intent ----------------------------------------------
    def submit_intent(self, agent_id: str, intent: Intent) -> IntentResult:
        if intent.intent_class not in ALL_INTENT_CLASSES:
            return self._reject(agent_id, intent, "unknown_intent_class")
        handler = getattr(self, "_do_" + intent.intent_class.split(".", 1)[1].lower(), None)
        if handler is None:
            return self._reject(agent_id, intent, "unsupported_intent")
        result = handler(agent_id, intent.payload)
        if result is None:
            return self._reject(agent_id, intent, "invalid_payload")
        return result

    def _reject(self, agent_id: str, intent: Intent, reason: str) -> IntentResult:
        self._emit("INTENT_REJECTED", {"agent_id": agent_id, "intent_class": intent.intent_class,
                                       "reason": reason, "requested": intent.payload},
                   phase=35, actor=agent_id)
        return IntentResult(ok=False, reason=reason, event_seqs=())

    def _do_plan(self, agent_id, p):
        slots = p.get("slots")
        if not slots:
            return None
        for s in slots:
            if s.get("place") not in self.places or s.get("activity_type") not in C.ACTIVITY_TYPES:
                return None
        seq = self._emit("SCHEDULE_PLANNED", {"agent_id": agent_id, "horizon": p.get("horizon", "week"),
                                              "week": p.get("week"), "slots": slots}, phase=2, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    def _do_goal(self, agent_id, p):
        if p.get("op") != "set" or not p.get("goals"):
            return None
        goals = _agent(self.state, agent_id).setdefault("goals", {})
        specs = []
        for g in p["goals"]:
            gid = g.get("goal_id")
            if not gid or gid in goals:
                return None
            # FLAT schema per 08 §1.2-C: one GOAL_SET per goal, top-level goal_id
            specs.append(("GOAL_SET", {"goal_id": gid, "agent_id": agent_id,
                                       "kind": g.get("kind"), "layer": g.get("layer"),
                                       "priority": g.get("priority", 0.5),
                                       "description_ref": g.get("description_ref"),
                                       "target_metric": g.get("target_metric"),
                                       "deadline_week": g.get("deadline_week")}))
        seqs = [self._emit(t, pl, phase=2, actor=agent_id) for t, pl in specs]
        return IntentResult(ok=True, event_seqs=tuple(seqs))

    def _do_move(self, agent_id, p):
        to_place = p.get("to_place")
        spec = self.places.get(to_place)
        if spec is None:
            return None
        t = self.derive_time(self.state["round"])
        if t.slot not in spec.get("open_slots", ["morning", "afternoon", "evening", "night"]):
            return None
        a = _agent(self.state, agent_id)
        if a["location"] == to_place:
            return IntentResult(ok=True, event_seqs=())
        s1 = self._emit("PLACE_MOVE", {"agent_id": agent_id, "from_place": a["location"],
                                       "to_place": to_place, "travel_ticks": 1, "day": t.day,
                                       "slot": t.slot}, phase=35, actor=agent_id)
        s2 = self._emit("PLACE_ARRIVED", {"agent_id": agent_id, "place": to_place, "day": t.day,
                                          "slot": t.slot}, phase=35, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(s1, s2))

    def _do_activity(self, agent_id, p):
        atype, place, slot_id = p.get("activity_type"), p.get("place"), p.get("slot_id")
        if atype not in C.ACTIVITY_TYPES or place not in self.places or not slot_id:
            return None
        t = self.derive_time(self.state["round"])
        seq = self._emit("ACTIVITY_STARTED", {
            "activity_id": p.get("activity_id", f"ACT-{agent_id}-{slot_id}"), "agent_id": agent_id,
            "activity_type": atype, "place": place, "slot_id": slot_id,
            "start_tick": self.state["round"], "participants": p.get("participants", [agent_id]),
            "day": t.day, "slot": t.slot}, phase=35, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    def _do_memory(self, agent_id, p):
        op = p.get("op")
        if op == "write":
            mid = p.get("mem_id")
            if not mid or mid in self.state["memory_index"] or not p.get("body_ref") or not p.get("embed_ref"):
                return None
            seq = self._emit("MEMORY_WRITE", {"mem_id": mid, "agent_id": agent_id, "kind": p["kind"],
                                              "importance": p["importance"], "day": p["day"],
                                              "slot": p["slot"], "subject": p.get("subject"),
                                              "body_ref": p["body_ref"], "embed_ref": p["embed_ref"],
                                              "source_event_seq": p.get("source_event_seq")},
                             phase=35, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        if op == "retrieve":
            seq = self._emit("MEMORY_RETRIEVE", {"agent_id": agent_id, "query_id": p["query_id"],
                                                 "top_k": p["top_k"], "selected_mem_ids": p["selected_mem_ids"],
                                                 "scores": p["scores"], "weights": p["weights"],
                                                 "tie_order": p["tie_order"]}, phase=2, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        if op == "reflect":
            seq = self._emit("MEMORY_REFLECT", {"agent_id": agent_id,
                                                "triggered_by_mem_ids": p["triggered_by_mem_ids"],
                                                "importance_sum": p["importance_sum"],
                                                "produced_mem_id": p["produced_mem_id"]}, phase=35, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        return None

    def _do_observe(self, agent_id, p):
        target = p.get("target_event_seq")
        if target is None or target not in self.state["event_index"]:
            return None
        t = self.derive_time(self.state["round"])
        seq = self._emit("OBSERVATION", {"observer": agent_id, "target_event_seq": target,
                                         "salience": p.get("salience", 0), "day": t.day, "slot": t.slot},
                         phase=35, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    def _do_social(self, agent_id, p):
        scope = p.get("scope")
        body = (p.get("body") or "").strip()
        if not body:
            return None
        refs = list(p.get("refs") or [])
        r = self.state["round"]
        if scope == "private":
            to = p.get("to")
            if to not in self.state["agents"]:
                return None
            seq = self._emit("MSG_DM", {"msg_id": f"D-{r}-{agent_id}-{to}", "from": agent_id,
                                        "to": to, "body": body, "refs": refs,
                                        "visibility": "private"}, phase=2, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        if scope == "global":
            seq = self._emit("MSG_PUBLIC", {"msg_id": f"P-{r}-{agent_id}", "author": agent_id,
                                            "body": body, "refs": refs, "scope": "global"},
                             phase=2, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        if scope == "place_group":
            gid = p.get("group_id")
            members = self.state.setdefault("groups", {}).get(gid)
            if not members or agent_id not in members:
                return None
            seq = self._emit("MSG_GROUP", {"msg_id": f"G-{gid}-{r}-{agent_id}", "group_id": gid,
                                           "from": agent_id, "body": body, "refs": refs},
                             phase=2, actor=agent_id)
            return IntentResult(ok=True, event_seqs=(seq,))
        return None

    def _do_relation(self, agent_id, p):
        dim = p.get("dim")
        if dim not in C.RELATION_DIMS:
            return None
        lo, hi = C.RELATION_RANGE[dim]
        after = max(lo, min(hi, int(p.get("after", 0))))
        seq = self._emit("RELATION_CHANGE", {"from": agent_id, "to": p.get("to"), "dim": dim,
                                             "before": p.get("before", 0), "after": after,
                                             "cause": p.get("cause", ""),
                                             "cause_event_seq": p.get("cause_event_seq")},
                         phase=35, actor=agent_id)
        return IntentResult(ok=True, event_seqs=(seq,))

    # ---- Phase 3.5 (L1..L7) ----------------------------------------------
    def run_phase35(self) -> None:
        # Faithful to the real engine: fold each hook's output *before* the next
        # hook runs (blueprint §2.3, serial folding) so later hooks see earlier
        # hooks' effects (e.g. L7 reads L3's ACTIVITY_COMPLETED).
        for name in ("advance_time", "resolve_schedule", "settle_activities", "apply_needs",
                     "update_relations", "write_memories", "emit_tags"):
            for spec in self.hooks[name](self.state, self.state["round"], self.ctx):
                self._emit(spec.type, spec.payload, phase=spec.phase, actor=spec.actor)

    # ---- round driver -----------------------------------------------------
    def tick(self, agents: dict) -> None:
        for aid in sorted(agents):
            agents[aid].step()
        self.run_phase35()
        self.commit_round()          # ADR-08: sole append point
        self.turn_seal(self.state["round"])
        self.state["round"] += 1

    # ---- replay -----------------------------------------------------------
    @classmethod
    def replay(cls, ledger: list[dict], *, seed: int = 42) -> dict:
        state = initial_state(seed)
        prev = GENESIS_HASH
        last_round = -1
        for ev in ledger:
            assert ev["prev_hash"] == prev, f"hash chain broken at seq {ev['seq']}"
            recomputed = "sha256:" + canonical_hash({k: v for k, v in ev.items() if k != "hash"})
            assert recomputed == ev["hash"], f"bad event hash at seq {ev['seq']}"
            apply_event(state, ev)
            prev = ev["hash"]
            last_round = ev["round"]
        state["round"] = last_round + 1 if last_round >= 0 else 0
        return state
