"""P2·交易指标（`metrics.econ_loop.exchange`）——T134。

口径权威：`v1.1/08-engine-stats-extension.md §1.2 R`（T129 登记）。**全 D 类、只读日志、纯函数、
两次重算字节相等、`llm_judged_metric_count==0`**。

交付：
  1) `distinct_sellers_excl_world` —— **排除 world 的卖方去重数**（G-P1-1 真判据）；
  2) `distinct_buyers_excl_world`（对称）；并列输出含 world 的 `distinct_sellers/buyers`；
  3) `agent_agent_share`：分子 = |MARKET_TRADE: buyer&seller 均∈Agents| + |EXCHANGE_SETTLED: parties 双方均∈Agents|，
     分母 = |MARKET_TRADE| + |EXCHANGE_SETTLED|（**写死，与 08 §1.2 R 一致**）；
  4) `V2a`（工具可用）与 `V2b`（AI 真交易）**分列**。V2a **仅认 `kind:"sale"` 的市场挂单或真实成交**，
     社交伪要约（`kind:"trade"`/`terms:{amount_mu}`，见 `life/settlement.py`）不计入 —— 由
     `offer_source_split()` 按来源/kind 拆分给出证据（T136 前置）。

world 标识：`{WORLD, MARKET, BANK, SYSTEM, TAX_POOL}`；agent = `AGENT_BORN` 出现过的 id。
对手方判定优先用一等字段 `counterparty`（08 §1.2 R，A1），否则回退到 seller/buyer 主体 id。
**卖方/买方口径 = 所有成交事件的并集**：`MARKET_TRADE.seller/buyer` ∪ `EXCHANGE_SETTLED` 商品腿
`from/to`（08 §1.2 R：`distinct_sellers_excl_world` 是「卖方去重排除 world」，覆盖两条成交出口）。
"""

from __future__ import annotations

import collections

from .folds import agents as _agents

WORLD_IDS = frozenset({"WORLD", "MARKET", "BANK", "SYSTEM", "TAX_POOL"})

# OFFER_CREATED 存在**两套 schema**，来源不同、语义不同（T136 前置要求：按来源/kind 拆分）：
#   real_sale     : kind=="sale"，terms 含 {good_id, price_mu, qty}（life/agent.py::_maybe_offer →
#                   INTENT.ECON.OFFER，真正的市场挂单/发现路径，`to:[]` 广播）
#   social_pseudo : kind=="trade"，terms 仅 {amount_mu}（life/settlement.py::_m6_specs，模板
#                   `polite_reject`/`counter_propose` 产的社交礼仪要约，非真实交易）
#   other         : 其余/未知 schema —— **如实单列，绝不并入任何一类**
# V2a（工具可用）只认 real_sale（或真实成交），**不得拿社交伪要约当证据**。
REAL_SALE = "real_sale"
SOCIAL_PSEUDO = "social_pseudo"
OFFER_OTHER = "other"


def _p(r):
    return r.get("payload") or {}


def classify_offer(payload) -> str:
    """把一条 `OFFER_CREATED` 的 payload 归入 real_sale / social_pseudo / other（纯函数、确定性）。"""
    terms = (payload or {}).get("terms") or {}
    kind = str((payload or {}).get("kind", "") or "").lower()
    has_good = (isinstance(terms.get("good_id"), str)
                and "price_mu" in terms and "qty" in terms)
    if kind == "sale" and has_good:
        return REAL_SALE
    if kind == "trade" and (not terms or set(terms) <= {"amount_mu"}):
        return SOCIAL_PSEUDO
    return OFFER_OTHER


