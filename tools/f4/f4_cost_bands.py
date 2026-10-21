#!/usr/bin/env python3
"""F-4 成本归因：**按回合段对齐**的调用密度表（R13；零跑批，只读日志）。

为什么不用总调用数直接比
------------------------
60 回合批的单回合调用密度**不是稳态**：前期有 judge/importance 为主的启动固定成本，
后期单人回合密度自然下降。直接拿「前 10 回合 × 6」外推会把启动段当稳态，得出错误的预算结论
（R13 实际发生过一次，已在报告更正）。正确做法是与基线臂**同回合区间对齐**，再看差异落在哪一段。

输出
----
对每个臂、每个回合段（默认 1–10 / 11–30 / 31–60，可按 --bands 覆盖）：
  calls / 回合数 / 每回合密度 / purpose 分布 / degraded 条数 / dequp_retry 条数

用法（仓库根，干净 shell 可复制；只读，不写除 --out-json 外的任何文件）：
  python3 tools/f4/f4_cost_bands.py \
    --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
    --run on=v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
    --out-json v2/evidence/f4_cost_bands.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_BANDS = ((0, 9), (10, 10), (11, 30), (31, 60))  # 段B = round 10 单列（日结/反思批量段）


def analyze(label: str, path: str, bands) -> dict:
    per_round = defaultdict(Counter)   # round -> purpose counter
    degraded = Counter()
    retry = Counter()
    mr = -1
    for ln in open(path, encoding="utf-8"):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        rd = r.get("round")
        if isinstance(rd, int) and rd > mr:
            mr = rd
        if r.get("type") != "LLM_CALL":
            continue
        pl = r.get("payload") or {}
        rk = rd if isinstance(rd, int) else -1
        per_round[rk][pl.get("purpose") or "?"] += 1
        if pl.get("degraded") is True:
            degraded[rk] += 1
        if pl.get("dequp_retry"):
            retry[rk] += 1

    def agg(lo: int, hi: int) -> dict:
        purposes = Counter()
        rounds = 0
        for rd in range(lo, hi + 1):
            if rd in per_round:
                rounds += 1
                purposes.update(per_round[rd])
        calls = sum(purposes.values())
        return {"rounds": rounds, "calls": calls,
                "calls_per_round": round(calls / rounds, 3) if rounds else None,
                "purposes": dict(sorted(purposes.items())),
                "degraded": sum(degraded.get(rd, 0) for rd in range(lo, hi + 1)),
                "dequp_retry": sum(retry.get(rd, 0) for rd in range(lo, hi + 1))}

    return {"label": label, "log": os.path.relpath(path, REPO),
            "log_sha8": None,  # 由 main 填，避免脚本内重复读大文件
            "max_round": mr,
            "bands": {f"{lo}-{hi}": agg(lo, hi) for lo, hi in bands},
            "total_calls": sum(sum(c.values()) for c in per_round.values())}


def sha8(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, metavar="LABEL=PATH")
    ap.add_argument("--bands", default="0-9,10-10,11-30,31-60",
                    help="段划分；round 10 结构性批量段默认单列（0-9/10-10/11-30/31-60）")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args(argv)

    bands = []
    for spec in args.bands.split(","):
        lo, _, hi = spec.partition("-")
        bands.append((int(lo), int(hi)))

    arms = []
    for spec in args.run:
        label, _, rel = spec.partition("=")
        path = rel if os.path.isabs(rel) else os.path.join(REPO, rel)
        a = analyze(label, path, bands)
        a["log_sha8"] = sha8(path)
        arms.append(a)

    # 与基线（第一个 --run）同段差值：calls / degraded / retry
    base = arms[0] if arms else None
    for a in arms:
        for band, s in a["bands"].items():
            bs = (base["bands"].get(band) or {}) if base else {}
            s["delta_vs_baseline"] = {
                "baseline_label": base["label"] if base else None,
                "calls": (s["calls"] - bs.get("calls", 0)) if bs else None,
                "degraded": (s["degraded"] - bs.get("degraded", 0)) if bs else None,
                "dequp_retry": (s["dequp_retry"] - bs.get("dequp_retry", 0)) if bs else None,
                "baseline_rounds": bs.get("rounds"),
                "comparable": bool(bs) and bs.get("rounds") == s["rounds"],
            }

    print("\n| arm | sha8 | 段 | 回合数 | calls | 每回合 | Δcalls vs 基线 | judge | dialogue | importance | plan | reflect | degraded | retry | 可比 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a in arms:
        for band, s in a["bands"].items():
            p = s["purposes"]
            d = s["delta_vs_baseline"]
            print("| %s | %s | %s | %d | %d | %s | %s | %d | %d | %d | %d | %d | %d | %d | %s |" % (
                a["label"], a["log_sha8"], band, s["rounds"], s["calls"], s["calls_per_round"],
                d["calls"], p.get("judge", 0), p.get("dialogue", 0), p.get("importance", 0),
                p.get("plan", 0), p.get("reflect", 0), s["degraded"], s["dequp_retry"],
                "是" if d["comparable"] else "否(段未完/回合数不等)"))

    if args.out_json:
        out = args.out_json if os.path.isabs(args.out_json) else os.path.join(REPO, args.out_json)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        open(out, "w", encoding="utf-8").write(
            json.dumps({"schema": "f4-cost-bands/1", "bands": args.bands, "arms": arms},
                       ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        print("written:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
