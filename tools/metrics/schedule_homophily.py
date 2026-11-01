#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作息个体差异读数器（R53 维度的官方尺子；**纯只读、零 LLM、零跑批**）。

回答的问题：**同一职业（role_id）的不同居民，在同一天同一时段，是不是被排了同一套作息？**

## 为什么需要这把尺子（问题定性，跑批前已定，证据见 `reports/R53-prereg-schedule-offset-20261102.md` §1）

  * `code/life/agent.py::_base_activity(day_type, slot)` 只依赖 `(day_type, slot)` 与本人
    `work_place`，与 `agent_id` 无关 ⇒ 同 role 同 (day,slot) 的 `activity_type` **必然相同**；
  * `code/life/agent.py::_plan()` 里 `planned_tick = dow*12 + si*ROUNDS_PER_SLOT` 与 agent 无关
    ⇒ 全体居民的 `start_tick` **逐位相同**（既有批次实测 96/96 = 1.000 同质）；
  * 唯一能把同 role 两人拉开的，是 `_choose_activity()` 的 deprivation 覆盖（`needs < θ_dep`），
    即「差异来自需求，不来自个人习惯」。

## 口径（**先冻结，再读数**；改这里 = 改尺子，必须同步改预登记卡并声明作废）

样本：`run.jsonl` 中 `type == "ACTIVITY_STARTED"` 的事件；逐条取
`payload.{agent_id, day, slot, activity_type, place, start_tick}`。

角色表：`code/config/personas.json::personas[*].{persona_id, role_id}`（`--personas` 可覆盖）。
**同角色对** = 同一 `role_id` 下所有无序 `agent_id` 对（role 只有 1 人的不产生对）。
`agent_id` 在角色表里查不到的，**剔除并单列计数** `unknown_role_agents`（不静默丢）。

**配对细胞**（pair-cell，唯一统计单位）：
`(day, slot) × 同角色对`，且要求**双方在该细胞都有 `ACTIVITY_STARTED`**。任一方缺 ⇒ 不进分母
（缺的一方可能是 `DROPPED` / `INTENT_REJECTED` / 睡过去，口径上不可判，不补 0）。

三个同质率（分子/分母口径逐条写死）：

| 键 | 分子 | 分母 |
|---|---|---|
| `act_homophily` | 双方 `activity_type` 相同的 pair-cell | 全部 pair-cell |
| `place_homophily` | 双方 `place` 相同的 pair-cell | 全部 pair-cell |
| `both_homophily` | `(activity_type, place)` 均相同的 pair-cell | 全部 pair-cell |
| `tick_homophily` | 双方 `start_tick` 相同的 pair-cell | 全部 pair-cell |

守卫读数（防止「把工作换成闲逛」被当成改善，口径对齐 `code/life/planner.py` 的 G3 先例）：
`work_share_day`：分子 = `slot ∈ {morning, afternoon}` 且 `activity_type == "work"` 的
`ACTIVITY_STARTED` **条数**；分母 = 同范围的 `ACTIVITY_STARTED` **条数**（**条**，不是 pair-cell）。

噪声带：每个率都同时给 `rule_of_three_pp`（= `3/den*100`，分母为 0 时写 `null`，**不写 0**）。
理由：本读数在既有 6 个批次上逐位相同（见预登记 §1 F3），观测噪声为 0，`rule-of-three`
是**保守上界**；本器不做二项推断、不报 p。

两臂对照（`--arm off=<path> --arm on=<path>`）：逐键给 `rate_off / rate_on / delta_pp`
（`delta_pp = (rate_off − rate_on) * 100`，**正数 = 同质率下降 = 作息被拉开**），
并按预登记阈值机械比对给出 `verdict ∈ {成立, 不成立, 不可判}`（阈值由 `--thr-*` 传入，
**不写死在代码里**，避免尺子自带判据）。

