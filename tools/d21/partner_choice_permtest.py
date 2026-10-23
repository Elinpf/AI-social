#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.2 诊断（二）：对端选择 HHI 的**置换检验** —— 实测比"均匀随机抽"更集中吗？

零假设 H0：每名居民的每次发起，都是从其候选池（默认 = 全体其他居民，n-1）**均匀独立**抽一个对端。
统计量：各居民对端分布的 HHI 均值（`herfindahl_mean`，见 partner_choice_stats.py）。
做法：保持每人的发起次数 k_i 不变，在池内均匀抽 k_i 次，算 HHI 均值，重复 B 次 ⇒ 零分布。
判读：实测值落在零分布 [q025, q975] 内 ⇒ **不能拒绝"均匀随机"**（��说明有偏好）。

注意（口径）：候选池取 n-1 是**上界假设**（真实 `peers` 可能更小，见 planner._participants）；
池越小、零分布越集中 ⇒ 本检验**偏保守**（更容易判"有偏好"）。若在保守假设下都不显著，
结论"看不出偏好"就成立。

用法：python3 tools/d21/partner_choice_permtest.py --log path --B 2000 --seed 42
"""
import argparse, json, random, statistics
from collections import defaultdict, Counter

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def load_inits(path):
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
        if pl.get("from") is None or pl.get("turn_index") != 0 or not pl.get("to"):
            continue
        rows.append((pl["from"], pl["to"]))
    return rows


def hhi_mean(by_agent):
    vals = []
    for c in by_agent.values():
        tot = sum(c.values())
        if tot:
            vals.append(sum((v / tot) ** 2 for v in c.values()))
    return sum(vals) / len(vals) if vals else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pool", choices=["all_others", "observed_union"], default="all_others")
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()

    inits = load_inits(a.log)
    agents = sorted({x for pair in inits for x in pair})
    by_agent = defaultdict(Counter)
    for frm, to in inits:
        by_agent[frm][to] += 1
    obs = hhi_mean(by_agent)

    rng = random.Random(a.seed)
    sims = []
    for _ in range(a.B):
        sim = defaultdict(Counter)
        for ag, c in by_agent.items():
            k = sum(c.values())
            if a.pool == "all_others":
                pool = [x for x in agents if x != ag]
            else:
                pool = sorted(set(agents) | set(c.keys()) - {ag})
            for _ in range(k):
                sim[ag][rng.choice(pool)] += 1
        sims.append(hhi_mean(sim))
    sims.sort()
    lo, hi = sims[int(0.025 * a.B)], sims[int(0.975 * a.B) - 1]
    p_ge = sum(1 for s in sims if s >= obs) / a.B           # 单侧：比随机更集中
    out = {
        "log": a.log,
        "pool": a.pool,
        "B": a.B,
        "seed": a.seed,
        "n_inits": len(inits),
        "n_agents": len(agents),
        "observed_hhi_mean": round(obs, 4),
        "null_hhi_mean": round(statistics.mean(sims), 4),
        "null_q025": round(lo, 4),
        "null_q975": round(hi, 4),
        "null_sd": round(statistics.pstdev(sims), 4),
        "p_value_one_sided_ge": round(p_ge, 4),
        "verdict": ("不能拒绝均匀随机（实测落在零分布内）" if lo <= obs <= hi
                    else ("显著比均匀随机更集中" if obs > hi else "显著比均匀随机更分散")),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.out_json:
        json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
