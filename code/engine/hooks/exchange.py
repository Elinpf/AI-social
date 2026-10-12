"""P2 engine 交易/契约原语（v2/04）：`apply_exchange`@4.1、`apply_contracts`@4.2（实现）。

契约（同 4.x）：纯函数 `fn(state, round_no, ctx) -> list[EventSpec]`；整数、不调 LLM、emit 守 ADR-08。

- `apply_exchange`：一笔「双边同意、原子、零和」的交换结算 → `EXCHANGE_SETTLED`
  （多腿商品/货币；`parties` 按 `agent_id` 升序应用消除顺序套利；任一校验不过整笔拒绝）。
- `apply_contracts`：复用 `OFFER_*→CONTRACT_*` 生命周期，**确定性违约判定**；软判定只产布尔且冻结进
  `LLM_JUDGMENT`（本实现只用确定性判定；软判定调用点预留，不在此直接改金额）。
- 开关 `exchange.enabled`（默认 true）：**语义 = agent↔agent 成交**；OFF → 不产成交事件 + 审计
  `DROPPED{reason/flag=exchange_disabled}`，**不 fail-loud**（world 市场保留，由 settle_market 处理）。
- 可转让：`production.is_transferable(good)`（默认 true；service=False → 经 inventory 的腿拒绝）。
"""

from __future__ import annotations

from ..constants import PHASE_ARBITRATE
from ..events import spec
from .. import production as P

P4 = PHASE_ARBITRATE

_SYSTEM = ("MARKET", "BANK", "WORLD", "SYSTEM", "TAX_POOL")


# ---------------------------------------------------------------- 开关
def exchange_enabled(ctx) -> bool:
    """`policy.exchange.enabled` / runtime `config.exchange.enabled`，默认 true（行为不变）。"""
    cfg = getattr(ctx, "config", None)
    if isinstance(cfg, dict):
        rt = cfg.get("exchange")
        if isinstance(rt, dict) and "enabled" in rt:
            return bool(rt["enabled"])
        pol = cfg.get("policy")
        if isinstance(pol, dict):
            e = pol.get("exchange")
            if isinstance(e, dict) and "enabled" in e:
                return bool(e["enabled"])
    return True


def _is_agent(state, x) -> bool:
    return isinstance(x, str) and x in state.agents and x not in _SYSTEM


def _cash(state, a) -> int:
    return int(state.cash.get(a, 0))


def _inv_get(state, owner, good) -> int:
    return P.inv_get(getattr(state, "inventory", {}) or {}, owner, good)


# ---------------------------------------------------------------- deal 归一
def normalize_deal(state, intent: dict) -> dict | None:
    """把 life 意图归一为内部 deal：{parties(升序), goods[(f,t,g,qty)], money[(f,t,mu)], meta}。

    **唯一 canonical payload（v2/04 §5.1 / Leader A3）**：
      `{"counterparty": other, "give": [{"good":g,"qty":n} | {"mu":m}], "take": [...], "meta": {...}}`
      （`give`=我付出、`take`=我获得）。
    ⚠️ **已废弃**：`{"deal": {parties, goods, money, meta}}`（保留解析仅为向后兼容，**请勿再用于新代码**——
    两套形状并存会造成「同名不同义」）。新代码一律用 canonical 形态。
    """
    p = (intent or {}).get("payload", {}) or {}
    deal = p.get("deal") if isinstance(p.get("deal"), dict) else None
    me = intent.get("agent_id")
    if deal is None and p.get("counterparty") is not None:
        other = p["counterparty"]
        goods, money = [], []
        for it in (p.get("give") or []):
            if "good" in it:
                goods.append((me, other, str(it["good"]), int(it.get("qty", 0))))
            elif "mu" in it:
                money.append((me, other, int(it["mu"])))
        for it in (p.get("take") or []):
            if "good" in it:
                goods.append((other, me, str(it["good"]), int(it.get("qty", 0))))
            elif "mu" in it:
                money.append((other, me, int(it["mu"])))
        deal = {"parties": [me, other], "goods": goods, "money": money,
                "meta": p.get("meta", {})}
    if not isinstance(deal, dict):
        return None
    parties = deal.get("parties") or []
    if len(parties) != 2 or parties[0] == parties[1]:
        return None
    goods = [(str(f), str(t), str(g), int(q)) for (f, t, g, q) in (deal.get("goods") or [])]
    money = [(str(f), str(t), int(m)) for (f, t, m) in (deal.get("money") or [])]
    return {"parties": sorted(parties), "goods": goods, "money": money,
            "meta": deal.get("meta") or {}}


