"""反作弊检测与「有效净流入 I_eff」（v1/02 §4/§5）。

覆盖 C1–C10 确定性检测（可注入、可复现）与 I_eff/E_eff 过滤口径：

I_eff(agent,t) = Σ inflow(有效) − Σ outflow(有效)
  有效 tx 条件（v1/02 §5.2）：
    ① from ≠ to（排除自成交）
    ② from/to 非同一主体（排除 Sybil）
    ③ 不在 wash/cycle/mule 组
    ④ flag ∉ {wash, cycle, self, mule}（canonical 四类；其余 large/split/refi 仅审计）
    ⑤ tx_type ∈ {transfer, trade}（系统项 ubi/mint/tax/fee/interest/penalty/revive_fee
       与债务项 loan 不计入——它们是对 E 的直接调整，不是「赚来的收入」）

所有检测只读日志、纯函数、确定性（全序 tie-break、固定滑窗）。
"""

from __future__ import annotations

from .params import AntiFraudParams, DEFAULT_PARAMS

# 可作为「收入」的 tx_type（其余为系统/债务项，直接调整 E，不计入 I_eff）
INCOME_TX_TYPES = ("transfer", "trade")

# 系统 / 债务项 tx_type（v1/02 §5.2 ⑤ + 借贷项）
SYSTEM_TX_TYPES = (
    "ubi", "mint", "tax", "fee", "interest", "penalty", "revive_fee", "loan",
)

# canonical 排除 flags（v1/02 §5.2 ④）
I_EFF_EXCLUDE_FLAGS = ("wash", "cycle", "self", "mule")

# 全量审计 flags（含非排除项）
ALL_FLAGS = ("wash", "cycle", "self", "mule", "large", "split",
             "sybil", "near_death_surge", "refi", "double_pledge", "ordering")


def _tx(rec) -> dict | None:
    """把 TRANSFER / MARKET_TRADE 归一为 tx 结构（非交易返回 None）。"""
    t = rec["type"]
    p = rec.get("payload") or {}
    if t == "TRANSFER":
        frm, to = p.get("from"), p.get("to")
        tx_type = p.get("tx_type", "transfer")
    elif t == "MARKET_TRADE":
        frm, to = p.get("buyer"), p.get("seller")
        tx_type = p.get("tx_type", "trade")
    else:
        return None
    if frm is None or to is None:
        return None
    return {
        "seq": int(rec["seq"]),
        "round": int(rec["round"]),
        "from": frm,
        "to": to,
        "amount": int(p.get("amount", 0)),
        "tx_type": str(tx_type),
        "counterparty_id": p.get("counterparty_id"),
        "owner_id": p.get("owner_id"),
        "counterparty_owner_id": p.get("counterparty_owner_id"),
        "flags": sorted(set(p.get("flags") or [])),
        "collateral_id": p.get("collateral_id"),
    }


def _all_tx(records) -> list[dict]:
    out = [_tx(r) for r in records]
    return [x for x in out if x is not None]


def _flags_add(flags_by_seq: dict, seq: int, *flags: str) -> None:
    flags_by_seq.setdefault(seq, set()).update(flags)


# ─────────────────────────── C1 wash（对倒） ───────────────────────────

def detect_wash(txs, params: AntiFraudParams) -> list[tuple]:
    """C1：滑窗 W_wash 内同一对双向流水对消比 ≥ ρ_wash → 标 wash。

    返回标记的 (seq...) 集合（determinstic）。
    """
    by_pair: dict[tuple, list] = {}
    for tx in txs:
        pair = tuple(sorted((tx["from"], tx["to"])))
        by_pair.setdefault(pair, []).append(tx)
    marked = set()
    for pair in sorted(by_pair):
        arr = sorted(by_pair[pair], key=lambda x: (x["round"], x["seq"]))
        n = len(arr)
        for i in range(n):
            r0 = arr[i]["round"]
            win = [x for x in arr if r0 <= x["round"] <= r0 + params.w_wash]
            ab = sum(x["amount"] for x in win if x["from"] == pair[0])
            ba = sum(x["amount"] for x in win if x["from"] == pair[1])
            if ab > 0 and ba > 0:
                ratio = min(ab, ba) / max(ab, ba)
                if ratio >= params.rho_wash:
                    for x in win:
                        marked.add(int(x["seq"]))
    return sorted(marked)


