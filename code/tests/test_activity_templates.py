"""T45：活动模板库（config/activity_templates.json）加载 / 校验 / 结算 / 指纹。

覆盖验收：
  ① 20 条模板 schema 合法且被加载；
  ② 至少 1 条模板端到端可触发（真内核 Phase 3.5，附日志证据）；
  ③ 模板文件纳入 engine_version 指纹。
"""

import json
import shutil
from pathlib import Path

import pytest

from life import templates
from engine import version
from engine.kernel import Engine
from engine.runner import default_config
from orchestration.integration import load_places, register_life_hooks

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


# ---------------- ① 加载 / 校验 ----------------

def test_load_20_templates():
    tbl = templates.load_activity_templates(places=load_places())
    assert len(tbl) == 20
    assert set(tbl) == set(templates.EXPECTED_TEMPLATE_IDS)
    for tid, t in tbl.items():
        for k in ("template_id", "census_class", "activity_type", "place_allowed",
                  "slot_allowed", "participants", "preconditions",
                  "deterministic_settlement", "outputs", "llm_slots", "cost_class",
                  "event_emit"):
            assert k in t, f"{tid} 缺 {k}"
        assert t["cost_class"] in ("T0", "T1", "T2")
        assert t["census_class"] in templates.CENSUS_CLASSES


def test_template_ids_sorted_and_complete():
    ids = templates.template_ids()
    assert ids == sorted(ids)
    assert ids == sorted(templates.EXPECTED_TEMPLATE_IDS)


def test_load_raises_on_missing_file(tmp_path):
    with pytest.raises(templates.TemplateError):
        templates.load_activity_templates(tmp_path)


def test_validate_rejects_bad_activity_type():
    data = json.loads((CONFIG_DIR / "activity_templates.json").read_text(encoding="utf-8"))
    data["templates"][0]["activity_type"] = "nonsense"
    with pytest.raises(templates.TemplateError):
        templates.validate_templates(data, require_all_20=False)


def test_validate_rejects_duplicate_id():
    data = json.loads((CONFIG_DIR / "activity_templates.json").read_text(encoding="utf-8"))
    data["templates"][1]["template_id"] = data["templates"][0]["template_id"]
    with pytest.raises(templates.TemplateError):
        templates.validate_templates(data, require_all_20=False)


def test_validate_rejects_unknown_place():
    data = json.loads((CONFIG_DIR / "activity_templates.json").read_text(encoding="utf-8"))
    data["templates"][0]["place_allowed"] = ["atlantis"]
    with pytest.raises(templates.TemplateError):
        templates.validate_templates(data, places=load_places(), require_all_20=False)


def test_version_mismatch_raises(tmp_path):
    cfg = tmp_path
    (cfg / "activity_templates.json").write_text(json.dumps(
        {"version": "v0", "templates": []}), encoding="utf-8")
    with pytest.raises(templates.TemplateError):
        templates.load_activity_templates(cfg)


# ---------------- ③ 指纹 ----------------

def test_fingerprint_includes_activity_templates():
    comps = version.component_digests()
    assert comps["activity_templates.json"] is not None
    assert version.compute_fingerprint() == version.compute_fingerprint()


def test_fingerprint_changes_when_templates_change(tmp_path):
    data = json.loads((CONFIG_DIR / "activity_templates.json").read_text(encoding="utf-8"))
    base = version.component_digests(tmp_path)  # 无文件 -> None
    assert base["activity_templates.json"] is None
    (tmp_path / "activity_templates.json").write_text(json.dumps(data), encoding="utf-8")
    a = version.component_digests(tmp_path)["activity_templates.json"]
    data["templates"][0]["cost_class"] = "T2"
    (tmp_path / "activity_templates.json").write_text(json.dumps(data), encoding="utf-8")
    b = version.component_digests(tmp_path)["activity_templates.json"]
    assert a != b


def test_engine_version_declares_templates_and_is_consistent():
    ev = version.load_engine_version()
    assert ev["components"]["activity_templates"]["file"] == "activity_templates.json"
    version.assert_version_consistency()  # 不应抛错


