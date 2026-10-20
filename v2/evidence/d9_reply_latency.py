#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9 回复延迟分布（reply latency）—— 只读 run.jsonl，零 LLM，不改业务代码。

口径：
  * 消息抽取复用 tools/d5/dialogue_metrics.py::extract_messages（与 F 系列同分母来源）。
  * **回复指针用 `payload.reply_to`，其值即目标消息的 `msg_uid`（形如 `<seed>:<seq>`），
    绝不用会撞号的 `msg_id`**（A0 实测 msg_id 仅 216 个不同值 / 686 条消息）。
  * 延迟 = 回复所在 round − 被回复消息所在 round（按 round 计，对应 reply_window_rounds 的单位）。
  * 分母 = 全部带 reply_to 的消息条数。

用法：
    python3 v2/evidence/d9_reply_latency.py --log <run.jsonl> --out-json <o.json> [--out-md <o.md>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "d5"))
import dialogue_metrics as dm  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    a = ap.parse_args(argv)

    if not os.path.isfile(a.log):
        print(f"[FAIL] 缺日志: {a.log}", file=sys.stderr)
        return 2
    recs, _ = dm.read_run(a.log)
    msgs = dm.extract_messages(recs)
    by_uid = {m["msg_uid"]: m for m in msgs}

    replies = [m for m in msgs if m.get("reply_to")]
    dist = Counter()
    cross_thread = 0
    missing = 0
    per_channel = defaultdict(Counter)
    for m in replies:
        t = by_uid.get(m["reply_to"])
        if t is None:
            missing += 1
            continue
        if t["thread_id"] != m["thread_id"]:
            cross_thread += 1
        lat = int(m["round"]) - int(t["round"])
        dist[lat] += 1
        per_channel[m["channel"]][lat] += 1

    total = sum(dist.values())
    ge3 = sum(v for k, v in dist.items() if k >= 3)
    out = {
        "source": os.path.abspath(a.log),
        "n_msgs": len(msgs),
        "replies": len(replies),
        "resolved": total,
        "unresolved_reply_to": missing,
        "cross_thread_pointers": cross_thread,
        "latency_rounds": {str(k): v for k, v in sorted(dist.items())},
        "by_channel": {ch: {str(k): v for k, v in sorted(c.items())} for ch, c in per_channel.items()},
        "denominator": total,
        "latency_eq0": dist.get(0, 0),
        "latency_eq1": dist.get(1, 0),
        "latency_eq2": dist.get(2, 0),
        "latency_ge3": ge3,
        "rate_ge3": (round(ge3 / total, 6) if total else None),
        "pointer_field": "payload.reply_to 存的是目标 msg_uid（非 msg_id）",
        "note_overwindow_unreplied": "「因超窗未被回复」无法直接判定：日志无「曾被看见但未回」的记录；标未验证",
    }

    if a.out_json:
        with open(a.out_json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    if a.out_md:
        with open(a.out_md, "w", encoding="utf-8") as f:
            f.write("# D9 回复延迟分布（reply latency）\n\n")
            f.write(f"- 来源：`{a.log}`\n- 分母（带 reply_to 的消息条数）：**{total}**\n")
            f.write(f"- 延迟（round 差）分布：{out['latency_rounds']}\n")
            f.write(f"- 0 回合 {out['latency_eq0']} / 1 回合 {out['latency_eq1']} / "
                    f"2 回合 {out['latency_eq2']} / ≥3 回合 **{ge3}**\n")
            f.write(f"- 未解析 reply_to：{missing}；跨线程指针：{cross_thread}\n")

    print(json.dumps({k: out[k] for k in ("n_msgs", "replies", "resolved", "unresolved_reply_to",
                                         "cross_thread_pointers", "latency_rounds", "denominator",
                                         "latency_ge3", "rate_ge3")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
