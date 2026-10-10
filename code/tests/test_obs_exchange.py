"""T134：交易指标（excl_world + agent↔agent 占比 + V2a/V2b）测试。"""

from obs import metrics, to_canonical
from obs.metrics_econ_loop import econ_loop_metrics
from obs.metrics_exchange import exchange_metrics, dropped_reconcile
from obs.testsupport import build_log


def _log():
    lb = build_log(seed=1, agents=("A000", "A001", "A002"))
    # MARKET_TRADE：agent→agent + agent→world
    lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "A001", "amount": 10, "qty": 1000, "good_id": "food"})
    lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "MARKET", "amount": 5, "qty": 1000, "good_id": "food", "counterparty": "MARKET"})
    # EXCHANGE_SETTLED：双方均 agent + 含 world
    lb.add(2, 4, "SYSTEM", "EXCHANGE_SETTLED", {"exchange_id": "E1", "channel": "offer", "parties": ["A001", "A002"], "legs": {"goods": [], "money": []}})
    lb.add(2, 4, "SYSTEM", "EXCHANGE_SETTLED", {"exchange_id": "E2", "channel": "order", "parties": ["A000", "WORLD"], "legs": {"goods": [], "money": []}})
    # 真实市场挂单（kind=sale，terms 含 good_id/price_mu/qty）+ 被接受
    lb.add(3, 2, "A000", "OFFER_CREATED", {"offer_id": "S1", "from": "A000", "to": [],
                                           "kind": "sale", "terms": {"good_id": "food", "price_mu": 120, "qty": 1}})
    lb.add(3, 2, "A001", "OFFER_ACCEPTED", {"offer_id": "S1", "by": "A001"})
    # 社交伪要约（kind=trade，terms 仅 amount_mu）+ 拒绝：**不得计入 V2a**
    lb.add(3, 2, "A000", "OFFER_CREATED", {"offer_id": "O2", "from": "A000", "to": ["A002"],
                                           "kind": "trade", "terms": {"amount_mu": 100}})
    lb.add(3, 2, "A002", "OFFER_REJECTED", {"offer_id": "O2", "by": "A002", "reason": "polite"})
    return lb.records()


def test_exchange_metrics_basic():
    m = exchange_metrics(_log())
    assert m["n_market_trade"] == 2 and m["n_exchange_settled"] == 2
    assert m["distinct_sellers"] == 2          # A001 + MARKET
    assert m["distinct_sellers_excl_world"] == 1   # 仅 A001
    assert m["distinct_buyers_excl_world"] == 1    # 仅 A000
    assert m["agent_agent_deals"] == 2         # MARKET agent-agent + EXCHANGE both-agent
    assert m["all_deals"] == 4
    assert m["agent_agent_share"] == 0.5
    assert m["V2a_tool_available"] is True     # 有 real_sale 挂单 + 被接受
    assert m["V2b_ai_trades"] is False         # distinct_sellers_excl_world=1（未>1）
    assert m["llm_judged_metric_count"] == 0


def test_offer_source_split_counts_by_kind():
    sp = exchange_metrics(_log())["offer_source_split"]
    assert sp["created_total"] == 2
    assert sp["created_real_sale"] == 1
    assert sp["created_social_pseudo"] == 1
    assert sp["created_other"] == 0
    assert sp["accepted_total"] == 1
    assert sp["accepted_real_sale"] == 1
    assert sp["accepted_social_pseudo"] == 0


def test_V2a_false_when_only_social_pseudo_offers():
    """关键防假绿：只有社交伪要约时 V2a 必须为 False（不拿伪要约当证据）。"""
    lb = build_log(seed=9, agents=("A000", "A001"))
    lb.add(1, 2, "A000", "OFFER_CREATED", {"offer_id": "O-1-A000-A001", "from": "A000",
                                           "to": ["A001"], "kind": "trade", "terms": {"amount_mu": 100}})
    lb.add(1, 2, "A001", "OFFER_REJECTED", {"offer_id": "O-1-A000-A001", "by": "A001", "reason": "polite"})
    m = exchange_metrics(lb.records())
    assert m["V2a_components"]["offer_created"] == 1
    assert m["V2a_components"]["offer_created_social_pseudo"] == 1
    assert m["V2a_tool_available"] is False
    assert m["offer_source_split"]["created_real_sale"] == 0


def test_V2a_false_for_legacy_market_trade_only():
    """沿用 T134 语义：只有 MARKET_TRADE、无 real_sale 被接受 → V2a False（不被 legacy 成交顶真）。"""
    lb = build_log(seed=11, agents=("A000", "A001"))
    lb.add(1, 2, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "A001", "amount": 1, "qty": 1000, "good_id": "food"})
    assert exchange_metrics(lb.records())["V2a_tool_available"] is False


