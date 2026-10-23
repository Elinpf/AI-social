#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-H 判定指标 `overlap_frac` 的**出数时全局重算**（不采信落盘自证值）。

口径（写死，改这里等于改判据 ⇒ 必须先改 `v2/refs/D12H-prereg-in-context-pairing.md` 并重跑）：

1. **shingle** = `code/life/d12e_shingles.py` 的 8-gram（`normalize` 去空白/标点/全角括号→半角/小写），
   逐 shingle 取 `blake2b(digest_size=8)` 十六进制（与 agent 落盘的 `cand_shingle_hashes` **同一算法**，
   所以候选的 hash 列表可直接与「历史前缀」的 hash 集合求交）。
2. **历史** = 全批 `MSG_DM/MSG_GROUP/MSG_PUBLIC` 中 `(round, seq)` **严格小于**本消息的全部台词
   （**含自比排除**：本消息自身不进历史）。
3. `overlap_frac(x) = |shingles(x) ∩ 历史shingles| / |shingles(x)|`；`|shingles| = 0` ⇒ **`N/A`（不得记 0）**。
4. **J-1**：`d_i = off.overlap_frac[off.picked] − on.overlap_frac[on.picked]`，对**全部有效对**取 `mean(d)`
   （**含 `d = 0`**；有效对 = 两组被选候 `|shingles|` 均 > 0）。`d ≠ 0` 均值只作描述，须标选择性偏差。
5. **CI**：`B = 2000`、`seed = 42`，**slot 级**（重采样单位 = 一条消息对）与**线程级**
   （重采样单位 = `thread_id` 簇，抽到则并入该簇全部对）**双报、不得互代**。

用法（在仓库根或任意目录均可）：
    python3 tools/d12h/overlap_frac.py --log <run.jsonl> --out-json v2/evidence/<dir>/d12h_metrics.json

退出码：0 = 正常出数；2 = 日志不足以出数（无 `ctx.d12h` 消息）；3 = 日志结构异常（`(round,seq)` 非严格递增）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from collections import Counter, defaultdict

MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")
B_DEFAULT = 2000
SEED_DEFAULT = 42
ON_SUFFIX = "\n开口先叫对方一声，别用你上一句或对方上一句的前四个字。"

# 与 agent 端同算法（见 code/life/d12e_shingles.py + LifeLayerAgent._d12h_shingle_hashes）
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "code"))
from life import d12e_shingles as D12S  # noqa: E402


def _h(sh: str) -> str:
    return hashlib.blake2b(sh.encode("utf-8"), digest_size=8).hexdigest()


def body_hashes(body: str) -> list:
    return sorted({_h(s) for s in D12S.shingles(body or "")})


def load_messages(path: str):
    msgs = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("type") not in MSG_TYPES:
            continue
        pl = d.get("payload") or {}
        msgs.append({
            "round": int(d.get("round") if d.get("round") is not None else pl.get("round", 0) or 0),
            "seq": int(d.get("seq") if d.get("seq") is not None else pl.get("seq", 0) or 0),
            "body": pl.get("body") or "",
            "thread_id": pl.get("thread_id"),
            "place": pl.get("place"),
            "ctx": pl.get("ctx") or {},
            "type": d.get("type"),
        })
    return msgs


def _quant(xs, q):
    if not xs:
        return None
    ys = sorted(xs)
    k = (len(ys) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(ys) - 1)
    return round(ys[lo] + (ys[hi] - ys[lo]) * (k - lo), 6)


def _mean(xs):
    return round(statistics.fmean(xs), 6) if xs else None


def _slot_ci(pairs, b, rng):
    """slot 级：重采样单位 = 一条消息对。"""
    n = len(pairs)
    if n == 0:
        return None
    ds = [p["d"] for p in pairs]
    out = []
    for _ in range(b):
        s = [ds[rng.randrange(n)] for _ in range(n)]
        out.append(statistics.fmean(s))
    return [round(_quant(out, 0.025), 6), round(_quant(out, 0.975), 6)]


