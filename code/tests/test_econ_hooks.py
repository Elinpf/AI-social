"""T51：Phase 4.1–4.3 经济 hook 单元测试。

覆盖任务要求的验收测试项：
  - 原子性（余额不足不得半成交/半记账）
  - 货币守恒（含手续费 50% 税池 / 50% 销毁、铸币/销毁）
  - 守恒破坏 → 整回合回滚（内核级，见 test_emit_rollback 的补充）
  - 自成交 / 自转账拒绝
  - 反作弊 flags 打标（wash / cycle / mule / self）
  - UBI 不计入 I_eff（系统项）
  - 余额为负须借贷背书（续命贷发放 → 计息）
  - resource_intents / pending_intents 真正被消费
"""

from __future__ import annotations

from engine import conservation
from engine.events import spec
from engine.hooks import econ
from engine.ledger import Ledger
from engine.replay import apply_event
from engine.rng import Ctx
from engine.state import initial_state, money_total, state_hash


# ------------------------------------------------------------------ helpers
def _cfg(**econ_over):
    from engine.runner import default_config
    cfg = default_config()
    cfg.setdefault("economy", {})
    cfg["economy"].update(econ_over)
    return cfg


def _make(agents=("A", "B"), endow=10000, seed=1):
    st = initial_state(seed)
    led = Ledger()
    total = 0

    def ap(ev):
        rec = led.append_spec(ev)
        apply_event(st, rec)
        return rec

    for a in agents:
        ap(spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": a, "birth_round": 0}))
        ap(spec(0, 0, "SYSTEM", "INIT_ENDOW", {"agent_id": a, "amount": endow}))
        total += endow
    if total:
        ap(spec(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": total, "reason": "genesis"}))
    return st, led, ap


def _ctx(cfg, seed=1, round_no=1):
    return Ctx(seed, cfg, round_no, 4)


def _apply(st, led, specs):
    for ev in specs:
        rec = led.append_spec(ev)
        apply_event(st, rec)
    return st


def _inject_activity(st, seq, round_no, agent_id, intents):
    st.event_index[seq] = {"seq": seq, "round": round_no, "type": "ACTIVITY_COMPLETED",
                           "actor": agent_id, "phase": 35,
                           "payload": {"agent_id": agent_id, "resource_intents": intents}}


def _by_type(specs, t):
    return [s for s in specs if s.type == t]


# ------------------------------------------------------------------ 4.1 转账 / 成交
def test_gift_resource_intent_settles_as_transfer():
    st, led, ap = _make()
    _inject_activity(st, 100, 1, "A", [
        {"kind": "gift", "from": "A", "to": "B", "amount_mu": 100, "reason": "gift"}])
    outs = econ.settle_market(st, 1, _ctx(_cfg(income_tax_bp=0, ubi_mu=0)))
    tr = _by_type(outs, "TRANSFER")
    assert len(tr) == 1
    assert tr[0].payload["from"] == "A" and tr[0].payload["to"] == "B"
    assert tr[0].payload["amount"] == 100
    _apply(st, led, outs)
    assert st.cash["A"] == 9900 and st.cash["B"] == 10100
    assert conservation.check_conservation(st) == []


def test_deposit_resource_intent_settles_as_deposit():
    st, led, ap = _make()
    _inject_activity(st, 101, 1, "A", [
        {"kind": "deposit", "from": "A", "to": "BANK", "amount_mu": 100, "event": "DEPOSIT"}])
    outs = econ.settle_market(st, 1, _ctx(_cfg()))
    dp = _by_type(outs, "DEPOSIT")
    assert len(dp) == 1 and dp[0].payload["amount"] == 100
    _apply(st, led, outs)
    assert conservation.check_conservation(st) == []
    # 与 obs 口径一致：现金 → 存款（科目转移，总量不变）
    from obs.econ import fold_economy
    eco = fold_economy(led.records)
    assert eco["deposits"]["A"] == 100 and eco["cash"]["A"] == 9900


def test_market_buy_fee_split_conserves():
    st, led, ap = _make()
    _inject_activity(st, 102, 1, "A", [
        {"kind": "buy", "from": "A", "to": "MARKET", "amount_mu": 100,
         "reason": "scarce_buy", "scarcity_index": 5}])
    outs = econ.settle_market(st, 1, _ctx(_cfg(fee_market_bp=1000)))  # 10% -> 10mu fee
    trades = _by_type(outs, "MARKET_TRADE")
    assert len(trades) == 1
    assert trades[0].payload["amount"] == 100
    assert trades[0].payload["scarcity_index"] == 5
    fees = _by_type(outs, "TAX_LEVIED")
    assert sum(f.payload["amount"] for f in fees) == 5  # 池半额 5，销毁半额走 fee 字段
    assert trades[0].payload["fee"] == 5
    _apply(st, led, outs)
    assert conservation.check_conservation(st) == []
    # 市场账户被显式移出存活集
    assert st.agents["MARKET"]["status"] == "terminated"


def test_atomicity_insufficient_funds_no_partial():
    st, led, ap = _make(endow=50)
    _inject_activity(st, 103, 1, "A", [
        {"kind": "gift", "from": "A", "to": "B", "amount_mu": 100, "reason": "gift"}])
    outs = econ.settle_market(st, 1, _ctx(_cfg()))
    assert _by_type(outs, "TRANSFER") == []
    assert _by_type(outs, "DROPPED")
    _apply(st, led, outs)
    assert st.cash["A"] == 50 and st.cash["B"] == 50  # 半成交/半记账不发生
    assert conservation.check_conservation(st) == []


def test_self_transfer_rejected():
    st, led, ap = _make()
    _inject_activity(st, 104, 1, "A", [
        {"kind": "gift", "from": "A", "to": "A", "amount_mu": 100, "reason": "gift"}])
    outs = econ.settle_market(st, 1, _ctx(_cfg()))
    assert _by_type(outs, "TRANSFER") == []
    assert any(d.payload.get("reason") == "self_transfer_rejected" for d in _by_type(outs, "DROPPED"))


def test_scarcity_index_filled_0_100():
    st, led, ap = _make()
    _inject_activity(st, 400, 1, "A", [
        {"kind": "buy", "from": "A", "to": "MARKET", "amount_mu": 100, "reason": "scarce_buy"}])
    outs = econ.settle_market(st, 1, _ctx(_cfg(fee_market_bp=0)))
    tr = _by_type(outs, "MARKET_TRADE")[0]
    si = tr.payload.get("scarcity_index")
    assert isinstance(si, int) and 0 <= si <= 100  # T60：0–100 整数
    assert tr.payload["reason"] == "scarce_buy"


def test_economy_enabled_switch_off():
    """T58：economy.enabled=false → 4.1–4.3 全跳过、零经济事件、守恒平凡成立。"""
    st, led, ap = _make()
    _inject_activity(st, 500, 1, "A", [
        {"kind": "gift", "from": "A", "to": "B", "amount_mu": 100, "reason": "gift"}])
    st.pending_intents.append({"agent_id": "A", "intent_class": "INTENT.ECON.TRANSFER",
                               "payload": {"to": "B", "amount_mu": 50}})
    cfg = _cfg(enabled=False)
    ctx = _ctx(cfg)
    assert econ.settle_market(st, 1, ctx) == []
    assert econ.settle_obligations(st, 1, ctx) == []
    assert econ.apply_tax(st, 1, ctx) == []
    assert conservation.check_conservation(st) == []
    # policy 块同样可关（config['policy']['economy']['enabled']）
    ctx2 = _ctx({"policy": {"economy": {"enabled": False}}, "economy": {}})
    assert econ.settle_market(st, 1, ctx2) == []


def test_economy_enabled_switch_on_default():
    st, led, ap = _make()
    _inject_activity(st, 501, 1, "A", [
        {"kind": "gift", "from": "A", "to": "B", "amount_mu": 100, "reason": "gift"}])
    cfg = _cfg()  # 未显式设 enabled → 默认 true
    assert len(_by_type(econ.settle_market(st, 1, _ctx(cfg)), "TRANSFER")) == 1


def test_pending_econ_transfer_consumed_once():
    st, led, ap = _make()
    st.pending_intents.append({"agent_id": "A", "intent_class": "INTENT.ECON.TRANSFER",
                               "payload": {"to": "B", "amount_mu": 500, "reason": "help"}})
    outs = econ.settle_market(st, 1, _ctx(_cfg()))
    assert len(_by_type(outs, "TRANSFER")) == 1
    assert st.pending_intents == []  # 已消费，不会重复结算
    _apply(st, led, outs)
    assert conservation.check_conservation(st) == []


def test_order_book_instant_cross_and_no_self_trade():
    st, led, ap = _make()
    st.pending_intents.extend([
        {"agent_id": "A", "intent_class": "INTENT.ECON.ORDER_PLACE",
         "payload": {"side": "buy", "price_mu": 100, "qty": 2}},
        {"agent_id": "B", "intent_class": "INTENT.ECON.ORDER_PLACE",
         "payload": {"side": "sell", "price_mu": 100, "qty": 1}},
    ])
    outs = econ.settle_market(st, 1, _ctx(_cfg(fee_market_bp=0)))
    assert len(_by_type(outs, "MARKET_TRADE")) == 1
    _apply(st, led, outs)
    assert conservation.check_conservation(st) == []
    # 自成交：同 agent 买卖不自成交
    st2, led2, ap2 = _make()
    st2.pending_intents.extend([
        {"agent_id": "A", "intent_class": "INTENT.ECON.ORDER_PLACE",
         "payload": {"side": "buy", "price_mu": 100, "qty": 1}},
        {"agent_id": "A", "intent_class": "INTENT.ECON.ORDER_PLACE",
         "payload": {"side": "sell", "price_mu": 100, "qty": 1}},
    ])
    outs2 = econ.settle_market(st2, 1, _ctx(_cfg(fee_market_bp=0)))
    assert _by_type(outs2, "MARKET_TRADE") == []


# ------------------------------------------------------------------ 反作弊 flags
def test_flags_self_wash_cycle_mule():
    params = {"w_wash": 4, "rho_wash_bp": 8000, "l_cycle": 5, "l_hop": 3}
    # self
    assert "self" in econ._flags_for(
        {"round": 5, "from": "A", "to": "A", "amount": 10}, [], params)
    # wash：A->B 与 B->A 对消
    prior = [{"seq": 1, "round": 5, "from": "A", "to": "B", "amount": 100}]
    fl = econ._flags_for({"round": 5, "from": "B", "to": "A", "amount": 100}, prior, params)
    assert "wash" in fl
    # cycle：A->B->C->A
    prior2 = [{"seq": 1, "round": 4, "from": "B", "to": "C", "amount": 10},
              {"seq": 2, "round": 4, "from": "C", "to": "A", "amount": 10}]
    fl2 = econ._flags_for({"round": 5, "from": "A", "to": "B", "amount": 10}, prior2, params)
    assert "cycle" in fl2


# ------------------------------------------------------------------ 4.2 借贷 / 计息
def test_revival_loan_issued_then_interest_charged():
    st, led, ap = _make()
    # 构造：A 现金跌到 trigger 以下、但有抵押（存款 3000）→ 可授信
    ap(spec(0, 0, "SYSTEM", "DEPOSIT", {"agent_id": "A", "amount": 3000}))
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "A", "amount": 6900}))  # cash: 10000->100
    assert st.cash["A"] == 100 and st.deposits["A"] == 3000
    assert conservation.check_conservation(st) == []
    cfg = _cfg(loan_max_debt_mu=10000, loan_rate_bp=500, k_pen_bp=5000,
               income_tax_bp=0, ubi_mu=0, liquid_trigger_mu=200, liquid_sustain_mu=600)
    outf = econ.settle_obligations(st, 1, _ctx(cfg))
    loans = _by_type(outf, "LOAN_ISSUED")
    assert len(loans) == 1 and loans[0].payload["borrower"] == "A"
    _apply(st, led, outf)
    assert st.cash["A"] >= 200                        # L 被抬过 trigger（真能续命）
    assert conservation.check_conservation(st) == []
    # 下一回合计息
    outs2 = econ.settle_obligations(st, 2, _ctx(cfg, round_no=2))
    interest = _by_type(outs2, "INTEREST_CHARGED")
    assert len(interest) == 1 and interest[0].payload["amount"] > 0
    assert interest[0].payload["borrower"] == "A"
    _apply(st, led, outs2)
    assert conservation.check_conservation(st) == []


