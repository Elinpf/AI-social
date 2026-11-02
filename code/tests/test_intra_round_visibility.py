"""D9z：同轮可见（intra-round visibility）开关 —— 默认关等价 + 开时接线自证。

覆盖三件事（对应实现面）：
  1. `engine.perceive.intra_round_mode()` / `with_pending()`：默认 `off` 时**原样返回同一对象**；
  2. `Kernel.pending_records()`：缓冲区投影的 `seq` 与 `emit` 分配的临时序号一致、`round` 为本回合；
  3. `Adapter.perceive()`（经 `visibility_query(extra=...)`）：开关开时**本回合已发出的 MSG_DM
     真的进了 `WorldView.visible_events`**；关时不进 —— 且两者只差这一条事件。
"""

from __future__ import annotations

import pytest

from engine.constants import PHASE_LIFE
from engine.events import spec
from engine import perceive as P
from orchestration.integration import build_world

ENV = P.INTRA_ROUND_ENV


def _emit_dm_in_round(eng, round_no: int, frm: str, to: str, place: str,
                      msg_uid: str = "D9Z-1") -> int:
    """在 `round_no` 的缓冲区里发一条 MSG_DM，返回它分配到的临时 seq。"""
    eng.state.round = round_no
    eng.arbiter.discard()
    seqs = eng.emit_specs([spec(round_no, PHASE_LIFE, frm, "MSG_DM", {
        "msg_uid": msg_uid, "msg_id": msg_uid, "thread_id": "T-" + msg_uid,
        "from": frm, "to": to, "participants": [frm, to], "body": "同轮可见性测试正文",
        "place": place, "slot": "am", "topic": None, "refs": [], "reply_to": None,
        "body_ref": None, "ctx": {}, "tag_hints": [],
    })])
    return seqs[0]


# ---- 1. 默认关：零行为变化 ------------------------------------------------
def test_default_off_is_noop(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    assert P.intra_round_mode() == "off"
    assert P.intra_round_enabled() is False
    recs = [{"seq": 1, "type": "MSG_DM", "round": 0, "actor": "A", "payload": {}}]
    pending = [{"seq": 2, "type": "MSG_DM", "round": 1, "actor": "B", "payload": {}}]
    assert P.with_pending(recs, pending) is recs          # 同一对象（不复制、不改内容）


def test_invalid_value_falls_back_to_off(monkeypatch):
    for v in ("0", "false", "off", "", "wat"):
        monkeypatch.setenv(ENV, v)
        assert P.intra_round_mode() == "off", v


def test_mode_values(monkeypatch):
    for v in ("1", "true", "yes", "on", "msg"):
        monkeypatch.setenv(ENV, v)
        assert P.intra_round_mode() == "msg", v
    for v in ("all", "any", "2"):
        monkeypatch.setenv(ENV, v)
        assert P.intra_round_mode() == "all", v


# ---- 2. 缓冲区投影 --------------------------------------------------------
def test_pending_records_seq_matches_emit(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    w = build_world(seed=42, n=3)
    eng = w["engine"]
    eng.run_round(0)
    committed = len(eng.ledger.records)
    seq = _emit_dm_in_round(eng, 1, "P001", "P002", "market")
    pend = eng.pending_records()
    assert seq == committed and pend[0]["seq"] == committed
    assert pend[0]["round"] == 1 and pend[0]["type"] == "MSG_DM"
    # 投影不落盘：账本长度不变，仍只有已提交事件
    assert len(eng.ledger.records) == committed


def test_pending_view_filters_by_mode(monkeypatch):
    w = build_world(seed=42, n=3)
    eng = w["engine"]; ad = w["adapter"]
    # 只测过滤口径：直接给投影喂一份混合缓冲区（不经过 emit，避免无关事件的 payload 约束）
    fake = [
        {"seq": 100, "round": 1, "phase": 35, "actor": "P001", "type": "MSG_DM", "payload": {}},
        {"seq": 101, "round": 1, "phase": 35, "actor": "P001", "type": "PLACE_MOVE", "payload": {}},
    ]
    monkeypatch.setattr(eng, "pending_records", lambda: fake)
    monkeypatch.delenv(ENV, raising=False)
    assert ad._pending_view() is None
    monkeypatch.setenv(ENV, "1")
    assert [r["type"] for r in ad._pending_view()] == ["MSG_DM"]
    monkeypatch.setenv(ENV, "all")
    assert [r["type"] for r in ad._pending_view()] == ["MSG_DM", "PLACE_MOVE"]


# ---- 3. 接线自证：同轮消息真的进 WorldView ------------------------------
def _visible_seq(ad, aid):
    return [e.seq for e in ad.perceive(aid).visible_events]


def test_intra_round_msg_enters_worldview_only_when_on(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    w = build_world(seed=42, n=4)
    eng = w["engine"]; ad = w["adapter"]
    eng.run_round(0)
    seq = _emit_dm_in_round(eng, 1, "P001", "P002", "market")

    # 关：同轮已发出的 DM 对收件人不可见
    assert seq not in _visible_seq(ad, "P002")
    # 开（msg 口径）：同一 seq 出现在收件人的 visible_events 里
    monkeypatch.setenv(ENV, "1")
    on = _visible_seq(ad, "P002")
    assert seq in on
    # 单变量：开/关只差这一条
    monkeypatch.delenv(ENV, raising=False)
    off = _visible_seq(ad, "P002")
    assert set(on) - set(off) == {seq}
    assert set(off) - set(on) == set()


def test_intra_round_msg_respects_scope(monkeypatch):
    """`private` 语义不变：非收发双方看不到（开关开也只加可见性上界，不改作用域）。"""
    monkeypatch.setenv(ENV, "1")
    w = build_world(seed=42, n=4)
    eng = w["engine"]; ad = w["adapter"]
    eng.run_round(0)
    seq = _emit_dm_in_round(eng, 1, "P001", "P002", "market")
    assert seq in _visible_seq(ad, "P002")
    third = next(a for a in sorted(eng.state.agents) if a not in ("P001", "P002"))
    assert seq not in _visible_seq(ad, third)


def test_off_state_hash_unchanged_by_pending(monkeypatch):
    """关闭时 `pending_records()` 只读：调用前后 `state_hash` 不变（纯投影）。"""
    from engine.state import state_hash
    monkeypatch.delenv(ENV, raising=False)
    w = build_world(seed=7, n=3)
    eng = w["engine"]
    eng.run_round(0)
    _emit_dm_in_round(eng, 1, "P001", "P002", "market")
    h1 = state_hash(eng.state)
    eng.pending_records()
    assert state_hash(eng.state) == h1