def validate_deal(state, deal) -> str | None:
    """返回拒绝原因（None=通过）。纯函数、任一不过整笔拒绝。"""
    for (f, t, g, q) in deal["goods"]:
        if q <= 0:
            return "non_positive_qty"
        if not _is_agent(state, f) or not _is_agent(state, t):
            return "unknown_party"
        if not P.is_transferable(g):
            return "good_not_transferable"
        if _inv_get(state, f, g) < q:
            return "insufficient_goods"
    for (f, t, m) in deal["money"]:
        if m <= 0:
            return "non_positive_money"
        if not _is_agent(state, f) or not _is_agent(state, t):
            return "unknown_party"
        if _cash(state, f) < m:
            return "insufficient_cash"
    # 零和是**结构性**的：每条腿 (f,t,g,q) 同时是 f 的「出」与 t 的「入」，
    # 故 ∀good 净额=0、Σmoney 净额=0 自动成立（交换只改归属，不进总量式）。
    # 这里额外拒绝「自腿」（from==to）以防畸形 deal。
    for (f, t, g, q) in deal["goods"]:
        if f == t:
            return "self_leg"
    for (f, t, m) in deal["money"]:
        if f == t:
            return "self_leg"
    return None


def _exchange_settled_spec(round_no, deal, channel, exchange_id, counterparty, price_mu):
    return spec(round_no, P4, deal["parties"][0], "EXCHANGE_SETTLED", {
        "exchange_id": exchange_id,
        "channel": channel,
        "parties": list(deal["parties"]),
        "legs": {
            "goods": [{"from": f, "to": t, "good_id": g, "qty": q}
                      for (f, t, g, q) in deal["goods"]],
            "money": [{"from": f, "to": t, "mu": m} for (f, t, m) in deal["money"]],
        },
        "counterparty": counterparty,
        "price_mu": price_mu,
        "meta": deal.get("meta") or {},
        "round": int(round_no),
    })


def _drain_trade_intents(state):
    q = getattr(state, "pending_intents", None) or []
    taken, keep = [], []
    for it in q:
        (taken if (it or {}).get("intent_class") == "INTENT.ECON.TRADE" else keep).append(it)
    state.pending_intents = keep
    return taken


def _offer_chain(state, round_no):
    """折叠 OFFER_CREATED/COUNTERED/ACCEPTED（全序）→ (offers, accepts)。

    offers[oid] 的 terms = **链上最后一个 counter 的 terms**（规则 1：防"还价后用旧价结算"）。
    """
    idx = getattr(state, "event_index", {}) or {}
    offers: dict[str, dict] = {}
    accepts = []
    from ..event_acc import recs_of_types  # T295：读路径增量聚合（等价全表扫）
    for r in recs_of_types(state, ("OFFER_CREATED", "OFFER_COUNTERED", "OFFER_ACCEPTED",
                                   "OFFER_REJECTED", "OFFER_EXPIRED")):
        t, p = r.get("type"), (r.get("payload") or {})
        if t == "OFFER_CREATED":
            oid = p.get("offer_id")
            if oid and oid not in offers:
                offers[oid] = {"from": p.get("from"), "to": list(p.get("to") or []),
                               "kind": str(p.get("kind", "")).lower(),
                               "terms": dict(p.get("terms") or {}),
                               "enforceable": bool(p.get("enforceable", False))}
        elif t == "OFFER_COUNTERED":
            oid = p.get("offer_id")
            if oid in offers and isinstance(p.get("terms"), dict):
                offers[oid]["terms"] = dict(p["terms"])       # 规则 1：取最后 counter
        elif t == "OFFER_ACCEPTED":
            accepts.append((int(r.get("seq", 0)), p.get("offer_id"), p.get("by"),
                            int(r.get("round", -1))))
    return offers, accepts


