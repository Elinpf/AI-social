#!/usr/bin/env python3
"""D2 线程结构指标：从 run.jsonl 复算（只读、纯函数、确定性）。

两种重建口径并列输出，避免口径混淆：
  A) tid 口径      —— 按 `payload.thread_id` 分组；旧日志无该键 → 单发线程（长度 1）。
                      ⚠ 该口径下 before 的「平均轮次 1.0」是**定义产物**，不代表改造前只有单发。
  B) temporal 口径 —— 时间邻近重建，before/after **同规则**，才真正可横向比较：
                      * MSG_DM   : 同一无序对端，按 (round, seq) 排序；相邻两条 round 差 ≤1
                                   且说话人交替 → 同一条链
                      * MSG_GROUP: 同一 group_id，相邻 round 差 ≤1 且说话人不同
                      * MSG_PUBLIC: 同一 place（或 global 桶），相邻 round 差 ≤1 且作者不同

指标（两口径同定义）：
  n_threads / mean_turns / max_turns / median_turns / turns_dist
  single_msg_thread_ratio(turns==1) / multi_turn_thread_ratio(turns>=3)
  duplicate_body_ratio（线程内 body 完全重复占比）
  reply_coverage（有非空 reply_to 的消息占比；旧日志恒 0）
  turn_index_violations（turn_index 非 0 起或非连续 +1 的线程数）
  以及断言块：msg_id_unique / reply_to_same_thread / turn_index_dense /
             participants_consistent / ptr_cross_thread

输出：JSON 到 stdout（`-o` 写文件）。

用法：
  python3 tools/d2/thread_metrics.py <run.jsonl> [-o out.json] [--strict]
  `--strict`：任一断言失败 → exit 4（用于 after 臂自检）
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _msgs(records):
    out = []
    for r in records:
        if r.get("type") not in MSG_TYPES:
            continue
        p = r.get("payload") or {}
        out.append({
            "seq": int(r["seq"]),
            "round": int(r.get("round", 0)),
            "type": r["type"],
            "msg_id": p.get("msg_id"),
            "msg_uid": p.get("msg_uid"),
            "from": p.get("from") or p.get("author") or r.get("actor"),
            "to": p.get("to"),
            "group_id": p.get("group_id"),
            "place": p.get("place"),
            "body": (p.get("body") or "").strip(),
            "thread_id": p.get("thread_id"),
            "turn_index": p.get("turn_index"),
            "reply_to": p.get("reply_to"),
            "participants": list(p.get("participants") or []),
        })
    out.sort(key=lambda m: m["seq"])
    return out


def _turns(groups):
    return [len(g) for g in groups]


def _metrics(groups, msgs) -> dict:
    turns = _turns(groups)
    dup_num = dup_den = 0
    for g in groups:
        bodies = [m["body"] for m in g if m["body"]]
        if not bodies:
            continue
        dup_den += len(bodies)
        c = Counter(bodies)
        dup_num += sum(v - 1 for v in c.values() if v > 1)
    n = len(turns)
    has_tid = any(m.get("thread_id") for m in msgs)
    with_reply = [m for m in msgs if m.get("reply_to")]
    return {
        "n_threads": n,
        "n_messages": len(msgs),
        "mean_turns": round(statistics.mean(turns), 4) if n else 0.0,
        "max_turns": max(turns) if n else 0,
        "median_turns": statistics.median(turns) if n else 0,
        "turns_dist": {str(k): v for k, v in sorted(Counter(turns).items())},
        "single_msg_thread_ratio": round(sum(1 for t in turns if t == 1) / n, 4) if n else 0.0,
        "multi_turn_thread_ratio": round(sum(1 for t in turns if t >= 3) / n, 4) if n else 0.0,
        "duplicate_body_ratio": round(dup_num / dup_den, 4) if dup_den else 0.0,
        "reply_coverage": round(len(with_reply) / len(msgs), 4) if msgs and has_tid else 0.0,
        "turn_index_violations": _turn_violations(groups),
    }


def _turn_violations(groups) -> int:
    bad = 0
    for g in groups:
        idx = [m["turn_index"] for m in g if m.get("turn_index") is not None]
        if not idx:
            continue
        if idx[0] != 0 or any(b != a + 1 for a, b in zip(idx, idx[1:])):
            bad += 1
    return bad


def group_by_tid(msgs):
    g = defaultdict(list)
    for i, m in enumerate(msgs):
        g[m.get("thread_id") or f"__solo_{i}"].append(m)
    for v in g.values():
        v.sort(key=lambda m: (m["round"], m["seq"]))
    return list(g.values())


def _chain_by_pointer(msgs):
    """按 reply_to 指针建链（仅 tid 口径有意义）：返回每条线程按指针串起来的最大链长。"""
    by_id = {m["msg_uid"]: m for m in msgs if m.get("msg_uid")}
    depth = {}
    for m in msgs:
        if not m.get("msg_uid"):
            continue
        cur, steps, seen = m, 1, {m["msg_uid"]}
        while True:
            rt = cur.get("reply_to")
            if not rt or rt not in by_id or rt in seen:
                break
            seen.add(rt)
            cur = by_id[rt]
            steps += 1
        depth[m["msg_uid"]] = steps
    per_thread = defaultdict(int)
    for m in msgs:
        if m.get("msg_uid") in depth and m.get("thread_id"):
            per_thread[m["thread_id"]] = max(per_thread[m["thread_id"]], depth[m["msg_uid"]])
    return per_thread


def group_temporal(msgs):
    chains = []

    def push(ch, m, same):
        if same(ch[-1], m):
            ch.append(m)
        else:
            chains.append(ch)
            return [m]
        return ch

    for bucket_key, sel in (
        ("dm", lambda m: m["type"] == "MSG_DM"),
        ("group", lambda m: m["type"] == "MSG_GROUP"),
        ("public", lambda m: m["type"] == "MSG_PUBLIC"),
    ):
        buckets = defaultdict(list)
        for m in msgs:
            if not sel(m):
                continue
            if bucket_key == "dm":
                key = tuple(sorted((m["from"], m["to"])))
            elif bucket_key == "group":
                key = m["group_id"]
            else:
                key = m["place"] or "__global__"
            buckets[key].append(m)
        for key in sorted(buckets, key=str):
            evs = sorted(buckets[key], key=lambda m: (m["round"], m["seq"]))
            ch = [evs[0]]
            for m in evs[1:]:
                ch = push(ch, m, lambda prev, cur: (cur["round"] - prev["round"] <= 1
                                                    and cur["from"] != prev["from"]))
            chains.append(ch)
    return chains


def assertions(msgs) -> dict:
    # D2：唯一键是 msg_uid（msg_id 保留旧语义，跨 agent 会撞，属**已知历史缺陷**，单列不判 FAIL）
    uids = [m.get("msg_uid") for m in msgs if m.get("msg_uid")]
    dup_uid = {k: v for k, v in Counter(uids).items() if v > 1}
    ids = [m["msg_id"] for m in msgs if m.get("msg_id")]
    dup_mid = {k: v for k, v in Counter(ids).items() if v > 1}
    owner = {m["msg_uid"]: m for m in msgs if m.get("msg_uid")}
    cross = dangling = 0
    for m in msgs:
        rt = m.get("reply_to")
        if not rt:
            continue
        if rt not in owner:
            dangling += 1
        elif owner[rt].get("thread_id") != m.get("thread_id"):
            cross += 1
        elif owner[rt]["seq"] >= m["seq"]:
            cross += 1
    parts_bad = 0
    by_thread = defaultdict(set)
    for m in msgs:
        if m.get("thread_id"):
            by_thread[m["thread_id"]].add(tuple(m["participants"]))
    for tid, variants in by_thread.items():
        base = None
        for v in variants:
            if base is None:
                base = set(v)
            elif base != set(v):
                parts_bad += 1
                break
    groups = group_by_tid(msgs)
    dense_bad = _turn_violations(groups)
    return {
        "msg_uid_unique": (not dup_uid) if uids else None,
        "dup_msg_uids": dup_uid,
        "msg_id_unique": not dup_mid,
        "dup_msg_ids_legacy_known_defect": dup_mid,
        "reply_to_same_thread": (cross == 0 and dangling == 0),
        "ptr_cross_thread": cross,
        "ptr_dangling": dangling,
        "turn_index_dense": dense_bad == 0,
        "turn_index_violations": dense_bad,
        "participants_consistent": parts_bad == 0,
        "participants_violations": parts_bad,
    }


def _chain_diff(msgs, groups_tid, ptr_chain) -> dict:
    """per-thread：说话人交替链长 vs 指针链长，仅列不一致者（供 eval 检查「指针与交替脱节」）。"""
    alt = {}
    for g in groups_tid:
        tid = g[0].get("thread_id") if g else None
        if tid:
            alt[tid] = len(g)
    out = {}
    for tid in sorted(alt):
        by_ptr = ptr_chain.get(tid, 0)
        if by_ptr != alt[tid]:
            out[tid] = {"alternation": alt[tid], "by_pointer": by_ptr}
    return out


def compute(path: str) -> dict:
    records = load(path)
    msgs = _msgs(records)
    groups_tid = group_by_tid(msgs)
    groups_tmp = group_temporal(msgs)
    ptr_chain = _chain_by_pointer(msgs)
    ptr_max = max(ptr_chain.values()) if ptr_chain else 0
    tid_metrics = _metrics(groups_tid, msgs)
    return {
        "source": path,
        "events_total": len(records),
        "msg_share": round(len(msgs) / len(records), 4) if records else 0.0,
        "msg_counts": dict(Counter(m["type"] for m in msgs)),
        "has_thread_fields": any(m.get("thread_id") for m in msgs),
        "tid_mode": tid_metrics,
        "temporal_mode": _metrics(groups_tmp, msgs),
        "chain_by_alternation": tid_metrics["max_turns"],
        "chain_by_pointer": ptr_max,
        "chain_diff_detail": _chain_diff(msgs, groups_tid, ptr_chain),
        "assertions": assertions(msgs),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_jsonl")
    ap.add_argument("-o", "--out")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    res = compute(a.run_jsonl)
    text = json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    if a.strict:
        bad = [k for k, v in res["assertions"].items()
               if k.startswith(("msg_uid_unique", "reply_to_same", "turn_index_dense", "participants_"))
               and v is not True]
        if bad:
            print(f"[thread_metrics] FAIL: {bad}", file=sys.stderr)
            return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