def test_exchange_sellers_include_exchange_legs():
    """08 §1.2 R：卖方口径 = MARKET_TRADE ∪ EXCHANGE_SETTLED 商品腿；只读 MARKET_TRADE 会漏整条 exchange 路径。"""
    lb = build_log(seed=12, agents=("A000", "A001", "A002"))
    # MARKET_TRADE 卖方全是 world
    lb.add(1, 2, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "MARKET", "counterparty": "MARKET",
                                          "amount": 5, "qty": 1000, "good_id": "food"})
    # 两笔 EXCHANGE_SETTLED：A001→A000、A002→A000 卖 material
    lb.add(2, 2, "SYSTEM", "EXCHANGE_SETTLED", {"exchange_id": "X1", "channel": "offer", "parties": ["A000", "A001"],
        "legs": {"goods": [{"from": "A001", "to": "A000", "good_id": "material", "qty": 1000}],
                 "money": [{"from": "A000", "to": "A001", "mu": 100}]}})
    lb.add(2, 2, "SYSTEM", "EXCHANGE_SETTLED", {"exchange_id": "X2", "channel": "offer", "parties": ["A000", "A002"],
        "legs": {"goods": [{"from": "A002", "to": "A000", "good_id": "material", "qty": 1000}],
                 "money": [{"from": "A000", "to": "A002", "mu": 100}]}})
    m = exchange_metrics(lb.records())
    assert m["distinct_sellers_excl_world"] == 2          # A001, A002（来自 exchange 商品腿）
    assert m["distinct_sellers_excl_world_market_trade"] == 0
    assert m["distinct_sellers_excl_world_exchange"] == 2
    assert m["V2b_ai_trades"] is True                      # 修前只读 MARKET_TRADE → 这里会误判 False


def test_dropped_reconcile_reclassifies_offer_exhausted():
    """跨回合售罄：该 offer 此前已 EXCHANGE_SETTLED 的 insufficient_goods → 离线改判 offer_exhausted。"""
    lb = build_log(seed=13, agents=("A000", "A001", "A002"))
    lb.add(1, 2, "A000", "OFFER_CREATED", {"offer_id": "S1", "from": "A000", "to": [],
        "kind": "sale", "terms": {"good_id": "food", "price_mu": 10, "qty": 1}})
    # 回合 2 已成交（seq 早于后面的 DROPPED）
    lb.add(2, 2, "SYSTEM", "EXCHANGE_SETTLED", {"exchange_id": "E1", "channel": "offer",
        "parties": ["A000", "A001"], "meta": {"offer_id": "S1"},
        "legs": {"goods": [{"from": "A000", "to": "A001", "good_id": "food", "qty": 1000}],
                 "money": [{"from": "A001", "to": "A000", "mu": 10}]}})
    lb.add(3, 2, "A001", "DROPPED", {"offer_id": "S1", "reason": "insufficient_goods"})   # 已成交过 → 售罄
    lb.add(3, 2, "A002", "DROPPED", {"offer_id": "S9", "reason": "insufficient_goods"})   # 无成交 → 真缺货
    lb.add(3, 2, "A001", "DROPPED", {"offer_id": "S1", "reason": "insufficient_cash"})    # 他因不动
    dr = dropped_reconcile(lb.records())
    assert dr["engine"] == {"insufficient_cash": 1, "insufficient_goods": 2}
    assert dr["offline"] == {"insufficient_cash": 1, "insufficient_goods": 1, "offer_exhausted": 1}
    assert dr["reclassified"] == 1 and dr["reclassified_cross_round"] == 1


def test_dropped_reconcile_in_metrics_and_bitwise():
    recs = _log()
    m = exchange_metrics(recs)
    assert "dropped_reconcile" in m
    assert to_canonical(exchange_metrics(recs)) == to_canonical(exchange_metrics(recs))


def test_offer_split_unknown_kind_is_other():
    lb = build_log(seed=10, agents=("A000",))
    lb.add(1, 2, "A000", "OFFER_CREATED", {"offer_id": "X1", "from": "A000", "to": [],
                                           "kind": "weird", "terms": {"foo": 1}})
    lb.add(1, 2, "A000", "OFFER_CREATED", {"offer_id": "X2", "from": "A000", "to": [],
                                           "kind": "sale"})  # 缺 good_id → 不算 real_sale
    sp = exchange_metrics(lb.records())["offer_source_split"]
    assert sp["created_other"] == 2 and sp["created_real_sale"] == 0


def test_exchange_V2b_true_when_multiple_agent_sellers():
    lb = build_log(seed=2, agents=("A000", "A001", "A002"))
    lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "A001", "amount": 1, "qty": 1000, "good_id": "food"})
    lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "A002", "amount": 1, "qty": 1000, "good_id": "food"})
    assert exchange_metrics(lb.records())["V2b_ai_trades"] is True


def test_exchange_zero_when_only_world():
    lb = build_log(seed=3, agents=("A000",))
    lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "MARKET", "amount": 5, "qty": 1, "good_id": "food"})
    m = exchange_metrics(lb.records())
    assert m["distinct_sellers_excl_world"] == 0   # 卖方仅 world
    assert m["distinct_buyers_excl_world"] == 1    # 买方 A000 是 agent（对称面保留）
    assert m["agent_agent_share"] == 0.0 and m["V2b_ai_trades"] is False


def test_exchange_in_econ_loop_and_bitwise():
    recs = _log()
    el = econ_loop_metrics(recs)
    assert "exchange" in el and el["exchange"]["agent_agent_share"] == 0.5
    assert to_canonical(econ_loop_metrics(recs)) == to_canonical(econ_loop_metrics(recs))
    assert to_canonical(metrics(recs)) == to_canonical(metrics(recs))
    assert metrics(recs)["metrics"]["econ_loop"]["exchange"]["llm_judged_metric_count"] == 0
