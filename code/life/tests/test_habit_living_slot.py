"""F-5 生活气息臂（`HITT_LIVING_SLOT`）单测：OFF 逐字节等价 / ON 只改闲时段 / 确定性 / 不丢 slot。

覆盖四条硬要求（对应口径卡 `round1-prereg-F5.md` §2 + §5）：
  1. **OFF（默认）逐字节等价**：2688 组 (agent×day_type×slot×slot_id×cash×focus) 输入下，
     `plan_slot` 的返回值与 baseline `d2d1993` 的实现**逐行相同**（夹具
     `tests/support/planner_off_golden.json` 由 `tools/habit/gen_planner_golden.py` 直接执行
     baseline 源码生成，不是手抄）；
  2. **ON 只改闲时段**：night / morning / workday-afternoon 的计划与 OFF **完全相同**；
     evening（以及周末 afternoon）若排上模板，必属生活类候选集；
  3. **确定性**：同一输入两次调用结果相同（可 replay；不读墙钟、不引入 RNG 状态）；
  4. **不丢 slot**：ON 的闲时段跳过 1/3 频率门是**有界**的——若该时段没有任何可排的生活类
     候选，必须回落到与 OFF 完全相同的原路径（而不是返回 None 把日子过空）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from life import planner as PL

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"
GOLDEN = Path(__file__).resolve().parent / "support" / "planner_off_golden.json"

LIVING_ALL = set(PL._LIVING_CANDIDATES["evening"]) | set(PL._LIVING_CANDIDATES["afternoon"])
PEERS = [f"P{i:03d}" for i in range(1, 17)]


def _templates() -> dict:
    d = json.loads((CONFIG / "activity_templates.json").read_text())
    return {t["template_id"]: t for t in d["templates"]}


def _places() -> dict:
    d = json.loads((CONFIG / "places.json").read_text())
    return {p["place_id"]: p for p in d["places"]}


def _planner(agent: str = "P001") -> PL.Planner:
    return PL.Planner(agent, _templates(), PEERS, _places())


def _living_slot(day_type: str, slot: str) -> bool:
    """口径卡 AMENDMENT-1：evening 每天都算；afternoon 只周末算。"""
    return slot == "evening" or (slot == "afternoon" and day_type == "weekend")


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv(PL.LIVING_ENV, raising=False)
    yield


# ---------------------------------------------------------------- 1. OFF 逐字节等价
def test_off_matches_baseline_golden():
    """夹具 = baseline `d2d1993` 源码的直接产出；当前树在开关未设时必须逐行相同。"""
    golden = json.loads(GOLDEN.read_text())["rows"]
    assert len(golden) == 2688, "夹具规模变了（生成脚本被改？）"
    got = []
    for row in golden:
        agent, day_type, slot, slot_id, cash, focus = row[:6]
        got.append(_planner(agent).plan_slot(day_type, slot, slot_id, cash, focus))
    want = [r[6] for r in golden]
    assert got == want


def test_switch_default_off(monkeypatch):
    assert PL.living_enabled() is False
    for v in ("1", "true", "YES", "on"):
        monkeypatch.setenv(PL.LIVING_ENV, v)
        assert PL.living_enabled() is True
    for v in ("0", "", "off", "no"):
        monkeypatch.setenv(PL.LIVING_ENV, v)
        assert PL.living_enabled() is False


# ---------------------------------------------------------------- 2. ON 只改闲时段
def test_on_leaves_non_living_slots_identical(monkeypatch):
    """night / morning / workday-afternoon：开与关的点子必须完全相同。"""
    p = _planner()
    checks = 0
    for day_type in ("workday", "weekend"):
        for slot in ("morning", "night"):
            for d in range(7):
                sid = f"day{d}-{slot}"
                for cash in (0, 50, 120):
                    off = p.plan_slot(day_type, slot, sid, cash)
                    monkeypatch.setenv(PL.LIVING_ENV, "1")
                    on = p.plan_slot(day_type, slot, sid, cash)
                    monkeypatch.delenv(PL.LIVING_ENV)
                    assert on == off, (day_type, slot, sid, cash)
                    checks += 1
    for d in range(7):
        sid = f"day{d}-afternoon"
        off = p.plan_slot("workday", "afternoon", sid, 120)
        monkeypatch.setenv(PL.LIVING_ENV, "1")
        on = p.plan_slot("workday", "afternoon", sid, 120)
        monkeypatch.delenv(PL.LIVING_ENV)
        assert on == off, sid
        checks += 1
    assert checks == 7 * 2 * 2 * 3 + 7


def test_on_evening_only_living_templates(monkeypatch):
    monkeypatch.setenv(PL.LIVING_ENV, "1")
    p = _planner()
    n_plan = 0
    for d in range(7):
        for agent_day_type in ("workday", "weekend"):
            for cash in (0, 120):
                got = p.plan_slot(agent_day_type, "evening", f"day{d}-evening", cash)
                if got is None:
                    continue
                n_plan += 1
                assert got["template_id"] in LIVING_ALL, got
                assert got["activity_type"] in ("socialize", "leisure"), got
                assert "evening" in _templates()[got["template_id"]]["slot_allowed"]
    assert n_plan > 0, "evening 一个计划都没排出来，用例失效"


def test_on_weekend_afternoon_living(monkeypatch):
    monkeypatch.setenv(PL.LIVING_ENV, "1")
    p = _planner()
    got = p.plan_slot("weekend", "afternoon", "day5-afternoon", 120)
    assert got is not None
    assert got["template_id"] in LIVING_ALL


# ---------------------------------------------------------------- 3. 确定性
def test_on_is_deterministic(monkeypatch):
    monkeypatch.setenv(PL.LIVING_ENV, "1")
    a = _planner("P003").plan_slot("workday", "evening", "day2-evening", 120)
    b = _planner("P003").plan_slot("workday", "evening", "day2-evening", 120)
    assert a == b


# ---------------------------------------------------------------- 4. 有界：不丢 slot
def test_on_falls_back_when_no_living_candidate(monkeypatch):
    """把生活类候选清空 ⇒ ON 必须回落到与 OFF 完全相同的原路径（含频率门）。"""
    monkeypatch.setenv(PL.LIVING_ENV, "1")
    monkeypatch.setattr(PL, "_LIVING_CANDIDATES",
                        {"evening": [], "afternoon": []})
    p = _planner()
    for d in range(7):
        for cash in (0, 120):
            on = p.plan_slot("workday", "evening", f"day{d}-evening", cash)
            monkeypatch.delenv(PL.LIVING_ENV)
            off = p.plan_slot("workday", "evening", f"day{d}-evening", cash)
            monkeypatch.setenv(PL.LIVING_ENV, "1")
            assert on == off, (d, cash)


def test_on_bypasses_frequency_gate(monkeypatch):
    """至少存在一个偶数 slot：OFF 被 1/3 频率门跳过、ON 却排上了生活类（有界绕过）。"""
    p = _planner()
    found = 0
    for d in range(7):
        sid = f"day{d}-evening"
        off = p.plan_slot("workday", "evening", sid, 120)
        monkeypatch.setenv(PL.LIVING_ENV, "1")
        on = p.plan_slot("workday", "evening", sid, 120)
        monkeypatch.delenv(PL.LIVING_ENV)
        if off is None and on is not None:
            found += 1
            assert on["template_id"] in LIVING_ALL
    assert found >= 1, "没有任何 slot 体现频率门绕过，用例失效"