def test_credit_limit_zero_without_collateral():
    """无抵押/无收入 → credit_limit=0 → 借不到（配合 T61『借不到→死』路径）。"""
    from engine import liquidity as liq
    st, led, ap = _make()
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "A", "amount": 10100}))  # cash -100, 无存款
    cfg = _cfg(liquid_trigger_mu=200, credit_unsecured_base_mu=0)
    p = econ._params(_ctx(cfg))
    assert liq.credit_limit(st, "A", 1, p) == 0
    assert liq.can_borrow(st, "A", 1, p) is False
    assert _by_type(econ.settle_obligations(st, 1, _ctx(cfg)), "LOAN_ISSUED") == []


def test_negative_worth_penalty_emitted():
    """负净值惩罚（P1 升级）：net_worth<0 且仍有现金 → PENALTY_APPLIED。"""
    st, led, ap = _make()
    ap(spec(0, 0, "SYSTEM", "LOAN_ISSUED", {
        "loan_id": "L1", "lender": None, "borrower": "A", "principal": 5000,
        "outstanding": 5000, "rate_bp": 500, "due_round": 100}))
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "A", "amount": 14900}))  # cash A -> 100
    assert st.cash["A"] == 100 and conservation.check_conservation(st) == []
    cfg = _cfg(negative_worth_penalty_bp=100, income_tax_bp=0, ubi_mu=0)
    outs = econ.settle_obligations(st, 1, _ctx(cfg))
    pen = [s for s in _by_type(outs, "PENALTY_APPLIED") if s.payload.get("kind") == "negative_worth"]
    assert pen and pen[0].payload["agent_id"] == "A" and pen[0].payload["amount"] > 0
    _apply(st, led, outs)
    assert conservation.check_conservation(st) == []


