"""P2·交易指标（`metrics.econ_loop.exchange`）——T134。

口径权威：`v1.1/08-engine-stats-extension.md §1.2 R`（T129 登记）。**全 D 类、只读日志、纯函数、
两次重算字节相等、`llm_judged_metric_count==0`**。

交付：
  1) `distinct_sellers_excl_world` —— **排除 world 的卖方去重数**（G-P1-1 真判据）；
  2) `distinct_buyers_excl_world`（对称）；并列输出含 world 的 `distinct_sellers/buyers`；
  3) `agent_agent_share`：分子 = |MARKET_TRADE: buyer&seller 均∈Agents| + |EXCHANGE_SETTLED: parties 双方均∈Agents|，
     分母 = |MARKET_TRADE| + |EXCHANGE_SETTLED|（**写死，与 08 §1.2 R 一致**）；
  4) `V2a`（工具可用）与 `V2b`（AI 真交易）**分列**。

world 标识：`{WORLD, MARKET, BANK, SYSTEM, TAX_POOL}`；agent = `AGENT_BORN` 出现过的 id。
对手方判定优先用一等字段 `counterparty`（08 §1.2 R，A1），否则回退到 seller/buyer 主体 id。
"""

from __future__ import annotations

from .folds import agents as _agents

WORLD_IDS = frozenset({"WORLD", "MARKET", "BANK", "SYSTEM", "TAX_POOL"})


def _p(r):
    return r.get("payload") or {}


def exchange_metrics(records) -> dict:
    agents = set(_agents(records))

    def is_agent(x) -> bool:
        return x is not None and x not in WORLD_IDS and x in agents

    trades = [r for r in records if r["type"] == "MARKET_TRADE"]
    exchs = [r for r in records if r["type"] == "EXCHANGE_SETTLED"]

    sellers, buyers = [], []
    n_agent_trade = 0
    for r in trades:
        p = _p(r)
        sellers.append(p.get("seller"))
        buyers.append(p.get("buyer"))
        if is_agent(p.get("buyer")) and is_agent(p.get("seller")):
            n_agent_trade += 1

    n_agent_exch = 0
    for r in exchs:
        parties = _p(r).get("parties") or []
        if len(parties) >= 2 and all(is_agent(x) for x in parties):
            n_agent_exch += 1

    d_sellers = len({s for s in sellers if s is not None})
    d_buyers = len({b for b in buyers if b is not None})
    d_sellers_excl = len({s for s in sellers if is_agent(s)})
    d_buyers_excl = len({b for b in buyers if is_agent(b)})

    num = n_agent_trade + n_agent_exch
    den = len(trades) + len(exchs)
    share = round(num / den, 6) if den else 0.0

    # V2a：工具可用（意图/事件侧可观测代理；intent 不落日志，故用 OFFER_CREATED/成交事件代理）
    offer_created = sum(1 for r in records if r["type"] == "OFFER_CREATED")
    offer_accepted = sum(1 for r in records if r["type"] == "OFFER_ACCEPTED")
    v2a = bool((offer_created > 0 or len(trades) > 0 or len(exchs) > 0) and offer_accepted > 0)
    # V2b：AI 真交易
    v2b = bool(d_sellers_excl > 1)

    return {
        "n_market_trade": len(trades),
        "n_exchange_settled": len(exchs),
        "distinct_sellers": d_sellers,
        "distinct_sellers_excl_world": d_sellers_excl,
        "distinct_buyers": d_buyers,
        "distinct_buyers_excl_world": d_buyers_excl,
        "agent_agent_deals": num,
        "all_deals": den,
        "agent_agent_share": share,
        "V2a_tool_available": v2a,
        "V2b_ai_trades": v2b,
        "V2a_components": {"offer_created": offer_created, "offer_accepted": offer_accepted,
                           "market_trade": len(trades), "exchange_settled": len(exchs)},
        "llm_judged_metric_count": 0,
    }


__all__ = ["exchange_metrics", "WORLD_IDS"]
