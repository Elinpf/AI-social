#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.3 结构性风险核查（**纯离线、不调模型**）：`place` 分布是否被 D2.3 改动影响？

预登记 §5/§7.2 写明：本臂**唯一的**结构性风险是「把 place 的计算提前 ⇒ place 分布变了 ⇒ 作废（非单变量）」。
`d23_mock_verification.md` §2 报的"place 直方图逐项相等"是**平凡相等**（60 轮内只有 round=0 一次计划、
历史为空 ⇒ `place_peer_counts={}` ⇒ 权重恒 1 ⇒ ON≡OFF，日志逐字节相同，sha256 都相等），
**不能**用来证明"提前算 place 不改 place"。

本工具补的是**非平凡**核查：人为注入**强极化**的 `place_peer_counts`（保证权重真的不同 ⇒ 对端真的变了），
在**真实模板表 + 真实地点表 + 完整一周（7 天 × 4 时段）16 个居民**上，逐槽比较
ON（权重生效）与 OFF（原路径）的 `place` 是否**逐项相等**，同时报 `participants` 的换人率。

判据（写死）：
  * `place_identical_rate` **必须 = 100%**（否则本臂作废：非单变量）；
  * `participants_change_rate` **应当 > 0**（否则权重没生效，核查无意义 ⇒ 读数标注 invalid）。

用法：
    python3 tools/d23/place_invariance_check.py [--root code] [--out-json path]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

_SLOTS = ["morning", "afternoon", "evening", "night"]
_DAY_TYPES = ["workday", "workday", "workday", "workday", "workday", "weekend", "weekend"]


def _load(root: str):
    sys.path.insert(0, root)
    from life.templates import load_activity_templates
    raw = json.load(open(os.path.join(root, "config", "places.json"), encoding="utf-8"))
    places = {x["place_id"]: x for x in raw["places"]}
    tpls = load_activity_templates(places=places)
    return tpls, places


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="code")
    ap.add_argument("--agents", type=int, default=16)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--alpha", type=float, default=3.0)
    a = ap.parse_args()

    tpls, places = _load(a.root)
    from life.planner import Planner

    agents = ["P%03d" % i for i in range(1, a.agents + 1)]
    # 强极化 counts：让每个 place 下的权重真的不同（最大 1+3*9=28 vs 1）
    polar = {}
    for pi, place in enumerate(sorted(places)):
        polar[place] = {p: (9 if (i + pi) % 4 == 0 else 0) for i, p in enumerate(agents)}

    n_slot = place_diff = parts_diff = parts_slots = 0
    place_hist_on, place_hist_off = Counter(), Counter()
    per_agent_change = {}
    for ag in agents:
        peers = [p for p in agents if p != ag]
        p_off = Planner(ag, tpls, peers, places)
        p_on = Planner(ag, tpls, peers, places,
                       place_peer_counts=polar, place_affinity_alpha=a.alpha)
        ch = 0
        for dow in range(7):
            for si, slot in enumerate(_SLOTS):
                slot_id = f"day{dow}-{slot}"
                # cash 取足够大，保证 template 前置条件不因现金差异掩盖差异
                off = p_off.plan_slot(_DAY_TYPES[dow], slot, slot_id, cash=10 ** 6)
                on = p_on.plan_slot(_DAY_TYPES[dow], slot, slot_id, cash=10 ** 6)
                n_slot += 1
                assert (off is None) == (on is None), (ag, slot_id, off, on)
                if off is None:
                    continue
                place_hist_off[str(off["place"])] += 1
                place_hist_on[str(on["place"])] += 1
                if off["place"] != on["place"]:
                    place_diff += 1
                if off["template_id"] != on["template_id"]:
                    parts_diff += 1          # 模板变了 ⇒ 对端不可比，单独计数
                    continue
                parts_slots += 1
                if off["participants"] != on["participants"]:
                    parts_diff += 1
                    ch += 1
        per_agent_change[ag] = ch

    out = {
        "mode": "offline-plan-only (no LLM)",
        "n_agents": a.agents, "n_slots": n_slot,
        "alpha": a.alpha,
        "place_identical_rate_pct": round(100.0 * (n_slot - place_diff) / n_slot, 4) if n_slot else None,
        "place_diff_count": place_diff,
        "place_hist_equal": dict(place_hist_on) == dict(place_hist_off),
        "place_hist_off": dict(place_hist_off),
        "place_hist_on": dict(place_hist_on),
        "comparable_slots": parts_slots,
        "participants_change_rate_pct": round(100.0 * parts_diff / parts_slots, 2) if parts_slots else None,
        "verdict": None,
    }
    ok_place = out["place_identical_rate_pct"] == 100.0
    ok_change = (out["participants_change_rate_pct"] or 0) > 0
    out["verdict"] = ("PASS（place 逐项不变 + 权重确实改了人）" if ok_place and ok_change
                      else "INVALID（权重未生效，核查无意义）" if ok_place else
                      "FAIL（place 分布变了 ⇒ 作废：非单变量）")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.out_json:
        json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if ok_place else 1


if __name__ == "__main__":
    sys.exit(main())
