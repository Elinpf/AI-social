#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""p1_count.py —— D2.7 P1 的**连续口径**读数器（二元口径的天花板补充，只读、零 LLM）

背景：`d12c_metrics.py` 的 `P1_specificity_rate` 是**二元命中率**（每条消息命中任一
器物/量词/数字词即记 1），C 臂已达 93.53%，可用空间仅 6.47pp ⇒ 二元口径会饱和。
按 `v2/evidence/d27_C_baseline_readings.md` §2/§3 的预先声明，补一个**连续口径**：
`P1_count_mean` = 每条消息命中的**具体词个数**均值（能区分"1 个词 → 3 个词"）。

口径来源：**词表原样 import `v2/evidence/d12c_metrics.py` 的 `DETAIL`**（不自创词表），
只把 `any(re.search(...))` 改成 `sum(len(re.findall(...)))`。

用法：
  python3 v2/evidence/d27_harvest/p1_count.py \
      --run C=v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
      --run B=.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl \
      --out-json v2/evidence/d27_harvest/p1_count_c_b.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import statistics as st
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "d12c_metrics", REPO / "v2" / "evidence" / "d12c_metrics.py")
_d12c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d12c)
DETAIL = list(_d12c.DETAIL)
MSG = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def metrics(path: str) -> dict:
    n = 0
    counts = []
    zero = 0
    binary = 0
    for line in open(path, encoding="utf-8"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG:
            continue
        body = (e.get("payload") or {}).get("body") or ""
        c = sum(len(re.findall(p, body)) for p in DETAIL)
        counts.append(c)
        n += 1
        if c == 0:
            zero += 1
        if c > 0:
            binary += 1
    return {
        "n_msgs": n,
        "P1_count_sum": sum(counts),
        "P1_count_mean": round(sum(counts) / n, 4) if n else None,
        "P1_count_p50": st.median(sorted(counts)) if counts else None,
        "P1_count_zero_share_pct": round(100.0 * zero / n, 2) if n else None,
        "P1_binary_rate_pct_selfcheck": round(100.0 * binary / n, 2) if n else None,
        "detail_patterns": len(DETAIL),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="arm=path")
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    out = {}
    for spec in a.run:
        arm, _, path = spec.partition("=")
        if not arm or not path:
            raise SystemExit(f"--run 需 arm=path：{spec!r}")
        out[arm] = metrics(path)
    Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out_json).write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
