#!/usr/bin/env python3
"""T349 非作者独立核：T300 §6b 事件数 −8,421 逐族归因（只读）。

自建口径：直接流式扫描两份 jsonl，`Counter(rec["type"])`，逐族对账 §6 表 + 独立复现算数闭合。
不 import 作者脚本、不改任何产物。
运行：cd repo && python3 v2/evidence/t349_t300_attribution_verify.py [OLD] [NEW]
"""
import json
import sys
import os
import hashlib
from collections import Counter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OLD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "v2/evidence/run_t236_canon_n20_llm.jsonl")
NEW = sys.argv[2] if len(sys.argv) > 2 else "/root/t271/runs/t300/run.jsonl"

# §6 表（作者声明）
S6 = {
    "MEMORY_FORGET": (143543, 134367),
    "MEMORY_WRITE": (58531, 58547),
    "PERSONA_DRIFT": (0, 240),
    "PERSONA_DRIFT_CANDIDATE": (0, 527),
    "PRODUCE": (317, 167),
    "EXCHANGE_SETTLED": (20, 25),
    "LLM_CALL": (4794, 4797),
    "LLM_JUDGMENT": (1010, 1010),
    "RELATION_CHANGE": (16725, 16725),
}
S6_TOTAL = (301384, 292963)
# §6b A 组"可隔离"
S6B_A = {
    "MEMORY_FORGET": -9176, "MEMORY_WRITE": 16, "PERSONA_DRIFT": 240,
    "PERSONA_DRIFT_CANDIDATE": 527, "PRODUCE": -150, "SERVICE_DELIVERED": 149,
}


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
    print("=== T349 独立核 · T300 §6b 归因 ===")
    print(f"OLD = {OLD}\n  sha256_16={sha16(OLD)}")
    print(f"NEW = {NEW}\n  sha256_16={sha16(NEW)}")
    co, no = counts(OLD)
    cn, nn = counts(NEW)
    print(f"\n行数 OLD={no} NEW={nn}（§6 TOTAL 声明 {S6_TOTAL}） -> "
          f"{'一致' if (no,nn)==S6_TOTAL else '不一致'}")

    diffs = []
    print("\n[§6 表逐行对账]")
    for fam, (o, n) in S6.items():
        go, gn = co.get(fam, 0), cn.get(fam, 0)
        ok = (go, gn) == (o, n)
        if not ok:
            diffs.append(f"{fam}: 页={o}/{n} 实={go}/{gn}")
        print(f"  {fam:24s} old={go:>7d}(声明{o:>7d}) new={gn:>7d}(声明{n:>7d}) Δ={gn-go:>+7d} {'OK' if ok else '✗'}")

    # ---- 全族 delta + 算数闭合 ----
    allfam = sorted(set(co) | set(cn))
    deltas = {f: cn.get(f, 0) - co.get(f, 0) for f in allfam}
    total_delta = sum(deltas.values())
    print(f"\n[算数闭合] 全族数={len(allfam)}  Σ逐族Δ = {total_delta} （§6 TOTAL Δ = {S6_TOTAL[1]-S6_TOTAL[0]}）"
          f" -> {'闭合 ✓' if total_delta == S6_TOTAL[1]-S6_TOTAL[0] else '✗ 有残差'}")
    # 逐项相加 = 新增-减少，与总行数差核对
    print(f"  行数差 NEW-OLD = {nn-no} -> {'=ΣΔ ✓' if nn-no == total_delta else '✗'}")

    print("\n[非零 Δ 全清单]")
    for f in allfam:
        if deltas[f] != 0:
            print(f"  {f:26s} {deltas[f]:>+7d}")

    # ---- §6b A 组核对 ----
    print("\n[§6b A 组（作者称可隔离）逐项核对]")
    a_sum = 0
    for fam, dv in S6B_A.items():
        real = deltas.get(fam, 0)
        a_sum += real
        print(f"  {fam:24s} 声明Δ={dv:>+6d} 实Δ={real:>+6d} {'OK' if real==dv else '✗'}")
    print(f"  A 组实Σ = {a_sum}")
    b_sum = total_delta - a_sum
    print(f"  ⇒ 其余（应为 §6b B 组机制归因 + 未列族）Σ = {b_sum}")

    print("\n==== 差异清单 ====")
    if diffs:
        for d in diffs:
            print("  ✗ " + d)
    else:
        print("  0 处差异（§6 表 N/N 全等）")
    return 0 if (not diffs and total_delta == S6_TOTAL[1]-S6_TOTAL[0]) else 1


if __name__ == "__main__":
    sys.exit(main())
