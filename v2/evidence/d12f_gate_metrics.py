#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-F 机制闸读数器（M0 / M1 / M3 / M4 + picked 分布）；只读 run.jsonl，不联网、不调 LLM。

口径（与 D12-E / D12-F 预登记同源）：
- n_msgs         = 全部 MSG_DM / MSG_PUBLIC / MSG_GROUP 事件数
- **M1 接线**    = payload.ctx.d12f.m == 3 的 MSG 数 / n_msgs；预登记要求 = 100%
- **M3 择优正确**= 在「scores 非全同」的样本里，scores[picked] == min(scores) 的比例；要求 = 100%
- **M4 可分性**  = scores 非全同的样本数 / n_msgs；预登记要求 >= 25%（D12-E 实测 16.1%）
- **M0 真调用**  = LLM_CALL 中 cached == False 的条数 / LLM_CALL 总数；门槛 >= 50%（Leader 前置闸：
                  不达标即「效果不可判，先查缓存链路」）
- picked 分布    = Counter(payload.ctx.d12f.picked)

工程约束：
- **逐行解析**，末行不完整（flush-every 2 会留半行）直接跳过并计数，绝不整文件 json.load；
- 支持中途快照：--partial 时输出里写 partial=true / snapshot_at / snapshot_round / seals；
- 输出两次运行逐字节相同（除 snapshot_at 时间戳）。

