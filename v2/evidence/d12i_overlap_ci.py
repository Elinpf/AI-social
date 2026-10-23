#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-I 主判据出数器：`overlap_frac(4g)` 对固定外部语料 `S_ext` + 双口径 bootstrap CI。

口径（照 `v2/refs/D12I-prereg-aligned-objective.md` §1/§3 与 §⑤-2 的更正）：
  * shingle = `normalize`（镜像 `code/life/d12e_shingles.py::normalize`，与 `tools/d5/dialogue_metrics.py::normalize_body` 一致）
    + **4-gram** 窗口 + `blake2b(digest_size=8).hexdigest()`（与 `S_ext` 生成时同算法）；
  * `overlap_frac(c) = |shingles(c) ∩ S_ext| / |shingles(c)|`，`|shingles(c)|=0 ⇒ N/A`（不记 0）；
  * **对比语料 = T5 留出集 `round ∈ [40,59]`**（`S_ext` 本体是 T5 `round<40`，对前缀自身算恒 ≈1.0 ⇒ 无意义）；
  * CI：独立两样本 bootstrap（B=2000 / seed=42），消息级 + **线程级**（按 `thread_id` 整簇重采样），两口径不得互代。

用法：
    python3 v2/evidence/d12i_overlap_ci.py \
      --run .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
      --sext .worktrees/d12i-aligned/v2/evidence/d12i_external_shingles_4gram.json \
      --holdout .worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl \
      --holdout-rounds 40 59 --out-json v2/evidence/d12i_overlap_ci.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import statistics as st
import sys
from collections import defaultdict

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
_STRIP = r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)\[\]【】]"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def normalize(body: str) -> str:
    s = (body or "").strip().lower().replace("（", "(").replace("）", ")")
    return re.sub(_STRIP, "", s)


def sh4(body: str):
    t = normalize(body)
    return {hashlib.blake2b(t[i:i + 4].encode("utf-8"), digest_size=8).hexdigest()
            for i in range(max(0, len(t) - 3))}


def load(path: str):
    rows = []
    for line in open(path, encoding="utf-8"):
        if '"MSG_' not in line:
            continue
        r = json.loads(line)
        if r.get("type") not in MSG_TYPES:
            continue
        p = r.get("payload") or {}
        rows.append({"round": r.get("round") or 0, "thread": p.get("thread_id"),
                     "body": p.get("body") or ""})
    rows.sort(key=lambda x: (x["round"], x["thread"] or ""))
    return rows


def fracs(rows, sext, lo=None, hi=None):
    out = []
    for r in rows:
        if lo is not None and not (lo <= r["round"] <= hi):
            continue
        s = sh4(r["body"])
        if not s:
            continue
        out.append((len(s & sext) / len(s), r["thread"]))
    return out


def boot_ind(a, b, B, seed):
    rnd = random.Random(seed)
    na, nb = len(a), len(b)
    out = []
    for _ in range(B):
        x = [a[rnd.randrange(na)] for _ in range(na)]
        y = [b[rnd.randrange(nb)] for _ in range(nb)]
        out.append(st.mean(x) - st.mean(y))
    out.sort()
    return [round(100 * out[int(0.025 * B)], 4), round(100 * out[int(0.975 * B) - 1], 4)]


def boot_thread(a, b, B, seed):
    ga, gb = defaultdict(list), defaultdict(list)
    for v, t in a:
        ga[t].append(v)
    for v, t in b:
        gb[t].append(v)
    ka, kb = list(ga), list(gb)
    rnd = random.Random(seed)
    out = []
    for _ in range(B):
        pa = [ka[rnd.randrange(len(ka))] for _ in range(len(ka))]
        pb = [kb[rnd.randrange(len(kb))] for _ in range(len(kb))]
        xa = [v for k in pa for v in ga[k]]
        xb = [v for k in pb for v in gb[k]]
        out.append(st.mean(xa) - st.mean(xb))
    out.sort()
    return {"ci95_pp": [round(100 * out[int(0.025 * B)], 4), round(100 * out[int(0.975 * B) - 1], 4)],
            "n_threads": [len(ka), len(kb)]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--sext", required=True)
    ap.add_argument("--holdout", required=True)
    ap.add_argument("--holdout-rounds", nargs=2, type=int, default=[40, 59])
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-json")
    a = ap.parse_args()

    sx = json.load(open(a.sext, encoding="utf-8"))
    sext = set(sx["shingles"])
    A = fracs(load(a.run), sext)
    B_ = fracs(load(a.holdout), sext, a.holdout_rounds[0], a.holdout_rounds[1])
    va, vb = [x for x, _ in A], [x for x, _ in B_]
    res = {
        "impl": {"path": os.path.abspath(__file__), "sha256": sha256_file(os.path.abspath(__file__))},
        "policy": {"ngram": 4, "hash": "blake2b digest_size=8 hex",
                   "metric": "|shingles(c) ∩ S_ext| / |shingles(c)|",
                   "compare": "T5 holdout round in [%d,%d]" % tuple(a.holdout_rounds),
                   "B": a.B, "seed": a.seed, "rule": "CI 含 0 ⇒ 不可分辨"},
        "inputs": {"run": {"path": a.run, "sha256": sha256_file(a.run)},
                   "sext": {"path": a.sext, "sha256": sha256_file(a.sext),
                            "content_sha256": sx.get("spec", {}).get("content_sha256"),
                            "n_shingles": len(sext)},
                   "holdout": {"path": a.holdout, "sha256": sha256_file(a.holdout)}},
        "run_arm": {"n": len(va), "mean": round(st.mean(va), 6), "median": round(st.median(va), 6),
                    "zero_share_pct": round(100 * sum(1 for v in va if v == 0) / len(va), 3)},
        "holdout_arm": {"n": len(vb), "mean": round(st.mean(vb), 6), "median": round(st.median(vb), 6),
                        "zero_share_pct": round(100 * sum(1 for v in vb if v == 0) / len(vb), 3)},
        "diff": {
            "pp": round(100 * (st.mean(va) - st.mean(vb)), 4),
            "median_pp": round(100 * (st.median(va) - st.median(vb)), 4),
            "relative_pct": round(100 * (st.mean(va) / st.mean(vb) - 1), 2),
            "ci_message_pp": boot_ind(va, vb, a.B, a.seed),
            "ci_thread": boot_thread(A, B_, a.B, a.seed),
        },
    }
    res["diff"]["ci_message_contains_zero"] = bool(res["diff"]["ci_message_pp"][0] <= 0 <= res["diff"]["ci_message_pp"][1])
    t = res["diff"]["ci_thread"]["ci95_pp"]
    res["diff"]["ci_thread_contains_zero"] = bool(t[0] <= 0 <= t[1])
    if a.out_json:
        with open(a.out_json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
    print(json.dumps({k: res[k] for k in ("run_arm", "holdout_arm", "diff")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
