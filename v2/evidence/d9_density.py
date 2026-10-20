#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9 对话往来密度读数器（只读 run.jsonl，零 LLM，不改任何业务代码）。

口径来源：
  * 消息抽取与线程分组**直接复用** tools/d5/dialogue_metrics.py 的 extract_messages / group_threads
    （保证与 F-2b 同一口径、同一分母），不另写解析。
  * 「轮数」= 线程内 turn_index 去重后的个数（与 d5 的 S-1C、dialogue_compare.py 的 distinct_turns、
    D7 的「6 轮 = 18 条消息」同一口径）；「条数」= 线程内消息条数。
  * 「每 slot 发消息数」= 同一 agent 在同一 (day, slot) 内发出的 MSG 条数（对应 max_messages_per_slot 的作用单位）。

用法：
    python3 v2/evidence/d9_density.py --log <run.jsonl> --out-json <out.json> [--out-md <out.md>]

退出码：0 成功；2 输入不可用。
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "d5"))
import dialogue_metrics as dm  # noqa: E402


def dist(vals):
    if not vals:
        return {"n": 0}
    s = sorted(vals)
    def pct(q):
        k = (len(s) - 1) * q
        lo, hi = int(k), min(int(k) + 1, len(s) - 1)
        return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 4)
    return {
        "n": len(s), "min": s[0], "max": s[-1],
        "mean": round(st.mean(s), 4), "median": round(st.median(s), 4),
        "p10": pct(0.10), "p50": pct(0.50), "p90": pct(0.90),
        "stdev": round(st.pstdev(s), 4) if len(s) > 1 else 0.0,
        "histogram": {str(k): v for k, v in sorted(Counter(s).items())},
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    a = ap.parse_args(argv)

    if not os.path.isfile(a.log):
        print(f"[FAIL] 缺日志: {a.log}", file=sys.stderr)
        return 2
    recs, _info = dm.read_run(a.log)
    msgs = dm.extract_messages(recs)
    if not msgs:
        print("[FAIL] 日志内无消息事件", file=sys.stderr)
        return 2

    threads, schema = dm.group_threads(msgs)
    # group_threads 的 key 形如 T:<tid>；对外统一去掉前缀
    tinfo = []
    for key in sorted(threads):
        th = threads[key]
        rounds = len({m["turn_index"] for m in th if m["turn_index"] is not None})
        speakers = {str(m["from"]) for m in th}
        tinfo.append({
            "thread_id": key[2:] if key.startswith("T:") else key,
            "channel": Counter(m["channel"] for m in th).most_common(1)[0][0],
            "n_msgs": len(th),
            "n_rounds": rounds,
            "n_speakers": len(speakers),
            "speakers": sorted(speakers),
            "reply_msgs": sum(1 for m in th if m.get("reply_to")),
        })

    n_threads = len(tinfo)
    n_rounds_list = [t["n_rounds"] for t in tinfo]
    n_msgs_list = [t["n_msgs"] for t in tinfo]
    n_speakers_list = [t["n_speakers"] for t in tinfo]

    ge3r = [t for t in tinfo if t["n_rounds"] >= 3]
    ge6r = [t for t in tinfo if t["n_rounds"] >= 6]
    ge3s = [t for t in tinfo if t["n_speakers"] >= 3]

    def top(lst, k="n_msgs"):
        return sorted(lst, key=lambda t: (-t[k], t["thread_id"]))[0] if lst else None

    longest_msgs = top(tinfo, "n_msgs")
    longest_rounds = top(tinfo, "n_rounds")

    # ---- 每 agent 每 (day, slot) 发消息数（max_messages_per_slot 的作用单位）
    slot_cnt = Counter()
    for m in msgs:
        slot_cnt[(str(m["from"]), m["day"], m["slot"])] += 1
    slot_vals = list(slot_cnt.values())

    # ---- 每 agent 每 day 发消息数（参考量，不受该参数直接约束）
    day_cnt = Counter((str(m["from"]), m["day"]) for m in msgs)

    out = {
        "source": os.path.abspath(a.log),
        "thread_schema": schema,
        "n_messages": len(msgs),
        "n_threads": n_threads,
        "channel_msg_counts": dict(Counter(m["channel"] for m in msgs)),
        "threads": {
            "n_rounds": dist(n_rounds_list),
            "n_msgs": dist(n_msgs_list),
            "n_speakers": dist(n_speakers_list),
            "mean_roundtrip": round(st.mean(n_rounds_list), 4) if n_threads else None,
            "mean_msgs_per_thread": round(st.mean(n_msgs_list), 4) if n_threads else None,
            "threads_ge3_rounds": len(ge3r),
            "threads_ge6_rounds": len(ge6r),
            "threads_ge3_speakers": len(ge3s),
            "ratio_ge3_rounds": dm.rate(len(ge3r), n_threads),
            "ratio_ge6_rounds": dm.rate(len(ge6r), n_threads),
            "ratio_ge3_speakers": dm.rate(len(ge3s), n_threads),
            "longest_by_msgs": longest_msgs,
            "longest_by_rounds": longest_rounds,
            "top10_by_msgs": sorted(tinfo, key=lambda t: -t["n_msgs"])[:10],
            "definitions": {
                "n_rounds": "线程内 turn_index 去重个数（群聊同轮多人并发只计 1 轮）；与 d5 S-1C / D7 一致",
                "n_msgs": "线程内 MSG 条数（说话人交替段数）",
                "n_speakers": "线程内不同 from 的 agent 数",
            },
        },
        "per_slot": {
            "unit": "同一 agent 在同一 (day, slot) 内发出的 MSG 条数",
            "n_units": len(slot_cnt),
            "dist": dist(slot_vals),
            "units_at_cap2": sum(1 for v in slot_vals if v == 2),
            "units_ge3": sum(1 for v in slot_vals if v >= 3),
            "units_eq1": sum(1 for v in slot_vals if v == 1),
            "cap2_binding_note": ("all_units_le_2 = %s；若为 True 且 units_at_cap2 占比高，说明 max_messages_per_slot=2 是硬约束"
                                  % (max(slot_vals) <= 2)),
        },
        "per_agent_day": {
            "unit": "同一 agent 在同一 day 内发出的 MSG 条数（参考，不受 max_messages_per_slot 直接约束）",
            "dist": dist(list(day_cnt.values())),
        },
        "reply_coverage": dm.rate(sum(1 for m in msgs if m.get("reply_to")), len(msgs)),
    }

    if a.out_json:
        with open(a.out_json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)

    # 注：`t` 必须在 `if a.out_md:` 之前绑定 —— 否则只传 --out-json 时，
    # 下方 stdout 摘要读 t[...] 会抛 UnboundLocalError。纯赋值位置调整，不动任何计算逻辑。
    t = out["threads"]

    if a.out_md:
        lines = [
            "# D9 对话往来密度读数", "",
            f"- 来源：`{a.log}`", f"- 消息数：{out['n_messages']}；线程数：{n_threads}；schema={schema}", "",
            "## 线程级（tid 口径）",
            f"- 轮数（turn_index 去重）分布：{t['n_rounds']['histogram']}",
            f"- 条数分布：{t['n_msgs']['histogram']}",
            f"- 平均往返轮数：{t['mean_roundtrip']}；平均条数：{t['mean_msgs_per_thread']}",
            f"- ≥3 轮线程：{t['threads_ge3_rounds']}/{n_threads} = {t['ratio_ge3_rounds']}",
            f"- ≥6 轮线程：{t['threads_ge6_rounds']}/{n_threads} = {t['ratio_ge6_rounds']}",
            f"- ≥3 发言者线程：{t['threads_ge3_speakers']}/{n_threads} = {t['ratio_ge3_speakers']}",
            f"- 最长线程（按条数）：{json.dumps(t['longest_by_msgs'], ensure_ascii=False)}",
            f"- 最长线程（按轮数）：{json.dumps(t['longest_by_rounds'], ensure_ascii=False)}",
            "",
            "## 每 agent 每 (day, slot) 发消息数（max_messages_per_slot 作用单位）",
            f"- 单位数：{out['per_slot']['n_units']}；分布：{out['per_slot']['dist']['histogram']}",
            f"- 命中上限 2 的单位：{out['per_slot']['units_at_cap2']}；≥3：{out['per_slot']['units_ge3']}",
        ]
        with open(a.out_md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    print(json.dumps({
        "n_messages": out["n_messages"], "n_threads": n_threads,
        "mean_roundtrip": t["mean_roundtrip"], "max_rounds": t["n_rounds"]["max"],
        "max_msgs": t["n_msgs"]["max"],
        "ge3_rounds": t["threads_ge3_rounds"], "ge6_rounds": t["threads_ge6_rounds"],
        "ge3_speakers": t["threads_ge3_speakers"],
        "slot_units": out["per_slot"]["n_units"], "slot_at_cap2": out["per_slot"]["units_at_cap2"],
        "slot_ge3": out["per_slot"]["units_ge3"],
        "out_json": a.out_json, "out_md": a.out_md,
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
