#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.10 离线先验（**不跑批、不调模型**）：公开场合接话会被触发几次？够不够判？

回答预登记的两个"早期止损"问题：
  1. **机会量**：现有批里有多少条 `MSG_PUBLIC` 有"同场旁人"（=机制可触发）；
  2. **预测触发量**：按本臂的确定性规则重放同一批，**预测会真的接上几句**（含配额/窗口/轮数顶）。

规则照抄实现（`agent._pick_reply_target` + `dialogue_threads.is_replyable` + `public_reply`）：
  - 候选 = 可见、同场（`place_ctx == 我的计划地点`）、作者非我、有 `thread_id`；
  - `max_turns=6`（`max_turn+1 < 6`）、`reply_window_rounds=4`（`round - ev.round <= 4`）、
    单回合接话 ≤ `max_turns_per_round=2`、单 slot 发消息 ≤ `max_messages_per_slot=2`、同线程同轮只接一次。

在场集合口径：`ACTIVITY_STARTED` 的 `(agent, slot_id) -> place`（**这是 plan 真值的落账近似**，
比 D2.3 离线工具用的"该 round 发过消息的 (agent,place)"更接近真值；两者差异在读数里分列）。

用法：
    python3 tools/d210/public_reply_preview.py --log <run.jsonl> [--out-json x.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

SLOTS = ["morning", "afternoon", "evening", "night"]
MAX_TURNS = 6
WINDOW = 4
K_PER_ROUND = 2
MAX_MSGS_PER_SLOT = 2


def _slot_id(round_no: int) -> str:
    return f"day{round_no // 12}-{SLOTS[(round_no % 12) // 3]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()

    acts = {}
    pub = []
    msg_by_agent_slot = Counter()
    for line in open(a.log, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        t = e.get("type")
        pl = e.get("payload") or {}
        if t == "ACTIVITY_STARTED" and pl.get("place"):
            acts[(pl.get("agent_id"), pl.get("slot_id"))] = pl["place"]
        elif t in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            who = pl.get("author") or pl.get("from")
            if who:
                msg_by_agent_slot[(who, _slot_id(int(e["round"])))] += 1
            if t == "MSG_PUBLIC":
                pub.append(e)

    # ---- 1) 机会量（用 ACTIVITY_STARTED 的 plan 真值近似）
    opp = 0
    opp_by_place = Counter()
    for e in pub:
        pl = e["payload"]
        A, r = pl["author"], int(e["round"])
        sid = _slot_id(r)
        place = acts.get((A, sid))
        peers = [b for (b, s) in acts if s == sid and acts[(b, s)] == place and b != A] if place else []
        if peers:
            opp += 1
            opp_by_place[place] += 1

    # ---- 2) 预测触发量：按 rounds 顺序重放，确定性
    replied_threads = defaultdict(set)          # thread -> {round}
    replied_msgs = set()
    per_round = defaultdict(int)
    predicted = []
    for e in pub:
        pl = e["payload"]
        A, r = pl["author"], int(e["round"])
        sid = _slot_id(r)
        place = acts.get((A, sid))
        tid = pl.get("thread_id")
        if not place or not tid:
            continue
        cands = [b for (b, s) in acts if s == sid and acts[(b, s)] == place and b != A]
        if not cands:
            continue
        uid = pl.get("msg_uid") or pl.get("msg_id")
        if uid in replied_msgs:
            continue
        # 每个同场旁人各自尝试（取确定性首个仍有余量的：按 agent_id 排序）
        for b in sorted(cands):
            if per_round[r] >= K_PER_ROUND * 8:      # 粗上限：每轮总接话数（16 人 × K/2）
                break
            if msg_by_agent_slot[(b, sid)] >= MAX_MSGS_PER_SLOT:
                continue
            if r in replied_threads[tid]:
                continue
            replied_threads[tid].add(r)
            replied_msgs.add(uid)
            per_round[r] += 1
            msg_by_agent_slot[(b, sid)] += 1
            predicted.append({"round": r, "slot": sid, "place": place,
                              "replier": b, "initiator": A, "thread": tid, "reply_to": uid})
            break

    # ---- 3) F-2_content_drift 基线（质量闸 Q2 的离线依据，口径见 tools/d5/dialogue_metrics.py）
    def _bigrams(t: str) -> set:
        t = "".join(ch for ch in (t or "") if not ch.isspace())
        return {t[i:i + 2] for i in range(len(t) - 1)}

    threads = defaultdict(list)
    for line in open(a.log, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            continue
        pl = e.get("payload") or {}
        if not pl.get("thread_id"):
            continue
        threads[pl["thread_id"]].append((e["round"], pl.get("turn_index") or 0,
                                         e.get("type"), pl.get("body") or ""))

    def _drift(types):
        pairs = drift = 0
        for _k, v in threads.items():
            v.sort()
            if len(v) < 2 or v[0][2] not in types:
                continue
            for i in range(1, len(v)):
                aa, bb = _bigrams(v[i - 1][3]), _bigrams(v[i][3])
                jac = (len(aa & bb) / len(aa | bb)) if (aa | bb) else 0.0
                pairs += 1
                drift += (jac < 0.10)
        return pairs, drift, (round(100.0 * drift / pairs, 2) if pairs else None)

    dm_d = _drift(("MSG_DM",))
    pub_d = _drift(("MSG_PUBLIC",))

    out = {
        "log": a.log,
        "mode": "offline preview (no LLM, no batch)",
        "n_msg_public": len(pub),
        "n_public_reply_to_null": sum(1 for e in pub if e["payload"].get("reply_to") is None),
        "participants_len_hist": dict(Counter(len(e["payload"].get("participants") or []) for e in pub)),
        "opportunity_n": opp,
        "opportunity_rate_pct": round(100.0 * opp / len(pub), 2) if pub else None,
        "opportunity_by_place": dict(opp_by_place),
        "predicted_replies_n": len(predicted),
        "predicted_reply_rate_pct": round(100.0 * len(predicted) / len(pub), 2) if pub else None,
        "predicted_by_round": dict(sorted(per_round.items())),
        "predicted_sample": predicted[:5],
        "f2_content_drift_dm_adjacent_pairs": dm_d[0],
        "f2_content_drift_dm_rate_pct": dm_d[2],
        "f2_content_drift_public_adjacent_pairs": pub_d[0],
        "f2_content_drift_public_rate_pct": pub_d[2],
        "caveat": ("在场集合用 ACTIVITY_STARTED 的 (agent,slot)->place 近似（plan 真值的落账）；"
                   "预测不含 LLM 是否愿意说、也不含 D2.8 措辞线交互；仅作「够不够判」的先验。"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.out_json:
        json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
