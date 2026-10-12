"""Phase 4.1–4.3 经济层 hook（实现）。

契约（kernel-dev 交接 / ADR-08）：纯函数 `fn(state, round_no, ctx) -> list[EventSpec]`，
**只返回事件、不直写账**；金额一律整数 `mu`（1 CR = 100 mu），禁浮点；不调 LLM；
随机只经 `ctx.rng`；不得抛异常（抛异常 = 整回合回滚，故逐笔 try/except 降级为 DROPPED）。

  4.1 settle_market       消费 life 层 L2/L3 产出的 `resource_intents` 与 `pending_intents`，
                          原子转账 / 成交，手续费 50% 税池 + 50% 销毁，反作弊 flags 打标，拒绝自成交。
  4.2 settle_obligations  到期债务 / 计息（INTEREST_CHARGED）/ 续命贷发放（确定性信贷规则）/
                          逾期坏账；存款（DEPOSIT/WITHDRAW）。
  4.3 apply_tax           内部固定子序：铸币判定 → 收入税 → 财富税 → UBI。
                          对 `max(0, I_eff)` 计征；UBI/税/费/息等系统项不计入 `I_eff`。

实现口径说明（以既有 `engine/replay.py` 折叠器为准，避免跨模块改接口）：
  - 手续费分流：销毁半额经 `TRANSFER/MARKET_TRADE.fee` 字段（折叠器 `burned += fee` 且扣付款方）；
    税池半额经 `TAX_LEVIED(kind="fee")`（折叠器 `cash-=amt; tax_pool+=amt`）。两者合计守恒。
  - 系统对手方（MARKET/BANK）非真 Agent：市场账户首次出现即打 `STATE_CHANGE → terminated`，
    使其不进入存活集（不参与 UBI/代谢/判死）。
  - 铸币：既有 `MONEY_MINTED` 折叠器只增 `money_minted_total` 而不落任何账户，单独 emit 必然
    破坏守恒；故本次仅在“可守恒地注入税池”的路径上实现（当前无 drains，M≈M_target，不触发），
    留接口 `_maybe_seigniorage`（不改内核折叠器）。
"""

from __future__ import annotations

from engine.constants import PHASE_ARBITRATE
from engine.events import spec
from engine import liquidity as liq
from engine import production as _prod
from engine.liquidity import bp as _bp, resolve_params as _resolve_params
from engine.state import money_total as _money_total

P4 = PHASE_ARBITRATE  # = 4

# 系统对手方（非真 Agent 账户）
_SYSTEM_ACCOUNTS = frozenset({"MARKET", "BANK", "WORLD", "SYSTEM", "TAX_POOL"})

# 计入 I_eff 的收入型 tx（与 obs/antifraud.INCOME_TX_TYPES 一致）
_INCOME_TX_TYPES = ("transfer", "trade")
# 反作弊排除 flags（与 obs/antifraud.I_EFF_EXCLUDE_FLAGS 一致）
_EXCLUDE_FLAGS = frozenset({"wash", "cycle", "self", "mule"})

# 内置默认与参数解析统一在 `engine/liquidity.py`（T61×T62 单一来源），此处仅再导出。


def _econ_enabled(ctx) -> bool:
    """经济总开关（T58 消融用）。默认 true；runtime `config['economy']['enabled']` 优先，
    其次 `config['policy']['economy']['enabled']`（policy.json，随指纹）。false 时 4.1–4.3 全跳过。"""
    cfg = getattr(ctx, "config", None)
    if isinstance(cfg, dict):
        econ = cfg.get("economy")
        if isinstance(econ, dict) and "enabled" in econ:
            return bool(econ["enabled"])
        pol = cfg.get("policy")
        if isinstance(pol, dict):
            e = pol.get("economy")
            if isinstance(e, dict) and "enabled" in e:
                return bool(e["enabled"])
    return True


def _params(ctx) -> dict:
    """经济/流动性参数（单一来源：`engine.liquidity.resolve_params`）。"""
    return _resolve_params(ctx)


def _e0(ctx) -> int:
    cfg = getattr(ctx, "config", None)
    try:
        return int(cfg.get("genesis", {}).get("initial_endowment_mu", 10000))
    except Exception:
        return 10000


# ------------------------------------------------------------------ state helpers
def _cash(state, aid) -> int:
    return int(state.cash.get(aid, 0))


def _is_real_agent(state, aid) -> bool:
    return isinstance(aid, str) and aid in state.agents and aid not in _SYSTEM_ACCOUNTS


def _alive_real_agents(state) -> list:
    out = []
    for aid, a in state.agents.items():
        if aid in _SYSTEM_ACCOUNTS:
            continue
        if a.get("status") in ("dead", "terminated"):
            continue
        out.append(aid)
    return sorted(out)