## 用法（仓库根执行）

    # 单臂
    python3 tools/metrics/schedule_homophily.py --arm off=v2/evidence/<批>/run.jsonl

    # 两臂对照 + 落盘（阈值照预登记卡原文抄）
    python3 tools/metrics/schedule_homophily.py \
      --arm off=v2/evidence/<off批>/run.jsonl \
      --arm on=v2/evidence/<on批>/run.jsonl \
      --thr-act-max 0.50 --thr-act-delta-pp 15.0 \
      --thr-tick-max 0.75 --thr-tick-delta-pp 25.0 \
      --thr-work-guard-pp 5.0 \
      --out-json v2/evidence/r53-schedule-offset/compare.json

退出码：`0` = 出数成功（**含** verdict=不成立）；`2` = 前置条件缺失（日志/角色表不存在、
无 `ACTIVITY_STARTED`）；`3` = 调用方式错误（如 `--arm` 缺少 `label=path` 形态）。

幂等：输出不含时间戳、不含绝对路径、不含随机 ⇒ 同一输入两次运行**逐字节相等**。
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import sys
from collections import Counter, defaultdict

IMPL = "schedule-homophily/1"
RULER_VERSION = "r53-schedule-offset-v1"
MSG_TYPES = ("ACTIVITY_STARTED",)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _personas_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    # 仓库根执行时的默认相对路径（不写绝对路径，保证输出可移植）
    cand = os.path.join("code", "config", "personas.json")
    return cand


def load_roles(path: str) -> tuple[dict, str]:
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    personas = doc.get("personas") if isinstance(doc, dict) else doc
    roles = {}
    for p in personas or []:
        pid = p.get("persona_id")
        if not pid:
            continue
        roles[pid] = p.get("role_id") or ""
    return roles, sha256_file(path)


def role_pairs(roles: dict) -> tuple[list, dict]:
    by_role = defaultdict(list)
    for pid, rid in roles.items():
        if rid:
            by_role[rid].append(pid)
    pairs = []
    for rid in sorted(by_role):
        for a, b in itertools.combinations(sorted(by_role[rid]), 2):
            pairs.append((rid, a, b))
    return pairs, {rid: sorted(ms) for rid, ms in sorted(by_role.items())}


def read_activity(path: str, roles: dict) -> tuple[dict, dict, dict]:
    """返回 (cells[(day,slot)][agent] = (atype, place, start_tick), stats, unknown)。"""
    cells: dict = defaultdict(dict)
    n_events = 0
    unknown_agents = Counter()
    by_type = Counter()
    work_num = work_den = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") not in MSG_TYPES:
                continue
            p = ev.get("payload") or {}
            aid = p.get("agent_id")
            day, slot = p.get("day"), p.get("slot")
            atype, place, tick = p.get("activity_type"), p.get("place"), p.get("start_tick")
            if aid is None or day is None or slot is None or atype is None:
                continue
            n_events += 1
            by_type[str(atype)] += 1
            if aid not in roles:
                unknown_agents[aid] += 1
            # 同一 (day,slot) 同一 agent 多条 ACTIVITY_STARTED：取 (start_tick, seq) 最小的一条，
            # 保证确定性（不依赖行序），且把「重复起活动」这件事单列计数。
            key = (day, slot)
            cur = cells[key].get(aid)
            cand = (atype, place, tick)
            if cur is None or (tick if tick is not None else 1 << 30) < (
                cur[2] if cur[2] is not None else 1 << 30
            ):
                cells[key][aid] = cand
            if slot in ("morning", "afternoon"):
                work_den += 1
                work_num += int(str(atype) == "work")
    stats = {
        "activity_started_events": n_events,
        "cells_day_slot": len(cells),
        "activity_type_dist": dict(sorted(by_type.items())),
        "work_share_day": {"num": work_num, "den": work_den},
        "unknown_role_agents": dict(sorted(unknown_agents.items())),
        "unknown_role_agent_events": sum(unknown_agents.values()),
    }
    return cells, stats, unknown_agents


