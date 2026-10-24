#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.3 离线映射自检（T1）：**C 档（α=0）与 B 档（α=3）在同一 seed 下选中不同对端的比例**。

为什么需要它：本臂实现把"对端抽取"从 `%len` 改成**累积权重轴**，这引入一个**映射伪影**；
故预登记 §3 要求用同一映射下 α=0（C 档）与 α=3（B 档）同池对比，隔离出**纯权重效应**。
本脚本在**已落盘的 OFF 日志**上重放，不跑批、不调 LLM。

seed 口径（与实现一致）：`f"{A}|{slot_id}|{tid}|p{i}"`，`slot_id = f"day{round//12}-{SLOTS[(round%12)//3]}"`（i=0）。

`place_peer_counts` 口径（与 `agent._place_peer_counts` 一致）：A 自己发的 / 别人发给 A 的、`place` 非空的
消息里，除 A 外的每个参与者 +1，按 place 归集；**只用在第 r 轮之前（严格 < r）**的历史 ⇒ 与"计划期可得"同步。

用法：
    python3 tools/d23/t1_mapping_check.py --log <OFF run.jsonl> [--out-json x.json]
退出码：0；2 日志不足。
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from life.planner import _pick, _weighted_pick, place_affinity_weight  # noqa: E402

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
SLOTS = ["morning", "afternoon", "evening", "night"]


def load(log):
    rows = []
    for line in open(log, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        if e.get("type") not in MSG_TYPES or e.get("round") is None:
            continue
        pl = e.get("payload") or {}
        frm = pl.get("from") or pl.get("author")
        if not frm:
            continue
        parts = set(pl.get("participants") or [])
        parts.add(frm)
        if pl.get("to"):
            parts.add(pl["to"])
        rows.append({"r": e["round"], "frm": frm, "to": pl.get("to"), "place": pl.get("place"),
                     "topic": pl.get("topic"), "turn": pl.get("turn_index"), "parts": parts})
    rows.sort(key=lambda x: (x["r"], str(x["topic"])))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--alpha", type=float, default=3.0)
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args(argv)

    rows = load(a.log)
    if not rows:
        print("[CANNOT-VERIFY] 日志里没有可用 MSG", file=sys.stderr)
        return 2
    agents = sorted({x["frm"] for x in rows} | {p for x in rows for p in x["parts"]})

    buckets = collections.defaultdict(collections.Counter)          # (agent, place) -> Counter(peer)
    history_by_round = []                                           # 逐轮快照不可行的替代：
    n_init = 0                                                      # 这里按增量构建 + 查询"严格 < r"
    same_A = same_C = 0
    changed = 0
    by_place = collections.Counter()
    pend = sorted(rows, key=lambda x: x["r"])
    ptr = 0
    snap = {}                                                       # r -> deep-ish snapshot of buckets

    def _snapshot():
        return {k: dict(v) for k, v in buckets.items()}

    cur_r = None
    for x in pend:
        if x["r"] != cur_r:
            # 归档上一轮的"之前"快照，然后并入上一轮消息（供后续轮使用）
            cur_r = x["r"]
        if x["turn"] != 0 or not x["to"]:
            pass
        else:
            A, tid, r, place = x["frm"], x["topic"], x["r"], x["place"]
            snap.setdefault(r, _snapshot())                         # 该轮开始时（尚未计入本轮消息）的历史
            peers = [p for p in agents if p != A]
            if peers:
                dow, si = r // 12, (r % 12) // 3
                seed = f"{A}|day{dow}-{SLOTS[si]}|{tid}|p0"
                pA = _pick(seed, peers)
                pC = _weighted_pick(seed, peers, [place_affinity_weight(0, 0)] * len(peers))
                counts = (snap[r].get((A, place)) or {}) if place else {}
                pB = _weighted_pick(seed, peers,
                                    [place_affinity_weight(counts.get(p, 0), a.alpha) for p in peers])
                n_init += 1
                same_A += (pA == x["to"])
                same_C += (pC == x["to"])
                changed += (pB != pC)
                by_place[place] += 1
        # 计入本轮消息到历史（供 r' > r 使用）
        A = x["frm"]
        if x["place"]:
            for p in x["parts"]:
                if p and p != A:
                    buckets[(A, x["place"])][p] += 1
                    buckets[(p, x["place"])][A] += 1               # 双向：对方也"在那见过 A"

    out = {
        "log": a.log, "alpha": a.alpha, "n_init": n_init, "n_agents": len(agents),
        "self_check_A_matches_actual_rate_pct": round(100.0 * same_A / n_init, 2) if n_init else None,
        "self_check_C_matches_actual_rate_pct": round(100.0 * same_C / n_init, 2) if n_init else None,
        "change_rate_B_vs_C_pct": round(100.0 * changed / n_init, 2) if n_init else None,
        "offline_expectation_pct": 80.70,
        "tolerance_pp": 10.0,
        "place_distribution_of_inits": dict(by_place),
        "note": ("B 用 place_peer_counts（严格 < r 的双向历史，与 agent._place_peer_counts 同口径）；"
                 "C 用 α=0（w≡1）⇒ 同池同映射，只差权重。"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.out_json:
        Path(a.out_json).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[t1] n_init={n_init}  A 复现={out['self_check_A_matches_actual_rate_pct']}%  "
          f"**change_rate_B_vs_C={out['change_rate_B_vs_C_pct']}%**（离线预期 80.70% ±10pp）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
