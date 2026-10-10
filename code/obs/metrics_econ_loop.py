"""v2 经济循环指标（`metrics.econ_loop.*`，D 类）——T101 经济半侧。

口径权威：`v2/01-economy-substrate.md §2.1–§2.3、§5.1`；事件字段：`v1.1/08 §1.2`（T90 登记）。

只读日志、纯函数、`llm_calls==0`、`llm_judged_metric_count==0`、两次重算字节相等。

口径与来源（凡不确定的均显式标注，不臆造）：
  - `M(t)`：`TURN_SEAL.money_supply`（逐回合序列）→ `M_min/M_final/M_max`。
  - `M_target`：创世铸币总额 `Σ MONEY_MINTED{reason=genesis}`（日志确定性可算；作为"目标总量"基准）。
  - 流通速度 `V` = `(Σ TRANSFER.amount + Σ MARKET_TRADE.amount) / M_ref`，`M_ref=mean(M(t))`。
  - 总产出 `Y` = `Σ PRODUCE: (qty_milli/1000) × p_ref_mu[good]`（`p_ref_mu` 为商品注册表参考价，仅统计计价）。
    注意：`p_ref` 权威在 `engine/production.GOODS`；观测层不可 import 写路径，故此处**镜像**该表，
    并由 `tests/test_obs_econ_loop.py::test_pref_mirror_matches_engine` **交叉校验**（漂移即测试红）。
  - 中位工资：`TRANSFER{reason∈{wage,salary}}` 收款额的中位数（无则 `None`）。
  - Gini：净值分布（复用 `fold_economy` 的现金/存款/债务）。
  - 铸销平衡 `|minted−burned|/M_final`；`tax_pool_final`。
  - 价格离散度 `CV`：`MARKET_TRADE` 中带 `good_id` 且有 `qty>0` 的成交价 `amount/qty` 的 `σ/μ`（分商品）。
"""

from __future__ import annotations

from .econ import fold_economy, gini

# 镜像 engine/production.GOODS 的 p_ref_mu（仅统计计价参考价）；由测试交叉校验防漂移。
GOODS_PREF_MU = {
    "food": 100, "material": 150, "tool": 500, "service": 200, "art": 1000,
}


def _money_series(records):
    ser = []
    for r in records:
        if r["type"] == "TURN_SEAL":
            ms = (r.get("payload") or {}).get("money_supply")
            if ms is not None:
                ser.append((int(r["round"]), int(ms)))
    ser.sort()
    return [v for _, v in ser]


