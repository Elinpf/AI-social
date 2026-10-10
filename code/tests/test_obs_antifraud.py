"""反作弊 C1–C10 注入测试（v1/02 §5）。

验收④「反作弊注入用例全部被标记」且作弊流量不计入 I_eff。
"""

from obs import antifraud
from obs.params import DEFAULT_PARAMS
from obs.testsupport import build_log


P = DEFAULT_PARAMS.antifraud


def _flags(analysis, seq):
    return set(analysis["tx_flags"].get(seq, ()))


def test_c1_wash_pair_flagged():
    lb = build_log(seed=1)
    a = lb.add(1, 4, "A000", "TRANSFER", {"from": "A000", "to": "A001", "amount": 50})
    b = lb.add(1, 4, "A001", "TRANSFER", {"from": "A001", "to": "A000", "amount": 50})
    res = antifraud.analyze(lb.records(), P)
    assert "wash" in _flags(res, a["seq"])
    assert "wash" in _flags(res, b["seq"])


def test_c2_cycle_flagged():
    lb = build_log(seed=1)
    e1 = lb.add(1, 4, "A000", "TRANSFER", {"from": "A000", "to": "A001", "amount": 10})
    lb.add(1, 4, "A001", "TRANSFER", {"from": "A001", "to": "A002", "amount": 10})
    lb.add(1, 4, "A002", "TRANSFER", {"from": "A002", "to": "A000", "amount": 10})
    res = antifraud.analyze(lb.records(), P)
    assert "cycle" in _flags(res, e1["seq"])


def test_c5_sybil_same_owner_flagged():
    lb = build_log(seed=1)
    t = lb.add(1, 4, "A010", "TRANSFER", {"from": "A010", "to": "A011", "amount": 20,
                                          "owner_id": "own1", "counterparty_owner_id": "own1"})
    res = antifraud.analyze(lb.records(), P)
    assert {"self", "sybil"} <= _flags(res, t["seq"])


def test_c6_self_trade_flagged():
    lb = build_log(seed=1)
    t = lb.add(1, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "A000", "amount": 5})
    res = antifraud.analyze(lb.records(), P)
    assert "self" in _flags(res, t["seq"])


def test_c8_split_flagged():
    lb = build_log(seed=1)
    seqs = [lb.add(1 + i, 4, "A000", "TRANSFER",
                   {"from": "A000", "to": "A001", "amount": 5})["seq"] for i in range(4)]
    res = antifraud.analyze(lb.records(), P)
    assert all("split" in _flags(res, s) for s in seqs)


def test_c10_mule_long_cycle_flagged():
    lb = build_log(seed=1)
    nodes = ["A000", "A001", "A002", "A003", "A004"]
    first = None
    for i in range(len(nodes)):
        r = lb.add(1, 4, nodes[i], "TRANSFER",
                   {"from": nodes[i], "to": nodes[(i + 1) % len(nodes)], "amount": 7})
        if i == 0:
            first = r["seq"]
    res = antifraud.analyze(lb.records(), P)
    assert "mule" in _flags(res, first)


def test_c4_refinancing_audit():
    lb = build_log(seed=1)
    lb.add(1, 4, "BANK", "LOAN_ISSUED", {"loan_id": "l1", "lender": None,
                                         "borrower": "A000", "principal": 10})
    lb.add(2, 4, "BANK", "LOAN_ISSUED", {"loan_id": "l2", "lender": None,
                                         "borrower": "A000", "principal": 10})
    res = antifraud.analyze(lb.records(), P)
    assert res["audit"]["refi"], "借新还旧未被审计"


def test_c7_double_pledge_audit():
    lb = build_log(seed=1)
    lb.add(1, 4, "BANK", "LOAN_ISSUED", {"loan_id": "l1", "borrower": "A000",
                                         "principal": 10, "collateral_id": "house"})
    lb.add(2, 4, "BANK", "LOAN_ISSUED", {"loan_id": "l2", "borrower": "A001",
                                         "principal": 10, "collateral_id": "house"})
    res = antifraud.analyze(lb.records(), P)
    assert res["audit"]["double_pledge"], "重复质押未被审计"


def test_c9_ordering_audit():
    lb = build_log(seed=1)
    lb.add(1, 4, "SYSTEM", "TAX_LEVIED", {"agent_id": "A000", "amount": 5})
    lb.add(1, 4, "A000", "TRANSFER", {"from": "A000", "to": "A001", "amount": 3})
    res = antifraud.analyze(lb.records(), P)
    assert res["audit"]["ordering"], "顺序套利未被审计"


def test_c3_near_death_surge_audit():
    lb = build_log(seed=1, agents=("A000",))
    # A001 连续 3 回合净额为负（< floor=0）后收到大额流入
    lb.born("A001", 0, 0)
    for r in range(3):
        lb.add(r, 4, "A001", "TRANSFER", {"from": "A001", "to": "A000", "amount": 10})
    t = lb.add(3, 4, "A000", "TRANSFER", {"from": "A000", "to": "A001", "amount": 40})
    res = antifraud.analyze(lb.records(), P)
    assert "near_death_surge" in _flags(res, t["seq"])


def test_ie_eff_excludes_cheat_flows():
    lb = build_log(seed=1, agents=("A000", "A001", "A002", "A003"))
    # 合法转账
    lb.add(1, 4, "A000", "TRANSFER", {"from": "A000", "to": "A001", "amount": 40})
    # wash 对倒
    lb.add(2, 4, "A002", "TRANSFER", {"from": "A002", "to": "A003", "amount": 30})
    lb.add(2, 4, "A003", "TRANSFER", {"from": "A003", "to": "A002", "amount": 30})
    # 自成交
    lb.add(3, 4, "A000", "MARKET_TRADE", {"buyer": "A000", "seller": "A000", "amount": 5})
    res = antifraud.analyze(lb.records(), P)
    ie = antifraud.ie_eff(lb.records(), res["tx_flags"], P)
    assert ie["A001"]["I_eff"] == 40          # 合法收入计入
    assert ie["A002"]["I_eff"] == 0            # wash 不计入
    assert ie["A003"]["I_eff"] == 0
    assert ie["A002"]["excluded_inflow"] > 0


def test_all_c_flag_whitelist_documented():
    """任一 C 案产生的 flag 均在审计白名单内。"""
    for f in antifraud.ALL_FLAGS:
        assert isinstance(f, str)
    assert set(antifraud.I_EFF_EXCLUDE_FLAGS) == {"wash", "cycle", "self", "mule"}
