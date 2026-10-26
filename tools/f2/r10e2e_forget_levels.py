#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R10-E2E 遗忘级别分布读数器（**冻结件 · 伴生**，只读 run.jsonl）。

为什么单独一支脚本
------------------
主读数器 `tools/f2/r10e2e_axes.py` 的 sha256 已被 leader / report-writer 引用为
「同一段代码」的锚点；本件用来补 `MEMORY_FORGET` 的 **level 分布**，
**不改主件、不动其 sha256**，两者各自独立可复算。

判据口径（life-engineer 2026-10-23 建议，已采纳）
------------------------------------------------
`MEMORY_FORGET` 不能只看总数升降，要看 **level 分布是否可解释**：
`plan_forgetting` 对 `protected` 记忆只 `demote`/`keep`，新增语义记忆
（`importance=6`、`-SM-` 派生）可能走 `demote` 而非 `drop` ⇒ 级别分布改变、
总数不一定上涨。因此本件同时输出：
- 总数、按 `level` 的分布、按 `reason` 的分布；
- `protected` 占比、`retention_permille` 的分位（p10/p50/p90）；
- 按 `kind` 无关（`MEMORY_FORGET` 只带 `mem_id`），故 mem_id 前缀直方图另给
  （`-SM-` 出现次数），用于判断语义记忆是否进入遗忘链。

退出码：0 正常；2 参数/文件错误。
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import statistics
import sys


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R10-E2E 遗忘级别分布读数器（冻结伴生件）")
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--label", default=None)
    args = ap.parse_args(argv)

    if not os.path.exists(args.run):
        print(f"[forget-levels] FAIL: run 不存在: {args.run}", file=sys.stderr)
        return 2

    level = collections.Counter()
    reason = collections.Counter()
    protected = collections.Counter()
    sm_hits = 0
    total = 0
    ret: list[int] = []

    with open(args.run, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("type") != "MEMORY_FORGET":
                continue
            total += 1
            pl = r.get("payload") or {}
            level[str(pl.get("level"))] += 1
            reason[str(pl.get("reason"))] += 1
            protected[bool(pl.get("protected"))] += 1
            mid = str(pl.get("mem_id") or "")
            if "-SM-" in mid:
                sm_hits += 1
            v = pl.get("retention_permille")
            if isinstance(v, (int, float)):
                ret.append(int(v))

    def q(p: float):
        if not ret:
            return None
        s = sorted(ret)
        idx = min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))
        return s[idx]

    out = {
        "reader": {
            "script": os.path.abspath(__file__),
            "script_sha256": sha256_file(os.path.abspath(__file__)),
        },
        "source": {
            "run": os.path.abspath(args.run),
            "run_sha256": sha256_file(args.run),
            "label": args.label,
        },
        "MEMORY_FORGET": {
            "total": total,
            "by_level": dict(sorted(level.items())),
            "by_reason": dict(sorted(reason.items())),
            "protected_true": protected[True],
            "protected_false": protected[False],
            "sm_mem_id_hits": sm_hits,
            "retention_permille": {
                "n": len(ret),
                "min": min(ret) if ret else None,
                "p10": q(0.10),
                "p50": q(0.50),
                "p90": q(0.90),
                "max": max(ret) if ret else None,
                "mean": round(statistics.fmean(ret), 2) if ret else None,
            },
        },
    }

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"[forget-levels] written: {args.out}")
        print(json.dumps(out["MEMORY_FORGET"], ensure_ascii=False))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