def _accept_deals(state, round_no):
    """本回合 `OFFER_ACCEPTED` → 待结算 deal（仅 `kind=sale` 即时成交；其余走契约，规则 2）。"""
    offers, accepts = _offer_chain(state, round_no)
    out = []
    for seq, oid, by, rd in accepts:
        if rd != int(round_no):
            continue                                          # 仅处理本回合的 accept
        if oid not in offers or by is None:
            # 链断裂（无对应 OFFER_CREATED）或缺接受者 → 显式 DROPPED（不崩）
            out.append((seq, ("DROPPED",
                              "unknown_offer" if oid not in offers else "no_accepter",
                              oid, by)))
            continue
        o = offers[oid]
        if o["kind"] != "sale":                               # 规则 2：长周期契约不当即时成交
            continue
        terms = o["terms"]
        g = terms.get("good_id")
        price = int(terms.get("price_mu", 0) or 0)
        qty = int(terms.get("qty", 0) or 0)
        frm, to = o["from"], by
        if not g or price <= 0 or qty <= 0 or frm is None:
            out.append((seq, ("DROPPED", "bad_terms", oid, by)))
            continue
        deal = {"parties": sorted([frm, to]),
                "goods": [(frm, to, str(g), qty * P.MILLI)],
                "money": [(to, frm, price * qty)],            # 价全来自 terms（不预设）
                "meta": {"offer_id": oid}}
        out.append((seq, ("DEAL", deal, by)))
    return sorted(out, key=lambda x: x[0])


def apply_exchange(state, round_no, ctx):
    """4.1：消费 `INTENT.ECON.TRADE` 与「本回合 `OFFER_ACCEPTED`（(B) 单源=offer terms）」
    的双边交换 → `EXCHANGE_SETTLED`（原子、零和）。

    **不直写 state**（hook 纯净）：同一回合内多笔 deal 的"防超卖"用**本地影子视图**完成；
    真正落账由 replay 折叠 `EXCHANGE_SETTLED`（每腿一次）。
    """
    if not exchange_enabled(ctx):
        return [spec(round_no, P4, "SYSTEM", "DROPPED",
                     {"reason": "exchange_disabled", "flag": "exchange_disabled"})]
    specs = []
    # 影子视图（本回合内多笔 deal 互不重复占用；不写 state）
    sc = {a: int(v) for a, v in state.cash.items()}
    si = {k: {g: int(q) for g, q in v.items()}
          for k, v in (getattr(state, "inventory", {}) or {}).items()}

    def _val(deal):
        for (f, t, g, q) in deal["goods"]:
            if q <= 0:
                return "non_positive_qty"
            if not _is_agent(state, f) or not _is_agent(state, t):
                return "unknown_party"
            if not P.is_transferable(g):
                return "good_not_transferable"
            if int(si.get(f, {}).get(g, 0)) < q:
                return "insufficient_goods"
        for (f, t, m) in deal["money"]:
            if m <= 0:
                return "non_positive_money"
            if not _is_agent(state, f) or not _is_agent(state, t):
                return "unknown_party"
            if int(sc.get(f, 0)) < m:
                return "insufficient_cash"
        return None

    def _shadow(deal):
        for (f, t, g, q) in deal["goods"]:
            si.setdefault(f, {})
            si.setdefault(t, {})
            si[f][g] = int(si[f].get(g, 0)) - q
            si[t][g] = int(si[t].get(g, 0)) + q
        for (f, t, m) in deal["money"]:
            sc[f] = int(sc.get(f, 0)) - m
            sc[t] = int(sc.get(t, 0)) + m

    def _emit_deal(deal, eid, extra=None):
        reason = _val(deal)
        if reason is not None:
            p = {"reason": reason, "exchange_id": eid, "parties": deal["parties"]}
            p.update(extra or {})
            specs.append(spec(round_no, P4, "SYSTEM", "DROPPED", p))
            return
        _shadow(deal)
        counterparty = deal["parties"][1] if len(deal["parties"]) == 2 else "WORLD"
        specs.append(_exchange_settled_spec(round_no, deal, "offer", eid, counterparty,
                                            sum(m for (_, _, m) in deal["money"])))

    # (a) 显式 TRADE 意图
    for i, it in enumerate(_drain_trade_intents(state)):
        deal = normalize_deal(state, it)
        if deal is None:
            specs.append(spec(round_no, P4, "SYSTEM", "DROPPED",
                              {"reason": "bad_deal", "exchange_id": f"ex:{round_no}:{i}"}))
            continue
        _emit_deal(deal, f"ex:{round_no}:{i}")
    # (b) OFFER_ACCEPTED → deal（(B)；规则 1/2/3）
    # ⚠️ 作用域限制（T137）：「已结算 offer 集合」仅限**本回合**。跨回合重复接受同一要约在此
    #   仍会报 `insufficient_goods`，而非 `offer_exhausted`（完整修法需跨回合持久状态，代价高）。
    #   如需**全日志口径**，由 **obs 侧离线复算**把"该 offer 此前已有成交"的 insufficient_goods 重分类。
    settled_offers: set = set()
    for seq, item in _accept_deals(state, round_no):
        if item[0] == "DROPPED":
            _, reason, oid, by = item
            specs.append(spec(round_no, P4, "SYSTEM", "DROPPED",
                              {"reason": reason, "offer_id": oid, "by": by}))
            continue
        _, deal, by = item
        oid = deal["meta"].get("offer_id")
        reason = _val(deal)
        if reason is None:
            _shadow(deal)
            settled_offers.add(oid)
            counterparty = deal["parties"][1] if len(deal["parties"]) == 2 else "WORLD"
            specs.append(_exchange_settled_spec(round_no, deal, "offer",
                                                f"ex:{round_no}:offer:{seq}", counterparty,
                                                sum(m for (_, _, m) in deal["money"])))
            continue
        # 语义细分：该要约**本回合已成功结算过**再被接受 → 属**超额认购/售罄**，非"真缺货"
        if reason == "insufficient_goods" and oid in settled_offers:
            reason = "offer_exhausted"
        specs.append(spec(round_no, P4, "SYSTEM", "DROPPED",
                          {"reason": reason, "exchange_id": f"ex:{round_no}:offer:{seq}",
                           "offer_id": oid, "by": by, "parties": deal["parties"]}))
    return specs


