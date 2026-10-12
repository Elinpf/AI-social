"""语义事件普查（L2 层，20 类，15-event-census-spec §1/§2）。

判定式**只读日志、`llm_calls==0`**；`[F]` 项只读 `LLM_JUDGMENT.frozen`、
单列 `emergence_soft`，**绝不进入判定/门禁**。

返回：`semantic_hits`（20 行 hit/first_round/participants/count）+ `miss_list`
+ `soft`（F 类冻结判定计数）。
"""

from __future__ import annotations

from contracts.actors import is_agent_actor

from .folds import (
    familiarity, relation_weights, same_skill, skill_levels,
)
from .params import EmergenceParams, DEFAULT_PARAMS

# 20 类语义事件顺序（T14 E1–E20）
SEMANTIC_EVENT_ORDER = [
    "E1_mentorship", "E2_gift_giving", "E3_combat_training", "E4_creative_collab",
    "E5_saving_money", "E6_whispered_comm", "E7_emotion_burnout", "E8_diff_scoring",
    "E9_scarcity_buy", "E10_skill_practice", "E11_polite_rejection",
    "E12_passion_vs_salary", "E13_group_proposal", "E14_academic_collab",
    "E15_counter_propose", "E16_select_location", "E17_power_conflict",
    "E18_rel_acceptance", "E19_ice_breaking", "E20_rel_maintenance",
]

# 07/15 标记的「难触发项」
HARD_TO_TRIGGER = ["E4_creative_collab", "E8_diff_scoring",
                   "E12_passion_vs_salary", "E13_group_proposal", "E17_power_conflict"]


def _tpl(p) -> str:
    return str(p.get("template") or p.get("activity_type") or p.get("kind") or "")


def _participants(p) -> set:
    from .folds import _iter_ids
    ps = set(_iter_ids(p.get("participants")))
    for k in ("from", "to", "a", "b", "agent_id", "parties"):
        ps.update(_iter_ids(p.get(k)))
    return {x for x in ps if isinstance(x, str) and x}


class _Acc:
    """单语义事件累加器（determinstic）。"""

    def __init__(self):
        self.count = 0
        self.first = None
        self.parts = set()
        self._keys = set()

    def hit(self, round_no, parts, key=None):
        if key is not None:
            if key in self._keys:
                return
            self._keys.add(key)
        self.count += 1
        if self.first is None or round_no < self.first:
            self.first = int(round_no)
        for p in parts:
            if p:
                self.parts.add(p)

    def to_dict(self):
        return {
            "hit": self.count > 0,
            "first_round": self.first,
            "participants": len(self.parts),
            "count": self.count,
        }


