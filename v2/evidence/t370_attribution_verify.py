#!/usr/bin/env python3
"""T370 非作者独立核：T355 收口 —— ① 事件数归因逐项复算 + 算数闭合（只读）。

仿 T349（当时核 T300 §6b）。自建口径：流式 `Counter(type)`，不 import 作者脚本。
⚠️ 前置门：等 T355 跑完 + obs 产物 + Leader 广播后跑。

用法：
  python3 v2/evidence/t370_attribution_verify.py [OLD.jsonl] [NEW.jsonl] [EXPECTED.json]
默认 OLD=/root/t271/runs/t300/run.jsonl（上一基线）NEW=/root/t271/runs/t355/run.jsonl。
EXPECTED.json（可选）：{families:{fam:[old,new]}, total:[old,new]} —— 作者清单，逐行对账。
"""
import os
import sys
import json
import hashlib
from collections import Counter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OLD = sys.argv[1] if len(sys.argv) > 1 else "/root/t271/runs/t300/run.jsonl"
NEW = sys.argv[2] if len(sys.argv) > 2 else "/root/t271/runs/t355/run.jsonl"
EXP = sys.argv[3] if len(sys.argv) > 3 else None


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def counts(p):
    c = Counter()
    n = 0
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n += 1
            c[json.loads(line).get("type")] += 1
    return c, n


def main():
    for p in (OLD, NEW):
        if not os.path.exists(p):
            print(f"PENDING: 日志不存在 {p}（T355 未跑完？）")
            return 2
    print(f"OLD={OLD}\n  sha256_16={sha16(OLD)}")
    print(f"NEW={NEW}\n  sha256_16={sha16(NEW)}")
    co, no = counts(OLD)
    cn, nn = counts(NEW)
    print(f"\n行数 OLD={no} NEW={nn} Δ={nn-no}")
    allf = sorted(set(co) | set(cn))
    deltas = {f: cn.get(f, 0) - co.get(f, 0) for f in allf}
    total = sum(deltas.values())
    print(f"[算数闭合] 全族数={len(allf)} Σ逐族Δ={total}；行数差={nn-no} -> "
          f"{'闭合 ✓（无残差）' if total == nn - no else '✗ 有残差'}")
    print("\n[非零 Δ 全清单]")
    for f in allf:
        if deltas[f]:
            print(f"  {f:28s} {co.get(f,0):>8d} -> {cn.get(f,0):>8d}  Δ={deltas[f]:>+7d}")

    if EXP and os.path.exists(EXP):
        exp = json.load(open(EXP))
        diffs = []
        for fam, (o, n) in (exp.get("families") or {}).items():
            if (co.get(fam, 0), cn.get(fam, 0)) != (o, n):
                diffs.append(f"{fam}: 声明{o}/{n} 实{co.get(fam,0)}/{cn.get(fam,0)}")
        if exp.get("total"):
            o, n = exp["total"]
            if (no, nn) != (o, n):
                diffs.append(f"TOTAL: 声明{o}/{n} 实{no}/{nn}")
        print(f"\n[对账作者清单] {'N/N 全等' if not diffs else '差异:'}")
        for d in diffs:
            print("  ✗ " + d)
        return 0 if (not diffs and total == nn - no) else 1
    return 0 if total == nn - no else 1


if __name__ == "__main__":
    sys.exit(main())
