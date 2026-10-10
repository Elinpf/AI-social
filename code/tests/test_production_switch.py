"""T114：生产层一等开关 `production.enabled` 三态 + fail-loud 协同。

三态（Leader/kernel-dev 口径）：
  1) economy on + production on + 已挂载 → 正常 PRODUCE>0；
  2) production.enabled=false（显式关闭）→ 不触发 fail-loud；PRODUCE==0；双账本守恒仍成立；
     flag=production_disabled；M(t) 不穿负；
  3) economy on + production on + 未挂载 → fail-loud 必须 FAIL（T35 同型防线，不得削弱）。
"""

from __future__ import annotations

from collections import Counter

import pytest

import engine.hooks as H
from engine import conservation
from engine.state import money_total
from engine.runner import default_config


def _cfg(production_enabled=None, economy_enabled=None):
    cfg = default_config()
    if production_enabled is not None:
        cfg.setdefault("production", {})["enabled"] = production_enabled
    if economy_enabled is not None:
        cfg.setdefault("economy", {})["enabled"] = economy_enabled
    return cfg


# ---- 态 3：fail-loud（先测，无需跑世界）----
def test_state3_fail_loud_when_mounted_missing(monkeypatch):
    monkeypatch.setattr(H, "PRODUCTION_HOOK_AVAILABLE", False)
    monkeypatch.setattr(H, "PRODUCTION_HOOK_ERROR", "simulated-import-failure")
    # economy on + production on（默认 true）→ 必须 FAIL
    with pytest.raises(RuntimeError):
        H.assert_production_available(_cfg())
    # 显式关 production → 不 FAIL（态 2 的 fail-loud 侧）
    H.assert_production_available(_cfg(production_enabled=False))
    # economy 关 → 允许 no-op
    H.assert_production_available(_cfg(economy_enabled=False))
    H.assert_production_available({})


# ---- 态 1：默认开、已挂载 → PRODUCE>0 ----
def test_state1_default_on_produces():
    assert H.PRODUCTION_HOOK_AVAILABLE is True
    H.assert_production_available(_cfg())            # 不抛
    from orchestration.integration import build_world
    eng = build_world(seed=42, n=6)["engine"]
    assert eng.config["policy"]["production"]["enabled"] is True
    for r in range(24):
        eng.run_round(r)
    c = Counter(rec["type"] for rec in eng.ledger.records)
    assert c.get("SYSTEM_ERROR", 0) == 0
    assert c.get("PRODUCE", 0) > 0


# ---- 态 2：显式关闭 → PRODUCE==0、守恒、flag、M≥0 ----
def test_state2_disabled_zero_produce_and_conserved():
    from orchestration.integration import build_world
    cfg = _cfg(production_enabled=False)
    eng = build_world(seed=42, config=cfg, n=6)["engine"]
    m_min = None
    for r in range(24):
        eng.run_round(r)
        m = money_total(eng.state)
        m_min = m if m_min is None else min(m_min, m)
    c = Counter(rec["type"] for rec in eng.ledger.records)
    assert c.get("PRODUCE", 0) == 0                 # 零生产
    assert c.get("SYSTEM_ERROR", 0) == 0
    assert conservation.check_conservation(eng.state, eng.config) == []
    assert m_min is not None and m_min >= 0          # M(t) 不穿负
    # flag=production_disabled 审计可见
    assert any((rec.get("payload") or {}).get("flag") == "production_disabled"
               for rec in eng.ledger.records)


def test_state2_disabled_hook_returns_audit_only():
    from engine.hooks.production import apply_production
    from engine.rng import Ctx
    from engine.state import initial_state
    st = initial_state(1)
    outs = apply_production(st, 3, Ctx(1, _cfg(production_enabled=False), 3, 4))
    assert all(s.type == "DROPPED" for s in outs)
    assert any(s.payload.get("flag") == "production_disabled" for s in outs)