def semantic_census(records, params: EmergenceParams | None = None) -> dict:
    params = params or DEFAULT_PARAMS.emergence
    acc = {k: _Acc() for k in SEMANTIC_EVENT_ORDER}
    wmap = relation_weights(records)
    lv = skill_levels(records)
    aff_tl = _build_affinity_timeline(records)

    # 预索引
    def of(t):
        return [r for r in records if r["type"] == t]

    # E1 Mentorship
    mentor_acts = {}
    for r in of("ACTIVITY_COMPLETED"):
        p = r.get("payload") or {}
        if _tpl(p) == "mentorship":
            for pair in _pairs(_participants(p)):
                mentor_acts[pair] = mentor_acts.get(pair, 0) + 1
    for (a, b) in sorted(mentor_acts):
        if not same_skill(lv, a, b):
            continue
        # 技能级差
        la = _max_skill(lv, a)
        lb = _max_skill(lv, b)
        if abs(la - lb) >= params.skill_gap_mentor and familiarity(wmap, a, b) >= params.epsilon:
            if mentor_acts[(a, b)] >= 2:
                acc["E1_mentorship"].hit(_first_round(records, "ACTIVITY_COMPLETED"),
                                        {a, b}, key=(a, b))

    # E2 Gift-giving（affinity 取转账发生时点，前缀折叠）
    for r in of("TRANSFER"):
        p = r.get("payload") or {}
        reason = str(p.get("reason") or p.get("memo") or "")
        frm, to = p.get("from"), p.get("to")
        if "gift" in reason and frm and to and \
                _affinity_at_tl(aff_tl, frm, to, int(r["seq"])) >= params.epsilon_strong:
            acc["E2_gift_giving"].hit(r["round"], {frm, to}, key=(frm, to, r["seq"]))

    # E3 Combat Training
    for r in of("ACTIVITY_STARTED"):
        if _tpl(r.get("payload") or {}) == "combat_training":
            acc["E3_combat_training"].hit(r["round"], _participants(r.get("payload") or {}),
                                          key=r["seq"])
    for r in of("CONFLICT_RESOLVED"):
        if (r.get("payload") or {}).get("rule_ref") == "training":
            acc["E3_combat_training"].hit(r["round"], _participants(r.get("payload") or {}),
                                          key=("cr", r["seq"]))

    # E4 Creative Collab
    has_skill_output = bool(of("SKILL_OUTPUT"))
    for r in of("ACTIVITY_COMPLETED"):
        p = r.get("payload") or {}
        if _tpl(p) == "creative_collab" and len(_participants(p)) >= 2 and has_skill_output:
            acc["E4_creative_collab"].hit(r["round"], _participants(p), key=r["seq"])

    # E5 Saving Money
    for r in of("DEPOSIT") + of("WITHDRAW"):
        p = r.get("payload") or {}
        acc["E5_saving_money"].hit(r["round"], {p.get("agent_id")}, key=r["seq"])
    for r in of("TRANSFER"):
        p = r.get("payload") or {}
        to = p.get("to")
        if to and str(to).upper() in ("BANK", "SYSTEM"):
            acc["E5_saving_money"].hit(r["round"], {p.get("from")}, key=r["seq"])

    # E6 Whispered Comm
    for r in of("MSG_DM"):
        p = r.get("payload") or {}
        if p.get("visibility") == "private":
            frm, to = p.get("from"), p.get("to")
            if frm and to and _affinity_at_tl(aff_tl, frm, to, int(r["seq"])) >= params.epsilon:
                acc["E6_whispered_comm"].hit(r["round"], {frm, to}, key=(frm, to, r["seq"]))

    # E7 Emotion Burnout（T248：非 Agent 主体 agent_id 不得当居民，复用 contracts.actors）
    cons: dict[str, int] = {}
    for r in sorted(records, key=lambda x: x["seq"]):
        if r["type"] in ("NEED_UPDATE", "NEEDS_UPDATE"):
            p = r.get("payload") or {}
            aid = p.get("agent_id")
            if not is_agent_actor(aid):
                continue
            dim = p.get("dim")
            after = p.get("after")
            if dim in ("energy", "leisure") and after is not None:
                if float(after) < params.theta_dep:
                    cons[aid] = cons.get(aid, 0) + 1
                    if cons[aid] >= params.w_burn:
                        acc["E7_emotion_burnout"].hit(r["round"], {aid}, key=aid)
                else:
                    cons[aid] = 0
        elif r["type"] == "STATE_CHANGE":
            p = r.get("payload") or {}
            if p.get("to") == "exhausted" and is_agent_actor(p.get("agent_id")):
                acc["E7_emotion_burnout"].hit(r["round"], {p.get("agent_id")}, key=("sc", r["seq"]))

    # E8 Diff Scoring
    posted = {c for r in of("SCORE_POSTED")
              for c in [(r.get("payload") or {}).get("contest_id")]}
    ranked = {c for r in of("RANKING_EMITTED")
              for c in [(r.get("payload") or {}).get("contest_id")]}
    for c in sorted(posted & ranked, key=str):
        if c is not None:
            acc["E8_diff_scoring"].hit(_first_round(records, "SCORE_POSTED"), set(), key=c)

    # E9 Scarcity Buy（08 §1.2-N：MARKET_TRADE.scarcity_index 为 0–100 整数；缺失=未知，保守不计）
    for r in of("MARKET_TRADE"):
        p = r.get("payload") or {}
        si = p.get("scarcity_index")
        if si is not None and float(si) >= float(params.theta_scarce):
            acc["E9_scarcity_buy"].hit(r["round"], _participants(p), key=r["seq"])

    # E10 Skill Practice
    for r in of("SKILL_PRACTICE"):
        p = r.get("payload") or {}
        acc["E10_skill_practice"].hit(r["round"], {p.get("agent_id")},
                                      key=(p.get("agent_id"), p.get("skill_id"), r["seq"]))

    # E11 Polite Rejection
    rejected_intents = set()
    for r in of("INTENT_REJECTED"):
        p = r.get("payload") or {}
        if p.get("offer_id") is not None:
            rejected_intents.add((r["round"], p.get("offer_id")))
    for r in of("OFFER_REJECTED"):
        p = r.get("payload") or {}
        oid = p.get("offer_id")
        if (r["round"], oid) not in rejected_intents:
            acc["E11_polite_rejection"].hit(r["round"], {p.get("by")}, key=(oid, r["seq"]))

    # E12 Passion vs Salary
    job_offers = {r["round"] for r in of("OFFER_CREATED")
                  if str((r.get("payload") or {}).get("kind")) == "job"}
    for r in of("ROLE_CHANGE"):
        p = r.get("payload") or {}
        if job_offers or p.get("utility_conflict") or str(p.get("cause")) == "preference":
            acc["E12_passion_vs_salary"].hit(r["round"], {p.get("agent_id")}, key=r["seq"])

    # E13 Group Proposal
    proposed = {r["payload"].get("norm_id") for r in of("NORM_PROPOSED") if r.get("payload")}
    for r in of("NORM_ADOPTED"):
        p = r.get("payload") or {}
        nid = p.get("norm_id")
        sup = p.get("support_count", p.get("threshold_used"))
        if nid in proposed:
            acc["E13_group_proposal"].hit(r["round"], set(p.get("adopters") or []), key=nid)

    # E14 Academic Collab
    has_gain = bool(of("SKILL_LEVEL_UP") or of("SKILL_OUTPUT"))
    for r in of("ACTIVITY_COMPLETED"):
        p = r.get("payload") or {}
        if _tpl(p) == "academic_collab" and len(_participants(p)) >= 2 and has_gain:
            acc["E14_academic_collab"].hit(r["round"], _participants(p), key=r["seq"])

    # E15 Counter-propose
    for r in of("OFFER_COUNTERED"):
        p = r.get("payload") or {}
        rn = p.get("round_no", 0)
        if rn is not None and int(rn) <= params.n_round:
            acc["E15_counter_propose"].hit(r["round"], {p.get("by")},
                                           key=(p.get("offer_id"), r["seq"]))

    # E16 Select Location
    for r in of("PLACE_MOVE"):
        p = r.get("payload") or {}
        acc["E16_select_location"].hit(r["round"], {p.get("agent_id")}, key=r["seq"])

    # E17 Power Conflict
    started = {r["payload"].get("conflict_id") for r in of("CONFLICT_STARTED") if r.get("payload")}
    for r in of("CONFLICT_RESOLVED"):
        p = r.get("payload") or {}
        cid = p.get("conflict_id")
        if cid in started and p.get("winner") is not None:
            acc["E17_power_conflict"].hit(r["round"], _participants(p), key=cid)

    # E18 Rel Acceptance（D 部分：affinity 跨 ε_strong；F 部分单列 soft）
    for r in sorted(records, key=lambda x: x["seq"]):
        if r["type"] != "RELATION_CHANGE":
            continue
        p = r.get("payload") or {}
        if p.get("dim") == "affinity" and p.get("after") is not None:
            if abs(float(p["after"])) >= params.epsilon_strong:
                acc["E18_rel_acceptance"].hit(r["round"], {p.get("from"), p.get("to")},
                                              key=(p.get("from"), p.get("to")))

    # E19 Ice-breaking：首次 RELATION_ENCOUNTER{a,b} ∧ familiarity<ε ∧ 存在 MSG_{a↔b}
    pairs_with_msg: set = set()
    for r in records:
        if r["type"] in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            p = r.get("payload") or {}
            frm, to = p.get("from"), p.get("to")
            if frm and to and frm != to:
                pairs_with_msg.add(tuple(sorted((frm, to))))
    seen_enc: set = set()
    for r in sorted(records, key=lambda x: x["seq"]):
        if r["type"] != "RELATION_ENCOUNTER":
            continue
        p = r.get("payload") or {}
        a_, b_ = p.get("a"), p.get("b")
        if not (a_ and b_) or a_ == b_:
            continue
        pair = tuple(sorted((a_, b_)))
        if pair in seen_enc:
            continue
        seen_enc.add(pair)
        if _familiarity_at_tl(aff_tl, a_, b_, int(r["seq"])) < params.epsilon \
                and pair in pairs_with_msg:
            acc["E19_ice_breaking"].hit(r["round"], {a_, b_}, key=pair)

    # E20 Rel Maintenance
    last_inter: dict[tuple, int] = {}
    for r in sorted(records, key=lambda x: x["seq"]):
        if r["type"] in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP", "RELATION_ENCOUNTER"):
            p = r.get("payload") or {}
            for pair in _pairs([p.get("from"), p.get("to"), p.get("a"), p.get("b")]):
                last_inter[pair] = int(r["round"])
        elif r["type"] == "RELATION_CHANGE":
            p = r.get("payload") or {}
            pair = tuple(sorted((p.get("from"), p.get("to"))))
            if None not in pair and p.get("from") != p.get("to"):
                last = last_inter.get(pair)
                if last is not None and int(r["round"]) - last > params.d_maint:
                    acc["E20_rel_maintenance"].hit(r["round"], set(pair), key=(pair, r["seq"]))

    hits = {k: acc[k].to_dict() for k in SEMANTIC_EVENT_ORDER}
    miss = [k for k in SEMANTIC_EVENT_ORDER if not hits[k]["hit"]]
    return {
        "semantic_hits": hits,
        "miss_list": miss,
        "soft": soft_judgment_counts(records),
    }


