#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.2 诊断（三）：**条件置换检验** —— 对端集中能不能被"时段+话题的格子结构"解释？

背景（partner_choice_permtest.py）：无条件检验下，实测 HHI 0.2877 落在零分布
[0.1938, 0.2462] 之外（p<0.0005）⇒ 对端**确实比"每人固定次数均匀抽"更集中**。
但那只能说明"有结构"，不能说明结构来自**关系偏好**。

本检验把零假设收紧为：
    H0'：**给定每人的 (slot, topic) 序列（即"什么时段做几件什么事"完全不变）**，
         每次发起的对端从 peers 内**均匀独立**抽取。
⇒ 若实测仍落在 H0' 零分布之外 ⇒ 集中**超出格子结构所能解释**，才可谈"偏好"；
   若落回带内 ⇒ 集中**完全由格子结构解释**，与"亲疏关系"无关。

用法：python3 tools/d21/partner_choice_permtest_conditional.py --log path --B 2000 --seed 42
"""
import argparse, json, random, statistics
from collections import defaultdict, Counter

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def load_inits(path):
    out = []
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
        out.append({"frm": pl["from"], "to": pl["to"],
                    "cell": (pl.get("slot"), pl.get("topic")), "ts": e.get("mono_ts") or 0})
    out.sort(key=lambda r: r["ts"])
    return out


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
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()

    rows = load_inits(a.log)
    agents = sorted({r["frm"] for r in rows} | {r["to"] for r in rows})
    by_agent = defaultdict(Counter)
    for r in rows:
        by_agent[r["frm"]][r["to"]] += 1
    obs = hhi_mean(by_agent)

    rng = random.Random(a.seed)
    sims = []
    for _ in range(a.B):
        sim = defaultdict(Counter)
        for r in rows:                                  # 保留每条的 (slot,topic)
            pool = [x for x in agents if x != r["frm"]]
            sim[r["frm"]][rng.choice(pool)] += 1
        sims.append(hhi_mean(sim))
    sims.sort()
    lo, hi = sims[int(0.025 * a.B)], sims[int(0.975 * a.B) - 1]
    out = {
        "log": a.log, "B": a.B, "seed": a.seed,
        "n_inits": len(rows), "n_agents": len(agents),
        "null": "保留每条 (slot,topic)，对端在 peers 内均匀独立抽",
        "observed_hhi_mean": round(obs, 4),
        "null_hhi_mean": round(statistics.mean(sims), 4),
        "null_q025": round(lo, 4), "null_q975": round(hi, 4),
        "null_sd": round(statistics.pstdev(sims), 4),
        "p_value_one_sided_ge": round(sum(1 for s in sims if s >= obs) / a.B, 4),
        "verdict": ("不能拒绝：集中可由格子结构解释" if lo <= obs <= hi
                    else ("集中超出格子结构（提示存在对端偏好）" if obs > hi else "比条件随机更分散")),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.out_json:
        json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
