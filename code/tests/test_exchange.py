"""T131：P2 交换/契约原语（engine/hooks/exchange.py）测试。

纯函数部分（normalize/validate/开关）无条件测；发 `EXCHANGE_SETTLED` 的部分在类型注册后自动生效。
"""

from __future__ import annotations

import pytest

import engine.hooks as H
from engine.events import EVENT_TYPES, spec
from engine.hooks import exchange as X
from engine.ledger import Ledger
from engine.replay import apply_event
from engine.rng import Ctx
from engine.state import initial_state

_NEED_REG = "EXCHANGE_SETTLED" not in EVENT_TYPES


def _cfg(**over):
    from engine.runner import default_config
    cfg = default_config()
    if over:
        cfg.setdefault("exchange", {}).update(over)
    return cfg


def _state(agents=("A", "B"), endow=10000):
    st = initial_state(1)
    led = Ledger()

    def ap(ev):
        rec = led.append_spec(ev)
        apply_event(st, rec)
        return rec

    total = 0
    for a in agents:
        ap(spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": a, "birth_round": 0}))
        ap(spec(0, 0, "SYSTEM", "INIT_ENDOW", {"agent_id": a, "amount": endow}))
        total += endow
    ap(spec(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": total, "reason": "genesis"}))
    st.inventory.setdefault("A", {})["food"] = 5000
    return st, led


def _ctx(cfg):
    return Ctx(1, cfg, 1, 4)


# ---------------- 纯函数：归一 / 校验 ----------------
def test_normalize_give_take():
    st, _ = _state()
    deal = X.normalize_deal(st, {"agent_id": "A", "payload": {
        "counterparty": "B", "give": [{"good": "food", "qty": 2000}], "take": [{"mu": 300}]}})
    assert deal["parties"] == ["A", "B"]
    assert deal["goods"] == [("A", "B", "food", 2000)]
    assert deal["money"] == [("B", "A", 300)]


def test_validate_rejections():
    st, _ = _state()
    # 货不足
    d = {"parties": ["A", "B"], "goods": [("A", "B", "food", 99999)], "money": []}
    assert X.validate_deal(st, d) == "insufficient_goods"
    # 钱不足
    d = {"parties": ["A", "B"], "goods": [], "money": [("A", "B", 99999999)]}
    assert X.validate_deal(st, d) == "insufficient_cash"
    # 不可转让（service）
    d = {"parties": ["A", "B"], "goods": [("A", "B", "service", 100)], "money": []}
    assert X.validate_deal(st, d) == "good_not_transferable"
    # 自腿
    d = {"parties": ["A", "B"], "goods": [("A", "A", "food", 100)], "money": []}
    assert X.validate_deal(st, d) == "self_leg"
    # 通过
    d = {"parties": ["A", "B"], "goods": [("A", "B", "food", 1000)],
         "money": [("B", "A", 200)]}
    assert X.validate_deal(st, d) is None


# ---------------- 开关 ----------------
def test_switch_off_audit_and_no_events():
    st, led = _state()
    st.pending_intents.append({"agent_id": "A", "intent_class": "INTENT.ECON.TRADE",
                               "payload": {"counterparty": "B",
                                           "give": [{"good": "food", "qty": 1000}],
                                           "take": [{"mu": 200}]}})
    cfg = _cfg(enabled=False)
    outs = X.apply_exchange(st, 1, _ctx(cfg))
    assert all(s.type == "DROPPED" for s in outs)
    assert any(s.payload.get("flag") == "exchange_disabled" for s in outs)
    # 契约执行器同样 OFF → 审计
    outs2 = X.apply_contracts(st, 1, _ctx(cfg))
    assert any(s.payload.get("flag") == "exchange_disabled" for s in outs2)


def test_switch_on_no_intents_no_events():
    st, _ = _state()
    assert X.apply_exchange(st, 1, _ctx(_cfg())) == []
    assert X.apply_contracts(st, 1, _ctx(_cfg())) == []


# ---------------- fail-loud 三态 ----------------
def test_exchange_fail_loud_states(monkeypatch):
    monkeypatch.setattr(H, "EXCHANGE_HOOK_AVAILABLE", False)
    monkeypatch.setattr(H, "EXCHANGE_HOOK_ERROR", "simulated")
    with pytest.raises(RuntimeError):
        H.assert_exchange_available(_cfg())                     # on + 未挂载 → FAIL
    H.assert_exchange_available(_cfg(enabled=False))            # 显式关 → 不 FAIL
    c = _cfg(); c["economy"] = {"enabled": False}
    H.assert_exchange_available(c)                              # 经济关 → no-op


# ---------------- 发 EXCHANGE_SETTLED（需类型注册） ----------------
@pytest.mark.skipif(_NEED_REG, reason="EXCHANGE_SETTLED 未注册（等 kernel-dev）")
def test_apply_exchange_emits_settled_atomic():
    st, led = _state()
    st.pending_intents.append({"agent_id": "B", "intent_class": "INTENT.ECON.TRADE",
                               "payload": {"counterparty": "A",
                                           "give": [{"mu": 200}],
                                           "take": [{"good": "food", "qty": 1000}]}})
    outs = X.apply_exchange(st, 1, _ctx(_cfg()))
    ex = [s for s in outs if s.type == "EXCHANGE_SETTLED"]
    assert len(ex) == 1
    p = ex[0].payload
    assert p["parties"] == ["A", "B"]                      # 顺序按 agent_id 升序
    assert p["legs"]["goods"] == [{"from": "A", "to": "B", "good_id": "food", "qty": 1000}]
    assert p["legs"]["money"] == [{"from": "B", "to": "A", "mu": 200}]
    assert p["counterparty"] in ("A", "B")
    # 应用后：goods/money 净额守恒
    for s in outs:
        apply_event(st, led.append_spec(s))
    assert st.inventory["A"]["food"] == 4000 and st.inventory["B"]["food"] == 1000
    assert st.cash["A"] == 10200 and st.cash["B"] == 9800


@pytest.mark.skipif(_NEED_REG, reason="EXCHANGE_SETTLED 未注册（等 kernel-dev）")
def test_apply_exchange_reject_is_noop():
    st, led = _state()
    st.pending_intents.append({"agent_id": "A", "intent_class": "INTENT.ECON.TRADE",
                               "payload": {"counterparty": "B",
                                           "give": [{"good": "food", "qty": 999999}],
                                           "take": [{"mu": 1}]}})
    outs = X.apply_exchange(st, 1, _ctx(_cfg()))
    assert all(s.type == "DROPPED" for s in outs)          # 整笔拒绝，无 EXCHANGE_SETTLED
    assert st.inventory["A"]["food"] == 5000               # 无痕
