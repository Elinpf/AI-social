"""PLAN-phase activity-template planner (T49).

Puts the 20 activity templates (`config/activity_templates.json`) into the weekly
plan: for eligible (day_type, slot) it selects a deterministic `template_id` +
`participants`, so the templates actually fire during *natural* runs and the
20-class census can light up.

Discipline:
  * **deterministic** — selection/partners are driven by seeded hashing of
    (agent_id, slot_id); no wall clock, no LLM (RNG decides the branch, per 00 §5.4);
  * **frequency-bounded** — at most one template per (day_type, slot) rule, plus a
    deterministic gate that skips ~1/3 of eligible slots, so event volume stays sane;
  * only life-side facts are used (agent's own cash/needs, peer roster, place open
    slots). Preconditions that need another agent's private state (skill gap,
    affinity) are treated as an *availability proxy*: they gate on having a peer.
"""
from __future__ import annotations

import os

from .util import sha256_hex

# ---------------------------------------------------------------------------
# F-5 生活气息臂（round1）：把「闲」排进作息表 —— 单 env 开关，**默认关 = 逐字节等价**
#
# 口径卡：`<team-workspace>/round1-prereg-F5.md`（公式/阈值先于本文件落盘）。
# 关（`HITT_LIVING_SLOT` 未设/`0`）⇒ `plan_slot` 走与接入前**完全相同**的代码路径，
# 同 seed 同输入产出逐字节相同的计划 ⇒ 可消融。
# 开 ⇒ 只在「闲时段」改一件事：在**既有** eligibility 流程内优先排生活类模板，并跳过
# 1/3 频率门（保证这天真有「闲」）；闲时段之外（含 night、workday 的 morning/afternoon）
# 一字不改 ⇒ 生产性活动占比（口径卡 G3）不受影响。
#
# 闲时段（AMENDMENT-1）：每天 `evening`（下工以后）+ 周末 `afternoon`。
# 生活类候选**全部是 `config/activity_templates.json` 里既有模板**（不新增模板、不改配置
# ⇒ `engine_version` 指纹两臂一致）；`contest` 计两份权重（每周的「比赛」是高光生活事件）。
LIVING_ENV = "HITT_LIVING_SLOT"
_LIVING_CANDIDATES = {
    "evening": ["contest", "contest", "gift", "whisper", "rel_maintain",
                "ice_break", "creative_collab", "select_location"],
    "afternoon": ["select_location", "ice_break", "rel_maintain",
                  "creative_collab", "combat_training"],
}


