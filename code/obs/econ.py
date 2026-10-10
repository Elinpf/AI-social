"""经济 / 生命周期指标（K 类，口径冻结于 v1）。

只读日志、纯函数、确定性；**绝不接受 LLM 判定为输入**（T9 R5）。
`fold_economy` 复刻内核 `replay` 对经济事件的折叠语义（口径与 v1/03 §5 一致），
供守恒校验与经济指标使用；已由测试对拍 `engine.state.money_total`。
"""

from __future__ import annotations

from engine.time import derive_time


def fold_economy(records) -> dict:
    """折叠经济事件得到账务快照（纯整数 mu）。"""
    cash: dict[str, int] = {}
    deposits: dict[str, int] = {}
    loans: dict[str, dict] = {}
    tax_pool = 0
    bank_reserve = 0
    minted = 0
    burned = 0

    def c(a):
        return cash.get(a, 0)

    def setc(a, v):
        cash[a] = int(v)

    for r in records:
        t = r["type"]
        p = r.get("payload") or {}
        if t == "AGENT_BORN":
            aid = p.get("agent_id")
            cash.setdefault(aid, 0)
            deposits.setdefault(aid, 0)
        elif t == "INIT_ENDOW":
            aid = p["agent_id"]
            cash.setdefault(aid, 0)
            setc(aid, c(aid) + int(p["amount"]))
        elif t == "MONEY_MINTED":
            minted += int(p["amount"])
        elif t == "MONEY_BURNED":
            burned += int(p["amount"])
        elif t == "TRANSFER":
            frm, to = p["from"], p["to"]
            amt = int(p["amount"])
            fee = int(p.get("fee", 0))
            setc(frm, c(frm) - amt - fee)
            setc(to, c(to) + amt)
            burned += fee
        elif t == "MARKET_TRADE":
            buyer, seller = p["buyer"], p["seller"]
            amt = int(p["amount"])
            fee = int(p.get("fee", 0))
            setc(buyer, c(buyer) - amt - fee)
            setc(seller, c(seller) + amt)
            burned += fee
        elif t == "TAX_LEVIED":
            aid = p["agent_id"]
            amt = int(p["amount"])
            setc(aid, c(aid) - amt)
            tax_pool += amt
        elif t == "UBI_PAID":
            aid = p["agent_id"]
            amt = int(p["amount"])
            setc(aid, c(aid) + amt)
            tax_pool -= amt
        elif t == "METABOLISM":
            aid = p["agent_id"]
            amt = int(p["amount"])
            setc(aid, c(aid) - amt)
            burned += amt
        elif t == "PENALTY_APPLIED":
            aid = p["agent_id"]
            amt = int(p["amount"])
            setc(aid, c(aid) - amt)
            burned += amt
        elif t == "REVIVE_FEE_PAID":
            aid = p["agent_id"]
            amt = int(p["amount"])
            setc(aid, c(aid) - amt)
            bank_reserve += amt
        elif t == "INTEREST_CHARGED":
            aid = p.get("borrower")
            amt = int(p["amount"])
            setc(aid, c(aid) - amt)
            tax_pool += amt
        elif t == "INTEREST_PAID":
            aid = p["agent_id"]
            amt = int(p["amount"])
            setc(aid, c(aid) + amt)
            bank_reserve -= amt
        elif t == "LOAN_ISSUED":
            lid = p["loan_id"]
            lender = p.get("lender")
            borrower = p["borrower"]
            principal = int(p["principal"])
            if lender is not None:
                setc(lender, c(lender) - principal)
            else:
                minted += principal
            setc(borrower, c(borrower) + principal)
            loans[lid] = {
                "loan_id": lid, "lender": lender, "borrower": borrower,
                "principal": principal,
                "outstanding": int(p.get("outstanding", principal)),
                "status": "active",
            }
        elif t == "LOAN_REPAY":
            lid = p["loan_id"]
            amt = int(p["amount"])
            loan = loans.get(lid)
            if loan is not None:
                loan["outstanding"] = int(loan.get("outstanding", 0)) - amt
                if loan["outstanding"] <= 0:
                    loan["status"] = "repaid"
            payer = p.get("payer")
            if payer is not None:
                setc(payer, c(payer) - amt)
        elif t == "LOAN_DEFAULT":
            lid = p["loan_id"]
            loan = loans.get(lid)
            if loan is not None:
                loan["status"] = "written_off"
                loan["outstanding"] = int(p.get("outstanding", loan.get("outstanding", 0)))
        elif t == "DEPOSIT":
            aid = p["agent_id"]
            amt = int(p["amount"])
            setc(aid, c(aid) - amt)
            deposits[aid] = deposits.get(aid, 0) + amt
        elif t == "WITHDRAW":
            aid = p["agent_id"]
            amt = int(p["amount"])
            setc(aid, c(aid) + amt)
            deposits[aid] = deposits.get(aid, 0) - amt

    supply = sum(cash.values()) + sum(deposits.values()) + tax_pool + bank_reserve
    return {
        "cash": cash, "deposits": deposits, "loans": loans,
        "tax_pool": tax_pool, "bank_reserve": bank_reserve,
        "money_minted_total": minted, "money_burned_total": burned,
        "money_supply": supply,
    }


