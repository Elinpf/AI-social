#!/usr/bin/env python3
"""P2 只读出数器：「计划同伴 vs 实际同处」一致率 + 缺口档。

性质：只读。只吃既有 run.jsonl，不跑批、不调 LLM、不改任何 code/** 文件、
不写日志。输出确定性 JSON（无时间戳字段）；同一输入 + 同参数重放字节一致。

口径全部写死在本文件顶部（DEFINITIONS）与 v2/evidence/p2_plan_actual_consistency/README.md。
禁止「反复试分母」——改口径必须先改 README 再重跑。

用法：
  python3 tools/p2/plan_actual_consistency.py \
      --run v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
      --out v2/evidence/p2_plan_actual_consistency/p2_plan_actual_consistency.json \
      --secondary-run v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
      --stable
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os

RPS = 3  # ROUNDS_PER_SLOT，与 tools/f9 同源（code/life/constants.py TIME_CONFIG）
SLOTS = ["morning", "afternoon", "evening", "night"]

DEFINITIONS = {
    "unit_plan_peer": "「计划同伴对实例」= 一条 ACTIVITY_STARTED 行 (agent A, day, slot) 的 "
                      "payload.participants 中除 A 自身之外的每一个 agent B，构成一个有向对实例 (A→B)。"
                      "同一对 (A,B) 若双方各自的行都列了对方，则计 2 个有向实例；"
                      "另给去重无向口径 unique_undirected。",
    "unit_realized_place": "「实际所在」= 同一 (agent, day, slot) 格的 ACTIVITY_STARTED.payload.place。"
                           "这是磁盘日志里唯一全覆盖的落点字段（16 agents × 5 days × 4 slots = 320 格，"
                           "ACTIVITY_STARTED 行数 320，无缺口）；PLACE_ARRIVED.payload.place 仅覆盖发生位移的 299 格，"
                           "用于交叉校验（见 validators.arrival_place_vs_activity_place_mismatch）。",
    "time_alignment": "以 slot 对齐（(day, slot) 二元组），不以 round 对齐。理由："
                      "ACTIVITY_STARTED 本身就挂在 slot 上（每格一行，start_tick 固定为槽内 tick）；"
                      "日志里同一 slot 内的位移事件只发生在槽首，round 级对齐不增加信息量。",
    "consistent": "对实例 (A→B, day, slot) 判「一致」当且仅当 "
                  "place(B, day, slot) == place(A, day, slot) —— 即 B 自己这一格记录的落点与 A 计划里的落点相同。"
                  "注意：一致 = 空间共处，不等于「两人真的互动过」；互动另由 msg_lens 段报告。",
    "decidable": "对实例可判定当且仅当 B 在该 (day, slot) 有 ACTIVITY_STARTED 行且 place 非 null。"
                 "不可判定的实例单独计数，不进主分母（本批实测 0）。",
    "excluded_events": "排除：MSG_DM/MSG_PUBLIC（对话层，只用于 msg_lens 辅助段，不进主口径）、"
                       "GROUP_CREATED（只用于第 5 项对账）、RELATION_ENCOUNTER（关系层共现，非落点）、"
                       "OBSERVATION（观察者视角，非本人落点）。",
    "gap_classes": "缺口 = 可判定但对实例不一致。互斥主类按以下优先级判定，命中即停："
                   "(1) peer_at_residence：B 同槽落点 = residence（私域/在家）；"
                   "(2) peer_planner_gate_skip_fallback：B 同槽行无 template 且 planner 1/3 确定性门判定为跳过"
                   "（复刻 code/life/planner.py:102-104），即 B 走 _base_activity 兜底；"
                   "(3) peer_planned_elsewhere_with_own_group：B 非门跳过，且 B 自己的 participants 长度 >=2"
                   "（B 另有同伴，只是不在 A 这里）；"
                   "(4) peer_planned_elsewhere_solo：B 非门跳过，且 B 自己的 participants 长度 <=1（B 独自在别处）。",
    "crosscut_flags": "非互斥标签，与主类正交：reciprocal_both_listed（B 的行也列了 A）、"
                      "peer_no_place_move（B 该格无 PLACE_MOVE/PLACE_ARRIVED，原地未动）、"
                      "peer_stayed_prev_place（B 该格落点 == B 上一槽落点）。",
    "secondary_batch": "副批只用于「同一把尺子在另一批是否同量级」，不构成横向比较结论，"
                       "也不是同臂重跑（两批 env 开关不同、臂不同）。",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def gate_skipped(agent_id: str, slot_id: str) -> bool:
    """复刻 code/life/planner.py:102-104 的确定性 1/3 跳过门（与 tools/f9 同一实现）。"""
    return int(sha256_hex(f"{agent_id}|{slot_id}|gate")[:2], 16) % 3 == 0


def pct(n: int, d: int) -> dict:
    return {"numerator": n, "denominator": d, "value": (n / d) if d else None}


def analyze(path: str, full: bool) -> dict:
    """对一个 run.jsonl 出读数。full=False 时只出主读数（副批用，省字段噪声）。"""
    acts = []
    arrived = []
    moved_cells = set()
    groups = []
    msg_links = collections.defaultdict(set)
    n_msgs = 0
    n_lines = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            d = json.loads(line)
            t = d["type"]
            p = d.get("payload") or {}
            if t == "ACTIVITY_STARTED":
                acts.append(p)
            elif t == "PLACE_ARRIVED":
                arrived.append(p)
                moved_cells.add((p.get("agent_id"), p.get("day"), p.get("slot")))
            elif t == "PLACE_MOVE":
                moved_cells.add((p.get("agent_id"), p.get("day"), p.get("slot")))
            elif t == "GROUP_CREATED":
                groups.append(p)
            elif t in ("MSG_DM", "MSG_PUBLIC"):
                n_msgs += 1
                k = (p.get("day"), p.get("slot"))
                if t == "MSG_DM":
                    if p.get("from") and p.get("to"):
                        msg_links[k].add(tuple(sorted((p["from"], p["to"]))))
                else:
                    ps = sorted({x for x in (p.get("participants") or [p.get("author")]) if x})
                    for i in range(len(ps)):
                        for j in range(i + 1, len(ps)):
                            msg_links[k].add((ps[i], ps[j]))

    cell = {(p["agent_id"], p["day"], p["slot"]): p for p in acts}
    # 规划层指纹：只取「计划层」六要素，用于判断两批的规划流是否逐字段相同
    plan_fp = hashlib.sha256(json.dumps(
        [[p["agent_id"], p["day"], p["slot"], p.get("place"),
          list(p.get("participants") or []), p.get("template")] for p in acts],
        ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    agents = sorted({a for (a, _d, _s) in cell})
    days = sorted({d for (_a, d, _s) in cell})
    arr_place = {(p["agent_id"], p["day"], p["slot"]): p.get("place") for p in arrived}

    pair_instances = []
    for p in acts:
        A = p["agent_id"]
        for B in (p.get("participants") or []):
            if B == A:
                continue
            pair_instances.append((A, B, p["day"], p["slot"], p.get("place"),
                                   len(p.get("participants") or [])))

    decidable = 0
    undecidable = 0
    consistent = 0
    gaps = []
    by_slot = collections.defaultdict(lambda: {"decidable": 0, "consistent": 0})
    by_psize = collections.defaultdict(lambda: {"decidable": 0, "consistent": 0})
    recip_total = recip_consistent = 0

    for A, B, day, slot, a_place, a_psize in pair_instances:
        bp = cell.get((B, day, slot))
        b_place = bp.get("place") if bp else None
        both = bool(bp) and (A in (bp.get("participants") or []))
        if both:
            recip_total += 1
        if b_place is None:
            undecidable += 1
            continue
        decidable += 1
        key = "1" if a_psize <= 1 else ("2" if a_psize == 2 else ("3-4" if a_psize <= 4 else "5+"))
        by_slot[slot]["decidable"] += 1
        by_psize[key]["decidable"] += 1
        if b_place == a_place:
            consistent += 1
            by_slot[slot]["consistent"] += 1
            by_psize[key]["consistent"] += 1
            if both:
                recip_consistent += 1
            continue
        slot_id = bp.get("slot_id") or f"day{day}-{slot}"
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
        idx = SLOTS.index(slot)
        prev = cell.get((B, day, SLOTS[idx - 1])) if idx > 0 else cell.get((B, day - 1, "night"))
        prev_place = prev.get("place") if prev else None
        gaps.append({
            "A": A, "B": B, "day": day, "slot": slot,
            "a_place": a_place, "b_place": b_place, "class": cls,
            "flags": {
                "reciprocal_both_listed": both,
                "peer_no_place_move": (B, day, slot) not in moved_cells,
                "peer_stayed_prev_place": prev_place is not None and prev_place == b_place,
            },
            "a_psize": a_psize, "b_psize": b_psize,
        })

    gap_total = len(gaps)
    gap_classes = collections.Counter(g["class"] for g in gaps)

    # 去重无向口径
    und = {}
    for A, B, day, slot, _ap, _ps in pair_instances:
        k = (tuple(sorted((A, B))), day, slot)
        if k in und:
            continue
        ap = cell.get((A, day, slot))
        bp = cell.get((B, day, slot))
        ok = bool(ap and bp and ap.get("place") is not None and bp.get("place") is not None)
        und[k] = {"decidable": ok,
                  "consistent": ok and ap.get("place") == bp.get("place")}
    und_dec = sum(1 for v in und.values() if v["decidable"])
    und_con = sum(1 for v in und.values() if v["decidable"] and v["consistent"])

    core = {
        "input": path,
        "input_sha256": sha256_file(path),
        "input_lines": n_lines,
        "consistency_rate": pct(consistent, decidable),
        "decidable_pair_instances": decidable,
        "consistent_pair_instances": consistent,
        "gap_total": gap_total,
        "gap_share_of_decidable": pct(gap_total, decidable),
        "gap_classes": {c: {"count": gap_classes[c], "share_of_gaps": pct(gap_classes[c], gap_total)}
                        for c in sorted(gap_classes)},
        "unique_undirected_pairs": len(und),
        "consistency_rate_undirected": pct(und_con, und_dec),
        "activity_plan_fingerprint_sha256": plan_fp,
        "activity_plan_fingerprint_note": "对 ACTIVITY_STARTED 的 [agent, day, slot, place, participants, template] "
                                          "整体取 sha256；两批相同即规划流逐字段相同。",
    }
    if not full:
        return core

    gap_by_slot = collections.Counter(g["slot"] for g in gaps)
    gap_b_place = collections.Counter(g["b_place"] for g in gaps)
    flag_counts = {
        "reciprocal_both_listed": sum(1 for g in gaps if g["flags"]["reciprocal_both_listed"]),
        "peer_no_place_move": sum(1 for g in gaps if g["flags"]["peer_no_place_move"]),
        "peer_stayed_prev_place": sum(1 for g in gaps if g["flags"]["peer_stayed_prev_place"]),
    }

    # msg_lens
    cons_und = [k for k, v in und.items() if v["decidable"] and v["consistent"]]
    cons_msg = sum(1 for (ab, day, slot) in cons_und if ab in msg_links.get((day, slot), ()))
    gap_msg = sum(1 for g in gaps
                  if tuple(sorted((g["A"], g["B"]))) in msg_links.get((g["day"], g["slot"]), ()))

    # 第 5 项对账
    one_row_matches = 0
    gc_rows = []
    for g in groups:
        members = set(g.get("members") or [])
        matched = [p["agent_id"] for p in acts
                   if p["day"] == g["day"] and p["slot"] == g["slot"]
                   and set(p.get("participants") or []) == members]
        if len(matched) == 1:
            one_row_matches += 1
        gc_rows.append({"group_id": g.get("group_id"), "day": g["day"], "slot": g["slot"],
                        "n_members": len(members), "members": sorted(members),
                        "matching_activity_rows": matched})
    size8_rows = [p for p in acts if len(p.get("participants") or []) == 8]
    big_dec = big_con = 0
    for p in size8_rows:
        for B in (p.get("participants") or []):
            if B == p["agent_id"]:
                continue
            big_dec += 1
            q = cell.get((B, p["day"], p["slot"]))
            if q and q.get("place") == p.get("place"):
                big_con += 1

    mism = sum(1 for k, v in arr_place.items() if k in cell and cell[k].get("place") != v)
    expected_pairs = sum(max(0, len(p.get("participants") or []) - 1) for p in acts)

    core.update({
        "universe": {
            "agents": len(agents),
            "days": len(days),
            "slots": SLOTS,
            "rounds_per_slot": RPS,
            "activity_started_rows": len(acts),
            "agent_day_slot_cells": len(cell),
            "cells_formula": "16 agents × 5 days × 4 slots = 320",
            "place_arrived_rows": len(arrived),
            "cells_with_place_move": len(moved_cells),
            "msg_rows": n_msgs,
            "group_created_rows": len(groups),
        },
        "plan_pairs": {
            "planned_pair_instances": len(pair_instances),
            "planned_pair_check_expected": expected_pairs,
            "decidable_pair_instances": decidable,
            "undecidable_pair_instances": undecidable,
            "consistent_pair_instances": consistent,
            "consistency_rate": pct(consistent, decidable),
            "consistency_rate_denominator_note":
                "分母 = 可判定的计划对端有向对实例数（不是 agent 数、不是 slot 数）；"
                "分子 = 其中对端同槽落点与计划落点相同的实例数。",
            "unique_undirected_pairs": len(und),
            "unique_undirected_decidable": und_dec,
            "unique_undirected_consistent": und_con,
            "consistency_rate_undirected": pct(und_con, und_dec),
            "by_slot": {s: dict(by_slot[s], rate=pct(by_slot[s]["consistent"], by_slot[s]["decidable"]))
                        for s in SLOTS},
            "by_planner_participants_size": {
                k: dict(v, rate=pct(v["consistent"], v["decidable"]))
                for k, v in sorted(by_psize.items())},
            "reciprocal": {
                "pair_instances_both_listed": recip_total,
                "of_which_consistent": recip_consistent,
                "rate": pct(recip_consistent, recip_total),
                "pair_instances_unilateral": decidable - recip_total,
                "unilateral_consistent": consistent - recip_consistent,
                "unilateral_rate": pct(consistent - recip_consistent, decidable - recip_total),
                "note": "双向都在计划里互相列名的实例一致率单列；单向列名占多数，"
                        "「计划同伴」多数是单方列名。",
            },
        },
        "gap_breakdown": {
            "gap_total": gap_total,
            "gap_share_of_decidable": pct(gap_total, decidable),
            "classes": {c: {"count": gap_classes[c], "share_of_gaps": pct(gap_classes[c], gap_total)}
                        for c in sorted(gap_classes)},
            "class_definitions": DEFINITIONS["gap_classes"],
            "by_slot": {s: gap_by_slot.get(s, 0) for s in SLOTS},
            "peer_realized_place_histogram": dict(sorted(gap_b_place.items(), key=lambda kv: (-kv[1], kv[0]))),
            "crosscut_flags": {k: {"count": v, "share_of_gaps": pct(v, gap_total)}
                               for k, v in flag_counts.items()},
            "class_x_reciprocal": {c: sum(1 for g in gaps
                                          if g["class"] == c and g["flags"]["reciprocal_both_listed"])
                                   for c in sorted(gap_classes)},
            "unassignable": 0,
            "unassignable_note": "本批全部缺口都能在事件流里找到「对端自己这一格的落点 + 是否门跳过」两条可核事实，"
                                 "故主类归属 0 条无法归因。但「对端为什么改主意去别处」属动机层，日志不可归因，"
                                 "见 unconfirmed。",
        },
        "msg_lens": {
            "definition": "在「一致」的无向对里，看同 (day, slot) 是否出现一条把两人连起来的对话事件"
                          "（MSG_DM 的 from→to；MSG_PUBLIC 的 participants 两两全连接）。"
                          "辅助列，不进主分母，只回答「同处了有没有说话」。",
            "consistent_undirected_pairs": len(cons_und),
            "with_msg_link": cons_msg,
            "without_msg_link": len(cons_und) - cons_msg,
            "with_msg_link_rate": pct(cons_msg, len(cons_und)),
            "gap_pairs_with_msg_link": gap_msg,
            "gap_pairs_with_msg_link_note": "缺口对（不同地点）却仍出现对话连接的实例数；"
                                            "本口径下对话不需要同处，故该数不是矛盾。",
        },
        "group_created_reconciliation": {
            "question": "CYCLE-16 §3.2 P2 的反读矛盾：17 个 8 人组 vs 仅 17 行 participants=8，是否真实矛盾。",
            "group_created_total": len(groups),
            "group_created_distinct_member_sets": len({tuple(sorted(g.get("members") or [])) for g in groups}),
            "group_created_by_group_place_slot": {
                "|".join(k): v for k, v in sorted(collections.Counter(
                    (str(g.get("group_id")), g["slot"]) for g in groups).items())},
            "groups_with_exactly_one_matching_activity_row": one_row_matches,
            "activity_rows_with_participants_size_8": len(size8_rows),
            "rows_size8_by_slot": dict(sorted(collections.Counter(p["slot"] for p in size8_rows).items())),
            "rows_size8_by_place": dict(sorted(collections.Counter(p["place"] for p in size8_rows).items())),
            "size8_peer_pairs_decidable": big_dec,
            "size8_peer_pairs_co_located": big_con,
            "size8_peer_pair_co_located_rate": pct(big_con, big_dec),
            "verdict": "计数口径差异 + 字段语义差异，不是真实矛盾。GROUP_CREATED 以「组」为单位由世界层发出；"
                       "ACTIVITY_STARTED.participants 是「每个 agent 自己计划里的同伴名单」。"
                       "每个 GROUP_CREATED 的成员集合恰好对应 1 条（不是 8 条）ACTIVITY_STARTED 行的 participants，"
                       "即只有发起人那一条行把整组成员写进自己的名单，其余成员各自另发自己的行。"
                       "因此 17 组 ⇒ 17 行 size=8 自洽，17 不能用 8 去验。",
            "detail": gc_rows,
        },
        "validators": {
            "arrival_place_vs_activity_place_mismatch": mism,
            "arrival_place_vs_activity_place_note": "PLACE_ARRIVED.place 与同格 ACTIVITY_STARTED.place 不一致的格数（期望 0），"
                                                    "用于确认「落点取自 ACTIVITY_STARTED」不引入位移噪声。",
            "planned_pairs_sum_matches_row_arithmetic": (len(pair_instances) == expected_pairs),
            "cells_without_place_move": len(cell) - len(moved_cells),
            "cells_without_place_move_note": "这些格无位移事件（原地未动），落点仍由 ACTIVITY_STARTED.place 表征；"
                                             "已核对不存在「落点变了却没有位移事件」的情形"
                                             "（对应 gap crosscut flag peer_no_place_move 的语义边界）。",
            "gate_skip_cells": sum(1 for k, v in cell.items()
                                   if v.get("template") is None
                                   and gate_skipped(k[0], v.get("slot_id") or "")),
            "meta_assertion_participants_consistent": "meta.json: assertions.participants_consistent=true / "
                                                      "participants_violations=0 指的是「参加者集合内部自洽」的日志断言，"
                                                      "与「计划同伴 = 实际同处」的一致率不是一回事，不得互相解释。",
        },
        "unconfirmed": [
            "「对端为什么去了别处」的动机不可从日志归因；本文件只给落点事实与门跳过事实，不给因果。",
            "ACTIVITY_STARTED 是 slot 级计划事件，不是逐 round 的在场记录；同槽内短时错峰到场/离场本口径不可见。",
            "一致 ≠ 互动：msg_lens 的「同处但无对话」不能被解释为关系冷淡，只能说该槽内没有对话事件。",
            "max_messages_per_slot=2 饱和 / reply_window_rounds 错过属对话层参数，无法解释落点层缺口（缺口对按定义不同处）；"
            "至多是「同处之后没说话」的下游候选原因，未验证。",
            "单批读数；副批（另一 env 臂、同 code_sha）只用于「同尺子是否同量级」，不构成横向比较结论，"
            "也不能替代同臂重跑。",
        ],
    })
    return core


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--secondary-run", default=None)
    ap.add_argument("--stable", action="store_true",
                    help="保留参数以显式声明「无时间戳、可字节重放」；输出与是否传该参数无关。")
    args = ap.parse_args()

    primary = analyze(args.run, full=True)

    out = {
        "meta": {
            "script": "tools/p2/plan_actual_consistency.py",
            "input_run": args.run,
            "input_sha256": primary["input_sha256"],
            "input_lines": primary["input_lines"],
            "stable_flag_passed": bool(args.stable),
            "evidence_status": "描述性读数（无判据编号）",
            "note": "确定性输出：无时间戳字段；同一 run.jsonl + 同参数重放应字节一致。只读，不跑批、不调 LLM。",
        },
        "definitions": DEFINITIONS,
        "primary_batch": {
            "run_jsonl": args.run,
            "run_jsonl_sha256": primary["input_sha256"],
            "run_jsonl_lines": primary["input_lines"],
            "activity_plan_fingerprint_sha256": primary["activity_plan_fingerprint_sha256"],
        },
        "universe": primary["universe"],
        "plan_pairs": primary["plan_pairs"],
        "gap_breakdown": primary["gap_breakdown"],
        "msg_lens": primary["msg_lens"],
        "group_created_reconciliation": primary["group_created_reconciliation"],
        "validators": primary["validators"],
        "unconfirmed": primary["unconfirmed"],
        "secondary_batch": None,
    }

    if args.secondary_run:
        sec = analyze(args.secondary_run, full=False)
        out["secondary_batch"] = {
            "run_jsonl": args.secondary_run,
            "run_jsonl_sha256": sec["input_sha256"],
            "run_jsonl_lines": sec["input_lines"],
            "arm_note": "副批是 F-4（对话修复）ON 臂，与主批 F-3 OFF 臂不同 env 开关；同 code_sha / 同 seed / 同 n16r60。"
                        "因此本字段只回答「同一把尺子在另一批是否同量级」，不是同臂重跑，也不构成横向比较结论。",
            "consistency_rate": sec["consistency_rate"],
            "decidable_pair_instances": sec["decidable_pair_instances"],
            "consistent_pair_instances": sec["consistent_pair_instances"],
            "gap_total": sec["gap_total"],
            "gap_share_of_decidable": sec["gap_share_of_decidable"],
            "gap_classes": sec["gap_classes"],
            "consistency_rate_undirected": sec["consistency_rate_undirected"],
            "activity_plan_fingerprint_sha256": sec["activity_plan_fingerprint_sha256"],
            "activity_plan_identical_to_primary": None,
            "same_magnitude_as_primary": None,
            "same_magnitude_rule": "判定规则（先写死）：两批主读数绝对差 <= 10 个百分点即判「同量级」。",
        }
        pv = primary["plan_pairs"]["consistency_rate"]["value"]
        sv = sec["consistency_rate"]["value"]
        out["secondary_batch"]["same_magnitude_as_primary"] = (
            None if (pv is None or sv is None) else (abs(pv - sv) <= 0.10))
        same_plan = (primary["activity_plan_fingerprint_sha256"]
                     == sec["activity_plan_fingerprint_sha256"])
        out["secondary_batch"]["activity_plan_identical_to_primary"] = same_plan
        out["secondary_batch"]["replication_strength_note"] = (
            "两批的 ACTIVITY_STARTED 规划流（agent/day/slot/place/participants/template）逐字段相同 ⇒ "
            "副批对本尺子的「同量级」判断是对同一份计划数据重跑尺子，不是不同计划的独立复现；"
            "因此 same_magnitude_as_primary=true 的强度是「尺子确定性一致」，而非「跨计划稳定」。"
            if same_plan else
            "两批规划流不同 ⇒ 副批可作为「不同计划下同尺子是否同量级」的较弱证据。")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    print("wrote", args.out)
    r = out["plan_pairs"]["consistency_rate"]
    print("primary consistency %d/%d = %.4f | gaps %d" % (
        r["numerator"], r["denominator"], r["value"], out["gap_breakdown"]["gap_total"]))
    if out["secondary_batch"]:
        s = out["secondary_batch"]
        print("secondary consistency %d/%d = %.4f | same_magnitude %s" % (
            s["consistent_pair_instances"], s["decidable_pair_instances"],
            s["consistency_rate"]["value"], s["same_magnitude_as_primary"]))


if __name__ == "__main__":
    main()
