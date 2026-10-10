"""T61 取证脚本：流动性判据（死亡/续命）实测证据。

跑法：  python scripts/lifecycle_liquidity_run.py            # life 模式 N=20×84（默认经济+生命周期开）
        python scripts/lifecycle_liquidity_run.py --n 20 --rounds 84

产出（code/reports/lifecycle_t61_*.{json,md,jsonl.gz}）：
  - 计数（METABOLISM/STATE_CHANGE/AGENT_DIED/AGENT_REVIVED/LOAN_*）；
  - 状态迁移链 + **死亡轮次分布**（验证错峰）；
  - 存活率曲线；
  - **借贷续命实证**：借贷者 vs 未借贷者的死亡轮次；一条「净值<0 但仍未死（L 尚可）」的 journal；
  - SYSTEM_ERROR=0、守恒、replay 逐位一致。
"""

from __future__ import annotations

import argparse
import collections
import gzip
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import conservation
from engine.hooks.lifecycle import effective_preset
from engine.replay import replay_records
from engine.runner import default_config, write_log
from engine.state import state_hash

_CODE = Path(__file__).resolve().parents[1]
_OUT = _CODE / "reports"


def _summarize(recs, state, cfg):
    c = collections.Counter(r["type"] for r in recs)
    pairs = collections.Counter(
        f"{r['payload'].get('from')}->{r['payload'].get('to')}"
        for r in recs if r["type"] == "STATE_CHANGE")
    death_round = {}
    for r in recs:
        if r["type"] == "AGENT_DIED":
            death_round[r["payload"]["agent_id"]] = int(r["round"])
    borrowers = collections.OrderedDict()
    for r in recs:
        if r["type"] == "LOAN_ISSUED":
            b = r["payload"]["borrower"]
            borrowers.setdefault(b, []).append((int(r["round"]), int(r["payload"]["principal"])))

    # 存活率曲线（每回合末，非 terminated 占比）
    terminated, dead = set(), set()
    curve = {}
    for r in recs:
        if r["type"] == "STATE_CHANGE" and r["payload"].get("to") == "terminated":
            terminated.add(r["payload"]["agent_id"])
        if r["type"] == "AGENT_DIED":
            dead.add(r["payload"]["agent_id"])
        if r["type"] == "AGENT_REVIVED":
            dead.discard(r["payload"]["agent_id"])
        if r["type"] == "TURN_SEAL":
            n = len([a for a in state.agents if a not in _SYSTEM])
            curve[int(r["round"])] = {
                "non_terminated": n - len(terminated & set(state.agents)),
                "terminated": len(terminated & set(state.agents)),
            }

    borrowers_dr = sorted(death_round[b] for b in borrowers if b in death_round)
    nonborrow_dr = sorted(death_round[a] for a in death_round if a not in borrowers)
    revived = sorted({r["payload"]["agent_id"] for r in recs if r["type"] == "AGENT_REVIVED"})
    real = [a for a in state.agents if a not in _SYSTEM]
    survivors = sorted(a for a in real if state.agents[a].get("status") not in ("dead", "terminated"))
    survivors_borrowed = sorted(set(survivors) & set(borrowers))
    return {
        "event_total": len(recs),
        "counts": {k: c.get(k, 0) for k in (
            "METABOLISM", "STATE_CHANGE", "AGENT_DIED", "AGENT_REVIVED",
            "REVIVE_FEE_PAID", "LOAN_ISSUED", "INTEREST_CHARGED", "LOAN_DEFAULT",
            "PENALTY_APPLIED", "SYSTEM_ERROR")},
        "state_transitions": dict(pairs),
        "death_rounds": dict(sorted(collections.Counter(death_round.values()).items())),
        "death_round_by_agent": death_round,
        "borrowers": {b: v for b, v in borrowers.items()},
        "borrower_death_rounds": borrowers_dr,
        "nonborrower_death_rounds": nonborrow_dr,
        "revived_agents": revived,
        "survivors": survivors,
        "survivors_that_borrowed": survivors_borrowed,
        "alive_rate_curve": curve,
    }


