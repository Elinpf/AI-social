#!/usr/bin/env python3
"""从 run.jsonl 抽取「完整多轮对话」原始样本（含 thread_id / 参与者 / 逐轮 body / seq 区间）。

用途：D2 验收③「至少 3 段完整多轮对话原始记录」，以及报告里的可复算示例。
**只读**：不写世界、不改日志。

用法：
  python3 tools/d2/extract_thread_samples.py --log <run.jsonl> --out <json> \
      [--min-turns 3] [--n-samples 5] [--include-public]

输出 schema：hitt.d2.thread_samples/1
  {"source":…, "run_sha256":…, "n_threads":…, "samples":[{thread_id, participants, turns, seq_range,
    messages:[{seq, round, type, from, to, turn_index, reply_to, msg_uid, body, ctx}]}]}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-turns", type=int, default=3)
    ap.add_argument("--n-samples", type=int, default=5)
    ap.add_argument("--include-public", action="store_true",
                    help="PUBLIC 线程天然长度为 1，默认不计入样本（只统计 DM/GROUP 往复）")
    a = ap.parse_args(argv)

    recs = []
    with open(a.log, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                recs.append(json.loads(line))
    h = hashlib.sha256(open(a.log, "rb").read()).hexdigest()

    threads: dict[str, list] = defaultdict(list)
    for r in recs:
        if r["type"] not in MSG_TYPES:
            continue
        p = r.get("payload") or {}
        if not a.include_public and r["type"] == "MSG_PUBLIC":
            continue
        tid = p.get("thread_id")
        if not tid:
            continue
        threads[tid].append({
            "seq": int(r["seq"]), "round": int(r["round"]), "type": r["type"],
            "from": p.get("from") or p.get("author"), "to": p.get("to"),
            "group_id": p.get("group_id"),
            "turn_index": p.get("turn_index"), "reply_to": p.get("reply_to"),
            "msg_uid": p.get("msg_uid"), "body": (p.get("body") or "").strip(),
            "ctx": p.get("ctx"),
        })

    for v in threads.values():
        v.sort(key=lambda m: (m["round"], m["seq"]))

    eligible = {t: v for t, v in threads.items() if len(v) >= a.min_turns}
    # 确定性选样：轮次多者优先，同轮次按 thread_id 字典序
    picked = sorted(eligible.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:a.n_samples]

    samples = []
    for tid, msgs in picked:
        parts = sorted({x for m in msgs for x in (m["from"], m["to"]) if x})
        samples.append({
            "thread_id": tid,
            "participants": parts,
            "turns": len(msgs),
            "seq_range": [msgs[0]["seq"], msgs[-1]["seq"]],
            "round_range": [msgs[0]["round"], msgs[-1]["round"]],
            "messages": msgs,
        })

    out = {
        "schema": "hitt.d2.thread_samples/1",
        "source": a.log,
        "run_sha256": h,
        "n_threads_total": len(threads),
        "n_threads_ge_min": len(eligible),
        "min_turns": a.min_turns,
        "samples": samples,
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"[samples] threads={len(threads)} ge{ a.min_turns}={len(eligible)} picked={len(samples)} -> {a.out}")
    for s in samples:
        print(f"  {s['thread_id']}  turns={s['turns']}  seq={s['seq_range']}  parts={s['participants']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
