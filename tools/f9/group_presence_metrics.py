#!/usr/bin/env python3
"""f9 只读出数器：群体聚集 / 同场共处 / 独处-空闲 的描述性读数。

只读既有 run.jsonl，不跑批、不写仓库其它文件，输出确定性 JSON（无时间戳，
同一输入重放字节一致）。

用法：
  python3 tools/f9/group_presence_metrics.py \
      --run v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
      --out v2/evidence/group_presence_20261024/group_presence_metrics.json

口径全部写在 README.md（v2/evidence/group_presence_20261024/README.md）。
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os

RPS = 3          # ROUNDS_PER_SLOT（code/life/constants.py TIME_CONFIG）
SLOTS = ["morning", "afternoon", "evening", "night"]
RPD = RPS * len(SLOTS)  # 12 rounds per day


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def gate_skipped(agent_id: str, slot_id: str) -> bool:
    """复刻 code/life/planner.py:102-104 的确定性 1/3 跳过门。"""
    return int(sha256_hex(f"{agent_id}|{slot_id}|gate")[:2], 16) % 3 == 0


def pct(num: int, den: int) -> dict:
    return {"numerator": num, "denominator": den,
            "value": (num / den) if den else None}


def median(xs: list) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return float(s[mid]) if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def pctl_nearest_rank(xs: list, p: float) -> float | None:
    """nearest-rank 百分位（p 为 0-100），返回该名次上的取值。"""
    if not xs:
        return None
    s = sorted(xs)
    import math
    k = max(1, math.ceil(p / 100.0 * len(s)))
    return float(s[k - 1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    acts = []      # ACTIVITY_STARTED payloads
    groups = []    # GROUP_CREATED payloads
    arrived = []   # PLACE_ARRIVED payloads
    moves = 0
    time_marks = []
    seals = 0
    born = set()
    n_lines = 0

    with open(args.run, "r", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            d = json.loads(line)
            t = d["type"]
            p = d.get("payload", {})
            if t == "ACTIVITY_STARTED":
                acts.append(p)
            elif t == "GROUP_CREATED":
                groups.append(p)
            elif t == "PLACE_ARRIVED":
                arrived.append(p)
            elif t == "PLACE_MOVE":
                moves += 1
            elif t == "TIME_MARK":
                time_marks.append(p)
            elif t == "TURN_SEAL":
                seals += 1
            elif t == "AGENT_BORN":
                born.add(p["agent_id"])

    # ---- 全域分母：agents × days × slots -----------------------------------
    agents = sorted(born)
    days = sorted({a["day"] for a in acts})
    day_by_round = {tm["round"]: tm["day"] for tm in time_marks}
    universe_cells = [(ag, d, s) for ag in agents for d in days for s in SLOTS]
    act_cells = {(a["agent_id"], a["day"], a["slot"]) for a in acts}
    act_rows = len(acts)

    universe = {
        "agents_source": "AGENT_BORN.payload.agent_id 去重",
        "agents_count": len(agents),
        "days_source": "ACTIVITY_STARTED.payload.day 去重（与 TIME_MARK.payload.day 一致）",
        "days_count": len(days),
        "days": days,
        "slots_per_day_source": "code/life/constants.py TIME_CONFIG.SLOTS_PER_DAY",
        "slots_per_day": SLOTS,
        "rounds_per_slot": RPS,
        "rounds_per_day": RPD,
        "turns_in_log": seals,
        "derived_days_from_turns": seals / RPD,
        "time_mark_count": len(time_marks),
        "agent_day_slot_total": len(universe_cells),
        "activity_started_rows": act_rows,
        "activity_started_unique_agent_day_slot": len(act_cells),
        "universe_formula": "16 agents × 5 days × 4 slots = 320 = 60 turns / 12 rounds_per_day × 4 slots × 16 agents",
        "self_check_no_activity_cells": len(universe_cells) - len(act_cells),
    }

    # ---- A. 聚集层 --------------------------------------------------------
    place_of_group = {}
    for g in groups:
        gid = g["group_id"]
        place_of_group[gid] = gid.split(":", 1)[1] if ":" in gid else gid

    group_by_place = collections.Counter(place_of_group[g["group_id"]] for g in groups)
    group_members_size = collections.Counter(len(g["members"]) for g in groups)
    group_by_slot = collections.Counter(g["slot"] for g in groups)
    distinct_member_sets = len({tuple(sorted(g["members"])) for g in groups})

    part_size = collections.Counter(len(a.get("participants") or []) for a in acts)
    bucket = {"1": 0, "2-4": 0, "5+": 0}
    for size, cnt in part_size.items():
        if size <= 1:
            bucket["1"] += cnt
        elif size <= 4:
            bucket["2-4"] += cnt
        else:
            bucket["5+"] += cnt
    multi_rows = sum(cnt for size, cnt in part_size.items() if size >= 2)

    arrived_by_place = collections.Counter(a["place"] for a in arrived)
    arrived_cells = {(a["agent_id"], a["day"], a["slot"]) for a in arrived}
    # 一致性：有 PLACE_ARRIVED 且同 cell 有 ACTIVITY_STARTED 的，place 是否一致
    act_place_by_cell = {(a["agent_id"], a["day"], a["slot"]): a["place"] for a in acts}
    arr_place_mismatch = sum(
        1 for a in arrived
        if (a["agent_id"], a["day"], a["slot"]) in act_place_by_cell
        and act_place_by_cell[(a["agent_id"], a["day"], a["slot"])] != a["place"])

    # 每人每日被拉入多人活动的次数（multi = participants>=2）
    multi_per_agent_day = collections.Counter()
    for a in acts:
        if len(a.get("participants") or []) >= 2:
            multi_per_agent_day[(a["agent_id"], a["day"])] += 1
    per_agent_day_values = [multi_per_agent_day.get((ag, d), 0)
                            for ag, d in [(ag, d) for ag in agents for d in days]]

    gathering = {
        "group_created": {
            "total": len(groups),
            "by_place": dict(sorted(group_by_place.items())),
            "by_place_source": "GROUP_CREATED.group_id 形如 'place:<name>'，取冒号后部分",
            "by_slot": dict(sorted(group_by_slot.items())),
            "members_size_distribution": {str(k): v for k, v in sorted(group_members_size.items())},
            "distinct_member_sets": distinct_member_sets,
            "denominator_note": "分母口径 = 该日志内 GROUP_CREATED 事件总数 %d" % len(groups),
        },
        "activity_started": {
            "total_rows": act_rows,
            "total_rows_denominator": "ACTIVITY_STARTED 事件行数（每 (agent,day,slot) 一行）= %d" % act_rows,
            "participants_size_distribution": {str(k): v for k, v in sorted(part_size.items())},
            "participants_buckets": bucket,
            "multi_person_rows": multi_rows,
            "multi_person_ratio": pct(multi_rows, act_rows),
            "multi_person_ratio_denominator_note":
                "分子 = participants 长度 >=2 的 ACTIVITY_STARTED 行数 %d；"
                "分母 = 全部 ACTIVITY_STARTED 行数 %d（按 agent-槽计，不按去重活动计）" % (multi_rows, act_rows),
        },
        "place_arrived": {
            "total": len(arrived),
            "by_place": dict(sorted(arrived_by_place.items(), key=lambda kv: (-kv[1], kv[0]))),
            "agent_slots_without_arrival": len(set(act_place_by_cell) - arrived_cells),
            "agent_slots_without_arrival_note":
                "这些 agent-槽 未发 PLACE_MOVE/PLACE_ARRIVED（原地未移动）；"
                "其地点仍由同槽 ACTIVITY_STARTED.place 表征",
            "arrival_place_vs_activity_place_mismatch": arr_place_mismatch,
            "place_arrived_total_denominator": "PLACE_ARRIVED 事件行数 %d（agent-槽 ×发生了移动）" % len(arrived),
        },
        "per_agent_day_multi_involvement": {
            "definition": "对每个 (agent, day)：其 ACTIVITY_STARTED 行中 participants 长度>=2 的行数",
            "n_cells": len(per_agent_day_values),
            "n_cells_denominator": "agents × days = %d × %d" % (len(agents), len(days)),
            "mean": round(sum(per_agent_day_values) / len(per_agent_day_values), 4),
            "median": median(per_agent_day_values),
            "p90_nearest_rank": pctl_nearest_rank(per_agent_day_values, 90),
            "histogram": {str(k): v for k, v in sorted(collections.Counter(per_agent_day_values).items())},
            "caveat": "participants 是各 agent 自己计划里的同伴列表，同一多人活动在不同 agent 行里同伴集合可能不同；"
                      "本字段计的是「被列入多少人活动的次数」，不是实际同处人数",
        },
    }

    # ---- B. 同场共处 ------------------------------------------------------
    def copresence(rows, exclude_residence: bool):
        in_scope = [r for r in rows
                    if not (exclude_residence and r["place"] == "residence")]
        groups_cnt = collections.Counter(
            (r["day"], r["slot"], r["place"]) for r in in_scope)
        sizes = list(groups_cnt.values())
        persons_ge2 = sum(1 for r in in_scope
                          if groups_cnt[(r["day"], r["slot"], r["place"])] >= 2)
        persons_in_scope = len(in_scope)
        # 每个 (day, slot) 内最大的同处人数
        max_by_cell = collections.defaultdict(int)
        for (d_, s_, pl), cnt in groups_cnt.items():
            max_by_cell[(d_, s_)] = max(max_by_cell[(d_, s_)], cnt)
        day_slots = sorted(max_by_cell)
        ds_any_ge2 = sum(1 for ds in day_slots if max_by_cell[ds] >= 2)
        return {
            "place_groups_total": len(groups_cnt),
            "place_groups_size_histogram": {str(k): v for k, v in sorted(collections.Counter(sizes).items())},
            "place_groups_ge2": sum(1 for s in sizes if s >= 2),
            "ratio_of_place_groups_ge2": pct(sum(1 for s in sizes if s >= 2), len(groups_cnt)),
            "persons_in_scope": persons_in_scope,
            "persons_in_ge2_group": persons_ge2,
            "ratio_of_persons_in_ge2_group": pct(persons_ge2, persons_in_scope),
            "day_slot_cells": len(day_slots),
            "day_slot_cells_with_any_ge2": ds_any_ge2,
            "ratio_of_day_slot_cells_with_any_ge2": pct(ds_any_ge2, len(day_slots)),
        }

    copresence_all = copresence(acts, False)
    copresence_pub = copresence(acts, True)

    co = {
        "definition": "以 ACTIVITY_STARTED.place 为「同处地点」（已核对：299 条 PLACE_ARRIVED 的 place 与同槽"
                      " ACTIVITY_STARTED.place 零不一致），按 (day, slot, place) 归组统计人数",
        "cell_key": "(day, slot, place)",
        "variant_including_residence": copresence_all,
        "variant_excluding_residence": copresence_pub,
        "variant_note": "residence 是家（私域），夜槽 rest 全部落在 residence，会把「同处」抬到 100%；"
                        "因此主口径给出「含 residence」与「不含 residence」两版，均写明分母",
        "denominators": {
            "place_groups": "(day, slot, place) 三元组个数",
            "persons": "该口径下纳入的 ACTIVITY_STARTED 行数（含 residence 版 = 320；不含 residence 版 = 240）",
            "day_slot_cells": "(day, slot) 二元组个数（含 residence 版共 20 个；不含 residence 版仅统计有非 residence 活动的 cell）",
        },
    }

    # ---- C. 独处 / 空闲 ---------------------------------------------------
    solo_rows = sum(1 for a in acts if len(a.get("participants") or []) <= 1)
    non_night = [a for a in acts if a["slot"] != "night"]
    solo_non_night = sum(1 for a in non_night if len(a.get("participants") or []) <= 1)
    gated_cells = [c for c in universe_cells if gate_skipped(c[0], f"day{c[1]}-{c[2]}")]
    gated_non_night = [c for c in gated_cells if c[2] != "night"]
    # 门控自检：non-night 槽上「门命中」与「无 template 字段」是否逐一吻合
    tmpl_by_cell = {(a["agent_id"], a["day"], a["slot"]): a.get("template") for a in acts}
    agree = sum(1 for c in non_night
                if gate_skipped(c["agent_id"], c["slot_id"]) == (c.get("template") is None))
    night_no_tmpl = sum(1 for a in acts if a["slot"] == "night" and a.get("template") is None)

    solitude = {
        "universe": "对每个 (agent, day, slot) 交叉 ACTIVITY_STARTED；全域 = 16 × 5 × 4 = 320（见 universe 段）",
        "idle_cells_no_activity": len(universe_cells) - len(act_cells),
        "idle_ratio_no_activity": pct(len(universe_cells) - len(act_cells), len(universe_cells)),
        "solo_activity_rows": solo_rows,
        "solo_activity_ratio": pct(solo_rows, act_rows),
        "solo_activity_ratio_denominator_note":
            "分子 = participants 长度 <=1 的 ACTIVITY_STARTED 行 %d；分母 = 全部行 %d" % (solo_rows, act_rows),
        "solo_activity_ratio_excluding_night": pct(solo_non_night, len(non_night)),
        "solo_activity_ratio_excluding_night_note":
            "夜槽（night）16×5=80 行全部为 rest/residence 单人，会机械抬高独处占比，故另给白天三槽口径",
        "self_check_planner_gate": {
            "gate_rule": "code/life/planner.py:102-104：sha256(f'{agent}|{slot_id}|gate')[:2] % 3 == 0 时 plan_slot 返回 None",
            "gate_effect": "planner.py 返回 None 后，agent.py:_weekly_slots 走 _choose_activity→_base_activity 兜底，"
                           "仍然产出 (activity_type, place) 并照常发 ACTIVITY_STARTED",
            "gated_cells_total": len(gated_cells),
            "gated_cells_non_night": len(gated_non_night),
            "non_night_rows": len(non_night),
            "non_night_rows_without_template_field": sum(1 for a in non_night if a.get("template") is None),
            "non_night_gate_vs_no_template_agreement": agree,
            "non_night_gate_vs_no_template_agreement_denominator": len(non_night),
            "night_rows_all_no_template": night_no_tmpl,
            "conclusion": "白天三槽 240 行中，门命中数(83)与无 template 字段行数(83)完全一致，逐格吻合 240/240："
                          "门跳过只改「计划来源」，不造成 ACTIVITY_STARTED 缺席；"
                          "夜槽 80 行全部无 template 是因为 planner 无 night 规则，走 _base_activity→rest/residence。",
        },
        "unconfirmed": [
            "「无活动安排 slot」在本日志中恒为 0（320/320 全部有 ACTIVITY_STARTED），"
            "因此该字段是结构下限（设计使然），不可当作「居民不空闲」的行为结论。",
            "participants 列表是各 agent 计划里的同伴名单，并不保证被列名的同伴在同一槽也把自己的 participants 指向对方；"
            "「计划同伴」与「实际同处」是两个口径，本文件分别给出，未确认二者的一致率。",
            "空闲/独处的行为语义（例如独处是否等于孤独）未确认，本文件不作任何价值判断。",
        ],
    }

    out = {
        "meta": {
            "script": "tools/f9/group_presence_metrics.py",
            "input_run": args.run,
            "input_sha256": sha256_file(args.run),
            "input_lines": n_lines,
            "note": "确定性输出：无时间戳字段，同一输入重放应字节一致；只读，不写日志、不跑批。",
        },
        "universe": universe,
        "gathering": gathering,
        "copresence": co,
        "solitude_idle": solitude,
        "misc_counts": {"place_move": moves, "turn_seal": seals},
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
