"""T287 期①：tick 内时间区间 —— 可选 span + 纯函数排序 + time_model 版本戳（默认 off）。"""

import json

from engine import time_model as tm
from engine.events import spec
from engine.kernel import Engine
from engine.runner import default_config


def _cfg(enabled: bool):
    cfg = default_config()
    cfg.setdefault("time", {})
    cfg["time"] = {"version": "1.0", "U": 6, "interval": {"enabled": enabled},
                   "ongoing": {"enabled": False}, "interleave": {"enabled": False}}
    return cfg


# ---- 纯函数 ----
def test_micro_time_and_span_default():
    assert tm.micro_time(3, 2, 6) == 20
    assert tm.span_bounds({"round": 4}, 6) == (24, 24)          # 缺省=瞬时 (round,0)
    assert tm.span_bounds({"round": 4, "span": {"start_round": 4, "start_sub": 1,
                                                "end_round": 5, "end_sub": 0}}, 6) == (25, 30)


def test_semantic_key_and_order_are_deterministic_total_order():
    recs = [
        {"seq": 2, "round": 0, "actor": "B"},
        {"seq": 1, "round": 0, "actor": "A"},
        {"seq": 0, "round": 0, "actor": "A", "span": {"start_round": 0, "start_sub": 3, "end_round": 0, "end_sub": 3}},
    ]
    # (start_μt, actor, seq)：A@15(seq0) 后于 A@0(seq1)、B@0(seq2)
    order = [r["seq"] for r in tm.derive_order(recs, _cfg(True))]
    assert order == [1, 2, 0]


def test_time_model_stamp_values():
    assert tm.time_model_of(_cfg(False)) == "atomic"
    assert tm.time_model_of(_cfg(True)) == "interval-U6"
    assert tm.interval_enabled(_cfg(False)) is False


# ---- off：零行为（不写 span、TURN_SEAL 无戳）----
def test_off_writes_no_span_and_no_seal_stamp():
    eng = Engine(seed=1, config=_cfg(False))
    eng.genesis()
    wi = eng.ledger.records[0]
    assert wi["payload"]["time_model"] == "atomic"      # WORLD_INIT 总带（自描述；指纹行）
    for r in range(3):
        eng.run_round(r)
    assert all("span" not in r for r in eng.ledger.records)
    for r in eng.ledger.records:
        if r["type"] == "TURN_SEAL":
            assert "time_model" not in r["payload"]      # off ⇒ 封条字节不变


# ---- on：span 落账 + TURN_SEAL 带戳（仅存储/排序，不改结算）----
def test_on_records_span_and_stamps_seal():
    eng = Engine(seed=1, config=_cfg(True))
    eng.genesis()
    assert eng.ledger.records[0]["payload"]["time_model"] == "interval-U6"
    # 手工落一条带区间的记录（模拟发射侧提供 span）
    rec = eng.ledger.append(0, 0, "A", "IDLE", {"x": 1},
                            span={"start_round": 0, "start_sub": 2, "end_round": 0, "end_sub": 5})
    assert rec["span"]["start_sub"] == 2
    assert tm.span_bounds(rec, 6) == (2, 5)
    eng.run_round(0)
    seal = [r for r in eng.ledger.records if r["type"] == "TURN_SEAL"][-1]
    assert seal["payload"].get("time_model") == "interval-U6"


def test_span_absent_is_backward_compatible():
    """无 span 的旧事件 = 瞬时（向后兼容）；derive_order 对无 span 记录按 (round*U, actor, seq)。"""
    old = {"seq": 5, "round": 2, "actor": "Z"}
    assert tm.span_bounds(old, 6) == (12, 12)
    assert tm.semantic_key(old, 6) == (12, "Z", 5)
