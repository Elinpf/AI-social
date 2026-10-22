#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D4 · judge 汇总器（按 d4_judge_sampling_plan.md §3 一致性口径）

用法：
  python3 v2/evidence/d4_judge_summary.py --runs v2/evidence/d4_judge_runs.jsonl \
      --out-md v2/evidence/d4_judge_report.md --out-json v2/evidence/d4_judge_summary.json

输出：
  * 每臂 × 每维度：n、均值、中位数、分布（1–7 计数）
  * 一致性：两次重复的 exact agreement、Cohen's κ（1–7 二值化为 <4 / >=4）、Spearman ρ
  * 冲突标记：若某臂 L-2 低但 naturalness 也低，则在 md 里显式列出（由调用方给 --flag 提示）
  * 只读 runs.jsonl，不调 LLM。
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict

DIMS = ("naturalness", "persona_fit", "specificity", "is_reply")


def load(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        rows.append(r)
    return rows


def kappa(pairs):
    """二值化 κ（<4 vs >=4）。pairs: [(a,b)]"""
    if not pairs:
        return None
    po = sum(1 for a, b in pairs if (a < 4) == (b < 4)) / len(pairs)
    pa = sum(1 for a, _ in pairs if a < 4) / len(pairs)
    pb = sum(1 for _, b in pairs if b < 4) / len(pairs)
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1:
        return None
    return round((po - pe) / (1 - pe), 4)


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 4) if den else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    rows = load(a.runs)
    by_arm = defaultdict(list)
    for r in rows:
        by_arm[r.get("arm")].append(r)

    out = {"source": a.runs, "n_calls": len(rows), "arms": {}}
    md = ["# D4 · judge 汇总（客观读数的补充，不替代）", "",
          f"> 来源：`{a.runs}`（{len(rows)} 次调用）；维度：{', '.join(DIMS)}；重复 2 次一致性见 §2。", ""]
    for arm, rs in by_arm.items():
        arm_out = {"n_calls": len(rs), "dims": {}, "consistency": {}}
        ok = [r for r in rs if r.get("parsed")]
        arm_out["n_parsed"] = len(ok)
        arm_out["n_error"] = len(rs) - len(ok)
        for dim in DIMS:
            vals = [r["parsed"].get(dim) for r in ok if isinstance(r["parsed"].get(dim), (int, float))]
            if dim == "is_reply":
                vals = [v for v in vals if v > 0]
            if not vals:
                arm_out["dims"][dim] = None
                continue
            arm_out["dims"][dim] = {"n": len(vals), "mean": round(statistics.mean(vals), 2),
                                    "median": statistics.median(vals),
                                    "dist": dict(sorted(Counter(vals).items()))}
        # 一致性：按 (msg_uid) 对齐两次 repetition
        pairs = defaultdict(dict)
        for r in ok:
            pairs[r.get("msg_uid")][r.get("rep")] = r["parsed"]
        for dim in DIMS:
            xs, ys, pp = [], [], []
            for uid, d in pairs.items():
                if 0 in d and 1 in d:
                    v0, v1 = d[0].get(dim), d[1].get(dim)
                    if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                        if dim == "is_reply" and (v0 <= 0 or v1 <= 0):
                            continue
                        xs.append(v0); ys.append(v1); pp.append((v0, v1))
            if pp:
                arm_out["consistency"][dim] = {
                    "n_pairs": len(pp),
                    "exact_agreement": round(sum(1 for x, y in pp if x == y) / len(pp), 4),
                    "kappa_binarized": kappa(pp),
                    "spearman": spearman(xs, ys)}
        out["arms"][arm] = arm_out
        md += [f"## {arm}", "",
               f"- 调用 {len(rs)} 次，可解析 {len(ok)}，失败 {len(rs) - len(ok)}", "",
               "| 维度 | n | 均值 | 中位数 | 分布 |", "|---|---|---|---|---|"]
        for dim in DIMS:
            d = arm_out["dims"].get(dim)
            md.append(f"| {dim} | {d['n']} | {d['mean']} | {d['median']} | {d['dist']} |" if d else f"| {dim} | – | – | – | – |")
        md += ["", "**一致性（重复 2 次）**", "", "| 维度 | 对数 | exact | κ(<4) | ρ |", "|---|---|---|---|---|"]
        for dim in DIMS:
            c = arm_out["consistency"].get(dim)
            md.append(f"| {dim} | {c['n_pairs']} | {c['exact_agreement']} | {c['kappa_binarized']} | {c['spearman']} |" if c else f"| {dim} | – | – | – | – |")
        md += ["", "> κ<0.4 或 ρ<0.5 的维度**不得进结论**，只能作观察。", ""]

    md += ["## 冲突与边界（必须写进报告）", "",
           "- judge 只支撑「读起来更好」，**不替代**客观读数与原文并排；三者并列。",
           "- 若某臂客观指标改善但 judge 该维度下降 ⇒ **保留冲突记录**，不取平均、不择一。",
           "- 各臂分母/窗口不同（A0 686 / P1 91 / A1 视实际）⇒ **率值不可横比**，只报分布。", ""]
    open(a.out_md, "w", encoding="utf-8").write("\n".join(md))
    json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)
    print(f"[ok] {a.out_md} / {a.out_json}；arms={list(by_arm)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
