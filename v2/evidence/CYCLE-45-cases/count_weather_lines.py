#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""辅助观察：统计各批 MSG_DM/MSG_PUBLIC 正文中是否出现天气线索词。

仅作"该批是否有天气相关台词"的定位辅助，不作为效果结论（机制接通≠效果改善）。

用法：python3 v2/evidence/CYCLE-45-cases/count_weather_lines.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BATCHES = [
    "v2/evidence/run_weather_on_n16r24_seed42_c28",
    "v2/evidence/run_weather_off_n16r24_seed42_c28",
]
# 只做定位用的线索词（含季节/冷暖/天象），命中一条即在正文层面留痕
KW = ["天", "雨", "晴", "云", "风", "冷", "热", "暖", "凉", "阴", "潮", "露水", "开春", "节气"]


def main():
    for b in BATCHES:
        path = os.path.join(REPO, b, "run.jsonl")
        tot = hit = 0
        seqs = []
        for line in open(path, "rb"):
            o = json.loads(line.decode("utf-8"))
            if o.get("type") not in ("MSG_DM", "MSG_PUBLIC"):
                continue
            tot += 1
            body = o["payload"].get("body") or ""
            if any(k in body for k in KW):
                hit += 1
                seqs.append(o["seq"])
        print("%s  msgs=%d  with_weather_lexicon=%d  pct=%.2f%%" % (b, tot, hit, 100.0 * hit / tot if tot else 0.0))
        print("  seqs=%s" % seqs[:40])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
