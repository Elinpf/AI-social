#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-5（口径下沉版）作息/生活气息读数器 —— 纯只读、零跑批、零 LLM。

口径唯一真源：`<team-workspace>/round1-prereg-F5.md` §3（本文件 `SPEC` 与之一一对应；
两者不一致即视为缺陷，先改口径卡再改这里）。

数据来源：`run.jsonl` 里的 `ACTIVITY_STARTED` 事件（引擎已落盘，字段实测含
`agent_id / day / day_type / slot / slot_id / place / activity_type / template / participants`）。

指标（公式逐条对应口径卡 §3）：

  M1  生活类活动人均日频   = #{p: p.template ∈ LIVING} / (agents × days)
  M2  休闲人均 5 天频      = #{p: p.activity_type == "leisure"} / (agents × days) × 5   （对齐 R23/R4）
  M3  闲时段命中率         = #{(agent,day): 该 (agent,day) 在 living_slot(dow) 上出现 template ∈ LIVING}
                             / (agents × days)
  M4  白天作息稳定性       = mean over (agent, slot∈{morning,afternoon,evening}) of
                             众数(place,activity_type) 的天数 / 该 slot 观测天数        （仅描述）
  G1  活动多样性           = mean over agent of #{distinct (slot, place, activity_type)}
  G2  活动总量             = #ACTIVITY_STARTED（守恒判据用 agents × days × 4 对照）
  G3  生产性活动占比       = #{p: p.activity_type ∈ {work, learn, trade}} / #ACTIVITY_STARTED
  G4  模板命中率           = #{p: template 非空} / #ACTIVITY_STARTED

用法（仓库根执行，只读）：
    python3 tools/habit/habit_readings.py --run OFF=v2/evidence/<off_dir> \
        --run ON=v2/evidence/<on_dir> --out-json v2/evidence/<x>/habit_readings.json
    python3 tools/habit/habit_readings.py --run A0=v2/evidence/run_d12c_off_n16r60_seed42

退出码：0 成功；2 输入不可用（目录/run.jsonl 缺失或无 ACTIVITY_STARTED）。
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA_VERSION = "habit-readings/1.0"

#: 生活类模板集合（口径卡 §3 写死；只列 `activity_templates.json` 里既有的模板 id）
LIVING = (
    "combat_training",
    "contest",
    "ice_break",
    "select_location",
    "creative_collab",
    "rel_maintain",
)
#: 生产性活动类型（守卫 G3）
PRODUCTIVE = ("work", "learn", "trade")
#: 白天时段（M4 口径；night 因全员同睡同地点被剔除）
DAY_SLOTS = ("morning", "afternoon", "evening")
#: 闲时段轮转表（口径卡 §2.2，与 planner._LIVING_SLOTS 同源语义）
LIVING_SLOTS = ("morning", "afternoon", "evening")

