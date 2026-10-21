#!/usr/bin/env python3
"""F-2 睡眠—遗忘—人格漂移：**只读**指标脚本（T-F2）。

职责：把一个已完成 run 的 `run.jsonl`（引擎事件日志）折算成可直接写进报告的
「记忆存活率 / 遗忘曲线 / 睡眠后召回率 / 人格漂移幅度 / 睡眠前后行为差异」五组指标。

设计约束（与项目纪律一致）：
  * **只读**：不写 run 目录、不改 `code/` 任何文件、不启动跑批、不调 LLM。
  * **纯整数/确定性**：不读墙钟、不用随机、不依赖浮点排序（均值允许用 float，但输入是整数）。
  * **口径不复制**：情感判定复用 `code/life/emotion.py::emotion_sign`（单一真源）；
    存活/遗忘的**语义**遵循 `code/engine/replay.py` 的 fold 行为（只有 `drop` 会从
    `memory_index` 移除；`demote`/`merge` 只标记 `forgotten_level`）。
  * 日志中没有的字段一律标 `null` 并在 `summary.json.metrics_unobserved` 里登记，
    **不推断成实测**。

用法（可直接复制复算）：

    cd social-experiment
    python3 tools/f2/memory_drift_report.py \
        --run-dir v2/evidence/run_g1_b0_n16r60_seed42 \
        --out-dir /tmp/f2_g1b0

产物：out-dir 下 summary.json / forgetting_curve.csv / forget_levels.csv /
      survival_by_window.csv / recall_overnight.csv / persona_drift.csv /
      behavior_before_after.csv / anomalies.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC")
DIMS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")


# --------------------------------------------------------------------------- #
# 单一真源：复用 code/life/emotion.py 的 emotion_sign（不复制词表）
# --------------------------------------------------------------------------- #
def _load_emotion_sign():
    p = REPO_ROOT / "code" / "life" / "emotion.py"
    if not p.exists():
        return None, f"missing:{p}"
    spec = importlib.util.spec_from_file_location("f2_emotion_src", p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # pragma: no cover - 只在环境异常时触发
        return None, f"import_error:{exc}"
    return getattr(mod, "emotion_sign", None), str(p)


# --------------------------------------------------------------------------- #
# 日志读取
# --------------------------------------------------------------------------- #
def read_events(log_path: Path):
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def build_index(log_path: Path):
    writes: dict[str, dict] = {}
    forgets: list[dict] = []
    sleeps: list[dict] = []
    sleep_done: list[dict] = []
    drifts: list[dict] = []
    drift_cands: list[dict] = []
    retrieves: list[dict] = []
    msgs: list[dict] = []
    consolidates: list[dict] = []
    dropped: Counter = Counter()
    type_counts: Counter = Counter()
    write_kind: Counter = Counter()

    for ev in read_events(log_path):
        t = ev.get("type")
        p = ev.get("payload") or {}
        if t is None:
            continue
        type_counts[t] += 1
        rnd = ev.get("round")
        if t == "MEMORY_WRITE":
            mid = p.get("mem_id")
            if not mid:
                continue
            writes[mid] = {
                "mem_id": mid,
                "agent": p.get("agent_id"),
                "kind": p.get("kind"),
                "importance": p.get("importance"),
                "subject": p.get("subject"),
                "round": rnd,
                "day": p.get("day"),
                "slot": p.get("slot"),
            }
            write_kind[p.get("kind")] += 1
        elif t == "MEMORY_FORGET":
            forgets.append({
                "round": rnd,
                "seq": ev.get("seq"),
                "agent": p.get("agent_id"),
                "mem_id": p.get("mem_id"),
                "level": p.get("level"),
                "retention_permille": p.get("retention_permille"),
                "protected": bool(p.get("protected")),
                "protection_reason": p.get("protection_reason"),
                "reason": p.get("reason"),
                "day": p.get("day"),
                "slot": p.get("slot"),
            })
        elif t == "SLEEP_STARTED":
            sleeps.append({"agent": p.get("agent_id"), "day": p.get("day"),
                           "slot": p.get("slot"), "round": rnd,
                           "planned_ticks": p.get("planned_ticks")})
        elif t == "SLEEP_COMPLETED":
            sleep_done.append({"agent": p.get("agent_id"), "day": p.get("day"),
                               "round": rnd, "slot": p.get("slot"),
                               "drift_permille": p.get("drift_permille"),
                               "pf0": p.get("pf0"), "pf_t": p.get("pf_t")})
        elif t == "PERSONA_DRIFT":
            drifts.append({
                "round": rnd, "seq": ev.get("seq"), "agent": p.get("agent_id"),
                "dim": p.get("dim"), "before": p.get("before"), "after": p.get("after"),
                "anchor": p.get("anchor"), "cause_mem_id": p.get("cause_mem_id"),
                "drift_permille": p.get("drift_permille"), "day": p.get("day"),
                "pf0": p.get("pf0"), "pf_t": p.get("pf_t"),
            })
        elif t == "PERSONA_DRIFT_CANDIDATE":
            drift_cands.append({"agent": p.get("agent_id"), "dim": p.get("dim"),
                                "sign": p.get("sign"), "round": rnd,
                                "reached": bool(p.get("reached_threshold"))})
        elif t == "MEMORY_RETRIEVE":
            retrieves.append({"round": rnd, "agent": p.get("agent_id"),
                              "selected": list(p.get("selected_mem_ids") or []),
                              "top_k": p.get("top_k"),
                              "mode": p.get("retrieval_mode"),
                              "vec_available": p.get("vec_available")})
        elif t == "MEMORY_CONSOLIDATE":
            consolidates.append({"round": rnd, "agent": p.get("agent_id"),
                                 "subject": p.get("subject"),
                                 "produced_mem_id": p.get("produced_mem_id"),
                                 "source_mem_ids": list(p.get("source_mem_ids") or [])})
        elif t in MSG_TYPES:
            msgs.append({
                "round": rnd, "day": p.get("day"), "slot": p.get("slot"),
                "actor": ev.get("actor"), "author": p.get("author") or p.get("from"),
                "body": p.get("body") or "", "topic": p.get("topic"),
                "msg_id": p.get("msg_id"),
            })
        elif t == "DROPPED":
            reason = p.get("reason")
            if reason == "unknown_intent_field":
                dropped[f"{p.get('type')}::{'/'.join(p.get('keys') or [])}"] += 1
    return {
        "writes": writes, "forgets": forgets, "sleeps": sleeps, "sleep_done": sleep_done,
        "drifts": drifts, "drift_cands": drift_cands, "retrieves": retrieves,
        "msgs": msgs, "consolidates": consolidates, "dropped": dropped,
        "type_counts": type_counts, "write_kind": write_kind,
    }


# --------------------------------------------------------------------------- #
# 指标 1：记忆存活率 / 遗忘曲线
# --------------------------------------------------------------------------- #
def drop_rounds(forgets) -> dict[str, int]:
    """`level=="drop"` 的首次 round（replay.py:359-368：只有 drop 会把 mem 移除）。"""
    out: dict[str, int] = {}
    for f in sorted(forgets, key=lambda x: (x["seq"] if x["seq"] is not None else 0)):
        if f["level"] == "drop" and f["mem_id"]:
            out.setdefault(f["mem_id"], f["round"])
    return out


def alive_at(writes, drops, agent, round_no) -> set[str]:
    out = set()
    for mid, w in writes.items():
        if w["agent"] != agent or w["round"] is None or w["round"] >= round_no:
            continue
        if mid in drops and drops[mid] < round_no:
            continue
        out.add(mid)
    return out


def forget_levels_metrics(forgets) -> list[dict]:
    by = defaultdict(list)
    for f in forgets:
        by[f["level"]].append(f)
    rows = []
    for lvl in ("demote", "merge", "drop"):
        xs = by.get(lvl, [])
        rets = [int(x["retention_permille"]) for x in xs if x["retention_permille"] is not None]
        rows.append({
            "level": lvl,
            "n_actions": len(xs),
            "n_unique_mem": len({x["mem_id"] for x in xs}),
            "n_protected": sum(1 for x in xs if x["protected"]),
            "retention_min": min(rets) if rets else None,
            "retention_max": max(rets) if rets else None,
            "retention_mean": round(sum(rets) / len(rets), 1) if rets else None,
        })
    return rows


AGE_BUCKETS = [(0, 6), (7, 12), (13, 24), (25, 36), (37, 48), (49, 60), (61, 10 ** 9)]


def _age_bucket(age: int) -> str:
    for lo, hi in AGE_BUCKETS:
        if lo <= age <= hi:
            return f"{lo}-{hi}" if hi < 10 ** 9 else f"{lo}+"
    return "unknown"


def _mean(xs) -> float | None:
    vals = [x for x in xs if x is not None]
    return round(sum(vals) / len(vals), 6) if vals else None


def forgetting_curve(writes, forgets) -> list[dict]:
    """经验遗忘曲线：R（retention_permille）对**写入后经过的 round 数**（age）。

    注意：`life/forgetting.py:130-132` 的 dt 用的是 `last_access`（记忆最近被检索的 round），
    日志里**没有** `last_access`/`access_count` 字段 ⇒ age ≥ dt，本曲线是 dt 的**上界**刻度。
    """
    buckets = defaultdict(list)
    for f in forgets:
        w = writes.get(f["mem_id"])
        if not w or w["round"] is None or f["round"] is None:
            buckets["unknown"].append(f)
            continue
        buckets[_age_bucket(int(f["round"]) - int(w["round"]))].append(f)
    rows = []
    order = [f"{lo}-{hi}" if hi < 10 ** 9 else f"{lo}+" for lo, hi in AGE_BUCKETS]
    for name in order:
        xs = buckets.get(name, [])
        rets = [int(x["retention_permille"]) for x in xs if x["retention_permille"] is not None]
        rows.append({
            "age_rounds": name,
            "n_forget_actions": len(xs),
            "n_unique_mem": len({x["mem_id"] for x in xs}),
            "retention_min": min(rets) if rets else None,
            "retention_max": max(rets) if rets else None,
            "retention_mean": round(sum(rets) / len(rets), 1) if rets else None,
            "n_demote": sum(1 for x in xs if x["level"] == "demote"),
            "n_merge": sum(1 for x in xs if x["level"] == "merge"),
            "n_drop": sum(1 for x in xs if x["level"] == "drop"),
        })
    return rows


def survival_by_window(writes, forgets, sleeps, drops) -> list[dict]:
    """每个睡眠窗的存活率 = 1 − 本窗 drop 数 / 睡前存活数（replay 只有 drop 会移除）。"""
    per_window = defaultdict(Counter)
    for f in forgets:
        per_window[(f["agent"], f["round"])][f["level"]] += 1
    rows = []
    for s in sorted(sleeps, key=lambda x: (str(x["agent"]), x["round"])):
        agent, rnd = s["agent"], s["round"]
        live_before = alive_at(writes, drops, agent, rnd)
        n_live = len(live_before)
        c = per_window.get((agent, rnd), Counter())
        n_drop, n_merge, n_demote = c["drop"], c["merge"], c["demote"]
        rows.append({
            "agent": agent, "day": s["day"], "slot": s["slot"], "sleep_round": rnd,
            "mem_alive_before": n_live,
            "n_demote": n_demote, "n_merge": n_merge, "n_drop": n_drop,
            "n_forget_actions": n_drop + n_merge + n_demote,
            "survival_rate_window": round(1 - (n_drop / n_live), 6) if n_live else None,
            "forget_rate_window": round((n_drop + n_merge + n_demote) / n_live, 6) if n_live else None,
        })
    return rows


# --------------------------------------------------------------------------- #
# 指标 2：唤醒后对「睡前信息」的召回率
# --------------------------------------------------------------------------- #
def recall_overnight(writes, sleeps, retrieves, drops) -> list[dict]:
    """对每个睡眠窗：睡前存活记忆集合 → 睡后一个睡眠周期内被检索到的比例。"""
    by_agent_sleeps = defaultdict(list)
    for s in sleeps:
        by_agent_sleeps[s["agent"]].append(s["round"])
    for a in by_agent_sleeps:
        by_agent_sleeps[a].sort()
    ret_by_agent = defaultdict(list)
    for r in retrieves:
        ret_by_agent[r["agent"]].append(r)
    for a in ret_by_agent:
        ret_by_agent[a].sort(key=lambda x: x["round"])

    rows = []
    for agent, rounds in sorted(by_agent_sleeps.items()):
        for i, rnd in enumerate(rounds):
            nxt = rounds[i + 1] if i + 1 < len(rounds) else None
            horizon = nxt if nxt is not None else (rnd + 12)
            prev = rounds[i - 1] if i > 0 else (rnd - 12)
            presleep = alive_at(writes, drops, agent, rnd)
            retrieved: set[str] = set()
            retrieved_slots = 0
            ctrl: set[str] = set()
            ctrl_slots = 0
            for r in ret_by_agent.get(agent, []):
                if rnd < r["round"] <= horizon:
                    retrieved.update(r["selected"])
                    retrieved_slots += len(r["selected"])
                elif prev < r["round"] <= rnd:      # 睡前一个睡眠周期：同集合的对照召回
                    ctrl.update(r["selected"])
                    ctrl_slots += len(r["selected"])
            hit = len(presleep & retrieved)
            ctrl_hit = len(presleep & ctrl)
            rate_post = hit / len(presleep) if presleep else None
            rate_pre = ctrl_hit / len(presleep) if presleep else None
            rows.append({
                "agent": agent,
                "sleep_round": rnd,
                "window_after": f"({rnd},{horizon}]",
                "window_control_before": f"({prev},{rnd}]",
                "mem_alive_before_sleep": len(presleep),
                "retrieved_distinct_after_sleep": len(retrieved),
                "retrieved_slots_after_sleep": retrieved_slots,
                "presleep_mem_recalled": hit,
                "recall_rate_presleep": round(rate_post, 6) if rate_post is not None else None,
                "precision_on_presleep": round(hit / len(retrieved), 6) if retrieved else None,
                "control_slots_before_sleep": ctrl_slots,
                "control_presleep_mem_recalled": ctrl_hit,
                "control_recall_rate": round(rate_pre, 6) if rate_pre is not None else None,
                "delta_recall_post_minus_pre": (round(rate_post - rate_pre, 6)
                                                if rate_post is not None and rate_pre is not None
                                                else None),
            })
    return rows


def recall_overall(writes, retrieves, drops) -> dict:
    """全局：检索槽命中率、槽位选择的**记忆年龄分布**。"""
    n_slots = sum(len(r["selected"]) for r in retrieves)
    n_empty = sum(1 for r in retrieves if not r["selected"])
    unknown = sum(1 for r in retrieves for mid in r["selected"] if mid not in writes)
    ages: list[int] = []
    for r in retrieves:
        for mid in r["selected"]:
            w = writes.get(mid)
            if w and w["round"] is not None and r["round"] is not None:
                ages.append(int(r["round"]) - int(w["round"]))
    return {
        "n_retrieve_events": len(retrieves),
        "n_empty_retrieve": n_empty,
        "n_retrieve_slots": n_slots,
        "selected_mem_not_in_write_log": unknown,
        "retrieval_hit_rate": round(1 - n_empty / len(retrieves), 6) if retrieves else None,
        "mean_selected_per_retrieve": round(n_slots / len(retrieves), 3) if retrieves else None,
        "mean_age_rounds_of_selected": round(sum(ages) / len(ages), 2) if ages else None,
        "share_selected_age_gt_12": round(sum(1 for a in ages if a > 12) / len(ages), 4)
        if ages else None,
        "share_selected_age_gt_36": round(sum(1 for a in ages if a > 36) / len(ages), 4)
        if ages else None,
        "top_k_modes": dict(Counter(r["mode"] for r in retrieves)),
        "vec_available": dict(Counter(str(r["vec_available"]) for r in retrieves)),
    }


# --------------------------------------------------------------------------- #
# 指标 3：人格向量漂移
# --------------------------------------------------------------------------- #
def persona_drift_metrics(drifts, drift_cands, sleep_done, agents) -> list[dict]:
    per_agent = defaultdict(list)
    for d in drifts:
        per_agent[d["agent"]].append(d)
    rows = []
    for agent in sorted(set(agents) | set(per_agent)):
        evs = sorted((d for d in per_agent.get(agent, []) if d["seq"] is not None),
                     key=lambda x: x["seq"])
        state: dict[str, int] = {}
        anchor: dict[str, int] = {}
        for d in evs:
            dim = d["dim"]
            if dim in DIMS:
                if d.get("anchor") is not None:
                    anchor[dim] = int(d["anchor"])
                if d.get("after") is not None:
                    state[dim] = int(d["after"])
        observed_dims = sorted(state)
        raw_l1 = sum(abs(int(d["after"]) - int(d["before"])) for d in evs
                     if d.get("after") is not None and d.get("before") is not None)
        l2 = None
        cos = None
        if observed_dims:
            l2 = round(sum((state[d] - anchor.get(d, state[d])) ** 2 for d in observed_dims) ** 0.5, 3)
            if all(d in anchor for d in observed_dims):
                num = sum(state[d] * anchor[d] for d in observed_dims)
                da = sum(state[d] ** 2 for d in observed_dims) ** 0.5
                db = sum(anchor[d] ** 2 for d in observed_dims) ** 0.5
                cos = round(num / (da * db), 6) if da and db else None
        last = evs[-1] if evs else None
        rows.append({
            "agent": agent,
            "n_drift_events": len(evs),
            "n_drift_candidates": sum(1 for c in drift_cands if c["agent"] == agent),
            "n_candidates_reached": sum(1 for c in drift_cands
                                        if c["agent"] == agent and c["reached"]),
            "dims_drifted": "/".join(observed_dims) if observed_dims else "",
            "sum_abs_delta_raw": raw_l1,
            "l2_vs_anchor_partial": l2,
            "cosine_vs_anchor_partial": cos,
            "drift_permille_last_event": int(last["drift_permille"])
            if last and last.get("drift_permille") is not None else None,
            "pf0": last.get("pf0") if last else None,
            "pf_t": last.get("pf_t") if last else None,
            "state_observed": json.dumps({d: state[d] for d in observed_dims}, sort_keys=True),
            "anchor_observed": json.dumps({d: anchor[d] for d in sorted(anchor)}, sort_keys=True),
            "note": "" if evs else "no_drift_event",
        })
    return rows


# --------------------------------------------------------------------------- #
# 指标 4：睡眠前后行为差异
# --------------------------------------------------------------------------- #
def _msgs_in(msgs, agent, lo, hi):
    return [m for m in msgs if m["actor"] == agent and m["round"] is not None and lo < m["round"] <= hi]


def _tv_distance(c1: Counter, c2: Counter) -> float | None:
    keys = set(c1) | set(c2)
    n1, n2 = sum(c1.values()), sum(c2.values())
    if not n1 or not n2:
        return None
    return round(0.5 * sum(abs(c1[k] / n1 - c2[k] / n2) for k in keys), 6)


def _behavior_block(msgs, emotion_sign):
    bodies = [m["body"] for m in msgs if m["body"]]
    pos = neg = hit = 0
    if emotion_sign is not None:
        for b in bodies:
            s = emotion_sign(b)
            if s > 0:
                pos += 1
                hit += 1
            elif s < 0:
                neg += 1
                hit += 1
    return {
        "n_msg": len(msgs),
        "mean_len": round(sum(len(b) for b in bodies) / len(bodies), 2) if bodies else None,
        "n_nonempty": len(bodies),
        "pos": pos,
        "neg": neg,
        "polarity_hit_rate": round(hit / len(bodies), 4) if bodies else None,
        "pos_ratio_among_hits": round(pos / hit, 4) if hit else None,
        "topics": Counter(m["topic"] for m in msgs if m["topic"]),
    }


def behavior_before_after(msgs, sleeps, emotion_sign) -> tuple[list[dict], dict]:
    by_agent_sleeps = defaultdict(list)
    for s in sleeps:
        by_agent_sleeps[s["agent"]].append(s["round"])
    for a in by_agent_sleeps:
        by_agent_sleeps[a].sort()
    rows = []
    pooled_pre = defaultdict(list)
    pooled_post = defaultdict(list)
    for agent, rounds in sorted(by_agent_sleeps.items()):
        for i, rnd in enumerate(rounds):
            prev = rounds[i - 1] if i > 0 else (rnd - 12)
            pre = _msgs_in(msgs, agent, prev, rnd)
            post = _msgs_in(msgs, agent, rnd, rnd + 12)
            bpre = _behavior_block(pre, emotion_sign)
            bpost = _behavior_block(post, emotion_sign)
            tv_len = None
            if bpre["mean_len"] is not None and bpost["mean_len"] is not None:
                tv_len = round(bpost["mean_len"] - bpre["mean_len"], 2)
            rows.append({
                "agent": agent,
                "sleep_round": rnd,
                "pre_n_msg": bpre["n_msg"],
                "post_n_msg": bpost["n_msg"],
                "pre_mean_len": bpre["mean_len"],
                "post_mean_len": bpost["mean_len"],
                "delta_mean_len": tv_len,
                "pre_pos_ratio": bpre["pos_ratio_among_hits"],
                "post_pos_ratio": bpost["pos_ratio_among_hits"],
                "topic_tv_distance": _tv_distance(bpre["topics"], bpost["topics"]),
            })
            for m in pre:
                pooled_pre[agent].append(m)
            for m in post:
                pooled_post[agent].append(m)
    all_pre = [m for xs in pooled_pre.values() for m in xs]
    all_post = [m for xs in pooled_post.values() for m in xs]
    bpre = _behavior_block(all_pre, emotion_sign)
    bpost = _behavior_block(all_post, emotion_sign)
    pooled = {
        "pre": {k: v for k, v in bpre.items() if k != "topics"},
        "post": {k: v for k, v in bpost.items() if k != "topics"},
        "delta_mean_len": (round(bpost["mean_len"] - bpre["mean_len"], 2)
                           if bpre["mean_len"] is not None and bpost["mean_len"] is not None else None),
        "topic_tv_distance": _tv_distance(bpre["topics"], bpost["topics"]),
        "pre_topic_dist": dict(bpre["topics"].most_common()),
        "post_topic_dist": dict(bpost["topics"].most_common()),
    }
    return rows, pooled


# --------------------------------------------------------------------------- #
# 异常/一致性审计
# --------------------------------------------------------------------------- #
def anomalies(idx) -> dict:
    drop_after = 0
    first_drop: dict[str, int] = {}
    acts = defaultdict(list)
    for f in idx["forgets"]:
        if f["mem_id"]:
            acts[f["mem_id"]].append((f["seq"], f["level"]))
    for mid, xs in acts.items():
        xs.sort()
        for i, (seq, lvl) in enumerate(xs):
            if lvl == "drop" and i + 1 < len(xs):
                drop_after += 1
                break
    cons_ok = sum(1 for c in idx["consolidates"] if c["produced_mem_id"])
    sm_writes = sum(1 for m in idx["writes"].values() if "-SM-" in str(m["mem_id"]))
    sleep_null_drift = sum(1 for s in idx["sleep_done"] if s["drift_permille"] is None)
    return {
        "n_mem_written": len(idx["writes"]),
        "n_mem_written_by_kind": dict(idx["write_kind"]),
        "n_mem_dropped_distinct": len({f["mem_id"] for f in idx["forgets"] if f["level"] == "drop"}),
        "n_mem_with_action_after_drop": drop_after,
        "n_consolidate_events": len(idx["consolidates"]),
        "n_consolidate_with_produced_id": cons_ok,
        "n_consolidate_source_ids": sum(len(c["source_mem_ids"]) for c in idx["consolidates"]),
        "n_semantic_memory_write_events": sm_writes,
        "n_sleep_completed": len(idx["sleep_done"]),
        "n_sleep_completed_drift_null": sleep_null_drift,
        "n_persona_drift_events": len(idx["drifts"]),
        "n_persona_drift_candidates": len(idx["drift_cands"]),
        "unknown_intent_fields": dict(idx["dropped"]),
        "note": ("MEMORY_CONSOLIDATE 事件落账但伴随 DROPPED(unknown_intent_field: text)；"
                 "replay.py:372-388 仍会 fold 出 semantic 记忆（importance 缺省 6），"
                 "但日志中不存在该 SM 的 MEMORY_WRITE ⇒ SM 正文/importance 在日志侧未观测。"),
    }


# --------------------------------------------------------------------------- #
def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="f2.memory_drift_report",
                                 description="F-2 睡眠/遗忘/人格漂移 只读指标脚本")
    ap.add_argument("--run-dir", help="包含 run.jsonl 的 run 目录")
    ap.add_argument("--log", help="直接指定 run.jsonl 路径（优先于 --run-dir）")
    ap.add_argument("--out-dir", default=None, help="产出目录（默认 <run-dir>/f2_metrics）")
    ap.add_argument("--top", type=int, default=8, help="摘要里保留的 top 条数")
    args = ap.parse_args(argv)

    log_path = Path(args.log) if args.log else (Path(args.run_dir) / "run.jsonl")
    if not log_path.exists():
        print(f"log not found: {log_path}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir) if args.out_dir else (log_path.parent / "f2_metrics")
    out_dir.mkdir(parents=True, exist_ok=True)

    sha = hashlib.sha256()
    with log_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            sha.update(chunk)

    idx = build_index(log_path)
    emotion_sign, emotion_src = _load_emotion_sign()
    agents = sorted({w["agent"] for w in idx["writes"].values() if w["agent"]})
    drops = drop_rounds(idx["forgets"])

    levels = forget_levels_metrics(idx["forgets"])
    curve = forgetting_curve(idx["writes"], idx["forgets"])
    surv = survival_by_window(idx["writes"], idx["forgets"], idx["sleeps"], drops)
    recall_rows = recall_overnight(idx["writes"], idx["sleeps"], idx["retrieves"], drops)
    recall_all = recall_overall(idx["writes"], idx["retrieves"], drops)
    persona = persona_drift_metrics(idx["drifts"], idx["drift_cands"], idx["sleep_done"], agents)
    beh_rows, beh_pooled = behavior_before_after(idx["msgs"], idx["sleeps"], emotion_sign)
    anom = anomalies(idx)

    total_written = len(idx["writes"])
    total_dropped = anom["n_mem_dropped_distinct"]
    summary = {
        "log": str(log_path),
        "log_sha256": sha.hexdigest(),
        "n_events": sum(idx["type_counts"].values()),
        "event_type_counts": dict(idx["type_counts"].most_common()),
        "emotion_single_source": {"used": bool(emotion_sign), "path": emotion_src,
                                  "criterion": "natural(默认)"},
        "agents": agents,
        # --- M1 记忆存活率 ---
        "m1_memory_survival": {
            "n_mem_written": total_written,
            "n_mem_dropped_distinct": total_dropped,
            "survival_rate_end": round(1 - total_dropped / total_written, 6)
            if total_written else None,
            "forget_levels": levels,
            "n_forget_actions_total": len(idx["forgets"]),
            "n_sleep_windows": len(idx["sleeps"]),
            "mean_survival_rate_per_window": round(
                sum(r["survival_rate_window"] for r in surv
                    if r["survival_rate_window"] is not None)
                / len([r for r in surv if r["survival_rate_window"] is not None]), 6)
            if any(r["survival_rate_window"] is not None for r in surv) else None,
            "retention_observed_min": min((int(f["retention_permille"]) for f in idx["forgets"]
                                           if f["retention_permille"] is not None), default=None),
            "retention_observed_max": max((int(f["retention_permille"]) for f in idx["forgets"]
                                           if f["retention_permille"] is not None), default=None),
        },
        # --- M2 召回 ---
        "m2_overnight_recall": {
            "overall": recall_all,
            "mean_recall_rate_presleep": _mean([r["recall_rate_presleep"] for r in recall_rows]),
            "mean_control_recall_rate": _mean([r["control_recall_rate"] for r in recall_rows]),
            "mean_delta_recall_post_minus_pre": _mean(
                [r["delta_recall_post_minus_pre"] for r in recall_rows]),
            "n_windows": len(recall_rows),
            "windows_with_zero_recall": sum(1 for r in recall_rows
                                            if r["presleep_mem_recalled"] == 0),
            "windows_recall_up_after_sleep": sum(
                1 for r in recall_rows if (r["delta_recall_post_minus_pre"] or 0) > 0),
        },
        # --- M3 人格漂移 ---
        "m3_persona_drift": {
            "n_agents_with_drift": sum(1 for r in persona if r["n_drift_events"] > 0),
            "n_agents_total": len(persona),
            "max_drift_permille_observed": max(
                (r["drift_permille_last_event"] for r in persona
                 if r["drift_permille_last_event"] is not None), default=None),
            "mean_sum_abs_delta_raw": round(
                sum(r["sum_abs_delta_raw"] for r in persona) / len(persona), 3) if persona else None,
            "drift_by_dim": dict(Counter(d["dim"] for d in idx["drifts"])),
            "per_agent": persona,
        },
        # --- M4 行为差异 ---
        "m4_behavior_before_after": beh_pooled,
        "anomalies": anom,
        "metrics_unobserved": [
            "mem.last_access / access_count / emo：日志无字段（MEMORY_WRITE 只带 importance/kind/subject）",
            "SLEEP_COMPLETED.drift_permille/pf0/pf_t：payload 恒为 null（sleep_end 未携带）",
            "semantic(SM) 记忆的 importance 与正文：日志无 MEMORY_WRITE，仅事件落实（replay 缺省 importance=6）",
            "TAG_EMITTED.valence 恒为 0，不能作为情感极性来源；本脚本改用 emotion_sign 复算（派生量）",
        ],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(out_dir / "forget_levels.csv", levels)
    write_csv(out_dir / "forgetting_curve.csv", curve)
    write_csv(out_dir / "survival_by_window.csv", surv)
    write_csv(out_dir / "recall_overnight.csv", recall_rows)
    write_csv(out_dir / "persona_drift.csv", persona)
    write_csv(out_dir / "behavior_before_after.csv", beh_rows)
    (out_dir / "anomalies.json").write_text(
        json.dumps(anom, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[f2] log={log_path} sha256={summary['log_sha256'][:12]}... events={summary['n_events']}")
    print(f"[f2] M1 survival_rate_end={summary['m1_memory_survival']['survival_rate_end']} "
          f"levels={ {r['level']: r['n_actions'] for r in levels} }")
    print(f"[f2] M2 mean_recall_presleep={summary['m2_overnight_recall']['mean_recall_rate_presleep']} "
          f"hit_rate={recall_all['retrieval_hit_rate']}")
    print(f"[f2] M3 agents_with_drift={summary['m3_persona_drift']['n_agents_with_drift']}"
          f"/{summary['m3_persona_drift']['n_agents_total']} "
          f"max_drift_permille={summary['m3_persona_drift']['max_drift_permille_observed']}")
    print(f"[f2] M4 delta_mean_len={beh_pooled['delta_mean_len']} "
          f"topic_tv={beh_pooled['topic_tv_distance']}")
    print(f"[f2] out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
