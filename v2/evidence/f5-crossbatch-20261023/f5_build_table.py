#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把每批 metrics_*.json + coverage_*.json 汇成一张跨批对照 CSV。

原则：
- 指标值**只读** dialogue_metrics.py 的 JSON 输出，不重算；
- 分子分母：den = n_distinct_agents（= 工具里 agents_all 的基数），
  num = habit_strength * den（工具输出的是 num/den 的精确商，16 分母下可逆；
  脚本里做可逆性断言，若残差 >1e-6 直接报错，不猜）；
- 口径可比性：day 窗口 < 3 的批次，F-5「同一 (slot,place) ≥3 天」结构上不可能成立，
  标 floor_limited（不可比），不参与跨批比较，也不合并求均值。
"""
from __future__ import annotations

import argparse
import csv
import json
import os

BATCHES = [
    # (tag, 说明)
    ("d12b_off", "d12b off（seed7 n16 r24）"),
    ("d12b_on", "d12b on（seed7 n16 r24）"),
    ("d12c_off", "d12c off（seed42 n16 r60）"),
    ("d12c_on", "d12c on（seed42 n16 r60）"),
    ("d12d_on", "d12d on（seed42 n16 r60 含 DEDUP）"),
    ("scene_anchor_off", "scene_anchor off（seed42 n16 r24）"),
    ("scene_anchor_on", "scene_anchor on（seed42 n16 r24）"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = []
    for tag, label in BATCHES:
        mj = os.path.join(a.dir, "raw", f"metrics_{tag}.json")
        cj = os.path.join(a.dir, "raw", f"coverage_{tag}.json")
        if not (os.path.exists(mj) and os.path.exists(cj)):
            print(f"[SKIP] {tag}: 缺少 metrics/coverage json")
            continue
        M = json.load(open(mj, encoding="utf-8"))
        C = json.load(open(cj, encoding="utf-8"))
        f5 = M["F-5_habit_repetition"]
        f1 = M["F-1_chatter"]
        den = C["n_distinct_agents"]
        hs = f5["habit_strength"]
        num = None
        if hs is not None and den:
            num_f = hs * den
            num = int(round(num_f))
            assert abs(num_f - num) < 1e-6, f"{tag}: habit_strength*den 不可逆 ({num_f})"
        func = f1["functional_msgs"]
        n_msg = M["meta"]["n_messages"]
        days = C["n_days"]
        floor_limited = days < 3
        rows.append({
            "batch": tag,
            "label": label,
            "log": M["inputs"]["log"],
            "run_sha256": M["inputs"]["run_sha256"],
            "seed": M["inputs"]["seed"],
            "n_agents": den,
            "n_rounds": M["E_efficiency"].get("n_rounds"),
            "n_messages": n_msg,
            "n_days_covered": days,
            "day_values": "|".join(C["day_values"]),
            "null_place_rate": C["null_place_rate"],
            "F5_habit_strength": hs,
            "F5_strong_agents": num,
            "F5_den_agents": den,
            "F5b_max_repeat_days_mean": f5["max_repeat_days_mean"],
            "F1_nonfunctional_chatter_rate": f1["nonfunctional_chatter_rate"],
            "F1_nonfunctional_msgs": None if f1["nonfunctional_chatter_rate"] is None else n_msg - func,
            "F1_den_msgs": n_msg,
            "admission_verdict": M["admission"]["verdict"],
            "comparability": "floor_limited_days_lt_3" if floor_limited else "comparable_days_ge_3",
        })

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {a.out} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
