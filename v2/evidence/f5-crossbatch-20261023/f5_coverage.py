#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-5 复算的**覆盖度事实**提取器（不是指标实现）。

为什么需要它：现有 tools/d5/dialogue_metrics.py 只输出 F-5 的比率
（habit_strength = strong/agents、max_repeat_days_mean），不输出：
  1) 该批日志覆盖了几天（day 集合大小）——决定 F-5「≥3 天」是否可能成立；
  2) 消息里 place 缺失率——place=None 会被并入 (slot, None) 桶，影响口径解释；
  3) 分子分母原始计数（strong 数 / agent 数）。
本脚本只做上述**事实计数**（字段取值分布），不重复实现 F-5 判定逻辑；
F-5 的判定结论一律取自 dialogue_metrics.py 的 JSON 输出。

字段抽取与 dialogue_metrics.extract_messages 完全一致：
  day = payload.day, slot = payload.slot, place = payload.place,
  from = payload.from or record.actor
（对齐 tools/d5/dialogue_metrics.py 第 200~232 行）
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter

MSG_TYPES = {"MSG_DM", "MSG_PUBLIC", "MSG_GROUP"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    n_msg = 0
    days: Counter = Counter()
    slots: Counter = Counter()
    places: Counter = Counter()
    null_place = 0
    agents = set()
    rounds = set()

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
            days[str(p.get("day"))] += 1
            slots[str(p.get("slot"))] += 1
            pl = p.get("place")
            if pl is None:
                null_place += 1
                places["<None>"] += 1
            else:
                places[str(pl)] += 1
            agents.add(str(p.get("from") or r.get("actor")))
            rounds.add(r.get("round"))

    out = {
        "log": os.path.abspath(a.log),
        "n_messages": n_msg,
        "n_distinct_agents": len(agents),
        "n_distinct_rounds": len(rounds),
        "day_values": sorted(days.keys()),
        "n_days": len(days),
        "msgs_per_day": dict(sorted(days.items())),
        "slot_dist": dict(sorted(slots.items())),
        "place_dist": dict(sorted(places.items(), key=lambda kv: -kv[1])),
        "null_place_msgs": null_place,
        "null_place_rate": round(null_place / n_msg, 6) if n_msg else None,
        "note": "仅覆盖度事实；F-5 判定值不在此文件，见 metrics_*.json 的 F-5_habit_repetition",
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
    print(json.dumps({"coverage_out": a.out, "n_days": out["n_days"], "null_place_rate": out["null_place_rate"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
