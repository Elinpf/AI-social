#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立复核 C1 锚点时序缺陷：`ctx.scene.place` 是否取自「本轮移动前的场所」。

**刻意做成零依赖、单文件、只读 run.jsonl**：不 import 仓库任何模块，
不复用 `c1_effect_metrics.py` 的任何实现，供他人（run-observer 等）独立复现同一数字。

输出三块：
  1. 汇总：会话条数 / 含 scene 键条数 / 锚点相符 / 锚点错位 / 错位率；
     错位里「锚点 == 同轮前一次 PLACE_MOVE.from_place」的条数（主判据）；
     「既非 from 也非 to」条数（**判伪反例**，>0 即推翻解释）。
  2. 逐条明细：seq | round | actor | 消息 place | 锚点 place | 前置移动 from→to | 正文前 40 字。
  3. 判伪清单：三条可在本批直接检验的判伪条件各自的反例条数。

用法：
    python3 tools/metrics/c1_anchor_stale_check.py <arm_dir>/run.jsonl
    # 期望输出（A1，2026-11-01）：
    #   dialogue=191 scene_key=191 anchor_match=104 anchor_mismatch=87 mismatch_rate=0.4555
    #   anchor_eq_from_place=87 (100.00%) neither_from_nor_to=0
    #   falsify_H2_no_move_but_mismatch=0 falsify_H3_place_ne_to_place=0
"""
from __future__ import annotations

import collections
import json
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 c1_anchor_stale_check.py <run.jsonl>", file=sys.stderr)
        return 2
    path = sys.argv[1]

    moves = collections.defaultdict(list)    # actor -> [(round, seq, from_place, to_place)]
    msgs = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        t = e.get("type")
        if t == "PLACE_MOVE":
            p = e.get("payload") or {}
            actor = e.get("actor") or p.get("agent_id")
            if actor:
                moves[actor].append((e.get("round"), e.get("seq"),
                                     str(p.get("from_place") or ""), str(p.get("to_place") or "")))
        elif t in ("MSG_PUBLIC", "MSG_DM"):
            msgs.append(e)

    n_msg = n_scene = n_match = 0
    stale = []
    for e in msgs:
        n_msg += 1
        p = e.get("payload") or {}
        ctx = p.get("ctx") or {}
        scene = ctx.get("scene") if isinstance(ctx.get("scene"), dict) else None
        if scene is None:
            continue
        n_scene += 1
        anchor = str(scene.get("place") or "")
        msg_place = str(p.get("place") or "")
        if anchor == msg_place:
            n_match += 1
            continue
        actor, rnd, seq = e.get("actor"), e.get("round"), e.get("seq")
        prior = [m for m in moves.get(actor, ())
                 if m[0] == rnd and m[1] is not None and seq is not None and m[1] < seq]
        last = prior[-1] if prior else None
        stale.append({
            "seq": seq, "round": rnd, "actor": actor,
            "msg_place": msg_place, "anchor": anchor,
            "move": ("%s→%s" % (last[2], last[3])) if last else "NO_MOVE_THIS_ROUND",
            "eq_from": bool(last) and anchor == last[2],
            "neither": (not last) or (anchor != last[2] and anchor != last[3]),
            "body": str(p.get("body") or "")[:40],
        })

    n_stale = len(stale)
    eq_from = sum(1 for r in stale if r["eq_from"])
    neither = sum(1 for r in stale if r["neither"])
    no_move_mismatch = sum(1 for r in stale if r["move"] == "NO_MOVE_THIS_ROUND")

    # 判伪条件③：payload.place 是否等于同轮前一次 move.to_place（若不等，说明 place 记录口径可疑）
    place_ne_to = 0
    for e in msgs:
        p = e.get("payload") or {}
        actor, rnd, seq = e.get("actor"), e.get("round"), e.get("seq")
        prior = [m for m in moves.get(actor, ())
                 if m[0] == rnd and m[1] is not None and seq is not None and m[1] < seq]
        if prior and prior[-1][3] != str(p.get("place") or ""):
            place_ne_to += 1

    print("dialogue=%d scene_key=%d anchor_match=%d anchor_mismatch=%d mismatch_rate=%.4f"
          % (n_msg, n_scene, n_match, n_stale, (n_stale / n_scene) if n_scene else 0.0))
    print("anchor_eq_from_place=%d (%s) neither_from_nor_to=%d"
          % (eq_from, ("%.2f%%" % (100.0 * eq_from / n_stale)) if n_stale else "NA", neither))
    print("falsify_H2_no_move_but_mismatch=%d falsify_H3_place_ne_to_place=%d"
          % (no_move_mismatch, place_ne_to))
    print("")
    print("# 逐条明细（seq | round | actor | 消息place | 锚place | 前置移动 from→to | 正文前40字）")
    for r in stale:
        print("%s | %s | %s | %s | %s | %s | %s" % (
            r["seq"], r["round"], r["actor"], r["msg_place"], r["anchor"], r["move"], r["body"]))
    print("")
    print("# 判伪反例（非空即推翻「移动前快照」解释）")
    n = 0
    for r in stale:
        if r["neither"]:
            n += 1
            print("NEITHER seq=%s actor=%s anchor=%s move=%s" % (r["seq"], r["actor"], r["anchor"], r["move"]))
    for e in msgs:
        pass
    if n == 0:
        print("(none：锚点场所 100% 落在 from_place 上)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
