"""Phase 3.5 `LIFE` settlement hooks — L1..L7 (08 §2.2/§2.3).

Contract (agreed with kernel-dev): a hook is a *pure* function

    fn(state, round_no, ctx) -> list[EventSpec]

It reads the derived state and returns the events the kernel should fold. Hooks
NEVER carry a money delta — any monetary consequence is attached as a
`resource_intents` entry for the 4.1–4.8 arbitration phase (rule L-2 / P7).

`state` is a plain, documented mapping (see `LifeState`). The canonical writer of
that state is the kernel's `apply_event`; hooks only *read* it. Visibility is
computed by `life.visibility.visible_events` (never by an LLM).

L1 advance_time · L2 resolve_schedule · L3 settle_activities · L4 apply_needs(+goals)
L5 update_relations · L6 write_memories · L7 emit_tags(+norms)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from . import constants as C
from . import goals as G
from . import relations as R
from .util import clamp

PHASE_LIFE = C.PHASE_LIFE
ENC_DURATION = 3                  # D_enc: co-presence duration that counts as an encounter


class Ctx(Protocol):
    def derive_time(self, round_no: int) -> dict: ...
    def rng(self, stream_id: str, seq: int, n: int) -> list[int]: ...


@dataclass(frozen=True)
class EventSpec:
    type: str
    payload: dict
    phase: int = PHASE_LIFE
    actor: str = "SYSTEM"


class LifeState:
    """Duck-typed view over the kernel state mapping (read-only for hooks)."""

    def __init__(self, state: dict, kernel=None) -> None:
        self.s = state
        self.kernel = kernel  # T319: 内核只读端口（提供 round_events）；缺省则回退全扫

    @property
    def round(self) -> int:
        return int(self.s.get("round", 0))

    def agents(self) -> dict[str, dict]:
        return self.s.setdefault("agents", {})

    def agent_ids(self) -> list[str]:
        return sorted(self.agents().keys())

    def relations(self) -> dict:
        return self.s.get("relations", {}) or {}

    def goals(self, aid: str) -> dict:
        g = self.agents().get(aid, {}).get("goals", {})
        if isinstance(g, list):  # tolerate list form
            return {x.get("goal_id"): x for x in g}
        return g

    def tags(self) -> dict:
        return self.s.get("tags", {}) or {}

    def norms(self) -> dict:
        return self.s.get("norms", {}) or {}

    def events_this_round(self, round_no: int, etype: str | None = None, kernel=None) -> list:
        # T319: 走内核只读端口（派生累加器，去全扫）；无端口（如 mini 测试内核）时回退全扫。
        fn = getattr(kernel if kernel is not None else self.kernel, "round_events", None)
        if fn is not None:
            return fn(round_no, (etype,) if etype else None)
        out = []
        for rec in self.s.get("event_index", {}).values():
            if rec.get("round") != round_no:
                continue
            if etype is None or rec.get("type") == etype:
                out.append(rec)
        out.sort(key=lambda r: r.get("seq", 0))
        return out


def _time(ctx: Ctx, round_no: int) -> dict:
    return ctx.derive_time(round_no)


# ---- relation helpers --------------------------------------------------------
def _rel_value(state: dict, frm: str, to: str) -> dict:
    return (state.get("relations", {}) or {}).get(frm, {}).get(to, {})


def _relation_specs(state: dict, frm: str, to: str, cause: str, *, amount: int = 0,
                    duration: int = 0) -> list[EventSpec]:
    rel = _rel_value(state, frm, to)
    delta = R.rel_delta(cause, current=rel, amount=amount, duration=duration)
    specs: list[EventSpec] = []
    for dim in sorted(delta):
        lo, hi = C.RELATION_RANGE[dim]
        before = int(rel.get(dim, 0))
        after = clamp(before + int(delta[dim]), lo, hi)
        if after == before:
            continue
        specs.append(EventSpec("RELATION_CHANGE",
                               {"from": frm, "to": to, "dim": dim, "before": before,
                                "after": after, "cause": cause, "cause_event_seq": None},
                               phase=PHASE_LIFE, actor=frm))
    return specs


# ---- cross-hook completion detection (L3 only) ------------------------------
# L3 (settle_activities) runs BEFORE its own ACTIVITY_COMPLETED is folded, so it
# detects due completions from `current_activity`. (L4/L7 run AFTER L3's fold, so
# they must read the same-round ACTIVITY_COMPLETED *events* instead — L3 clears
# `current_activity`.)
def _due_completions(state: dict, round_no: int) -> list[dict]:
    st = LifeState(state)
    out: list[dict] = []
    for aid in st.agent_ids():
        cur = st.agents()[aid].get("current_activity")
        if not cur:
            continue
        dur = int(cur.get("duration_ticks", C.TIME_CONFIG["ROUNDS_PER_SLOT"]))
        if round_no - int(cur["start_tick"]) >= dur:
            out.append({"agent_id": aid, "activity_type": cur.get("activity_type"),
                        "place": cur.get("place"), "activity_id": cur.get("activity_id"),
                        "duration_ticks": dur})
    return out


# ---- L1 advance_time ---------------------------------------------------------
def advance_time(state: dict, round_no: int, ctx: Ctx) -> list[EventSpec]:
    t = _time(ctx, round_no)
    rpd = C.TIME_CONFIG["ROUNDS_PER_SLOT"] * len(C.TIME_CONFIG["SLOTS_PER_DAY"])
    events: list[EventSpec] = []
    if round_no % rpd == 0:
        events.append(EventSpec("TIME_MARK", {
            "round": round_no, "week": t["week"], "day": t["day"],
            "slot": t["slot"], "day_type": t["day_type"]}))
    return events


# ---- L2 resolve_schedule -----------------------------------------------------
def _start_event(aid: str, slot: dict, round_no: int, t: dict) -> EventSpec:
    """Build an ACTIVITY_STARTED spec for a due slot (shared by L2 and L3)."""
    payload = {
        "activity_id": f"ACT-{aid}-{slot['slot_id']}", "agent_id": aid,
        "activity_type": slot["activity_type"], "place": slot["place"],
        "slot_id": slot["slot_id"], "start_tick": round_no,
        "participants": list(slot.get("participants") or [aid]),
        "day": t["day"], "slot": t["slot"], "day_type": t["day_type"],
    }
    tpl = slot.get("template_id") or slot.get("template")
    if tpl:
        payload["template"] = tpl
    return EventSpec("ACTIVITY_STARTED", payload, actor=aid)


def _next_due_slot(a: dict, round_no: int) -> dict | None:
    started = set(a.get("started_slots", []))
    due = [s for s in a.get("schedule", [])
           if s["slot_id"] not in started and int(s.get("planned_tick", -1)) <= round_no]
    if not due:
        return None
    return min(due, key=lambda s: (int(s.get("planned_tick", 0)), s["slot_id"]))


def _start_specs(aid: str, slot: dict, round_no: int, t: dict) -> list[EventSpec]:
    """ACTIVITY_STARTED (+ GROUP_CREATED for a multi-party template). Used by L2 & L3
    so the place-group is materialised regardless of which path starts the activity."""
    out = [_start_event(aid, slot, round_no, t)]
    parts = sorted({p for p in (slot.get("participants") or [aid]) if p})
    from .policy import social_enabled
    if social_enabled() and len(parts) >= 3 and (slot.get("template_id") or slot.get("template")):
        out.append(EventSpec("GROUP_CREATED", {
            "group_id": f"place:{slot['place']}", "members": parts,
            "created_round": round_no, "day": t["day"], "slot": t["slot"]}, actor="SYSTEM"))
    return out


def resolve_schedule(state: dict, round_no: int, ctx: Ctx) -> list[EventSpec]:
    t = _time(ctx, round_no)
    st = LifeState(state)
    events: list[EventSpec] = []
    for aid in st.agent_ids():
        a = st.agents()[aid]
        if a.get("current_activity"):
            continue
        slot = _next_due_slot(a, round_no)
        if slot is None:
            continue
        events += _start_specs(aid, slot, round_no, t)
    return events


# ---- L3 settle_activities ----------------------------------------------------
# ---- 活动模板库接入（T45 / 12-event-lineage §4）：模板即数据，确定性结算 --------
_TPL_CACHE: dict = {}


def _templates() -> dict:
    if "tbl" not in _TPL_CACHE:
        from .templates import load_activity_templates
        _TPL_CACHE["tbl"] = load_activity_templates()
    return _TPL_CACHE["tbl"]


def _started_record(state: dict, activity_id: str) -> dict | None:
    for rec in state.get("event_index", {}).values():
        if rec.get("type") == "ACTIVITY_STARTED":
            if (rec.get("payload") or {}).get("activity_id") == activity_id:
                return rec
    return None


def _skill_level(state: dict, aid: str, skill_id: str) -> int:
    lv = 0
    for rec in sorted(state.get("event_index", {}).values(), key=lambda r: r.get("seq", 0)):
        if rec.get("type") != "SKILL_LEVEL_UP":
            continue
        p = rec.get("payload") or {}
        if p.get("agent_id") == aid and (skill_id in ("*", None) or p.get("skill_id") == skill_id):
            lv = int(p.get("level_after", lv))
    return lv


def _contest_specs(state: dict, round_no: int, t: dict, cs: dict,
                   parts: list[str], tid: str) -> list[EventSpec]:
    """确定性对抗/评分结算（17/12 §3，LLM 不当裁判）。"""
    out: list[EventSpec] = []
    rule = str(cs.get("rule_ref", "score"))
    if rule in ("power", "training"):
        cid = f"CF-{tid}-{round_no}-" + "-".join(parts)
        out.append(EventSpec("CONFLICT_STARTED", {
            "conflict_id": cid, "parties": list(parts), "stakes": rule, "rule_ref": rule,
            "day": t["day"], "slot": t["slot"], "round": round_no}, actor="SYSTEM"))
        power = {a: int(state.get("cash", {}).get(a, 0)) for a in parts}
        winner = min(parts, key=lambda a: (-power[a], a)) if parts else None
        out.append(EventSpec("CONFLICT_RESOLVED", {
            "conflict_id": cid, "winner": winner, "parties": list(parts), "rule_ref": rule,
            "power_breakdown": power, "day": t["day"], "slot": t["slot"]}, actor="SYSTEM"))
    else:
        cid = f"SC-{tid}-{round_no}"
        scores = {a: (_skill_level(state, a, "general") or 1) for a in parts}
        for a in sorted(parts):
            out.append(EventSpec("SCORE_POSTED", {
                "contest_id": cid, "subject": a, "attrs": {"skill": scores[a]},
                "score": scores[a], "day": t["day"], "slot": t["slot"]}, actor="SYSTEM"))
        ranking = sorted(parts, key=lambda a: (-scores[a], a))
        out.append(EventSpec("RANKING_EMITTED", {
            "contest_id": cid,
            "ranking": [{"subject": a, "score": scores[a], "rank": i + 1}
                        for i, a in enumerate(ranking)],
            "day": t["day"], "slot": t["slot"]}, actor="SYSTEM"))
    return out


def _template_settlement(state: dict, round_no: int, t: dict,
                         started_rec: dict, activity_type: str):
    """按模板 deterministic_settlement 产出确定性事件 + 货币 resource_intents（L-2）。"""
    from .templates import role_agents, normalized_effects, money_intents, contest_spec
    sp = started_rec.get("payload") or {}
    tid = sp.get("template") or sp.get("template_id")
    tpl = _templates().get(tid)
    if tpl is None:
        return [], []
    parts = list(sp.get("participants") or [sp.get("agent_id")])
    parts = sorted({p for p in parts if p})
    roles = role_agents(tpl, parts)

    def _agent(tok: str):
        if tok in roles:
            return roles[tok]
        if tok in parts:
            return tok
        return parts[0] if parts else None

    events: list[EventSpec] = []
    for e in normalized_effects(tpl):
        k = e["kind"]
        if k == "skill":
            aid = _agent(e.get("target", "self"))
            if not aid:
                continue
            skill_id = e.get("skill_id") or "general"
            if skill_id == "*":
                skill_id = "general"
            before = _skill_level(state, aid, skill_id) or 1
            after = min(5, before + int(e.get("delta_levels", 1)))
            emits = e.get("emit") or ["SKILL_LEVEL_UP"]
            if "SKILL_PRACTICE" in emits:
                events.append(EventSpec("SKILL_PRACTICE", {
                    "agent_id": aid, "skill_id": skill_id, "skill_before": before,
                    "day": t["day"], "slot": t["slot"]}, actor=aid))
            if "SKILL_OUTPUT" in emits:
                events.append(EventSpec("SKILL_OUTPUT", {
                    "agent_id": aid, "skill_id": skill_id,
                    "output_ref": f"side://skill/{aid}/{skill_id}", "quality": after,
                    "day": t["day"], "slot": t["slot"]}, actor=aid))
            if "SKILL_LEVEL_UP" in emits and after != before:
                events.append(EventSpec("SKILL_LEVEL_UP", {
                    "agent_id": aid, "skill_id": skill_id, "level_before": before,
                    "level_after": after, "cause": f"activity:{tid}",
                    "day": t["day"], "slot": t["slot"]}, actor=aid))
        elif k == "need":
            aid = _agent(e.get("who", "self"))
            if not aid:
                continue
            before = int(state.get("agents", {}).get(aid, {}).get("needs", {}).get(e["dim"], 50))
            after = clamp(before + int(e.get("delta", 0)), C.NEED_MIN, C.NEED_MAX)
            if after != before:
                events.append(EventSpec("NEED_UPDATE", {
                    "agent_id": aid, "dim": e["dim"], "before": before, "after": after,
                    "cause": f"activity:{tid}", "day": t["day"], "slot": t["slot"]}, actor=aid))
        elif k == "relation":
            frm, to = _agent(e.get("from", "self")), _agent(e.get("to", "self"))
            if not frm or not to or frm == to:
                continue
            dim = e["dim"]
            lo, hi = C.RELATION_RANGE[dim]
            rel = (state.get("relations", {}) or {}).get(frm, {}).get(to, {})
            before = int(rel.get(dim, 0))
            after = clamp(before + int(e.get("delta", 0)), lo, hi)
            if after != before:
                events.append(EventSpec("RELATION_CHANGE", {
                    "from": frm, "to": to, "dim": dim, "before": before, "after": after,
                    "cause": f"activity:{tid}", "cause_event_seq": None}, actor=frm))
        elif k == "state":
            aid = _agent(e.get("who", "self"))
            if not aid:
                continue
            cur = state.get("agents", {}).get(aid, {}).get("status", "alive")
            events.append(EventSpec("STATE_CHANGE", {
                "agent_id": aid, "from": cur, "to": e.get("to"), "cause": e.get("cause", "")},
                actor=aid))
        elif k == "role":
            aid = _agent(e.get("who", "self"))
            if aid:
                events.append(EventSpec("ROLE_CHANGE", {
                    "agent_id": aid, "from_role": None, "to_role": None,
                    "cause": e.get("cause", ""), "day": t["day"]}, actor=aid))
        # money → resource_intents（下方）

    cs = contest_spec(tpl)
    if cs:
        events += _contest_specs(state, round_no, t, cs, parts, tid)
    events += _m6_specs(tid, parts, state, round_no, t)
    return events, money_intents(tpl, roles)


# ---- M6 dialogue / negotiation (T56) -----------------------------------------
def _m6_specs(tid: str, parts: list, state: dict, round_no: int, t: dict) -> list[EventSpec]:
    """Deterministic relation nudge + `OFFER_*` state machine for social templates.

    T98: dialogue (`MSG_*`) is now generated in the **decision phase**
    (`agent._communicate` via `INTENT.SOCIAL`); the hardcoded template bodies are
    removed here. Only the deterministic consequences stay: a `chat` affinity nudge
    and the `OFFER_*` state machine (T14 §3.3).
    """
    if len(parts) < 2:
        return []
    frm, to = parts[0], parts[1]
    out: list[EventSpec] = []
    if tid in ("whisper", "ice_break", "gift", "rel_maintain", "rel_accept"):
        # a chat nudges affinity deterministically -> makes E2/E6/E18 thresholds reachable
        out += _relation_specs(state, frm, to, "chat", duration=10)
        out += _relation_specs(state, to, frm, "chat", duration=10)
    if tid == "polite_reject":
        oid = f"O-{round_no}-{frm}-{to}"
        out.append(EventSpec("OFFER_CREATED", {"offer_id": oid, "from": frm, "to": [to],
                                               "kind": "trade", "terms": {"amount_mu": 100},
                                               "round_no": 0}, actor=frm))
        out.append(EventSpec("OFFER_REJECTED", {"offer_id": oid, "by": to, "reason": "polite"},
                             actor=to))
    elif tid == "counter_propose":
        oid = f"O-{round_no}-{frm}-{to}"
        out.append(EventSpec("OFFER_CREATED", {"offer_id": oid, "from": frm, "to": [to],
                                               "kind": "trade", "terms": {"amount_mu": 100},
                                               "round_no": 0}, actor=frm))
        out.append(EventSpec("OFFER_COUNTERED", {"offer_id": oid, "by": to,
                                                 "new_terms": {"amount_mu": 120}, "round_no": 1},
                             actor=to))
    return out


def settle_activities(state: dict, round_no: int, ctx: Ctx) -> list[EventSpec]:
    t = _time(ctx, round_no)
    st = LifeState(state)
    events: list[EventSpec] = []
    for c in _due_completions(state, round_no):
        aid = c["agent_id"]
        started = _started_record(state, c["activity_id"])
        tid = None
        parts = [aid]
        tpl_events: list[EventSpec] = []
        intents: list[dict] = []
        if started is not None:
            sp = started.get("payload") or {}
            tid = sp.get("template") or sp.get("template_id")
            parts = list(sp.get("participants") or [aid])
            if tid:
                tpl_events, intents = _template_settlement(state, round_no, t, started,
                                                           c["activity_type"])
        payload = {
            "activity_id": c["activity_id"], "agent_id": aid, "activity_type": c["activity_type"],
            "place": c["place"], "outcome": "done", "duration_ticks": c["duration_ticks"],
            "resource_intents": intents, "day": t["day"], "slot": t["slot"]}
        if tid:
            payload["template"] = tid
            payload["participants"] = parts
        events.append(EventSpec("ACTIVITY_COMPLETED", payload, actor=aid))
        events += tpl_events
        if not tid:  # 模板活动用模板 need 效果；非模板沿用既有满足度
            sat = C.ACTIVITY_SATISFACTION.get(c["activity_type"], {})
            needs = st.agents()[aid].get("needs", {})
            for dim in sorted(sat):
                before = int(needs.get(dim, 50))
                after = clamp(before + int(sat[dim]), C.NEED_MIN, C.NEED_MAX)
                if after != before:
                    events.append(EventSpec("NEED_UPDATE", {
                        "agent_id": aid, "dim": dim, "before": before, "after": after,
                        "cause": f"activity:{c['activity_type']}",
                        "day": t["day"], "slot": t["slot"]}, actor=aid))
        # chain the next due slot in the SAME round this one completes, so a week
        # executes all 28 slots within 84 rounds without cumulative drift (L2 alone
        # would skip a busy agent for one round per activity).
        nxt = _next_due_slot(st.agents()[aid], round_no)
        if nxt is not None:
            events += _start_specs(aid, nxt, round_no, t)
    return events


# ---- L4 apply_needs (+ deterministic goal progress) -------------------------
def apply_needs(state: dict, round_no: int, ctx: Ctx) -> list[EventSpec]:
    rps = C.TIME_CONFIG["ROUNDS_PER_SLOT"]
    t = _time(ctx, round_no)
    st = LifeState(state)
    events: list[EventSpec] = []
    # (a) natural decay at slot boundaries (D-11)
    if round_no % rps == 0:
        for aid in st.agent_ids():
            needs = st.agents()[aid].get("needs", {})
            for dim in sorted(C.NEED_DECAY):
                before = int(needs.get(dim, 50))
                after = clamp(before - int(C.NEED_DECAY[dim]), C.NEED_MIN, C.NEED_MAX)
                if after != before:
                    events.append(EventSpec("NEED_UPDATE", {
                        "agent_id": aid, "dim": dim, "before": before, "after": after,
                        "cause": "decay", "day": t["day"], "slot": t["slot"]}, actor=aid))
    # (b) goal progress from activities completed this round (deterministic, 08 §1.2 C).
    #     Read the SAME-ROUND ACTIVITY_COMPLETED events (already folded by serial L3),
    #     not `current_activity` (L3 clears it).
    done_by_agent: dict[str, list[str]] = {}
    for rec in st.events_this_round(round_no, "ACTIVITY_COMPLETED", kernel=ctx):
        done_by_agent.setdefault(rec["payload"]["agent_id"], []).append(rec["payload"]["activity_type"])
    for aid in st.agent_ids():
        acted = sorted(set(done_by_agent.get(aid, [])))
        if not acted:
            continue
        goals = st.goals(aid)
        for gid in sorted(goals):
            goal = goals[gid]
            if goal.get("status", "active") != "active":
                continue
            old = float(goal.get("progress", 0.0))
            new = old
            for atype in acted:
                new = G.advance(G.Goal(goal_id=gid, agent_id=aid, kind=goal.get("kind", "security"),
                                       layer=goal.get("layer", "growth"), progress=new), atype)
            if new > old:
                events.append(EventSpec("GOAL_PROGRESS", {
                    "goal_id": gid, "agent_id": aid, "before": round(old, 6), "after": round(new, 6),
                    "day": t["day"], "slot": t["slot"]}, actor=aid))
                if G.is_achieved(new) and not G.is_achieved(old):
                    events.append(EventSpec("GOAL_ACHIEVED", {
                        "goal_id": gid, "agent_id": aid, "reward_intents": [],
                        "day": t["day"], "slot": t["slot"]}, actor=aid))
    # (c) deterministic goal abandon — `stalled` hook (08 §1.2 C; T231).
    #     At the last round of a week (REVIEW boundary): an `active` goal whose
    #     progress delta over THIS week is 0 is abandoned. The delta is derived
    #     faithfully from the week's own `GOAL_PROGRESS` events (goals are re-seeded
    #     to progress=0 at weekly GOAL_SET, and L4 only ever emits GOAL_PROGRESS when
    #     progress actually increased) → no fabricated events; a stall-free week
    #     yields 0 events (allowed). `deadline`/`voluntary` reasons stay defined in
    #     08 §1.2 C but are not enabled here. Effect: only removes stalled goals,
    #     deterministic and replayable; no other decision path is touched.
    WEEK_ROUNDS = (C.TIME_CONFIG["DAYS_PER_WEEK"] * len(C.TIME_CONFIG["SLOTS_PER_DAY"])
                   * C.TIME_CONFIG["ROUNDS_PER_SLOT"])
    if round_no % WEEK_ROUNDS == WEEK_ROUNDS - 1:
        week_start = (round_no // WEEK_ROUNDS) * WEEK_ROUNDS
        progressed: set = set()
        for rec in state.get("event_index", {}).values():
            if rec.get("type") != "GOAL_PROGRESS":
                continue
            rr = int(rec.get("round", -1))
            if not (week_start <= rr <= round_no):
                continue
            rp = rec.get("payload") or {}
            progressed.add((rp.get("agent_id"), rp.get("goal_id")))
        for aid in st.agent_ids():
            goals = st.goals(aid)
            for gid in sorted(goals):
                goal = goals[gid]
                if goal.get("status", "active") != "active":
                    continue
                if (aid, gid) in progressed:      # 本周有推进 → 不停滞
                    continue
                events.append(EventSpec("GOAL_ABANDON", {
                    "goal_id": gid, "agent_id": aid, "reason": "stalled",
                    "progress_at_abandon": float(goal.get("progress", 0.0)),
                    "week": round_no // WEEK_ROUNDS,
                    "day": t["day"], "slot": t["slot"]}, actor=aid))
    return events


# ---- L5 update_relations -----------------------------------------------------
def update_relations(state: dict, round_no: int, ctx: Ctx) -> list[EventSpec]:
    t = _time(ctx, round_no)
    st = LifeState(state)
    events: list[EventSpec] = []
    by_place: dict[str, list[str]] = {}
    for aid in st.agent_ids():
        by_place.setdefault(st.agents()[aid].get("location", "residence"), []).append(aid)
    seen_pairs: set[tuple[str, str]] = set()
    for place in sorted(by_place):
        occ = sorted(by_place[place])
        for i in range(len(occ)):
            for j in range(i + 1, len(occ)):
                a, b = occ[i], occ[j]
                if (a, b) in seen_pairs:
                    continue
                seen_pairs.add((a, b))
                ea = st.agents()[a].get("encounters", {})
                first = int(ea.get(b, 0)) == 0
                if first:
                    events.append(EventSpec("RELATION_ENCOUNTER", {
                        "a": a, "b": b, "place": place, "day": t["day"], "slot": t["slot"],
                        "duration_ticks": ENC_DURATION}, actor=a))
                    events += _relation_specs(state, a, b, "copresence", duration=ENC_DURATION)
                    events += _relation_specs(state, b, a, "copresence", duration=ENC_DURATION)
                # familiarity grows with every co-present round (monotone, capped)
                events += _relation_specs(state, a, b, "encounter")
                events += _relation_specs(state, b, a, "encounter")
    # co-located trades / rescues — read the PREVIOUS round's committed econ events
    # (Phase 4 runs after Phase 3.5, so this round's econ is not available yet).
    econ_round = round_no - 1
    for rec in st.events_this_round(econ_round, "MARKET_TRADE", kernel=ctx):
        p = rec["payload"]
        buyer, seller = p.get("buyer"), p.get("seller")
        if buyer and seller and buyer != seller:
            events += _relation_specs(state, buyer, seller, "trade_success", amount=int(p.get("amount", 0)))
            events += _relation_specs(state, seller, buyer, "trade_success", amount=int(p.get("amount", 0)))
    for rec in st.events_this_round(econ_round, "TRANSFER", kernel=ctx):
        p = rec["payload"]
        frm, to, reason = p.get("from"), p.get("to"), str(p.get("reason", ""))
        if frm and to and frm != to and any(k in reason for k in ("rescue", "help", "gift", "aid")):
            events += _relation_specs(state, to, frm, "transfer_rescue")  # recipient's view
    return events


# ---- L6 write_memories -------------------------------------------------------
# global/notable events that the kernel forces every (visible) agent to notice;
# the agent's own Phase-2 pass then materialises the memory body (side storage).
_SIGNIFICANT = {"AGENT_DIED", "SEED_EVENT", "NORM_VIOLATED", "MARKET_TRADE", "TRANSFER"}


def write_memories(state: dict, round_no: int, ctx: Ctx) -> list[EventSpec]:
    from .visibility import visible_events
    t = _time(ctx, round_no)
    st = LifeState(state)
    # T330：传**稳定的 `event_index` dict**（勿每次 list() 新建对象）⇒ 命中 T264 索引 provider，避免全扫回退
    records = st.s.get("event_index", {})
    events: list[EventSpec] = []
    for aid in st.agent_ids():
        observed = set(st.agents()[aid].get("observed_event_seqs", []))
        for rec in visible_events(records, aid, round_no):
            if rec["seq"] in observed or rec.get("type") not in _SIGNIFICANT:
                continue
            events.append(EventSpec("OBSERVATION", {
                "observer": aid, "target_event_seq": rec["seq"],
                "salience": 6 if rec["type"] in ("AGENT_DIED", "SEED_EVENT") else 3,
                "day": t["day"], "slot": t["slot"]}, actor=aid))
    return events


# ---- L7 emit_tags (+ deterministic norm lifecycle) --------------------------
def emit_tags(state: dict, round_no: int, ctx: Ctx) -> list[EventSpec]:
    t = _time(ctx, round_no)
    st = LifeState(state)
    events: list[EventSpec] = []
    # (a) TAG_EMITTED: one per completed activity — read the SAME-ROUND
    #     ACTIVITY_COMPLETED events (folded by serial L3), deterministic topic prior.
    tag_emitters: dict[tuple[str, str], set] = {}
    for rec in st.events_this_round(round_no, "ACTIVITY_COMPLETED", kernel=ctx):
        p = rec["payload"]
        aid = p["agent_id"]
        topic = C.ACTIVITY_TAG_TOPIC.get(p.get("activity_type"))
        if not topic:
            continue
        events.append(EventSpec("TAG_EMITTED", {
            "agent_id": aid, "tag": topic, "valence": 0, "source_msg_id": None,
            "day": t["day"], "slot": t["slot"]}, actor=aid))
        scope = p.get("place") or st.agents().get(aid, {}).get("location", "plaza")
        tag_emitters.setdefault((scope, topic), set()).add(aid)
    # (b) NORM lifecycle — thresholds are pure rules, never LLM (08 §1.2 F / T14-C5)
    norms = st.norms()
    for (scope, tag) in sorted(tag_emitters):
        supporters = sorted(tag_emitters[(scope, tag)])
        rule_ref = f"norm:{scope}:{tag}:majority"
        existing = next((nid for nid, n in norms.items()
                         if n.get("rule_ref") == rule_ref and n.get("status") == "adopted"), None)
        if existing is None and len(supporters) >= C.NORM_DEFAULT_THRESHOLD:
            norm_id = f"N-{scope}-{tag}"
            events.append(EventSpec("NORM_PROPOSED", {
                "norm_id": norm_id, "proposer": supporters[0], "rule_ref": rule_ref,
                "support_count": len(supporters), "threshold": C.NORM_DEFAULT_THRESHOLD,
                "day": t["day"], "slot": t["slot"]}, actor=supporters[0]))
            events.append(EventSpec("NORM_ADOPTED", {
                "norm_id": norm_id, "adopters": supporters, "adopted_day": t["day"],
                "threshold_used": C.NORM_DEFAULT_THRESHOLD}, actor="SYSTEM"))
    # (c) NORM_VIOLATED — deterministic predicate over SAME-ROUND ACTIVITY_STARTED events
    adopted = {nid: n for nid, n in st.norms().items() if n.get("status") == "adopted"}
    for nid in sorted(adopted):
        rule_ref = adopted[nid].get("rule_ref", "")
        for rec in st.events_this_round(round_no, "ACTIVITY_STARTED", kernel=ctx):
            p = rec["payload"]
            if _violates(rule_ref, p, t):
                events.append(EventSpec("NORM_VIOLATED", {
                    "norm_id": nid, "violator": p["agent_id"], "day": t["day"], "severity": 1},
                    actor=p["agent_id"]))
    return events


def _violates(rule_ref: str, activity: dict, t: dict) -> bool:
    """Deterministic violation predicate, keyed by rule_ref (never LLM)."""
    # skeleton rule: norm:<scope>:no_work_at_night:majority
    if rule_ref.endswith("no_work_at_night:majority"):
        scope = rule_ref.split(":", 2)[1]
        return (activity.get("place") == scope and activity.get("activity_type") == "work"
                and t.get("slot") == "night")
    return False


PHASE35_HOOKS = {
    "advance_time": advance_time,
    "resolve_schedule": resolve_schedule,
    "settle_activities": settle_activities,
    "apply_needs": apply_needs,
    "update_relations": update_relations,
    "write_memories": write_memories,
    "emit_tags": emit_tags,
}


def register_into(register_fn) -> None:
    for name, fn in PHASE35_HOOKS.items():
        register_fn(name, fn)
