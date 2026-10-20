#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D6 头条三指标对照（裁决用一行式）：多轮线程占比 / 回复指针完整率 / 对端称呼率。

每条都给：值、分母、band_source（B2(m=..) / rule-of-three(3/n) / 无可用带 / single-arm）。
**结构类两指标（多轮、指针）在 v0-anchor→A0 这一对不套 B2**（切分口径不同），因此 band_source 会标 `口径不可比`。

用法：
    python3 tools/d5/headline.py --arms "v0-anchor:v2/evidence/d5_metrics_v0anchor.json" "A0:v2/evidence/d5_metrics_a0.json" \
        [--band v2/evidence/d5_noiseband_bootstrap_t300_t355.json]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))

INDICATORS = [
    ("多轮线程占比 (turns_A>=3)", "S-2_thread_scale.multi_turn_thread_ratio", "threads", "thread:multi_turn_thread"),
    ("回复指针完整率", "S-4_reply_pointer_coverage.rate", "ptr_nonfirst", None),
    ("对端称呼率 L-12b（判定用）", "L_wording.L-12b_peer_address_rate", "dm_group", "item:L-12"),
    ("对端提及率 L-12a（描述）", "L_wording.L-12_peer_mention_rate", "dm_group", "item:L-12"),
]


def get(d: Any, path: str) -> Any:
    cur = d
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def denom(m: Dict[str, Any], src: str) -> Optional[int]:
    if src == "threads":
        return get(m, "L_wording.denominators.threads") or get(m, "meta.n_threads")
    if src == "dm_group":
        return get(m, "L_wording.denominators.dm_group")
    if src == "ptr_nonfirst":
        return get(m, "S-4_reply_pointer_coverage.denominator_nonfirst_msgs")
    return None


def band_of(band_json: Optional[Dict[str, Any]], key: Optional[str], dn: Optional[int]) -> str:
    if not band_json or key is None or dn is None:
        return "无可用带"
    table = (band_json.get("B2_band_by_denom") or {}).get(key) or {}
    if not table:
        return "无可用带"
    dens = sorted(int(k) for k in table)
    if dn < dens[0]:
        return "无可用带"
    mm = next((d for d in dens if d >= dn), dens[-1])
    hw = table.get(str(mm), {}).get("halfwidth_pp")
    if hw is None:
        return "无可用带"
    if hw == 0:
        return f"rule-of-three(3/{dn})"
    return f"B2(m={mm}) ±{hw}pp"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D6 头条三指标对照")
    ap.add_argument("--arms", nargs="+", required=True, help="name:path")
    ap.add_argument("--band", default=None)
    args = ap.parse_args(argv)
    band_json = json.load(open(args.band, encoding="utf-8")) if args.band else None
    arms = []
    for spec in args.arms:
        n, p = spec.split(":", 1)
        arms.append((n, json.load(open(p, encoding="utf-8"))))

    lines = []
    for label, path, dsrc, bkey in INDICATORS:
        parts = []
        for name, m in arms:
            v = get(m, path)
            dn = denom(m, dsrc)
            vs = "N/A" if v in (None, "N/A") else (f"{v:.1%}" if isinstance(v, (int, float)) else str(v))
            parts.append(f"{name}={vs}(n={dn})")
        # band：v0→A0 结构口径不可比；只有同口径两臂（如 A0→A1）才给 B2
        same_schema = len({m.get("meta", {}).get("thread_schema") for _, m in arms}) == 1
        b = band_of(band_json, bkey, denom(arms[-1][1], dsrc)) if same_schema else "口径不可比(v0-anchor 与 A0 thread_schema 不同)"
        lines.append(f"- {label}: " + " | ".join(parts) + f" | band_source={b}")

    out = "\n".join(lines)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
