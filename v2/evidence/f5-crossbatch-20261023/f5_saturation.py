#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-5 天花板/饱和诊断（**解释性诊断**，不替代指标值）。

指标值一律以 tools/d5/dialogue_metrics.py 输出为准；本脚本只回答一个问题：
「在这个窗口里，F-5 为什么是 1.0（或 0.0），它还有区分度吗？」

判定规则与 dialogue_metrics.py 的 F-5 完全相同（照抄其 rule 字符串）：
  习惯 = 同一 agent 在同一 (slot, place) 出现 ≥3 天
  强度 = 有习惯的 agent / agent 总数
输出额外的结构性事实：
  - 每个 (agent, slot, place) 桶的天数直方图；
  - ≥3 天桶的占比；
  - place=None 的消息占全部计入消息的比例（None 自成桶）。
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict

MSG_TYPES = {"MSG_DM", "MSG_PUBLIC", "MSG_GROUP"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    buckets: Dict[tuple, set] = defaultdict(set)  # type: ignore[name-defined]
    n_msg = n_day_known = n_place_none = 0
    with open(a.log, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:  # noqa: BLE001
                continue
            if r.get("type") not in MSG_TYPES:
                continue
            p = r.get("payload") or {}
            n_msg += 1
            day = p.get("day")
            if day is None:
                continue
            n_day_known += 1
            place = p.get("place")
            if place is None:
                n_place_none += 1
            buckets[(str(p.get("from") or r.get("actor")), str(p.get("slot")), str(place))].add(day)

    hist = Counter(len(v) for v in buckets.values())
    ge3 = sum(c for d, c in hist.items() if d >= 3)
    out = {
        "log": os.path.abspath(a.log),
        "n_messages_counted": n_msg,
        "n_messages_with_day": n_day_known,
        "n_place_none_msgs": n_place_none,
        "place_none_share_of_dayknown": round(n_place_none / n_day_known, 6) if n_day_known else None,
        "n_buckets": len(buckets),
        "bucket_days_histogram": {str(k): v for k, v in sorted(hist.items())},
        "buckets_ge3_days": ge3,
        "buckets_ge3_share": round(ge3 / len(buckets), 6) if buckets else None,
        "diagnostic_only": True,
        "note": "解释性诊断；F-5 指标值以 metrics_*.json 的 F-5_habit_repetition 为准",
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
    print(json.dumps({"saturation_out": a.out, "n_buckets": out["n_buckets"],
                      "buckets_ge3_share": out["buckets_ge3_share"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