def offer_source_split(records) -> dict:
    """按来源/kind 拆分 `OFFER_CREATED`（及按同一分类拆 `OFFER_ACCEPTED`）。

    确定性：计数，无排序歧义；两次调用字节相等。未知/断链的 accept 单列 `accepted_unknown`。
    """
    created = collections.Counter()
    oid_class: dict = {}
    for r in records:
        if r["type"] != "OFFER_CREATED":
            continue
        p = _p(r)
        c = classify_offer(p)
        created[c] += 1
        oid = p.get("offer_id")
        if oid is not None and oid not in oid_class:
            oid_class[oid] = c
    accepted = collections.Counter()
    for r in records:
        if r["type"] != "OFFER_ACCEPTED":
            continue
        accepted[oid_class.get(_p(r).get("offer_id"), "unknown")] += 1
    return {
        "created_total": sum(created.values()),
        "created_real_sale": created.get(REAL_SALE, 0),
        "created_social_pseudo": created.get(SOCIAL_PSEUDO, 0),
        "created_other": created.get(OFFER_OTHER, 0),
        "accepted_total": sum(accepted.values()),
        "accepted_real_sale": accepted.get(REAL_SALE, 0),
        "accepted_social_pseudo": accepted.get(SOCIAL_PSEUDO, 0),
        "accepted_other": accepted.get(OFFER_OTHER, 0),
        "accepted_unknown": accepted.get("unknown", 0),
    }


def dropped_reconcile(records) -> dict:
    """`DROPPED{insufficient_goods}` 的**离线复算**：区分「要约售罄」与「真缺货」。

    引擎口径（econ `offer_exhausted`）只覆盖**同回合**超额认购；跨回合的被接受仍落
    `insufficient_goods`。离线口径更权威：某 `DROPPED{insufficient_goods}` 的 `offer_id`
    **此前（seq 更小）已出现过 `EXCHANGE_SETTLED`** ⇒ 该要约已成交过 ⇒ 这次是**售罄**，
    重分类为 `offer_exhausted`。同/跨回合再细分。

    纯函数、只读、确定性。
    """
    settled = collections.defaultdict(list)  # offer_id -> [(round, seq)]
    for r in records:
        if r["type"] == "EXCHANGE_SETTLED":
            oid = (_p(r).get("meta") or {}).get("offer_id")
            if oid is not None:
                settled[oid].append((int(r.get("round", 0)), int(r.get("seq", 0))))
    engine = collections.Counter()
    offline = collections.Counter()
    same_round = cross_round = 0
    for r in records:
        if r["type"] != "DROPPED":
            continue
        p = _p(r)
        reason = p.get("reason")
        engine[reason] += 1
        oid = p.get("offer_id")
        seq, rnd = int(r.get("seq", 0)), int(r.get("round", 0))
        prior = [x for x in settled.get(oid, ()) if x[1] < seq] if oid is not None else []
        if reason == "insufficient_goods" and prior:
            offline["offer_exhausted"] += 1
            if any(pr == rnd for (pr, _s) in prior):
                same_round += 1
            else:
                cross_round += 1
        else:
            offline[reason] += 1
    return {
        "engine": {k: engine[k] for k in sorted(engine) if k},
        "offline": {k: offline[k] for k in sorted(offline) if k},
        "reclassified": same_round + cross_round,
        "reclassified_same_round": same_round,
        "reclassified_cross_round": cross_round,
    }


