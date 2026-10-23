#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-I / D12-H 选优机制统计（纯只读）：**`argmin_unique` 与 `not_all_equal` 并列输出**。

为什么要并列（今晚的"同名不同义"教训）：
- **`argmin_unique`** = "**最小值的索引唯一**"（`scores=[1,1,2]` ⇒ **False**：最小值 1 出现在 0 和 1 两处）
  —— 这才是预登记里"argmin 唯一率"的字面含义，是**目标能否唯一择优**的判据；
- **`not_all_equal`** = "**分数不全同**"（`scores=[1,1,2]` ⇒ **True**）
  —— 只说明"有区分度"，**不能**当 `argmin_unique` 用。两者混用会把 94.1% 说成 98.6%。

用法：
    python3 tools/d12i/selector_stats.py --log <run.jsonl> [--rounds N] [--key d12i|d12h] [--out-json x.json]
退出码：0 正常；2 日志无该类消息。
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--rounds", type=int, default=None, help="只看前 N 轮")
    ap.add_argument("--key", default="d12i", choices=["d12i", "d12h"])
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args(argv)

    ctxs = []
    with open(a.log, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if not str(r.get("type", "")).startswith("MSG"):
                continue
            if a.rounds is not None and (not isinstance(r.get("round"), int) or r["round"] >= a.rounds):
                continue
            ctx = (r.get("payload") or {}).get("ctx")
            if isinstance(ctx, dict) and a.key in ctx:
                ctxs.append(ctx[a.key])
    if not ctxs:
        print(f"[CANNOT-VERIFY] 没有 ctx.{a.key} 消息（--rounds={a.rounds}）", file=sys.stderr)
        return 2

    n = len(ctxs)

    def _scores(c):
        """D12-I: `scores`；D12-H: 取 on 组。"""
        if "scores" in c:
            return c["scores"]
        return (c.get("on") or {}).get("recent16_scores") or []

    argmin_unique = 0
    not_all_equal = 0
    all_zero = 0
    has_na = 0
    picked = collections.Counter()
    vals = []
    for c in ctxs:
        ss = _scores(c)
        valid = [s for s in ss if s is not None]
        if len(valid) != len(ss):
            has_na += 1
        if not valid:
            continue
        m = min(valid)
        if sum(1 for s in ss if s == m) == 1:
            argmin_unique += 1
        if len(set(ss)) > 1:
            not_all_equal += 1
        if all(s == 0.0 for s in valid):
            all_zero += 1
        vals.extend(valid)
        if "picked" in c:
            picked[c["picked"]] += 1

    same_hash = None
    hkey = "cand_shingle_hashes_4g" if a.key == "d12i" else "cand_shingle_hashes"
    if all(hkey in c or (a.key == "d12h") for c in ctxs):
        try:
            same_hash = sum(
                1 for c in ctxs
                if len({tuple(h) for h in (c.get(hkey) or (c.get("on") or {}).get(hkey) or [])}) == 1)
        except Exception:
            same_hash = None

    out = {
        "log": a.log, "key": a.key, "rounds_filter": a.rounds, "n": n,
        "definitions": {
            "argmin_unique": "最小值的索引唯一（scores=[1,1,2] ⇒ False）—— 判据用这个",
            "not_all_equal": "分数不全同（scores=[1,1,2] ⇒ True）—— 只说明有区分度，不得当 argmin_unique 用",
        },
        "argmin_unique": argmin_unique,
        "argmin_unique_rate": argmin_unique / n,
        "not_all_equal": not_all_equal,
        "not_all_equal_rate": not_all_equal / n,
        "all_zero": all_zero,
        "all_zero_rate": all_zero / n,
        "contains_na": has_na,
        "three_candidates_shingle_identical": same_hash,
        "three_candidates_shingle_identical_rate": (same_hash / n) if same_hash is not None else None,
        "picked_distribution": dict(sorted(picked.items())),
        "scores": {"mean": statistics.mean(vals) if vals else None,
                   "median": statistics.median(vals) if vals else None,
                   "max": max(vals) if vals else None},
    }
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    print(txt)
    if a.out_json:
        Path(a.out_json).write_text(txt + "\n", encoding="utf-8")
    print(f"[selector_stats] key={a.key} n={n}", file=sys.stderr)
    print(f"  argmin_unique   = {argmin_unique}/{n} = {argmin_unique / n * 100:.1f}%   ← 判据（最小值索引唯一）",
          file=sys.stderr)
    print(f"  not_all_equal   = {not_all_equal}/{n} = {not_all_equal / n * 100:.1f}%   ← 仅「有区分度」，不是同一件事",
          file=sys.stderr)
    print(f"  all_zero        = {all_zero}/{n} = {all_zero / n * 100:.1f}%   picked={out['picked_distribution']}",
          file=sys.stderr)
    if same_hash is not None:
        print(f"  三候选 shingle 层全同 = {same_hash}/{n} = {same_hash / n * 100:.2f}%", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