def test_credit_unsecured_enables_negative_networth_alive():
    """未完全抵押授信：debt 可 > cash → net_worth<0 且 L≥trigger 仍 alive（可达）。"""
    from engine import liquidity as liq
    st, led, ap = _make()
    # A 现金降到 trigger 以下、无存款；unsecured 5000 → 可借到 sustain 阈值 → 借后 debt>现金
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "A", "amount": 9800}))  # cash A -> 200
    cfg = _cfg(liquid_trigger_mu=250, liquid_sustain_mu=3000,
               credit_unsecured_base_mu=5000, loan_max_debt_mu=10000,
               income_tax_bp=0, ubi_mu=0)
    p = econ._params(_ctx(cfg))
    assert liq.credit_limit(st, "A", 1, p) >= 3000
    outs = econ.settle_obligations(st, 1, _ctx(cfg))
    _apply(st, led, outs)
    # 借后：cash≈sustain，debt≈sustain-300
    assert st.cash["A"] >= 250
    # 继续代谢使 cash 下探但 ≥trigger，此时 net_worth = cash - debt < 0（负资产存活窗口）
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "A", "amount": 2000}))
    nw = st.net_worth("A")
    assert st.cash["A"] >= 250 and nw < 0
    assert conservation.check_conservation(st) == []


