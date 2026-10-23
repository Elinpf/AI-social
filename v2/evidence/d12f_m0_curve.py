#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-F M0（真调用率）随轮次的曲线；每 10 轮一档，按 purpose 分项。

回答的问题：**overall 新调用率下滑，是 dialogue 层在涨，还是非对话层在涨？**

口径（与 D12-F 锁定口径一致）：
- overall 新调用率 = `cached==false` 的 LLM_CALL / 全部 LLM_CALL（**判定只用这一版**）
- purpose 分层**只披露**，不作判据
- 分档：round 0-9 / 10-19 / ... / 50-59（按 LLM_CALL 事件的 round 字段）

用法：
    python3 v2/evidence/d12f_m0_curve.py \
        --run-jsonl <run.jsonl> --out-json v2/evidence/d12f_m0_curve.json [--partial]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict

PURPOSES = ("dialogue", "importance", "judge", "plan", "reflect", "negotiation")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def pct(k, n):
    return None if not n else round(100.0 * k / n, 4)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-jsonl", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--partial", action="store_true")
    ap.add_argument("--snapshot-at", default=None)
    ap.add_argument("--bucket", type=int, default=10)
    a = ap.parse_args(argv)

    # bucket -> purpose -> [calls, cached]
    acc = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    rounds_seen = set()
    seals = 0
    bad = 0
    total_lines = 0

    with open(a.run_jsonl, encoding="utf-8") as f:
        for line in f:
            total_lines += 1
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except Exception:
                bad += 1
                continue
            if e.get("type") == "TURN_SEAL":
                seals += 1
                continue
            if e.get("type") != "LLM_CALL":
                continue
            r = e.get("round")
            if r is None:
                continue
            rounds_seen.add(r)
            b = (r // a.bucket) * a.bucket
            pl = e.get("payload") or {}
            p = pl.get("purpose") or "unknown"
            cell = acc[b][p]
            cell[0] += 1
            if pl.get("cached"):
                cell[1] += 1

    buckets = []
    for b in sorted(acc):
        per = {}
        tot = cac = 0
        for p, (calls, cached) in sorted(acc[b].items()):
            per[p] = {"calls": calls, "cached": cached, "cached_false": calls - cached,
                      "cached_rate_pct": pct(cached, calls),
                      "uncached_rate_pct": pct(calls - cached, calls)}
            tot += calls
            cac += cached
        buckets.append({
            "round_range": f"{b}-{b + a.bucket - 1}",
            "by_purpose": per,
            "overall": {"calls": tot, "cached": cac, "cached_false": tot - cac,
                        "cached_rate_pct": pct(cac, tot), "uncached_rate_pct": pct(tot - cac, tot)},
        })

    # 全批汇总
    grand = {}
    gt = gc = 0
    for b in acc:
        for p, (calls, cached) in acc[b].items():
            g = grand.setdefault(p, [0, 0])
            g[0] += calls
            g[1] += cached
            gt += calls
            gc += cached
    summary = {p: {"calls": v[0], "cached": v[1], "cached_false": v[0] - v[1],
                   "cached_rate_pct": pct(v[1], v[0]), "uncached_rate_pct": pct(v[0] - v[1], v[0])}
               for p, v in sorted(grand.items())}

    d = summary.get("dialogue", {})
    n = summary.get("importance", {})
    out = {
        "reader": "v2/evidence/d12f_m0_curve.py",
        "reader_sha256": sha256_file(__file__),
        "source_run_jsonl": a.run_jsonl,
        "source_run_jsonl_sha256": sha256_file(a.run_jsonl),
        "partial": bool(a.partial),
        "snapshot": {"snapshot_at": a.snapshot_at, "turn_seals": seals, "rounds_seen": len(rounds_seen),
                     "max_round_seen": max(rounds_seen) if rounds_seen else None,
                     "lines_total": total_lines, "lines_unparsable_or_partial": bad},
        "bucket_size_rounds": a.bucket,
        "locked_ruling": ("判定只用 overall（cached 全算命中，不分层）；purpose 分层只披露。"
                          "预登记四情形（写于 seals 34/60、未见终态）："
                          "overall>=50 且 dialogue>=50 ⇒ 通过；overall>=50 且 dialogue<50 ⇒ 通过但须披露对话层缓存；"
                          "overall<50 且 dialogue>=50 ⇒ 判「口径分歧」，效果可计算但须写"
                          "「在对话采样全新鲜前提下可判；overall 未过闸已披露」，禁止写「真 LLM 已验证」或「批次无效」；"
                          "overall<50 且 dialogue<50 ⇒ 批次无效，五条效果判据不参与。"),
        "overall_uncached_rate_pct": pct(gt - gc, gt),
        "dialogue_uncached_rate_pct": d.get("uncached_rate_pct"),
        "importance_cached_rate_pct": n.get("cached_rate_pct"),
        "by_purpose_summary": summary,
        "buckets": buckets,
    }
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")

    print(json.dumps({"snapshot": out["snapshot"],
                      "overall_uncached_rate_pct": out["overall_uncached_rate_pct"],
                      "dialogue_uncached_rate_pct": out["dialogue_uncached_rate_pct"],
                      "by_purpose_summary": summary}, ensure_ascii=False, indent=1))
    print("buckets (overall_uncached / dialogue_uncached):")
    for b in buckets:
        dp = b["by_purpose"].get("dialogue", {})
        print(f"  r{b['round_range']:<7} overall={b['overall']['uncached_rate_pct']}% "
              f"dialogue={dp.get('uncached_rate_pct')}% importance_cached={b['by_purpose'].get('importance', {}).get('cached_rate_pct')}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
