"""T134：交易指标（excl_world + agent↔agent 占比 + V2a/V2b）测试。"""

from obs import metrics, to_canonical
from obs.metrics_econ_loop import econ_loop_metrics
from obs.metrics_exchange import exchange_metrics
from obs.testsupport import build_log


def _log():
    lb = build_log(seed=1, agents=("A000", "A001", "A002"))
    # MARKET_TRADE：agent→agent + agent→world
    lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "A001", "amount": 10, "qty": 1000, "good_id": "food"})
    lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "MARKET", "amount": 5, "qty": 1000, "good_id": "food", "counterparty": "MARKET"})
    # EXCHANGE_SETTLED：双方均 agent + 含 world
    lb.add(2, 4, "SYSTEM", "EXCHANGE_SETTLED", {"exchange_id": "E1", "channel": "offer", "parties": ["A001", "A002"], "legs": {"goods": [], "money": []}})
    lb.add(2, 4, "SYSTEM", "EXCHANGE_SETTLED", {"exchange_id": "E2", "channel": "order", "parties": ["A000", "WORLD"], "legs": {"goods": [], "money": []}})
    lb.add(3, 2, "A000", "OFFER_CREATED", {"offer_id": "O1", "from": "A000", "to": ["A001"], "kind": "trade"})
    lb.add(3, 2, "A001", "OFFER_ACCEPTED", {"offer_id": "O1", "by": "A001"})
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
    assert m["V2a_tool_available"] is True     # offer_created/accepted>0
    assert m["V2b_ai_trades"] is False         # distinct_sellers_excl_world=1（未>1）
    assert m["llm_judged_metric_count"] == 0


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
