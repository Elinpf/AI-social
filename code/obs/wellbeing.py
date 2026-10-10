"""幸福感 / 生活质量指标（W1–W7，13-wellbeing-metrics）。

- `metrics.wellbeing`（D 类）：W1/W4/W5/W6 全量 + W2/W7 的确定性代理；
- `metrics.wellbeing_soft`（F 类）：W3 主观满足、W2 互评、W7 meaning——只读冻结
  `LLM_JUDGMENT`，**仅描述/敏感性，不进判定与门禁**。

激励层（经济机制）与观测层（W1–W7）分离；**禁止合成单一分数优化**。
"""

from __future__ import annotations

from . import emergence as _em
from .census import soft_judgment_counts
from .econ import fold_economy, gini
from .folds import affinity, agents, alive_agents, familiarity, relation_weights
from .life import need_metrics
from .params import WellbeingParams, DEFAULT_PARAMS


def _pct_rank(sorted_vals: list, v: float) -> float:
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    below = sum(1 for x in sorted_vals if x < v)
    return round(below / n, 6)


def wellbeing_metrics(records, params: WellbeingParams | None = None) -> dict:
    params = params or DEFAULT_PARAMS.wellbeing
    eco = fold_economy(records)
    wmap = relation_weights(records)
    alive = alive_agents(records)
    cash = eco["cash"]

    net_worth = {a: cash.get(a, 0) - _liab(eco, a) for a in sorted(set(list(cash) + alive))}
    nw_vals = sorted(net_worth.values())

    # W1 经济状况（派生展示）
    w1 = {}
    metabolism_rounds = _metabolism_burn(records)
    per_round_burn = metabolism_rounds.get("__per_round__", 0)
    for a in sorted(net_worth):
        w1[a] = {
            "net_worth": int(net_worth[a]),
            "wealth_percentile": _pct_rank(nw_vals, net_worth[a]),
            "income_weekly": int(_income_weekly(records, a)),
            "consumption_weekly": int(_consumption_weekly(records, a)),
            "financial_security_rounds": round(
                max(0, cash.get(a, 0)) / per_round_burn, 6) if per_round_burn else 0.0,
        }

    # W2 社会地位（D 部分）
    pr = {e["agent_id"]: e for e in _em.relation_metrics(records, DEFAULT_PARAMS.emergence)["pagerank_top"]}
    incoming_strong = {}
    for (a, b, dim), v in wmap.items():
        if a and b and abs(float(v)) >= DEFAULT_PARAMS.emergence.epsilon_strong:
            incoming_strong[b] = incoming_strong.get(b, 0) + 1
    cited = _cited_counts(records)
    w2 = {}
    for a in sorted(set(pr) | set(alive)):
        w2[a] = {
            "pagerank_rank": pr.get(a, {}).get("rank"),
            "incoming_strong_ties": incoming_strong.get(a, 0),
            "cited_count": cited.get(a, 0),
            "governance_influence": _governance_influence(records, a),
        }

    # W4 健康（D）
    need = need_metrics(records)["dims"]
    clinic = _place_activity_counts(records, "clinic")
    w4 = {}
    for a in sorted(alive):
        hl = _last_need(records, a, "health")
        en = _last_need(records, a, "energy")
        w4[a] = {
            "health_level": hl,
            "energy_level": en,
            "clinic_visits": clinic.get(a, 0),
            "health_deprivation": bool(hl is not None and hl < params.theta_dep),
        }

    # W5 关系质量（D）
    w5 = {}
    for a in sorted(alive):
        strong = 0
        recip = 0
        aff_sum = 0.0
        deg = 0
        for (frm, to, dim), v in wmap.items():
            if frm != a:
                continue
            deg += 1
            if abs(float(v)) >= DEFAULT_PARAMS.emergence.epsilon_strong:
                strong += 1
            aff_sum += affinity(wmap, a, to)
            if abs(affinity(wmap, to, a)) >= DEFAULT_PARAMS.emergence.epsilon:
                recip += 1
        w5[a] = {
            "strong_ties": strong,
            "reciprocity": round(recip / deg, 6) if deg else 0.0,
            "mean_affinity": round(aff_sum / deg, 6) if deg else 0.0,
            "isolation_flag": deg == 0,
        }

    # W6 技能/成长（D）
    w6 = _skill_growth(records, alive)

    # W7 自主/意义（D 代理）
    w7 = _autonomy(records, alive)

    # 背离检测（D）
    divergence = _divergence(records, net_worth, w1, w4, w5, w6, w7, params)

    summary = {
        "n_alive": len(alive),
        "gini_net_worth": gini(list(net_worth.values())),
        "mean_net_worth": round(sum(net_worth.values()) / len(net_worth), 6) if net_worth else 0.0,
        "wellbeing_vector_keys": ["W1", "W2", "W3", "W4", "W5", "W6", "W7"],
        "divergence_count": divergence["divergence_count"],
    }

    return {
        "W1_economy": w1,
        "W2_social_status_D": w2,
        "W4_health": w4,
        "W5_relation_quality": w5,
        "W6_skill_growth": w6,
        "W7_autonomy_meaning_D": w7,
        "divergence": divergence,
        "summary": summary,
        "llm_judged_metric_count": 0,
    }


