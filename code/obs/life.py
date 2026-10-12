"""生活层指标（D 类，`metrics.life`，08 §4.1/§4.2/§4.9）。

只读日志、纯函数、确定性。
"""

from __future__ import annotations


def _agent_of(rec) -> str | None:
    p = rec.get("payload") or {}
    return p.get("agent_id") or rec.get("actor")


def _alive_count(records) -> int:
    born = set()
    dead = set()
    revived = set()
    for r in records:
        p = r.get("payload") or {}
        if r["type"] == "AGENT_BORN":
            born.add(p.get("agent_id"))
        elif r["type"] == "AGENT_DIED":
            dead.add(p.get("agent_id"))
        elif r["type"] == "AGENT_REVIVED":
            revived.add(p.get("agent_id"))
    return len([a for a in born if a and (a not in dead or a in revived)])


def activity_metrics(records) -> dict:
    planned: dict[str, set] = {}
    for r in records:
        if r["type"] == "SCHEDULE_PLANNED":
            p = r.get("payload") or {}
            aid = p.get("agent_id")
            for s in (p.get("slots") or []):
                planned.setdefault(s.get("activity_type"), set()).add(aid)
    started: dict[str, set] = {}
    n_started: dict[str, int] = {}
    n_completed: dict[str, int] = {}
    n_interrupted: dict[str, int] = {}
    durations: dict[str, list] = {}
    for r in records:
        p = r.get("payload") or {}
        t = p.get("activity_type")
        if r["type"] == "ACTIVITY_STARTED":
            started.setdefault(t, set()).add(p.get("agent_id"))
            n_started[t] = n_started.get(t, 0) + 1
        elif r["type"] == "ACTIVITY_COMPLETED":
            if p.get("outcome", "done") == "done":
                n_completed[t] = n_completed.get(t, 0) + 1
            if p.get("duration_ticks") is not None:
                durations.setdefault(t, []).append(int(p["duration_ticks"]))
        elif r["type"] == "ACTIVITY_INTERRUPTED":
            n_interrupted[t] = n_interrupted.get(t, 0) + 1

    types = sorted(set(list(planned) + list(started) + list(n_started)))
    per = {}
    for t in types:
        elig = len(planned.get(t, set()))
        part = len(started.get(t, set()))
        st = n_started.get(t, 0)
        per[t] = {
            "eligible": elig,
            "participated": part,
            "participation_rate": round(part / elig, 6) if elig else 0.0,
            "completion_rate": round(n_completed.get(t, 0) / st, 6) if st else 0.0,
            "interrupt_rate": round(n_interrupted.get(t, 0) / st, 6) if st else 0.0,
            "mean_duration": round(sum(durations.get(t, [])) / len(durations[t]), 6)
            if durations.get(t) else 0.0,
        }
    total_participated = len(set().union(*started.values())) if started else 0
    alive = _alive_count(records)
    return {
        "by_type": per,
        "activity_engagement": round(total_participated / alive, 6) if alive else 0.0,
        "n_activity_started": sum(n_started.values()),
        "n_activity_completed": sum(n_completed.values()),
        "n_activity_interrupted": sum(n_interrupted.values()),
    }


def need_metrics(records) -> dict:
    """需求满足度（取每 Agent 每维最后一笔 after）。"""
    latest: dict[tuple, float] = {}
    for r in records:
        if r["type"] not in ("NEED_UPDATE", "NEEDS_UPDATE"):
            continue
        p = r.get("payload") or {}
        key = (p.get("agent_id"), p.get("dim"))
        if p.get("after") is not None:
            latest[key] = float(p["after"])
    dims = sorted({k[1] for k in latest})
    alive = _alive_count(records)
    out = {}
    for d in dims:
        vals = sorted(v for (a, dd), v in latest.items() if dd == d)
        out[d] = {
            "mean": round(sum(vals) / len(vals), 6) if vals else 0.0,
            "min": round(min(vals), 6) if vals else 0.0,
            "max": round(max(vals), 6) if vals else 0.0,
            "p10": _pct(vals, 0.10),
            "p90": _pct(vals, 0.90),
        }
    return {"dims": out, "n_need_updates": sum(
        1 for r in records if r["type"] in ("NEED_UPDATE", "NEEDS_UPDATE"))}


