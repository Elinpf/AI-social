#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.2 诊断：**对端选择是不是"均匀随机抽"**

代码事实（`code/life/planner.py::_participants`，master @ 2a52123）：
    chosen.append(_pick(f"{agent_id}|{slot_id}|{tid}|p{i}", rem))
⇒ 对端 = 对 `peers` 做**种子哈希均匀抽取**，**不看**关系、亲疏、欠回复、地点/时段。
本工具从日志量出这件事的**可观测后果**，不读代码也不猜。

口径（并列输出，名字带后缀，§3.113）：
- `n_agents` / `n_peers_max`            : 出现在 from/to 里的居民数；最大可能对端数
- `pairs_observed` / `pairs_possible`   : 无向 pair 覆盖（完全图 = n*(n-1)/2）
- `pair_coverage_rate`                  : pairs_observed / pairs_possible
- `n_init`                              : 发起数（turn_index==0 且有 to）
- `top1_partner_share`                  : 单个居民最强对端占其发起数的最大比例（看有没有"固定搭子"）
- `repeat_pair_rate`                    : 发起中，"这对组合此前已出现过"的比例（看有没有持续关系）
- `herfindahl_mean`                     : 各居民对端分布 HHI 均值（均匀随机 ≈ 1/k，有偏好会显著更高）
- `uniform_expected_hhi_mean`           : 同 k 下均匀随机的期望 HHI = 1/k（作参照，**不是判据**）

用法：python3 tools/d21/partner_choice_stats.py --log ARM=path [--out-json ...]
"""
import argparse, json, sys
from collections import defaultdict, Counter
from itertools import combinations

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def load(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG_TYPES:
            continue
        pl = e.get("payload") or {}
        if pl.get("from") is None:
            continue
        rows.append({"ts": e.get("mono_ts") or 0, "frm": pl["from"], "to": pl.get("to"),
                     "turn": pl.get("turn_index"), "uid": pl.get("msg_uid")})
    rows.sort(key=lambda r: (r["ts"], str(r["uid"])))
    return rows


def analyse(rows):
    agents = sorted({r["frm"] for r in rows} | {r["to"] for r in rows if r["to"]})
    n = len(agents)
    pairs_possible = n * (n - 1) // 2 if n >= 2 else 0

    directed = Counter((r["frm"], r["to"]) for r in rows if r["to"])
    undirected = Counter()
    for (a, b), c in directed.items():
        undirected[tuple(sorted((a, b)))] += c

    inits = [r for r in rows if r["turn"] == 0 and r["to"]]
    seen = set()
    repeat = 0
    for r in inits:
        key = tuple(sorted((r["frm"], r["to"])))
        if key in seen:
            repeat += 1
        else:
            seen.add(key)

    by_agent = defaultdict(Counter)
    for r in inits:
        by_agent[r["frm"]][r["to"]] += 1

    hhis, top1, ks = [], [], []
    for a, c in by_agent.items():
        tot = sum(c.values())
        if tot == 0:
            continue
        hhis.append(sum((v / tot) ** 2 for v in c.values()))
        top1.append(max(c.values()) / tot)
        ks.append(len(c))

    def mean(xs):
        return round(sum(xs) / len(xs), 4) if xs else None

    return {
        "n_agents": n,
        "n_init": len(inits),
        "n_initiators": len(by_agent),
        "pairs_observed": len(undirected),
        "pairs_possible": pairs_possible,
        "pair_coverage_rate": round(100.0 * len(undirected) / pairs_possible, 2) if pairs_possible else None,
        "repeat_pair_rate": round(100.0 * repeat / len(inits), 2) if inits else None,
        "top1_partner_share_max": round(100.0 * max(top1), 2) if top1 else None,
        "top1_partner_share_mean": round(100.0 * mean(top1), 2) if top1 else None,
        "herfindahl_mean": mean(hhis),
        "uniform_expected_hhi_mean": round(mean([1.0 / k for k in ks]), 4) if ks else None,
        "distinct_partners_mean": mean(ks),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", action="append", required=True, help="ARM=path")
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()
    out = {}
    for spec in a.log:
        arm, _, path = spec.partition("=")
        try:
            out[arm] = analyse(load(path))
        except FileNotFoundError:
            out[arm] = {"error": "missing"}
        out[arm]["log"] = path
        print(f"[{arm}] {json.dumps(out[arm], ensure_ascii=False)}", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    if a.out_json:
        json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