# ─────────────────────────── C2 / C10 环路 ───────────────────────────

def _simple_cycles(adj: dict, max_len: int) -> list[list]:
    """枚举有向简单环（以最小节点为锚，长度 ∈ [2, max_len]）。"""
    nodes = sorted(adj)
    cycles: list[list] = []

    def dfs(start, u, path):
        for v in sorted(adj.get(u, ())):
            if v == start and len(path) >= 2:
                cycles.append(list(path))
            elif v > start and v not in path and len(path) < max_len:
                dfs(start, v, path + [v])

    for s in nodes:
        dfs(s, s, [s])
    return cycles


def detect_cycles(txs, params: AntiFraudParams) -> dict:
    """C2（中环 3..L_cycle → cycle）与 C10（长环 > L_hop → mule）。

    返回 {seq: set(flags)}。
    """
    adj: dict[str, set] = {}
    edges: dict[tuple, list] = {}
    for tx in txs:
        adj.setdefault(tx["from"], set()).add(tx["to"])
        edges.setdefault((tx["from"], tx["to"]), []).append(int(tx["seq"]))
    max_len = max(params.l_cycle, params.l_hop + 2, 8)
    out: dict[int, set] = {}
    for cyc in _simple_cycles(adj, max_len):
        length = len(cyc)
        # 环上的边
        edge_pairs = [(cyc[i], cyc[(i + 1) % length]) for i in range(length)]
        labels = set()
        if 3 <= length <= params.l_cycle:
            labels.add("cycle")
        if length > params.l_hop:
            labels.add("mule")
        if not labels:
            continue
        for e in edge_pairs:
            for seq in edges.get(e, ()):  # 所有该边的记录
                # 仅标记时间窗内可成环的实例（简化：该边全部实例）
                out.setdefault(int(seq), set()).update(labels)
    return {k: v for k, v in sorted(out.items())}


# ─────────────────────────── C5 Sybil / C6 self ───────────────────────────

def detect_self(txs) -> dict:
    """C5 同主体（owner_id 相同）+ C6 自成交（from == to）→ self / sybil。"""
    out: dict[int, set] = {}
    for tx in txs:
        seq = int(tx["seq"])
        frm, to = tx["from"], tx["to"]
        if frm == to:
            out.setdefault(seq, set()).update({"self"})
        else:
            own_f = tx.get("owner_id")
            # 同 owner 需显式提供（不同 agent_id 但同 owner_id）
            if own_f is not None and tx.get("counterparty_owner_id") is not None:
                if own_f == tx["counterparty_owner_id"]:
                    out.setdefault(seq, set()).update({"self", "sybil"})
    return {k: v for k, v in sorted(out.items())}


# ─────────────────────────── C8 split / C3 surge ───────────────────────────

def detect_split(txs, params: AntiFraudParams) -> dict:
    """C8：滑窗 W_split 内同 (from,to) 笔数 ≥ K_split 或累计 > T_large → split。"""
    by_pair: dict[tuple, list] = {}
    for tx in txs:
        by_pair.setdefault((tx["from"], tx["to"]), []).append(tx)
    out: dict[int, set] = {}
    for pair in sorted(by_pair):
        arr = sorted(by_pair[pair], key=lambda x: (x["round"], x["seq"]))
        n = len(arr)
        for i in range(n):
            r0 = arr[i]["round"]
            win = [x for x in arr if r0 <= x["round"] <= r0 + params.w_split]
            tot = sum(x["amount"] for x in win)
            if len(win) >= params.k_split or tot > params.t_large:
                for x in win:
                    out.setdefault(int(x["seq"]), set()).add("split")
    return {k: v for k, v in sorted(out.items())}