def test_bad_debt_default_emits_penalty():
    """逾期过久 → LOAN_DEFAULT + PENALTY_APPLIED（P5 抵押没收/坏账罚没）。"""
    st, led, ap = _make()
    ap(spec(0, 0, "SYSTEM", "LOAN_ISSUED", {
        "loan_id": "L1", "lender": None, "borrower": "A", "principal": 1000,
        "outstanding": 1000, "rate_bp": 500, "due_round": 1}))
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "A", "amount": 10500}))  # cash A -> 500
    assert st.cash["A"] == 500
    assert conservation.check_conservation(st) == []
    cfg = _cfg(n_overdue=3, income_tax_bp=0, ubi_mu=0)
    outs = econ.settle_obligations(st, 5, _ctx(cfg, round_no=5))  # due=1, round=5 逾期4>=3
    assert _by_type(outs, "LOAN_DEFAULT")
    pen = _by_type(outs, "PENALTY_APPLIED")
    assert pen and pen[0].payload["kind"] == "bad_debt_forfeit"
    _apply(st, led, outs)
    assert conservation.check_conservation(st) == []


# ------------------------------------------------------------------ 4.3 税 / UBI / I_eff
def test_income_tax_on_ieff_and_ubi_not_in_ieff():
    st, led, ap = _make()
    # 制造一笔真实收入（B 收到 1000）
    _inject_activity(st, 200, 1, "A", [
        {"kind": "gift", "from": "A", "to": "B", "amount_mu": 1000, "reason": "gift"}])
    outs = econ.settle_market(st, 1, _ctx(_cfg(income_tax_bp=0, ubi_mu=0)))
    _apply(st, led, outs)
    # I_eff：B=+1000, A=-1000
    assert econ._round_ie_eff(st, 1, "B", {}) == 1000
    # 开启 10% 收入税 + UBI：B 缴 100
    cfg = _cfg(income_tax_bp=1000, ubi_mu=100, fee_market_bp=0)
    tax_outs = econ.apply_tax(st, 1, _ctx(cfg))
    income = [s for s in _by_type(tax_outs, "TAX_LEVIED") if s.payload.get("kind") == "income"]
    assert any(s.payload["agent_id"] == "B" and s.payload["amount"] == 100 for s in income)
    # 税后税池 100，UBI 预算 100 → 20? 只有 2 个 agent，每人至多 50
    _apply(st, led, tax_outs)
    assert conservation.check_conservation(st) == []
    # UBI 计入现金但不计入 I_eff
    received = [s for s in _by_type(tax_outs, "UBI_PAID") if s.payload["agent_id"] == "B"]
    assert received and received[0].payload["amount"] > 0
    st.round = 1  # 保持同回合
    assert econ._round_ie_eff(st, 1, "B", {}) == 1000  # UBI 未被计入（系统项）