def _pairs(items):
    xs = sorted({x for x in items if x})
    out = []
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            out.append((xs[i], xs[j]))
    return out


def _max_skill(lv, a):
    vals = [v for (ag, s), v in lv.items() if ag == a]
    return max(vals) if vals else 0.0


def _build_affinity_timeline(records) -> dict:
    """(from,to) -> [(seq, after)]，按 seq 升序（一次性预计算，避免 O(n²)）。"""
    tl: dict[tuple, list] = {}
    for r in sorted(records, key=lambda x: x["seq"]):
        if r["type"] != "RELATION_CHANGE":
            continue
        p = r.get("payload") or {}
        if p.get("dim") == "affinity" and p.get("after") is not None:
            tl.setdefault((p.get("from"), p.get("to")), []).append((int(r["seq"]), float(p["after"])))
    return tl


def _affinity_at_tl(tl: dict, frm, to, seq) -> float:
    """(frm→to) 的 affinity 在事件 seq 之前（含）的最后折叠值（二分）。"""
    import bisect
    arr = tl.get((frm, to))
    if not arr:
        return 0.0
    i = bisect.bisect_right(arr, (seq, float("inf"))) - 1
    return arr[i][1] if i >= 0 else 0.0


def _familiarity_at_tl(tl: dict, a_, b_, seq) -> float:
    return max(_affinity_at_tl(tl, a_, b_, seq), _affinity_at_tl(tl, b_, a_, seq))