def _net_worth(state, aid) -> int:
    try:
        return int(state.net_worth(aid))
    except Exception:
        return int(state.cash.get(aid, 0))


# ------------------------------------------------------------------ 意图收集
def _round_activity_intents(state, round_no):
    """本回合 ACTIVITY_COMPLETED 携带的 resource_intents（按事件 seq 全序）。"""
    out = []
    idx = getattr(state, "event_index", {}) or {}
    recs = [r for r in idx.values()
            if r.get("type") == "ACTIVITY_COMPLETED" and int(r.get("round", -1)) == int(round_no)]
    for r in sorted(recs, key=lambda x: int(x.get("seq", 0))):
        p = r.get("payload") or {}
        for i, it in enumerate(p.get("resource_intents") or []):
            if isinstance(it, dict):
                out.append({"src": "activity", "seq": int(r.get("seq", 0)),
                            "agent_id": p.get("agent_id"), "intent": it, "i": i})
    return out


def _drain_pending_intents(state, classes):
    """取走并移除本回合待结算的 ECON.* 意图（瞬时队列，不入 state_hash）。

    说明：`pending_intents` 是 IF-2 的瞬时队列，注释明确「由 3.5 / 4.x hook 消费」；
    消费后必须移除，否则会被逐回合重复结算。该字段不参与 state_hash，清空不影响重放。
    """
    q = getattr(state, "pending_intents", None) or []
    taken, keep = [], []
    for it in q:
        cls = (it or {}).get("intent_class")
        (taken if cls in classes else keep).append(it)
    state.pending_intents = keep
    return taken


# ------------------------------------------------------------------ 反作弊打标（确定性）
def _tx_list_from_index(state, before_round):
    out = []
    idx = getattr(state, "event_index", {}) or {}
    for r in idx.values():
        t = r.get("type")
        if t not in ("TRANSFER", "MARKET_TRADE"):
            continue
        if int(r.get("round", -1)) >= int(before_round):
            continue
        p = r.get("payload") or {}
        if t == "TRANSFER":
            frm, to = p.get("from"), p.get("to")
        else:
            frm, to = p.get("buyer"), p.get("seller")
        if frm is None or to is None:
            continue
        out.append({"seq": int(r.get("seq", 0)), "round": int(r.get("round", 0)),
                    "from": frm, "to": to, "amount": int(p.get("amount", 0))})
    return out


def _simple_cycles(adj, max_len):
    nodes = sorted(adj)
    cycles = []

    def dfs(start, u, path):
        for v in sorted(adj.get(u, ())):
            if v == start and len(path) >= 2:
                cycles.append(list(path))
            elif v > start and v not in path and len(path) < max_len:
                dfs(start, v, path + [v])

    for s in nodes:
        dfs(s, s, [s])
    return cycles


def _flags_for(cur, all_txs, params):
    flags = set()
    frm, to = cur["from"], cur["to"]
    if frm == to:
        flags.add("self")
    # 候选池 = 历史 + 当前笔（wash 需含当前笔才能识别同回合对倒）
    pool = list(all_txs) + [cur]
    # wash：同对滑窗内双向对消比 ≥ rho
    w_wash = int(params.get("w_wash", 4))
    rho = int(params.get("rho_wash_bp", 8000))
    pair = (min(frm, to), max(frm, to))
    win = [t for t in pool
           if (min(t["from"], t["to"]), max(t["from"], t["to"])) == pair
           and cur["round"] - w_wash <= t["round"] <= cur["round"]]
    ab = sum(t["amount"] for t in win if t["from"] == pair[0])
    ba = sum(t["amount"] for t in win if t["from"] == pair[1])
    if ab > 0 and ba > 0 and min(ab, ba) * 10000 >= rho * max(ab, ba):
        flags.add("wash")
    # cycle / mule：当前边落在环上
    adj = {}
    for t in pool:
        adj.setdefault(t["from"], set()).add(t["to"])
    adj.setdefault(frm, set()).add(to)
    max_len = max(int(params.get("l_cycle", 5)), int(params.get("l_hop", 3)) + 2, 8)
    for cyc in _simple_cycles(adj, max_len):
        L = len(cyc)
        edges = {(cyc[k], cyc[(k + 1) % L]) for k in range(L)}
        if (frm, to) in edges:
            if 3 <= L <= int(params.get("l_cycle", 5)):
                flags.add("cycle")
            if L > int(params.get("l_hop", 3)):
                flags.add("mule")
    return sorted(flags)


# ------------------------------------------------------------------ 4.1 settle_market
def _emit_transfer(round_no, params, frm, to, amount, fee, reason, flags, tx_id, local, all_txs):
    tx = {"seq": -1, "round": int(round_no), "from": frm, "to": to, "amount": int(amount)}
    fl = flags if flags is not None else _flags_for(tx, all_txs, params)
    local.append(tx)
    return spec(round_no, P4, frm, "TRANSFER", {
        "tx_id": tx_id, "from": frm, "to": to, "amount": int(amount), "fee": int(fee),
        "tx_type": "transfer", "reason": reason or "transfer",
        "counterparty_id": to, "flags": sorted(set(fl)),
    })


