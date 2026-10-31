#!/usr/bin/env python3
# derive_gap_d47.py — D47 批「接话/往返 gap」衍生算术（**非仓内固化尺子**，仅本轮取证用）
#
# 为什么单独写：仓内 tools/public_talk/public_talk_metrics.py（ruler-f2/1）只判
# 「PUB 的 reply_to 是否命中一条真实消息（msg_uid）」= 接话条数，**不产出 gap**
# （impl-note §6.5 明确写：gap=0/同轮往返是另一把尺子，不可与接话条数混引）。
# 本脚本只做一件可逐行复核的事：对每条 reply_to 非空的 MSG_PUBLIC，
#   gap = round(本条) − round(reply_to 指向的那条消息)
# 输出：gap 分布、接话条数、以及「同轮(gap=0)」与「跨轮(gap≥1)」的分解。
# 口径纪律：单批、单 seed、无对照 ⇒ 只作描述性读数，不作判据、不写「变好/变差」。
#
# 用法：python3 v2/evidence/d47-ruler-f2-20261101_n16r24_s42/derive_gap_d47.py <run.jsonl>
import json
import sys
from collections import Counter

path = sys.argv[1]
msgs = {}          # msg_uid -> {round, type, thread_id}
pubs = []          # 全部 MSG_PUBLIC 事件 payload
for raw in open(path, encoding="utf-8"):
    raw = raw.strip()
    if not raw:
        continue
    ev = json.loads(raw)
    t = ev.get("type")
    if t not in ("MSG_PUBLIC", "MSG_DM", "MSG_GROUP"):
        continue
    p = ev.get("payload") or {}
    uid = p.get("msg_uid")
    rnd = ev.get("round", p.get("round"))
    if uid is not None:
        msgs[uid] = {"round": rnd, "type": t, "thread_id": p.get("thread_id")}
    if t == "MSG_PUBLIC":
        pubs.append((rnd, p))

# 注意：payload 里的 round 若缺失，回落到事件级 round 字段（两者都缺失则记为 None 并单列）
missing_round = sum(1 for r, _ in pubs if r is None)

nonnull = [(r, p) for r, p in pubs if p.get("reply_to")]
gaps = []
detail = []
for r_rnd, p in nonnull:
    tgt = msgs.get(p["reply_to"])
    if tgt is None:
        gaps.append("dangling")
        detail.append({"self_uid": p.get("msg_uid"), "reply_to": p["reply_to"], "gap": "dangling"})
        continue
    g = (r_rnd - tgt["round"]) if (r_rnd is not None and tgt["round"] is not None) else "unknown"
    gaps.append(g)
    detail.append({
        "self_uid": p.get("msg_uid"), "self_round": r_rnd,
        "reply_to": p["reply_to"], "target_round": tgt["round"], "target_type": tgt["type"],
        "same_thread": p.get("thread_id") == tgt["thread_id"], "gap": g,
    })

cnt = Counter(gaps)
out = {
    "ruler": "d47/derive_gap/1（非仓内固化尺子，仅描述性）",
    "input": path,
    "pub_total": len(pubs),
    "pub_missing_round": missing_round,
    "pub_reply_to_nonnull": len(nonnull),
    "gap_distribution": {str(k): v for k, v in sorted(cnt.items(), key=lambda kv: str(kv[0]))},
    "same_round_gap0": cnt.get(0, 0),
    "cross_round_gap_ge1": sum(v for k, v in cnt.items() if isinstance(k, int) and k >= 1),
    "dangling": cnt.get("dangling", 0),
    "detail": detail,
    "dm_messages_total": sum(1 for uid, m in msgs.items() if m["type"] == "MSG_DM"),
    "dm_reply_to_nonnull_reference_from_metrics": "见 readings_d47_newruler.json: msg_graph_degree.dm_reply_to_nonnull = 117",
    "not_a_judgment": True,
    "note": "gap = 本条 round − reply_to 目标消息 round；单批单 seed 无对照，只作描述性读数",
}
print(json.dumps(out, ensure_ascii=False, indent=1))
