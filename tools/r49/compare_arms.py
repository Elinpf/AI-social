#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R49 两臂对照读数器（只读、零 LLM、零跑批）。

把三把尺子在同一对 run.jsonl 上跑一遍，并给出**判据所需**的统计量：
  * 每臂的 `num/den/rate/wilson95`（直接复用 `tools/metrics/lex_template_rate.py`
    与 `tools/metrics/r49_detail_opener.py` 的 `compute()`，**不另写一套口径**）；
  * 两臂的 **Fisher 精确检验双侧 p**（纯标准库实现，不依赖 scipy/statsmodels）；
  * 与预登记（`reports/R49-prereg-diversity-20261101.md` §3）阈值逐条比对，给出
    `M1 / E1 / E2 / E3` 的**机械判定**（不含任何人工解释）。

判据阈值**照抄预登记文件**，本脚本**不提供改阈值的开关**——要改判据只能改预登记并留痕。

用法:
  python3 tools/r49/compare_arms.py --off <off>/run.jsonl --on <on>/run.jsonl \
      --out-json v2/evidence/r49-diversity-compare.json
退出码 0（读数与判定都产出即成功）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


LEX = _load("lex_template_rate", "tools/metrics/lex_template_rate.py")
DET = _load("r49_detail_opener", "tools/metrics/r49_detail_opener.py")

# ---- 预登记阈值（逐字抄自 reports/R49-prereg-diversity-20261101.md §3） ----
M1_MDE_PP = 11.7        # detail_opener6：ON − OFF ≥ +11.7pp
E1_MDE_PP = 5.9         # opener_top10_share：OFF − ON ≥ 5.9pp
N_FLOOR = 160           # 每臂消息数下限


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2×2 表 [[a,b],[c,d]] 的双侧 Fisher 精确检验 p（超几何求和，纯标准库）。"""
    n = a + b + c + d
    r1, r2, c1, c2 = a + b, c + d, a + c, b + d

    def lcomb(n_, k_):
        return math.lgamma(n_ + 1) - math.lgamma(k_ + 1) - math.lgamma(n_ - k_ + 1)

    def prob(x: int) -> float:
        return math.exp(lcomb(r1, x) + lcomb(r2, c1 - x) - lcomb(n, c1))

    lo = max(0, c1 - r2)
    hi = min(r1, c1)
    obs = prob(a)
    total = 0.0
    for x in range(lo, hi + 1):
        p = prob(x)
        if p <= obs * (1 + 1e-12):
            total += p
    return min(1.0, total)


def _arm(path: str) -> dict:
    msgs = LEX.iter_bodies(path)
    lex = LEX.compute(msgs)
    bodies = DET.collect_bodies(path)
    det = DET.measure(bodies)
    return {"lex": lex, "det": det, "log": path}


def _blk(arm: dict, name: str) -> dict:
    if name in ("opener_top10_share", "distinct_body_ratio", "backref_hit"):
        return arm["lex"][name]
    return arm["det"][name]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--out-json", default="")
    a = ap.parse_args(argv)

    off, on = _arm(a.off), _arm(a.on)
    rows = {}
    for name in ("detail_opener6", "detail_line", "detail_body", "paren_lead",
                 "opener_top10_share", "distinct_body_ratio", "backref_hit"):
        o, n = _blk(off, name), _blk(on, name)
        p = None
        if o["den"] and n["den"]:
            p = fisher_exact_two_sided(o["num"], o["den"] - o["num"], n["num"], n["den"] - n["num"])
        rows[name] = {
            "off": o, "on": n,
            "delta_pp": round(100 * (n["rate"] - o["rate"]), 4) if o["rate"] is not None and n["rate"] is not None else None,
            "fisher_two_sided_p": None if p is None else round(p, 6),
            "wilson_overlap": None if not (o.get("wilson95") and n.get("wilson95")) else
                              (o["wilson95"]["lo"] <= n["wilson95"]["hi"] and n["wilson95"]["lo"] <= o["wilson95"]["hi"]),
        }

    n_off, n_on = off["det"]["n_msgs"], on["det"]["n_msgs"]
    u1 = not (n_off >= N_FLOOR and n_on >= N_FLOOR)

    m1 = rows["detail_opener6"]
    m1_pass = (not u1) and m1["delta_pp"] is not None and m1["delta_pp"] >= M1_MDE_PP \
              and (m1["fisher_two_sided_p"] is not None and m1["fisher_two_sided_p"] < 0.05)
    m1_verdict = "机制生效(采纳)" if m1_pass else (
        "机制未生效(未达 MDE 或未显著)" if not u1 else "不可判(分母不足)")

    e1 = rows["opener_top10_share"]
    e1_drop = None if e1["delta_pp"] is None else round(-e1["delta_pp"], 4)  # 正数 = 下降 pp
    if u1:
        e1_verdict = "不可判(分母不足)"
    elif e1_drop is not None and e1_drop >= E1_MDE_PP and (e1["fisher_two_sided_p"] or 1) < 0.05:
        e1_verdict = "效果成立"
    else:
        e1_verdict = "不可判(效应低于本采样结构 MDE %.1fpp 或未显著)" % E1_MDE_PP

    res = {
        "prereg": "reports/R49-prereg-diversity-20261101.md",
        "thresholds": {"M1_MDE_PP": M1_MDE_PP, "E1_MDE_PP": E1_MDE_PP, "N_FLOOR": N_FLOOR},
        "n_msgs": {"off": n_off, "on": n_on},
        "rows": rows,
        "verdicts": {
            "U1_denominator_ok": not u1,
            "M1_mechanism": m1_verdict,
            "E1_opener_share": e1_verdict,
            "E2_distinct_body_ratio": "不可判(预登记：OFF 已达 1.000 天花板，无改善空间)",
            "E3_backref_hit": "只描述，不进判据（预登记 §3.3）",
        },
    }
    text = json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out_json:
        Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out_json).write_text(text + "\n", encoding="utf-8")
    print("arm            metric                       off            on             Δpp     fisher_p")
    for name, r in rows.items():
        o, n = r["off"], r["on"]
        print("%-14s %-26s %4d/%-4d %6.2f%% %4d/%-4d %6.2f%% %+7.2f %s" % (
            "", name, o["num"], o["den"], 100 * (o["rate"] or 0), n["num"], n["den"],
            100 * (n["rate"] or 0), r["delta_pp"] or 0.0,
            "%.4g" % r["fisher_two_sided_p"] if r["fisher_two_sided_p"] is not None else "-"))
    print(json.dumps(res["verdicts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
