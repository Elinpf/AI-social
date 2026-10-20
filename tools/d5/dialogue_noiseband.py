#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D5 噪声带（null pair）对比器。

用途：把两批「提示词实质相同、只差无关树改动」的真 LLM 批的指标读数做差，
得到「什么都不改也会有的波动」——即每个指标的噪声带 band_i = |metric_i(A) - metric_i(B)|。
D4/D6 声称的改善必须落在带外；带内只记「印象」。

同时可选计算**逐条一致率**（证明「同 seed ≠ 同文本」，写进报告局限章节）。

用法:
    python3 artifacts/code/dialogue_noiseband.py \
        --metrics-a /tmp/m_t300.json --metrics-b /tmp/m_t355.json \
        --log-a /root/t271/runs/t300/run.jsonl --log-b /root/t271/runs/t355/run.jsonl \
        --out-json v2/evidence/noiseband_t300_t355.json \
        --out-md   v2/evidence/noiseband_t300_t355.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

SCHEMA = "d5-noiseband/1.0"
SKIP_KEYS = {"n", "n_agents", "n_rounds", "denominator_adjacent_pairs",
             "denominator_nonfirst_msgs", "ptr_ok", "ptr_empty", "ptr_cross_thread",
             "ptr_forward", "L-10_denominator", "calls", "llm_calls", "dialogue_calls",
             "degraded_calls", "n_messages", "n_threads", "denominator"}


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return "sha256:" + h.hexdigest()


def flatten(obj: Any, prefix: str = "") -> Dict[str, float]:
    out: Dict[str, float] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix] = float(obj)
    return out


def r6(x):
    return None if x is None else round(float(x), 6)


