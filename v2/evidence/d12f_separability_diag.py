#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-F 可分性诊断：**为什么候选不可分**——是"文本几乎相同"，还是"文本不同但打分器分辨不出"？

三组数（leader 16:59 指定）：
1. **同一 prompt 下三候选两两文本相似度**：对每条消息取它的 3 个候选（run.jsonl 中连续的 3 条 dialogue `LLM_CALL`），
   用 hashtable `cache_key -> text`（来自侧车 `freeze_cache/responses/*.json` 的 `cache_key`/`text` 字段）取回候选文本，
   计算两两 char-bigram Jaccard（与 `normalize_body` 同口径：去标点/空白/小写）；
   报 **中位数 / p90 / 最小 / 最大**，以及"三候选两两 jaccard 全部 ≥0.90 的消息占比"。
2. **`scores` 极差分布**（max-min，来自 MSG 的 `payload.ctx.d12f.scores`）：中位数 / p90 / 等于 0 的占比。
3. `picked` 与 `argmin` 一致率：本脚本不重算（见 `d12f_gates_*.json` 的 M3）。

判读规则（写死，先于读数）：
- 若「候选两两 jaccard 中位数 ≥0.60 且 scores 极差中位数 = 0」⇒ **结构多样化没让候选文本分开**（机制本身无效）
- 若「候选两两 jaccard 中位数 < 0.60 但 scores 极差中位数为 0」⇒ **文本不同、打分器分辨不出**（评分器问题）
- 其余情形 ⇒ 部分可分，按实际数报，不下二元结论

用法：
    python3 v2/evidence/d12f_separability_diag.py --run-jsonl <run.jsonl> \
        --responses-dir /tmp/d12f_side/freeze_cache/responses \
        --out-json v2/evidence/d12f_separability_diag.json --snapshot-at <ISO> [--partial]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from collections import defaultdict

PUNCT = re.compile(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)\[\]【】（）]")


def norm(s: str) -> str:
    return PUNCT.sub("", (s or "").strip().lower())


def bigrams(t: str) -> set:
    return {t[i:i + 2] for i in range(len(t) - 1)}