用法：
    python3 v2/evidence/d12f_gate_metrics.py \
        --run-jsonl .worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42/run.jsonl \
        --label D12F --partial --out-json v2/evidence/d12f_metrics_partial_rNN.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def r4(x):
    return None if x is None else round(x, 4)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-jsonl", required=True)
    ap.add_argument("--label", default="D12F")
    ap.add_argument("--partial", action="store_true")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--sample-scores", type=int, default=8)
    ap.add_argument("--snapshot-at", default=None,
                    help="采集时刻（由 wrapper 用 date -Iseconds 传入；禁止手写）")
    ap.add_argument("--ctx-key", default="d12f", choices=["d12f", "d12e"],
                    help="读哪个 ctx 子键（d12f=本臂；d12e=回归自检用）")
    args = ap.parse_args(argv)

    total_lines = bad_lines = 0
    n_msgs = 0
    m1_hit = 0
    non_uniform = 0
    ctx_msgs = 0          # 带 ctx.<key> 且为 dict 的 MSG
    picked_none = 0       # 其中 picked is None
    non_uniform_excl_none = 0
    argmin_ok = 0
    argmin_viol = []
    picked_cnt = Counter()
    scores_samples = []
    seen_d12e = 0
    rounds = set()
    seals = 0
    last_seq = None
    scores_len_dist = Counter()
    argmin_idx_dist = Counter()      # 非全同样本中「最小值的（并列取最小）索引」分布
    nonuniform_picked0 = 0           # 非全同样本中 picked==0 的条数
    llm_calls = 0
    cached_true = 0
    by_purpose = defaultdict(lambda: {"calls": 0, "cached": 0, "cached_false": 0,
                                      "tokens_in": 0, "tokens_out": 0})
    degraded = 0
    providers = Counter()

    with open(args.run_jsonl, encoding="utf-8") as f:
        for line in f:
            total_lines += 1
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except Exception:
                bad_lines += 1  # 末行半行 / 坏行：跳过，不认数
                continue
            last_seq = e.get("seq", last_seq)
            t = e.get("type")
            if t == "TURN_SEAL":
                seals += 1
                if e.get("round") is not None:
                    rounds.add(e["round"])
                continue
            if t == "LLM_CALL":
                llm_calls += 1
                pl = e.get("payload") or {}
                purpose = pl.get("purpose") or "unknown"
                b = by_purpose[purpose]
                b["calls"] += 1
                if pl.get("cached"):
                    cached_true += 1
                    b["cached"] += 1
                else:
                    b["cached_false"] += 1
                    b["tokens_in"] += int(pl.get("tokens_in") or 0)
                    b["tokens_out"] += int(pl.get("tokens_out") or 0)
                if pl.get("degraded"):
                    degraded += 1
                providers[pl.get("provider") or "none"] += 1
                continue
            if t not in MSG_TYPES:
                continue

            n_msgs += 1
            ctx = (e.get("payload") or {}).get("ctx") or {}
            d = ctx.get(args.ctx_key)
            if isinstance(ctx.get("d12e"), dict):
                seen_d12e += 1
            if not isinstance(d, dict):
                continue
            if d.get("m") == 3:
                m1_hit += 1
            ctx_msgs += 1
            picked = d.get("picked")
            if picked is None:
                picked_none += 1
            scores = d.get("scores") or []
            picked_cnt[str(picked)] += 1
            sset = list(scores)
            scores_len_dist[len(sset)] += 1
            distinct = len(set(sset)) if sset else 0
            if distinct > 1:
                non_uniform += 1
                if picked is not None:
                    non_uniform_excl_none += 1
                if sset:
                    mn = min(sset)
                    argmin_idx_dist[str(sset.index(mn))] += 1
                if picked is not None and int(picked) == 0:
                    nonuniform_picked0 += 1
                if picked is not None and 0 <= int(picked) < len(sset):
                    if sset[int(picked)] == min(sset):
                        argmin_ok += 1
                    else:
                        argmin_viol.append({"seq": e.get("seq"), "picked": picked, "scores": sset})
                else:
                    argmin_viol.append({"seq": e.get("seq"), "picked": picked, "scores": sset,
                                        "reason": "picked out of range / None"})
            if picked is not None and int(picked) != 0 and len(scores_samples) < args.sample_scores:
                scores_samples.append({
                    "seq": e.get("seq"), "round": e.get("round"), "type": t,
                    "from": (e.get("payload") or {}).get("from") or (e.get("payload") or {}).get("author"),
                    "scores": sset, "picked": picked,
                    "body_head": ((e.get("payload") or {}).get("body") or "")[:60],
                })

    pct = lambda k, n: (100.0 * k / n) if n else None
    out = {
        "reader": "v2/evidence/d12f_gate_metrics.py",
        "reader_sha256": sha256_file(__file__),
        "label": args.label,
        "ctx_key": args.ctx_key,
        "source_run_jsonl": args.run_jsonl,
        "source_run_jsonl_sha256": sha256_file(args.run_jsonl),
        "snapshot": {
            "snapshot_at": args.snapshot_at,
            "partial": bool(args.partial),
            "snapshot_rounds_seen": len(rounds),
            "max_round_seen": max(rounds) if rounds else None,
            "turn_seals": seals,
            "last_seq": last_seq,
            "lines_total": total_lines,
            "lines_unparsable_or_partial": bad_lines,
            "note": ("中途快照：partial=true，**不得**当作终态判读结论"
                     if args.partial else "终态读数"),
        },
        "n_msgs": n_msgs,
        "M1_wiring": {
            "msgs_with_ctx_d12f_m3": m1_hit,
            "n_msgs": n_msgs,
            "rate_pct": r4(pct(m1_hit, n_msgs)),
            "threshold_pct": 100.0,
            "msgs_with_ctx_d12e_as_well": seen_d12e,
            "rule": "分子 = payload.ctx.d12f.m == 3 的 MSG；分母 = 全部 MSG_*",
        },
        "M0_uncached": {
            "llm_calls": llm_calls,
            "cached_true": cached_true,
            "cached_false": llm_calls - cached_true,
            "uncached_rate_pct": r4(pct(llm_calls - cached_true, llm_calls)),
            "threshold_pct": 50.0,
            "degraded_calls": degraded,
            "provider_counts": dict(sorted(providers.items())),
            "by_purpose": {k: {"calls": v["calls"], "cached": v["cached"],
                               "cached_false": v["cached_false"],
                               "cached_rate_pct": r4(pct(v["cached"], v["calls"])),
                               "tokens_in_uncached": v["tokens_in"],
                               "tokens_out_uncached": v["tokens_out"]}
                           for k, v in sorted(by_purpose.items())},
            "rule": "分子 = LLM_CALL 中 payload.cached == false；分母 = 全部 LLM_CALL。"
                    "门槛 >=50%（Leader 前置闸）：不达标即「效果不可判，先查缓存链路」",
        },
        "scores_len_dist": {str(k): v for k, v in sorted(scores_len_dist.items())},
        "M3_argmin": {
            "definition_note": ("分母 = **scores 非全同的样本数**（不是 n_msgs）；"
                                "若 picked 全非 None 且 len(scores) 恒为 3，则『非全同』是唯一筛选条件。"
                                "D12-E 实测 den=82、violations=0 —— 与 d12e_result.md 的 82/82 一致"),
            "den_non_uniform": non_uniform,
            "num_argmin_ok": argmin_ok,
            "rate_pct": r4(pct(argmin_ok, non_uniform)),
            "threshold_pct": 100.0,
            "argmin_index_dist": {k: argmin_idx_dist[k] for k in sorted(argmin_idx_dist)},
            "nonuniform_picked0_count": nonuniform_picked0,
            "picked0_interpretation_note": ("若 `nonuniform_picked0_count` 很大且 `argmin_index_dist['0']` 也很大 ⇒ "
                                            "候选 0 在多数非全同样本里本来就是最小分，择优正常；"
                                            "若 `nonuniform_picked0_count` 远大于 `argmin_index_dist['0']` ⇒ 择优偏向索引 0，属实现问题"),
            "violations": argmin_viol[:20],
            "n_violations": len(argmin_viol),
            "rule": "分母 = scores 非全同的 MSG；分子 = scores[picked] == min(scores)",
        },
        "M4_separability": {
            "denominator_A_all_msgs_with_ctx": {
                "num": non_uniform, "den": ctx_msgs, "rate_pct": r4(pct(non_uniform, ctx_msgs)),
                "definition": "分母 = 全部带 ctx.<ctxkey> 的 MSG_*（每一条 MSG 都有一条 ctx）",
            },
            "denominator_B_excluding_picked_none": {
                "num": non_uniform_excl_none, "den": ctx_msgs - picked_none,
                "rate_pct": r4(pct(non_uniform_excl_none, ctx_msgs - picked_none)),
                "definition": "分母 = 带 ctx.<ctxkey> 且 picked is not None 的 MSG",
            },
            "picked_none_count": picked_none,
            "ctx_msgs": ctx_msgs,
            "threshold_pct": 25.0,
            "locked_ruling": ("分母口径在终态读数之前锁定：**两种分母同时报出，任何一版都不得单独使用**；"
                              "两种分母的裁决一致才算 M4 通过/不通过；不一致则 M4 判「口径不明、不可判」，"
                              "并转「有条件通过：需补预登记分母定义」。严禁择分母。"),
            "legacy_flat_fields": {"non_uniform_samples": non_uniform, "n_msgs": n_msgs,
                                   "rate_pct": r4(pct(non_uniform, n_msgs))},
            "rule": "分子 = scores 非全同的 MSG（len(set(scores))>1）",
        },
        "picked_dist": {k: picked_cnt[k] for k in sorted(picked_cnt, key=lambda x: (x == "None", x))},
        "scores_samples_picked_nonzero": scores_samples,
    }
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({k: out[k] for k in ("label", "snapshot", "n_msgs", "M1_wiring",
                                          "M0_uncached", "M3_argmin", "M4_separability",
                                          "picked_dist")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