def _running_net_by_round(records) -> dict:
    """按 (agent, round) 折叠净流入（含 INIT_ENDOW；仅 tx + 注入）。"""
    per: dict[str, dict[int, int]] = {}
    for r in records:
        t = r["type"]
        p = r.get("payload") or {}
        rd = int(r["round"])
        if t == "INIT_ENDOW":
            aid = p.get("agent_id")
            per.setdefault(aid, {}).setdefault(rd, 0)
            per[aid][rd] += int(p.get("amount", 0))
        else:
            tx = _tx(r)
            if tx is not None:
                per.setdefault(tx["from"], {}).setdefault(rd, 0)
                per.setdefault(tx["to"], {}).setdefault(rd, 0)
                per[tx["from"]][rd] -= tx["amount"]
                per[tx["to"]][rd] += tx["amount"]
    return per


def detect_near_death_surge(txs, records, params: AntiFraudParams) -> dict:
    """C3：濒死滞回期内的大额「瞬时回正」流入 → near_death_surge。

    判定（确定性）：某 inflow tx 的收款方在之前 n_death 个连续回合净额均 < θ_floor，
    且本笔金额 ≥ T_large。属审计标注；其是否排除由底层 wash/cycle 标记决定。
    """
    per = _running_net_by_round(records)
    cum: dict[str, dict[int, int]] = {}
    for aid in sorted(per):
        run = 0
        for rd in sorted(per[aid]):
            run += per[aid][rd]
            cum.setdefault(aid, {})[rd] = run
    rounds_by_agent = {a: sorted(d) for a, d in cum.items()}
    out: dict[int, set] = {}
    for tx in txs:
        to = tx["to"]
        rd = tx["round"]
        hist = cum.get(to, {})
        prior_rounds = [r for r in rounds_by_agent.get(to, []) if r < rd]
        tail = prior_rounds[-params.n_death:] if prior_rounds else []
        if len(tail) >= params.n_death and all(hist[r] < params.floor for r in tail):
            if tx["amount"] >= params.t_large:
                out.setdefault(int(tx["seq"]), set()).add("near_death_surge")
    return {k: v for k, v in sorted(out.items())}


# ─────────────────────────── C4 / C7 / C9 审计（非流量） ───────────────────────────

def detect_loan_abuse(records, params: AntiFraudParams) -> dict:
    """C4 借新还旧（refi）+ C7 重复质押（double_pledge）——审计项。"""
    loans = [r for r in records if r["type"] == "LOAN_ISSUED"]
    refi = []
    by_borrower: dict[str, list] = {}
    for r in sorted(loans, key=lambda x: (x["round"], x["seq"])):
        p = r.get("payload") or {}
        by_borrower.setdefault(p.get("borrower"), []).append((int(r["round"]), int(r["seq"])))
    for b in sorted(by_borrower, key=lambda x: str(x)):
        seqs = by_borrower[b]
        for i in range(1, len(seqs)):
            if seqs[i][0] - seqs[i - 1][0] < params.w_refi:
                refi.append({"borrower": b, "seq": seqs[i][1],
                             "prev_seq": seqs[i - 1][1], "round": seqs[i][0]})
    # double pledge
    coll: dict[str, list] = {}
    for r in sorted(loans, key=lambda x: (x["round"], x["seq"])):
        cid = (r.get("payload") or {}).get("collateral_id")
        if cid is not None:
            coll.setdefault(str(cid), []).append(int(r["seq"]))
    dbl = [{"collateral_id": c, "seqs": s} for c, s in sorted(coll.items()) if len(s) > 1]
    return {"refi": refi, "double_pledge": dbl}


