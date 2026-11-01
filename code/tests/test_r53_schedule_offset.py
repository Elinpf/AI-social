"""R53 作息「个体差异 / 错峰」臂 —— 零 LLM 单测（env `HITT_SCHEDULE_OFFSET`，默认关）。

口径卡：`reports/R53-prereg-schedule-offset-20261102.md`
  * §9.5 关掉时必须逐字节等价（本条用**改动前树 `18a78fe` 上跑出的冻结指纹**证明）；
  * §9.4 四条机制约束（确定性 / 取值合法 / 时点边界 / 不许抢生产）。

本文件不起引擎、不调 LLM（`_weekly_slots` 的 `focus` 直接给定，绕过 LLM 判定）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import constants as C
from life import schedule_offset as S
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.util import canonical_json, sha256_hex

CONFIG = Path(__file__).resolve().parents[1] / "config"

#: 夹具 agent（覆盖 5 个角色，含多个同角色对：farmer P001/P003/P012、craftsman P002/P013）
FIXTURE_AGENTS = ["P001", "P002", "P004", "P007", "P012", "P013"]

#: **改动前冻结指纹**：`18a78fe` 的树在**开关未设**时跑出的 `_weekly_slots` 全集
#: （canonical_json(agent_id → slots) 的 sha256）。改口径（角色表/场所表/基础作息）即失效。
FROZEN_OFF_SHA256 = "87d2a402a1c0fad3534d5a60b377635176c399da71f16265cb2a34cbe2a0dd40"


class _Kernel:
    """最小内核桩：plan 阶段不 perceive / 不提交意图。"""

    def perceive(self, agent_id):  # pragma: no cover - 不应被调用
        raise RuntimeError("plan 阶段不应 perceive")

    def submit_intent(self, *a, **kw):  # pragma: no cover
        pass


def _places() -> dict:
    doc = json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))
    return {p["place_id"]: p for p in doc["places"]}


def _agent(tmp_path: Path, aid: str, places: dict) -> LifeLayerAgent:
    personas = load_personas(CONFIG / "personas.json")
    return LifeLayerAgent(aid, personas[aid], _Kernel(),
                          side_store=SideStore(tmp_path / f"side-{aid}"),
                          embedding=HashEmbeddingModel(), places=places,
                          peers=sorted(personas), peer_names={})


def _slots(tmp_path: Path, aid: str, places: dict) -> list:
    ag = _agent(tmp_path, aid, places)
    wv = SimpleNamespace(cash=100, time=SimpleNamespace(week=0))
    return ag._weekly_slots(wv, focus="balance")


def _all_slots(tmp_path: Path, places: dict) -> dict:
    return {aid: _slots(tmp_path, aid, places) for aid in FIXTURE_AGENTS}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv(S.OFFSET_ENV, raising=False)


# ---- 1. 开关默认关 --------------------------------------------------------
def test_switch_default_off(monkeypatch):
    assert S.offset_enabled() is False
    for raw in ("0", "false", "off", "", "  "):
        monkeypatch.setenv(S.OFFSET_ENV, raw)
        assert S.offset_enabled() is False, f"{raw!r} 不应被当成开"
    for raw in ("1", "true", "yes", "on", "ON", " True "):
        monkeypatch.setenv(S.OFFSET_ENV, raw)
        assert S.offset_enabled() is True, f"{raw!r} 应被当成开"


# ---- 2. OFF 逐字节等价（改动前冻结指纹） ----------------------------------
def test_off_byte_identical_to_pre_change(tmp_path):
    places = _places()
    slots = _all_slots(tmp_path, places)
    assert sha256_hex(canonical_json(slots)) == FROZEN_OFF_SHA256
    # OFF 态不得出现 R53 审计键
    for aid, arr in slots.items():
        for s in arr:
            assert "schedule_offset" not in s, f"{aid} {s['slot_id']} OFF 态出现审计键"
    # OFF 态 planned_tick 仍是基准网格（与改动前同一公式）
    for arr in slots.values():
        for s in arr:
            dow = int(s["slot_id"].split("-")[0][3:])
            si = C.TIME_CONFIG["SLOTS_PER_DAY"].index(s["slot_id"].split("-")[1])
            assert s["planned_tick"] == dow * 12 + si * C.TIME_CONFIG["ROUNDS_PER_SLOT"]


# ---- 3. ON 确定性（同一 agent/slot 两次结果相同） -------------------------
def test_on_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.setenv(S.OFFSET_ENV, "1")
    places = _places()
    a = _all_slots(tmp_path, places)
    b = _all_slots(tmp_path, places)
    assert canonical_json(a) == canonical_json(b)


# ---- 4. ON 相位偏移：取值域 {0,+1}、按人常量、不越 slot 边界 ------------
def test_tick_offset_domain_and_constancy(tmp_path, monkeypatch):
    monkeypatch.setenv(S.OFFSET_ENV, "1")
    places = _places()
    slots = _all_slots(tmp_path, places)
    for aid, arr in slots.items():
        off = S.tick_offset(aid)
        assert off in (0, 1), f"{aid} 相位越界: {off}"
        assert S.phase_raw(aid) in (-1, 0, 1)
        # -1 会越过 slot 边界 ⇒ 契约 §9.4.3 回退 0
        if S.phase_raw(aid) < 0:
            assert off == 0
        for s in arr:
            dow = int(s["slot_id"].split("-")[0][3:])
            si = C.TIME_CONFIG["SLOTS_PER_DAY"].index(s["slot_id"].split("-")[1])
            base = dow * 12 + si * C.TIME_CONFIG["ROUNDS_PER_SLOT"]
            assert s["planned_tick"] == base + off
            # 不越过本 slot 边界
            assert si * C.TIME_CONFIG["ROUNDS_PER_SLOT"] <= (s["planned_tick"] - dow * 12) \
                < (si + 1) * C.TIME_CONFIG["ROUNDS_PER_SLOT"]
            assert s["schedule_offset"] == {"ticks": off,
                                            "activity_changed": s["schedule_offset"]["activity_changed"]}


# ---- 5. ON 活动类型个体化：合法、锁定槽不动、确有变化 -------------------
def test_on_activity_individualized_legally(tmp_path, monkeypatch):
    places = _places()
    ag_off = _agent(tmp_path, "P001", places)
    wv = SimpleNamespace(cash=100, time=SimpleNamespace(week=0))
    off = ag_off._weekly_slots(wv, focus="balance")
    monkeypatch.setenv(S.OFFSET_ENV, "1")
    ag_on = _agent(tmp_path, "P001", places)
    on = ag_on._weekly_slots(wv, focus="balance")
    changed = 0
    for s_off, s_on in zip(off, on):
        slot = s_off["slot_id"].split("-")[1]
        dow = int(s_off["slot_id"].split("-")[0][3:])
        day_type = C.TIME_CONFIG["DAY_TYPES"][dow]
        if S.slot_locked(day_type, slot, s_off["activity_type"]):
            assert (s_on["activity_type"], s_on["place"]) == \
                   (s_off["activity_type"], s_off["place"]), f"{s_off['slot_id']} 锁定槽被改"
            assert s_on["schedule_offset"]["activity_changed"] is False
            continue
        if s_on["schedule_offset"]["activity_changed"]:
            changed += 1
            atype, place = s_on["activity_type"], s_on["place"]
            # 取值合法（既有场所 ∧ open_slots ∧ affordances）
            assert ag_on._valid(atype, place, slot), f"{s_off['slot_id']} 候选不合法"
            # 不新造活动类型/场所
            assert place in C.ACTIVITY_TO_PLACES[atype]
        # 未变化时与原值完全一致（不得顺手改别的字段）
        if not s_on["schedule_offset"]["activity_changed"]:
            assert (s_on["activity_type"], s_on["place"]) == \
                   (s_off["activity_type"], s_off["place"])
    assert changed > 0, "ON 臂没有任何活动类型被个体化（机制是死代码）"


# ---- 6. 需求剥夺覆盖的 slot 不被个体化（habitual=False 直通） ------------
def test_need_driven_slot_not_individualized():
    places = _places()
    base = ("self_care", "kitchen")
    # 该 slot 的取值不是基础作息（来自 needs<θ_dep 覆盖）⇒ habitual=False
    out = S.plan_activity("P001", "workday", "evening", "day0-evening", base,
                          lambda a, p, s: True, habitual=False)
    assert out == (base[0], base[1], False)


# ---- 7. 候选池只含该 slot 合法的既有 (atype, place) ---------------------
def test_candidates_are_existing_and_legal():
    places = _places()

    def valid(atype, place, slot):
        spec = places.get(place, {})
        return slot in spec.get("open_slots", []) and atype in spec.get("affordances", [])

    base = ("socialize", "cafe")
    cands = S.candidates("workday", "evening", base, valid)
    assert cands, "evening 的候选池不应为空"
    assert base not in cands
    assert cands == sorted(cands), "候选必须稳定排序（幂等）"
    for atype, place in cands:
        assert place in C.ACTIVITY_TO_PLACES[atype]
        assert valid(atype, place, "evening")
