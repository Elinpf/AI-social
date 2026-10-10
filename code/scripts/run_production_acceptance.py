"""T91 验收证据：v2 P1 物理层（生产/库存/双账本守恒/M(t)≥0/保底）。

用法： python scripts/run_production_acceptance.py [--rounds 84] [--n 20] [--seed 42]
输出： PRODUCE 计数与分商品、商品双账本守恒、M(t) 全程、收入 vs 代谢、事件分布、replay。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import conservation
from engine.replay import replay_records
from engine.state import money_total, state_hash
from engine.runner import default_config
from orchestration.integration import build_world


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--metabolism", type=int, default=None)
    ap.add_argument("--production-off", action="store_true", help="生产层开关关闭（消融）")
    ap.add_argument("--fallback-on", action="store_true",
                    help="开启 C 层兜底铸币（policy.economy.fallback_mint_enabled）；默认 off")
    args = ap.parse_args()

    cfg = default_config()
    if args.production_off:
        cfg.setdefault("production", {})["enabled"] = False
    # C 层兜底铸币：off=默认（policy.economy.fallback_mint_enabled=false）；on 时显式置位（写进证据）
    if args.fallback_on:
        cfg.setdefault("economy", {}).update(
            {"fallback_mint_enabled": True, "fallback_issue_max_mu": 20000})
    if args.metabolism is not None:
        cfg["lifecycle"] = {"ENABLED": True, "METABOLISM_MU": args.metabolism}
    world = build_world(args.seed, cfg, n=args.n)
    eng = world["engine"]
    m_curve = []
    for r in range(args.rounds):
        eng.run_round(r)
        m_curve.append(money_total(eng.state))
    recs = eng.ledger.records
    c = Counter(rec["type"] for rec in recs)

    # ---- 商品双账本守恒（从日志核算，与 kernel check_all 独立）----
    produce_by_good, consume_by_good = Counter(), Counter()
    sum_produce = sum_overflow = sum_deprec = sum_consume = 0
    for rec in recs:
        t, p = rec["type"], (rec.get("payload") or {})
        if t == "PRODUCE":
            q = int(p.get("qty", 0)); produce_by_good[p.get("good_id")] += q; sum_produce += q
        elif t == "CONSUME":
            q = int(p.get("qty", 0)); consume_by_good[p.get("good_id")] += q; sum_consume += q
        elif t == "PRODUCE_OVERFLOW":
            sum_overflow += int(p.get("qty_dropped", 0))
        elif t == "DEPRECIATE":
            sum_deprec += int(p.get("delta_mu", 0))
    inv_total = sum(int(q) for o, gs in (getattr(eng.state, "inventory", {}) or {}).items()
                    for q in gs.values())
    goods_ok = (sum_produce == sum_consume + inv_total + sum_overflow + sum_deprec)

    # ---- 收入 vs 代谢（obs 口径 I_eff；未达则如实报）----
    from obs.antifraud import analyze, ie_eff
    af = analyze(recs)
    ie = ie_eff(recs, af["tx_flags"])
    incomes = sorted(max(0, v["I_eff"]) for v in ie.values()) if ie else []
    import statistics
    median_income = int(statistics.median(incomes)) if incomes else 0
    metab = int((cfg.get("lifecycle") or {}).get("METABOLISM_MU",
                (cfg.get("policy", {}).get("lifecycle", {}) or {}).get("metabolism_mu", 0)))

    h1 = state_hash(eng.state)
    h2 = state_hash(replay_records(recs, verify=False, verify_seals=False))
    fb = sum(1 for r in recs if r["type"] == "MONEY_MINTED"
             and (r.get("payload") or {}).get("reason") == "fallback_mint")
    # ---- 根因钉死三件套（Leader 要求）----
    sellers = Counter()
    market_volume = 0
    for r in recs:
        if r["type"] == "MARKET_TRADE":
            p = r.get("payload") or {}
            sellers[p.get("seller")] += 1
            market_volume += int(p.get("amount", 0))
    n_mt = sum(sellers.values())
    top_seller_share = (max(sellers.values()) / n_mt) if n_mt else 0.0
    ivals = sorted(v["I_eff"] for v in ie.values()) if ie else []

    def _pct(xs, q):
        if not xs:
            return 0
        return xs[min(len(xs) - 1, int(q * (len(xs) - 1)))]
    pos_ratio = (sum(1 for x in ivals if x > 0) / len(ivals)) if ivals else 0.0
    minted_by_reason = Counter()
    metab_total = 0
    for r in recs:
        p = r.get("payload") or {}
        if r["type"] == "MONEY_MINTED":
            minted_by_reason[p.get("reason", "?")] += int(p.get("amount", 0))
        elif r["type"] == "METABOLISM":
            metab_total += int(p.get("amount", 0))
    out = {
        "market_trade_count": n_mt, "market_volume_mu": market_volume,
        "market_distinct_sellers": len(sellers), "market_top_seller_share": round(top_seller_share, 4),
        "income_p50_ieff": _pct(ivals, 0.5), "income_p90_ieff": _pct(ivals, 0.9),
        "income_max_ieff": (max(ivals) if ivals else 0),
        "income_positive_ratio": round(pos_ratio, 4),
        "minted_by_reason": dict(minted_by_reason), "metabolism_total_mu": metab_total,
        "seed": args.seed, "rounds": args.rounds, "n_agents": args.n,
        "total_events": sum(c.values()),
        "SYSTEM_ERROR": c.get("SYSTEM_ERROR", 0),
        "ECONOMY_INVARIANT_VIOLATION": c.get("ECONOMY_INVARIANT_VIOLATION", 0),
        "conservation_ok": len(conservation.check_conservation(eng.state, eng.config)) == 0,
        "replay_parity": (h1 == h2),
        "M_min": min(m_curve), "M_max": max(m_curve), "M_final": m_curve[-1],
        "M_min_gt0": min(m_curve) > 0,
        "fallback_mint_events": fb,
        "PRODUCE": c.get("PRODUCE", 0), "CONSUME": c.get("CONSUME", 0),
        "DEPRECIATE": c.get("DEPRECIATE", 0), "PRODUCE_OVERFLOW": c.get("PRODUCE_OVERFLOW", 0),
        "produce_sum_milli": sum_produce, "consume_sum_milli": sum_consume,
        "inventory_sum_milli": inv_total, "overflow_sum_milli": sum_overflow,
        "deprec_sum_milli": sum_deprec,
        "goods_ledger_conserved": goods_ok,
        "produce_by_good": dict(sorted(produce_by_good.items())),
        "median_income_ieff": median_income, "metabolism_mu": metab,
        "median_income_ge_metabolism": (median_income >= metab),
        "econ_counts": {k: c.get(k, 0) for k in (
            "TRANSFER", "MARKET_TRADE", "DEPOSIT", "TAX_LEVIED", "UBI_PAID",
            "INTEREST_CHARGED", "LOAN_ISSUED", "LOAN_DEFAULT", "PENALTY_APPLIED",
            "METABOLISM", "AGENT_DIED", "AGENT_REVIVED", "PRODUCE", "CONSUME")},
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return out


if __name__ == "__main__":
    main()