def _thread_ci(pairs, b, rng):
    """线程级：重采样单位 = thread_id 簇（抽到则并入该簇全部对）。"""
    buckets = defaultdict(list)
    for p in pairs:
        buckets[p["thread_id"] or "<none>"].append(p["d"])
    keys = list(buckets)
    if not keys:
        return None, 0
    ns = len(keys)
    out = []
    for _ in range(b):
        pool = []
        for _ in range(ns):
            pool.extend(buckets[keys[rng.randrange(ns)]])
        out.append(statistics.fmean(pool) if pool else 0.0)
    return [round(_quant(out, 0.025), 6), round(_quant(out, 0.975), 6)], ns


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--b", type=int, default=B_DEFAULT)
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    a = ap.parse_args(argv)

    msgs = load_messages(a.log)
    # 历史前缀要求 (round, seq) 严格递增；不递增就报错（不静默猜顺序）
    key = [(m["round"], m["seq"]) for m in msgs]
    for i in range(1, len(key)):
        if not key[i] > key[i - 1]:
            print(f"[FATAL] 日志 (round,seq) 非严格递增：{key[i-1]} -> {key[i]}", file=sys.stderr)
            return 3

    # ---- 逐消息重算：历史前缀 hash 集合（严格小于本消息） ----
    prefix = set()
    pairs = []
    n_d12h = 0
    body_eq_on = 0
    field_missing = 0
    na_on = na_off = 0
    na_hashes = []          # |shingles|==0 的候选文本 sha（只记录，便于定位）
    on_overlaps, off_overlaps = [], []
    threads_of_pair = set()
    for m in msgs:
        own = body_hashes(m["body"])
        ctx = m["ctx"]
        h = ctx.get("d12h") if isinstance(ctx, dict) else None
        if not isinstance(h, dict):
            prefix |= set(own)          # 非本臂消息同样进入历史（全批前序台词 = 历史）
            continue
        n_d12h += 1
        on, off = h.get("on") or {}, h.get("off") or {}
        spins = [i for i in (on.get("picked"), off.get("picked")) if not isinstance(i, int)]
        hs = (on.get("cand_shingle_hashes") or [], off.get("cand_shingle_hashes") or [])
        cs = (on.get("cand_shingle_counts") or [], off.get("cand_shingle_counts") or [])
        if spins or len(hs[0]) != 3 or len(hs[1]) != 3 or len(cs[0]) != 3 or len(cs[1]) != 3:
            field_missing += 1
            prefix |= set(own)
            continue
        on_h = hs[0][on["picked"]]
        off_h = hs[1][off["picked"]]
        on_c = cs[0][on["picked"]]
        off_c = cs[1][off["picked"]]
        # 自检：落库 body 必须等于 ON 组选中候选（否则「落库的不是被判定那条」）
        if own == sorted(on_h):
            body_eq_on += 1
        else:
            print(f"[WARN] seq={m['seq']} round={m['round']} 落库 body 的 shingle 与 ON 选中候选不一致",
                  file=sys.stderr)
        rec = {"round": m["round"], "seq": m["seq"], "thread_id": m["thread_id"],
               "place": m["place"], "on_n": on_c, "off_n": off_c}
        for tag, hh, cc, store in (("on", on_h, on_c, on_overlaps),
                                   ("off", off_h, off_c, off_overlaps)):
            if cc <= 0:
                rec[f"{tag}_overlap_frac"] = None
                if tag == "on":
                    na_on += 1
                else:
                    na_off += 1
                na_hashes.append({"seq": m["seq"], "group": tag})
            else:
                frac = len(set(hh) & prefix) / cc
                rec[f"{tag}_overlap_frac"] = round(frac, 6)
                store.append(frac)
        valid = rec["on_overlap_frac"] is not None and rec["off_overlap_frac"] is not None
        rec["valid"] = valid
        if valid:
            rec["d"] = round(rec["off_overlap_frac"] - rec["on_overlap_frac"], 6)
            pairs.append(rec)
            threads_of_pair.add(m["thread_id"] or "<none>")
        prefix |= set(own)

    if n_d12h == 0:
        print("[FATAL] 日志内没有任何带 ctx.d12h 的消息", file=sys.stderr)
        return 2

    ds = [p["d"] for p in pairs]
    pos = [d for d in ds if d > 0]
    neg = [d for d in ds if d < 0]
    zero = [d for d in ds if d == 0]
    nz = [d for d in ds if d != 0]
    rng = random.Random(a.seed)
    slot_ci = _slot_ci(pairs, a.b, rng)
    rng2 = random.Random(a.seed)
    thread_ci, n_threads = _thread_ci(pairs, a.b, rng2)

    # 10 轮分层（证明差不是时间趋势驱动；只作描述）
    strat = defaultdict(list)
    for p in pairs:
        strat[(p["round"] // 10) * 10].append(p["d"])
    strat_out = [{"round_from": k, "n": len(v), "mean_d": _mean(v)}
                 for k, v in sorted(strat.items())]

    out = {
        "log": os.path.abspath(a.log),
        "spec": {
            "ngram": D12S.NGRAM, "shingle_hash": "blake2b-8B-hex",
            "history": "全批 MSG_DM/MSG_GROUP/MSG_PUBLIC 中 (round,seq) 严格小于本消息",
            "valid_pair": "ON 与 OFF 被选候 |shingles| 均 > 0",
            "bootstrap": {"B": a.b, "seed": a.seed, "slot_unit": "消息对", "thread_unit": "thread_id 簇"},
        },
        "counts": {
            "messages": len(msgs),
            "messages_with_ctx_d12h": n_d12h,
            "valid_pairs": len(pairs),
            "invalid_pairs": n_d12h - len(pairs),
            "na_on": na_on, "na_off": na_off,
            "field_missing": field_missing,
            "body_equals_on_picked": body_eq_on,
            "threads_in_valid_pairs": len(threads_of_pair),
            "na_detail": na_hashes[:20],
        },
        "J1": {
            "mean_d_all_valid_incl_zero": _mean(ds),
            "mean_d_nonzero_descriptive_only": _mean(nz),
            "n_valid": len(ds),
            "split": {"gt0": len(pos), "eq0": len(zero), "lt0": len(neg)},
            "ci_slot": slot_ci,
            "ci_thread": thread_ci,
            "threads": n_threads,
        },
        "distributions": {
            "on_overlap_frac": {"mean": _mean(on_overlaps), "p50": _quant(on_overlaps, 0.5),
                                "p90": _quant(on_overlaps, 0.9), "n": len(on_overlaps),
                                "gt0_share": round(len([x for x in on_overlaps if x > 0]) / len(on_overlaps), 6)
                                if on_overlaps else None},
            "off_overlap_frac": {"mean": _mean(off_overlaps), "p50": _quant(off_overlaps, 0.5),
                                 "p90": _quant(off_overlaps, 0.9), "n": len(off_overlaps),
                                 "gt0_share": round(len([x for x in off_overlaps if x > 0]) / len(off_overlaps), 6)
                                 if off_overlaps else None},
        },
        "strata_10round": strat_out,
        "pairs": pairs,
    }
    with open(a.out_json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    pp = lambda x: "None" if x is None else f"{x*100:+.2f}pp"   # noqa: E731
    print(json.dumps({k: out[k] for k in ("counts", "J1")}, ensure_ascii=False, indent=1))
    print(f"[J-1] mean(d) 含 d=0 = {pp(out['J1']['mean_d_all_valid_incl_zero'])}"
          f"（n={len(ds)}）slot CI={slot_ci} thread CI={thread_ci}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