def test_ubi_scales_to_available_pool():
    st, led, ap = _make(agents=("A", "B", "C"))
    # 守恒地给税池注入 2mu（A 缴 2）
    ap(spec(0, 0, "SYSTEM", "TAX_LEVIED", {"agent_id": "A", "amount": 2, "kind": "income"}))
    assert st.tax_pool == 2 and conservation.check_conservation(st) == []
    cfg = _cfg(ubi_mu=1000, income_tax_bp=0, wealth_tax_bp=0)
    outs = econ.apply_tax(st, 1, _ctx(cfg))
    ubis = _by_type(outs, "UBI_PAID")
    assert sum(u.payload["amount"] for u in ubis) == 2  # 不铸币，按比例缩放
    _apply(st, led, outs)
    assert st.tax_pool == 0
    assert conservation.check_conservation(st) == []


def test_wealth_tax_above_threshold():
    st, led, ap = _make(agents=("A",), endow=10000)
    st.cash["A"] = 30000  # 需要对应铸币
    # 修正铸币保持守恒
    ap(spec(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": 20000, "reason": "test"}))
    assert conservation.check_conservation(st) == []
    cfg = _cfg(wealth_tax_bp=1000, income_tax_bp=0, ubi_mu=0)
    outs = econ.apply_tax(st, 1, _ctx(cfg))
    wt = [s for s in _by_type(outs, "TAX_LEVIED") if s.payload.get("kind") == "wealth"]
    # 净值 30000 - 2*10000 = 10000 基数，10% = 1000
    assert wt and wt[0].payload["amount"] == 1000
    _apply(st, led, outs)
    assert conservation.check_conservation(st) == []


# ------------------------------------------------------------------ 4.x 纯函数 & 内核集成
def test_hooks_do_not_mutate_world_state_except_transient_queue():
    st, led, ap = _make()
    _inject_activity(st, 300, 1, "A", [
        {"kind": "gift", "from": "A", "to": "B", "amount_mu": 100, "reason": "gift"}])
    before = state_hash(st)
    for fn in (econ.settle_market, econ.settle_obligations, econ.apply_tax):
        fn(st, 1, _ctx(_cfg()))
    assert state_hash(st) == before  # 未直写账（pending_intents 不入 hash）


def test_kernel_round_conserves_with_econ():
    from engine.kernel import Engine
    from engine.state import state_hash as sh
    eng = Engine(1, _cfg(income_tax_bp=1000, ubi_mu=100, wealth_tax_bp=200))
    eng.genesis({"A000": {"home_place": "residence", "needs_init": {}},
                 "A001": {"home_place": "residence", "needs_init": {}}})
    eng.state.pending_intents.append(
        {"agent_id": "A000", "intent_class": "INTENT.ECON.TRANSFER",
         "payload": {"to": "A001", "amount_mu": 500, "reason": "help"}})
    eng.run_round(0)
    types = [r["type"] for r in eng.ledger.records]
    assert "SYSTEM_ERROR" not in types
    assert "ECONOMY_INVARIANT_VIOLATION" not in types
    assert conservation.check_conservation(eng.state) == []
    from engine.replay import replay_records
    assert sh(replay_records(eng.ledger.records, verify=False, verify_seals=False)) == sh(eng.state)


def test_fallback_mint_fires_and_conserves():
    """C 层兜底铸币：M 逼近地板时按 3×N×代谢 补足，守恒（MONEY_MINTED+INIT_ENDOW 配对）。"""
    st, led, ap = _make()  # A,B 各 10000，M=20000
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "A", "amount": 19900}))  # M -> 100
    assert conservation.check_conservation(st) == []
    cfg = _cfg(fallback_mint_enabled=True, fallback_issue_max_mu=5000)
    outs = econ.apply_tax(st, 1, _ctx(cfg))
    mints = _by_type(outs, "MONEY_MINTED")
    endows = _by_type(outs, "INIT_ENDOW")
    assert mints and endows                       # 兜底触发
    assert sum(e.payload["amount"] for e in endows) == mints[0].payload["amount"]
    before = sum(st.cash.values()) + st.tax_pool + sum(st.deposits.values())
    _apply(st, led, outs)
    assert conservation.check_conservation(st) == []
    assert money_total(st) > before               # M 被抬升且守恒


