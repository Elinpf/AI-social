#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A5 judge：按消息为单位（2 次重复取均值）计算两臂 Δ 与 bootstrap 95% CI（leader 协议 v2）

口径（写死）：
  * 单位 = 消息（(arm,msg_uid) → 两次重复的均值）
  * Δ = CTRL − A5（正 = CTRL 更高）
  * CI = 两臂各自有放回重采样（B=5000, seed 42），取 Δ 的 2.5/97.5 分位
  * 另给 Mann–Whitney U 双侧 p（小样本备用判据，仅参考）
  * is_reply 只用 >0（即确为回复）的消息
用法： python3 v2/evidence/a5_judge_delta_ci.py --runs v2/evidence/a5_judge_runs.jsonl --out-json ... --out-md ...
"""
import argparse, json, random, statistics
from collections import defaultdict

DIMS = ("naturalness", "persona_fit", "specificity", "is_reply")


def mwu_p(a, b):
    """双侧 Mann–Whitney U 的正态近似 p（无并列修正；仅参考）"""
    n1, n2 = len(a), len(b)
    if n1 < 3 or n2 < 3:
        return None
    allv = sorted(a + b)
    rank = {}
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            rank[allv[k]] = r
        i = j + 1
    R1 = sum(rank[x] for x in a)
    U1 = R1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    sd = (n1 * n2 * (n1 + n2 + 1) / 12) ** 0.5
    if sd == 0:
        return None
    z = (U1 - mu) / sd
    # two-sided normal approx
    from math import erf, sqrt
    p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    return round(p, 4)


def boot_ci(a, b, B=5000, seed=42):
    rng = random.Random(seed)
    d = []
    for _ in range(B):
        ra = [a[rng.randrange(len(a))] for _ in a]
        rb = [b[rng.randrange(len(b))] for _ in b]
        d.append(statistics.mean(ra) - statistics.mean(rb))
    d.sort()
    return [round(d[int(0.025 * (B - 1))], 3), round(d[int(0.975 * (B - 1))], 3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.runs, encoding="utf-8")]
    by = defaultdict(dict)
    for r in rows:
        if r.get("parsed"):
            by[(r["arm"], r.get("msg_uid"))][r["rep"]] = r["parsed"]
    # 每消息取均值
    per_msg = defaultdict(lambda: defaultdict(list))
    for (arm, uid), reps in by.items():
        for dim in DIMS:
            vals = [v.get(dim) for v in reps.values() if isinstance(v.get(dim), (int, float))]
            if dim == "is_reply":
                vals = [x for x in vals if x > 0]
            if vals:
                per_msg[arm][dim].append(statistics.mean(vals))
    out = {"source": a.runs, "unit": "message(mean of 2 reps)", "delta": "CTRL - A5", "dims": {}}
    md = ["# A5 judge · Δ 与 bootstrap 95% CI（协议 v2，单位=消息）", "",
          "> Δ = `CTRL − A5`（正=CTRL 更高）；单位=每条消息先对 2 次重复取均值；CI=两臂重采样 B=5000/seed 42。", "",
          "| 维度 | CTRL 均值(n) | A5 均值(n) | Δ | **95% CI** | 是否含 0 | MWU p（参考） |", "|---|---|---|---|---|---|---|"]
    for dim in DIMS:
        c = per_msg["CTRL"][dim]
        t = per_msg["A5"][dim]
        if len(c) < 2 or len(t) < 2:
            md.append(f"| {dim} | n={len(c)} | n={len(t)} | – | – | – | – |")
            continue
        d = statistics.mean(c) - statistics.mean(t)
        ci = boot_ci(c, t)
        contains0 = ci[0] <= 0 <= ci[1]
        p = mwu_p(c, t)
        out["dims"][dim] = {"n_ctrl": len(c), "n_a5": len(t),
                            "mean_ctrl": round(statistics.mean(c), 3),
                            "mean_a5": round(statistics.mean(t), 3),
                            "delta": round(d, 3), "ci95": ci, "ci_contains_0": contains0,
                            "mwu_p": p}
        md.append(f"| {dim} | {round(statistics.mean(c),2)}（n={len(c)}） | {round(statistics.mean(t),2)}（n={len(t)}） | **{round(d,2)}** | **[{ci[0]}, {ci[1]}]** | {'**是 ⇒ 无结论**' if contains0 else '否'} | {p} |")
    json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)
    open(a.out_md, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
