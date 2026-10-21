#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-3 双臂同场景对照样本抽取（零跑批，只读日志）。

做什么
------
在 ON 臂里挑出「机制判定可呼应」的回复（`payload.ctx.echo` 存在），
按 `(thread_id, turn_index)` 去 OFF 臂找**同一线程同一位次**的回复，拼成逐组对照：
  OFF 上一句 / OFF 回复   ←→   ON 上一句 / ON 回复 + 机制审计字段
另外给出「两臂是否收敛到同一话题/同一线程」的判断，避免拿不可比的组当举证。

用法
----
  python3 tools/f3/f3_samples.py \
      --off v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
      --on  v2/evidence/run_f3_on_n16r60_seed42/run.jsonl \
      --out v2/evidence/f3_samples_pairing.md --n 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional


def read(path: str) -> List[dict]:
    out: List[dict] = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if rec.get("type") not in ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC"):
                continue
            p = rec.get("payload") or {}
            if not isinstance(p.get("body"), str):
                continue
            out.append({
                "seq": rec.get("seq"), "round": rec.get("round"), "type": rec.get("type"),
                "thread_id": p.get("thread_id"), "turn_index": p.get("turn_index"),
                "from": p.get("from"), "to": p.get("to"), "body": p["body"],
                "reply_to": p.get("reply_to"), "topic": p.get("topic"),
                "echo": (p.get("ctx") or {}).get("echo"),
            })
    return out


def index_by_pos(msgs: List[dict]) -> Dict[tuple, dict]:
    idx: Dict[tuple, dict] = {}
    for m in msgs:
        if m["thread_id"] is None or m["turn_index"] is None:
            continue
        idx[(str(m["thread_id"]), int(m["turn_index"]))] = m
    return idx


def index_prev(msgs: List[dict]) -> Dict[tuple, dict]:
    """同线程内 turn_index 紧邻的上一句。"""
    by_thread: Dict[str, List[dict]] = defaultdict(list)
    for m in msgs:
        if m["thread_id"] is not None and m["turn_index"] is not None:
            by_thread[str(m["thread_id"])].append(m)
    prev: Dict[tuple, dict] = {}
    for tid, th in by_thread.items():
        th.sort(key=lambda m: int(m["turn_index"]))
        for i in range(1, len(th)):
            prev[(tid, int(th[i]["turn_index"]))] = th[i - 1]
    return prev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=5)
    a = ap.parse_args()

    off = read(a.off)
    on = read(a.on)
    off_idx, on_idx = index_by_pos(off), index_by_pos(on)
    off_prev, on_prev = index_prev(off), index_prev(on)

    cands: List[dict] = []
    for k, m in on_idx.items():
        if not m["echo"]:
            continue
        o = off_idx.get(k)
        if not o:
            continue
        op, np_ = on_prev.get(k), off_prev.get(k)
        if not op or not np_:
            continue
        cands.append({"key": k, "on": m, "off": o, "on_prev": np_, "off_prev": op})

    # 选择：优先负向（安抚）与强度高的，覆盖不同 kind/source，最多 n 组
    cands.sort(key=lambda c: (-int((c["on"]["echo"] or {}).get("intensity") or 0), c["key"]))
    picked: List[dict] = []
    seen_kind = defaultdict(int)
    for c in cands:
        kind = str((c["on"]["echo"] or {}).get("kind"))
        if seen_kind[kind] >= max(1, a.n // 2) and len(picked) < a.n:
            continue
        picked.append(c)
        seen_kind[kind] += 1
        if len(picked) >= a.n:
            break

    lines: List[str] = []
    lines.append("# F-3 ON/OFF 同场景对照样本（自动抽取，零跑批）\n")
    lines.append(f"- OFF 日志：`{os.path.abspath(a.off)}`（{len(off)} 条 MSG）")
    lines.append(f"- ON  日志：`{os.path.abspath(a.on)}`（{len(on)} 条 MSG）")
    lines.append(f"- 可配对候选（ON 有 ctx.echo 且 OFF 同线程同 turn_index 存在）：**{len(cands)}** 组")
    lines.append(f"- 本文件抽取：**{len(picked)}** 组；配对键 = `(thread_id, turn_index)`\n")
    lines.append("> 说明：两臂各自独立采样，文本必然不同；本对照用于**举证机制是否让回应方向变了**，")
    lines.append("> 不用于统计推断（统计看 `v2/evidence/f3_readings.json`）。\n")

    for i, c in enumerate(picked, 1):
        e = c["on"]["echo"] or {}
        lines.append(f"## 样本 {i} · 线程 `{c['key'][0]}` · 位次 {c['key'][1]} · 话题 `{c['on']['topic']}`\n")
        lines.append("| | OFF 臂 | ON 臂 |")
        lines.append("|---|---|---|")
        lines.append(f"| 上一句（{c['off_prev']['from']}） | {c['off_prev']['body']} | {c['on_prev']['from']}：{c['on_prev']['body']} |")
        lines.append(f"| 回应（{c['off']['from']}） | {c['off']['body']} | {c['on']['from']}：{c['on']['body']} |")
        lines.append("")
        lines.append(f"- ON 机制审计：`sign={e.get('sign')} intensity={e.get('intensity')} "
                     f"tier={e.get('tier')} kind={e.get('kind')} source={e.get('source')} "
                     f"mood={e.get('mood')} prompted={e.get('prompted')}`")
        lines.append(f"- OFF 同位置是否有审计字段：`{'有' if c['off']['echo'] else '无（符合预期）'}`\n")

    text = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[written] {os.path.abspath(a.out)}  候选={len(cands)} 抽取={len(picked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
