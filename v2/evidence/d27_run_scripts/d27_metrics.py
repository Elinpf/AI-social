#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""d27_metrics.py —— D2.7 专用读数器（**只读 run.jsonl，不联网、不调 LLM**）

补 `v2/evidence/d12c_metrics.py`（冻结读数器）没覆盖的 M1 第二条件与旁白形态：
  · M1-a paren_rate：正文以 `（` / `(` 起头的消息占比（与 d12c_metrics 同口径，见其 :52）
  · M1-b 短旁白占比：**在带前导旁白的消息里**，`len(body) <= 80` 的占比（预登记 §4 要求 ≥ 80%）
  · 形态观察：前导旁白字数分布、旁白内含「心理/心想/心里/想着」等词的比例（判「旁白变心理独白」）
  · 台词本体长度：去掉括号后的 `len(body)` 分位（与 d12c_metrics 的 len_p50 同口径，用于 T 闸交叉核对）
  · 结构：n_msgs / n_threads / MSG_TYPE 计数

用法：
  python3 v2/evidence/d27_run_scripts/d27_metrics.py \
      --run C=<某 run.jsonl> --run B=<某 run.jsonl> --out-json <路径>
两次运行对同一输入**逐字节相同**（纯函数、无随机、无时间戳）。
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
from collections import Counter

MSG = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
PAREN = re.compile(r"[（(][^）)]{0,200}[）)]")
LEAD = re.compile(r"^\s*[（(]")
MENTAL = ("心想", "心里", "想道", "暗想", "觉得", "寻思", "念头", "心中")


def _pct(x: int, n: int):
    return round(100.0 * x / n, 2) if n else None


def metrics(path: str) -> dict:
    rows = []
    for line in open(path, encoding="utf-8"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG:
            continue
        rows.append(e)
    n = len(rows)
    types = Counter(e.get("type") for e in rows)
    lead = 0
    lead_body_le80 = 0
    paren_lens = []
    mental = 0
    lens_x = []
    threads = Counter()
    for e in rows:
        pl = e.get("payload") or {}
        b = pl.get("body") or ""
        body_lead = bool(LEAD.match(b))
        if body_lead:
            lead += 1
            if len(b) <= 80:
                lead_body_le80 += 1
            m = PAREN.match(b)
            if m:
                inner = m.group(0).strip("（）()").strip()
                paren_lens.append(len(inner))
                if any(w in inner for w in MENTAL):
                    mental += 1
        lens_x.append(len(PAREN.sub("", b).strip()))
        threads[pl.get("thread_id") or f"legacy-{pl.get('msg_uid')}"] += 1
    lens_x.sort()
    return {
        "n_msgs": n,
        "msg_types": dict(sorted(types.items())),
        "n_threads": len(threads),
        "threads_p50": st.median(sorted(threads.values())) if threads else None,
        "M1a_paren_lead_rate": _pct(lead, n),
        "M1a_paren_lead_count": lead,
        "M1b_short_paren_share_pct": _pct(lead_body_le80, lead),
        "M1b_denominator": lead,
        "paren_inner_len_p50": st.median(paren_lens) if paren_lens else None,
        "paren_inner_len_max": max(paren_lens) if paren_lens else None,
        "paren_mental_share_pct": _pct(mental, len(paren_lens)),
        "len_p50_excl_paren": st.median(lens_x) if lens_x else None,
        "len_all_p50": st.median(sorted(len((e.get("payload") or {}).get("body") or "")
                                        for e in rows)) if rows else None,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="arm=path，可多次")
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args(argv)
    out = {}
    for spec in a.run:
        arm, _, path = spec.partition("=")
        if not arm or not path:
            raise SystemExit(f"--run 需 arm=path 形式：{spec!r}")
        out[arm] = metrics(path)
    js = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    with open(a.out_json, "w", encoding="utf-8") as fh:
        fh.write(js + "\n")
    print(js)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
