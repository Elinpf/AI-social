#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9z「同轮往返可见」读数复算器（只读、零依赖、零 LLM、零跑批）。

用途：让第三方**照抄一条命令**即可复算 D9z 判定件（`v2/evidence/d9z-judgement-20261101.md`）
与事实链（`v2/evidence/d9z-fact-chain-one-pager-by-verifier.md`）里的全部核心数字，
不依赖任何私有中间件、不 import 仓库模块。

口径（与判定件/事实链一致，改动即作废读数，必须在报告里标版本）：
  * 样本 = `run.jsonl` 里 `type ∈ {MSG_DM, MSG_PUBLIC, MSG_GROUP}` 的事件，按 `payload.msg_uid` 去重
    （同一 `msg_uid` 会重复出现：每条消息既作为独立事件、又作为别人可见事件被再记录一次）。
  * 相邻对（adjacent pair）= 带 `payload.reply_to` 且父条 `msg_uid` 能在本次样本里找到的消息。
  * `gap` = `round(子) - round(父)`（**轮次距离**，不是"是否下一句"；线程内 `gap=2` 仍是紧邻两轮）。
  * `gap=0` ⇒ 同轮往返（父条与本条在同一 round 内，机制 ON 才可能出现）。
  * 配额口径 `max_messages_per_slot = 2`（`code/config` 既有值）：`prior(agent, day, slot, seq)`
    = 该 agent 在同一 `(day, slot)` 里**seq 严格小于**给定 seq 的已发消息数。
    **必须用 `seq <`，不能用 `round <=`**（后者会把父条之后发的也算进来，污染 `gap=0` 组）。
    **配额主体是「回复方」= 子消息的 `actor`**（不是父消息作者、也不是父消息收件人），
    `(day, slot)` 取**父消息**的（父条到达那一刻的时段），参照点 `seq` 取父消息的 `seq`。
  * 收件人一律用 `thread_id` 解析（`TH-Pxxx-Pyyy-<day>` 取非发送者），**不用 `participants[0]`**
    （`participants` 有 70 条是一对多，长度 8）。

输出：固定顺序的 KEY=VALUE 行（无时间戳、无绝对路径、无随机）⇒ 同一输入两次运行逐字节一致。

用法：
    python3 tools/metrics/d9z_gap_recompute.py --log v2/evidence/d9z-on_n16r56_s42/run.jsonl
    python3 tools/metrics/d9z_gap_recompute.py --log <off>/run.jsonl --label OFF
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys

MSG_TYPES = {"MSG_DM", "MSG_PUBLIC", "MSG_GROUP"}
MAX_MESSAGES_PER_SLOT = 2     # code/config 既有值；改这里 = 改口径


def load(path):
    """返回 (去重后的消息列表按 seq 升序, LLM_CALL 计数, degraded 计数, 事件总数)。"""
    by_uid: dict[str, dict] = {}
    llm_calls = 0
    degraded = 0
    total = 0
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        total += 1
        e = json.loads(line)
        t = e.get("type")
        if t == "LLM_CALL":
            llm_calls += 1
            if (e.get("payload") or {}).get("degraded"):
                degraded += 1
            continue
        if t not in MSG_TYPES:
            continue
        p = e.get("payload") or {}
        uid = p.get("msg_uid")
        if uid is None or uid in by_uid:
            continue
        by_uid[uid] = {
            "uid": uid,
            "type": t,
            "round": int(e.get("round", 0)),
            "seq": int(e.get("seq", 0)),
            "actor": e.get("actor") or p.get("from") or p.get("author"),
            "place": p.get("place"),
            "reply_to": p.get("reply_to"),
            "thread_id": p.get("thread_id"),
            "day": p.get("day"),
            "slot": p.get("slot"),
        }
    msgs = sorted(by_uid.values(), key=lambda m: m["seq"])
    return msgs, llm_calls, degraded, total