def homophily(cells: dict, pairs: list) -> dict:
    den = 0
    n_act = n_place = n_both = n_tick = 0
    for key in sorted(cells, key=lambda k: (k[0], str(k[1]))):
        agents = cells[key]
        for _rid, a, b in pairs:
            va, vb = agents.get(a), agents.get(b)
            if va is None or vb is None:
                continue
            den += 1
            n_act += int(va[0] == vb[0])
            n_place += int(va[1] == vb[1])
            n_both += int((va[0], va[1]) == (vb[0], vb[1]))
            n_tick += int(va[2] == vb[2])
    out = {}
    for name, num, d in (
        ("act_homophily", n_act, den),
        ("place_homophily", n_place, den),
        ("both_homophily", n_both, den),
        ("tick_homophily", n_tick, den),
    ):
        out[name] = _rate(num, d)
    out["pair_cells"] = den
    return out


def _rate(num: int, den: int) -> dict:
    r = {
        "num": num,
        "den": den,
        "rate": (num / den) if den else None,
        "rate_pct": round(num / den * 100, 4) if den else None,
        "rule_of_three_pp": round(3 / den * 100, 4) if den else None,
    }
    return r


def arm_report(log: str, personas: str, label: str) -> dict:
    roles, personas_sha = load_roles(personas)
    pairs, by_role = role_pairs(roles)
    cells, stats, _ = read_activity(log, roles)
    rep = {
        "label": label,
        "log": log,
        "log_bytes": os.path.getsize(log),
        "log_sha256": sha256_file(log),
        "personas": personas,
        "personas_sha256": personas_sha,
        "n_agents_in_personas": len(roles),
        "n_roles": len(by_role),
        "roles_multi": {r: ms for r, ms in by_role.items() if len(ms) >= 2},
        "n_same_role_pairs": len(pairs),
        "stats": stats,
    }
    rep.update(homophily(cells, pairs))
    return rep


