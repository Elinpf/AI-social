"""T101：v2 经济循环指标（metrics.econ_loop.*）测试 + p_ref 镜像漂移校验。"""

from obs import metrics, to_canonical
from obs.metrics_econ_loop import GOODS_PREF_MU, econ_loop_metrics
from obs.testsupport import build_log


def test_pref_mirror_matches_engine():
    """防漂移：obs 镜像的 p_ref_mu 必须等于 engine.production.GOODS（测试可 import engine）。"""
    from engine.production import GOODS
    for g, spec in GOODS.items():
        assert g in GOODS_PREF_MU, g
        assert GOODS_PREF_MU[g] == int(spec["p_ref_mu"]), g


def test_econ_loop_basic():
    lb = build_log(seed=1, agents=("P001", "P002"), endow=1000)
    # 两条 TURN_SEAL 提供 M(t)
    lb.add(0, 6, "SYSTEM", "TURN_SEAL", {"money_supply": 2000})
    lb.add(1, 6, "SYSTEM", "TURN_SEAL", {"money_supply": 2150})
    # 生产（milli）：food 2000 milli × p_ref 100 = 200 mu
    lb.add(1, 4, "P001", "PRODUCE", {"agent_id": "P001", "good_id": "food", "qty": 2000,
                                     "place": "farm", "recipe": "food", "skill_level": 0})
    # 交易（带 good_id + qty）价格 = 120*1000/1000 = 120
    lb.add(1, 4, "P001", "MARKET_TRADE", {"buyer": "P001", "seller": "P002", "amount": 120,
                                          "qty": 1000, "good_id": "food"})
    # 工资
    lb.add(1, 4, "P002", "TRANSFER", {"from": "P002", "to": "P001", "amount": 300, "reason": "wage"})
    m = econ_loop_metrics(lb.records())
    assert m["M_target"] == 2000            # genesis mint（build_log 两 agent 各 1000）
    assert m["M_final"] == 2150 and m["M_min"] == 2000
    assert m["M_never_negative"] is True
    assert m["Y_mu"] == 200                 # 2000 milli /1000 × 100
    assert m["median_wage_mu"] == 300
    assert m["price_cv"]["food"] == 0.0     # 单点 → CV 0
    assert m["llm_judged_metric_count"] == 0


def test_econ_loop_empty_denominators_safe():
    lb = build_log(seed=1)                  # 无 PRODUCE/交易/工资
    m = econ_loop_metrics(lb.records())
    assert m["V"] == 0.0
    assert m["Y_mu"] == 0
    assert m["median_wage_mu"] is None
    assert m["price_cv"] == {}
    assert m["price_cv_mean"] == 0.0


def test_econ_loop_in_snapshot_and_bitwise():
    recs = build_log(seed=1).records()
    assert to_canonical(econ_loop_metrics(recs)) == to_canonical(econ_loop_metrics(recs))
    snap = metrics(recs)["metrics"]
    assert "econ_loop" in snap
    assert to_canonical(metrics(recs)) == to_canonical(metrics(recs))


def test_V_distinguishable_and_zero_safe():
    """V：分母0→0.0；不同成交量→不同 V（可区分）。"""
    lb = build_log(seed=1)
    lb.add(0, 6, "SYSTEM", "TURN_SEAL", {"money_supply": 1000})
    assert econ_loop_metrics(lb.records())["V"] == 0.0
    lb.add(1, 4, "A000", "TRANSFER", {"from": "A000", "to": "A001", "amount": 500})
    v1 = econ_loop_metrics(lb.records())["V"]
    lb.add(1, 4, "A000", "TRANSFER", {"from": "A000", "to": "A001", "amount": 500})
    v2 = econ_loop_metrics(lb.records())["V"]
    assert v1 > 0 and v2 > v1                     # 成交量翻倍 → V 上升


def test_CV_distinguishable_and_zero_safe():
    """价格 CV：单点→0；价位分散→>0。"""
    lb = build_log(seed=1)
    lb.add(0, 6, "SYSTEM", "TURN_SEAL", {"money_supply": 1000})
    lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "A001", "amount": 100,
                                          "qty": 1000, "good_id": "food"})
    assert econ_loop_metrics(lb.records())["price_cv"]["food"] == 0.0
    lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "A001", "amount": 300,
                                          "qty": 1000, "good_id": "food"})
    assert econ_loop_metrics(lb.records())["price_cv"]["food"] > 0.0


def test_gini_distinguishable_and_zero_safe():
    """Gini：全等→0；不等→>0（可区分）。"""
    from obs.metrics_econ_loop import econ_loop_metrics as el
    lb = build_log(seed=1, agents=("A000", "A001"), endow=1000)
    assert el(lb.records())["gini_net_worth"] == 0.0        # 等额
    lb.add(1, 4, "A000", "TRANSFER", {"from": "A000", "to": "A001", "amount": 500})
    assert el(lb.records())["gini_net_worth"] > 0.0         # 转移后不等


def test_mint_burn_window_not_trivially_one():
    """防假绿：累计 (minted−burned)≡M 会让"累计口径"永远=1.0；窗口口径必须可区分。"""
    lb = build_log(seed=1)
    lb.add(0, 6, "SYSTEM", "TURN_SEAL", {"money_supply": 2000})
    lb.add(0, 4, "SYSTEM", "MONEY_BURNED", {"amount": 100})
    lb.add(1, 6, "SYSTEM", "TURN_SEAL", {"money_supply": 1900})   # 最后一回合无铸销
    m = econ_loop_metrics(lb.records())
    assert m["net_mint_burn_last_round"] == 0          # 最后一回合无 MONEY_* → 0
    assert m["mint_burn_balance_window"] == 0.0        # 非 1.0
    # 最后一回合有净铸币 → 比例 >0 且 ≠1
    lb.add(1, 4, "SYSTEM", "MONEY_MINTED", {"amount": 50})
    m2 = econ_loop_metrics(lb.records())
    assert m2["net_mint_burn_last_round"] == 50
    assert 0.0 < m2["mint_burn_balance_window"] < 1.0
