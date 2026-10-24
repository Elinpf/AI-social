#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独处/空闲维度的三把尺子出数器（纯只读、零跑批、零 LLM、确定性输出）。

口径来自（先写口径后出数，读数算出后不得回改口径）：
    team-workspace/solitude/round1-prereg.md

统计单位（钉死）：
    U细胞  = (day, slot, agent) 笛卡尔积 = 5×4×16 = 320        -> S-1 分母
    P对细胞 = C(16,2)=120 对 × 20 slot-cell = 2400              -> S-2 分母
    A实例  = ACTIVITY_STARTED 实例（按 activity_type 过滤）      -> S-3 分母

三个尺子：
    S1_solitude_share        独处占比（place 主口径 / joint 保守副口径，两个都出）
    S2_copresence_pairshare  同场共处（先做可重建性评估，不达标就写 NOT_RECONSTRUCTABLE）
    S3_leisure_to_social     空闲→社交（主口径槽级状态归因 + 两个弱化口径）

另出诊断：
    diag_slot_level   (a) 有行为/状态证据 vs (b) 日志空洞（U细胞级）
    diag_round_level  round 级空洞（320×3=960 子细胞），因为 ACTIVITY_STARTED 是调度骨架事件
    diag_density      每细胞 OBSERVATION / NEED_UPDATE 密度分布

用法：
    python3 tools/solitude/solitude_metrics.py \
        --log v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
        --meta v2/evidence/run_d27_C_n16r60_seed42/meta.json \
        --out /tmp/readings.json        # --out 省略则打印到 stdout

退出码：0 正常 / 2 输入缺失或无法解析 / 3 机制闸失败（M1/M4 硬失败）
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path

DAYS = [0, 1, 2, 3, 4]
SLOTS = ["morning", "afternoon", "evening", "night"]
ROUNDS_PER_SLOT = 3