def _affinity_at_seq(records, frm, to, seq) -> float:
    """兼容入口（单次查询）；批量场景请用 `_build_affinity_timeline` + `_affinity_at_tl`。"""
    return _affinity_at_tl(_build_affinity_timeline(records), frm, to, seq)


def _familiarity_at_seq(records, a_, b_, seq) -> float:
    return max(_affinity_at_seq(records, a_, b_, seq),
               _affinity_at_seq(records, b_, a_, seq))


def _first_round(records, type_):
    rs = [int(r["round"]) for r in records if r["type"] == type_]
    return min(rs) if rs else None


def soft_judgment_counts(records) -> dict:
    """F 类：只读 LLM_JUDGMENT.frozen 的冻结判定计数（不重问 LLM）。"""
    by_dim: dict[str, int] = {}
    by_dim_decision: dict[str, dict] = {}
    frozen_refs: list = []
    for r in records:
        if r["type"] != "LLM_JUDGMENT":
            continue
        p = r.get("payload") or {}
        if p.get("frozen") is not True:
            continue
        dim = p.get("dimension")
        by_dim[dim] = by_dim.get(dim, 0) + 1
        dec = str(p.get("decision"))
        by_dim_decision.setdefault(dim, {})
        by_dim_decision[dim][dec] = by_dim_decision[dim].get(dec, 0) + 1
        frozen_refs.append({"judgment_id": p.get("judgment_id"), "dimension": dim,
                            "decision": p.get("decision"), "model": p.get("model"),
                            "context_digest": p.get("context_digest")})
    return {
        "basis": "F",
        "source": "frozen_llm",
        "counts_by_dimension": {k: by_dim[k] for k in sorted(by_dim)},
        "decisions_by_dimension": {
            k: {kk: by_dim_decision[k][kk] for kk in sorted(by_dim_decision[k])}
            for k in sorted(by_dim_decision)
        },
        "frozen_ref": frozen_refs,
        "contains_llm_judgment": bool(by_dim),
    }


__all__ = ["semantic_census", "soft_judgment_counts", "SEMANTIC_EVENT_ORDER", "HARD_TO_TRIGGER"]
