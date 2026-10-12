"""Agent cognition main loop: perceive -> retrieve -> plan -> act -> reflect.

Generative Agents `Persona.move()` *structure* (persona/persona.py, Apache-2.0),
adapted to our deterministic kernel: every step reads ONLY from `kernel.perceive()`
(IF-1) and writes ONLY by handing an `Intent` to `kernel.submit_intent()` (IF-2).
The agent never mutates world state.

  perceive  : refresh local cache + track own needs + record salient observations
  retrieve  : three-factor memory retrieval (logged as MEMORY_RETRIEVE)
  plan      : weekly plan (deprivation-aware) -> INTENT.PLAN; seed goals -> INTENT.GOAL
  act       : move toward the planned place -> INTENT.MOVE
  reflect   : accumulated-importance / weekly trigger -> reflection memories
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import constants as C
from . import goals as G
from . import degrade as _degrade
from . import relations as R
from .llm import LLMClient, get_llm_client
from .memory import AssociativeMemory, EmbeddingModel, HashEmbeddingModel, SideStore
from .persona import Persona
from . import persona_drift as PD
from . import emotion as E
from . import sleep_window as _sleep
from .policy import (social_enabled, exchange_enabled, m2b_judge_mode, m2b_importance_mode,
                     narrative_persist_enabled)
from .ports import (
    INTENT_ECON_OFFER,
    INTENT_GOAL, INTENT_MEMORY, INTENT_MOVE, INTENT_OBSERVE, INTENT_PLAN, INTENT_RELATION,
    INTENT_SOCIAL, Intent, KernelPort,
)
from .soft import get_soft_layer, rng_branch
from .util import clamp, sha256_hex

_SALIENT_EVENTS = {
    "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "PLACE_ARRIVED",
    "MSG_PUBLIC", "MSG_DM", "MSG_GROUP", "RELATION_ENCOUNTER", "RELATION_CHANGE",
    "SEED_EVENT", "AGENT_DIED", "TAG_EMITTED", "NARRATIVE", "NORM_VIOLATED",
}

_TPL_TBL: dict | None = None


def _templates(places: dict) -> dict:
    global _TPL_TBL
    if _TPL_TBL is None:
        from .templates import load_activity_templates
        _TPL_TBL = load_activity_templates(places=places)
    return _TPL_TBL

# deprivation -> satisfying (activity_type, place), deterministic (06 §7.3)
_NEED_ACTIVITY = {
    "satiety": ("self_care", "kitchen"), "energy": ("rest", "residence"),
    "social": ("socialize", "plaza"), "leisure": ("leisure", "park"),
    "esteem": ("civic", "town_hall"), "mastery": ("learn", "school"),
}

# template_id -> dialogue channel (T98). private=MSG_DM, place_group=MSG_GROUP,
# global=MSG_PUBLIC.
_DM_TEMPLATES = {"whisper", "gift", "ice_break", "rel_maintain", "rel_accept",
                 "polite_reject", "counter_propose", "mentorship"}
_GROUP_TEMPLATES = {"creative_collab", "academic_collab", "power_conflict", "contest",
                    "combat_training"}
_PUBLIC_TEMPLATES = {"group_proposal", "job_choice"}


@dataclass
class StepReport:
    round: int
    perceived: int = 0
    observed: int = 0
    retrieved: list = field(default_factory=list)
    planned: bool = False
    goals_set: bool = False
    moved_to: str | None = None
    reflected: bool = False
    concentrated: bool = False
    soft_judgments: int = 0
    narrated: bool = False
    accepted: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    slept: int = 0


class LifeLayerAgent:
    def __init__(self, agent_id: str, persona: Persona, kernel: KernelPort, *,
                 llm: LLMClient | None = None, side_store: SideStore,
                 embedding: EmbeddingModel | None = None,
                 memory_params: dict | None = None,
                 places: dict[str, dict] | None = None,
                 peers: list[str] | None = None) -> None:
        self.agent_id = agent_id
        self.persona = persona
        self.kernel = kernel
        self.llm = llm or get_llm_client()
        self.embedding = embedding or HashEmbeddingModel()
        self.memory = AssociativeMemory(agent_id, self.embedding, side_store, memory_params)
        self.side_store = side_store       # T234: 叙事正文 writer 复用同一 side root
        self.places = places or {}
        self.peers = [p for p in (peers or []) if p and p != agent_id]
        self.soft = get_soft_layer(self.llm)
        self._rel_cache: dict = {}          # (to, dim) -> current outgoing relation value
        self._judged: set = set()           # (to, dim, level) already soft-judged
        self._llm_permit = True             # T221c: M4 本回合 LLM 许可（默认 True=不变）
        self._appraised: set = set()        # (to, week) already social-appraised (T127)
        self._narrated_weeks: set = set()
        self._comm_slot: str | None = None  # last slot we generated dialogue for (≤1/slot)
        self._accepted: set = set()         # offer_ids already accepted (T133)
        # own needs (initial from persona; then folded from own NEED_UPDATE events)
        self.needs: dict[str, int] = {d: int(persona.needs_init.get(d, 50)) for d in C.NEED_DIMS}
        # agent-local ephemera (NOT world state):
        self._planned_weeks: set[int] = set()
        self._goals_set_weeks: set[int] = set()
        self._plan_slots: dict[str, dict] = {}
        self._observed_seqs: set[int] = set()
        # T224 睡眠离线窗（默认关；见 config/life_v2.json）—— agent-local 表达层状态
        self._persona_state: dict | None = None
        self._persona_p0: dict | None = None
        self._slept_days: set[int] = set()
        self._drift_streak: dict[str, int] = {}  # T244: 逐维"连续被反思信号"计数（分抖动/真漂移）

    # ---- T288 / T276: 从账本单一真源恢复「只前向累积」的内部态 ---------------
    def restore(self, state, records) -> None:
        """Rebuild forward-accumulated internal state from the ledger (single source).

        Called by `orchestration` once, right after `load_prefix` (duck-typed hook).
        **只做「原样重建」，不做有界化**（有界化=改语义，另议）。

        Rebuilt: `_observed_seqs` / `needs` / `_plan_slots`(schedule) /
        `_planned_weeks` / `_goals_set_weeks` / `_comm_slot` / `_narrated_weeks` /
        `_accepted` / `_rel_cache`, plus `memory` via `sync_from_refs`.
        No new decision, no event payload change — the engine world state was already
        restored by `replay_records`; this only re-syncs the life-side mirrors.
        """
        from .ports import MemoryRef
        a = state.agents.get(self.agent_id)
        if a is None:
            return
        # memory (bodies/embeddings live in side storage; sync rebuilds nodes)
        self.memory.sync_from_refs(tuple(
            MemoryRef(mem_id=m["mem_id"], kind=m["kind"], body_ref=m["body_ref"],
                      embed_ref=m["embed_ref"], importance=int(m["importance"]),
                      day=int(m["day"]), slot=m["slot"], subject=m.get("subject"),
                      source_event_seq=m.get("source_event_seq"),
                      last_access=int(m.get("last_access", 0)),
                      access_count=int(m.get("access_count", 0)))
            for m in a.get("memories", [])))
        # memory reflection state (reflection dedup + unreflected accumulator):
        # otherwise the resumed run re-fires MEMORY_REFLECT (observed at N=20).
        _W = (C.TIME_CONFIG["DAYS_PER_WEEK"] * len(C.TIME_CONFIG["SLOTS_PER_DAY"])
              * C.TIME_CONFIG["ROUNDS_PER_SLOT"])
        for rec in records:
            if rec.get("type") == "MEMORY_REFLECT" and (rec.get("payload") or {}).get("agent_id") == self.agent_id:
                for mid in ((rec.get("payload") or {}).get("triggered_by_mem_ids") or []):
                    nd = self.memory.nodes.get(mid)
                    if nd is not None:
                        nd.reflected = True
                self.memory.note_reflection(int(rec.get("round", 0)) // _W)
        self.memory._unreflected_importance = sum(
            n.importance for n in self.memory.nodes.values()
            if n.kind == "observation" and not n.reflected)
        # T244 睡眠/人格前向态（原样重建）—— 否则 cut 落在 night 边界时，续跑会**重跑**该日
        # 睡眠窗（`_slept_days` 空）并丢失已累积的人格漂移（`_persona_state`）。
        slept: set = set()
        persona_after: dict = {}
        for rec in records:
            p = rec.get("payload") or {}
            if p.get("agent_id") != self.agent_id:
                continue
            t = rec.get("type")
            if t in ("SLEEP_STARTED", "SLEEP_COMPLETED") and p.get("day") is not None:
                slept.add(int(p["day"]))
            elif t == "PERSONA_DRIFT" and p.get("dim"):
                persona_after[p["dim"]] = p.get("after")
        self._slept_days = slept
        if slept or persona_after:
            anchor = {"personality_big5": self.persona.personality_big5}
            self._persona_p0 = PD.init_state(anchor)
            st = PD.init_state(anchor)
            for k, v in persona_after.items():
                if v is not None:
                    st[k] = int(v)
            self._persona_state = st
        # T323：`_drift_streak` 按"**逐维**、连续含候选窗数"原样重建
        # （每睡眠窗：该维有候选→+1；`reached_threshold`→清零；缺失→0）
        cand_reached: dict = {}
        for rec in records:
            p = rec.get("payload") or {}
            if rec.get("type") == "PERSONA_DRIFT_CANDIDATE" and p.get("agent_id") == self.agent_id:
                cand_reached[(p.get("window"), p.get("dim"))] = bool(p.get("reached_threshold"))
        if slept or cand_reached:
            streak: dict = {}
            for w in sorted(slept):
                for dim in PD.BIG5_DIMS:
                    key = (w, dim)
                    if key in cand_reached:
                        streak[dim] = streak.get(dim, 0) + 1
                        if cand_reached[key]:
                            streak[dim] = 0
                    else:
                        streak[dim] = 0
            self._drift_streak = streak
        # observed: engine-authoritative OBSERVATION set ∪ this agent's MEMORY_WRITE sources
        obs = set(a.get("observed_event_seqs", []))
        for rec in records:
            if rec.get("type") == "MEMORY_WRITE" and (rec.get("payload") or {}).get("agent_id") == self.agent_id:
                s = (rec["payload"] or {}).get("source_event_seq")
                if s is not None:
                    obs.add(s)
        self._observed_seqs = obs
        # needs (own NEED_UPDATE folded into engine agent state)
        self.needs = {d: int(a.get("needs", {}).get(d, self.needs.get(d, 50))) for d in C.NEED_DIMS}
        # schedule -> _plan_slots (planner re-reads this; avoids re-planning drift)
        self._plan_slots = {}
        for s in a.get("schedule", []) or []:
            sid = s.get("slot_id")
            if not sid:
                continue
            e = {"activity_type": s.get("activity_type"), "place": s.get("place")}
            for k in ("template_id", "participants"):
                if k in s:
                    e[k] = s[k]
            self._plan_slots[sid] = e
        # week caches + dialogue/narrative dedup (else resume re-emits events)
        W = (C.TIME_CONFIG["DAYS_PER_WEEK"] * len(C.TIME_CONFIG["SLOTS_PER_DAY"])
             * C.TIME_CONFIG["ROUNDS_PER_SLOT"])
        planned: set[int] = set()
        goals_weeks: set[int] = set()
        narrated: set[int] = set()
        accepted: set = set()
        judged: set = set()
        appraised: set = set()
        comm_round = None   # _comm_slot 按"是否**尝试**过对话"定（被拒的尝试不留 MSG_*）
        _slot_names = C.TIME_CONFIG["SLOTS_PER_DAY"]
        _rps = C.TIME_CONFIG["ROUNDS_PER_SLOT"]
        _dow = C.TIME_CONFIG.get("DAYS_PER_WEEK", 7)

        def _slot_of(rr: int) -> str:
            per_day = len(_slot_names) * _rps
            return f"day{(rr // per_day) % _dow}-{_slot_names[(rr % per_day) // _rps]}"

        rel: dict = {}
        for rec in records:
            t = rec.get("type")
            p = rec.get("payload") or {}
            r = int(rec.get("round", 0))
            if t == "SCHEDULE_PLANNED" and p.get("agent_id") == self.agent_id:
                planned.add(r // W)
            elif t == "GOAL_SET" and (p.get("agent_id") == self.agent_id or rec.get("actor") == self.agent_id):
                goals_weeks.add(r // W)
            elif t in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
                who = p.get("from") or p.get("author") or rec.get("actor")
                if who == self.agent_id:
                    if comm_round is None or r >= comm_round:
                        comm_round = r
            elif t == "INTENT_REJECTED":
                # `_communicate` 在**尝试**时就置 `_comm_slot`（即使 SOCIAL 被拒、无 MSG_*）⇒
                # 被拒的对话尝试也必须算，否则续跑会**重复尝试**同一 slot（T298 cut=75）。
                if p.get("agent_id") == self.agent_id and p.get("intent_class") == "INTENT.SOCIAL":
                    if comm_round is None or r >= comm_round:
                        comm_round = r
            elif t == "NARRATIVE":
                br = p.get("body_ref") or ""
                if f"narrative/{self.agent_id}/" in br:
                    tail = br.rsplit("-", 1)[-1].split(".")[0]
                    if tail.isdigit():
                        narrated.add(int(tail))
            elif t == "OFFER_ACCEPTED":
                who = p.get("by") or p.get("accepter") or p.get("to")
                oid = p.get("offer_id")
                if oid and who == self.agent_id:
                    accepted.add(oid)
            elif t == "RELATION_CHANGE" and p.get("from") == self.agent_id:
                rel[(p.get("to"), p.get("dim"))] = p.get("after")
            elif t == "LLM_JUDGMENT" and (p.get("judgment_id") or "").startswith("J-"):
                # 去重集按 **jid 归属人**（`J-<owner>-<to>-<dim>-...`）计，而非"parties 含我"——
                # 否则会把**对方**的判定误记到我名下（实测：`J-P003-P001-affinity-weak-11`
                # 曾被错加进 P001 的 `_judged`，导致 P001 在 round22 漏判）。
                dim = p.get("dimension") or ""
                toks = (p.get("judgment_id") or "").split("-")
                if len(toks) < 5 or toks[1] != self.agent_id:
                    continue
                if dim.startswith("rel_") and len(toks) >= 6:
                    judged.add((toks[2], dim[4:], toks[4]))
                elif dim in ("stance", "respect", "affection"):
                    tail = toks[4]
                    if tail[:1] == "w" and tail[1:].isdigit():
                        appraised.add((toks[2], int(tail[1:])))
        self._planned_weeks = planned
        self._goals_set_weeks = goals_weeks
        self._narrated_weeks = narrated
        self._accepted = accepted
        self._judged = judged
        self._appraised = appraised
        self._comm_slot = _slot_of(comm_round) if comm_round is not None else None
        self._rel_cache = rel

    # ---- public entry ------------------------------------------------------
    def step(self) -> StepReport:
        wv = self.kernel.perceive(self.agent_id)          # IF-1 (read-only)
        rep = StepReport(round=wv.round)
        self._llm_permit = self._llm_ok(wv)               # T221c: M4 本回合 LLM 许可
        self.memory.sync_from_refs(wv.memory_refs)
        self._update_needs(wv)
        self._observe(wv, rep)
        retrieved_ids, _ = self._retrieve(wv)
        rep.retrieved = retrieved_ids
        rep.planned, rep.goals_set = self._plan(wv)
        rep.moved_to = self._act(wv)
        rep.reflected = self._reflect(wv, retrieved_ids)
        self._fold_relations(wv)
        rep.soft_judgments = self._maybe_soft_judge(wv)
        self._maybe_social_appraisal(wv)
        rep.narrated = self._maybe_narrate(wv)
        self._communicate(wv)
        self._maybe_negotiate(wv)
        self._maybe_accept_offers(wv)
        rep.slept = self._maybe_sleep_window(wv)
        return rep

    # ---- helpers -----------------------------------------------------------
    def _submit(self, intent: Intent, rep: StepReport) -> bool:
        res = self.kernel.submit_intent(self.agent_id, intent)
        if res.ok:
            rep.accepted.append(intent.intent_class)
        else:
            rep.rejected.append(f"{intent.intent_class}:{res.reason}")
        return res.ok

    def _update_needs(self, wv) -> None:
        for ev in wv.visible_events:
            if ev.type == "NEED_UPDATE" and ev.payload.get("agent_id") == self.agent_id:
                self.needs[ev.payload["dim"]] = int(ev.payload["after"])

    # 1. perceive ----------------------------------------------------------
    def _observe(self, wv, rep: StepReport) -> None:
        rep.perceived = len(wv.visible_events)
        for ev in wv.visible_events:
            if ev.seq in self._observed_seqs or ev.type not in _SALIENT_EVENTS:
                continue
            self._observed_seqs.add(ev.seq)
            text = self._describe_event(ev)
            imp = self._score_importance(text, wv.round)
            payload = self.memory.prepare_write(
                kind="observation", text=text, importance=imp, day=wv.day, slot=wv.slot,
                tick=wv.round, subject=ev.actor if ev.actor != self.agent_id else None,
                refs=[str(ev.seq)], source_event_seq=ev.seq)
            if self._submit(Intent(INTENT_MEMORY, self.agent_id, payload), rep):
                self.memory.commit_write(payload)
                self._submit(Intent(INTENT_OBSERVE, self.agent_id,
                                    {"target_event_seq": ev.seq, "salience": imp}), rep)
                rep.observed += 1

    # 2. retrieve ----------------------------------------------------------
    def _retrieve(self, wv, query: str | None = None) -> tuple[list, dict]:
        if query is None:
            query = self._retrieval_query(wv)
        hits, debug = self.memory.score_and_rank(query, now_tick=wv.round)
        ids = [n.mem_id for n, _ in hits]
        scores = [round(s, 6) for _, s in hits]
        payload = {"op": "retrieve", "query_id": f"Q-{self.agent_id}-{wv.round}",
                   "top_k": debug["top_k"], "selected_mem_ids": ids, "scores": scores,
                   "weights": debug["weights"], "tie_order": debug["tie_order"],
                   "query_digest": self.embedding.version}
        # T228：检索降级标记（additive；字段名引用 freeze.side 单一来源，不另拼）
        try:
            from freeze.side import degradation_marker
            payload.update(degradation_marker(
                vec_available=debug.get("vec_available", True),
                retrieval_mode=debug.get("retrieval_mode", "vector")))
        except Exception:
            payload["vec_available"] = bool(debug.get("vec_available", True))
            payload["retrieval_mode"] = debug.get("retrieval_mode", "vector")
        if self._submit(Intent(INTENT_MEMORY, self.agent_id, payload), StepReport(wv.round)):
            self.memory.touch(ids, wv.round)
        return ids, debug

    def _retrieval_query(self, wv) -> str:
        recents = [n.text for n in list(self.memory.nodes.values())[-3:]]
        head = f"{self.persona.compressed_profile(self._current_goal())} {self._activity_for(wv)[0]}"
        return head + " " + " ".join(recents)

    # ---- M6 降级 gate（T221c）：默认关 = 行为不变 -------------------------------
    def _llm_ok(self, wv) -> bool:
        """M4：本回合该 agent 是否获准调用 LLM（`schedule_enabled` 时按 Kc 限流）。
        默认 True（未启用=行为不变）；异常偏保守（True，宁可多算不可静默少算）。"""
        try:
            return _degrade.llm_permit(wv)
        except Exception:
            return True

    def _judge_skip(self, wv, dimension: str, parties) -> bool:
        """M6 critical-only：该 judge 是否应跳过（M4 未许可 或 内核 critical-only 判跳）。
        内核已负责把跳过落成**可列** `DEGRADE`；life 只读布尔。默认 False=不跳。"""
        if not self._llm_ok(wv):
            return True
        try:
            return _degrade.should_skip_judgment(self.kernel, dimension, parties)
        except Exception:
            return False

    # 3. plan --------------------------------------------------------------
    def _plan(self, wv) -> tuple[bool, bool]:
        if wv.time.week in self._planned_weeks:
            return False, False
        focus = self._weekly_focus(wv)          # LLM-decided, frozen (T57)
        slots = self._weekly_slots(wv, focus)
        if self._llm_ok(wv):                     # T221c: M4 未许可 → 不调 LLM（计划本身确定性）
            self.llm.call("plan", self.persona.compressed_profile(self._current_goal()),
                          meta={"agent_id": self.agent_id, "round": wv.round})
        planned = self._submit(Intent(INTENT_PLAN, self.agent_id,
                                      {"horizon": "week", "week": wv.time.week, "slots": slots}),
                               StepReport(wv.round))
        if planned:
            self._planned_weeks.add(wv.time.week)
        goals_set = False
        if wv.time.week not in self._goals_set_weeks:
            goals = [g.as_dict() for g in G.initial_goals(self.agent_id, self.persona)]
            if self._submit(Intent(INTENT_GOAL, self.agent_id, {"op": "set", "goals": goals}),
                            StepReport(wv.round)):
                self._goals_set_weeks.add(wv.time.week)
                goals_set = True
        return planned, goals_set

    def _weekly_focus(self, wv) -> str:
        """LLM decides the week's focus from a small option set; the choice is FROZEN
        (LLM_JUDGMENT) so the resulting plan stays replay-stable, yet differs between
        mock and a real LLM (T57: LLM output drives structure)."""
        from .planner import FOCUS_OPTIONS
        mode = m2b_judge_mode()
        # M2b 判别式：候选含逃生项（单一真源 JUDGMENT_OPTIONS）；关闭时用旧 FOCUS_OPTIONS（逐项一致）
        options = list(C.JUDGMENT_OPTIONS["weekly_focus"]) if mode == "discriminative" \
            else list(FOCUS_OPTIONS)
        branch = rng_branch(self.agent_id, "weekly_focus", "self", wv.time.week, options)
        envelope = {"options": options}
        jid = f"JF-{self.agent_id}-{wv.time.week}"
        if self._judge_skip(wv, "weekly_focus", [self.agent_id]):
            return str(branch)               # 降级：确定性 RNG 选择，不调 LLM
        try:
            payload, emitted = self.soft.judge(
                judgment_id=jid, dimension="weekly_focus", question_ref="weekly_focus",
                envelope=envelope, rng_branch=branch, parties=[self.agent_id],
                context={"goal": self._current_goal(), "needs": dict(self.needs),
                         "memories": self.memory.summary_for_prompt(
                             list(self.memory.nodes)[-8:], 300)},
                round_no=wv.round, mode=mode)
        except Exception:
            return "balance"
        if not emitted:
            self._submit_audit("LLM_JUDGMENT", payload, phase=2)
        return str(payload.get("resolved", payload["decision"]))

    def _weekly_slots(self, wv, focus: str | None = None) -> list[dict]:
        """Weekly plan. Social/economy slots may carry a `template_id` (T49) chosen by
        the deterministic `Planner`; other slots fall back to the base template."""
        from .planner import Planner
        templates = _templates(self.places)
        planner = Planner(self.agent_id, templates, self.peers, self.places)
        slots = []
        self._plan_slots = {}
        for dow in range(C.TIME_CONFIG["DAYS_PER_WEEK"]):
            day_type = C.TIME_CONFIG["DAY_TYPES"][dow]
            for si, slot in enumerate(C.TIME_CONFIG["SLOTS_PER_DAY"]):
                slot_id = f"day{dow}-{slot}"
                planned_tick = dow * 12 + si * C.TIME_CONFIG["ROUNDS_PER_SLOT"]
                chosen = planner.plan_slot(day_type, slot, slot_id, int(wv.cash), focus)
                extra: dict = {}
                if chosen:
                    atype, place = chosen["activity_type"], chosen["place"]
                    extra = {"template_id": chosen["template_id"],
                             "participants": chosen["participants"]}
                    self._plan_slots[slot_id] = {"activity_type": atype, "place": place,
                                                 "template_id": chosen["template_id"],
                                                 "participants": chosen["participants"]}
                else:
                    atype, place = self._choose_activity(day_type, slot)
                    self._plan_slots[slot_id] = {"activity_type": atype, "place": place}
                d = {"slot_id": slot_id, "activity_type": atype, "place": place,
                     "priority": 0.7, "planned_tick": planned_tick}
                d.update(extra)
                slots.append(d)
        return slots

    def _base_activity(self, day_type: str, slot: str) -> tuple[str, str]:
        if slot == "night":
            return ("rest", "residence")
        if slot == "morning":
            if day_type == "workday":
                wp = self._work_place_for(slot)
                return ("work", wp) if wp else ("self_care", "residence")
            return ("self_care", "residence")
        if slot == "afternoon":
            if day_type == "workday":
                wp = self._work_place_for(slot)
                return ("work", wp) if wp else ("socialize", "plaza")
            return ("socialize", "plaza")
        return ("socialize", "cafe") if day_type == "workday" else ("leisure", "park")

    def _valid(self, atype: str, place: str, slot: str) -> bool:
        spec = self.places.get(place, {})
        return slot in spec.get("open_slots", []) and atype in spec.get("affordances", [])

    def _work_place_for(self, slot: str) -> str | None:
        """A place that actually affords `work` and is open at `slot` (role's, else any)."""
        wp = self.persona.work_place
        if self._valid("work", wp, slot):
            return wp
        for cand in C.ACTIVITY_TO_PLACES["work"]:
            if self._valid("work", cand, slot):
                return cand
        return None

    def _choose_activity(self, day_type: str, slot: str) -> tuple[str, str]:
        """Deprivation-aware (06 §7.3): a need below θ_dep overrides the template."""
        base = self._base_activity(day_type, slot)
        if slot == "night":
            return base
        deprived = [d for d in C.NEED_DIMS if self.needs.get(d, 50) < C.THETA_DEP]
        if not deprived:
            return base
        dim = min(deprived, key=lambda d: (self.needs.get(d, 50), d))
        atype, place = _NEED_ACTIVITY[dim]
        if self._valid(atype, place, slot):
            return (atype, place)
        return base

    def _activity_for(self, wv) -> tuple[str, str]:
        slot_id = f"day{wv.time.day_of_week}-{wv.time.slot}"
        entry = self._plan_slots.get(slot_id)
        if entry:
            return entry["activity_type"], entry["place"]
        return self._base_activity(wv.time.day_type, wv.time.slot)

    # 4. act ---------------------------------------------------------------
    def _act(self, wv) -> str | None:
        atype, place = self._activity_for(wv)
        if wv.location == place:
            return None
        slot_id = f"day{wv.time.day_of_week}-{wv.time.slot}"
        res = self.kernel.submit_intent(self.agent_id, Intent(
            INTENT_MOVE, self.agent_id, {"to_place": place, "slot_id": slot_id,
                                         "activity_type": atype}))
        return place if res.ok else None

    # 5. reflect -----------------------------------------------------------
    def _reflect(self, wv, retrieved_ids: list) -> bool:
        force_weekly = C.week_phase(
            {"day_of_week": wv.time.day_of_week, "slot": wv.time.slot}) == "REVIEW"
        if not self.memory.reflection_due(wv.time.week, force_weekly):
            return False
        if not self._llm_ok(wv):                     # T221c: M4 未许可 → 跳过反思 LLM
            return False
        src_ids, imp_sum = self.memory.take_reflection_input()
        prompt = self.persona.compressed_profile(self._current_goal()) + "\n" + \
            self.memory.summary_for_prompt(src_ids or retrieved_ids)
        text = self.llm.call("reflect", prompt,
                             meta={"agent_id": self.agent_id, "round": wv.round}).text
        produced = []
        for i in range(3):
            payload = self.memory.prepare_write(
                kind="reflection", text=f"{text}（insight {i + 1}）", importance=min(10, 6 + i),
                day=wv.day, slot=wv.slot, tick=wv.round, refs=list(src_ids))
            if self._submit(Intent(INTENT_MEMORY, self.agent_id, payload), StepReport(wv.round)):
                self.memory.commit_write(payload)
                produced.append(payload["mem_id"])
        if produced:
            self._submit(Intent(INTENT_MEMORY, self.agent_id, {
                "op": "reflect", "triggered_by_mem_ids": src_ids, "importance_sum": imp_sum,
                "produced_mem_id": produced[0], "produced_mem_ids": produced}), StepReport(wv.round))
            self.memory.note_reflection(wv.time.week)
            return True
        return False

    # ---- soft judgment (F) & narrative (N) --------------------------------
    def _fold_relations(self, wv) -> None:
        for ev in wv.visible_events:
            if ev.type == "RELATION_CHANGE" and ev.payload.get("from") == self.agent_id:
                to = ev.payload.get("to")
                if to:
                    self._rel_cache[(to, ev.payload["dim"])] = int(ev.payload["after"])

    def _submit_audit(self, kind: str, payload: dict, phase: int) -> None:
        fn = getattr(self.kernel, "submit_audit", None)
        if fn is not None:  # mini test-double path; the freeze layer emits on its own
            fn(kind, payload, actor=self.agent_id, phase=phase)

    def _maybe_soft_judge(self, wv) -> int:
        n = 0
        mode = m2b_judge_mode()
        for (to, dim), after in list(self._rel_cache.items()):
            if dim not in ("affinity", "trust", "respect", "familiarity"):
                continue
            level = "strong" if abs(after) >= C.EPS_STRONG else ("weak" if abs(after) >= C.EPS else None)
            if level is None or (to, dim, level) in self._judged:
                continue
            self._judged.add((to, dim, level))
            envelope = R.soft_judgment_envelope(dim, 0, after)
            if mode == "discriminative":  # M2b: 候选含逃生项（单一真源）
                envelope = {**envelope, "options": list(C.JUDGMENT_OPTIONS[f"rel_{dim}"])}
            branch = rng_branch(self.agent_id, dim, to, wv.round, envelope["options"])
            jid = f"J-{self.agent_id}-{to}-{dim}-{level}-{wv.round}"
            if self._judge_skip(wv, f"rel_{dim}", [self.agent_id, to]):
                continue
            payload, emitted = self.soft.judge(
                judgment_id=jid, dimension=f"rel_{dim}", question_ref="rel_relation_quality",
                envelope=envelope, rng_branch=branch, parties=[self.agent_id, to],
                context={"dim": dim, "to": to, "after": after}, round_no=wv.round, mode=mode)
            if not emitted:
                self._submit_audit("LLM_JUDGMENT", payload, phase=2)
            # numeric consequence from the FROZEN label (deterministic, D-12);
            # M2b 逃生项命中时用确定性兜底值 resolved（decision 保留模型原话）
            for d, dv in R.delta_from_frozen_label(
                    payload.get("resolved", payload["decision"])).items():
                before = int(self._rel_cache.get((to, d), 0))
                lo, hi = C.RELATION_RANGE[d]
                self.kernel.submit_intent(self.agent_id, Intent(INTENT_RELATION, self.agent_id, {
                    "to": to, "dim": d, "before": before,
                    "after": clamp(before + dv, lo, hi), "cause": "soft_judgment"}))
            n += 1
        return n

    def _maybe_social_appraisal(self, wv) -> int:
        """T127: emit frozen LLM_JUDGMENT for two extra social dimensions that light
        up the `rel-acceptance` (stance flip) and `diff-scoring` (respect/affection
        divergence) cards. Same frozen path as the relation judgments: RNG picks the
        branch, the LLM fills the label, the decision is frozen into the log (replay
        reads it back, never re-calls). One appraisal per (peer, week), bounded."""
        week = wv.time.week
        peers = sorted({to for (to, _dim) in self._rel_cache})[:4]
        n = 0
        mode = m2b_judge_mode()
        for to in peers:
            key = (to, week)
            if key in self._appraised:
                continue
            self._appraised.add(key)
            for dim, opts in (("stance", ["accept", "reject"]),
                              ("respect", ["high", "low"]),
                              ("affection", ["high", "low"])):
                if mode == "discriminative":  # M2b: 候选含逃生项（单一真源）
                    opts = list(C.JUDGMENT_OPTIONS[dim])
                branch = rng_branch(self.agent_id, dim, to, wv.round, opts)
                envelope = {"options": list(opts)}
                jid = f"J-{self.agent_id}-{to}-{dim}-w{week}"
                if self._judge_skip(wv, dim, [self.agent_id, to]):
                    continue
                payload, emitted = self.soft.judge(
                    judgment_id=jid, dimension=dim, question_ref=f"social_{dim}",
                    envelope=envelope, rng_branch=branch, parties=[self.agent_id, to],
                    context={"dim": dim, "to": to}, round_no=wv.round, mode=mode)
                if not emitted:
                    self._submit_audit("LLM_JUDGMENT", payload, phase=2)
                n += 1
        return n

    def _maybe_narrate(self, wv) -> bool:
        phase = C.week_phase({"day_of_week": wv.time.day_of_week, "slot": wv.time.slot})
        if phase != "REVIEW" or wv.time.week in self._narrated_weeks:
            return False
        if not self._llm_ok(wv):                     # T221c: M4 未许可 → 跳过叙事 LLM
            return False
        self._narrated_weeks.add(wv.time.week)
        seqs = [ev.seq for ev in wv.visible_events][-20:]
        nid = f"N-{self.agent_id}-{wv.time.week}"
        body_ref = SideStore.narrative_ref(self.agent_id, nid)
        payload, emitted, text = self.soft.narrate(
            narrative_id=nid, fact_event_seqs=seqs,
            body_ref=body_ref, round_no=wv.round)
        # T234: 写入叙事正文到 side（IF-7 body_ref 的 writer）；开关关时不写。
        if emitted and text and narrative_persist_enabled():
            self.side_store.write_narrative(self.agent_id, nid, text)
        if not emitted:
            self._submit_audit("NARRATIVE", payload, phase=6)
        return True

    # ---- M6 dialogue / public / group (T98) --------------------------------
    def _communicate(self, wv) -> None:
        """Generate wording via the LLM (purpose=dialogue) for a significant social
        event and submit INTENT.SOCIAL. Wording is frozen (logged in the MSG_* event),
        so replay never re-calls the model. ≤1 per agent per slot; round-level quotas
        are enforced by the kernel."""
        slot_id = f"day{wv.time.day_of_week}-{wv.time.slot}"
        if not social_enabled():          # T115: whole social-voice channel off
            return
        if not self._llm_ok(wv):          # T221c: M4 未许可 → 不发对话 LLM
            return
        if slot_id == self._comm_slot:
            return
        entry = self._plan_slots.get(slot_id)
        if not entry or not entry.get("template_id"):
            return
        tid = entry["template_id"]
        parts = list(entry.get("participants") or [self.agent_id])
        partners = [p for p in parts if p != self.agent_id]
        scope, to, gid = "global", None, None
        if tid in _DM_TEMPLATES and partners:
            scope, to = "private", partners[0]
        elif tid in _GROUP_TEMPLATES and len(parts) >= 3:
            scope, gid = "place_group", f"place:{entry['place']}"
        elif tid in _PUBLIC_TEMPLATES:
            scope = "global"
        elif partners:
            scope, to = "private", partners[0]
        res = self.llm.call("dialogue", self._dialogue_prompt(tid, parts),
                            meta={"agent_id": self.agent_id, "round": wv.round, "template": tid})
        body = (res.text or "").strip()
        if not body:
            return
        self._comm_slot = slot_id
        payload: dict = {"scope": scope, "body": body, "refs": [], "tag_hints": [tid]}
        if to:
            payload["to"] = to
        if gid:
            payload["group_id"] = gid
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_SOCIAL, self.agent_id, payload))

    def _dialogue_prompt(self, tid: str, parts: list) -> str:
        others = ", ".join(p for p in parts if p != self.agent_id) or "(独自)"
        return (self.persona.compressed_profile(self._current_goal())
                + f"\n场景：{tid}；对象：{others}。请用一句话自然地说点什么。")

    # ---- economy: negotiation / offer / order-cancel (T133) ----------------
    def _maybe_negotiate(self, wv) -> None:
        """Produce `INTENT.ECON.*` in the decision phase (v2/04 §5). The LLM
        (`purpose="negotiation"`, thinking=false) only writes the *wording*; the
        asking terms are the agent's own (deterministic, per-round) — never a preset
        world price. Money/goods consequences are settled by the kernel's 4.x hooks.
        Bounded: once per (agent, day)."""
        if not exchange_enabled():
            return
        if not self._llm_ok(wv):            # T221c: M4 未许可 → 不发议价 LLM
            return
        if wv.round % 12 != 0:              # ~ once per day per agent
            return
        # only sell what we actually hold; restrict to transferable goods if the
        # kernel exposes that hint (avoids good_not_transferable drops).
        held = {g: int(q) for g, q in (wv.inventory or []) if int(q) > 0}
        tg = set(getattr(wv, "transferable_goods", ()) or ())
        if tg:
            held = {g: q for g, q in held.items() if g in tg}
        if not held:
            return
        # deterministic pick: largest holding, ties by good_id asc (seed-stable)
        good = min(held, key=lambda g: (-held[g], g))
        res = self.llm.call(
            "negotiation",
            self.persona.compressed_profile(self._current_goal())
            + "\n请拟一句向街坊兜售余货/邀约议价的口头话（只写措辞，不写数字）。",
            meta={"agent_id": self.agent_id, "round": wv.round})
        wording = (res.text or "").strip()
        # agent's own ASK (deterministic, per-round); NOT a preset world price
        price = 50 + (int(sha256_hex(f"ask:{self.agent_id}:{wv.round}")[:6], 16) % 151)
        # public board offer (to=[] == broadcast discovery, v2/04 §4.1)
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_ECON_OFFER, self.agent_id, {
            "act": "create", "kind": "sale", "to": [],
            "terms": {"good_id": good, "price_mu": price, "qty": 1},
            "enforceable": False, "body": wording}))
        # NOTE (T133): no ORDER_PLACE / ORDER_CANCEL here — the order-book path is
        # deferred to its own wave; producing a cancel without a place is a half-state.

    def _maybe_accept_offers(self, wv) -> None:
        """P2: read the (public) offer board via `visible_events()` and ACCEPT an offer
        addressed to us or broadcast (`to=[]`), **at the offer's own terms** (no preset
        price). Submits `INTENT.ECON.OFFER{act:"accept",...}`; the kernel wraps it into
        `OFFER_ACCEPTED`. ≤1 accept per round; each offer accepted at most once."""
        if not exchange_enabled():
            return
        for ev in wv.visible_events:
            if ev.type != "OFFER_CREATED":
                continue
            p = ev.payload or {}
            oid = p.get("offer_id")
            to = list(p.get("to") or [])
            if not oid or oid in self._accepted or p.get("from") == self.agent_id:
                continue
            if to:                                    # only public-board offers (to==[])
                continue
            self._accepted.add(oid)
            self.kernel.submit_intent(self.agent_id, Intent(INTENT_ECON_OFFER, self.agent_id, {
                "act": "accept", "offer_id": oid, "terms": p.get("terms") or {}}))
            return                                    # ≤1 accept per round

    # ---- misc ------------------------------------------------------------
    def _sleep_params(self) -> dict:
        """T224：睡眠窗口参数（读 config/life_v2.json；默认关）。可被测试覆盖。"""
        return _sleep.load_params()

    def _maybe_sleep_window(self, wv) -> int:
        """T224 挂载点：night 时段执行一次睡眠离线窗（固化/遗忘/人格漂移）。

        **默认关**（`config/life_v2.json`）→ 直接返回 0、零副作用、行为与接入前逐项一致。
        产出以 INTENT.MEMORY 意图提交（`op ∈ {sleep_start,forget,consolidate,sleep_end}`），
        由裁决器落 `SLEEP_STARTED/MEMORY_FORGET/MEMORY_CONSOLIDATE/SLEEP_COMPLETED` 事件。
        **不新增决策类 LLM 调用**（纯整数模块）。不触碰 M2b 判定调用点。
        """
        params = self._sleep_params()
        if not _sleep.enabled(params):
            return 0
        slot = params["sleep"].get("slot", "night")
        if wv.time.slot != slot:
            return 0
        day = int(wv.time.day)
        if day in self._slept_days:
            return 0
        self._slept_days.add(day)

        anchor = {"persona_id": self.persona.persona_id,
                  "personality_big5": self.persona.personality_big5,
                  "values": self.persona.values, "skills": self.persona.skills}
        if self._persona_state is None:      # 锚定不写回：P(0)=anchor，之后只动表达层
            self._persona_state = PD.init_state(anchor)
            self._persona_p0 = dict(self._persona_state)
        mems = [{"mem_id": n.mem_id, "kind": n.kind, "importance": n.importance,
                 "last_access": n.last_access, "access_count": n.access_count,
                 "subject": n.subject, "emo": 0, "consolidated": False}
                for n in self.memory.nodes.values()]

        planned = int(params["sleep"].get("planned_ticks", 3))
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
            "op": "sleep_start", "day": day, "slot": slot, "planned_ticks": planned}))
        out = _sleep.run_sleep_window(self.agent_id, mems, wv.round, params,
                                      day=day, slot=slot, anchor=anchor,
                                      p_state=self._persona_state, p0=self._persona_p0,
                                      drift_events=self._reflection_drift_events(
                                          params, day=day, slot=slot, window=day))
        n = 0
        for a in out["forget"]:
            if self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
                    "op": "forget", "mem_id": a["mem_id"], "level": a["level"],
                    "retention_permille": a["retention_permille"], "reason": a["reason"],
                    "protected": a.get("protected"),                     # T244: 保护标记必须透传
                    "protection_reason": a.get("protection_reason"),
                    "day": day, "slot": slot})).ok:
                n += 1
        for g in out["consolidate"]:
            if self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
                    "op": "consolidate", "subject": g["subject"],
                    "source_mem_ids": g["source_mem_ids"],
                    "produced_mem_id": f"M-{self.agent_id}-SM-{g['subject']}",
                    "text": g["text"], "day": day, "slot": slot})).ok:
                n += 1
        # T244 W2b: 把 run_sleep_window 产出的 PERSONA_DRIFT 待发事件提交为 intent
        # （op="drift"，由 adapter `_do_memory` 落 PERSONA_DRIFT 事件；无候选/单窗不发）。
        for ev in out.get("events", []):
            if ev.get("type") != "PERSONA_DRIFT":
                continue
            p = dict(ev.get("payload") or {})
            p["op"] = "drift"
            if self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, p)).ok:
                n += 1
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
            "op": "sleep_end", "day": day, "slot": slot, "actual_ticks": planned}))
        return n

    def _current_goal(self) -> str:
        return str(self.persona.goal_tendencies[0].get("kind", "")) if self.persona.goal_tendencies else ""

    # T244 W3: 由**既有**反思（MEMORY_REFLECT 产出）转成**有界**人格漂移候选（不新增 LLM）。
    # T333：情感判定**单一真源**在 `life/emotion.py`（此处仅别名，供既有引用/测试）。
    _DRIFT_POS = E.STRICT_POS
    _DRIFT_NEG = E.STRICT_NEG

    def _reflection_drift_events(self, params: dict, *, day: int, slot: str, window: int) -> list[dict]:
        """把既有反思节点转成**有界**漂移候选（06 §1.2；T244 W3）。

        规则（确定性、**宁缺毋滥**、不新增 LLM 调用）：
          * 仅取 `kind=="reflection"` 且 `importance >= min_importance`（默认 7）；
          * `dim` 由 `sha256(mem_id)` **确定性**映射到大五之一；
          * `delta` 符号由**情感词表**定；**无情感词 → 不产**（不在噪声里乱发）；
          * 每窗口每维至多一条候选；
          * **抖动 vs 真漂移**：某维需**连续 `min_windows`（默认 2）个窗口**被反思信号才发
            `PERSONA_DRIFT`（单窗噪声不发）；发出后该维计数清零（自然冷却）；
          * 幅度 = `±delta_max`（`bounded_update` 再夹一层）。
        """
        pd = params.get("persona_drift", {}) or {}
        min_imp = int(pd.get("min_importance", PD.DEFAULTS["min_importance"]))
        dmax = int(pd.get("delta_max", 1))
        min_windows = int(pd.get("min_windows", PD.DEFAULTS["min_windows"]))
        criterion = str(pd.get("criterion", "natural"))   # T333：strict|natural（默认 natural）
        dims = PD.BIG5_DIMS
        cand: dict[str, tuple[int, str]] = {}          # dim -> (sign, mem_id)
        for n in sorted(self.memory.nodes.values(), key=lambda x: x.mem_id):
            if n.kind != "reflection" or n.importance < min_imp:
                continue
            sign = E.emotion_sign(n.text or "", criterion=criterion)   # 单一真源
            if sign == 0:
                continue
            dim = dims[int(sha256_hex(n.mem_id)[:8], 16) % len(dims)]
            if dim not in cand:                        # 每窗口每维至多一条
                cand[dim] = (sign, n.mem_id)
        evs: list[dict] = []
        for dim in dims:
            if dim in cand:
                sign, mem_id = cand[dim]
                self._drift_streak[dim] = self._drift_streak.get(dim, 0) + 1
                reached = self._drift_streak[dim] >= min_windows
                # T323：每窗每"有候选"维落一条 CANDIDATE（identity fold、non-state）——
                # 让 restore() 可按"连续含候选窗数"**逐维**原样重建 _drift_streak。
                self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
                    "op": "drift_candidate", "dim": dim, "sign": sign, "window": int(window),
                    "mem_id": mem_id, "reached_threshold": bool(reached),
                    "day": day, "slot": slot}))
                if reached:  # 持续 = 真漂移；单窗 = 抖动，不发
                    evs.append({"dim": dim, "delta": sign * dmax, "cause_mem_id": mem_id})
                    self._drift_streak[dim] = 0            # 发出后冷却
            else:
                self._drift_streak[dim] = 0
        return evs

    def _describe_event(self, ev) -> str:
        t, p = ev.type, (ev.payload or {})
        if t == "ACTIVITY_STARTED":
            return f"{ev.actor} 在 {p.get('place')} 开始 {p.get('activity_type')}。"
        if t == "ACTIVITY_COMPLETED":
            return f"{ev.actor} 完成了 {p.get('activity_type')}（{p.get('place')}|{p.get('outcome')}）。"
        if t == "PLACE_ARRIVED":
            return f"{ev.actor} 到达 {p.get('place')}。"
        if t.startswith("MSG_"):
            return f"{ev.actor} 说：{p.get('body', '')}"
        if t == "RELATION_ENCOUNTER":
            return f"{ev.actor} 与 {p.get('b')} 在 {p.get('place')} 相遇。"
        if t == "AGENT_DIED":
            return f"{p.get('agent_id')} 去世了。"
        return f"{ev.actor} 的 {t} 事件。"

    def _score_importance(self, text: str, round_no: int) -> int:
        low = text.lower()
        if not any(k in low for k in ("派对", "救助", "去世", "争吵", "相遇", "party", "help", "died")):
            return 2
        if not getattr(self, "_llm_permit", True):   # T221c: M4 未许可 → 确定性兜底
            return 2
        if m2b_importance_mode() == "discriminative":
            return self._importance_discriminative(text, round_no)
        out = self.llm.call("importance", text,
                            meta={"agent_id": self.agent_id, "round": round_no}).text
        try:
            return clamp(int(out.strip().split()[0]), 1, 10)
        except Exception:
            return 2

    def _importance_discriminative(self, text: str, round_no: int) -> int:
        """M2b：importance 走受限选择（候选 {1..10}+逃生项，单一真源）；关闭时不走此路。"""
        if not getattr(self, "_llm_permit", True):   # T221c: M4 未许可 → 确定性兜底
            return 2
        options = list(C.JUDGMENT_OPTIONS["importance"])
        branch = rng_branch(self.agent_id, "importance", "self", round_no, options)
        jid = f"IMP-{self.agent_id}-{round_no}-{sha256_hex(text)[:8]}"
        try:
            payload, emitted = self.soft.judge(
                judgment_id=jid, dimension="importance", question_ref="importance",
                envelope={"options": options}, rng_branch=branch, parties=[self.agent_id],
                context={"text": text[:200]}, round_no=round_no, mode="discriminative")
            if not emitted:
                self._submit_audit("LLM_JUDGMENT", payload, phase=2)
            return clamp(int(payload.get("resolved", payload["decision"])), 1, 10)
        except Exception:
            return 2