def recipient_of(m: dict) -> str | None:
    """用 thread_id 解析收件人（TH-Pxxx-Pyyy-<day> 取非发送者）；解析不出返回 None。"""
    tid = str(m.get("thread_id") or "")
    if not tid.startswith("TH-"):
        return None
    parts = tid.split("-")
    if len(parts) < 4:
        return None
    ids = [x for x in parts[1:] if x.startswith("P") and x[1:].isdigit()]
    others = [x for x in ids if x != m["actor"]]
    return others[0] if len(others) == 1 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="run.jsonl 路径")
    ap.add_argument("--label", default="", help="标签（仅用于打印，不参与计算）")
    args = ap.parse_args()

    msgs, llm_calls, degraded, total = load(args.log)
    digest = hashlib.sha256(open(args.log, "rb").read()).hexdigest()

    uid2msg = {m["uid"]: m for m in msgs}
    by_type = collections.Counter(m["type"] for m in msgs)

    # ---- 相邻对 ------------------------------------------------------------
    pairs = []                      # (child, parent)
    for m in msgs:
        r = m["reply_to"]
        if r and r in uid2msg and uid2msg[r]["uid"] != m["uid"]:
            pairs.append((m, uid2msg[r]))

    gap_dist = collections.Counter(c["round"] - p["round"] for c, p in pairs)

    # ---- gap=0 的同地/异地拆分 --------------------------------------------
    g0 = [(c, p) for c, p in pairs if c["round"] == p["round"]]
    g0_same_place = sum(1 for c, p in g0 if c["place"] is not None and c["place"] == p["place"])
    g0_cross_place = sum(1 for c, p in g0 if c["place"] is not None and c["place"] != p["place"])
    g0_place_none = len(g0) - g0_same_place - g0_cross_place

    # ---- 配额：prior 用 seq 严格小于父条 seq ---------------------------------
    sent = collections.defaultdict(list)      # (actor, day, slot) -> [seq, ...]
    for m in msgs:
        sent[(m["actor"], m["day"], m["slot"])].append(m["seq"])

    def prior_full(agent, day, slot, ref_seq: int) -> bool:
        n = sum(1 for s in sent.get((agent, day, slot), ()) if s < ref_seq)
        return n >= MAX_MESSAGES_PER_SLOT

    quota_by_gap = collections.defaultdict(lambda: [0, 0])   # gap -> [full, n]
    prior_dist_by_gap = collections.defaultdict(collections.Counter)
    for c, p in pairs:
        g = c["round"] - p["round"]
        replier = c["actor"]          # 配额主体 = 回复方（子消息作者）
        if not replier:
            continue
        n_prior = sum(1 for s in sent.get((replier, p["day"], p["slot"]), ()) if s < p["seq"])
        prior_dist_by_gap[g][n_prior] += 1
        quota_by_gap[g][1] += 1
        if n_prior >= MAX_MESSAGES_PER_SLOT:
            quota_by_gap[g][0] += 1

    # gap=0 / gap>=2 的同地点 / 跨地点配额满率（地点对照组）
    place_quota = collections.defaultdict(lambda: [0, 0])   # "gapN_same|cross" -> [full, n]
    for c, p in pairs:
        g = c["round"] - p["round"]
        if g not in (0, 2):
            continue
        replier = c["actor"]
        if not replier or c["place"] is None or p["place"] is None:
            continue
        n_prior = sum(1 for s in sent.get((replier, p["day"], p["slot"]), ()) if s < p["seq"])
        key = f"gap{g}_" + ("same" if c["place"] == p["place"] else "cross")
        place_quota[key][1] += 1
        if n_prior >= MAX_MESSAGES_PER_SLOT:
            place_quota[key][0] += 1

    # ---- DM 机会分母：被回复 / 沉没，按收件方当轮配额是否已满 --------------
    replied_uids = {c["reply_to"] for c, _ in pairs}
    opportunity = {"full": [0, 0], "not_full": [0, 0]}   # side -> [replied, total]
    for m in msgs:
        if m["type"] != "MSG_DM":
            continue
        rcpt = recipient_of(m)
        if rcpt is None:
            continue
        nxt_seq = min((x["seq"] for x in msgs if x["seq"] > m["seq"]),
                      default=None)
        # 用「父条发出时刻之后最近一条事件的 seq」作参照不好，这里按父条自身 seq 之后的
        # 第一条任意事件的 seq 记；口径与事实链 §4 一致（配额在父条发出前是否已满）
        ref = m["seq"] + 1 if nxt_seq is None else nxt_seq
        full = prior_full(rcpt, m["day"], m["slot"], ref)
        k = "full" if full else "not_full"
        opportunity[k][1] += 1
        if m["uid"] in replied_uids:
            opportunity[k][0] += 1

    # ---- 输出（顺序固定） ---------------------------------------------------
    out = []
    out.append(f"label={args.label}")
    out.append(f"run_jsonl_sha256={digest}")
    out.append(f"events_total={total}")
    out.append(f"msgs_deduped={len(msgs)}")
    out.append(f"msg_dm={by_type.get('MSG_DM', 0)}")
    out.append(f"msg_public={by_type.get('MSG_PUBLIC', 0)}")
    out.append(f"msg_group={by_type.get('MSG_GROUP', 0)}")
    out.append(f"adjacent_pairs={len(pairs)}")
    keys = sorted(gap_dist)
    out.append("gap_dist={" + ", ".join(f"{k}:{gap_dist[k]}" for k in keys) + "}")
    out.append(f"gap0={gap_dist.get(0, 0)}")
    out.append(f"gap_ge2={sum(v for k, v in gap_dist.items() if k >= 2)}")
    n = len(pairs)
    out.append(f"gap_ge2_rate={sum(v for k, v in gap_dist.items() if k >= 2) / n:.4f}" if n else
               "gap_ge2_rate=NA")
    out.append(f"gap0_same_place={g0_same_place}")
    out.append(f"gap0_cross_place={g0_cross_place}")
    out.append(f"gap0_place_none={g0_place_none}")
    out.append(f"gap0_cross_place_rate={g0_cross_place / len(g0):.4f}" if g0 else
               "gap0_cross_place_rate=NA")
    for g in sorted(quota_by_gap):
        full, tot = quota_by_gap[g]
        pc = prior_dist_by_gap[g]
        out.append("prior_dist_gap%d={%s}" % (g, ", ".join(f"{k}:{pc[k]}" for k in sorted(pc))))
        out.append(f"quota_full_gap{g}={full}/{tot}")
    for k in sorted(place_quota):
        full, tot = place_quota[k]
        out.append(f"quota_full_{k}={full}/{tot}")
    for side in ("full", "not_full"):
        rep, tot = opportunity[side]
        rate = f"{rep / tot:.4f}" if tot else "NA"
        out.append(f"dm_opportunity_{side}={rep}/{tot} reply_rate={rate}")
    out.append(f"llm_calls={llm_calls}")
    out.append(f"llm_degraded={degraded}")

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