def living_enabled() -> bool:
    """生活气息臂开关（env `HITT_LIVING_SLOT` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(LIVING_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _living_candidates(day_type: str, slot: str) -> list:
    """当前 (day_type, slot) 是否属于「闲时段」；是则返回生活类候选，否则空列表。

    规则（写死在代码里，可审计）：`evening` 每天都算；`afternoon` 只周末算。
    `night`/`morning`/workday `afternoon` **一律不算**（口径卡 AMENDMENT-1 的理由：
    这些时段被替换会压低生产性活动占比，击破 G3 守卫）。
    """
    if slot == "evening":
        return list(_LIVING_CANDIDATES["evening"])
    if slot == "afternoon" and day_type == "weekend":
        return list(_LIVING_CANDIDATES["afternoon"])
    return []


# (day_type, slot) -> ordered template candidates (by preference). The chosen one
# is picked deterministically per (agent, slot_id), so different days vary.
_WEEK_RULES = [
    ("workday", "morning", ["skill_practice", "mentorship", "job_choice", "combat_training"]),
    ("workday", "afternoon", ["scarce_buy", "savings", "polite_reject", "counter_propose"]),
    ("workday", "evening", ["gift", "rel_maintain", "whisper"]),
    ("weekend", "morning", ["academic_collab", "mentorship", "skill_practice", "combat_training"]),
    ("weekend", "afternoon", ["group_proposal", "creative_collab", "select_location", "power_conflict"]),
    ("weekend", "evening", ["ice_break", "rel_accept", "rel_maintain", "contest",
                            "combat_training", "creative_collab"]),
]
_RULES = {(dt, sl): cands for dt, sl, cands in _WEEK_RULES}

# LLM-decided weekly focus -> preferred template families (T57). The focus is a
# FROZEN label (LLM output), so the resulting plan is logged & replay-stable, yet
# differs between mock and a real LLM (different labels).
FOCUS_OPTIONS = ["work", "social", "study", "leisure", "balance"]
FOCUS_TEMPLATES = {
    "work": {"skill_practice", "mentorship", "job_choice", "savings", "scarce_buy"},
    "social": {"gift", "rel_maintain", "ice_break", "rel_accept", "whisper"},
    "study": {"academic_collab", "mentorship", "skill_practice"},
    "leisure": {"contest", "combat_training", "creative_collab", "select_location"},
    "balance": set(),
}


def _pick(seed: str, options: list):
    if not options:
        return None
    return options[int(sha256_hex(seed)[:8], 16) % len(options)]


class Planner:
    def __init__(self, agent_id: str, templates: dict, peers, places: dict) -> None:
        self.agent_id = agent_id
        self.templates = templates
        self.peers = sorted({p for p in (peers or []) if p and p != agent_id})
        self.places = places or {}

    # ---- eligibility ------------------------------------------------------
    def _open_places(self, tid: str, slot: str) -> list:
        tpl = self.templates[tid]
        return [p for p in tpl["place_allowed"]
                if slot in self.places.get(p, {}).get("open_slots", [])]

    def _self_cash_ok(self, tid: str, cash: int) -> bool:
        for r in self.templates[tid].get("preconditions", {}).get("resource", []) or []:
            if r.get("who") in ("self", None) and r.get("kind") == "cash" and r.get("op") == ">=":
                if int(cash) < int(r.get("val", 0)):
                    return False
        return True

    def _participants(self, tid: str, slot_id: str) -> list | None:
        tpl = self.templates[tid]
        mn = int(tpl["participants"]["min"])
        mx = int(tpl["participants"]["max"])
        need = max(0, mn - 1)
        if need > len(self.peers):
            return None
        k = need if mx <= mn else min(mx - 1, len(self.peers))
        chosen: list[str] = []
        for i in range(k):
            rem = [p for p in self.peers if p not in chosen]
            if not rem:
                break
            chosen.append(_pick(f"{self.agent_id}|{slot_id}|{tid}|p{i}", rem))
        if len(chosen) < need:
            return None
        return [self.agent_id] + chosen

    # ---- public -----------------------------------------------------------
    def _eligible(self, cands: list, slot: str, slot_id: str, cash: int) -> list:
        """按既有 eligibility 流程筛选候选（顺序与内容与接入前逐字一致）。

        只做「模板存在 / 时段允许 / 场所在该时段开放 / 本人现金前置 / 人数够」五项；
        需要他人私有状态的前置（技能差、好感度）仍按 docstring 的 availability proxy 处理。
        """
        eligible = []
        for tid in cands:
            if tid not in self.templates:
                continue
            tpl = self.templates[tid]
            if slot not in tpl["slot_allowed"]:
                continue
            places = self._open_places(tid, slot)
            if not places:
                continue
            if not self._self_cash_ok(tid, cash):
                continue
            parts = self._participants(tid, slot_id)
            if parts is None:
                continue
            eligible.append((tid, sorted(places), parts))
        return eligible

    def _materialize(self, pick: tuple, slot_id: str) -> dict:
        """(template_id, 可选场所, 参与者) → 计划项（场所由 sha256 确定性选取）。"""
        tid, places, parts = pick
        tpl = self.templates[tid]
        place = _pick(f"{self.agent_id}|{slot_id}|place", places)
        return {"activity_type": tpl["activity_type"], "place": place,
                "template_id": tid, "participants": parts}

    def plan_slot(self, day_type: str, slot: str, slot_id: str, cash: int,
                  focus: str | None = None) -> dict | None:
        cands = _RULES.get((day_type, slot))
        if not cands:
            return None
        # F-5 生活气息臂（默认关）：闲时段优先排生活类活动，并跳过 1/3 频率门。
        # 关闭时本块整段不执行 ⇒ 下面走与接入前逐字相同的路径。
        if living_enabled():
            living = _living_candidates(day_type, slot)
            if living:
                elig_living = self._eligible(living, slot, slot_id, cash)
                if elig_living:      # 没有可排的生活类 ⇒ 回落到原路径（不静默丢 slot）
                    return self._materialize(
                        _pick(f"{self.agent_id}|{slot_id}|living", elig_living), slot_id)
        # LLM-decided focus biases the candidate order (structure follows LLM output,
        # per T57); the actual pick among eligible is still deterministic.
        if focus and focus in FOCUS_TEMPLATES and focus != "balance":
            pref = FOCUS_TEMPLATES[focus]
            cands = sorted(cands, key=lambda t: (t not in pref, cands.index(t)))
        # deterministic frequency gate: skip ~1/3 of eligible slots
        if int(sha256_hex(f"{self.agent_id}|{slot_id}|gate")[:2], 16) % 3 == 0:
            return None
        eligible = self._eligible(cands, slot, slot_id, cash)
        if not eligible:
            return None
        # if the focus names a family that is eligible here, choose it (deterministic,
        # LLM-driven); otherwise fall back to the seeded pick.
        if focus and focus in FOCUS_TEMPLATES and focus != "balance":
            pref = FOCUS_TEMPLATES[focus]
            focused = [e for e in eligible if e[0] in pref]
            if focused:
                return self._materialize(focused[0], slot_id)
        return self._materialize(_pick(f"{self.agent_id}|{slot_id}", eligible), slot_id)
