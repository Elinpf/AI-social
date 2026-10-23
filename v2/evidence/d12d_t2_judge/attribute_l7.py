#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-D 判读·L-7 模板化代价归因（**非判据**，只作机制解释）

把 `L-7_dup_ngram8_rate` 的撞车 8-gram 拆成两类：
  A. 句式开头重复（head）：撞车 8-gram 在归一化正文中的起始位置 < HEAD_START（默认 4）
     —— 对应 D12-D 第 2 条指令「开口别用上句/对方句的前四个字」要打击的对象；
  B. 正文/具体物重复（body）：起始位置 >= HEAD_START 的撞车 8-gram
     —— 对应第 1 条指令「换新物」要打击的对象（器物/数词被复用）。
再各叠一层「是否含具体物词（D12-C 冻结词表）」的标注，得到 2×2 四格。

复用 `tools/d5/dialogue_metrics.normalize_body`（冻结实现）与 `tools/d12d/decompose_l7.py`
的 l7 算法（已自检逐位等于 D5 的 L-7），不自创口径、不产生新判据。

用法：
  python3 v2/evidence/d12d_t2_judge/attribute_l7.py \
      --run T1=v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
      --run T2=v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl \
      --out-json v2/evidence/d12d_t2_judge/l7_attribution.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "tools" / "d5"))
sys.path.insert(0, str(_ROOT / "tools" / "d12d"))

from dialogue_metrics import normalize_body  # noqa: E402
from decompose_l7 import read_msgs  # noqa: E402

NGRAM = 8
HEAD_START = 4
# 与 v2/evidence/d12c_metrics.py 的 DETAIL 冻结词表逐条一致（只读复制，不改口径）
DETAIL = [r"[0-9０-９一二三四五六七八九十百千万两]", r"[斤两把钱文斗升只条块张副担捆]",
          r"米|面|柴|油|盐|糖|布|木|铁|药|茶|酒|鸡|鱼|菜|糕|饼|书|笔|伞|鞋|绳|灯|碗|锅"]
DETAIL_RE = re.compile("|".join(DETAIL))


def analyze(path: str):
    msgs = read_msgs(path)
    texts = [normalize_body(m.get("body") or "") for m in msgs]
    n = len(texts)

    # shingle -> 出现在哪些消息（与 D5 / decompose_l7 同算法）
    shingles = [{t[i:i + NGRAM] for i in range(max(0, len(t) - (NGRAM - 1)))} for t in texts]
    index = defaultdict(list)
    for i, sh in enumerate(shingles):
        for g in sh:
            index[g].append(i)
    dup_msgs = set()
    for ids in index.values():
        if len(ids) > 1:
            dup_msgs.update(ids)

    # 对每条「撞车消息」，取它自己的撞车 shingle，按位置/词表归到四格
    cell_msg = defaultdict(set)     # cell -> set(msg idx)
    cell_shingle = defaultdict(set) # cell -> set(shingle)
    for i, sh in enumerate(shingles):
        t = texts[i]
        for g in sh:
            if len(index[g]) < 2:
                continue
            pos = t.find(g)
            is_head = 0 <= pos < HEAD_START
            has_detail = bool(DETAIL_RE.search(g))
            cell = ("A_head_detail" if is_head and has_detail else
                    "B_head_nodetail" if is_head else
                    "C_body_detail" if has_detail else
                    "D_body_nodetail")
            cell_msg[cell].add(i)
            cell_shingle[cell].add(g)
    # 开头层集中度（回答「换开头是不是换成同一个新开头」的待验假设 H1，非判据）
    head_sets = defaultdict(set)
    for i, sh in enumerate(shingles):
        t = texts[i]
        for g in sh:
            if len(index[g]) < 2:
                continue
            pos = t.find(g)
            if 0 <= pos < HEAD_START:
                head_sets[g].add(i)
    ranked = sorted(head_sets.items(), key=lambda kv: -len(kv[1]))
    top5 = set().union(*[v for _, v in ranked[:5]]) if ranked else set()
    PAT_BA = re.compile(r"^把.{1,8}往.{1,6}上一")
    return {
        "n_msgs": n,
        "head_concentration": {
            "distinct_head_shingles": len(head_sets),
            "top1_shingle": ranked[0][0] if ranked else None,
            "top1_msgs": len(ranked[0][1]) if ranked else 0,
            "top5_covers_msgs": len(top5),
            "top5_share_pct": round(100 * len(top5) / n, 4) if n else None,
        },
        "opening_pattern_ba_wang_yi": {
            "rule": "normalize_body 后以「把…往…上一」开头（句式模板代理，非判据）",
            "msgs": sum(1 for t in texts if PAT_BA.search(t)),
            "rate_pct": round(100 * sum(1 for t in texts if PAT_BA.search(t)) / n, 4) if n else None,
        },
        "dup_msgs": len(dup_msgs),
        "L7_norm8_rate_pct": round(100 * len(dup_msgs) / n, 6) if n else None,
        "cells": {c: {"msgs": len(cell_msg[c]),
                      "rate_pct": round(100 * len(cell_msg[c]) / n, 4) if n else None,
                      "distinct_shingles": len(cell_shingle[c])}
                  for c in sorted(set(cell_msg) | {"A_head_detail", "B_head_nodetail",
                                                   "C_body_detail", "D_body_nodetail"})},
        # 消息可同时落多格，故四格 msgs 之和 >= dup_msgs（并列说明，不作加和判据）
        "cells_msgs_sum": sum(len(v) for v in cell_msg.values()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    out = {}
    for spec in a.run:
        arm, _, path = spec.partition("=")
        out[arm] = analyze(path)
        r = out[arm]
        print(f"[{arm}] n={r['n_msgs']} dup={r['dup_msgs']} L7={r['L7_norm8_rate_pct']}% "
              f"sum_cells={r['cells_msgs_sum']}")
        for c, v in r["cells"].items():
            print(f"    {c:18s} msgs={v['msgs']:4d} rate={v['rate_pct']}% shingles={v['distinct_shingles']}")
    Path(a.out_json).write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