def _emit_market_trade(round_no, params, buyer, amount, fee_burn, fee_pool, reason,
                       flags, tx_id, scarcity_index, local, all_txs):
    seller = "MARKET"
    fee_total = int(fee_burn) + int(fee_pool)
    tx = {"seq": -1, "round": int(round_no), "from": buyer, "to": seller, "amount": int(amount)}
    fl = flags if flags is not None else _flags_for(tx, all_txs, params)
    local.append(tx)
    specs = []
    payload = {
        "tx_id": tx_id, "buyer": buyer, "seller": seller,
        "qty": 1, "unit_price": int(amount), "amount": int(amount),
        "fee": int(fee_burn), "tx_type": "trade", "reason": reason or "trade",
        "counterparty_id": seller, "counterparty": seller, "channel": "orderbook",
        "flags": sorted(set(fl)),
    }
    if scarcity_index is not None:
        payload["scarcity_index"] = scarcity_index
    # `MARKET_TRADE.scarcity_index`（08 §1.2-N / T60 已登记，0–100 整数）：
    # life 侧带上则透传；否则由 _scarcity_index 依确定性供需代理计算并填入。
    specs.append(spec(round_no, P4, buyer, "MARKET_TRADE", payload))
    if fee_pool > 0:
        # 手续费税池半额：走 TAX_LEVIED（kind=fee，不入 I_eff / 基础流速）
        specs.append(spec(round_no, P4, "SYSTEM", "TAX_LEVIED", {
            "agent_id": buyer, "amount": int(fee_pool), "kind": "fee",
            "reason": "market_fee", "rate_bp": int(params.get("fee_market_bp", 0)),
            "base": int(amount),
        }))
    assert fee_total >= 0
    return specs


