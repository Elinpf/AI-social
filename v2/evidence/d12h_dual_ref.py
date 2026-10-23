#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-H 双参照系出数器（**在余下轮次跑完前冻结**，实现 `v2/refs/D12H-amendment-2-foreign-reference.md` §2/§3）。

判据（照 amendment-2）：
  * **主（判据 1）** = `overlap_frac` 配对差，参照系 = **固定外部语料 T5 同窗前缀**（`round < R`）；
    `R` 默认取被读日志的最大 round + 1（同窗），可 `--window-rounds` 显式指定；
    `d = off_frac − on_frac`（**d > 0 ⇒ ON 组重叠更低 = 更好**）；
    **全部有效对（含 d=0）** 取均值；slot 级 + 线程级双口径 CI，**不得互代**；
  * 第二参照 = **T1 同窗前缀**（同规则），主判据要求**两个外部参照同向且 CI 均不含 0**；
  * **自身历史仅作一致性对照**，强制标注「含自亲和偏差、参照系偏向 OFF、不得单独判定」；
  * **必须同报绝对命中条数**（`满足 hash ∈ 参照语料` 的 shingle 个数），防比率被长度带偏（ON 短 10.7%）；
  * `|shingles| = 0` ⇒ `N/A` 计数，不记 0。

hash 约定与 `d12h_gate_check.py` 相同：
  `blake2b(shingle.encode("utf-8"), digest_size=8).hexdigest()`；shingle = `normalize_body` 后 8-window。

用法：
    python3 v2/evidence/d12h_dual_ref.py \
      --run .worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl \
      --ref-t5 v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
      --ref-t1 v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl \
      --out-json v2/evidence/d12h_dual_ref.json
（T5 前缀语料默认取 `run_d12g_diverse2_n16r60_seed42`，见 --ref-t5 默认值；T1 前缀取 `run_d12c_on_n16r60_seed42`。）
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
HERE = os.path.dirname(os.path.abspath(__file__))


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
            continue
        if r.get("type") not in MSG_TYPES:
            continue
        p = r.get("payload") or {}
        rows.append({"round": r.get("round") if r.get("round") is not None else 0,
                     "seq": r.get("seq") if r.get("seq") is not None else 0,
                     "body": p.get("body") or "",
                     "slot": (p.get("thread_id"), p.get("turn_index"), p.get("from")),
                     "ctx": (p.get("ctx") or {}).get("d12h")})
    rows.sort(key=lambda x: (x["round"], x["seq"]))
    return rows


def corpus_of(path: str, rounds_limit: int | None):
    hs = set()
    n = 0
    for r in load(path):
        if rounds_limit is not None and r["round"] >= rounds_limit:
            continue
        hs |= {h8(s) for s in shingles(r["body"])}
        n += 1
    return hs, n


def boot(vals, B, seed):
    rnd = random.Random(seed)
    n = len(vals)
    out = []
    for _ in range(B):
        out.append(sum(vals[rnd.randrange(n)] for _ in range(n)) / n)
    out.sort()
    lo, hi = out[int(0.025 * B)], out[int(0.975 * B) - 1]
    return {"ci95_lo": round(lo, 6), "ci95_hi": round(hi, 6),
            "contains_zero": bool(lo <= 0 <= hi)}


