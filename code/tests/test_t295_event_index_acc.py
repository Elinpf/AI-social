"""T295：`event_index` 读路径增量聚合 —— 增量表 == 全表扫 逐条等价（含反向验证）。"""

import os

os.environ.setdefault("N50_VEC", "0")

from orchestration.integration import build_world  # noqa: E402

from engine import event_acc  # noqa: E402
from engine import scheduling  # noqa: E402
from engine import liquidity  # noqa: E402
from engine.hooks import lifecycle  # noqa: E402
from engine.hooks import econ  # noqa: E402
from engine.state import state_hash  # noqa: E402


def _run(n=4, rounds=16, seed=42):
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return eng, w["engine"].config


# ---- 参考实现（全表扫，镜像原逻辑）----
def _ref_daily_token(state, day, cfg):
    tot = 0
    for rec in state.event_index.values():
        if rec.get("type") != "LLM_CALL" or scheduling.sim_day(rec.get("round", 0), cfg) != day:
            continue
        p = rec.get("payload", {}) or {}
        tot += int(p.get("tokens_in", 0) or 0) + int(p.get("tokens_out", 0) or 0)
    return tot


def _ref_daily_judge(state, day, cfg):
    n = 0
    for rec in state.event_index.values():
        if rec.get("type") != "LLM_CALL" or scheduling.sim_day(rec.get("round", 0), cfg) != day:
            continue
        if (rec.get("payload", {}) or {}).get("purpose") == "judge":
            n += 1
    return n


def _ref_round_ie(state, round_no, aid, params):
    inflow = outflow = 0
    for r in state.event_index.values():
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
        if tt not in econ._INCOME_TX_TYPES:
            continue
        flags = set(p.get("flags") or [])
        if frm == to or (flags & econ._EXCLUDE_FLAGS):
            continue
        amt = int(p.get("amount", 0))
        if to == aid:
            inflow += amt
        if frm == aid:
            outflow += amt
    return inflow - outflow


def _ref_events_of_round(state, round_no, types):
    out = [r for r in state.event_index.values()
           if int(r.get("round", -1)) == int(round_no)
           and (types is None or r.get("type") in types)]
    out.sort(key=lambda r: int(r.get("seq", 0)))
    return [r["seq"] for r in out]


# ---- 逐条对拍 ----
def test_daily_usage_judge_parity():
    eng, cfg = _run()
    for day in range(0, 5):
        assert scheduling.daily_token_usage(eng.state, day, cfg) == _ref_daily_token(eng.state, day, cfg)
        assert scheduling.daily_judge_calls(eng.state, day, cfg) == _ref_daily_judge(eng.state, day, cfg)


def test_round_ie_and_events_of_round_parity():
    eng, cfg = _run()
    params = {"w_income_rounds": 12}
    for r in range(eng.state.round + 1):
        for aid in sorted(eng.state.agents):
            assert econ._round_ie_eff(eng.state, r, aid, params) == _ref_round_ie(eng.state, r, aid, params)
        assert [x["seq"] for x in lifecycle._events_of_round(eng.state, r)] == _ref_events_of_round(eng.state, r, None)
        assert [x["seq"] for x in lifecycle._events_of_round(eng.state, r, ["LLM_CALL"])] == _ref_events_of_round(eng.state, r, ["LLM_CALL"])


def test_events_by_round_not_in_state_hash():
    eng, _ = _run()
    h1 = state_hash(eng.state)
    n_before = sum(len(v) for by in eng.state.events_by_round.values() for v in by.values())
    eng.state.events_by_round.clear()
    h2 = state_hash(eng.state)
    assert h1 == h2 and n_before > 0  # 派生表非空，但不入 hash


def test_live_equals_replay_accumulator():
    """维护点双侧齐：P6 commit 产出的累加器 == replay 重建的累加器。"""
    eng, _ = _run(rounds=12)
    from engine.replay import replay_records
    live = {r: {t: list(s) for t, s in by.items()} for r, by in eng.state.events_by_round.items()}
    rep = replay_records(eng.ledger.records)
    assert rep.events_by_round == live
    assert rep.seqs_by_type == eng.state.seqs_by_type


def test_reverse_verification_drops_one_seq_changes_output():
    """反向验证：人为把累加器改成**自洽但错误**（同步改 acc_n，绕过自愈）⇒ 消费点输出必须变。"""
    eng, cfg = _run()
    day = scheduling.sim_day(eng.state.round, cfg)
    before = scheduling.daily_token_usage(eng.state, day, cfg)
    for seq in list(event_acc.seqs_of_type(eng.state, "LLM_CALL")):
        rec = eng.state.event_index[seq]
        if scheduling.sim_day(rec.get("round", 0), cfg) == day:
            eng.state.events_by_round[int(rec["round"])]["LLM_CALL"].remove(seq)
            eng.state.seqs_by_type["LLM_CALL"].remove(seq)
            break
    after = scheduling.daily_token_usage(eng.state, day, cfg)
    assert after != before