# ---------------------------------------------------------------- 契约执行器
def _expire_offers(state, round_no, ctx):
    """T230：协商超限确定性终止 → `OFFER_EXPIRED`（08 §1.2 K）。

    对每个 `OFFER_CREATED` 后**未出现终态**（ACCEPTED/REJECTED/EXPIRED；COUNTERED 非终态）的要约，
    距创建 ≥ `offer_expire_rounds`（默认 7）即发一次 `OFFER_EXPIRED`（发后即终态，不重复）。
    """
    w = 7
    cfg = getattr(ctx, "config", None)
    if isinstance(cfg, dict) and isinstance(cfg.get("exchange"), dict):
        try:
            w = int(cfg["exchange"].get("offer_expire_rounds", w))
        except Exception:
            w = 7
    idx = getattr(state, "event_index", {}) or {}
    created: dict[str, int] = {}
    terminal: set = set()
    from ..event_acc import recs_of_types  # T295：读路径增量聚合
    for r in recs_of_types(state, ("OFFER_CREATED", "OFFER_ACCEPTED", "OFFER_REJECTED", "OFFER_EXPIRED")):
        t, p = r.get("type"), (r.get("payload") or {})
        if t == "OFFER_CREATED" and p.get("offer_id"):
            created.setdefault(p["offer_id"], int(r.get("round", 0)))
        elif t in ("OFFER_ACCEPTED", "OFFER_REJECTED", "OFFER_EXPIRED") and p.get("offer_id"):
            terminal.add(p["offer_id"])
    out = []
    for oid in sorted(created):                            # 确定性全序
        if oid in terminal:
            continue
        if int(round_no) - created[oid] >= w:
            out.append(spec(round_no, P4, "SYSTEM", "OFFER_EXPIRED", {
                "offer_id": oid, "created_round": created[oid], "round": int(round_no)}))
    return out


def _active_contracts(state, round_no):
    """从 `CONTRACT_CREATED` 折叠出未结契约（按 contract_id 升序，确定性）。"""
    idx = getattr(state, "event_index", {}) or {}
    status: dict[str, str] = {}
    created: dict[str, dict] = {}
    from ..event_acc import recs_of_types  # T295：读路径增量聚合
    for r in recs_of_types(state, ("CONTRACT_CREATED", "CONTRACT_FULFILLED",
                                   "CONTRACT_VIOLATED", "CONTRACT_EXPIRED")):
        t = r.get("type")
        p = r.get("payload") or {}
        if t == "CONTRACT_CREATED":
            cid = p.get("contract_id")
            if cid:
                created[cid] = p
                status[cid] = "active"
        elif t in ("CONTRACT_FULFILLED", "CONTRACT_VIOLATED", "CONTRACT_EXPIRED"):
            cid = p.get("contract_id")
            if cid:
                status[cid] = t
    return [(cid, created[cid]) for cid in sorted(created) if status.get(cid) == "active"]


