#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-H 出数器 + 1/3 自检闸（**放号前冻结**，禁止在看到结果后再改口径）。

定位：只读 `run.jsonl`（含中途快照），不联网、不调 LLM。
口径全部取自 `v2/refs/D12H-prereg-in-context-pairing.md` §2 / §3 / §5 / §6：
  * `overlap_frac(c) = |shingles(c) ∩ 历史全体 shingle| / |shingles(c)|`
    历史 = 全批、`(round, seq)` **严格小于**本消息的所有 MSG；`normalize_body` 后 8-window；
    `|shingles(c)| = 0` ⇒ `N/A`（**不记 0**）。
  * **主判据 = 全部对（含 d=0）的均值 + 全部对的配对 CI**；
    非零对均值/CI 只作描述，且必须标注"条件于 d≠0，含选择性偏差，不得作效应量"。
  * §3 闸（**实现自检闸**，不承担分辨力判定）：`d≠0` 占比 < **5%** ⇒ 判「**实现层可疑，先查接线**」
    （3.5–4.6% 是旧 `recent16`+argmin 口径的特征值），并核 4 项。
  * 双口径 CI：slot 级（`thread_id × turn_index × from`）+ **线程级**（按 thread 整簇重采样），**不得互代**。

hash 约定（**必须与实现一致，否则交集算不出来**）：
  `blake2b(shingle.encode("utf-8"), digest_size=8).hexdigest()`（16 hex 字符/项）。
  `--hash-check` 可先用一批已落库 body 反验：把历史 body 重算 hash 后，与被选候 hash 列表求交，
  若实现一致则 `overlap_frac > 0` 的比例应落在经验区间（约 30–35%，见 D12-G 实测 32.2/34.1%）。

用法：
    # 1/3 自检（中途快照，只看 4 项 + 非零占比）
    python3 v2/evidence/d12h_gate_check.py --run <run.jsonl> --gate
    # 全量出数
    python3 v2/evidence/d12h_gate_check.py --run <run.jsonl> --out-json v2/evidence/d12h_readout.json
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
PUNCT_RE = re.compile(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)\[\]【】]")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def normalize_body(body: str) -> str:
    s = (body or "").strip().lower().replace("（", "(").replace("）", ")")
    return PUNCT_RE.sub("", s)


def shingles(body: str):
    t = normalize_body(body)
    return {t[i:i + 8] for i in range(max(0, len(t) - 7))}


def h8(s: str) -> str:
    return hashlib.blake2b(s.encode("utf-8"), digest_size=8).hexdigest()


def load(path: str):
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or '"MSG_' not in line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue  # 中途快照末行可能不完整
        if r.get("type") not in MSG_TYPES:
            continue
        p = r.get("payload") or {}
        rows.append({
            "round": r.get("round") if r.get("round") is not None else 0,
            "seq": r.get("seq") if r.get("seq") is not None else 0,
            "body": p.get("body") or "",
            "slot": (p.get("thread_id"), p.get("turn_index"), p.get("from")),
            "ctx": (p.get("ctx") or {}).get("d12h"),
        })
    rows.sort(key=lambda x: (x["round"], x["seq"]))
    return rows


def frac_from_hashes(hlist, hist_hashes):
    """|shingles(c) ∩ 历史| / |shingles(c)|；分母用 stored 列表长度（= cand_shingle_counts）。"""
    if not hlist:
        return None
    s = set(hlist)
    return len(s & hist_hashes) / len(s)


def boot(ds, B, seed):
    rnd = random.Random(seed)
    n = len(ds)
    vals = []
    for _ in range(B):
        vals.append(sum(ds[rnd.randrange(n)] for _ in range(n)) / n)
    vals.sort()
    return {"ci95_lo": round(vals[int(0.025 * B)], 6), "ci95_hi": round(vals[int(0.975 * B) - 1], 6),
            "contains_zero": bool(vals[int(0.025 * B)] <= 0 <= vals[int(0.975 * B) - 1])}