def econ_loop_metrics(records, params=None) -> dict:
    from .metrics_exchange import exchange_metrics as _exchange  # noqa: local import avoids cycle
    eco = fold_economy(records)
    series = _money_series(records)
    M_final = series[-1] if series else eco["money_supply"]
    M_min = min(series) if series else M_final
    M_max = max(series) if series else M_final
    M_mean = (sum(series) // len(series)) if series else M_final

    genesis_mint = 0
    for r in records:
        if r["type"] == "MONEY_MINTED" and (r.get("payload") or {}).get("reason") == "genesis":
            genesis_mint += int((r.get("payload") or {}).get("amount", 0))
    M_target = genesis_mint or (series[0] if series else 0)

    # V
    vol = 0
    for r in records:
        if r["type"] in ("TRANSFER", "MARKET_TRADE"):
            vol += int((r.get("payload") or {}).get("amount", 0))
    V = round(vol / M_mean, 6) if M_mean else 0.0

    # Y（单位与计价）
    y_units: dict[str, int] = {}
    y_mu = 0
    for r in records:
        if r["type"] != "PRODUCE":
            continue
        p = r.get("payload") or {}
        g = p.get("good_id")
        q = int(p.get("qty", 0))          # milli 单位（1000 == 1 单位）
        y_units[g] = y_units.get(g, 0) + q
        y_mu += (q * int(GOODS_PREF_MU.get(g, 0))) // 1000
    Y_units_total = sum(y_units.values())

    # 中位工资
    wages = []
    for r in records:
        if r["type"] == "TRANSFER":
            p = r.get("payload") or {}
            if str(p.get("reason")) in ("wage", "salary"):
                wages.append(int(p.get("amount", 0)))
    wages.sort()
    med_wage = None
    if wages:
        n = len(wages)
        med_wage = wages[n // 2] if n % 2 else (wages[n // 2 - 1] + wages[n // 2]) // 2

    # Gini（净值）
    nw = {}
    for a in sorted(set(list(eco["cash"]) + list(eco["deposits"]))):
        liab = sum(int(l.get("outstanding", 0)) for l in eco["loans"].values()
                   if l.get("borrower") == a and l.get("status") in ("active", "overdue"))
        nw[a] = int(eco["cash"].get(a, 0)) + int(eco["deposits"].get(a, 0)) - liab

    # 价格离散度
    prices: dict[str, list] = {}
    for r in records:
        if r["type"] == "MARKET_TRADE":
            p = r.get("payload") or {}
            g, q, amt = p.get("good_id"), int(p.get("qty", 0)), int(p.get("amount", 0))
            if g and q > 0:
                prices.setdefault(g, []).append(amt * 1000 / q)
    price_cv = {}
    for g in sorted(prices):
        vals = prices[g]
        n = len(vals)
        if n == 0:
            continue
        mu = sum(vals) / n
        var = sum((v - mu) ** 2 for v in vals) / n
        price_cv[g] = round((var ** 0.5) / mu, 6) if mu else 0.0

    minted, burned = eco["money_minted_total"], eco["money_burned_total"]
    # 铸销平衡：**注意** 累计 (minted−burned) ≡ M_final（守恒恒等式）→ 用累计值会"永远=1.0"（假绿）。
    # 故改为**窗口口径**：最近一回合净铸销 / M_final（无事件则 0.0）。
    per_round_mb: dict[int, int] = {}
    for r in records:
        p = r.get("payload") or {}
        if r["type"] == "MONEY_MINTED":
            per_round_mb[int(r["round"])] = per_round_mb.get(int(r["round"]), 0) + int(p.get("amount", 0))
        elif r["type"] == "MONEY_BURNED":
            per_round_mb[int(r["round"])] = per_round_mb.get(int(r["round"]), 0) - int(p.get("amount", 0))
    last_round = max((int(r["round"]) for r in records), default=-1)
    net_last = per_round_mb.get(last_round, 0)
    return {
        "M_final": int(M_final), "M_min": int(M_min), "M_max": int(M_max), "M_mean": int(M_mean),
        "M_target": int(M_target),
        "M_final_over_target": round(M_final / M_target, 6) if M_target else 0.0,
        "M_min_over_target": round(M_min / M_target, 6) if M_target else 0.0,
        "M_never_negative": bool(M_min >= 0),
        "V": V,
        "Y_mu": int(y_mu), "Y_units_total_milli": int(Y_units_total),
        "Y_units_by_good": {k: y_units[k] for k in sorted(y_units)},
        "median_wage_mu": med_wage,
        "gini_net_worth": gini(list(nw.values())),
        "tax_pool_final": int(eco["tax_pool"]),
        "public_goods_spend_mu": 0,   # 无专事件前为 0（不臆造）；公共品预算执行额待 econ 事件
        "minted_total": int(minted), "burned_total": int(burned),
        "net_mint_burn_last_round": int(net_last),
        "mint_burn_balance_window": round(abs(net_last) / M_final, 6) if M_final else 0.0,
        "price_cv": price_cv,
        "price_cv_mean": round(sum(price_cv.values()) / len(price_cv), 6) if price_cv else 0.0,
        "n_produce": sum(1 for r in records if r["type"] == "PRODUCE"),
        "exchange": _exchange(records),
        "llm_judged_metric_count": 0,
    }


__all__ = ["econ_loop_metrics", "GOODS_PREF_MU"]
