#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""batch4 规格配套：**池子审计 + 排除名单校验**（只读，不跑 orchestration、不改 code/）。

三件事：
1. **`round` 三种取法对拍**（遵守 R1 边界 14：`round` 只能从 `msg_id` **次末段**取）
   - ✅ 正解：`msg_id` 次末段（`P-0-0` ⇒ round=0、`D-12-1` ⇒ round=12）
   - ❌ `msg_id` 末段 = `turn_index`
   - ❌ `thread_id` 末段（`-PUB-` 形态退化：末段恒 0，真实 min(round) 为 1–3）
   同时报告：台账事件自带的 `round` 字段与正解是否逐条相等（若相等，说明两者可互为校验）。
2. **尾截断判定**：`min(round) > maxround − (max_turns−1)`
3. **排除名单**：batch1∪batch2∪batch3 已用 `thread_id`（能查到的全部）+ 截断件；并校验两两交集 = 0。

用法：
  python3 tools/b4/pool_audit.py --run v2/evidence/run_a5_real_n16r42_seed42/run.jsonl \
      --max-turns 6 --json-out v2/evidence/batch4_pool_audit.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

MSG = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
TID = re.compile(r"thread=TH-[A-Za-z0-9-]+")

# 已用清单的**出处**（逐批写清 provenance，缺的部分明确标 NOT_ARCHIVED）
USED_SOURCES = {
    "batch2": ("v2/evidence/d12c_a5_batch2_raw_clean.txt", "thread="),
    "batch3": ("v2/evidence/d12c_batch3_sampled_raw.txt", "thread="),
}
# batch1 只有 2–3 轮层 4 条可在 `d12c_short_thread_tail_truncation.md` 表里核到；
# 其 4–6 轮层 8 条**没有任何抽样清单落盘** ⇒ 标 NOT_ARCHIVED，不得假装已知。
BATCH1_SHORT_KNOWN = [
    "TH-P016-P005-18", "TH-P002-P007-39", "TH-P005-P013-39", "TH-P002-P007-40",
]


def load_messages(path):
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("type") not in MSG:
            continue
        p = d.get("payload") or {}
        out.append({"tid": p.get("thread_id"), "turn": p.get("turn_index"),
                    "mid": p.get("msg_id"), "rnd_field": d.get("round"),
                    "actor": d.get("actor"), "type": d.get("type")})
    return out


def seg(x):
    return (x or "").split("-")


def round_from_msgid_second_last(mid):
    s = seg(mid)
    return int(s[-2]) if len(s) >= 2 and s[-2].lstrip("-").isdigit() else None


def round_from_msgid_last(mid):
    s = seg(mid)
    return int(s[-1]) if len(s) >= 1 and s[-1].lstrip("-").isdigit() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--max-turns", type=int, default=6)
    ap.add_argument("--json-out", default=None)
    a = ap.parse_args()

    msgs = load_messages(a.run)
    maxround = max(int(m["rnd_field"] or 0) for m in msgs)
    agree_field = sum(1 for m in msgs if round_from_msgid_second_last(m["mid"]) == int(m["rnd_field"]))

    th = defaultdict(list)
    for m in msgs:
        th[m["tid"]].append(m)
    for v in th.values():
        v.sort(key=lambda x: (x["rnd_field"], x["turn"] if x["turn"] is not None else 0))

    tail_cut = maxround - (a.max_turns - 1)
    per_thread = {}
    for tid, v in th.items():
        r_second = min(round_from_msgid_second_last(x["mid"]) for x in v)
        r_last = min(round_from_msgid_last(x["mid"]) for x in v)
        tid_last = seg(tid)[-1]
        tid_last_int = int(tid_last) if tid_last.isdigit() else None
        per_thread[tid] = {
            "len": len(v),
            "min_round_msgid_second_last": r_second,
            "min_round_msgid_last_WRONG": r_last,
            "thread_id_last_seg": tid_last_int,
            "truncated": r_second > tail_cut,
            "scope": ("PUBLIC" if "-PUB-" in tid else ("GROUP" if re.search(r"-G[^-]+-", tid) else "DM")),
        }

    # 三种取法的分歧计数（R1 边界 14 的两个坑）
    same_tid_last = sum(1 for t, d in per_thread.items()
                        if d["thread_id_last_seg"] == d["min_round_msgid_second_last"])
    same_last_seg = sum(1 for d in per_thread.values()
                        if d["min_round_msgid_last_WRONG"] == d["min_round_msgid_second_last"])

    # 已用清单
    used = {}
    for tag, (p, _) in USED_SOURCES.items():
        used[tag] = sorted(set(TID.findall(Path(p).read_text(encoding="utf-8")) and
                               [x.replace("thread=", "") for x in TID.findall(Path(p).read_text(encoding="utf-8"))]))
    used["batch1_short_known"] = sorted(BATCH1_SHORT_KNOWN)
    used["batch1_long_8"] = "NOT_ARCHIVED（无抽样清单落盘，不得假装已知）"

    # 交集校验（只对**能核实**的集合做）
    known_sets = {k: set(v) for k, v in used.items() if isinstance(v, list)}
    inter = {}
    ks = sorted(known_sets)
    for i, k1 in enumerate(ks):
        for k2 in ks[i + 1:]:
            inter[f"{k1}∩{k2}"] = sorted(known_sets[k1] & known_sets[k2])

    known_used = set().union(*known_sets.values())
    pool_ids = set(th)
    unknown_used = sorted(known_used - pool_ids)      # 已用但不在本臂 ⇒ 记录（应为空）

    # 层 × (总数/已用/截断/剩余)
    def layer(n):
        return "1" if n == 1 else ("2-3" if n in (2, 3) else ("4-6" if n >= 4 else "0"))

    table = {}
    for lay in ("1", "2-3", "4-6"):
        ids = [t for t, d in per_thread.items() if layer(d["len"]) == lay]
        used_hit = [t for t in ids if t in known_used]
        trunc = [t for t in ids if per_thread[t]["truncated"]]
        remaining = [t for t in ids if t not in known_used and not per_thread[t]["truncated"]]
        table[lay] = {
            "total": len(ids),
            "known_used": len(used_hit),
            "truncated": len(trunc),
            "remaining_clean": len(remaining),
            "remaining_clean_ids": sorted(remaining),
        }

    out = {
        "run": a.run,
        "maxround": maxround,
        "tail_cut_round": tail_cut,
        "round_sourcing_check": {
            "ledger_round_field_equals_msgid_second_last": f"{agree_field}/{len(msgs)}",
            "msgid_last_seg_equals_second_last(threads)": f"{same_last_seg}/{len(per_thread)}  ← 末段是 turn_index，取它会把 min(round) 全算成 0",
            "thread_id_last_seg_equals_second_last(threads)": f"{same_tid_last}/{len(per_thread)}  ← 不相等的都是 -PUB-（R1 边界14：局部对拍会骗人）",
            "rule": "round 只能从 msg_id **次末段**取（P-0-0 ⇒ 0；D-12-1 ⇒ 12）",
        },
        "used_lists": used,
        "pairwise_intersections": inter,
        "known_used_total": len(known_used),
        "known_used_not_in_this_run": unknown_used,
        "pool_by_layer": table,
        "truncated_thread_ids": sorted(t for t, d in per_thread.items() if d["truncated"]),
        "short_2_3_detail": {t: per_thread[t] for t in per_thread if per_thread[t]["len"] in (2, 3)},
    }
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    print(txt)
    if a.json_out:
        Path(a.json_out).write_text(txt + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