def boot_thread(ds, groups, B, seed):
    """线程级：整簇（同一 thread 的所有对）有放回重采样。"""
    by = defaultdict(list)
    for d, g in zip(ds, groups):
        by[g].append(d)
    keys = list(by)
    rnd = random.Random(seed)
    vals = []
    for _ in range(B):
        pick = [keys[rnd.randrange(len(keys))] for _ in range(len(keys))]
        tot = [d for k in pick for d in by[k]]
        vals.append(sum(tot) / len(tot))
    vals.sort()
    return {"ci95_lo": round(vals[int(0.025 * B)], 6), "ci95_hi": round(vals[int(0.975 * B) - 1], 6),
            "contains_zero": bool(vals[int(0.025 * B)] <= 0 <= vals[int(0.975 * B) - 1]),
            "n_threads": len(keys)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-json")
    a = ap.parse_args()

    rows = load(a.run)
    hist = set()          # 历史全体 shingle hash（严格小于当前消息）
    pairs = []            # (slot, round, on_frac, off_frac)
    n_ctx = n_na = n_counts_zero = n_allzero = n_same_hashes = 0
    n_msgs = 0
    layer = defaultdict(lambda: [0, 0])
    for r in rows:
        n_msgs += 1
        x = r["ctx"]
        if x:
            n_ctx += 1
            on, off = x.get("on") or {}, x.get("off") or {}
            po, pf = on.get("picked"), off.get("picked")
            ho = (on.get("cand_shingle_hashes") or [[]])[po] if po is not None else []
            hf = (off.get("cand_shingle_hashes") or [[]])[pf] if pf is not None else []
            co = (on.get("cand_shingle_counts") or [None])[po] if po is not None else None
            cf = (off.get("cand_shingle_counts") or [None])[pf] if pf is not None else None
            if co in (0, None) or cf in (0, None):
                n_na += 1
                if co == 0 or cf == 0:
                    n_counts_zero += 1
            else:
                fo, ff = frac_from_hashes(ho, hist), frac_from_hashes(hf, hist)
                if fo is not None and ff is not None:
                    pairs.append((r["slot"], r["round"], fo, ff))
                    if fo == 0 and ff == 0:
                        n_allzero += 1
                if ho and hf and set(ho) == set(hf):
                    n_same_hashes += 1
        hist |= {h8(s) for s in shingles(r["body"])}

    ds = [on - off for _, _, on, off in pairs]        # >0 ⇒ ON 组交集更小
    nonzero = [d for d in ds if d != 0]
    nz_share = 100.0 * len(nonzero) / len(ds) if ds else None
    out = {
        "impl_sha256": sha256_file(os.path.abspath(__file__)),
        "run": {"path": a.run, "sha256": sha256_file(a.run), "n_msgs_total": n_msgs, "n_ctx_d12h": n_ctx},
        "gate_items": {
            "ctx_hit_rate": round(100 * n_ctx / n_msgs, 3) if n_msgs else None,
            "N/A_share_pct": round(100 * n_na / n_ctx, 3) if n_ctx else None,
            "cand_shingle_counts_zero_rows": n_counts_zero,
            "overlap_frac_all_zero_pairs": n_allzero,
            "on_off_hashes_identical_rows": n_same_hashes,
            "pairs_usable": len(ds),
            "nonzero_pair_share_pct": round(nz_share, 3) if nz_share is not None else None,
        },
        "verdict_hint": ("IMPLEMENTATION_SUSPECT_CHECK_WIRING" if (nz_share is not None and nz_share < 5.0)
                         else "GATE_OK"),
        "primary": {},
        "descriptive": {},
    }
    if ds:
        out["primary"] = {
            "estimand": "全部对（含 d=0）的均值 —— 每条消息的平均效应",
            "mean_delta_all_pairs": round(st.mean(ds), 6),
            "ci_slot": boot(ds, a.B, a.seed),
            "ci_thread": boot_thread(ds, [q[0][0] for q in pairs], a.B, a.seed),
            "note": "两口径不得互代；CI 含 0 ⇒ 无结论",
        }
        out["descriptive"] = {
            "nonzero_pairs": len(nonzero),
            "nonzero_mean_delta": round(st.mean(nonzero), 6) if nonzero else None,
            "nonzero_ci_slot": boot(nonzero, a.B, a.seed) if nonzero else None,
            "WARNING": "条件于 d≠0，含选择性偏差，不得作效应量",
            "split": {"gt0": sum(1 for d in ds if d > 0), "eq0": sum(1 for d in ds if d == 0),
                      "lt0": sum(1 for d in ds if d < 0)},
            "on_frac": {"mean": round(st.mean([p[2] for p in pairs]), 6),
                        "median": round(st.median([p[2] for p in pairs]), 6),
                        "p90": round(sorted(p[2] for p in pairs)[int(0.9 * len(pairs))], 6),
                        "gt0_share_pct": round(100 * sum(1 for p in pairs if p[2] > 0) / len(pairs), 3)},
            "off_frac": {"mean": round(st.mean([p[3] for p in pairs]), 6),
                         "median": round(st.median([p[3] for p in pairs]), 6),
                         "p90": round(sorted(p[3] for p in pairs)[int(0.9 * len(pairs))], 6),
                         "gt0_share_pct": round(100 * sum(1 for p in pairs if p[3] > 0) / len(pairs), 3)},
            "by_round_10": {},
        }
        for (_, rd, on, off) in pairs:
            e = out["descriptive"]["by_round_10"].setdefault(str((rd // 10) * 10), [0, 0.0, 0.0])
            e[0] += 1
            e[1] += on
            e[2] += off
        for k, v in out["descriptive"]["by_round_10"].items():
            out["descriptive"]["by_round_10"][k] = {"n": v[0], "on_mean": round(v[1] / v[0], 6),
                                                    "off_mean": round(v[2] / v[0], 6)}
    if a.out_json:
        with open(a.out_json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
    print(json.dumps(out["gate_items"], ensure_ascii=False, indent=2))
    if not a.gate and out["primary"]:
        print(json.dumps(out["primary"], ensure_ascii=False, indent=2))
    print("verdict_hint:", out["verdict_hint"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
