#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-G · L-7 双口径 bootstrap CI（消息级重采样，B=2000，seed=42）。

定位：**不重新定义 L-7**。dup 判定完全复用 `v2/evidence/recompute_l7_indep.py`
的 `raw8` / `norm8` / `dup_index`（即「任一 8-gram shingle 与他人重合即算 dup」，
dup 率分母 = MSG 数），本脚本只做有放回重采样给出 Δ(T5−T4) 的 2.5%/97.5% 分位。

用法：
    python3 v2/evidence/d12g_l7_ci.py \
        --base <T4>/run.jsonl --test <T5>/run.jsonl \
        --out-json v2/evidence/d12g_l7_ci_t4_t5.json

判读纪律：CI 含 0 ⇒ 无结论；比率型写清分子/分母；本脚本不产出判定词。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RECOMP = os.path.join(HERE, "recompute_l7_indep.py")


def load_recomp():
    spec = importlib.util.spec_from_file_location("recompute_l7_indep", RECOMP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def load_flags(path: str, rc):
    MSG_TYPES = rc.MSG_TYPES
    bodies = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("type") not in MSG_TYPES:
            continue
        bodies.append((r.get("payload") or {}).get("body") or "")
    d_raw = rc.dup_index([rc.raw8(b) for b in bodies])
    d_norm = rc.dup_index([rc.norm8(b) for b in bodies])
    n = len(bodies)
    return n, [1 if i in d_raw else 0 for i in range(n)], [1 if i in d_norm else 0 for i in range(n)]


def boot_delta(a, b, B, seed):
    rnd = random.Random(seed)
    na, nb = len(a), len(b)
    ds = []
    for _ in range(B):
        sa = [a[rnd.randrange(na)] for _ in range(na)]
        sb = [b[rnd.randrange(nb)] for _ in range(nb)]
        ds.append(100.0 * (sum(sb) / nb - sum(sa) / na))
    ds.sort()
    lo = ds[int(0.025 * B)]
    hi = ds[int(0.975 * B) - 1]
    return {"ci95_lo": round(lo, 4), "ci95_hi": round(hi, 4),
            "contains_zero": bool(lo <= 0 <= hi)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()

    rc = load_recomp()
    out = {"recompute_impl": {"path": RECOMP, "sha256": sha256_file(RECOMP)},
           "policy": {"B": a.B, "seed": a.seed,
                      "note": "消息级有放回重采样；dup 口径复用 recompute_l7_indep（任一 shingle 重合即 dup，分母=MSG 数）",
                      "rule": "CI 含 0 ⇒ 无结论"},
           "logs": {"base": {"path": a.base, "sha256": sha256_file(a.base)},
                    "test": {"path": a.test, "sha256": sha256_file(a.test)}},
           "rates": {}}
    nb, base_raw, base_norm = load_flags(a.base, rc)
    nt, test_raw, test_norm = load_flags(a.test, rc)
    for name, va, vb in (("L7_raw8", base_raw, test_raw), ("L7_norm8", base_norm, test_norm)):
        kb, kt = sum(va), sum(vb)
        out["rates"][name] = {
            "base": {"k": kb, "n": nb, "pct": round(100 * kb / nb, 4)},
            "test": {"k": kt, "n": nt, "pct": round(100 * kt / nt, 4)},
            "delta_pp": round(100 * (kt / nt - kb / nb), 4),
            "diff": boot_delta(va, vb, a.B, a.seed),
        }
    out["n_msgs"] = {"base": nb, "test": nt}
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(out["rates"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
