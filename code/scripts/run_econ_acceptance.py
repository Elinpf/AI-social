"""T51 经济 hook 验收证据：rule-based N=20×84 实跑。

用法（在 code/ 下）：
    python scripts/run_econ_acceptance.py [--rounds 84] [--n 20] [--seed 42] [--metabolism 200]

输出：经济族事件计数表 + 守恒/SYSTEM_ERROR/replay 一致性 + obs 口径指标。
`--metabolism`>0 时注入一个**等价代谢扣除**的 4.4 占位 hook（因 T52 lifecycle 4.4 未落地），
仅用于贯通「代谢→负资产→续命贷→计息」环路以取证据；正式运行由 lifecycle-dev 的 4.4 提供。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import conservation
from engine import liquidity as _liq
from engine.constants import PHASE_ARBITRATE
from engine.events import spec
from engine.replay import replay_records
from engine.state import state_hash
from orchestration.integration import build_world


def liq_debt(state, aid):
    return _liq.debt_of(state, aid)

ECON_TYPES = ["TRANSFER", "MARKET_TRADE", "DEPOSIT", "WITHDRAW", "TAX_LEVIED",
              "UBI_PAID", "INTEREST_CHARGED", "INTEREST_PAID", "LOAN_ISSUED",
              "LOAN_REPAY", "LOAN_DEFAULT", "MONEY_MINTED", "MONEY_BURNED",
              "METABOLISM", "PENALTY_APPLIED", "DROPPED", "INTENT_REJECTED",
              "AGENT_DIED", "AGENT_REVIVED", "REVIVE_FEE_PAID", "STATE_CHANGE"]


def _install_metabolism(per_agent_mu: int):
    from engine.hooks import register_phase4_hook

    def apply_metabolism_stub(state, round_no, ctx):
        out = []
        for aid, a in sorted(state.agents.items()):
            if a.get("status") in ("dead", "terminated"):
                continue
            out.append(spec(round_no, PHASE_ARBITRATE, "SYSTEM", "METABOLISM",
                            {"agent_id": aid, "amount": per_agent_mu, "reason": "subsistence"}))
        return out

    register_phase4_hook("apply_metabolism", apply_metabolism_stub)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--metabolism", type=int, default=0,
                    help=">0 时启用真实 lifecycle 4.4（config['lifecycle'].ENABLED=true, METABOLISM_MU）")
    ap.add_argument("--metabolism-stub", type=int, default=0,
                    help=">0 时注入 4.4 占位（仅当 4.4 未落地时用于贯通环路）")
    ap.add_argument("--ubi", type=int, default=100)
    ap.add_argument("--trigger", type=int, default=None, help="liquid_trigger_mu 覆盖")
    ap.add_argument("--sustain", type=int, default=None, help="liquid_sustain_mu 覆盖")
    ap.add_argument("--unsecured", type=int, default=None, help="credit_unsecured_base_mu 覆盖")
    args = ap.parse_args()

    from engine.runner import default_config
    cfg = default_config()
    cfg.setdefault("economy", {}).update({
        "UBI_MU": args.ubi, "income_tax_bp": 1000, "wealth_tax_bp": 200,
        "fee_market_bp": 100, "loan_rate_bp": 500, "loan_max_debt_mu": 10000,
    })
    if args.trigger is not None:
        cfg["economy"]["liquid_trigger_mu"] = args.trigger
    if args.sustain is not None:
        cfg["economy"]["liquid_sustain_mu"] = args.sustain
    if args.unsecured is not None:
        cfg["economy"]["credit_unsecured_base_mu"] = args.unsecured
    if args.metabolism > 0:
        cfg["lifecycle"] = {"ENABLED": True, "METABOLISM_MU": args.metabolism}
    if args.metabolism_stub > 0:
        _install_metabolism(args.metabolism_stub)

    world = build_world(args.seed, cfg, n=args.n)
    eng = world["engine"]
    sysacc = ("MARKET", "BANK", "WORLD", "SYSTEM")
    neg_nw_alive_samples = []
    for r in range(args.rounds):
        eng.run_round(r)
        for aid in eng.state.agents:
            if aid in sysacc:
                continue
            if eng.state.agents[aid].get("status") in ("dead", "terminated"):
                continue
            nw = eng.state.net_worth(aid)
            if nw < 0:
                neg_nw_alive_samples.append({
                    "round": r, "agent_id": aid, "net_worth": nw,
                    "cash_L": int(eng.state.cash.get(aid, 0)),
                    "debt": _liq.debt_of(eng.state, aid)})
                break  # 每回合取一条样本足够
    recs = eng.ledger.records
    c = Counter(rec["type"] for rec in recs)

    viols = conservation.check_conservation(eng.state, eng.config)
    h1 = state_hash(eng.state)
    h2 = state_hash(replay_records(recs, verify=False, verify_seals=False))
    h3 = state_hash(replay_records(recs, verify=False, verify_seals=False))

    from obs.econ import econ_metrics
    from obs.antifraud import analyze
    from obs.census import semantic_census
    eco = econ_metrics(recs)
    af = analyze(recs)
    try:
        cen = semantic_census(recs)
        census_hits = {k: v["count"] for k, v in cen["semantic_hits"].items()}
    except Exception as exc:
        census_hits = {"error": repr(exc)}

    # ---- 流动性判死路径分析（T61×T62）----
    borrowers = {r["payload"]["borrower"] for r in recs if r["type"] == "LOAN_ISSUED"}
    death_rounds = sorted(int(r["round"]) for r in recs if r["type"] == "AGENT_DIED")
    agents = sorted(a for a in eng.state.agents if a not in ("MARKET", "BANK", "WORLD", "SYSTEM"))
    alive_final, dead_final = [], []
    for aid in agents:
        stt = eng.state.agents[aid].get("status")
        (alive_final if stt not in ("dead", "terminated") else dead_final).append(aid)
    borrowed_alive = sorted(a for a in alive_final if a in borrowers)
    borrowed_died = sorted(a for a in dead_final if a in borrowers)
    never_borrow_died = sorted(a for a in dead_final if a not in borrowers)
    # 含负净值但仍存活（借贷续命实证：净值<0 但 L 足够 → alive）
    neg_nw_alive = sorted(a for a in alive_final if eng.state.net_worth(a) < 0)
    journal = []
    for aid in neg_nw_alive[:3]:
        v = {"agent_id": aid, "status": eng.state.agents[aid].get("status"),
             "cash_L": int(eng.state.cash.get(aid, 0)),
             "net_worth": eng.state.net_worth(aid),
             "debt": liq_debt(eng.state, aid), "loan_taken": aid in borrowers}
        journal.append(v)

    out = {
        "seed": args.seed, "rounds": args.rounds, "n_agents": args.n,
        "metabolism_mu": args.metabolism if args.metabolism > 0 else 0,
        "metabolism_stub": args.metabolism_stub,
        "total_events": sum(c.values()),
        "SYSTEM_ERROR": c.get("SYSTEM_ERROR", 0),
        "ECONOMY_INVARIANT_VIOLATION": c.get("ECONOMY_INVARIANT_VIOLATION", 0),
        "conservation_ok": len(viols) == 0,
        "replay_parity": (h1 == h2 == h3),
        "first_run_equals_replay": (h1 == h2),
        "econ_counts": {k: c.get(k, 0) for k in ECON_TYPES},
        "obs_econ": {k: eco[k] for k in (
            "money_supply_final", "money_minted_total", "money_burned_total",
            "conservation_ok", "tax_pool_final", "n_transfers", "transfer_volume",
            "gini_cash_final", "n_active_loans", "outstanding_principal")},
        "flags_by_type": af["flags_by_type"],
        "flagged_tx_count": af["flagged_tx_count"],
        "census_hits": census_hits,
        "liquidity_paths": {
            "n_borrowers": len(borrowers),
            "borrowed_alive": borrowed_alive,
            "borrowed_died": borrowed_died,
            "never_borrow_died": never_borrow_died,
            "death_rounds": death_rounds,
            "neg_networth_alive_count": len(neg_nw_alive),
            "neg_networth_alive_journal": journal,
            "neg_networth_alive_rounds": sorted({s["round"] for s in neg_nw_alive_samples}),
            "neg_networth_alive_sample": neg_nw_alive_samples[:5],
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return out


if __name__ == "__main__":
    main()