def test_fallback_mint_off_by_default():
    st, led, ap = _make()
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "A", "amount": 19900}))
    cfg = _cfg(fallback_issue_max_mu=5000)        # 未开 enabled
    outs = econ.apply_tax(st, 1, _ctx(cfg))
    assert _by_type(outs, "MONEY_MINTED") == []


def test_loan_repay_and_money_burned_pair_conserves():
    """T230：系统贷按期还本 → LOAN_REPAY + MONEY_BURNED（配对，守恒不破、无双重计）。"""
    st, led, ap = _make()
    ap(spec(0, 0, "SYSTEM", "LOAN_ISSUED", {
        "loan_id": "L1", "lender": None, "borrower": "A", "principal": 1000,
        "outstanding": 1000, "rate_bp": 0, "due_round": 100}))
    assert conservation.check_conservation(st) == []
    cfg = _cfg(income_tax_bp=0, ubi_mu=0, loan_repay_bp=1000)
    outs = econ.settle_obligations(st, 1, _ctx(cfg))
    rp = _by_type(outs, "LOAN_REPAY")
    mb = _by_type(outs, "MONEY_BURNED")
    assert len(rp) == 1 and rp[0].payload["loan_id"] == "L1"
    assert len(mb) == 1 and mb[0].payload["amount"] == rp[0].payload["amount"]
    _apply(st, led, outs)
    assert st.loans["L1"]["status"] == "repaid"
    assert conservation.check_conservation(st) == []


def test_loan_repay_respects_world_budget():
    """T230：系统贷还款=销毁 → 受世界预算约束，不得击穿 μ_floor。"""
    st, led, ap = _make(endow=100)
    # 把 A 现金打到很低、M 逼近地板
    ap(spec(0, 0, "SYSTEM", "METABOLISM", {"agent_id": "B", "amount": 190}))  # M: 200->10
    ap(spec(0, 0, "SYSTEM", "LOAN_ISSUED", {"loan_id": "L1", "lender": None,
                                            "borrower": "A", "principal": 0,
                                            "outstanding": 50, "rate_bp": 0, "due_round": 100}))
    cfg = _cfg(income_tax_bp=0, ubi_mu=0, loan_repay_bp=10000, mu_floor=0)
    outs = econ.settle_obligations(st, 1, _ctx(cfg))
    _apply(st, led, outs)
    assert conservation.check_conservation(st) == []
    assert money_total(st) >= 0