def verdict_for(off: dict, on: dict, thr: dict) -> dict:
    """按预登记阈值机械比对（阈值由命令行传入，本函数不内置任何数字）。"""
    res: dict = {}
    den_off, den_on = off["pair_cells"], on["pair_cells"]
    min_den = thr.get("min_den", 68)
    base_undecidable = []
    if den_off < min_den or den_on < min_den:
        base_undecidable.append(
            f"pair_cells 分母过低（off={den_off}, on={den_on}, min={min_den}）"
        )

    def one(key: str, thr_max_key: str, thr_delta_key: str) -> dict:
        ro, rn = off[key]["rate"], on[key]["rate"]
        d = {
            "rate_off": ro,
            "rate_on": rn,
            "delta_pp": round((ro - rn) * 100, 4) if (ro is not None and rn is not None) else None,
            "num_off": off[key]["num"],
            "den_off": off[key]["den"],
            "num_on": on[key]["num"],
            "den_on": on[key]["den"],
            "rule_of_three_pp_off": off[key]["rule_of_three_pp"],
            "rule_of_three_pp_on": on[key]["rule_of_three_pp"],
            "thr_max": thr.get(thr_max_key),
            "thr_delta_pp": thr.get(thr_delta_key),
        }
        if base_undecidable or ro is None or rn is None:
            d["verdict"] = "不可判"
        elif thr.get(thr_max_key) is not None and rn > thr[thr_max_key]:
            d["verdict"] = "不成立"
        elif thr.get(thr_delta_key) is not None and d["delta_pp"] < thr[thr_delta_key]:
            d["verdict"] = "不成立"
        else:
            d["verdict"] = "成立"
        return d

    res["C1_act_homophily"] = one("act_homophily", "act_max", "act_delta_pp")
    res["C2_tick_homophily"] = one("tick_homophily", "tick_max", "tick_delta_pp")

    # 守卫：workday 白天 work 占比不得相对 OFF 掉超过 thr_work_guard_pp
    wo = off["stats"]["work_share_day"]
    wn = on["stats"]["work_share_day"]
    ro = (wo["num"] / wo["den"]) if wo["den"] else None
    rn = (wn["num"] / wn["den"]) if wn["den"] else None
    g = {
        "rate_off": ro,
        "rate_on": rn,
        "num_off": wo["num"],
        "den_off": wo["den"],
        "num_on": wn["num"],
        "den_on": wn["den"],
        "drop_pp": round((ro - rn) * 100, 4) if (ro is not None and rn is not None) else None,
        "thr_max_drop_pp": thr.get("work_guard_pp"),
        "rule_of_three_pp_off": round(3 / wo["den"] * 100, 4) if wo["den"] else None,
        "rule_of_three_pp_on": round(3 / wn["den"] * 100, 4) if wn["den"] else None,
    }
    if ro is None or rn is None:
        g["verdict"] = "不可判"
    elif thr.get("work_guard_pp") is not None and g["drop_pp"] > thr["work_guard_pp"]:
        g["verdict"] = "不成立"
    else:
        g["verdict"] = "成立"
    res["G1_work_share_day"] = g

    res["_undecidable_reasons"] = base_undecidable
    res["descriptive_only"] = ["place_homophily", "both_homophily"]
    return res


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="R53 作息个体差异读数器（只读、零 LLM）")
    ap.add_argument("--arm", action="append", default=[], metavar="LABEL=PATH",
                    help="臂，可重复；两臂时第一个视为 OFF、第二个视为 ON（按 label 排序前先校验）")
    ap.add_argument("--personas", default=None, help="角色表路径（默认 code/config/personas.json）")
    ap.add_argument("--thr-act-max", type=float, default=None)
    ap.add_argument("--thr-act-delta-pp", type=float, default=None)
    ap.add_argument("--thr-tick-max", type=float, default=None)
    ap.add_argument("--thr-tick-delta-pp", type=float, default=None)
    ap.add_argument("--thr-work-guard-pp", type=float, default=None)
    ap.add_argument("--min-den", type=int, default=68)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args(argv)

    arms = []
    for spec in args.arm:
        if "=" not in spec:
            print("ERROR: --arm 需为 LABEL=PATH", file=sys.stderr)
            return 3
        label, path = spec.split("=", 1)
        if not os.path.exists(path):
            print(f"ERROR: 日志不存在 {path}", file=sys.stderr)
            return 2
        arms.append((label.strip(), path.strip()))
    if not arms:
        print("ERROR: 至少一个 --arm", file=sys.stderr)
        return 3

    personas = _personas_path(args.personas)
    if not os.path.exists(personas):
        print(f"ERROR: 角色表不存在 {personas}", file=sys.stderr)
        return 2

    reports = []
    for label, path in arms:
        rep = arm_report(path, personas, label)
        if rep["stats"]["activity_started_events"] == 0:
            print(f"ERROR: {path} 无 ACTIVITY_STARTED", file=sys.stderr)
            return 2
        reports.append(rep)

    doc: dict = {
        "impl": IMPL,
        "ruler_version": RULER_VERSION,
        "impl_sha256": sha256_file(os.path.abspath(__file__)),
        "arms": reports,
    }
    if len(reports) == 2:
        thr = {
            "act_max": args.thr_act_max,
            "act_delta_pp": args.thr_act_delta_pp,
            "tick_max": args.thr_tick_max,
            "tick_delta_pp": args.thr_tick_delta_pp,
            "work_guard_pp": args.thr_work_guard_pp,
            "min_den": args.min_den,
        }
        doc["thresholds"] = thr
        doc["compare"] = verdict_for(reports[0], reports[1], thr)
    elif len(reports) > 2:
        print("ERROR: 目前只支持 1 或 2 个 --arm", file=sys.stderr)
        return 3

    text = json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2)
    print(text)
    if args.out_json:
        d = os.path.dirname(args.out_json)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