def jac(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def quantiles(vals, qs):
    if not vals:
        return {q: None for q in qs}
    v = sorted(vals)

    def p(q):
        if len(v) == 1:
            return v[0]
        k = (len(v) - 1) * q
        lo, hi = int(k), min(int(k) + 1, len(v) - 1)
        return v[lo] + (v[hi] - v[lo]) * (k - lo)

    return {q: round(p(q), 4) for q in qs}


def load_texts(resp_dir):
    m = {}
    if not os.path.isdir(resp_dir):
        return m
    for fn in os.listdir(resp_dir):
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(resp_dir, fn), encoding="utf-8"))
        except Exception:
            continue
        ck, txt = d.get("cache_key"), d.get("text")
        if ck and isinstance(txt, str):
            m[ck] = txt
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-jsonl", required=True)
    ap.add_argument("--responses-dir", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--snapshot-at", default=None)
    ap.add_argument("--partial", action="store_true")
    a = ap.parse_args(argv)

    texts = load_texts(a.responses_dir)

    events = []
    for line in open(a.run_jsonl, encoding="utf-8"):
        try:
            events.append(json.loads(line))
        except Exception:
            continue

    # 分组：连续的 dialogue LLM_CALL（遇到 MSG_* 或非 dialogue 调用即结算）
    cand_sets = []   # 每项: {'seqs':[...], 'cache_keys':[...], 'msg_seq':int}
    buf = []
    for e in events:
        t = e.get("type")
        pl = e.get("payload") or {}
        if t == "LLM_CALL" and pl.get("purpose") == "dialogue":
            buf.append({"seq": e.get("seq"), "ck": pl.get("cache_key"), "round": e.get("round")})
            continue
        if t in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            if len(buf) >= 2:
                cand_sets.append({"cands": buf[:], "msg_seq": e.get("seq"), "round": e.get("round")})
            buf = []
        elif t == "LLM_CALL":
            # 其他 purpose 打断候选块：不结算（同一消息的 3 候选之间不会插别的 purpose，保险起见拼接）
            continue

    pair_jacs = []
    triples_all_same = 0
    n_with_text = 0
    miss_text = 0
    per_msg = []
    for item in cand_sets:
        cks = [c["ck"] for c in item["cands"]]
        ts = [texts.get(ck) for ck in cks]
        if any(x is None for x in ts):
            miss_text += 1
            continue
        n_with_text += 1
        bs = [bigrams(norm(x)) for x in ts]
        js = []
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                js.append(jac(bs[i], bs[j]))
        if js and min(js) >= 0.90:
            triples_all_same += 1
        pair_jacs.extend(js)
        per_msg.append({"round": item["round"], "msg_seq": item["msg_seq"],
                        "n_cands": len(ts), "pair_jaccard": [round(x, 4) for x in js]})

    # scores 极差
    ranges = []
    all_same = 0
    n_msg = 0
    for e in events:
        if e.get("type") not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            continue
        d = (e.get("payload") or {}).get("ctx", {}).get("d12f")
        if not isinstance(d, dict):
            continue
        sc = d.get("scores") or []
        if len(sc) < 2:
            continue
        n_msg += 1
        rng = max(sc) - min(sc)
        ranges.append(rng)
        if rng == 0:
            all_same += 1

    q = quantiles(pair_jacs, [0.5, 0.9])
    rq = quantiles(ranges, [0.5, 0.9])
    med_j = q[0.5]
    med_r = rq[0.5]
    if med_j is not None and med_j >= 0.60 and med_r == 0:
        verdict = "A_候选文本几乎相同（结构多样化没让候选分开 ⇒ D12-F 机制本身无效）"
    elif med_j is not None and med_j < 0.60 and med_r == 0:
        verdict = "B_文本不同但打分器分辨不出（⇒ 评分器问题，改评分比改生成便宜）"
    else:
        verdict = "C_部分可分（按实际数报，不下二元结论）"

    out = {
        "reader": "v2/evidence/d12f_separability_diag.py",
        "source_run_jsonl": a.run_jsonl,
        "snapshot_at": a.snapshot_at,
        "partial": bool(a.partial),
        "candidate_text_similarity": {
            "messages_with_3_texts": n_with_text,
            "messages_missing_texts": miss_text,
            "pairwise_jaccard_median": med_j,
            "pairwise_jaccard_p90": q[0.9],
            "pairwise_jaccard_min": min(pair_jacs) if pair_jacs else None,
            "pairwise_jaccard_max": max(pair_jacs) if pair_jacs else None,
            "messages_all_pairs_ge_0_90": triples_all_same,
            "messages_all_pairs_ge_0_90_pct": round(100.0 * triples_all_same / n_with_text, 4) if n_with_text else None,
            "rule": "每条消息取连续 3 条 dialogue LLM_CALL 的 cache_key，从侧车 responses/*.json 取 text，"
                    "算两两 char-bigram Jaccard（normalize_body 同口径）",
        },
        "scores_range": {
            "n_msgs_with_scores": n_msg,
            "range_median": med_r,
            "range_p90": rq[0.9],
            "range_max": max(ranges) if ranges else None,
            "range_zero_pct": round(100.0 * all_same / n_msg, 4) if n_msg else None,
            "rule": "range = max(scores) - min(scores)",
        },
        "picked_vs_argmin": "见 d12f_gates_*.json 的 M3_argmin（本脚本不重算）",
        "verdict_locked_rule": ("判读规则先于读数写死：候选 jaccard 中位数≥0.60 且 scores 极差中位数=0 ⇒ A（机制无效）；"
                                "jaccard<0.60 但极差中位数=0 ⇒ B（评分器问题）；其余 ⇒ C（部分可分）"),
        "verdict": verdict,
        "samples": per_msg[:15],
    }
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({k: out[k] for k in ("snapshot_at", "candidate_text_similarity",
                                          "scores_range", "verdict")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
