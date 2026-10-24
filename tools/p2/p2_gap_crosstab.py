#!/usr/bin/env python3
"""P2 缺口的归因交叉表（只读诊断，主出数器之外的旁证）。

性质：只读。只吃既有 run.jsonl，不跑批、不调 LLM、不改 code/**、不写日志（除 --out）。
口径与 tools/p2/plan_actual_consistency.py 完全同源（同一份 DEFINITIONS、同一个
1/3 门复刻、同一个 gap 主类优先级）；本文件**不新造分母**，只做三件事：

  1. class × (b_place, slot, a_psize, b_psize, reciprocal, B_role_id) 交叉表；
  2. 对 `peer_planner_gate_skip_fallback` 档做**严格机制核验**：
     `code/life/agent.py:594-607 _base_activity` → `:613-621 _work_place_for` 是确定性函数，
     输入只有 (day_type, slot, persona.role_id, places)。本脚本把这三样**真值**接进来，
     不再用「任意 affords-work 地点」蒙混：
       - `role_id`      ← `code/config/personas.json`（agent_id == persona_id）
       - `ROLE_WORKPLACE` / `ACTIVITY_TO_PLACES` ← `code/life/constants.py`（**import 真源**）
       - `open_slots` / `affordances` ← `code/config/places.json`（复刻 `_valid`）
  3. **两个口径分开命名、分别报数、不得合并**（CYCLE-19 复核 #6c 要求）：
       - `gs_exact_strict`：按 persona `work_place` 逐条精确预测 ⇒ 只有它才能叫「逐条命中」；
       - `gs_exact_weak`  ：只判「落在任一 affords-`work` 的地点」⇒ 弱判定，仅作对照。

用法（脚本自己把 `<repo>/code` 插进 sys.path，且 `sys.dont_write_bytecode=True`
保证不在 `code/` 下留 `__pycache__`）：
  python3 tools/p2/p2_gap_crosstab.py \
      --run v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
      --out v2/evidence/p2-companion-gap-<sha8>/p2_gap_crosstab_f3off.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True          # 不在 code/ 下留 __pycache__（禁区纪律）

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
CODE = REPO / "code"
sys.path.insert(0, str(CODE))

from life.constants import ACTIVITY_TO_PLACES, ROLE_WORKPLACE  # noqa: E402  真源，不硬编码

SLOTS = ["morning", "afternoon", "evening", "night"]
DAY_TYPES = ["workday"] * 5 + ["weekend"] * 2  # code/life/constants.py TIME_CONFIG


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def gate_skipped(agent_id: str, slot_id: str) -> bool:
    """复刻 code/life/planner.py:103-104 的确定性 1/3 跳过门。"""
    return int(sha256_hex(f"{agent_id}|{slot_id}|gate")[:2], 16) % 3 == 0


def load_personas() -> dict:
    """`code/config/personas.json` → {persona_id: role_id}。"""
    raw = json.loads((CODE / "config" / "personas.json").read_text(encoding="utf-8"))["personas"]
    return {p["persona_id"]: p["role_id"] for p in raw}


def load_places() -> dict:
    """`code/config/places.json` → {place_id: {"open_slots": [...], "affordances": [...]}}。"""
    raw = json.loads((CODE / "config" / "places.json").read_text(encoding="utf-8"))["places"]
    return {p["place_id"]: {"open_slots": p.get("open_slots") or [],
                            "affordances": p.get("affordances") or []} for p in raw}


def valid(atype: str, place: str, slot: str, places: dict) -> bool:
    """复刻 code/life/agent.py:609-611 `_valid`。"""
    spec = places.get(place, {})
    return slot in spec.get("open_slots", []) and atype in spec.get("affordances", [])


def work_place_for(role_id: str, slot: str, places: dict) -> str | None:
    """复刻 code/life/agent.py:613-621 `_work_place_for`（persona.work_place → 兜底列表）。"""
    wp = ROLE_WORKPLACE.get(role_id, "plaza")
    if valid("work", wp, slot, places):
        return wp
    for cand in ACTIVITY_TO_PLACES["work"]:
        if valid("work", cand, slot, places):
            return cand
    return None


def base_activity(day_type: str, slot: str, role_id: str | None, places: dict) -> tuple[str, str | None]:
    """复刻 code/life/agent.py:594-607 `_base_activity`（work 分支走 `_work_place_for`）。"""
    if slot == "night":
        return ("rest", "residence")
    if slot == "morning":
        if day_type == "workday":
            wp = work_place_for(role_id or "", slot, places)
            return ("work", wp) if wp else ("self_care", "residence")
        return ("self_care", "residence")
    if slot == "afternoon":
        if day_type == "workday":
            wp = work_place_for(role_id or "", slot, places)
            return ("work", wp) if wp else ("socialize", "plaza")
        return ("socialize", "plaza")
    return ("socialize", "cafe") if day_type == "workday" else ("leisure", "park")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    personas = load_personas()
    places = load_places()

    acts, arrived, moved = [], [], set()
    with open(args.run, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            t, p = d["type"], (d.get("payload") or {})
            if t == "ACTIVITY_STARTED":
                acts.append(p)
            elif t == "PLACE_ARRIVED":
                arrived.append(p)
                moved.add((p.get("agent_id"), p.get("day"), p.get("slot")))
            elif t == "PLACE_MOVE":
                moved.add((p.get("agent_id"), p.get("day"), p.get("slot")))

    cell = {(p["agent_id"], p["day"], p["slot"]): p for p in acts}
    # 弱判定用的地点池：日志里**真实出现过**的 affords-work 地点（只服务 gs_exact_weak）
    work_places_seen = {p["place"] for p in acts if p.get("activity_type") == "work"}

    gaps = []
    for p in acts:
        A = p["agent_id"]
        for B in (p.get("participants") or []):
            if B == A:
                continue
            bp = cell.get((B, p["day"], p["slot"]))
            b_place = bp.get("place") if bp else None
            if b_place is None:
                continue
            if b_place == p.get("place"):
                continue
            slot_id = bp.get("slot_id") or f"day{p['day']}-{p['slot']}"
            has_tmpl = bp.get("template") is not None
            b_psize = len(bp.get("participants") or [])
            if b_place == "residence":
                cls = "peer_at_residence"
            elif (not has_tmpl) and gate_skipped(B, slot_id):
                cls = "peer_planner_gate_skip_fallback"
            elif b_psize >= 2:
                cls = "peer_planned_elsewhere_with_own_group"
            else:
                cls = "peer_planned_elsewhere_solo"
            day_type = DAY_TYPES[p["day"] % 7]
            role_id = personas.get(B)
            a_type, base_place_strict = base_activity(day_type, p["slot"], role_id, places)
            gaps.append({
                "A": A, "B": B, "day": p["day"], "slot": p["slot"], "day_type": day_type,
                "A_role_id": personas.get(A), "B_role_id": role_id,
                "a_place": p.get("place"), "b_place": b_place, "class": cls,
                "a_psize": len(p.get("participants") or []), "b_psize": b_psize,
                "reciprocal": A in (bp.get("participants") or []),
                "peer_no_place_move": (B, p["day"], p["slot"]) not in moved,
                "base_activity_type_predicted": a_type,
                "base_place_predicted_strict": base_place_strict,
                "base_place_predicted_weak": ("<any affords-work place>"
                                              if a_type == "work" else base_place_strict),
                "b_has_template": has_tmpl,
                "b_template": bp.get("template"),
            })

    total = len(gaps)
    by_class = collections.Counter(g["class"] for g in gaps)

    def xtab(field):
        out = {}
        for c in sorted(by_class):
            out[c] = dict(sorted(collections.Counter(
                str(g[field]) for g in gaps if g["class"] == c).items(), key=lambda kv: (-kv[1], kv[0])))
        return out

    # ---- 机制核验：两个口径分开计数，**不得合并** ----
    gs = [g for g in gaps if g["class"] == "peer_planner_gate_skip_fallback"]
    gs_strict = gs_weak = gs_mismatch = 0
    gs_mismatch_rows = []
    for g in gs:
        strict = g["base_place_predicted_strict"]
        if strict is not None and strict == g["b_place"]:
            gs_strict += 1
        else:
            gs_mismatch += 1
            gs_mismatch_rows.append(g)
        if g["base_activity_type_predicted"] == "work":
            if g["b_place"] in work_places_seen:
                gs_weak += 1
        elif g["b_place"] == strict:
            gs_weak += 1

    gs_no_tmpl = sum(1 for g in gs if not g["b_has_template"])
    gs_residence = sum(1 for g in gs if g["b_place"] == "residence")

    solo = [g for g in gaps if g["class"] == "peer_planned_elsewhere_solo"]
    own = [g for g in gaps if g["class"] == "peer_planned_elsewhere_with_own_group"]

    out = {
        "meta": {
            "script": "tools/p2/p2_gap_crosstab.py",
            "input_run": args.run,
            "input_sha256": hashlib.sha256(open(args.run, "rb").read()).hexdigest(),
            "role_source": "code/config/personas.json（agent_id == persona_id ⇒ role_id）",
            "constant_source": "code/life/constants.py（import 真源 ROLE_WORKPLACE / ACTIVITY_TO_PLACES）",
            "places_source": "code/config/places.json（open_slots / affordances，复刻 _valid）",
            "note": "只读诊断旁证；不改主出数器的分母与定义。与 plan_actual_consistency.py 同源复刻。",
        },
        "gap_total": total,
        "class_counts": dict(sorted(by_class.items())),
        "crosstab": {
            "class_x_b_place": xtab("b_place"),
            "class_x_slot": xtab("slot"),
            "class_x_a_psize": xtab("a_psize"),
            "class_x_b_psize": xtab("b_psize"),
            "class_x_reciprocal": xtab("reciprocal"),
            "class_x_peer_no_place_move": xtab("peer_no_place_move"),
            "class_x_b_role_id": xtab("B_role_id"),
        },
        "mechanism_checks": {
            "gate_skip_class": {
                "n": len(gs),
                "prediction_note": "严格口径把 persona.role_id → ROLE_WORKPLACE → _valid → ACTIVITY_TO_PLACES 兜底"
                                   "全链接进来；弱口径只判「落在任一 affords-work 地点」。两者不可混读，"
                                   "报告引用「逐条命中」时只能指 gs_exact_strict。",
                "gs_exact_strict": gs_strict,
                "gs_exact_weak": gs_weak,
                "mismatch_strict": gs_mismatch,
                "mismatch_rows": gs_mismatch_rows[:20],
                "b_has_template_false": gs_no_tmpl,
                "b_place_residence_share": gs_residence,
                "verdict_strict": ("机制已核验（严格口径）：门跳过的对端这一格 %d/%d 逐条等于 _base_activity "
                                   "严格预测落点（mismatch %d），且 %d/%d 无 template"
                                   % (gs_strict, len(gs), gs_mismatch, gs_no_tmpl, len(gs))),
            },
            "solo_class": {"n": len(solo),
                           "b_has_template_true": sum(1 for g in solo if g["b_has_template"])},
            "own_group_class": {"n": len(own),
                                "b_has_template_true": sum(1 for g in own if g["b_has_template"])},
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("wrote", args.out)
    print("gaps", total, "classes", dict(sorted(by_class.items())))
    print("gate_skip 严格口径 %d/%d 命中（mismatch %d）｜弱口径 %d/%d｜无template %d/%d"
          % (gs_strict, len(gs), gs_mismatch, gs_weak, len(gs), gs_no_tmpl, len(gs)))


if __name__ == "__main__":
    main()
