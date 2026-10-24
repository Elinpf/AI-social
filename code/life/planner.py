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

from .util import sha256_hex

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


def place_affinity_weight(count: int, alpha: float) -> float:
    """D2.3 权重（**纯函数，写死口径**）：`w(peer) = 1 + alpha * count`。

    `count` = 该居民在 `place` 下与该 peer 的**双向**共现次数（自己发的 + 别人发给自己的）；
    `alpha=0` ⇒ `w ≡ 1` ⇒ 与"等权映射（C 档）"逐字节等价（用于隔离映射伪影）。
    """
    return 1.0 + float(alpha) * max(0, int(count))


def _weighted_pick(seed: str, options: list, weights: list):
    """累积权重轴取点（确定性）：`u = sha256(seed)[:8] / 2**32 * sum(w)`，落轴即取。

    与离线工具 `tools/d21/d22_place_feasibility.py::axis_pick` **同一映射**（w≡1 时逐字节等价）。
    """
    if not options:
        return None
    if len(options) != len(weights):
        raise ValueError("options 与 weights 长度不一致")
    total = float(sum(weights))
    if total <= 0:
        return _pick(seed, options)
    u = (int(sha256_hex(seed)[:8], 16) / float(1 << 32)) * total
    acc = 0.0
    for opt, w in zip(options, weights):
        acc += float(w)
        if u < acc:
            return opt
    return options[-1]


class Planner:
    def __init__(self, agent_id: str, templates: dict, peers, places: dict,
                 place_peer_counts: dict | None = None, place_affinity_alpha: float = 3) -> None:
        self.agent_id = agent_id
        self.templates = templates
        self.peers = sorted({p for p in (peers or []) if p and p != agent_id})
        self.places = places or {}
        # D2.3：**只读**地点亲和快照 `{place: {peer: count}}`；None ⇒ 完全不启用（原路径逐字节不变）
        self.place_peer_counts = place_peer_counts or None
        self.place_alpha = place_affinity_alpha

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

    def _participants(self, tid: str, slot_id: str, place: str | None = None) -> list | None:
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
            seed = f"{self.agent_id}|{slot_id}|{tid}|p{i}"
            if place is None or self.place_peer_counts is None:
                chosen.append(_pick(seed, rem))
            else:
                counts = self.place_peer_counts.get(place, {}) or {}
                weights = [place_affinity_weight(counts.get(p, 0), self.place_alpha) for p in rem]
                chosen.append(_weighted_pick(seed, rem, weights))
        if len(chosen) < need:
            return None
        return [self.agent_id] + chosen

    # ---- public -----------------------------------------------------------
    def plan_slot(self, day_type: str, slot: str, slot_id: str, cash: int,
                  focus: str | None = None) -> dict | None:
        cands = _RULES.get((day_type, slot))
        if not cands:
            return None
        # LLM-decided focus biases the candidate order (structure follows LLM output,
        # per T57); the actual pick among eligible is still deterministic.
        if focus and focus in FOCUS_TEMPLATES and focus != "balance":
            pref = FOCUS_TEMPLATES[focus]
            cands = sorted(cands, key=lambda t: (t not in pref, cands.index(t)))
        # deterministic frequency gate: skip ~1/3 of eligible slots
        if int(sha256_hex(f"{self.agent_id}|{slot_id}|gate")[:2], 16) % 3 == 0:
            return None
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
            # D2.3：place 由独立种子决定（与 participants 无关）⇒ 提前算不改 place 分布
            place_guess = _pick(f"{self.agent_id}|{slot_id}|place", sorted(places))
            parts = self._participants(
                tid, slot_id, place_guess if self.place_peer_counts is not None else None)
            if parts is None:
                continue
            eligible.append((tid, sorted(places), parts))
        if not eligible:
            return None
        # if the focus names a family that is eligible here, choose it (deterministic,
        # LLM-driven); otherwise fall back to the seeded pick.
        if focus and focus in FOCUS_TEMPLATES and focus != "balance":
            pref = FOCUS_TEMPLATES[focus]
            focused = [e for e in eligible if e[0] in pref]
            if focused:
                tid, places, parts = focused[0]
                place = _pick(f"{self.agent_id}|{slot_id}|place", places)
                tpl = self.templates[tid]
                return {"activity_type": tpl["activity_type"], "place": place,
                        "template_id": tid, "participants": parts}
        tid, places, parts = _pick(f"{self.agent_id}|{slot_id}", eligible)
        tpl = self.templates[tid]
        place = _pick(f"{self.agent_id}|{slot_id}|place", places)
        return {"activity_type": tpl["activity_type"], "place": place,
                "template_id": tid, "participants": parts}