def wellbeing_soft(records) -> dict:
    """F 类：主观满足 W3、互评 W2、意义 W7——只读冻结判定。"""
    soft = soft_judgment_counts(records)
    subj = soft["decisions_by_dimension"].get("satisfaction", {})
    respect = soft["decisions_by_dimension"].get("respect_score", {})
    affection = soft["decisions_by_dimension"].get("affection_score", {})
    meaning = soft["decisions_by_dimension"].get("meaning", {})
    return {
        "subjective_satisfaction": subj,
        "social_status_llm": {"respect": respect, "affection": affection},
        "meaning_score": meaning,
        "basis": "F",
        "source": "frozen_llm",
        "contains_llm_judgment": soft["contains_llm_judgment"],
        "frozen_ref": soft["frozen_ref"],
    }


# ─────────────────────────── 辅助 ───────────────────────────

def _liab(eco, a) -> int:
    return sum(int(l.get("outstanding", 0)) for l in eco["loans"].values()
               if l.get("borrower") == a and l.get("status") in ("active", "overdue"))


def _metabolism_burn(records) -> dict:
    total = 0
    rounds = set()
    for r in records:
        if r["type"] == "METABOLISM":
            total += int((r.get("payload") or {}).get("amount", 0))
            rounds.add(int(r["round"]))
    d = {"total": total}
    if rounds:
        d["__per_round__"] = round(total / len(rounds), 6)
    return d


def _income_weekly(records, a) -> int:
    return sum(int((r.get("payload") or {}).get("amount", 0))
               for r in records if r["type"] in ("TRANSFER", "MARKET_TRADE")
               and _recipient(r) == a)


def _consumption_weekly(records, a) -> int:
    return sum(int((r.get("payload") or {}).get("amount", 0))
               for r in records if r["type"] in ("TRANSFER", "MARKET_TRADE")
               and _payer(r) == a)


def _payer(r):
    p = r.get("payload") or {}
    return p.get("from") if r["type"] == "TRANSFER" else p.get("buyer")


def _recipient(r):
    p = r.get("payload") or {}
    return p.get("to") if r["type"] == "TRANSFER" else p.get("seller")


def _cited_counts(records) -> dict:
    out: dict[str, int] = {}
    for r in records:
        if r["type"] in ("MSG_PUBLIC", "MSG_DM", "MSG_GROUP"):
            p = r.get("payload") or {}
            cites = p.get("cited_agent")
            if cites:
                out[cites] = out.get(cites, 0) + 1
            for c in (p.get("cited") or []):
                out[c] = out.get(c, 0) + 1
    return out


def _governance_influence(records, a) -> float:
    proposed = 0
    adopted = 0
    for r in records:
        p = r.get("payload") or {}
        if r["type"] == "NORM_PROPOSED" and p.get("proposer") == a:
            proposed += 1
        if r["type"] == "NORM_ADOPTED" and a in (p.get("adopters") or []):
            adopted += 1
    return round(adopted / proposed, 6) if proposed else 0.0