# ---------------- ② 端到端（真内核 Phase 3.5）----------------

def _engine_with(n=2, seed=42):
    register_life_hooks()
    cfg = default_config()
    cfg["lifecycle"] = {"ENABLED": False}   # 本测试聚焦活动模板 × 4.1 结算，隔离生命周期（代谢/判死）
    eng = Engine(seed, cfg)
    personas = {f"A{i:03d}": {"home_place": "residence", "needs_init": {}} for i in range(n)}
    eng.genesis(personas)
    for aid in personas:
        eng.state.ensure_agent(aid)
    return eng


def _run_rounds(eng, rounds):
    for r in range(rounds):
        eng.run_round(r)
    return eng.ledger.records


def _has(records, etype, **match):
    for rec in records:
        if rec["type"] != etype:
            continue
        p = rec.get("payload") or {}
        if all(p.get(k) == v for k, v in match.items()):
            return True
    return False


def test_mentorship_template_end_to_end():
    eng = _engine_with(n=2)
    a0, a1 = "A000", "A001"
    eng.state.agents[a0]["schedule"] = [{
        "slot_id": "day0-morning", "activity_type": "learn", "place": "school",
        "template_id": "mentorship", "planned_tick": 0, "priority": 0.7,
        "participants": [a0, a1]}]
    records = _run_rounds(eng, 4)

    # 事件合法
    from engine.events import EVENT_TYPES
    assert all(rec["type"] in EVENT_TYPES for rec in records)
    # 模板活动被触发
    assert _has(records, "ACTIVITY_STARTED", template="mentorship")
    assert _has(records, "ACTIVITY_COMPLETED", template="mentorship")
    # 模板确定性结算产出技能与关系事件（日志证据）
    assert _has(records, "SKILL_LEVEL_UP")
    assert _has(records, "RELATION_CHANGE")
    # 完成事件的参与者被记录（供 census/census E1 折叠）
    comp = next(r for r in records if r["type"] == "ACTIVITY_COMPLETED"
                and (r["payload"] or {}).get("template") == "mentorship")
    assert sorted(comp["payload"]["participants"]) == [a0, a1]


def test_gift_template_emits_resource_intent():
    eng = _engine_with(n=2)
    a0, a1 = "A000", "A001"
    eng.state.agents[a0]["schedule"] = [{
        "slot_id": "day0-afternoon", "activity_type": "socialize", "place": "plaza",
        "template_id": "gift", "planned_tick": 0, "priority": 0.7,
        "participants": [a0, a1]}]
    records = _run_rounds(eng, 4)
    comp = next(r for r in records if r["type"] == "ACTIVITY_COMPLETED"
                and (r["payload"] or {}).get("template") == "gift")
    intents = comp["payload"]["resource_intents"]
    assert any(i["kind"] == "gift" and i["reason"] == "gift"
               and i["amount_mu"] == 100 for i in intents)
    # 货币后果经 resource_intents 交 4.x（L-2：life hook 不直改账）；
    # 由 Phase 4.1 settle_market 消费并原子结算为 TRANSFER。
    assert _has(records, "TRANSFER", **{"from": a0, "to": a1, "amount": 100})
    from engine import conservation
    assert conservation.check_conservation(eng.state) == []
    assert int(eng.state.cash[a0]) <= 10000 - 100   # 付款方至少扣了礼金（另可能有代谢/税负）


def test_templates_do_not_break_plain_activities():
    """非模板活动沿用既有满足度路径（向后兼容）。"""
    eng = _engine_with(n=1)
    a0 = "A000"
    eng.state.agents[a0]["schedule"] = [{
        "slot_id": "day0-morning", "activity_type": "self_care", "place": "residence",
        "planned_tick": 0, "priority": 0.7}]
    records = _run_rounds(eng, 4)
    comp = next(r for r in records if r["type"] == "ACTIVITY_COMPLETED")
    assert comp["payload"]["resource_intents"] == []
    assert "template" not in comp["payload"]
