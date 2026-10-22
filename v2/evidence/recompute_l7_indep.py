#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R16/R17 · L-7 独立复算器（evidence-closer 自写，不复用 l7v2_judge.py / r1_recompute.py）。

目的：绕开任何既有判定脚本，直接从 run.jsonl 自解析 MSG_* 事件、自实现 8-gram 近重复，
产出 raw8（判定口径，仅去空白）与 norm8（辅助口径，tools/d5/dialogue_metrics.normalize_body
等价归一化）两套读数；再重算 S1/S2/S3/S3b 守卫分子，供与旧读数逐项比对。

口径来源（只读引用，不 import）：
  * tools/d5/dialogue_metrics.py:471-490  —— norm8 归一串 + 8-window shingle + 「任一 shingle 与他人重合即算 dup」
  * tools/d5/dialogue_metrics.py:588       —— L-7 = rate(len(dup_msgs), n_msg)
  * v2/evidence/l7v2_judge.py:53-77        —— raw8 = re.sub(r"\\s+","",body) 的 8-window（判定口径）

用法：
    python3 v2/evidence/recompute_l7_indep.py --log <run.jsonl> \
        [--baseline-dup 193 --baseline-n 510 --band -4.31 5.88] [--tag R16]

只读日志，不联网，不调 LLM；两次运行输出逐字节相同（无时间戳）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import defaultdict

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
PUNCT_RE = re.compile(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)\[\]【】]")
AGENT_ID_RE = re.compile(r"P\d{3}")
PAREN_OPEN = ("（", "(")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def raw8(body: str) -> set:
    t = re.sub(r"\s+", "", body or "")
    return {t[i:i + 8] for i in range(max(0, len(t) - 7))}


def norm8(body: str) -> set:
    s = (body or "").strip().lower().replace("（", "(").replace("）", ")")
    t = PUNCT_RE.sub("", s)
    return {t[i:i + 8] for i in range(max(0, len(t) - 7))}


def dup_index(sets) -> set:
    idx = defaultdict(list)
    for i, s in enumerate(sets):
        for g in s:
            idx[g].append(i)
    dup = set()
    for ids in idx.values():
        if len(ids) > 1:
            dup.update(ids)
    return dup


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(100 * max(0.0, c - h), 3), round(100 * min(1.0, c + h), 3)]


def newcombe(k1: int, n1: int, k2: int, n2: int, z: float = 1.96):
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    l1, u1, l2, u2 = l1 / 100, u1 / 100, l2 / 100, u2 / 100
    d = p2 - p1
    lo = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    hi = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return [round(100 * lo, 3), round(100 * hi, 3)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--tag", default="L-7")
    ap.add_argument("--baseline-dup", type=int, default=193)
    ap.add_argument("--baseline-n", type=int, default=510)
    ap.add_argument("--band", type=float, nargs=2, default=[-4.31, 5.88])
    a = ap.parse_args()

    msgs = []
    type_counts = defaultdict(int)
    n_lines = n_bad = 0
    for line in open(a.log, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        n_lines += 1
        try:
            r = json.loads(line)
        except Exception:
            n_bad += 1
            continue
        t = r.get("type")
        type_counts[str(t)] += 1
        if t not in MSG_TYPES:
            continue
        p = r.get("payload") or {}
        ctx = p.get("ctx") or {}
        msgs.append({"type": t, "body": p.get("body") or "", "from": p.get("from"), "ctx": ctx})

    n = len(msgs)
    bodies = [m["body"] for m in msgs]
    d_raw_set = dup_index([raw8(b) for b in bodies])
    d_norm_set = dup_index([norm8(b) for b in bodies])
    d_raw, d_norm = len(d_raw_set), len(d_norm_set)
    r_raw = d_raw / n if n else None
    r_norm = d_norm / n if n else None
    delta = round(100 * (d_raw - a.baseline_dup) / a.baseline_n, 4) if n else None
    lo, hi = a.band
    if delta is None:
        verdict = "UNDECIDABLE"
    elif delta > hi:
        verdict = "OUT_OF_BAND"
    elif delta < lo:
        verdict = "BELOW_BAND"
    elif delta <= 0:
        verdict = "IN_BAND_AND_DIR_NEG"
    else:
        verdict = "IN_BAND"

    ch = {}
    for c in MSG_TYPES:
        ids = [i for i, m in enumerate(msgs) if m["type"] == c]
        ch[c] = {"n": len(ids), "dup_raw8": sum(1 for i in ids if i in d_raw_set),
                 "dup_norm8": sum(1 for i in ids if i in d_norm_set)}

    # 守卫分子（独立重算）
    f6 = sum(1 for m in msgs if m["ctx"].get("memory_refs"))
    l2 = sum(1 for b in bodies if b.lstrip()[:1] in PAREN_OPEN)
    l8 = sum(1 for b in bodies if AGENT_ID_RE.search(b))
    l13 = sum(1 for m in msgs if m["ctx"].get("topic") and str(m["ctx"]["topic"]) in m["body"])
    # shingle 覆盖度旁证：raw8 与 norm8 的 dup 集合差异
    both = len(d_raw_set & d_norm_set)

    print(f"=== 独立复算 {a.tag}（脚本 v2/evidence/recompute_l7_indep.py）")
    print(f"日志: {a.log}")
    print(f"日志 sha256: {sha256_file(a.log)}")
    print(f"解析: 非空行 {n_lines}，JSON 解析失败 {n_bad}，MSG_* 消息数 n_msg = {n}")
    print(f"MSG 类型分布: " + json.dumps({k: v for k, v in sorted(type_counts.items())
                                          if k in MSG_TYPES}, ensure_ascii=False))
    print()
    print(f"[raw8 · 判定口径] dup = {d_raw} / {n} = {r_raw:.6%}"
          if n else "[raw8] n=0")
    print(f"[norm8 · 辅助口径] dup = {d_norm} / {n} = {r_norm:.6%}"
          if n else "[norm8] n=0")
    print(f"[集合交集] raw8∩norm8 dup = {both}（raw8 独有 {len(d_raw_set - d_norm_set)}，"
          f"norm8 独有 {len(d_norm_set - d_raw_set)}）")
    print(f"[OFF 基线 raw8] {a.baseline_dup} / {a.baseline_n} = "
          f"{a.baseline_dup / a.baseline_n:.6%}")
    if n:
        print(f"[M1] Δ(raw8 vs OFF) = {delta:+.4f}pp，噪声带 [{lo:+.2f}, {hi:+.2f}]pp ⇒ {verdict}")
        print(f"[wilson95 raw8] {wilson(d_raw, n)}")
        print(f"[newcombe95 Δpp] {newcombe(a.baseline_dup, a.baseline_n, d_raw, n)}")
    print(f"[逐频道] " + json.dumps(ch, ensure_ascii=False))
    print()
    print(f"[守卫独立重算] S1 F-6 memory_refs = {f6}/{n}（floor 32 ⇒ "
          f"{'PASS' if f6 >= 32 else 'FAIL'}）")
    print(f"                S2 L-2 旁白头 = {l2}/{n}（==0 ⇒ {'PASS' if l2 == 0 else 'FAIL'}）")
    print(f"                S3 L-8 裸ID = {l8}/{n}（==0 ⇒ {'PASS' if l8 == 0 else 'FAIL'}）")
    print(f"                S3b L-13 token泄漏 = {l13}/{n}（<=9 v1.1 ⇒ "
          f"{'PASS' if l13 <= 9 else 'FAIL'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
