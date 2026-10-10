"""反静默门禁：production 挂载 fail-loud + 生产真的在运转（T91 ②）。"""

from collections import Counter

import pytest

import engine.hooks as H
from orchestration.integration import build_world


def test_production_hook_mounted():
    assert H.PRODUCTION_HOOK_AVAILABLE is True, f"apply_production 未挂载：{H.PRODUCTION_HOOK_ERROR}"


def test_assert_production_available_fails_loud_when_missing(monkeypatch):
    # 经济启用却未挂载 -> 报错（fail-loud）；经济关闭 -> 允许 no-op
    monkeypatch.setattr(H, "PRODUCTION_HOOK_AVAILABLE", False)
    monkeypatch.setattr(H, "PRODUCTION_HOOK_ERROR", "simulated-import-failure")
    with pytest.raises(RuntimeError):
        H.assert_production_available({"policy": {"economy": {"enabled": True}}})
    # economy 关闭：不报错
    H.assert_production_available({"policy": {"economy": {"enabled": False}}})
    H.assert_production_available({})


def test_economy_enabled_produces_and_no_stall():
    """economy 启用（默认）下，若干回合内必须出现 PRODUCE，且无 SYSTEM_ERROR（防静默停摆）。"""
    world = build_world(seed=42, n=6)
    eng = world["engine"]
    assert eng.config["policy"]["economy"]["enabled"] is True
    for r in range(24):
        eng.run_round(r)
    c = Counter(rec["type"] for rec in eng.ledger.records)
    assert c.get("SYSTEM_ERROR", 0) == 0, "世界停摆：存在 SYSTEM_ERROR"
    assert c.get("PRODUCE", 0) > 0, "生产静默停摆：PRODUCE==0"
