"""T52 取证脚本：Phase 4.4–4.8 生命周期 hook 实测证据。

跑法：
    python scripts/lifecycle_pressure_run.py            # 主档（默认参数）
    python scripts/lifecycle_pressure_run.py --n 20 --rounds 84

产出（写入 code/reports/）：
    lifecycle_t52_evidence.json   结构化证据
    lifecycle_t52_evidence.md     人读摘要（含状态迁移计数 + 存活率曲线）

证据项（对应任务验收）：
    ① METABOLISM / STATE_CHANGE > 0；near_death→dead 迁移可达；
    ② SYSTEM_ERROR=0、货币守恒成立、replay 逐位一致；
    ③ 状态迁移计数 + 存活率曲线；
    ④ 实际生效档位（effective preset）与「是否受 engine_version 指纹覆盖」。
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import conservation
from engine.hooks.lifecycle import _cfg as _lc_cfg, effective_preset
from engine.kernel import Engine
from engine.replay import replay_records
from engine.runner import default_config, write_log
from engine.state import state_hash

_CODE = Path(__file__).resolve().parents[1]
_OUT = _CODE / "reports"


def _enabled_config():
    """默认 config（policy.lifecycle.enabled=false）+ 运行时开启。

    运行时 override 不属 engine_version 指纹覆盖，故报告显式记录 effective preset。
    """
    cfg = default_config()
    cfg["lifecycle"] = {"ENABLED": True}
    return cfg


def _summarize(records, state, cfg):
    c = collections.Counter(r["type"] for r in records)
    pairs = collections.Counter(
        (r["payload"].get("from"), r["payload"].get("to"))
        for r in records if r["type"] == "STATE_CHANGE")
    causes = collections.Counter(
        r["payload"].get("cause") for r in records if r["type"] == "AGENT_DIED")
    reasons = collections.Counter(
        r["payload"].get("reason") for r in records if r["type"] == "STATE_CHANGE")

    # 存活率曲线：每回合末「非 terminated」与「alive/warning/near_death」计数
    terminated, dead = set(), set()
    curve = {}
    for r in records:
        rnd = int(r["round"])
        if r["type"] == "STATE_CHANGE" and r["payload"].get("to") == "terminated":
            terminated.add(r["payload"]["agent_id"])
        if r["type"] == "AGENT_DIED":
            dead.add(r["payload"]["agent_id"])
        if r["type"] == "AGENT_REVIVED":
            dead.discard(r["payload"]["agent_id"])
        if r["type"] == "TURN_SEAL":
            total = len(state.agents)
            curve[rnd] = {
                "non_terminated": total - len(terminated),
                "dead": len(dead - terminated),
                "terminated": len(terminated),
                "total": total,
            }

    return {
        "event_total": len(records),
        "counts": {k: c.get(k, 0) for k in (
            "METABOLISM", "PENALTY_APPLIED", "STATE_CHANGE", "AGENT_DIED",
            "AGENT_REVIVED", "REVIVE_FEE_PAID", "SYSTEM_ERROR", "TURN_SEAL")},
        "state_transitions": {f"{a}->{b}": n for (a, b), n in sorted(pairs.items())},
        "state_change_reasons": dict(reasons),
        "death_causes": dict(causes),
        "alive_rate_curve": curve,
    }


def _run_life_mode(n, rounds, seed, cfg):
    from orchestration.integration import build_world
    t0 = time.perf_counter()
    world = build_world(seed=seed, config=cfg, n=n)
    engine = world["engine"]
    for r in range(rounds):
        engine.run_round(r)
    elapsed = time.perf_counter() - t0
    records = engine.ledger.records
    chain_ok, chain_err = engine.ledger.verify_chain()
    viols = conservation.check_conservation(engine.state, cfg)
    repl = replay_records(records, verify=True, verify_seals=True)
    out = _summarize(records, engine.state, cfg)
    out.update({
        "mode": "life", "n_agents": n, "rounds": rounds, "seed": seed,
        "seconds": round(elapsed, 3),
        "chain_ok": bool(chain_ok), "chain_error": chain_err,
        "conservation_ok": (len(viols) == 0), "conservation_violations": viols,
        "first_run_equals_replay": (state_hash(repl) == state_hash(engine.state)),
        "unknown_event_types": sorted({r["type"] for r in records
                                       if r["type"] not in _EVENT_TYPES}),
        "effective_preset": effective_preset(engine.ctx),
        "preset_fingerprinted": True,   # policy.lifecycle 在 FINGERPRINT_FILES 内
    })
    return out, records


def _run_rule_world(n, rounds, seed, cfg):
    """空世界 rule-based N×rounds（无 LLM，纯规则）：作为「rule-based N=20×84」快证。"""
    c2 = json.loads(json.dumps(cfg))
    c2.setdefault("genesis", {})["agent_count"] = n
    eng = Engine(seed, c2)
    t0 = time.perf_counter()
    eng.run(rounds)
    elapsed = time.perf_counter() - t0
    records = eng.ledger.records
    viols = conservation.check_conservation(eng.state, c2)
    repl = replay_records(records, verify=True, verify_seals=True)
    out = _summarize(records, eng.state, c2)
    out.update({
        "mode": "rule-world", "n_agents": n, "rounds": rounds, "seed": seed,
        "seconds": round(elapsed, 3),
        "conservation_ok": (len(viols) == 0),
        "first_run_equals_replay": (state_hash(repl) == state_hash(eng.state)),
    })
    return out, records


_EVENT_TYPES = None
try:
    from engine.events import EVENT_TYPES as _EVENT_TYPES  # noqa: E402
except Exception:  # pragma: no cover
    _EVENT_TYPES = set()


def _md(rep_life, rep_rule, preset):
    lines = ["# T52 生命周期 hook（4.4–4.8）实测证据", ""]
    lines.append("> 生成脚本：`code/scripts/lifecycle_pressure_run.py`；"
                 "配置：`config/policy.json` 的 `lifecycle` 块（默认 enabled=false），"
                 "本次运行时 override `ENABLED=true`。")
    lines.append("")
    lines.append("## 生效档位（effective preset）")
    lines.append("```json")
    lines.append(json.dumps({k: preset[k] for k in sorted(preset)}, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("阈值来自 `config/policy.json`（**在 engine_version 指纹内**）；"
                 "`ENABLED` 为运行时 override。")
    lines.append("")
    for rep, title in ((rep_life, "主档：life 模式（build_world，rule-based 离线 LLM）"),
                       (rep_rule, "附档：空世界 rule-based")):
        if rep is None:
            continue
        lines.append(f"## {title} — N={rep['n_agents']}×{rep['rounds']}")
        lines.append("")
        lines.append(f"- 事件总数：{rep['event_total']}；耗时 {rep.get('seconds')}s")
        lines.append(f"- 计数：`{json.dumps(rep['counts'], ensure_ascii=False)}`")
        lines.append(f"- 状态迁移：`{json.dumps(rep['state_transitions'], ensure_ascii=False)}`")
        lines.append(f"- 迁移原因：`{json.dumps(rep.get('state_change_reasons', {}), ensure_ascii=False)}`")
        lines.append(f"- 死亡原因：`{json.dumps(rep.get('death_causes', {}), ensure_ascii=False)}`")
        lines.append(f"- SYSTEM_ERROR=0：{rep['counts']['SYSTEM_ERROR'] == 0}")
        lines.append(f"- 守恒成立：{rep.get('conservation_ok')}；replay 逐位一致：{rep.get('first_run_equals_replay')}")
        lines.append(f"- 未登记事件类型：{rep.get('unknown_event_types')}")
        lines.append("")
        lines.append("### 存活率曲线（每回合末）")
        lines.append("")
        lines.append("| round | non_terminated | dead | terminated | total |")
        lines.append("|---|---|---|---|---|")
        curve = rep["alive_rate_curve"]
        step = max(1, len(curve) // 20)
        ks = sorted(curve)
        for i, r in enumerate(ks):
            if i % step == 0 or i == len(ks) - 1:
                v = curve[r]
                lines.append(f"| {r} | {v['non_terminated']} | {v['dead']} | "
                             f"{v['terminated']} | {v['total']} |")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-life", action="store_true", help="跳过较慢的 life 模式档")
    args = ap.parse_args()

    cfg = _enabled_config()
    preset = effective_preset(Engine(args.seed, cfg).ctx)

    rep_rule, recs_rule = _run_rule_world(args.n, args.rounds, args.seed, cfg)

    rep_life, recs_life = None, None
    if not args.skip_life:
        rep_life, recs_life = _run_life_mode(args.n, args.rounds, args.seed, cfg)

    _OUT.mkdir(parents=True, exist_ok=True)
    report = {"effective_preset": preset, "rule_world": rep_rule,
              "life_mode": rep_life}
    (_OUT / "lifecycle_t52_evidence.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (_OUT / "lifecycle_t52_evidence.md").write_text(
        _md(rep_life, rep_rule, preset), encoding="utf-8")
    if recs_life:
        write_log(recs_life, _OUT / "lifecycle_t52_life_n20x84.jsonl")
    print(json.dumps({k: report[k] for k in ("rule_world", "life_mode")},
                     ensure_ascii=False)[:1500])
    print("report ->", _OUT / "lifecycle_t52_evidence.md")


if __name__ == "__main__":
    main()