_SYSTEM = {"MARKET", "BANK", "WORLD", "SYSTEM", "TAX_POOL"}


def _journal_evidence(recs, state):
    """找「净值<0 但仍未死（status != dead/terminated）」与「借贷后续生存」的 journal 条目。"""
    # 重建每回合末各 agent 的 (cash, debt) 变化：用 METABOLISM 的 liquid 近似 L；用事件推 debt
    debt = collections.Counter()
    status = {a: "alive" for a in state.agents}
    neg_not_dead = []
    neg_alive = 0
    total_not_dead = 0
    for r in recs:
        t = r["type"]
        p = r["payload"]
        if t == "LOAN_ISSUED":
            debt[p["borrower"]] += int(p["outstanding"])
        elif t == "STATE_CHANGE":
            status[p["agent_id"]] = p["to"]
        elif t == "AGENT_DIED":
            status[p["agent_id"]] = "dead"
        elif t == "AGENT_REVIVED":
            status[p["agent_id"]] = "revived"
        elif t == "METABOLISM":
            aid = p["agent_id"]
            L = int(p.get("liquid", 0))
            nw = L - debt[aid]           # deposits 近似 0
            st = status.get(aid)
            if nw < 0 and st not in ("dead", "terminated"):
                total_not_dead += 1
                if st == "alive":
                    neg_alive += 1
                if len(neg_not_dead) < 6:
                    neg_not_dead.append({
                        "round": int(r["round"]), "agent_id": aid, "liquid_L": L,
                        "debt": debt[aid], "net_worth_approx": nw, "status": st})
    return {"neg_nw_not_dead_rounds": total_not_dead,
            "neg_nw_strict_alive_rounds": neg_alive,
            "samples": neg_not_dead}