SPEC = {
    "M1": "living_per_agent_day = #{ACTIVITY_STARTED: template in LIVING} / (agents * days)",
    "M2": "leisure_per_agent_5d = #{activity_type == 'leisure'} / (agents * days) * 5",
    "M3": "living_slot_hit = #{(agent,day): living_slot(dow) 上 template in LIVING} / (agents * days)",
    "M4": "daytime_routine_stability = mean_{agent,slot in DAY_SLOTS}(mode_days / observed_days)",
    "G1": "activity_diversity = mean_agent(#distinct (slot, place, activity_type))",
    "G2": "activity_total = #ACTIVITY_STARTED",
    "G3": "productive_share = #{activity_type in PRODUCTIVE} / #ACTIVITY_STARTED",
    "G4": "template_hit_rate = #{template non-empty} / #ACTIVITY_STARTED",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _dow(slot_id: str, day: int | None) -> int | None:
    """从 `slot_id`（形如 `day3-morning`）取 day_of_week；取不到则退化为 day % 7。"""
    s = str(slot_id or "")
    if s.startswith("day"):
        head = s[3:].split("-", 1)[0]
        if head.isdigit():
            return int(head) % 7
    if isinstance(day, int):
        return day % 7
    return None


def _living_slot(dow: int | None) -> str | None:
    if dow is None:
        return None
    return LIVING_SLOTS[dow % len(LIVING_SLOTS)]


def _rate(num: float, den: float) -> float | None:
    return None if not den else round(num / den, 6)


def _r6(x: float) -> float:
    return round(x, 6)


def _dist(values) -> dict:
    """计数分布；缺失值统一记为 `(none)`（JSON 键不能为 null，且需可排序）。"""
    c = Counter("(none)" if v is None else str(v) for v in values)
    return {k: c[k] for k in sorted(c)}


def analyze(run_dir: Path) -> dict:
    log = run_dir / "run.jsonl"
    if not log.is_file():
        raise SystemExit(f"[habit] missing run.jsonl: {log}")
    acts: list[dict] = []
    with log.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or '"ACTIVITY_STARTED"' not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("type") != "ACTIVITY_STARTED":
                continue
            p = rec.get("payload") or {}
            acts.append({
                "agent": str(p.get("agent_id")),
                "day": p.get("day"),
                "slot": p.get("slot"),
                "slot_id": p.get("slot_id"),
                "place": p.get("place"),
                "activity_type": p.get("activity_type"),
                "template": p.get("template"),
                "multi": len(p.get("participants") or []) > 1,
            })
    if not acts:
        raise SystemExit(f"[habit] no ACTIVITY_STARTED in {log}")

    agents = sorted({a["agent"] for a in acts})
    days = sorted({a["day"] for a in acts if isinstance(a["day"], int)})
    n_agents, n_days = len(agents), len(days)
    ad = n_agents * n_days                       # 分母：agents × days

    n = len(acts)
    living = [a for a in acts if a["template"] in LIVING]
    leisure = [a for a in acts if a["activity_type"] == "leisure"]
    prod = [a for a in acts if a["activity_type"] in PRODUCTIVE]
    tmpl = [a for a in acts if a["template"]]

    # M3：每个 (agent, day) 在其轮转闲时段是否排上生活类活动
    hit: dict[tuple, bool] = {}
    for a in acts:
        if not isinstance(a["day"], int):
            continue
        key = (a["agent"], a["day"])
        if a["slot"] != _living_slot(_dow(a["slot_id"], a["day"])):
            continue
        if a["template"] in LIVING:
            hit[key] = True
    m3_hits = sum(1 for v in hit.values() if v)

    # M4：白天作息稳定性（剔除 night）
    per_slot = defaultdict(list)
    for a in acts:
        if a["slot"] in DAY_SLOTS and isinstance(a["day"], int):
            per_slot[(a["agent"], a["slot"])].append((a["day"], (a["place"], a["activity_type"])))
    shares = []
    for key, rows in per_slot.items():
        cnt = Counter(pair for _d, pair in rows)
        days_seen = len({d for d, _ in rows})
        if not days_seen:
            continue
        shares.append(cnt.most_common(1)[0][1] / days_seen)
    m4 = _r6(sum(shares) / len(shares)) if shares else None

    # G1：每个 agent 的 distinct (slot, place, activity_type)
    triples = defaultdict(set)
    for a in acts:
        triples[a["agent"]].add((a["slot"], a["place"], a["activity_type"]))
    g1 = _r6(sum(len(v) for v in triples.values()) / len(agents)) if agents else None

    out = {
        "schema_version": SCHEMA_VERSION,
        "run_dir": str(run_dir),
        "run_jsonl_sha256": _sha256(log),
        "agents": n_agents,
        "days": n_days,
        "exposure": {"agents_x_days": ad, "activity_events": n},
        "M1_living_per_agent_day": {"value": _rate(len(living), ad), "num": len(living), "den": ad,
                                    "formula": SPEC["M1"]},
        "M2_leisure_per_agent_5d": {"value": _r6(len(leisure) / ad * 5) if ad else None,
                                    "num": len(leisure), "den": ad, "formula": SPEC["M2"]},
        "M3_living_slot_hit": {"value": _rate(m3_hits, ad), "num": m3_hits, "den": ad,
                               "formula": SPEC["M3"]},
        "M4_daytime_routine_stability": {"value": m4, "n_agent_slot": len(shares),
                                         "formula": SPEC["M4"]},
        "G1_activity_diversity": {"value": g1, "formula": SPEC["G1"]},
        "G2_activity_total": {"value": n, "expected_agents_days_x4": ad * 4,
                              "formula": SPEC["G2"]},
        "G3_productive_share": {"value": _rate(len(prod), n), "num": len(prod), "den": n,
                                "formula": SPEC["G3"]},
        "G4_template_hit_rate": {"value": _rate(len(tmpl), n), "num": len(tmpl), "den": n,
                                 "formula": SPEC["G4"]},
        "distribution": {
            "template": _dist(a["template"] for a in acts),
            "activity_type": _dist(a["activity_type"] for a in acts),
            "slot_x_template": {s: _dist(a["template"] for a in acts if a["slot"] == s)
                                for s in ("morning", "afternoon", "evening", "night")},
        },
        "recompute": "python3 tools/habit/habit_readings.py --run <TAG>=%s" % run_dir,
    }
    return out


def compare(arms: dict[str, dict]) -> dict:
    """OFF/ON 对照：只对 M/G 值做差与比值，口径卡 §5 的阈值判定仍由人/报告侧执行。"""
    if len(arms) < 2:
        return {}
    names = list(arms)
    base, treat = names[0], names[-1]
    keys = ["M1_living_per_agent_day", "M2_leisure_per_agent_5d", "M3_living_slot_hit",
            "M4_daytime_routine_stability", "G1_activity_diversity", "G2_activity_total",
            "G3_productive_share", "G4_template_hit_rate"]
    out = {"base": base, "treat": treat, "delta": {}}
    for k in keys:
        b = (arms[base].get(k) or {}).get("value")
        t = (arms[treat].get(k) or {}).get("value")
        if b is None or t is None:
            out["delta"][k] = None
            continue
        out["delta"][k] = {"base": b, "treat": t, "diff": _r6(t - b),
                           "ratio": _r6(t / b) if b else None}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F-5（口径下沉）作息/生活气息读数器（只读）")
    ap.add_argument("--run", action="append", default=[], metavar="TAG=DIR",
                    help="可重复；第一个为基臂（OFF），最后一个为处理臂（ON）")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--no-timestamp", action="store_true")
    a = ap.parse_args(argv)

    arms, meta = {}, {}
    for spec in a.run:
        if "=" not in spec:
            print(f"[habit] bad --run (want TAG=DIR): {spec}", file=sys.stderr)
            return 2
        tag, d = spec.split("=", 1)
        rd = Path(d).resolve()
        if not (rd / "run.jsonl").is_file():
            print(f"[habit] missing {rd / 'run.jsonl'}", file=sys.stderr)
            return 2
        arms[tag] = analyze(rd)
        mj = rd / "meta.json"
        if mj.is_file():
            try:
                m = json.loads(mj.read_text())
                meta[tag] = {k: m.get(k) for k in ("code_sha", "started_at", "ended_at",
                                                   "events", "rounds_effective")}
            except Exception:
                meta[tag] = None
        else:
            meta[tag] = None

    out = {"schema_version": SCHEMA_VERSION, "spec": SPEC, "arms": arms,
           "arm_meta": meta, "compare": compare(arms)}
    if not a.no_timestamp:
        import datetime
        out["generated_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    txt = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out_json:
        p = Path(a.out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt + "\n", encoding="utf-8")
        print(f"[habit] wrote {p}")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
