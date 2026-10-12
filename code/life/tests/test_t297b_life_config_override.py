"""T297b: life 配置注入 hook —— 单元（life 侧，不 import orchestration）。"""
from __future__ import annotations

from pathlib import Path

import pytest

from life import config as lc
from life import sleep_window as SW

_CFG = Path(__file__).resolve().parents[2] / "config" / "life_v2.json"


def setup_function(_):
    lc.clear_override()


def teardown_function(_):
    lc.clear_override()


def test_override_effective_and_clear_restores_baseline():
    base = SW.load_params()
    assert base["sleep"]["enabled"] is True          # 文件默认 true
    lc.set_override({"sleep": {"enabled": False}})
    assert SW.load_params()["sleep"]["enabled"] is False   # override 生效
    lc.clear_override()
    assert SW.load_params()["sleep"]["enabled"] is True    # clear = 回基线


def test_nested_override_only_touches_named_key():
    lc.set_override({"forgetting": {"consolidate_min": 5}})
    p = SW.load_params()
    assert p["forgetting"]["consolidate_min"] == 5
    assert p["forgetting"]["enabled"] is True        # 其余键不动


def test_unknown_key_fail_loud():
    lc.set_override({"bogus_section": {"x": 1}})
    with pytest.raises(ValueError):
        SW.load_params()


def test_type_conflict_fail_loud():
    lc.set_override({"sleep": {"enabled": {"nested": 1}}})   # dict 覆盖标量
    with pytest.raises(ValueError):
        SW.load_params()


def test_non_dict_override_rejected():
    with pytest.raises(ValueError):
        lc.set_override([1, 2, 3])  # type: ignore[arg-type]


def test_override_does_not_touch_config_file():
    before = _CFG.read_bytes()
    lc.set_override({"sleep": {"enabled": False}})
    SW.load_params()
    lc.clear_override()
    assert _CFG.read_bytes() == before   # 不落盘 ⇒ 指纹不变