def detect_ordering(records) -> dict:
    """C9：同回合内「先转移后课税/计息」的顺序套利嫌疑 → ordering 审计。"""
    settle_types = {"TAX_LEVIED", "INTEREST_CHARGED", "PENALTY_APPLIED", "METABOLISM"}
    by_round: dict[int, list] = {}
    for r in records:
        by_round.setdefault(int(r["round"]), []).append(r)
    flagged = []
    for rd in sorted(by_round):
        recs = sorted(by_round[rd], key=lambda x: x["seq"])
        settle_seqs = [int(r["seq"]) for r in recs if r["type"] in settle_types]
        if not settle_seqs:
            continue
        first_settle = min(settle_seqs)
        for r in recs:
            if r["type"] in ("TRANSFER", "MARKET_TRADE") and int(r["seq"]) > first_settle:
                flagged.append({"seq": int(r["seq"]), "round": rd,
                                "after_settle_seq": first_settle})
    return {"ordering": flagged}


# ─────────────────────────── 聚合 ───────────────────────────

def analyze(records, params: AntiFraudParams | None = None) -> dict:
    """执行 C1–C10 全部检测，返回结构化反作弊报告。"""
    params = params or DEFAULT_PARAMS.antifraud
    txs = _all_tx(records)
    flags_by_seq: dict[int, set] = {}

    for seq in detect_wash(txs, params):
        _flags_add(flags_by_seq, seq, "wash")
    for seq, fl in detect_cycles(txs, params).items():
        _flags_add(flags_by_seq, seq, *fl)
    for seq, fl in detect_self(txs).items():
        _flags_add(flags_by_seq, seq, *fl)
    for seq, fl in detect_split(txs, params).items():
        _flags_add(flags_by_seq, seq, *fl)
    for seq, fl in detect_near_death_surge(txs, records, params).items():
        _flags_add(flags_by_seq, seq, *fl)
    # large：金额告警（审计）
    for tx in txs:
        if tx["amount"] >= params.t_large:
            _flags_add(flags_by_seq, int(tx["seq"]), "large")

    audit = detect_loan_abuse(records, params)
    audit.update(detect_ordering(records))

    flags_out = {int(k): sorted(v) for k, v in sorted(flags_by_seq.items())}
    flags_by_type: dict[str, int] = {}
    for v in flags_out.values():
        for f in v:
            flags_by_type[f] = flags_by_type.get(f, 0) + 1

    return {
        "tx_flags": flags_out,
        "flags_by_type": {k: flags_by_type[k] for k in sorted(flags_by_type)},
        "audit": audit,
        "flagged_tx_count": len(flags_out),
    }


def ie_eff(records, tx_flags: dict, params: AntiFraudParams | None = None) -> dict:
    """计算每 Agent 的 I_eff（整段日志累计）与流入/流出明细。"""
    params = params or DEFAULT_PARAMS.antifraud
    per: dict[str, dict] = {}

    def _ensure(a):
        per.setdefault(a, {"I_eff": 0, "inflow": 0, "outflow": 0,
                           "excluded_inflow": 0, "excluded_outflow": 0})

    for r in records:
        tx = _tx(r)
        if tx is None:
            continue
        seq = int(tx["seq"])
        flags = set(tx_flags.get(seq, ()))
        excluded = (tx["from"] == tx["to"]
                    or bool(flags & set(I_EFF_EXCLUDE_FLAGS))
                    or tx["tx_type"] in SYSTEM_TX_TYPES
                    or tx["tx_type"] not in INCOME_TX_TYPES)
        _ensure(tx["from"])
        _ensure(tx["to"])
        if excluded:
            per[tx["from"]]["excluded_outflow"] += tx["amount"]
            per[tx["to"]]["excluded_inflow"] += tx["amount"]
        else:
            per[tx["to"]]["I_eff"] += tx["amount"]
            per[tx["from"]]["I_eff"] -= tx["amount"]
            per[tx["to"]]["inflow"] += tx["amount"]
            per[tx["from"]]["outflow"] += tx["amount"]
    return {a: per[a] for a in sorted(per)}


__all__ = [
    "analyze", "ie_eff", "detect_wash", "detect_cycles", "detect_self",
    "detect_split", "detect_near_death_surge", "detect_loan_abuse",
    "detect_ordering", "INCOME_TX_TYPES", "SYSTEM_TX_TYPES",
    "I_EFF_EXCLUDE_FLAGS", "ALL_FLAGS",
]
