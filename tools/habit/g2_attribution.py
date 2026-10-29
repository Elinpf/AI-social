#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G2「活动总量不得减少」的**归因**取证器（只读、零跑批、零 LLM）。

用途：口径卡 `round1-prereg-F5.md` AMENDMENT-3 · A3-4 的②条——若 ON 臂的
`#ACTIVITY_STARTED` 少于 `agents × days × 4`，本脚本给出"是否可归因于
`code/life/agent.py::_act` 的同地同活动去重门"的**事实依据**（不是结论，结论由 leader 裁决）。

判定所需的三组事实（全部来自 `run.jsonl`，不猜）：
  1. 缺失的 `(agent, day, slot)` 清单（与理论全集 `agents × days × 4` 对比）；
  2. 每个缺失三元组在该 slot 内**有没有** `PLACE_MOVE`：
     - 有 MOVE 却没有 `ACTIVITY_STARTED` ⇒ 归因**不是**去重门（记 `moved_but_no_activity`）；
     - 没有 MOVE ⇒ 与"本来就不需要动"或"被 `_act` 去重门拦下"一致，需看第 3 组；
  3. 该 agent 在该 slot 的**已知位置**（取此前的 `PLACE_ARRIVED`）与该 agent 最近一次
     `(place, activity_type)` 活动：若位置 == 该活动地点且 `activity_type` 与计划一致，
     则"同地 + 同活动进行中 ⇒ 不发起 MOVE"的去重门是**可能**成立的原因（记 `dedup_no_move`）。

用法（只读，跑完即可用）：
    python3 tools/habit/g2_attribution.py \
        --run ON=v2/evidence/run_f5_on_n16r48_seed42 \
        [--run OFF=v2/evidence/run_f5_off_n16r48_seed42] \
        --out-json v2/evidence/f5_round1/g2_attribution.json

退出码：0 = 打印完成（**不代表**判定通过）；2 = 输入不可用。
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

SLOTS = ("morning", "afternoon", "evening", "night")


def _load(run_dir: Path):
    log = run_dir / "run.jsonl"
    if not log.is_file():
        raise SystemExit(f"[g2] missing run.jsonl: {log}")
    acts, moves, arrives = {}, defaultdict(list), defaultdict(list)
    with log.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"ACTIVITY_STARTED"' not in line and '"PLACE_' not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            t = rec.get("type")
            p = rec.get("payload") or {}
            if t == "ACTIVITY_STARTED":
                key = (str(p.get("agent_id")), p.get("day"), p.get("slot"))
                acts[key] = {"place": p.get("place"), "activity_type": p.get("activity_type"),
                             "template": p.get("template"), "seq": rec.get("seq")}
            elif t == "PLACE_MOVE":
                moves[(str(p.get("agent_id")), p.get("day"), p.get("slot"))].append(
                    {"to": p.get("to_place"), "from": p.get("from_place"), "seq": rec.get("seq")})
            elif t == "PLACE_ARRIVED":
                arrives[str(p.get("agent_id"))].append(
                    {"day": p.get("day"), "slot": p.get("slot"), "place": p.get("place"),
                     "seq": rec.get("seq")})
    return acts, moves, arrives


def _last_place(arrives_by_agent, agent, day, slot):
    """该 agent 在 (day, slot) 之前最后到达的地点。"""
    idx = {s: i for i, s in enumerate(SLOTS)}
    best = None
    for a in arrives_by_agent.get(agent, []):
        if a["day"] is None or a["slot"] not in idx:
            continue
        if a["day"] < (day if day is not None else -1) or (
                a["day"] == day and idx[a["slot"]] <= idx.get(slot, 0)):
            if best is None or (a["day"], idx[a["slot"]]) > (best["day"], idx[best["slot"]]):
                best = a
    return best["place"] if best else None


def analyze(run_dir: Path) -> dict:
    acts, moves, arrives = _load(run_dir)
    agents = sorted({k[0] for k in acts})
    days = sorted({k[1] for k in acts if isinstance(k[1], int)})
    expected = len(agents) * len(days) * len(SLOTS)
    got = len(acts)
    missing = []
    for a in agents:
        for d in days:
            for s in SLOTS:
                if (a, d, s) not in acts:
                    mv = moves.get((a, d, s), [])
                    last = _last_place(arrives, a, d, s)
                    # 该 agent 最近一次"进行中"的活动（同 day 更早 slot）
                    idx = {x: i for i, x in enumerate(SLOTS)}
                    prior = None
                    for (aa, dd, ss), v in acts.items():
                        if aa == a and dd == d and idx.get(ss, 99) < idx.get(s, 0):
                            if prior is None or idx[ss] > idx[prior[0]]:
                                prior = (ss, v)
                    reason = ("moved_but_no_activity" if mv
                              else ("dedup_no_move" if (prior and last and
                                                        last == prior[1].get("place"))
                                    else "never_planned_or_asleep"))
                    missing.append({"agent": a, "day": d, "slot": s,
                                    "moves_in_slot": mv,
                                    "last_known_place": last,
                                    "prior_slot_activity": (None if not prior else
                                                            {"slot": prior[0], **prior[1]}),
                                    "candidate_reason": reason})
    by_reason = Counter(m["candidate_reason"] for m in missing)
    return {
        "run_dir": str(run_dir),
        "agents": len(agents), "days": len(days),
        "expected_agents_days_x4": expected,
        "actual_activity_started": got,
        "diff": got - expected,
        "g2_no_decrease": got >= expected or (expected - got) <= 2,
        "missing_total": len(missing),
        "missing_by_reason": dict(by_reason),
        "missing_detail": missing[:50],
        "note": ("本文件只给事实与候选归因，不作判定；A3-4 的②条由 leader 裁决。"
                 "`dedup_no_move` = 该 slot 无 MOVE 且当时位置 == 上一 slot 活动地点 ⇒ 与 "
                 "`_act` 同地同活动去重门一致；`moved_but_no_activity` = 有 MOVE 却无活动 ⇒ 不可归因于去重门。"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G2 活动总量归因取证（只读）")
    ap.add_argument("--run", action="append", default=[], metavar="TAG=DIR")
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args(argv)
    out, bad = {}, 0
    for spec in a.run:
        if "=" not in spec:
            print(f"[g2] bad --run: {spec}", file=sys.stderr)
            return 2
        tag, d = spec.split("=", 1)
        rd = Path(d).resolve()
        if not (rd / "run.jsonl").is_file():
            print(f"[g2] missing {rd / 'run.jsonl'}", file=sys.stderr)
            bad = 2
            continue
        out[tag] = analyze(rd)
        r = out[tag]
        print(f"[g2] {tag}: expected={r['expected_agents_days_x4']} "
              f"actual={r['actual_activity_started']} diff={r['diff']:+d} "
              f"missing={r['missing_total']} reasons={r['missing_by_reason']}")
    txt = json.dumps({"arms": out}, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out_json:
        p = Path(a.out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt + "\n", encoding="utf-8")
        print(f"[g2] wrote {p}")
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
