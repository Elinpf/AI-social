"""T328③：`recent_income` 标量累加器 —— 与全扫逐条等价（含反向验证）。"""

import os

os.environ.setdefault("N50_VEC", "0")

from orchestration.integration import build_world  # noqa: E402

from engine import event_acc, liquidity  # noqa: E402
from engine.state import state_hash  # noqa: E402


def _ref_recent_income(state, aid, round_no, params):
    window = int(params.get("w_income_rounds", 12))
    per_round = {}
    for rec in state.event_index.values():
        rd = int(rec.get("round", -1))
        if rd > int(round_no) or rd < int(round_no) - window:
            continue
        t = rec.get("type")
        p = rec.get("payload") or {}
        if t == "TRANSFER":
            frm, to, tt = p.get("from"), p.get("to"), p.get("tx_type", "transfer")
        elif t == "MARKET_TRADE":
            frm, to, tt = p.get("buyer"), p.get("seller"), p.get("tx_type", "trade")
        else:
            continue
        if tt not in liquidity._INCOME_TX_TYPES:
            continue
        flags = set(p.get("flags") or [])
        if frm == to or (flags & liquidity._EXCLUDE_FLAGS):
            continue
        amt = int(p.get("amount", 0))
        d = per_round.setdefault(rd, 0)
        if to == aid:
            d += amt
        if frm == aid:
            d -= amt
        per_round[rd] = d
    return sum(max(0, v) for v in per_round.values())


def _run(n=6, rounds=20, seed=42):
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return eng


def test_recent_income_parity():
    eng = _run()
    st = eng.state
    for params in ({"w_income_rounds": 12}, {"w_income_rounds": 4}, {"w_income_rounds": 1}):
        for r in range(st.round + 1):
            for aid in sorted(st.agents):
                assert liquidity.recent_income(st, aid, r, params) == \
                    _ref_recent_income(st, aid, r, params), (aid, r, params)


def test_income_net_not_in_state_hash():
    eng = _run()
    h1 = state_hash(eng.state)
    assert eng.state.income_net  # 非空（有 TRANSFER/MARKET_TRADE 时）
    saved = dict(eng.state.income_net)
    eng.state.income_net = {}
    assert state_hash(eng.state) == h1
    eng.state.income_net = saved


def test_live_equals_replay_income_net():
    eng = _run(rounds=12)
    from engine.replay import replay_records
    live = {a: dict(d) for a, d in eng.state.income_net.items()}
    rep = replay_records(eng.ledger.records)
    assert rep.income_net == live


def test_reverse_verification_income_net_corrupt_changes_output():
    eng = _run()
    st = eng.state
    aid = sorted(st.income_net)[0]
    r = max(st.income_net[aid])
    before = liquidity.recent_income(st, aid, r, {"w_income_rounds": 12})
    st.income_net[aid][r] += 1000  # 自洽但错误
    after = liquidity.recent_income(st, aid, r, {"w_income_rounds": 12})
    assert after != before
