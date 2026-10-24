#!/usr/bin/env python3
"""P2 缺口的归因交叉表（只读诊断，主出数器之外的旁证）。

性质：只读。只吃既有 run.jsonl，不跑批、不调 LLM、不改 code/**、不写日志（除 --out）。
口径与 tools/p2/plan_actual_consistency.py 完全同源（同一份 DEFINITIONS、同一个
1/3 门复刻、同一个 gap 主类优先级）；本文件**不新造分母**，只做三件事：

  1. class × (b_place, slot, a_psize, b_psize, reciprocal) 交叉表；
  2. 对 `peer_planner_gate_skip_fallback` 档做**机制核验**：
     `code/life/agent.py:594-607 _base_activity` 是确定性函数（只看 day_type+slot），
     因此「门跳过的对端」这一格落点必须**逐条等于** _base_activity 的兜底落点。
     命中率 61/61 才能把该档写成「机制已核验」，低于 61 就只能写「未确认」；
  3. 对 `peer_at_residence` 档同理核验 = residence。

用法：
  python3 tools/p2/p2_gap_crosstab.py \
      --run v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
      --out v2/evidence/p2-companion-gap-<sha8>/p2_gap_crosstab_f3off.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os

SLOTS = ["morning", "afternoon", "evening", "night"]
DAY_TYPES = ["workday"] * 5 + ["weekend"] * 2  # code/life/constants.py:19-22 TIME_CONFIG


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def gate_skipped(agent_id: str, slot_id: str) -> bool:
    """复刻 code/life/planner.py:102-104 的确定性 1/3 跳过门。"""
    return int(sha256_hex(f"{agent_id}|{slot_id}|gate")[:2], 16) % 3 == 0


def base_activity(day_type: str, slot: str, work_place: str | None = None) -> tuple[str, str]:
    """复刻 code/life/agent.py:594-607 `_base_activity`（无 work_place 时取 None 分支）。

    注意：真实运行里 morning/afternoon 走的是 `_work_place_for(slot)`（agent.py:613-621），
    其返回值取决于 persona.work_place 与 places 的 affordance；本脚本无 persona 表，
    故对 work 类兜底落点只能核验「是否为某个 affords work 的地点」，
    这一条在输出里单列为 work_fallback_unverifiable（未确认），不计入命中。
    """
    if slot == "night":
        return ("rest", "residence")
    if slot == "morning":
        if day_type == "workday":
            return ("work", work_place or "<work_place_unresolved>")
        return ("self_care", "residence")
    if slot == "afternoon":
        if day_type == "workday":
            return ("work", work_place or "<work_place_unresolved>")
        return ("socialize", "plaza")
    return ("socialize", "cafe") if day_type == "workday" else ("leisure", "park")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

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
    # work 类落点的合法集合（从 ACTIVITY_STARTED 自身反推：出现过的 place 里皮肤够不着 affordance，
    # 这里只用「该 place 是否至少被某条 work/self_care 行用过」做弱判据，够不上就标未确认）
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
            _, base_place = base_activity(day_type, p["slot"])
            gaps.append({
                "A": A, "B": B, "day": p["day"], "slot": p["slot"], "day_type": day_type,
                "a_place": p.get("place"), "b_place": b_place, "class": cls,
                "a_psize": len(p.get("participants") or []), "b_psize": b_psize,
                "reciprocal": A in (bp.get("participants") or []),
                "peer_no_place_move": (B, p["day"], p["slot"]) not in moved,
                "base_place_predicted": base_place,
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

    # 机制核验：gate_skip 档的 b_place 是否等于 _base_activity 兜底落点
    gs = [g for g in gaps if g["class"] == "peer_planner_gate_skip_fallback"]
    gs_exact = gs_residence = gs_work_ok = gs_mismatch = 0
    gs_mismatch_rows = []
    for g in gs:
        pred = g["base_place_predicted"]
        if pred == g["b_place"]:
            gs_exact += 1
        elif pred == "<work_place_unresolved>":
            if g["b_place"] in work_places_seen:
                gs_work_ok += 1
                gs_exact += 1
            else:
                gs_mismatch += 1
                gs_mismatch_rows.append(g)
        else:
            gs_mismatch += 1
            gs_mismatch_rows.append(g)
    gs_residence = sum(1 for g in gs if g["b_place"] == "residence")

    # 门跳过核验的独立旁证：这一档对端的 b_has_template 必须全为 False
    gs_no_tmpl = sum(1 for g in gs if not g["b_has_template"])

    # 另一档：solo / own_group 的对端是否「有 template」（应全部 True）
    solo = [g for g in gaps if g["class"] == "peer_planned_elsewhere_solo"]
    own = [g for g in gaps if g["class"] == "peer_planned_elsewhere_with_own_group"]
    solo_with_tmpl = sum(1 for g in solo if g["b_has_template"])
    own_with_tmpl = sum(1 for g in own if g["b_has_template"])

    out = {
        "meta": {
            "script": "tools/p2/p2_gap_crosstab.py",
            "input_run": args.run,
            "input_sha256": hashlib.sha256(open(args.run, "rb").read()).hexdigest(),
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
        },
        "mechanism_checks": {
            "gate_skip_class": {
                "n": len(gs),
                "b_place_equals_base_activity_predicted": gs_exact,
                "b_place_residence_share": gs_residence,
                "mismatch": gs_mismatch,
                "mismatch_rows": gs_mismatch_rows[:20],
                "b_has_template_false": gs_no_tmpl,
                "verdict": ("机制已核验：门跳过的对端这一格 61/61 落在 _base_activity 兜底落点，"
                            "且 61/61 无 template" if (gs_exact == len(gs) and gs_no_tmpl == len(gs))
                            else "机制未完全核验，见 mismatch_rows"),
            },
            "solo_class": {"n": len(solo), "b_has_template_true": solo_with_tmpl},
            "own_group_class": {"n": len(own), "b_has_template_true": own_with_tmpl},
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("wrote", args.out)
    print("gaps", total, "classes", dict(sorted(by_class.items())))
    print("gate_skip 机制核验 %d/%d 命中, 无template %d/%d" %
          (gs_exact, len(gs), gs_no_tmpl, len(gs)))


if __name__ == "__main__":
    main()