def gini(values: list[int]) -> float:
    """基尼系数（确定性、整数输入；空/全零 -> 0.0）。"""
    vals = sorted(int(v) for v in values)
    n = len(vals)
    if n == 0:
        return 0.0
    total = sum(vals)
    if total <= 0:
        return 0.0
    cum = 0
    weighted = 0
    for i, v in enumerate(vals, start=1):
        weighted += i * v
    # G = (2*Σ i*x_i)/(n*Σx) - (n+1)/n
    g = (2.0 * weighted) / (n * total) - (n + 1.0) / n
    return round(max(0.0, g), 6)


def econ_metrics(records, params=None) -> dict:
    """`metrics.econ`（K 类，口径冻结）。"""
    eco = fold_economy(records)
    txs = [r for r in records if r["type"] in ("TRANSFER", "MARKET_TRADE")]
    volume = sum(int((r.get("payload") or {}).get("amount", 0)) for r in txs)
    residual = (eco["money_minted_total"] - eco["money_burned_total"]) - eco["money_supply"]
    cash_vals = [int(v) for v in eco["cash"].values()]
    return {
        "money_supply_final": int(eco["money_supply"]),
        "money_minted_total": int(eco["money_minted_total"]),
        "money_burned_total": int(eco["money_burned_total"]),
        "conservation_residual": int(residual),
        "conservation_ok": bool(residual == 0),
        "tax_pool_final": int(eco["tax_pool"]),
        "bank_reserve_final": int(eco["bank_reserve"]),
        "n_transfers": len(txs),
        "transfer_volume": int(volume),
        "gini_cash_final": gini(cash_vals),
        "n_agents_with_account": len(eco["cash"]),
        "n_active_loans": sum(1 for l in eco["loans"].values()
                              if l.get("status") in ("active", "overdue")),
        "outstanding_principal": int(sum(
            int(l.get("outstanding", 0)) for l in eco["loans"].values()
            if l.get("status") in ("active", "overdue"))),
    }


def lifecycle_metrics(records, params=None) -> dict:
    """`metrics.lifecycle`（K 类，口径冻结）。"""
    born = set()
    for r in records:
        if r["type"] == "AGENT_BORN":
            born.add((r.get("payload") or {}).get("agent_id"))
    ever_dead = set()
    ever_revived = set()
    deaths = 0
    revivals = 0
    status = {}
    for r in records:
        p = r.get("payload") or {}
        if r["type"] == "AGENT_DIED":
            deaths += 1
            ever_dead.add(p.get("agent_id"))
        elif r["type"] == "AGENT_REVIVED":
            revivals += 1
            ever_revived.add(p.get("agent_id"))
        elif r["type"] == "STATE_CHANGE":
            status[p.get("agent_id")] = p.get("to")
    n = len([a for a in born if a is not None])
    dead_now = len(ever_dead - ever_revived)
    alive = n - dead_now
    survival_rate = round(alive / n, 6) if n else 0.0
    return {
        "n_agents_born": n,
        "n_alive_final": alive,
        "n_dead_final": dead_now,
        "death_events": deaths,
        "revival_events": revivals,
        "survival_rate": survival_rate,
        "n_state_changes": sum(1 for r in records if r["type"] == "STATE_CHANGE"),
    }


def rounds_per_week(time_cfg: dict | None) -> int:
    cfg = time_cfg or {}
    rps = int(cfg.get("ROUNDS_PER_SLOT", 3))
    spd = len(cfg.get("SLOTS_PER_DAY", ["m", "a", "e", "n"]))
    dpw = int(cfg.get("DAYS_PER_WEEK", 7))
    return rps * spd * dpw


__all__ = ["fold_economy", "gini", "econ_metrics", "lifecycle_metrics", "rounds_per_week"]
