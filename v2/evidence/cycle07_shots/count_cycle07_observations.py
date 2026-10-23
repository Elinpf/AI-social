#!/usr/bin/env python3
"""CYCLE-07 案例材料的**观察量**复算脚本（不是判据，不参与任何判定）。

只做两件事，全部只读 run.jsonl：
  1) 统计正文里出现的具体物/数关键词条数（「套路化上升」的可见形态）；
  2) 统计每条线程开场舞台指示前缀的复用次数（同一开场模板被反复使用）。

用法：
    python3 v2/evidence/cycle07_shots/count_cycle07_observations.py
输出为两臂对照的纯文本表；任何数字都可以用本脚本原样复算。
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # → 仓库根
ARMS = {
    "off": ROOT / "v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl",
    "on": ROOT / "v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl",
}
KEYS = ("第三格", "半指宽", "七钱", "把手里", "上回")


def bodies(p: Path) -> list[str]:
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            if str(e.get("type", "")).startswith("MSG"):
                b = (e.get("payload") or {}).get("body")
                if b:
                    out.append(b)
    return out


def main() -> int:
    for arm, p in ARMS.items():
        b = bodies(p)
        stage = [x for x in b if x.startswith("（")]
        print(f"[{arm}] messages={len(b)} 以『（』开头={len(stage)} ({len(stage)/len(b):.2%})")
        print("  关键词条数: " + "  ".join(f"{k}={sum(k in x for x in b)}" for k in KEYS))
        pref = collections.Counter(x[:12] for x in stage)
        print("  开场舞台指示前缀 top6: " + str(pref.most_common(6)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