def apply_contracts(state, round_no, ctx):
    """4.2：契约执行器（确定性「法院」）——**只执行「已存在的 `CONTRACT_CREATED`」，不创建契约**。

    「谁创建契约」（`INTENT.ECON.OFFER/CONTRACT_SIGN` → `OFFER_*`/`CONTRACT_CREATED`）是 **phase 2/3
    的内核封装**（v2/04 §6），由 kernel 侧实现；本 hook 仅消费其结果。
    软判定（服务达标等）必须走 `LLM_JUDGMENT(frozen)` 且**只产布尔、不得改金额**；本实现不含软判定。
    """
    if not exchange_enabled(ctx):
        return [spec(round_no, P4, "SYSTEM", "DROPPED",
                     {"reason": "exchange_disabled", "flag": "exchange_disabled"})]
    specs = _expire_offers(state, round_no, ctx)          # T230：协商超限 → OFFER_EXPIRED
    for cid, c in _active_contracts(state, round_no):
        kind = str(c.get("kind", "")).upper()
        terms = c.get("terms") or {}
        due = terms.get("due_round")
        spl = terms.get("slots_per_day")
        period = terms.get("period")
        is_due = (due is not None and int(round_no) >= int(due)) \
            or (period and int(round_no) % int(period) == 0) \
            or (spl and int(round_no) % int(spl) == 0)
        if not is_due:
            continue
        enforceable = bool(c.get("enforceable", True))
        # 确定性付款：EMPLOYMENT/SERVICE 等按 terms.wage_mu/fee_mu，payer→payee
        payer, payee, amt = _payment_of(kind, terms, c)
        if amt <= 0:
            # 无金额条款：仅结案
            specs.append(spec(round_no, P4, "SYSTEM", "CONTRACT_FULFILLED",
                              {"contract_id": cid, "kind": kind, "round": int(round_no)}))
            continue
        if _cash(state, payer) >= amt:
            specs.append(spec(round_no, P4, payer, "TRANSFER", {
                "tx_id": f"ct:{cid}:{round_no}", "from": payer, "to": payee, "amount": amt,
                "fee": 0, "tx_type": "transfer", "reason": f"contract:{kind.lower()}",
                "counterparty_id": payee, "flags": []}))
            specs.append(spec(round_no, P4, "SYSTEM", "CONTRACT_FULFILLED",
                              {"contract_id": cid, "kind": kind, "round": int(round_no),
                               "amount": amt}))
        elif enforceable and due is not None and int(round_no) > int(due):
            specs.append(spec(round_no, P4, "SYSTEM", "CONTRACT_VIOLATED",
                              {"contract_id": cid, "kind": kind, "round": int(round_no),
                               "reason": "insufficient_funds", "payer": payer, "amount": amt}))
        elif due is not None and int(round_no) > int(due):
            specs.append(spec(round_no, P4, "SYSTEM", "CONTRACT_EXPIRED",
                              {"contract_id": cid, "kind": kind, "round": int(round_no)}))
    return specs


def _payment_of(kind, terms, c):
    """确定性付款三元组 (payer, payee, amount_mu)；无付款返回 ("","",0)。"""
    if kind == "EMPLOYMENT":
        return (c.get("employer"), c.get("employee"), int(terms.get("wage_mu", 0)))
    if kind == "TENANCY":
        return (c.get("tenant"), c.get("owner"), int(terms.get("rent_mu", 0)))
    if kind == "SERVICE":
        return (c.get("client"), c.get("provider"), int(terms.get("fee_mu", 0)))
    return (c.get("payer"), c.get("payee"), int(terms.get("amount_mu", terms.get("fee_mu", 0))))


__all__ = ["apply_exchange", "apply_contracts", "exchange_enabled", "normalize_deal", "validate_deal"]