def exchange_metrics(records) -> dict:
    agents = set(_agents(records))

    def is_agent(x) -> bool:
        return x is not None and x not in WORLD_IDS and x in agents

    trades = [r for r in records if r["type"] == "MARKET_TRADE"]
    exchs = [r for r in records if r["type"] == "EXCHANGE_SETTLED"]

    # 口径（08 §1.2 R）：`distinct_sellers_excl_world` = **所有成交事件**的卖方去重、排除 world。
    #   卖方身份：MARKET_TRADE.seller ∪ EXCHANGE_SETTLED 商品腿 `from`（交货方=卖方）。
    #   ⚠️ 只读 MARKET_TRADE 会**漏掉整条 exchange 路径**（v2 的 agent↔agent 成交全在
    #   EXCHANGE_SETTLED）→ 卖方去重=0 的假象 → 误判「无 agent 间交易」。
    sellers, buyers = [], []               # 全部成交（含 world）
    mt_sellers, mt_buyers = [], []         # 细分：MARKET_TRADE
    ex_sellers, ex_buyers = [], []         # 细分：EXCHANGE_SETTLED（按商品腿 from/to）
    n_agent_trade = 0
    for r in trades:
        p = _p(r)
        sellers.append(p.get("seller")); buyers.append(p.get("buyer"))
        mt_sellers.append(p.get("seller")); mt_buyers.append(p.get("buyer"))
        if is_agent(p.get("buyer")) and is_agent(p.get("seller")):
            n_agent_trade += 1

    n_agent_exch = 0
    for r in exchs:
        p = _p(r)
        parties = p.get("parties") or []
        if len(parties) >= 2 and all(is_agent(x) for x in parties):
            n_agent_exch += 1
        for g in ((p.get("legs") or {}).get("goods") or []):
            sellers.append(g.get("from")); buyers.append(g.get("to"))
            ex_sellers.append(g.get("from")); ex_buyers.append(g.get("to"))

    d_sellers = len({s for s in sellers if s is not None})
    d_buyers = len({b for b in buyers if b is not None})
    d_sellers_excl = len({s for s in sellers if is_agent(s)})
    d_buyers_excl = len({b for b in buyers if is_agent(b)})
    # 细分（透明，便于定位卖方来自哪条路径）
    d_sellers_mt = len({s for s in mt_sellers if is_agent(s)})
    d_sellers_ex = len({s for s in ex_sellers if is_agent(s)})
    d_buyers_mt = len({b for b in mt_buyers if is_agent(b)})
    d_buyers_ex = len({b for b in ex_buyers if is_agent(b)})

    # 对手方（08 §1.2 R A1 一等字段）：与「卖方」口径不同，单独暴露以免混淆。
    #   卖方 = 交货/出货方（goods.from / MARKET_TRADE.seller）；counterparty = 该笔的**另一侧**。
    cp = [_p(r).get("counterparty") for r in trades + exchs]
    d_cp_excl = len({x for x in cp if is_agent(x)})

    num = n_agent_trade + n_agent_exch
    den = len(trades) + len(exchs)
    share = round(num / den, 6) if den else 0.0

    # V2a：工具可用（意图/事件侧可观测代理；intent 不落日志）。
    #   与 T134 口径一致，仅把「offer 计数」换成**只认 real_sale**的计数：
    #   A=有 real_sale 挂单或真实成交；B=有 **real_sale** 被接受。社交伪要约不计入 A/B。
    split = offer_source_split(records)
    real_created = split["created_real_sale"]
    real_accepted = split["accepted_real_sale"]
    traded = len(trades) + len(exchs)
    v2a = bool((real_created > 0 or traded > 0) and real_accepted > 0)
    # V2b：AI 真交易
    v2b = bool(d_sellers_excl > 1)

    return {
        "n_market_trade": len(trades),
        "n_exchange_settled": len(exchs),
        "distinct_sellers": d_sellers,
        "distinct_sellers_excl_world": d_sellers_excl,
        "distinct_sellers_excl_world_market_trade": d_sellers_mt,
        "distinct_sellers_excl_world_exchange": d_sellers_ex,
        "distinct_buyers": d_buyers,
        "distinct_buyers_excl_world": d_buyers_excl,
        "distinct_buyers_excl_world_market_trade": d_buyers_mt,
        "distinct_buyers_excl_world_exchange": d_buyers_ex,
        "distinct_counterparty_excl_world": d_cp_excl,
        "agent_agent_deals": num,
        "all_deals": den,
        "agent_agent_share": share,
        "V2a_tool_available": v2a,
        "V2b_ai_trades": v2b,
        "V2a_components": {"offer_created": split["created_total"],
                           "offer_created_real_sale": real_created,
                           "offer_created_social_pseudo": split["created_social_pseudo"],
                           "offer_created_other": split["created_other"],
                           "offer_accepted": split["accepted_total"],
                           "offer_accepted_real_sale": real_accepted,
                           "market_trade": len(trades), "exchange_settled": len(exchs)},
        "offer_source_split": split,
        "dropped_reconcile": dropped_reconcile(records),
        "llm_judged_metric_count": 0,
    }


__all__ = ["exchange_metrics", "offer_source_split", "classify_offer", "dropped_reconcile",
           "WORLD_IDS", "REAL_SALE", "SOCIAL_PSEUDO", "OFFER_OTHER"]
