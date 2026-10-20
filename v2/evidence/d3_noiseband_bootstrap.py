#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D3/D4 · 同分母噪声带（bootstrap）：把 t300/t355 的比率噪声带换算到任意目标分母

作者：prompt-linguist ｜ 只读（读 d3_annotated_corpus.jsonl，不跑 LLM、不改码）
方法（写死，供独立复算）：
  B1 从 t300 / t355 各按**消息**有放回重采样 m 条（m = 目标分母），各算比率
  B2 重复 B=2000 次（固定随机种子 seed=42，random.Random(42)），得到 diff = rate_t300 - rate_t355 的分布
  B3 噪声带 = diff 的 2.5% / 97.5% 分位（95% 区间，双侧）
  说明：这是**抽样噪声**带（分母大小差异导致），不是总体差异的置信区间；
        它回答的是"如果两臂真的一模一样，给定分母下比率差能有多大"。
用法：python3 v2/evidence/d3_noiseband_bootstrap.py [--denom 170]
"""
import argparse, json, random, statistics
from collections import defaultdict

CORPUS = "v2/evidence/d3_annotated_corpus.jsonl"
METRICS = {
    "L-2 narration_proxy": ("U2_narration_proxy", None),
    "L-8 agent_id_leak": ("U4_agent_id_leak", None),
    "L-11 no_second_person (DM+GROUP)": ("U5_no_second_person", {"dm", "group"}),
    "L-7 8gram_shared": ("U8b_ngram_shared", None),
    "K-1 cont_backref (in-thread)": ("K1_cont_backref", None),
    "U1 template_opening": ("U1_template_opening", None),
}


def load():
    rows = defaultdict(list)
    for line in open(CORPUS, encoding="utf-8"):
        r = json.loads(line)
        rows[r["run"]].append(r)
    return rows


def rate(sample, key, channels):
    if channels:
        sample = [r for r in sample if r["channel"] in channels]
    if not sample:
        return None
    hit = sum(1 for r in sample if r.get(key) is True)
    return hit / len(sample)


def boot(rows, key, channels, denom, B=2000, seed=42):
    rng = random.Random(seed)
    n = len(rows)
    diffs = []
    for _ in range(B):
        a = [rows[rng.randrange(n)] for _ in range(denom)]
        b = [rows[rng.randrange(n)] for _ in range(denom)]
        ra, rb = rate(a, key, channels), rate(b, key, channels)
        if ra is None or rb is None:
            continue
        diffs.append(100 * (ra - rb))
    diffs.sort()
    if not diffs:
        return None
    lo = diffs[int(0.025 * (len(diffs) - 1))]
    hi = diffs[int(0.975 * (len(diffs) - 1))]
    return {"band_pp": [round(lo, 2), round(hi, 2)], "width_pp": round(hi - lo, 2),
            "abs_p95_pp": round(max(abs(lo), abs(hi)), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--denom", type=int, nargs="+", default=[170, 230, 68])
    ap.add_argument("--out", default="v2/evidence/d3_noiseband_bootstrap.json")
    a = ap.parse_args()
    rows = load()
    # null pair 必须来自同配置两批：t300 / t355
    A, B_ = rows["t300"], rows["t355"]
    out = {"method": "bootstrap resampling of message-level rates, B=2000, seed=42; band=2.5-97.5 pct of rate_A-rate_B",
           "pairs": ["t300", "t355"], "results": {}}
    for d in a.denom:
        out["results"][f"denom_{d}"] = {}
        for name, (key, ch) in METRICS.items():
            out["results"][f"denom_{d}"][name] = boot(A, key, ch, d)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)
    for d in a.denom:
        print(f"== denom {d}")
        for name, v in out["results"][f"denom_{d}"].items():
            print(f"  {name:34s} {v['band_pp']} width={v['width_pp']}pp")


if __name__ == "__main__":
    main()