# 机制闸门槛（写死，来自口径卡 §5）
M2_ACT_COVERAGE_REQUIRED = 1.0
M3_PLACE_COVERAGE_REQUIRED = 1.0
M1_DEGRADED_FORBIDDEN = 0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frac(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="run.jsonl 路径（唯一数据源）")
    ap.add_argument("--meta", default=None, help="meta.json 路径（用于 M1 机制闸交叉校验，可选）")
    ap.add_argument("--out", default=None, help="输出 json 路径；省略则 stdout")
    args = ap.parse_args()

    log_path = Path(args.log)
    if not log_path.is_file():
        print(f"[solitude] 输入缺失: {log_path}", file=sys.stderr)
        return 2

    # ---------------- 单遍读取 ----------------
    lines = 0
    agents: set[str] = set()
    act: dict[tuple, dict] = {}          # (day,slot,agent) -> ACTIVITY_STARTED payload
    act_types: dict[str, int] = {}
    arrived: dict[tuple, dict] = {}      # (day,slot,agent) -> PLACE_ARRIVED payload
    moves: dict[tuple, list] = {}        # (day,slot,agent) -> [PLACE_MOVE payload]
    msg_events: list[dict] = []          # MSG_DM / MSG_PUBLIC payloads
    obs_by_cell: dict[tuple, int] = {}   # (day,slot,observer) -> OBSERVATION 条数
    need_by_cell: dict[tuple, int] = {}  # (day,slot,agent)   -> NEED_UPDATE 条数
    agent_events_by_round: dict[tuple, int] = {}  # (day,slot,agent,round) -> agent 归因事件数
    days_seen: set[int] = set()
    slots_seen: set[str] = set()
    rounds_seen: set[int] = set()

    with log_path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            lines += 1
            ev = json.loads(raw)
            t = ev.get("type")
            pl = ev.get("payload") or {}
            rnd = ev.get("round")
            if isinstance(rnd, int):
                rounds_seen.add(rnd)

            day = pl.get("day")
            slot = pl.get("slot")
            if day is not None:
                days_seen.add(day)
            if slot is not None:
                slots_seen.add(slot)

            if t == "AGENT_BORN":
                a = pl.get("agent_id")
                if a:
                    agents.add(a)
                continue

            if t == "ACTIVITY_STARTED":
                key = (day, slot, pl.get("agent_id"))
                act[key] = {
                    "activity_type": pl.get("activity_type"),
                    "place": pl.get("place"),
                    "participants": list(pl.get("participants") or []),
                    "day_type": pl.get("day_type"),
                    "start_tick": pl.get("start_tick"),
                }
                at = pl.get("activity_type")
                act_types[at] = act_types.get(at, 0) + 1
            elif t == "PLACE_ARRIVED":
                arrived[(day, slot, pl.get("agent_id"))] = {
                    "place": pl.get("place"),
                }
            elif t == "PLACE_MOVE":
                moves.setdefault((day, slot, pl.get("agent_id")), []).append(
                    {
                        "from_place": pl.get("from_place"),
                        "to_place": pl.get("to_place"),
                        "travel_ticks": pl.get("travel_ticks"),
                    }
                )
            elif t in ("MSG_DM", "MSG_PUBLIC"):
                msg_events.append(pl)
            elif t == "OBSERVATION":
                k = (day, slot, pl.get("observer"))
                obs_by_cell[k] = obs_by_cell.get(k, 0) + 1
                if isinstance(rnd, int) and pl.get("observer"):
                    kk = (day, slot, pl.get("observer"), rnd)
                    agent_events_by_round[kk] = agent_events_by_round.get(kk, 0) + 1
            elif t == "NEED_UPDATE":
                k = (day, slot, pl.get("agent_id"))
                need_by_cell[k] = need_by_cell.get(k, 0) + 1

            # round 级空洞检查：只统计"agent 归因"事件（ACTIVITY_*/NEED_UPDATE/OBSERVATION/
            # PLACE_*/SLEEP_* 这几类，排除 MEMORY_* 这类系统内部记账事件）
            if isinstance(rnd, int):
                who = pl.get("agent_id") or pl.get("observer")
                if who and t in (
                    "ACTIVITY_STARTED",
                    "ACTIVITY_COMPLETED",
                    "NEED_UPDATE",
                    "OBSERVATION",
                    "PLACE_MOVE",
                    "PLACE_ARRIVED",
                    "SLEEP_STARTED",
                    "SLEEP_COMPLETED",
                    "SKILL_PRACTICE",
                    "GOAL_PROGRESS",
                ):
                    kk = (day, slot, who, rnd)
                    agent_events_by_round[kk] = agent_events_by_round.get(kk, 0) + 1

    agents_sorted = sorted(agents)
    n_agents = len(agents_sorted)
    n_days = len(days_seen)
    n_slots = len(slots_seen)
    n_cells = n_days * n_slots * n_agents

    # ---------------- 重建在场（口径卡 §3） ----------------
    place_of: dict[tuple, str | None] = {}
    for k, v in act.items():
        place_of[k] = v["place"]

    arrive_match = arrive_total = 0
    for k, a in arrived.items():
        a_place = a.get("place")
        if k in act:
            arrive_total += 1
            if a_place == act[k]["place"]:
                arrive_match += 1

    multi_place_cells = 0
    for (d, s, a), mv in moves.items():
        tos = {m["to_place"] for m in mv}
        if len(tos) > 1:
            multi_place_cells += 1

    travel_ticks = sorted({m["travel_ticks"] for mv in moves.values() for m in mv})

    # ---------------- S-1 独处占比 ----------------
    msg_involved: set[tuple] = set()
    msg_involved_roster: set[tuple] = set()  # 敏感性副口径：一律用 participants 名单
    dm_from_cells: dict[tuple, int] = {}
    dm_roster_wider_than_pair = 0
    for pl in msg_events:
        d, s = pl.get("day"), pl.get("slot")
        participants = [w for w in (pl.get("participants") or []) if w]
        who = list(participants)
        if "from" in pl:  # MSG_DM
            who = [pl["from"], pl.get("to")]
            k = (d, s, pl["from"])
            dm_from_cells[k] = dm_from_cells.get(k, 0) + 1
            if len(set(participants)) > 2:
                dm_roster_wider_than_pair += 1
        elif "author" in pl:  # MSG_PUBLIC
            who = participants or [pl.get("author")]
        for w in who:
            if w:
                msg_involved.add((d, s, w))
        for w in (participants or who):
            if w:
                msg_involved_roster.add((d, s, w))

    cop_place: set[tuple] = set()
    for d in DAYS:
        for s in SLOTS:
            by_place: dict[str, list[str]] = {}
            for a in agents_sorted:
                k = (d, s, a)
                p = place_of.get(k)
                if p:
                    by_place.setdefault(p, []).append(a)
            for p, group in by_place.items():
                if len(group) > 1:
                    for a in group:
                        cop_place.add((d, s, a))

    joint: set[tuple] = set()
    for k, v in act.items():
        if len(v["participants"]) > 1:
            for a in v["participants"]:
                if a:
                    joint.add((k[0], k[1], a))

    universe = [(d, s, a) for d in DAYS for s in SLOTS for a in agents_sorted]
    num_place = [c for c in universe if c not in msg_involved and c not in cop_place]
    num_joint = [c for c in universe if c not in msg_involved and c not in joint]
    num_place_roster = [c for c in universe if c not in msg_involved_roster and c not in cop_place]

    # ---------------- S-2 同场共处 ----------------
    pair_num = 0
    pair_by_place: dict[str, int] = {}
    pair_by_place_slot: dict[str, int] = {}
    for d in DAYS:
        for s in SLOTS:
            by_place: dict[str, list[str]] = {}
            for a in agents_sorted:
                p = place_of.get((d, s, a))
                if p:
                    by_place.setdefault(p, []).append(a)
            for p, group in by_place.items():
                n = len(group)
                pairs = n * (n - 1) // 2
                pair_num += pairs
                pair_by_place[p] = pair_by_place.get(p, 0) + pairs
                key = f"{p}|{s}"
                pair_by_place_slot[key] = pair_by_place_slot.get(key, 0) + pairs

    pair_universe = (n_agents * (n_agents - 1) // 2) * (n_days * n_slots)

    # ---------------- S-3 空闲→社交 ----------------
    leisure_keys = [k for k, v in act.items() if v["activity_type"] == "leisure"]
    idle_keys = [k for k, v in act.items() if v["activity_type"] == "idle"]
    dm_in_leisure = sum(dm_from_cells.get(k, 0) for k in leisure_keys)
    leisure_with_dm = [k for k in leisure_keys if dm_from_cells.get(k, 0) > 0]

    trigger_enum: dict[str, int] = {}
    for pl in msg_events:
        if "from" in pl:
            ctx = pl.get("ctx") or {}
            tr = ctx.get("trigger")
            trigger_enum[str(tr)] = trigger_enum.get(str(tr), 0) + 1

    # ---------------- 诊断 (a)/(b) ----------------
    evidence_cells = [c for c in universe if c in act or obs_by_cell.get(c) or need_by_cell.get(c)]
    hole_cells = [c for c in universe if c not in act and not obs_by_cell.get(c) and not need_by_cell.get(c)]
    hole_in_s1_place = [c for c in num_place if c in set(hole_cells)]
    hole_in_s1_joint = [c for c in num_joint if c in set(hole_cells)]

    # round 级空洞
    slot_round_base = {(d, s): (d * len(SLOTS) + SLOTS.index(s)) * ROUNDS_PER_SLOT for d in DAYS for s in SLOTS}
    round_subcells = []
    for d in DAYS:
        for s in SLOTS:
            r0 = slot_round_base[(d, s)]
            for a in agents_sorted:
                for i in range(ROUNDS_PER_SLOT):
                    round_subcells.append((d, s, a, r0 + i))
    round_holes = [k for k in round_subcells if agent_events_by_round.get(k, 0) == 0]

    # 密度分布（只报分布刻度，不做插值）
    obs_density = sorted(obs_by_cell.get(c, 0) for c in universe)
    need_density = sorted(need_by_cell.get(c, 0) for c in universe)

    def pctl(sorted_list, q):
        if not sorted_list:
            return None
        idx = min(len(sorted_list) - 1, int(round(q * (len(sorted_list) - 1))))
        return sorted_list[idx]

    # ---------------- 机制闸 ----------------
    log_sha = sha256_file(log_path)
    meta = None
    if args.meta:
        mp = Path(args.meta)
        if mp.is_file():
            meta = json.loads(mp.read_text(encoding="utf-8"))

    gates = {}
    gates["M1_log_integrity"] = {
        "line_count": lines,
        "meta_events": (meta or {}).get("events"),
        "line_count_matches_meta": (meta or {}).get("events") == lines if meta else None,
        "computed_sha256": log_sha,
        "meta_run_sha256": (meta or {}).get("run_sha256"),
        "sha256_matches_meta": (meta or {}).get("run_sha256") == log_sha if meta else None,
        "meta_degraded_calls": (meta or {}).get("degraded_calls"),
        "degraded_ok": (meta or {}).get("degraded_calls") == M1_DEGRADED_FORBIDDEN if meta else None,
        "pass": bool(
            meta
            and (meta.get("events") == lines)
            and (meta.get("run_sha256") == log_sha)
            and (meta.get("degraded_calls") == M1_DEGRADED_FORBIDDEN)
        ),
    }

    act_cells_with_place = sum(1 for k, v in act.items() if v.get("place"))
    cells_expected = len(DAYS) * len(SLOTS) * n_agents
    act_cov = frac(len(act), cells_expected) or 0.0
    gates["M2_unit_coverage"] = {
        "activity_started_cells": len(act),
        "cells_expected": cells_expected,
        "coverage": act_cov,
        "required": M2_ACT_COVERAGE_REQUIRED,
        "pass": act_cov >= M2_ACT_COVERAGE_REQUIRED,
    }

    place_cov = frac(act_cells_with_place, cells_expected) or 0.0
    arrive_cov = frac(arrive_match, arrive_total) if arrive_total else None
    gates["M3_place_coverage"] = {
        "place_nonempty_cells": act_cells_with_place,
        "place_coverage": place_cov,
        "arrived_vs_activity_pairs": arrive_total,
        "arrived_place_matches_activity_place": arrive_match,
        "arrived_match_rate": arrive_cov,
        "cells_with_multiple_move_targets": multi_place_cells,
        "pass": bool(
            place_cov >= M3_PLACE_COVERAGE_REQUIRED
            and (arrive_cov is None or arrive_cov >= M3_PLACE_COVERAGE_REQUIRED)
            and multi_place_cells == 0
        ),
    }

    gates["M4_identity"] = {
        "n_agents": n_agents,
        "agents": agents_sorted,
        "days": sorted(days_seen),
        "slots": sorted(slots_seen),
        "n_slot_cells": len(days_seen) * len(slots_seen),
        "rounds_seen_min": min(rounds_seen) if rounds_seen else None,
        "rounds_seen_max": max(rounds_seen) if rounds_seen else None,
        "rounds_expected": len(days_seen) * len(slots_seen) * ROUNDS_PER_SLOT,
        "pass": bool(
            n_agents == 16
            and sorted(days_seen) == DAYS
            and sorted(slots_seen) == sorted(SLOTS)
            and rounds_seen
            and max(rounds_seen) == len(days_seen) * len(slots_seen) * ROUNDS_PER_SLOT - 1
        ),
    }

    gates["M5_no_extrapolation"] = {
        "single_source_file": str(args.log),
        "source_sha256": log_sha,
        "mock_or_imputed_values": 0,
        "interpolation_used": False,
        "pass": True,
    }

    gates_pass = all(v.get("pass") for v in gates.values())

    # ---------------- 读数装配 ----------------
    s1_place_value = frac(len(num_place), cells_expected)
    s1_joint_value = frac(len(num_joint), cells_expected)
    s2_value = frac(pair_num, pair_universe)
    s3_value = frac(dm_in_leisure, len(leisure_keys))
    s3a_value = frac(len(leisure_with_dm), len(leisure_keys))

    hole_share_slot = frac(len(hole_cells), len(universe))
    hole_share_round = frac(len(round_holes), len(round_subcells))

    reconstructable = gates["M3_place_coverage"]["pass"] and gates["M2_unit_coverage"]["pass"]

    readings = {
        "schema": "solitude-metrics/round1",
        "prereg": "team-workspace/solitude/round1-prereg.md",
        "generator": "tools/solitude/solitude_metrics.py",
        "input": {
            "log": str(args.log),
            "log_sha256": log_sha,
            "meta": str(args.meta) if args.meta else None,
            "lines": lines,
            "generator_sha256": sha256_file(Path(__file__).resolve()),
        },
        "units": {
            "resident_slot_cells": cells_expected,
            "pair_slot_cells": pair_universe,
            "round_subcells": len(round_subcells),
            "days": sorted(days_seen),
            "slots": SLOTS,
            "rounds_per_slot": ROUNDS_PER_SLOT,
            "n_agents": n_agents,
        },
        "activity_type_enumeration": dict(sorted(act_types.items(), key=lambda kv: (-kv[1], str(kv[0])))),
        "activity_type_note": "枚举取自数据实测；本批不存在 activity_type='idle'，故 S-3 的 idle 类为空集",
        "gates": gates,
        "gates_pass": gates_pass,
        "S1_solitude_share": {
            "unit": "resident x slot-cell",
            "denominator": cells_expected,
            "numerator": len(num_place),
            "value": s1_place_value,
            "definition": "既非 MSG_DM from/to、也不在 MSG_PUBLIC participants 内，且该 slot 未与他人同处（place 主口径：同 slot 重建地点相同的其他居民≥1）",
            "co_presence_rule": "place",
            "fields": [
                "MSG_DM.from",
                "MSG_DM.to",
                "MSG_PUBLIC.participants",
                "ACTIVITY_STARTED.place",
                "ACTIVITY_STARTED.participants",
            ],
            "source_file": str(args.log),
            "source_sha256": log_sha,
            "variant_joint": {
                "unit": "resident x slot-cell",
                "denominator": cells_expected,
                "numerator": len(num_joint),
                "value": s1_joint_value,
                "co_presence_rule": "joint（保守副口径：ACTIVITY_STARTED.participants 长度>1）",
                "note": "两个口径必须并列，不二选一；joint 只在显式联合活动时判同处，忽略同场地偶遇",
            },
            "variant_participants_roster": {
                "unit": "resident x slot-cell",
                "denominator": cells_expected,
                "numerator": len(num_place_roster),
                "value": frac(len(num_place_roster), cells_expected),
                "note": "敏感性副口径（不替代主口径）：MSG 一律按 participants 名单判是否卷入对话。实测有 53 条 MSG_DM 的 participants 是 8 人场面名单、而 from/to 只有 2 人，故本口径把「在场旁听」也算作不独处；主口径只看 from/to。两值差即为「同场旁听」的量级。",
                "dm_events_with_roster_wider_than_pair": dm_roster_wider_than_pair,
            },
            "numerator_activity_types": dict(
                sorted(
                    {
                        t: sum(1 for c in num_place if act.get(c, {}).get("activity_type") == t)
                        for t in {act.get(c, {}).get("activity_type") for c in num_place}
                        if t is not None
                    }.items(),
                    key=lambda kv: (-kv[1], kv[0]),
                )
            ),
            "numerator_detail": [
                {
                    "day": c[0],
                    "slot": c[1],
                    "agent": c[2],
                    "activity_type": act.get(c, {}).get("activity_type"),
                    "place": act.get(c, {}).get("place"),
                    "participants": act.get(c, {}).get("participants"),
                }
                for c in num_place
            ],
        },
        "S2_copresence_pairshare": {
            "unit": "resident-pair x slot-cell",
            "denominator": pair_universe,
            "numerator": pair_num,
            "value": s2_value,
            "definition": "同 (day,slot) 下两居民重建地点相同的对数量之和",
            "fields": ["ACTIVITY_STARTED.place", "PLACE_ARRIVED.place", "PLACE_MOVE.from_place", "PLACE_MOVE.to_place"],
            "source_file": str(args.log),
            "source_sha256": log_sha,
            "reconstructable": reconstructable,
            "reconstructability": {
                "place_coverage": gates["M3_place_coverage"]["place_coverage"],
                "arrived_match_rate": gates["M3_place_coverage"]["arrived_match_rate"],
                "cells_with_multiple_move_targets": multi_place_cells,
                "travel_ticks_values": travel_ticks,
                "slot_length_ticks": 12,
                "caveats": [
                    "无 PLACE_LEAVE / 离开事件：slot 内 presence 只能按「到达后驻留至 slot 末」处理，属上界假设",
                    "跨 slot 移动耗时 travel_ticks=1 tick（slot 长 12 tick），到达前该居民仍在上一个地点，误差窗口有界但不可消除",
                    "MSG place 与参与人活动地点可不一致（DM 可远距），故同场判定只用 ACTIVITY_STARTED.place，不用 MSG.place",
                ],
            },
            "place_granularity_caveat": {
                "distinct_places_in_log": len(pair_by_place),
                "pair_breakdown_by_place": dict(sorted(pair_by_place.items(), key=lambda kv: (-kv[1], kv[0]))),
                "top_place_slot": [
                    {"place_slot": k, "pairs": v}
                    for k, v in sorted(pair_by_place_slot.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
                ],
                "share_from_night_at_residence": frac(pair_by_place_slot.get("residence|night", 0), pair_num or 0),
                "note": "地点只有十来个粗粒度标签，全体居民夜间都记在 residence => 夜眠贡献的居民对属「结构性同处伪影」，不是互动。报告必须把这块单列，禁止把 S-2 直接读成社交密度。",
            },
            "note": "若 reconstructable=false，本尺子结论必须写「不可重建」，value 仅供内部核对、不得写进报告结论",
        },
        "S3_leisure_to_social": {
            "unit": "ACTIVITY_STARTED instance（activity_type in {leisure, idle}）",
            "denominator": len(leisure_keys) + len(idle_keys),
            "numerator": dm_in_leisure,
            "value": s3_value,
            "definition": "主口径：发起人当 slot 的 activity_type == leisure 的 MSG_DM 条数 / leisure 实例数（槽级状态归因）",
            "activity_types_used": {"leisure": len(leisure_keys), "idle": len(idle_keys)},
            "fields": [
                "MSG_DM.from",
                "MSG_DM.day",
                "MSG_DM.slot",
                "MSG_DM.ctx.trigger",
                "ACTIVITY_STARTED.activity_type",
            ],
            "source_file": str(args.log),
            "source_sha256": log_sha,
            "attribution_limitations": [
                "activity_type 无 'idle' 取值（实测 7 类），idle 类为空集，未与其他类合并",
                "MSG_DM.ctx.trigger 的实测枚举无 leisure/idle 类，trigger 不能用于归因（枚举见 msg_dm_trigger_enumeration）",
                "activity 是 slot 级状态，msg 精确时刻未知，故为「leisure 槽内发起」而非「leisure 瞬间发起」",
                f"分母仅 {len(leisure_keys)} 个实例，单 seed 只可给点估计，不设通过/不通过阈值",
            ],
            "variant_a_share_instances_with_dm": {
                "unit": "leisure instance",
                "denominator": len(leisure_keys),
                "numerator": len(leisure_with_dm),
                "value": s3a_value,
            },
            "variant_b_dm_per_leisure_instance": {
                "unit": "MSG_DM / leisure instance",
                "denominator": len(leisure_keys),
                "numerator": dm_in_leisure,
                "value": s3_value,
                "note": "与主口径分子分母相同，此处显式标为「比率」而非「占比」，防止被读成转化率",
            },
        },
        "diagnosis_solitude_quality": {
            "unit": "resident x slot-cell",
            "a_evidence_cells": len(evidence_cells),
            "b_hole_cells": len(hole_cells),
            "b_hole_share": hole_share_slot,
            "b_hole_in_S1_numerator_place": len(hole_in_s1_place),
            "b_hole_in_S1_numerator_place_share": frac(len(hole_in_s1_place), len(num_place) or 0),
            "b_hole_in_S1_numerator_joint": len(hole_in_s1_joint),
            "definition_a": "该细胞存在 ACTIVITY_STARTED 或 OBSERVATION(observer) 或 NEED_UPDATE(agent_id) 任一事件",
            "definition_b": "该细胞上述事件一个都没有（日志空洞）",
            "round_level": {
                "unit": "resident x slot-cell x round",
                "denominator": len(round_subcells),
                "numerator_zero_event_subcells": len(round_holes),
                "value": hole_share_round,
                "zero_event_subcells": [
                    {"day": k[0], "slot": k[1], "agent": k[2], "round": k[3]} for k in round_holes
                ],
                "why": "ACTIVITY_STARTED 由调度器每 slot 必发，属机制骨架而非行为证据；round 级空洞按 agent 归因事件计，用于区分「有骨架」与「真有内容」",
            },
            "density": {
                "observation_per_cell": {
                    "min": obs_density[0] if obs_density else None,
                    "p25": pctl(obs_density, 0.25),
                    "median": pctl(obs_density, 0.5),
                    "p75": pctl(obs_density, 0.75),
                    "max": obs_density[-1] if obs_density else None,
                    "cells_with_zero": sum(1 for x in obs_density if x == 0),
                },
                "need_update_per_cell": {
                    "min": need_density[0] if need_density else None,
                    "p25": pctl(need_density, 0.25),
                    "median": pctl(need_density, 0.5),
                    "p75": pctl(need_density, 0.75),
                    "max": need_density[-1] if need_density else None,
                    "cells_with_zero": sum(1 for x in need_density if x == 0),
                },
            },
        },
        "msg_dm_trigger_enumeration": dict(sorted(trigger_enum.items(), key=lambda kv: (-kv[1], kv[0]))),
        "verdict_rule_applied": {
            "rule": "口径卡 §7：M1-M5 全通过 + S-1/S-2 分母 100% 覆盖 + 诊断(b)<5% -> 能判（点估计级）；否则该尺子只能描述",
            "gates_pass": gates_pass,
            "S1_can_judge": bool(gates_pass and s1_place_value is not None and (hole_share_slot or 0) < 0.05),
            "S2_can_judge": bool(gates_pass and reconstructable),
            "S3_can_judge": False,
            "S3_reason": "分母仅 leisure 实例（极小），且 trigger 无 leisure/idle 归因通道、activity 为 slot 级 -> 只可描述，不可作为判据",
            "solitude_quality_can_judge": False,
            "solitude_quality_reason": "日志无「独处时在做什么/感受如何」的语义字段（activity_type 仅 7 类、leisure 23 实例），只能给独处频次/共处频次的点估计",
        },
        "effect_band": {
            "policy": "单 seed 只写点估计；不写显著、不写置信区间、不做跨批比较（口径卡 §6 E0）",
            "S1_band": None
            if s1_place_value is None
            else ("<5%" if s1_place_value < 0.05 else ("5%-20%" if s1_place_value <= 0.20 else ">20%")),
            "S2_band": None
            if s2_value is None
            else ("<20%" if s2_value < 0.20 else ("20%-60%" if s2_value <= 0.60 else ">60%")),
            "S3_threshold": "不设阈值",
        },
    }

    text = json.dumps(readings, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[solitude] wrote {args.out}")
    else:
        sys.stdout.write(text)

    hard_fail = not gates["M1_log_integrity"]["pass"] or not gates["M4_identity"]["pass"]
    return 3 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