def _pct(sorted_vals: list, q: float) -> float:
    """最近秩百分位（确定性）。"""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    idx = min(n - 1, max(0, int(round(q * (n - 1)))))
    return round(float(sorted_vals[idx]), 6)


def memory_metrics(records) -> dict:
    writes = [r for r in records if r["type"] == "MEMORY_WRITE"]
    retrieves = [r for r in records if r["type"] == "MEMORY_RETRIEVE"]
    reflects = [r for r in records if r["type"] == "MEMORY_REFLECT"]
    alive = _alive_count(records)
    hits = 0
    for r in retrieves:
        if (r.get("payload") or {}).get("selected_mem_ids"):
            hits += 1
    imp = [int((r.get("payload") or {}).get("importance", 0)) for r in writes]
    out = {
        "mem_write_count": len(writes),
        "mem_retrieve_count": len(retrieves),
        "mem_reflect_count": len(reflects),
        "retrieval_hit_rate": round(hits / len(retrieves), 6) if retrieves else 0.0,
        "mean_importance": round(sum(imp) / len(imp), 6) if imp else 0.0,
        "reflection_rate": round(len(reflects) / alive, 6) if alive else 0.0,
    }
    out.update(_memory_forget_metrics(records))
    out.update(_memory_consolidate_metrics(records))
    return out


# 遗忘保留度直方图固定分箱（千分比 0..1000，确定性；口径单源在 life）
RETENTION_BINS = [f"{i}-{i + 99}" for i in range(0, 1000, 100)] + ["1000"]


def _retention_bucket(v: int) -> str:
    if v >= 1000:
        return "1000"
    if v < 0:
        v = 0
    return f"{(v // 100) * 100}-{(v // 100) * 100 + 99}"


def _memory_forget_metrics(records) -> dict:
    """遗忘口径（T233 / 08 §1.2 S）。**只 count 事件，不复刻 life 的保护规则**（单源在 life）。"""
    by_level = {"demote": 0, "merge": 0, "drop": 0}
    hist = {b: 0 for b in RETENTION_BINS}
    protected_kept = 0
    protected_by_reason: dict = {}
    n = 0
    for r in records:
        if r["type"] != "MEMORY_FORGET":
            continue
        n += 1
        p = r.get("payload") or {}
        lvl = p.get("level")
        if lvl in by_level:
            by_level[lvl] += 1
        rp = p.get("retention_permille")
        if rp is not None:
            hist[_retention_bucket(int(rp))] += 1
        if p.get("protected"):
            protected_kept += 1
            reason = p.get("protection_reason") or "unspecified"
            protected_by_reason[reason] = protected_by_reason.get(reason, 0) + 1
    return {
        "forget_count": n,
        "forget_count_by_level": by_level,
        "retention_hist": hist,
        "protected_kept": protected_kept,
        "protected_by_reason": {k: protected_by_reason[k] for k in sorted(protected_by_reason)},
    }


def _memory_consolidate_metrics(records) -> dict:
    """记忆整合口径（T233 / 08 §1.2 S）：整合次数 + 被并入的源记忆条数。"""
    n = 0
    src_total = 0
    subjects: dict = {}
    for r in records:
        if r["type"] != "MEMORY_CONSOLIDATE":
            continue
        n += 1
        p = r.get("payload") or {}
        src_total += len(p.get("source_mem_ids") or [])
        subj = p.get("subject")
        if subj:
            subjects[subj] = subjects.get(subj, 0) + 1
    return {
        "consolidate_count": n,
        "consolidate_source_count": src_total,
        "consolidate_by_subject": {k: subjects[k] for k in sorted(subjects)},
    }


# 人格维度枚举（06 §2.2 / 08 §1.2 S：单事件单维）
PERSONA_DIMS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]


