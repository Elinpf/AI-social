#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-G · 「配对设计」可行性实测（只读两臂日志，不联网、不调 LLM）。

回答三个问题，供下一臂预登记定规模：
  Q1 两臂在同一 slot（thread_id × turn_index × from）上**逐字相同**的消息占比有多少？
     （= 配对能共享多少"同一文本"信息；若很低，所谓配对只是"位置对齐"）
  Q2 该占比是否随轮次衰减（轨迹分叉后配对失效）？
  Q3 配对 bootstrap（按 slot 对齐、有放回重采样 slot）的 CI 比独立 bootstrap 窄多少？
     （= 配对真实带来的方差压缩；若几乎为零，配对不能替代放大 n）

口径：dup 判定复用 `v2/evidence/recompute_l7_indep.py` 的 raw8 / norm8 / dup_index
（任一 8-gram shingle 与他人重合即算 dup，分母 = MSG 数）；同一 arm 内先算全局 dup 标记，
再按 slot 对齐两臂做差值。

用法：
    python3 v2/evidence/d12g_pairing_check.py \
        --arm-a <T4>/run.jsonl --arm-b <T5>/run.jsonl \
        --out-json v2/evidence/d12g_pairing_check.json
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


def load(path: str, rc):
    rows = []
    for line in open(path, encoding="utf-8"):
        if '"MSG_' not in line:
            continue
        d = json.loads(line)
        if d.get("type") not in rc.MSG_TYPES:
            continue
        p = d.get("payload") or {}
        rows.append({"slot": (p.get("thread_id"), p.get("turn_index"), p.get("from")),
                     "round": d.get("round"), "body": p.get("body") or ""})
    bodies = [r["body"] for r in rows]
    dn = rc.dup_index([rc.norm8(b) for b in bodies])
    dr = rc.dup_index([rc.raw8(b) for b in bodies])
    for i, r in enumerate(rows):
        r["dup_norm8"] = 1 if i in dn else 0
        r["dup_raw8"] = 1 if i in dr else 0
    return rows


def boot(ds, B, seed):
    rnd = random.Random(seed)
    n = len(ds)
    out = []
    for _ in range(B):
        out.append(100.0 * sum(ds[rnd.randrange(n)] for _ in range(n)) / n)
    out.sort()
    return [round(out[int(0.025 * B)], 4), round(out[int(0.975 * B) - 1], 4)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-a", required=True)
    ap.add_argument("--arm-b", required=True)
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()

    rc = load_recomp()
    A = load(a.arm_a, rc)
    B = load(a.arm_b, rc)
    ma = {}
    for r in A:
        ma.setdefault(r["slot"], []).append(r)
    mb = {}
    for r in B:
        mb.setdefault(r["slot"], []).append(r)
    shared = [s for s in ma if s in mb]

    exact = sum(1 for s in shared if [r["body"] for r in ma[s]] == [r["body"] for r in mb[s]])
    by_round = {}
    for s in shared:
        rd = ma[s][0]["round"] or 0
        b = (rd // 10) * 10
        e = by_round.setdefault(b, [0, 0])
        e[1] += 1
        if [r["body"] for r in ma[s]] == [r["body"] for r in mb[s]]:
            e[0] += 1

    res = {
        "impl": {"path": RECOMP, "sha256": sha256_file(RECOMP),
                 "driver_sha256": sha256_file(os.path.abspath(__file__))},
        "logs": {"arm_a": {"path": a.arm_a, "sha256": sha256_file(a.arm_a)},
                 "arm_b": {"path": a.arm_b, "sha256": sha256_file(a.arm_b)}},
        "policy": {"B": a.B, "seed": a.seed, "unit": "slot = (thread_id, turn_index, from)",
                   "note": "配对 bootstrap 按 slot 对齐有放回重采样；dup 标记先在各臂内全局计算"},
        "Q1_slot_exact_same": {"shared_slots": len(shared), "exact_same": exact,
                               "pct": round(100 * exact / len(shared), 3) if shared else None},
        "Q2_same_rate_by_round_bucket": {str(k): {"same": v[0], "slots": v[1],
                                                  "pct": round(100 * v[0] / v[1], 2)} for k, v in sorted(by_round.items())},
        "Q3_ci": {},
    }
    for key in ("dup_norm8", "dup_raw8"):
        ds = [mb[s][0][key] - ma[s][0][key] for s in shared]
        res["Q3_ci"][key] = {"paired_mean_delta_pp": round(100 * sum(ds) / len(ds), 4),
                             "paired_ci95": boot(ds, a.B, a.seed), "n_slots": len(ds)}
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps({k: res[k] for k in ("Q1_slot_exact_same", "Q2_same_rate_by_round_bucket", "Q3_ci")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