def _last_need(records, a, dim):
    val = None
    for r in sorted(records, key=lambda x: x["seq"]):
        if r["type"] not in ("NEED_UPDATE", "NEEDS_UPDATE"):
            continue
        p = r.get("payload") or {}
        if p.get("agent_id") == a and p.get("dim") == dim and p.get("after") is not None:
            val = round(float(p["after"]), 6)
    return val


def _place_activity_counts(records, place) -> dict:
    out: dict[str, int] = {}
    for r in records:
        if r["type"] not in ("ACTIVITY_STARTED", "ACTIVITY_COMPLETED"):
            continue
        p = r.get("payload") or {}
        if p.get("place") == place:
            a = p.get("agent_id")
            out[a] = out.get(a, 0) + 1
    return out


def _skill_growth(records, alive) -> dict:
    gains: dict[str, float] = {}
    practice: dict[str, int] = {}
    for r in records:
        p = r.get("payload") or {}
        if r["type"] == "SKILL_LEVEL_UP":
            before = p.get("level_before")
            after = p.get("level_after")
            if before is not None and after is not None:
                gains[p.get("agent_id")] = gains.get(p.get("agent_id"), 0.0) + (float(after) - float(before))
        elif r["type"] == "SKILL_PRACTICE":
            practice[p.get("agent_id")] = practice.get(p.get("agent_id"), 0) + 1
    out = {}
    for a in sorted(alive):
        out[a] = {"skill_gain": round(gains.get(a, 0.0), 6),
                  "practice_count": practice.get(a, 0)}
    return out


def _autonomy(records, alive) -> dict:
    planned = 0
    activities = 0
    self_goal = 0
    goals = 0
    types: dict[str, int] = {}
    for r in records:
        p = r.get("payload") or {}
        if r["type"] == "SCHEDULE_PLANNED":
            planned += len(p.get("slots") or [])
        elif r["type"] == "ACTIVITY_STARTED":
            activities += 1
            t = p.get("activity_type")
            types[t] = types.get(t, 0) + 1
        elif r["type"] == "GOAL_SET":
            goals += 1
            if str(p.get("kind")) in ("self", "intrinsic", "personal"):
                self_goal += 1
    # 归一化活动多样性熵
    total = sum(types.values())
    import math
    ent = 0.0
    for v in types.values():
        p_ = v / total
        if p_ > 0:
            ent -= p_ * math.log(p_)
    max_ent = math.log(len(types)) if len(types) > 1 else 0.0
    return {
        "autonomy_ratio": round(planned / activities, 6) if activities else 0.0,
        "activity_diversity": round(ent / max_ent, 6) if max_ent else 0.0,
        "self_goal_rate": round(self_goal / goals, 6) if goals else 0.0,
    }


def _divergence(records, net_worth, w1, w4, w5, w6, w7, params) -> dict:
    """背离计数（D）：sign(Δecon) ≠ sign(Δwellbeing_D) 的 Agent 比例。"""
    nw_vals = sorted(net_worth.values())

    def wealth_pct(a):
        return _pct_rank(nw_vals, net_worth[a]) if a in net_worth else 0.0

    cases = {"rich_unhappy": 0, "poor_but_rich_relations": 0, "growth_stalled": 0}
    counted = 0
    for a in sorted(net_worth):
        wp = wealth_pct(a)
        w4a = w4.get(a, {})
        w5a = w5.get(a, {})
        w6a = w6.get(a, {})
        rich_unhappy = wp >= params.wealth_high_pct and (
            w4a.get("health_deprivation") or w5a.get("isolation_flag"))
        poor_rich = wp <= params.wealth_low_pct and (
            (w5a.get("strong_ties", 0) >= 2) or w7.get("activity_diversity", 0) >= 0.5)
        stalled = (w6a.get("skill_gain", 0.0) == 0.0) and w1.get(a, {}).get(
            "financial_security_rounds", 0) > 0
        if rich_unhappy:
            cases["rich_unhappy"] += 1
        if poor_rich:
            cases["poor_but_rich_relations"] += 1
        if stalled:
            cases["growth_stalled"] += 1
        if rich_unhappy or poor_rich or stalled:
            counted += 1
    n = len(net_worth) or 1
    return {
        "divergence_count": counted,
        "divergence_rate": round(counted / n, 6),
        "cases": cases,
    }


__all__ = ["wellbeing_metrics", "wellbeing_soft"]