def boot_thread(vals, threads, B, seed):
    by = defaultdict(list)
    for v, t in zip(vals, threads):
        by[t].append(v)
    keys = list(by)
    rnd = random.Random(seed)
    out = []
    for _ in range(B):
        pick = [keys[rnd.randrange(len(keys))] for _ in range(len(keys))]
        tot = [v for k in pick for v in by[k]]
        out.append(sum(tot) / len(tot))
    out.sort()
    lo, hi = out[int(0.025 * B)], out[int(0.975 * B) - 1]
    return {"ci95_lo": round(lo, 6), "ci95_hi": round(hi, 6),
            "contains_zero": bool(lo <= 0 <= hi), "n_threads": len(keys)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--ref-t5", default=".worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl")
    ap.add_argument("--ref-t1", default="v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl")
    ap.add_argument("--window-rounds", type=int, default=None,
                    help="外部语料的同窗前缀：只用 round < R；默认 R = 本 run 最大 round + 1")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-json")
    a = ap.parse_args()

    rows = load(a.run)
    R = a.window_rounds if a.window_rounds is not None else (max(r["round"] for r in rows) + 1)

    refs = {}
    for name, path in (("T5_prefix", a.ref_t5), ("T1_prefix", a.ref_t1)):
        hs, n = corpus_of(path, R)
        refs[name] = {"path": path, "sha256": sha256_file(path), "rounds_lt": R,
                      "n_msgs_in_corpus": n, "n_shingles": len(hs), "_set": hs}

    own = set()
    recs = []          # per pair: dict of per-reference fractions and hit counts
    n_na = n_ctx = 0
    nz = {"own": [0, 0]}
    for name in refs:
        nz[name] = [0, 0]
    threads = []
    for r in rows:
        x = r["ctx"]
        if x:
            n_ctx += 1
            on, off = x.get("on") or {}, x.get("off") or {}
            po, pf = on.get("picked"), off.get("picked")
            hs_o = set((on.get("cand_shingle_hashes") or [[]])[po]) if po is not None else set()
            hs_f = set((off.get("cand_shingle_hashes") or [[]])[pf]) if pf is not None else set()
            co = (on.get("cand_shingle_counts") or [None])[po] if po is not None else None
            cf = (off.get("cand_shingle_counts") or [None])[pf] if pf is not None else None
            if not hs_o or not hs_f or co in (0, None) or cf in (0, None):
                n_na += 1
            else:
                rec = {"round": r["round"], "thread": r["slot"][0], "refs": {}}
                for name, rv in list(refs.items()) + [("own_history", {"_set": own})]:
                    c = rv["_set"]
                    rec["refs"][name] = {
                        "on_frac": len(hs_o & c) / len(hs_o),
                        "off_frac": len(hs_f & c) / len(hs_f),
                        "on_hits": len(hs_o & c),
                        "off_hits": len(hs_f & c),
                    }
                recs.append(rec)
                threads.append(r["slot"][0])
        own |= {h8(s) for s in shingles(r["body"])}

    out = {
        "impl": {"path": os.path.abspath(__file__), "sha256": sha256_file(os.path.abspath(__file__))},
        "amendment": "v2/refs/D12H-amendment-2-foreign-reference.md §2/§3",
        "run": {"path": a.run, "sha256": sha256_file(a.run), "n_msgs": len(rows),
                "n_ctx_d12h": n_ctx, "rounds_present_max": max(r["round"] for r in rows) if rows else None,
                "window_rounds_R": R},
        "gate": {"pairs_usable": len(recs), "N/A_rows": n_na,
                 "ctx_hit_rate_pct": round(100 * n_ctx / len(rows), 3) if rows else None},
        "references": {k: {kk: vv for kk, vv in v.items() if kk != "_set"} for k, v in refs.items()},
        "primary": {},
        "consistency_own_history": {},
    }

    def summarize(name):
        ds = [p["refs"][name]["off_frac"] - p["refs"][name]["on_frac"] for p in recs]
        on_hits = [p["refs"][name]["on_hits"] for p in recs]
        off_hits = [p["refs"][name]["off_hits"] for p in recs]
        on_f = [p["refs"][name]["on_frac"] for p in recs]
        off_f = [p["refs"][name]["off_frac"] for p in recs]
        return {
            "n_pairs": len(ds),
            "mean_d_off_minus_on": round(st.mean(ds), 6),
            "gt0_eq0_lt0": [sum(1 for d in ds if d > 0), sum(1 for d in ds if d == 0),
                            sum(1 for d in ds if d < 0)],
            "ci_slot": boot(ds, a.B, a.seed),
            "ci_thread": boot_thread(ds, threads, a.B, a.seed),
            "on_frac_mean": round(st.mean(on_f), 6),
            "off_frac_mean": round(st.mean(off_f), 6),
            "on_hits_mean": round(st.mean(on_hits), 4),
            "off_hits_mean": round(st.mean(off_hits), 4),
            "absolute_hits_note": "绝对命中条数（不除以候选长度）——防比率被长度带偏（ON 候选短约 10.7%）",
            "by_round_10": {},
        }

    def layering(res, name):
        agg = defaultdict(lambda: [0, 0.0, 0.0])
        for p in recs:
            e = agg[(p["round"] // 10) * 10]
            e[0] += 1
            e[1] += p["refs"][name]["on_frac"]
            e[2] += p["refs"][name]["off_frac"]
        for k, v in sorted(agg.items()):
            res["by_round_10"][str(k)] = {"n": v[0], "on_mean": round(v[1] / v[0], 6),
                                          "off_mean": round(v[2] / v[0], 6)}

    for name in refs:
        s = summarize(name)
        layering(s, name)
        out["primary"][name] = s
    own_s = summarize("own_history")
    layering(own_s, "own_history")
    own_s["WARNING"] = "含自亲和偏差（本 run 历史仅 ON 生成）、参照系偏向 OFF、**不得单独作判定**"
    out["consistency_own_history"] = own_s

    # 方向一致性
    def sign(x):
        return "+" if x > 0 else ("-" if x < 0 else "0")
    dirs = {k: sign(v["mean_d_off_minus_on"]) for k, v in out["primary"].items()}
    out["direction_check"] = {
        "signs": dirs,
        "external_refs_agree": len(set(dirs.values())) == 1,
        "own_history_sign": sign(own_s["mean_d_off_minus_on"]),
        "own_vs_external_reversed": bool(dirs and sign(own_s["mean_d_off_minus_on"]) not in set(dirs.values())),
        "note": "d = off_frac − on_frac（d>0 ⇒ ON 重叠更低）。两个外部参照须同向且 CI 均不含 0 才可判；"
                "自身历史若反向，报告必须并列写出，不得择一。",
    }

    if a.out_json:
        with open(a.out_json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
    print(json.dumps({"gate": out["gate"], "direction_check": out["direction_check"]}, ensure_ascii=False, indent=2))
    for name, s in list(out["primary"].items()) + [("own_history", own_s)]:
        print("%-12s n=%d mean(d)=%+.6f CI_slot=[%+.6f,%+.6f] CI_thr=[%+.6f,%+.6f] hits %.3f vs %.3f"
              % (name, s["n_pairs"], s["mean_d_off_minus_on"], s["ci_slot"]["ci95_lo"], s["ci_slot"]["ci95_hi"],
                 s["ci_thread"]["ci95_lo"], s["ci_thread"]["ci95_hi"], s["on_hits_mean"], s["off_hits_mean"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