def _scarcity_index(state, round_no, params, add=1):
    """确定性稀缺度（08 §1.2-N / T60）：整数 0–100。

    scarcity = clamp(0, 100, 100 − min(100, floor(100 · stock / demand)))
      - stock  = 市场名义可售存量（config market_scarce_supply，缺库存模型时的确定性代理）
      - demand = 近 W_scarce 回合的稀缺买需求（scarce_buy 的 MARKET_TRADE 计数）+ 本笔
    无随机/无 LLM；同日志可重放。阈值对齐 obs.params.theta_scarce（默认 50）。
    """
    W = int(params.get("w_scarce", 3))
    stock = int(params.get("market_scarce_supply", 8))
    demand = int(add)
    idx = getattr(state, "event_index", {}) or {}
    for r in idx.values():
        if r.get("type") != "MARKET_TRADE":
            continue
        if int(r.get("round", -1)) < int(round_no) - W:
            continue
        p = r.get("payload") or {}
        if str(p.get("reason", "")).startswith("scarce"):
            demand += 1
    if demand <= 0:
        return 0
    ratio = min(100, (stock * 100) // demand)
    return max(0, min(100, 100 - ratio))


def _ensure_market_terminated(state, round_no, specs):
    if "MARKET" not in state.agents and any(
            s.type == "MARKET_TRADE" for s in specs):
        specs.append(spec(round_no, P4, "SYSTEM", "STATE_CHANGE",
                          {"agent_id": "MARKET", "from": "alive", "to": "terminated",
                           "cause": "system_account"}))
    return specs


def _settle_market_intent(state, round_no, params, rec, prior, local, counter):
    """结算单条市场意图 -> list[EventSpec]（含降级 DROPPED）。"""
    it = rec["intent"]
    kind = str(it.get("kind", "")).lower()
    event = str(it.get("event", "")).lower()
    frm = it.get("from")
    to = it.get("to")
    amount = int(it.get("amount_mu", it.get("amount", 0)) or 0)
    reason = it.get("reason", kind or "transfer")
    all_txs = prior + local
    tx_id = f"tx:{round_no}:{rec.get('seq', 0)}:{rec.get('i', 0)}:{counter[0]}"
    counter[0] += 1

    # 自成交/非法金额：直接拒绝
    if amount <= 0:
        return [spec(round_no, P4, "SYSTEM", "DROPPED",
                     {"reason": "non_positive_amount", "intent": {"from": frm, "to": to, "amount_mu": amount}})]

    is_market = (kind in ("buy", "trade", "purchase") or str(to).upper() == "MARKET"
                 or event == "market_trade")
    is_deposit = (kind in ("deposit", "savings") or event == "deposit"
                  or str(to).upper() == "BANK")
    is_withdraw = (kind in ("withdraw",) or event == "withdraw")

    if is_market:
        if not _is_real_agent(state, frm):
            return [spec(round_no, P4, "SYSTEM", "DROPPED",
                         {"reason": "unknown_buyer", "buyer": frm, "tx_id": tx_id})]
        fee_bp = int(params.get("fee_market_bp", 0))
        fee_total = _bp(fee_bp, amount)
        burn = fee_total // 2
        pool = fee_total - burn
        # 世界预算保险（Leader 第3条）：销毁半额 ≤ burn_budget(M, μ_floor)；通常不触发（fee≪M）
        _bud = _prod.burn_budget(_money_total(state), int(params.get("mu_floor", 0)))
        if burn > _bud:
            burn = _bud
        if _cash(state, frm) < amount + burn + pool:
            return [spec(round_no, P4, "SYSTEM", "DROPPED",
                         {"reason": "insufficient_funds", "buyer": frm, "amount": amount,
                          "fee": fee_total, "tx_id": tx_id})]
        si = it.get("scarcity_index")
        if si is None:
            si = _scarcity_index(state, round_no, params)
        return _emit_market_trade(round_no, params, frm, amount, burn, pool, reason,
                                  None, tx_id, si, local, all_txs)

    if is_deposit:
        if not _is_real_agent(state, frm):
            return [spec(round_no, P4, "SYSTEM", "DROPPED",
                         {"reason": "unknown_depositor", "agent_id": frm, "tx_id": tx_id})]
        if _cash(state, frm) < amount:
            return [spec(round_no, P4, "SYSTEM", "DROPPED",
                         {"reason": "insufficient_funds", "agent_id": frm, "amount": amount, "tx_id": tx_id})]
        cash_after = _cash(state, frm) - amount
        dep_after = int(state.deposits.get(frm, 0)) + amount
        return [spec(round_no, P4, frm, "DEPOSIT", {
            "agent_id": frm, "amount": amount, "reason": reason,
            "cash_after": cash_after, "deposit_after": dep_after, "tx_id": tx_id})]

    if is_withdraw:
        if not _is_real_agent(state, frm):
            return [spec(round_no, P4, "SYSTEM", "DROPPED",
                         {"reason": "unknown_agent", "agent_id": frm, "tx_id": tx_id})]
        dep = int(state.deposits.get(frm, 0))
        amt = min(amount, dep)
        if amt <= 0:
            return [spec(round_no, P4, "SYSTEM", "DROPPED",
                         {"reason": "no_deposit", "agent_id": frm, "tx_id": tx_id})]
        return [spec(round_no, P4, frm, "WITHDRAW", {
            "agent_id": frm, "amount": amt, "reason": reason,
            "cash_after": _cash(state, frm) + amt, "deposit_after": dep - amt, "tx_id": tx_id})]

    # 默认：主体间转账（gift / transfer）
    if not _is_real_agent(state, frm) or not _is_real_agent(state, to):
        return [spec(round_no, P4, "SYSTEM", "DROPPED",
                     {"reason": "unknown_endpoint", "from": frm, "to": to, "tx_id": tx_id})]
    if frm == to:
        return [spec(round_no, P4, "SYSTEM", "DROPPED",
                     {"reason": "self_transfer_rejected", "from": frm, "to": to, "tx_id": tx_id})]
    fee = 0
    if _cash(state, frm) < amount + fee:
        return [spec(round_no, P4, "SYSTEM", "DROPPED",
                     {"reason": "insufficient_funds", "from": frm, "to": to,
                      "amount": amount, "tx_id": tx_id})]
    return [_emit_transfer(round_no, params, frm, to, amount, fee, reason, None, tx_id,
                           local, all_txs)]


def _settle_order_book(state, round_no, params, orders, prior, local, counter):
    """最小可行 CDA：同回合内限价单即时交叉（跨回合挂单簿留待扩展）。"""
    specs = []
    bids, asks = [], []
    for o in orders:
        p = o["intent"].get("payload", {}) or {}
        side = str(p.get("side", "")).lower()
        price = int(p.get("price_mu", p.get("price", 0)) or 0)
        qty = int(p.get("qty", 1) or 1)
        aid = o["agent_id"]
        rec = {"aid": aid, "price": price, "qty": qty, "seq": o.get("seq", 0)}
        if side == "buy":
            bids.append(rec)
        elif side == "sell":
            asks.append(rec)
    bids.sort(key=lambda x: (-x["price"], x["seq"], x["aid"]))
    asks.sort(key=lambda x: (x["price"], x["seq"], x["aid"]))
    bi = ai = 0
    while bi < len(bids) and ai < len(asks):
        b, a = bids[bi], asks[ai]
        if b["price"] < a["price"] or b["qty"] <= 0 or a["qty"] <= 0:
            break
        if b["aid"] == a["aid"]:  # 拒绝自成交
            ai += 1
            continue
        qty = min(b["qty"], a["qty"])
        price = a["price"]  # maker price（挂单方）
        amount = price * qty
        fee_total = _bp(int(params.get("fee_market_bp", 0)), amount)
        burn = fee_total // 2
        pool = fee_total - burn
        if _cash(state, b["aid"]) < amount + fee_total:
            bi += 1
            continue
        tx_id = f"tx:{round_no}:ord:{counter[0]}"
        counter[0] += 1
        all_txs = prior + local
        seller = a["aid"]
        tx = {"seq": -1, "round": int(round_no), "from": b["aid"], "to": seller, "amount": amount}
        fl = _flags_for(tx, all_txs, params)
        local.append(tx)
        payload = {"tx_id": tx_id, "buyer": b["aid"], "seller": seller, "qty": qty,
                   "unit_price": price, "amount": amount, "fee": burn, "tx_type": "trade",
                   "reason": "order_match", "counterparty_id": seller,
                   "counterparty": seller, "channel": "orderbook", "flags": sorted(set(fl))}
        specs.append(spec(round_no, P4, b["aid"], "MARKET_TRADE", payload))
        if pool > 0:
            specs.append(spec(round_no, P4, "SYSTEM", "TAX_LEVIED", {
                "agent_id": b["aid"], "amount": pool, "kind": "fee", "reason": "market_fee",
                "rate_bp": int(params.get("fee_market_bp", 0)), "base": amount}))
        b["qty"] -= qty
        a["qty"] -= qty
        if b["qty"] <= 0:
            bi += 1
        if a["qty"] <= 0:
            ai += 1
    # 未成交部分：显式 DROPPED（可审计）
    for i in range(bi, len(bids)):
        if bids[i]["qty"] > 0:
            specs.append(spec(round_no, P4, "SYSTEM", "DROPPED",
                              {"reason": "order_unfilled", "side": "buy", "agent_id": bids[i]["aid"]}))
    for i in range(ai, len(asks)):
        if asks[i]["qty"] > 0:
            specs.append(spec(round_no, P4, "SYSTEM", "DROPPED",
                              {"reason": "order_unfilled", "side": "sell", "agent_id": asks[i]["aid"]}))
    return specs


def settle_market(state, round_no, ctx):
    if not _econ_enabled(ctx):
        return []
    params = _params(ctx)
    specs = []
    counter = [0]

    activity = _round_activity_intents(state, round_no)
    pending = _drain_pending_intents(
        state, {"INTENT.ECON.ORDER_PLACE", "INTENT.ECON.ORDER_CANCEL",
                "INTENT.ECON.TRANSFER", "INTENT.ECON.LOAN_APPLY"})

    simple, orders = [], []
    for rec in activity:
        simple.append(rec)
    for it in pending:
        cls = it.get("intent_class")
        if cls == "INTENT.ECON.ORDER_PLACE":
            orders.append({"agent_id": it.get("agent_id"), "intent": it,
                           "seq": int(round_no)})
        elif cls == "INTENT.ECON.ORDER_CANCEL":
            # 无持久化订单簿：保留 DROPPED{no_order_book}（"无簿可撤"的正确反应）。
            # ORDER_CANCEL 事件出口的取舍待 Leader 裁（v2/04 A2c；见 T131 讨论）。
            specs.append(spec(round_no, P4, "SYSTEM", "DROPPED",
                              {"reason": "no_order_book", "agent_id": it.get("agent_id")}))
        elif cls == "INTENT.ECON.TRANSFER":
            p = it.get("payload") or {}
            simple.append({"src": "pending", "seq": 0, "agent_id": it.get("agent_id"),
                           "i": 0, "intent": {"kind": "transfer", "from": it.get("agent_id"),
                                              "to": p.get("to"),
                                              "amount_mu": int(p.get("amount_mu", p.get("amount", 0)) or 0),
                                              "reason": p.get("reason", "transfer")}})

    prior = _tx_list_from_index(state, round_no)
    local = []
    # 固定全序：按 (src_seq, i) 排序
    simple.sort(key=lambda x: (int(x.get("seq", 0)), int(x.get("i", 0))))
    for rec in simple:
        try:
            specs.extend(_settle_market_intent(state, round_no, params, rec, prior, local, counter))
        except Exception as exc:  # 单笔失败不得拖垮整回合
            specs.append(spec(round_no, P4, "SYSTEM", "DROPPED",
                              {"reason": "settle_market_error", "detail": repr(exc)}))
    try:
        specs.extend(_settle_order_book(state, round_no, params, orders, prior, local, counter))
    except Exception as exc:
        specs.append(spec(round_no, P4, "SYSTEM", "DROPPED",
                          {"reason": "order_book_error", "detail": repr(exc)}))

    _ensure_market_terminated(state, round_no, specs)
    return specs


# ------------------------------------------------------------------ 4.2 settle_obligations
def _loan_rate_bp(params, e, e0):
    base = int(params.get("loan_rate_bp", 0))
    kpen = int(params.get("k_pen_bp", 0))
    depth = max(0, -int(e))
    # r = r_base + k_pen·max(0,-E)/E0（k_pen 以 bp 表示系数：0.5 → 5000）；负净值越深越贵（P1）
    return base + (kpen * depth) // max(1, e0)


def _issue_loan_spec(round_no, params, borrower, principal, e0, e, reason):
    term = int(params.get("loan_term_rounds", 12))
    return spec(round_no, P4, "SYSTEM", "LOAN_ISSUED", {
        "loan_id": f"loan:{borrower}:{round_no}",
        "lender": None,  # 世界银行：系统续命贷（发行）
        "borrower": borrower, "principal": int(principal),
        "outstanding": int(principal), "rate_bp": _loan_rate_bp(params, e, e0),
        "due_round": int(round_no) + term, "reason": reason,
    })


def settle_obligations(state, round_no, ctx):
    """4.2：到期/逾期、计息、**确定性授信 + 续命贷发放**、坏账与惩罚、存款。

    流动性判死配套（T61）：以 `L=cash` 为判死基准，本 hook 负责**提供流动性**——
    对 `L<trigger 且可授信` 的 Agent 发放续命贷（`cash↑ + debt↑`，会计诚实、净值可降负），
    使其在生命周期的流动性判据下**真能续命**；授信为 0 者借不到 → 交由生命周期判死。
    """
    if not _econ_enabled(ctx):
        return []
    params = _params(ctx)
    e0 = _e0(ctx)
    n_overdue = int(params.get("n_overdue", 3))
    specs = []
    # 世界预算（M≥μ_floor）：**真正减 M 的通道**（坏账 forfeit / 负净值罚没）共用此预算，
    # 按 agent/贷款全序递减；转移类（INTEREST_CHARGED 等）不占预算、个体可负（Leader 最终口径）。
    burn_left = _prod.burn_budget(_money_total(state), int(params.get("mu_floor", 0)))

    # ---- (a) 计息 + 逾期/坏账 + 惩罚（派生判定，不直改 state）----
    for lid in sorted(state.loans):
        loan = state.loans[lid]
        st = loan.get("status")
        if st not in ("active", "overdue"):
            continue
        borrower = loan.get("borrower")
        if not _is_real_agent(state, borrower):
            continue
        due = int(loan.get("due_round", 0))
        overdue = bool(due) and int(round_no) > due       # 派生，不落 state
        outstanding = int(loan.get("outstanding", 0))
        if outstanding > 0:
            e = liq.net_worth_of(state, borrower)
            r_bp = _loan_rate_bp(params, e, e0)
            if overdue:
                r_bp += int(params.get("r_overdue_bp", 0))
            interest = _bp(r_bp, outstanding)
            if interest > 0:
                specs.append(spec(round_no, P4, "SYSTEM", "INTEREST_CHARGED", {
                    "borrower": borrower, "loan_id": lid, "amount": interest,
                    "rate_bp": r_bp, "base": outstanding, "overdue": overdue}))
        if overdue and (int(round_no) - due) >= n_overdue and st == "active":
            specs.append(spec(round_no, P4, "SYSTEM", "LOAN_DEFAULT", {
                "loan_id": lid, "borrower": borrower, "outstanding": outstanding}))
            # P5 抵押没收 / 坏账罚没（**销毁**，PENALTY_APPLIED；受世界预算）；信用降级由 credit_limit 派生
            desired_f = min(outstanding, max(0, _cash(state, borrower)))
            forfeit = min(desired_f, burn_left)
            burn_left -= forfeit
            if forfeit > 0:
                specs.append(spec(round_no, P4, "SYSTEM", "PENALTY_APPLIED", {
                    "agent_id": borrower, "kind": "bad_debt_forfeit", "amount": forfeit,
                    "base": outstanding, "loan_id": lid, "reason": "overdue_writeoff"}))

    # ---- (a2) 负净值惩罚（P1 升级：允许负资产但须付代价）----
    nw_pen_bp = int(params.get("negative_worth_penalty_bp", 0))
    if nw_pen_bp > 0:
        for aid in _alive_real_agents(state):
            nw = liq.net_worth_of(state, aid)
            if nw >= 0:
                continue
            pen = _bp(nw_pen_bp, -nw)
            amt = min(pen, max(0, _cash(state, aid)), burn_left)   # 受世界预算（销毁通道）
            burn_left -= max(0, amt)
            if amt > 0:
                specs.append(spec(round_no, P4, "SYSTEM", "PENALTY_APPLIED", {
                    "agent_id": aid, "kind": "negative_worth", "amount": amt,
                    "base": -nw, "reason": "negative_net_worth"}))

    # ---- (b) 续命贷发放（确定性授信，非 LLM；`can_borrow` 为放贷确切准入）----
    sustain = int(params.get("liquid_sustain_mu", 0))
    for aid in _alive_real_agents(state):
        if not liq.can_borrow(state, aid, round_no, params):
            continue
        lim = liq.credit_limit(state, aid, round_no, params)
        cash = int(state.cash.get(aid, 0))
        need = max(0, sustain - cash)                       # 抬到可持续阈值
        headroom = int(params.get("loan_max_debt_mu", 0)) - liq.debt_of(state, aid)
        principal = min(lim, need, headroom)
        if principal <= 0:
            continue
        e = liq.net_worth_of(state, aid)
        specs.append(_issue_loan_spec(round_no, params, aid, principal, e0, e, "revival_credit"))

    # ---- (c) 按期还本 → LOAN_REPAY（T230）----
    # 口径（MONEY_BURNED 防双计，已定）：`METABOLISM`/`PENALTY_APPLIED` 的销毁**维持由各自折叠器
    #   内部 `burned += amt` 承载、不额外发 `MONEY_BURNED`**；`MONEY_BURNED` **只承载"未被内嵌字段计过"
    #   的销毁**——当前唯一用途=**系统贷（lender=None）还款回收**（`LOAN_REPAY` 折叠只扣 cash、不记 burned，
    #   必须配 `MONEY_BURNED(amt)` 才守恒）。两条路径**不重叠 → 无双重计**。
    repay_bp = int(params.get("loan_repay_bp", 1000))     # 每回合还本比例（默认 10%）
    if repay_bp > 0:
        for lid in sorted(state.loans):
            loan = state.loans[lid]
            if loan.get("status") not in ("active", "overdue"):
                continue
            borrower = loan.get("borrower")
            if not _is_real_agent(state, borrower):
                continue
            outstanding = int(loan.get("outstanding", 0))
            cash = int(state.cash.get(borrower, 0))
            if outstanding <= 0 or cash <= 0:
                continue
            # 系统贷还款=销毁（真减 M）→ 受**世界预算**约束（与坏账 forfeit 共用 burn_left），防击穿 μ_floor
            amt = min(outstanding, cash * repay_bp // 10000, burn_left)
            if amt <= 0:
                continue
            burn_left -= amt
            lender = loan.get("lender")
            specs.append(spec(round_no, P4, borrower, "LOAN_REPAY", {
                "loan_id": lid, "amount": amt, "payer": borrower, "lender": lender,
                "reason": "scheduled_repay"}))
            if lender is None:
                specs.append(spec(round_no, P4, "SYSTEM", "MONEY_BURNED", {
                    "amount": amt, "reason": "loan_repay_system", "loan_id": lid,
                    "flag": "loan_repay"}))
            # lender 为 Agent 时：还款应为 TRANSFER（当前世界银行单贷方，无此情形）

    # ---- (e) 存款利息（默认关）----
    dep_rate = int(params.get("deposit_rate_bp", 0))
    if dep_rate > 0:
        for aid in _alive_real_agents(state):
            dep = int(state.deposits.get(aid, 0))
            interest = _bp(dep_rate, dep)
            if interest > 0:
                specs.append(spec(round_no, P4, "SYSTEM", "INTEREST_PAID", {
                    "agent_id": aid, "amount": interest, "rate_bp": dep_rate, "base": dep}))
    return specs


# ------------------------------------------------------------------ 4.3 apply_tax
def _round_ie_eff(state, round_no, agent_id, params):
    """本回合有效净流入 I_eff（与 obs/antifraud 口径一致）。"""
    idx = getattr(state, "event_index", {}) or {}
    inflow = outflow = 0
    for r in idx.values():
        if int(r.get("round", -1)) != int(round_no):
            continue
        t = r.get("type")
        p = r.get("payload") or {}
        if t == "TRANSFER":
            frm, to, tt = p.get("from"), p.get("to"), p.get("tx_type", "transfer")
        elif t == "MARKET_TRADE":
            frm, to, tt = p.get("buyer"), p.get("seller"), p.get("tx_type", "trade")
        else:
            continue
        if tt not in _INCOME_TX_TYPES:
            continue
        flags = set(p.get("flags") or [])
        if frm == to or (flags & _EXCLUDE_FLAGS):
            continue
        amount = int(p.get("amount", 0))
        if to == agent_id:
            inflow += amount
        if frm == agent_id:
            outflow += amount
    return inflow - outflow


def _maybe_seigniorage(state, round_no, ctx, params):
    """C 层**兜底铸币**（保底入口，带 `flag=fallback`）：`M` 逼近地板时小幅注入，**防代谢停摆**。

    口径：`trigger = fallback_trigger_mu`（0 → 自动 = N×代谢，即「不足一回合开销」）；
    `issue = min(issue_max, trigger − M)`（`issue_max=fallback_issue_max_mu`，0=关闭）。
    守恒：`MONEY_MINTED(issue)`（增 `minted`）**配对** `INIT_ENDOW` 等额分给存活 Agent（增 `cash`），
    故 `minted−burned` 与实物总量同步增加 → 守恒成立。默认关闭，仅在需要保底时经 config 开启。
    """
    alive = _alive_real_agents(state)
    n = len(alive)
    if n <= 0:
        return []
    if not params.get("fallback_mint_enabled", False):
        return []                      # 一等开关：默认 false（诚实的「保底不写死制度」基线）
    metab = 0
    try:
        metab = int((ctx.config.get("policy", {}) or {}).get("lifecycle", {}).get("metabolism_mu", 0))
    except Exception:
        metab = 0
    # 触发线默认 = 3×N×代谢（留 ≥2 回合余量：4.3 mint 后 4.4 代谢仍烧 ≥N×代谢，保证回合末 M>0）
    trig = int(params.get("fallback_trigger_mu", 0)) or (3 * n * metab)
    if trig <= 0:
        return []
    issue_max = int(params.get("fallback_issue_max_mu", 0))
    if issue_max <= 0:
        return []
    m = _money_total(state)
    if m >= trig:
        return []
    issue = min(issue_max, trig - m)
    if issue <= 0:
        return []
    specs = [spec(round_no, P4, "SYSTEM", "MONEY_MINTED",
                  {"amount": int(issue), "reason": "fallback_mint", "flag": "fallback"})]
    base, rem = divmod(int(issue), n)
    for i, aid in enumerate(alive):
        amt = base + (1 if i < rem else 0)
        if amt > 0:
            specs.append(spec(round_no, P4, "SYSTEM", "INIT_ENDOW",
                              {"agent_id": aid, "amount": amt, "reason": "fallback_mint",
                               "flag": "fallback"}))
    return specs


def apply_tax(state, round_no, ctx):
    if not _econ_enabled(ctx):
        return []
    params = _params(ctx)
    e0 = _e0(ctx)
    specs = []

    # (1) 铸币判定
    specs.extend(_maybe_seigniorage(state, round_no, ctx, params))

    alive = _alive_real_agents(state)

    # (2) 收入税：对 max(0, I_eff) 计征；系统项不计入 I_eff
    collected = 0  # 本 hook 内已产出的税（income+wealth），供 UBI 预算
    income_bp = int(params.get("income_tax_bp", 0))
    if income_bp > 0:
        for aid in alive:
            ie = _round_ie_eff(state, round_no, aid, params)
            base = max(0, ie)
            tax = _bp(income_bp, base)
            amt = min(tax, max(0, _cash(state, aid)))
            if amt > 0:
                collected += amt
                specs.append(spec(round_no, P4, "SYSTEM", "TAX_LEVIED", {
                    "agent_id": aid, "amount": amt, "kind": "income",
                    "rate_bp": income_bp, "base": base}))

    # (3) 财富税：超出 2·E0 的净值部分
    wealth_bp = int(params.get("wealth_tax_bp", 0))
    if wealth_bp > 0:
        threshold = 2 * e0
        for aid in alive:
            e = _net_worth(state, aid)
            base = max(0, e - threshold)
            # 已缴收入税从现金扣除尚未折叠：用本地记账近似可用现金
            tax = _bp(wealth_bp, base)
            amt = min(tax, max(0, _cash(state, aid)))
            if amt > 0:
                collected += amt
                specs.append(spec(round_no, P4, "SYSTEM", "TAX_LEVIED", {
                    "agent_id": aid, "amount": amt, "kind": "wealth",
                    "rate_bp": wealth_bp, "base": base}))

    # (4) UBI：税池发放（不足按比例缩放，不铸币；确定性最大余数分配）
    ubi_mu = int(params.get("ubi_mu", 0))
    if ubi_mu > 0 and alive:
        available = int(state.tax_pool) + collected  # 含本 hook 已产税（尚未折叠）
        n = len(alive)
        if available > 0:
            desired = ubi_mu * n
            budget = min(available, desired)
            if budget >= desired:
                alloc = {aid: ubi_mu for aid in alive}
            else:
                base, rem = divmod(budget, n)
                alloc = {aid: base + (1 if i < rem else 0) for i, aid in enumerate(alive)}
            for aid in alive:
                amt = alloc.get(aid, 0)
                if amt > 0:
                    specs.append(spec(round_no, P4, "SYSTEM", "UBI_PAID", {
                        "agent_id": aid, "amount": amt, "rate_bp": 10000,
                        "base": ubi_mu, "source": "tax_pool"}))
    return specs


__all__ = ["settle_market", "settle_obligations", "apply_tax"]
