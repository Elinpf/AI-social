#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""batch4 规格用：**只读**线程层占比普查（不改 code/、不跑 orchestration）。

口径（写死，下文每个数字都可由此脚本复现）：
- 线程层 = 该 `thread_id` 下的 MSG 条数（= `turn_index` 最大值 + 1，本臂两口径实测一致）；
- scope 由 `thread_id` 形态判定：含 `-PUB-` ⇒ PUBLIC；`-G<group>-` ⇒ GROUP；否则 DM；
- **尾截断线程** = `min(round) > maxround - (max_turns - 1)`，即起跑后剩余回合不足以长到封顶；
  这类线程的"短"来自**运行结束**而非对话机制，抽层时应单列或排除；
- `非尾` 分母 = DM 线程中非尾截断者。

用法：
  python3 tools/b4/layer_census.py --run v2/evidence/run_a5_real_n16r42_seed42/run.jsonl \
      --max-turns 6 [--json-out v2/evidence/batch4_layer_census.json]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict

MSG = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
GID = re.compile(r"-G[^-]+-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--max-turns", type=int, default=6)
    ap.add_argument("--json-out", default=None)
    a = ap.parse_args()

    msgs, calls, cached = [], Counter(), Counter()
    maxround = 0
    for line in open(a.run, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        t = d.get("type")
        maxround = max(maxround, int(d.get("round") or 0))
        if t in MSG:
            p = d.get("payload") or {}
            msgs.append({"tid": p.get("thread_id"), "turn": p.get("turn_index"),
                         "rnd": int(d.get("round") or 0), "actor": d.get("actor"),
                         "to": p.get("to"), "type": t})
        elif t == "LLM_CALL":
            p = d.get("payload") or {}
            calls[p.get("purpose")] += 1
            if p.get("cached"):
                cached[p.get("purpose")] += 1

    th = defaultdict(list)
    for m in msgs:
        th[m["tid"]].append(m)
    for v in th.values():
        v.sort(key=lambda x: (x["rnd"], x["turn"] if x["turn"] is not None else 0))

    def scope(tid: str) -> str:
        if "-PUB-" in tid:
            return "PUBLIC"
        if GID.search(tid):
            return "GROUP"
        return "DM"

    tail_cut = maxround - (a.max_turns - 1)
    start = {tid: min(x["rnd"] for x in v) for tid, v in th.items()}
    # **三个 scope 一律出键**（即使 0 条）：让"某 scope 为 0"是**可读事实**而不是"脚本漏算"。
    # 本臂 GROUP=0 属**事实**——GROUP 通路存在（`agent.py::_GROUP_TEMPLATES` + `_initiate` 的
    # `len(parts) >= 3` 门），只是本次没有模板同时满足"是 group 模板且参与者 ≥3"。
    SCOPES = ("DM", "GROUP", "PUBLIC")
    by_scope_len = {s_: Counter() for s_ in SCOPES}
    threads_by_scope = {s_: 0 for s_ in SCOPES}
    for tid, v in th.items():
        sc = scope(tid)
        by_scope_len[sc][len(v)] += 1
        threads_by_scope[sc] += 1

    dm = {t: v for t, v in th.items() if scope(t) == "DM"}
    dm_notail = {t: v for t, v in dm.items() if start[t] <= tail_cut}
    k_all = sum(1 for v in th.values() if len(v) in (2, 3))
    k_dm = sum(1 for v in dm.values() if len(v) in (2, 3))
    k_dm_nt = sum(1 for v in dm_notail.values() if len(v) in (2, 3))

    # 1-turn 归因（只看 1 条消息的线程）
    cap = 2
    per_actor_slot_init, per_actor_slot_reply = Counter(), Counter()
    slots = ["morning", "afternoon", "evening", "night"]
    rps = 3

    def slot_of(r):
        per_day = len(slots) * rps
        return f"day{(r // per_day) % 7}-{slots[(r % per_day) // rps]}"

    for m in msgs:
        key = (m["actor"], slot_of(m["rnd"]))
        if m["turn"] == 0:
            per_actor_slot_init[key] += 1
        else:
            per_actor_slot_reply[key] += 1
    cause = Counter()
    for tid, v in th.items():
        if len(v) != 1:
            continue
        m = v[0]
        if scope(tid) != "DM":
            cause["A_非DM不可回"] += 1
        elif m["rnd"] >= maxround:
            cause["B_尾回合发起(无后续回合)"] += 1
        elif m["to"] and per_actor_slot_reply[(m["to"], slot_of(m["rnd"]))] >= cap:
            cause["C_对端该slot回复额度已满"] += 1
        else:
            cause["D_对端当回合选了别的线程/未行动"] += 1

    gaps = Counter()
    for v in th.values():
        for x, y in zip(v, v[1:]):
            gaps[y["rnd"] - x["rnd"]] += 1

    out = {
        "run": a.run,
        "maxround": maxround,
        "max_turns_param": a.max_turns,
        "n_msgs": len(msgs),
        "n_threads": len(th),
        "msgs_by_type": dict(Counter(m["type"] for m in msgs)),
        "threads_by_scope": threads_by_scope,
        "len_by_scope": {s_: dict(sorted(c.items())) for s_, c in by_scope_len.items()},
        "scope_zero_note": ("threads_by_scope / len_by_scope 三个 scope 键恒存在；某 scope 为 0 或 {} "
                            "表示本臂**没有该类线程**（不是脚本漏算）。GROUP 通路存在："
                            "life/agent.py::_GROUP_TEMPLATES 且 _initiate 要求 len(parts)>=3。"),
        "layer_2_3": {
            "all_threads": {"k": k_all, "n": len(th), "pct": round(100.0 * k_all / len(th), 2)},
            "dm_only": {"k": k_dm, "n": len(dm), "pct": round(100.0 * k_dm / len(dm), 2)},
            "dm_non_tail": {"k": k_dm_nt, "n": len(dm_notail),
                            "pct": round(100.0 * k_dm_nt / len(dm_notail), 2)},
        },
        "tail_cut_round": tail_cut,
        "tail_born": {"all": sum(1 for t in th if start[t] > tail_cut),
                      "dm": sum(1 for t in dm if start[t] > tail_cut)},
        "one_turn_causes": dict(cause),
        "turn_gap_rounds": dict(sorted(gaps.items())),
        "cap_reached_6": {"k": sum(1 for v in dm.values() if len(v) >= a.max_turns), "n": len(dm),
                          "pct": round(100.0 * sum(1 for v in dm.values() if len(v) >= a.max_turns) / len(dm), 2)},
        "per_actor_slot": {"init_max": max(per_actor_slot_init.values() or [0]),
                           "reply_max": max(per_actor_slot_reply.values() or [0]),
                           "init_total": sum(per_actor_slot_init.values()),
                           "reply_total": sum(per_actor_slot_reply.values())},
        "llm_calls": {"by_purpose": dict(calls), "total": sum(calls.values()),
                      "cached_total": sum(cached.values()),
                      "network_total": sum(calls.values()) - sum(cached.values())},
        "layer_2_3_thread_ids": sorted([t for t, v in th.items() if len(v) in (2, 3)]),
    }
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    print(txt)
    if a.json_out:
        open(a.json_out, "w", encoding="utf-8").write(txt + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