def persona_metrics(records) -> dict:
    """人格漂移与指纹口径（T233 / 08 §1.2 S）。

    `PERSONA_FINGERPRINT` 是**快照非事件**；其派生视图由 `SLEEP_COMPLETED`（每次睡眠必发）
    与 `PERSONA_DRIFT` 携带，故本函数从这两类事件读取 `pf0/pf_t/drift_permille`。
    纯 count/聚合，不复刻 life 侧的漂移规则。
    """
    drifts = [r for r in records if r["type"] == "PERSONA_DRIFT"]
    by_dim: dict = {d: 0 for d in PERSONA_DIMS}
    for r in drifts:
        d = (r.get("payload") or {}).get("dim")
        if d is not None:
            by_dim[d] = by_dim.get(d, 0) + 1

    # 每 agent 最新指纹视图（按日志顺序折叠；确定性）
    last_fp: dict = {}
    for r in records:
        if r["type"] not in ("SLEEP_COMPLETED", "PERSONA_DRIFT"):
            continue
        p = r.get("payload") or {}
        aid = p.get("agent_id")
        if aid is None or p.get("drift_permille") is None:
            continue
        last_fp[aid] = {"pf0": p.get("pf0"), "pf_t": p.get("pf_t"),
                        "drift_permille": int(p["drift_permille"])}

    drift_vals = sorted(v["drift_permille"] for v in last_fp.values())
    alive = _alive_count(records)
    return {
        "n_drift_events": len(drifts),
        "drift_by_dim": {k: by_dim[k] for k in sorted(by_dim)},
        "n_fingerprint_views": len(last_fp),
        "pf0": {a: last_fp[a]["pf0"] for a in sorted(last_fp)},
        "pf_t": {a: last_fp[a]["pf_t"] for a in sorted(last_fp)},
        "drift_permille": {
            "mean": round(sum(drift_vals) / len(drift_vals), 6) if drift_vals else 0.0,
            "max": max(drift_vals) if drift_vals else 0,
            "min": min(drift_vals) if drift_vals else 0,
        },
        "drift_coverage": round(len(last_fp) / alive, 6) if alive else 0.0,
    }


def skill_metrics(records) -> dict:
    practice: dict[tuple, int] = {}
    levels: dict[tuple, float] = {}
    for r in records:
        p = r.get("payload") or {}
        if r["type"] == "SKILL_PRACTICE":
            k = (p.get("agent_id"), p.get("skill_id"))
            practice[k] = practice.get(k, 0) + 1
        elif r["type"] == "SKILL_LEVEL_UP":
            k = (p.get("agent_id"), p.get("skill_id"))
            if p.get("level_after") is not None:
                levels[k] = float(p["level_after"])
    return {
        "n_skill_practice": sum(practice.values()),
        "n_skill_level_up": sum(1 for r in records if r["type"] == "SKILL_LEVEL_UP"),
        "mean_skill_level": round(sum(levels.values()) / len(levels), 6) if levels else 0.0,
        "n_distinct_agent_skill_pairs": len(set(list(practice) + list(levels))),
    }


def goal_metrics(records) -> dict:
    set_n = sum(1 for r in records if r["type"] == "GOAL_SET")
    ach = sum(1 for r in records if r["type"] == "GOAL_ACHIEVED")
    ab = sum(1 for r in records if r["type"] == "GOAL_ABANDON")
    return {
        "n_goal_set": set_n,
        "n_goal_achieved": ach,
        "n_goal_abandon": ab,
        "goal_achievement_rate": round(ach / set_n, 6) if set_n else 0.0,
    }


def life_metrics(records) -> dict:
    return {
        "activity": activity_metrics(records),
        "need": need_metrics(records),
        "memory": memory_metrics(records),
        "persona": persona_metrics(records),
        "skill": skill_metrics(records),
        "goal": goal_metrics(records),
    }


__all__ = ["life_metrics", "activity_metrics", "need_metrics", "memory_metrics",
           "persona_metrics", "skill_metrics", "goal_metrics"]