def msg_stream(log_path: str) -> List[Tuple[Any, ...]]:
    msgs = []
    with open(log_path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or '"MSG_' not in ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if r.get("type") not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
                continue
            p = r.get("payload") or {}
            msgs.append((r.get("round"), r.get("seq"), p.get("from"), p.get("to"),
                         (p.get("body") or "").strip()))
    msgs.sort(key=lambda m: (m[0] if m[0] is not None else -1,
                             m[1] if m[1] is not None else -1))
    return msgs


def norm(s: str) -> str:
    s = s.strip().lower().replace("（", "(").replace("）", ")")
    return re.sub(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.]", "", s)


def identity(msgs_a, msgs_b) -> Dict[str, Any]:
    n = min(len(msgs_a), len(msgs_b))
    same_body = sum(1 for i in range(n) if norm(msgs_a[i][4]) == norm(msgs_b[i][4]))
    same_route = sum(1 for i in range(n) if (msgs_a[i][2], msgs_a[i][3]) == (msgs_b[i][2], msgs_b[i][3]))
    # 说话人序列一致率（位置对齐）
    same_speaker = sum(1 for i in range(n) if msgs_a[i][2] == msgs_b[i][2])
    return {
        "n_a": len(msgs_a), "n_b": len(msgs_b), "aligned_pairs": n,
        "identical_body": same_body, "identical_body_rate": r6(same_body / n) if n else None,
        "identical_route": same_route, "identical_route_rate": r6(same_route / n) if n else None,
        "identical_speaker": same_speaker,
        "identical_speaker_rate": r6(same_speaker / n) if n else None,
        "alignment": "按 (round, seq) 排序后按位置配对（两批 MSG 条数须一致才可用）",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D5 噪声带对比器")
    ap.add_argument("--metrics-a", required=True)
    ap.add_argument("--metrics-b", required=True)
    ap.add_argument("--label-a", default=None)
    ap.add_argument("--label-b", default=None)
    ap.add_argument("--log-a", default=None)
    ap.add_argument("--log-b", default=None)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args(argv)

    A = json.load(open(args.metrics_a, encoding="utf-8"))
    B = json.load(open(args.metrics_b, encoding="utf-8"))
    fa, fb = flatten(A), flatten(B)
    common = sorted(set(fa) & set(fb))
    rows = []
    for k in common:
        leaf = k.split(".")[-1]
        if leaf in SKIP_KEYS:
            continue
        a, b = fa[k], fb[k]
        band = abs(a - b)
        rows.append({
            "metric": k, "a": r6(a), "b": r6(b),
            "diff_a_minus_b": r6(a - b), "band": r6(band),
            "rel_band": r6(band / (abs(a) + abs(b) + 1e-9)),
        })
    rows.sort(key=lambda r: -(r["rel_band"] or 0))

    res: Dict[str, Any] = {
        "schema_version": SCHEMA,
        "pair": {
            "label_a": args.label_a or args.metrics_a,
            "label_b": args.label_b or args.metrics_b,
            "metrics_a": {"path": os.path.abspath(args.metrics_a), "sha256": sha256_file(args.metrics_a)},
            "metrics_b": {"path": os.path.abspath(args.metrics_b), "sha256": sha256_file(args.metrics_b)},
            "log_a": {"path": args.log_a, "sha256": sha256_file(args.log_a)} if args.log_a else None,
            "log_b": {"path": args.log_b, "sha256": sha256_file(args.log_b)} if args.log_b else None,
            "run_sha_a": A.get("inputs", {}).get("run_sha256"),
            "run_sha_b": B.get("inputs", {}).get("run_sha256"),
        },
        "protocol_note": (
            "null pair：两批提示词实质相同、只差无关树改动。band_i = |metric_i(A)-metric_i(B)| "
            "视为该指标「什么都不改也会有的波动」。D4/D6 的 Δ 必须报 vs_null_band = Δ/band；"
            "|vs_null_band|<=1 只能记印象。band 由单对批估计，样本量小、不可外推到不同规模/不同模型。"
        ),
        "n_metrics": len(rows),
        "metrics": rows,
    }
    if args.log_a and args.log_b:
        res["message_identity"] = identity(msg_stream(args.log_a), msg_stream(args.log_b))

    txt = json.dumps(res, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    lines = [f"# 噪声带（null pair）读数\n",
             f"- A: `{res['pair']['label_a']}` (run sha `{res['pair']['run_sha_a']}`)",
             f"- B: `{res['pair']['label_b']}` (run sha `{res['pair']['run_sha_b']}`)",
             f"- 协议：{res['protocol_note']}\n"]
    if "message_identity" in res:
        mi = res["message_identity"]
        lines += ["## 逐条一致率（证明同 seed≠同文本）\n",
                  "| 项 | 值 |", "|---|---|",
                  f"| MSG 条数 A / B | {mi['n_a']} / {mi['n_b']} |",
                  f"| 逐条正文一致 | {mi['identical_body']}/{mi['aligned_pairs']} = {mi['identical_body_rate']} |",
                  f"| 收发对一致 | {mi['identical_route']}/{mi['aligned_pairs']} = {mi['identical_route_rate']} |",
                  f"| 说话人一致 | {mi['identical_speaker']}/{mi['aligned_pairs']} = {mi['identical_speaker_rate']} |",
                  f"| 对齐方式 | {mi['alignment']} |", ""]
    lines += ["## 各指标噪声带（按相对带宽降序）\n",
              "| 指标 | A | B | Δ(A−B) | band=\\|Δ\\| | rel_band |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| `{r['metric']}` | {r['a']} | {r['b']} | {r['diff_a_minus_b']} | {r['band']} | {r['rel_band']} |")
    md = "\n".join(lines) + "\n"
    if args.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
        open(args.out_json, "w", encoding="utf-8").write(txt + "\n")
    if args.out_md:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
        open(args.out_md, "w", encoding="utf-8").write(md)
    print(json.dumps({"n_metrics": len(rows),
                      "message_identity": res.get("message_identity"),
                      "out_json": args.out_json, "out_md": args.out_md},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