def _md(rep, preset, journal):
    L = ["# T61 生命周期流动性判据 · 实测证据", ""]
    L.append("> 生成：`code/scripts/lifecycle_liquidity_run.py`；口径：**L=cash**，判死="
             "`L<liquid_trigger_mu 且 not can_borrow` 连续 `N_death` 回合；允许负净值存活。")
    L.append("")
    L.append("## 生效档位")
    L.append("```json")
    L.append(json.dumps({k: preset[k] for k in ("ENABLED", "METABOLISM_MU", "LIQUID_TRIGGER_MU",
                                                "LIQUID_SUSTAIN_MU", "N_DEATH", "K_EXIT")},
                        ensure_ascii=False, indent=2))
    L.append("```")
    L.append("")
    L.append(f"## 结果 — N={rep['n_agents']}×{rep['rounds']}（经济 + 生命周期开）")
    L.append("")
    L.append(f"- 事件总数：{rep['event_total']}；耗时 {rep.get('seconds')}s")
    L.append(f"- 计数：`{json.dumps(rep['counts'], ensure_ascii=False)}`")
    L.append(f"- 状态迁移：`{json.dumps(rep['state_transitions'], ensure_ascii=False)}`")
    L.append(f"- **死亡轮次分布：`{json.dumps(rep['death_rounds'], ensure_ascii=False)}`**")
    L.append(f"- 借贷者死亡轮次：{rep['borrower_death_rounds']}")
    L.append(f"- 未借贷者死亡轮次：{rep['nonborrower_death_rounds']}")
    L.append(f"- **借贷续命存活**（survivors ∩ borrowers）：{rep['survivors_that_borrowed']}"
             f"（共 {len(rep['survivors_that_borrowed'])} 人，占存活 {len(rep['survivors'])}）")
    L.append(f"- **复活**（dead→revived）：{rep['revived_agents']}")
    L.append(f"- **「净值<0 且存活」**（`status∉{{dead,terminated}}`）："
             f"{journal['neg_nw_not_dead_rounds']} 个 agent·回合（严格 alive："
             f"{journal['neg_nw_strict_alive_rounds']}）")
    L.append(f"- 两类路径并存：借贷续命存活 {len(rep['survivors_that_borrowed'])} 人 vs "
             f"借不到/最终死亡 {len(rep['death_round_by_agent']) - len(rep['survivors'])} 人")
    L.append(f"- SYSTEM_ERROR=0：{rep['counts']['SYSTEM_ERROR'] == 0}；守恒：{rep.get('conservation_ok')}；"
             f"replay 逐位一致：{rep.get('first_run_equals_replay')}")
    L.append("")
    L.append("### journal：净值<0 但仍存活（流动性判据不认净值；`status∉{dead,terminated}`）")
    L.append("```json")
    L.append(json.dumps(journal["samples"], ensure_ascii=False, indent=2))
    L.append("```")
    L.append("")
    L.append("### 存活率曲线（每回合末，抽样）")
    L.append("")
    L.append("| round | non_terminated | terminated |")
    L.append("|---|---|---|")
    curve = rep["alive_rate_curve"]
    ks = sorted(curve)
    step = max(1, len(ks) // 18)
    for i, r in enumerate(ks):
        if i % step == 0 or i == len(ks) - 1:
            L.append(f"| {r} | {curve[r]['non_terminated']} | {curve[r]['terminated']} |")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--metabolism-mu", type=int, default=None)
    ap.add_argument("--trigger-mu", type=int, default=None)
    ap.add_argument("--sustain-mu", type=int, default=None)
    ap.add_argument("--unsecured-mu", type=int, default=None)
    ap.add_argument("--endow-mu", type=int, default=None)
    args = ap.parse_args()

    from orchestration.integration import build_world
    cfg = default_config()   # canonical 档在 config/policy.json（lifecycle+economy），无需运行时覆盖
    life = {"ENABLED": True}
    if args.metabolism_mu is not None:
        life["METABOLISM_MU"] = args.metabolism_mu
    cfg["lifecycle"] = life
    econ = {}
    if args.trigger_mu is not None:
        econ["liquid_trigger_mu"] = args.trigger_mu
    if args.sustain_mu is not None:
        econ["liquid_sustain_mu"] = args.sustain_mu
    if args.unsecured_mu is not None:
        econ["credit_unsecured_base_mu"] = args.unsecured_mu
    if econ:
        cfg["economy"] = econ
    if args.endow_mu is not None:
        cfg.setdefault("genesis", {})["initial_endowment_mu"] = args.endow_mu
    t0 = time.perf_counter()
    world = build_world(seed=args.seed, config=cfg, n=args.n)
    eng = world["engine"]
    for r in range(args.rounds):
        eng.run_round(r)
    secs = round(time.perf_counter() - t0, 2)
    recs = eng.ledger.records
    viols = conservation.check_conservation(eng.state, cfg)
    repl = replay_records(recs, verify=True, verify_seals=True)
    rep = _summarize(recs, eng.state, cfg)
    rep.update({"n_agents": args.n, "rounds": args.rounds, "seed": args.seed, "seconds": secs,
                "conservation_ok": (len(viols) == 0), "conservation_violations": viols,
                "first_run_equals_replay": (state_hash(repl) == state_hash(eng.state))})
    journal = _journal_evidence(recs, eng.state)
    preset = effective_preset(eng.ctx)

    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "lifecycle_t61_evidence.json").write_text(
        json.dumps({"preset": preset, "report": rep, "journal": journal}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (_OUT / "lifecycle_t61_evidence.md").write_text(_md(rep, preset, journal), encoding="utf-8")
    lp = _OUT / "lifecycle_t61_life_n20x84.jsonl"
    write_log(recs, lp)
    with open(str(lp) + ".gz", "wb") as f:
        f.write(gzip.compress(lp.read_bytes()))
    lp.unlink()
    print(json.dumps({"counts": rep["counts"], "death_rounds": rep["death_rounds"],
                      "borrowers": len(rep["borrowers"]),
                      "borrower_death_rounds": rep["borrower_death_rounds"],
                      "conservation_ok": rep["conservation_ok"],
                      "replay": rep["first_run_equals_replay"]}, ensure_ascii=False))
    print("report ->", _OUT / "lifecycle_t61_evidence.md")


if __name__ == "__main__":
    main()
