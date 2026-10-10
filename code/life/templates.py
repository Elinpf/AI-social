"""活动模板库加载器 / 校验器 / 效果归一（12-event-lineage §4.1/§4.2，T45）。

模板是**数据**（`config/activity_templates.json`），落盘后由本模块严格加载并校验；
版本纳入 `engine_version` 指纹（`engine/version.py` FINGERPRINT_FILES）。

纪律：
- 只读、纯函数、确定性；不引入任何 LLM。
- 本模块**不** import `life.settlement`（避免环依赖）；只返回归一化的 effect/dict，
  由 `life.settlement` 构造 EventSpec 并折叠。
"""
from __future__ import annotations

import json
from pathlib import Path

#: 模板文件名（与 engine.version.FINGERPRINT_FILES 一致）
TEMPLATES_FILENAME = "activity_templates.json"
REQUIRED_VERSION = "v1.2-t45"

_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / TEMPLATES_FILENAME

ACTIVITY_TYPES = frozenset({"work", "learn", "socialize", "leisure",
                            "self_care", "civic", "trade", "rest"})
COST_CLASSES = frozenset({"T0", "T1", "T2"})
VALID_DIMS = frozenset({"affinity", "trust", "respect", "familiarity"})
VALID_NEEED_DIMS = frozenset({"energy", "satiety", "social", "esteem", "mastery", "leisure"})

#: census 20 类（15-event-census-spec §1），template.census_class 必须落在此集合
CENSUS_CLASSES = frozenset({
    "E1_mentorship", "E2_gift_giving", "E3_combat_training", "E4_creative_collab",
    "E5_saving_money", "E6_whispered_comm", "E7_emotion_burnout", "E8_diff_scoring",
    "E9_scarcity_buy", "E10_skill_practice", "E11_polite_rejection",
    "E12_passion_vs_salary", "E13_group_proposal", "E14_academic_collab",
    "E15_counter_propose", "E16_select_location", "E17_power_conflict",
    "E18_rel_acceptance", "E19_ice_breaking", "E20_rel_maintenance",
})

#: 20 条模板的规范 template_id（12-event-lineage §4.2）
EXPECTED_TEMPLATE_IDS = (
    "mentorship", "gift", "combat_training", "creative_collab", "savings",
    "whisper", "burnout_event", "contest", "scarce_buy", "skill_practice",
    "polite_reject", "job_choice", "group_proposal", "academic_collab",
    "counter_propose", "select_location", "power_conflict", "rel_accept",
    "ice_break", "rel_maintain",
)

_REQUIRED_KEYS = (
    "template_id", "census_class", "activity_type", "place_allowed", "slot_allowed",
    "participants", "preconditions", "deterministic_settlement", "outputs",
    "llm_slots", "cost_class", "event_emit",
)


class TemplateError(Exception):
    """模板缺失/非法（硬报错，不静默回退）。"""


def _read(path: Path) -> dict:
    if not path.exists():
        raise TemplateError(f"缺少活动模板文件：{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise TemplateError(f"活动模板文件解析失败：{path}: {exc}") from exc


def validate_templates(data: dict, places: dict | None = None,
                       time_config: dict | None = None,
                       *, require_all_20: bool = True) -> None:
    """严格校验模板表；任何非法 -> TemplateError（不做回退）。"""
    if not isinstance(data, dict) or "templates" not in data:
        raise TemplateError("activity_templates.json 缺少 `templates` 数组")
    tmpls = data["templates"]
    if not isinstance(tmpls, list) or not tmpls:
        raise TemplateError("`templates` 必须为非空数组")

    valid_places = set(places.keys()) if places else None
    valid_slots = (set(time_config["SLOTS_PER_DAY"]) if time_config
                   and time_config.get("SLOTS_PER_DAY") else None)

    seen: set[str] = set()
    for t in tmpls:
        if not isinstance(t, dict):
            raise TemplateError("模板项必须为对象")
        for k in _REQUIRED_KEYS:
            if k not in t:
                raise TemplateError(f"模板 {t.get('template_id')!r} 缺少字段 `{k}`")
        tid = t["template_id"]
        if tid in seen:
            raise TemplateError(f"template_id 重复：{tid!r}")
        seen.add(tid)
        if t["census_class"] not in CENSUS_CLASSES:
            raise TemplateError(f"模板 {tid!r} 的 census_class 非法：{t['census_class']!r}")
        if t["activity_type"] not in ACTIVITY_TYPES:
            raise TemplateError(f"模板 {tid!r} 的 activity_type 非法：{t['activity_type']!r}")
        if t["cost_class"] not in COST_CLASSES:
            raise TemplateError(f"模板 {tid!r} 的 cost_class 非法：{t['cost_class']!r}")
        if not isinstance(t["place_allowed"], list) or not t["place_allowed"]:
            raise TemplateError(f"模板 {tid!r} 的 place_allowed 必须为非空数组")
        if valid_places is not None:
            bad = [p for p in t["place_allowed"] if p not in valid_places]
            if bad:
                raise TemplateError(f"模板 {tid!r} 引用未知场所：{bad}")
        if not isinstance(t["slot_allowed"], list) or not t["slot_allowed"]:
            raise TemplateError(f"模板 {tid!r} 的 slot_allowed 必须为非空数组")
        if valid_slots is not None:
            bad = [s for s in t["slot_allowed"] if s not in valid_slots]
            if bad:
                raise TemplateError(f"模板 {tid!r} 引用未知 slot：{bad}")
        p = t["participants"]
        if not isinstance(p, dict) or "min" not in p or "max" not in p:
            raise TemplateError(f"模板 {tid!r} 的 participants 需含 min/max")
        if not (0 < int(p["min"]) <= int(p["max"])):
            raise TemplateError(f"模板 {tid!r} 的 participants.min/max 非法")
        if not isinstance(p.get("roles"), list) or not p["roles"]:
            raise TemplateError(f"模板 {tid!r} 的 participants.roles 必须为非空数组")
        ds = t["deterministic_settlement"]
        if not isinstance(ds, dict) or "effects" not in ds:
            raise TemplateError(f"模板 {tid!r} 的 deterministic_settlement 缺少 effects")
        _validate_effects(tid, ds["effects"])
        if not isinstance(t["event_emit"], list) or not t["event_emit"]:
            raise TemplateError(f"模板 {tid!r} 的 event_emit 必须为非空数组")

    if require_all_20:
        missing = [x for x in EXPECTED_TEMPLATE_IDS if x not in seen]
        extra = [x for x in seen if x not in EXPECTED_TEMPLATE_IDS]
        if missing:
            raise TemplateError(f"模板库缺少规范模板：{missing}")
        if extra:
            raise TemplateError(f"模板库含规范外模板：{extra}")


def _validate_effects(tid: str, effects: dict) -> None:
    if not isinstance(effects, dict):
        raise TemplateError(f"模板 {tid!r} 的 effects 必须为对象")
    for kind, items in effects.items():
        if not isinstance(items, list):
            raise TemplateError(f"模板 {tid!r} 的 effects.{kind} 必须为数组")
        for it in items:
            if not isinstance(it, dict):
                raise TemplateError(f"模板 {tid!r} 的 effects.{kind} 项必须为对象")
            if kind == "need" and it.get("dim") not in VALID_NEEED_DIMS:
                raise TemplateError(f"模板 {tid!r} 引用未知 need 维度：{it.get('dim')!r}")
            if kind == "relation" and it.get("dim") not in VALID_DIMS:
                raise TemplateError(f"模板 {tid!r} 引用未知 relation 维度：{it.get('dim')!r}")


def load_activity_templates(config_dir: str | Path | None = None, *,
                            places: dict | None = None,
                            time_config: dict | None = None,
                            require_all_20: bool = True) -> dict[str, dict]:
    """加载并严格校验模板库，返回 {template_id: template}（按 template_id 升序）。"""
    p = Path(config_dir) / TEMPLATES_FILENAME if config_dir else _DEFAULT_PATH
    data = _read(Path(p))
    if str(data.get("version", "")) != REQUIRED_VERSION:
        raise TemplateError(
            f"活动模板版本不匹配：{data.get('version')!r} != {REQUIRED_VERSION!r}")
    validate_templates(data, places=places, time_config=time_config,
                       require_all_20=require_all_20)
    return {t["template_id"]: t for t in sorted(data["templates"],
                                                key=lambda x: x["template_id"])}


def template_ids(config_dir: str | Path | None = None) -> list[str]:
    return sorted(load_activity_templates(config_dir).keys())


# ---------------------------------------------------------------- 效果归一/角色映射
def role_agents(tpl: dict, participants: list[str]) -> dict[str, str]:
    """把 participants 列表按 template.participants.roles 顺序映射为 role -> agent。

    多出的参与者归到最后一个 role（群体模板的 member/peer2 等）。
    """
    roles = list(tpl["participants"].get("roles", []))
    out: dict[str, str] = {}
    if not roles:
        return out
    for i, aid in enumerate(sorted({a for a in participants if a})):
        role = roles[i] if i < len(roles) else roles[-1]
        # 同一 role 多次出现时保留第一个（确定性）
        out.setdefault(role, aid)
    return out


def normalized_effects(tpl: dict) -> list[dict]:
    """把 template.deterministic_settlement.effects 归一为带 `kind` 的列表（确定性顺序）。"""
    eff = tpl["deterministic_settlement"].get("effects", {})
    out: list[dict] = []
    for kind in ("skill", "need", "relation", "money", "state", "role"):
        for it in eff.get(kind, []) or []:
            out.append({"kind": kind, **it})
    return out


def money_intents(tpl: dict, roles: dict[str, str]) -> list[dict]:
    """把 money 效果转为 resource_intents（货币后果交 4.x，L-2 不直改账）。"""
    intents: list[dict] = []
    for it in tpl["deterministic_settlement"].get("effects", {}).get("money", []) or []:
        intents.append({
            "kind": it.get("kind", "transfer"),
            "from": roles.get(it.get("from", ""), None),
            "to": (roles.get(it.get("to", "")) if it.get("to") not in (None, "BANK", "MARKET", "SYSTEM")
                   else it.get("to")),
            "amount_mu": int(it.get("amount_mu", 0)),
            "reason": it.get("reason", it.get("kind", "transfer")),
            "event": it.get("event", "TRANSFER"),
        })
    return intents


def contest_spec(tpl: dict) -> dict | None:
    c = tpl["deterministic_settlement"].get("contest")
    if c and c.get("enabled"):
        return c
    return None


__all__ = [
    "TEMPLATES_FILENAME", "REQUIRED_VERSION", "TemplateError", "EXPECTED_TEMPLATE_IDS",
    "CENSUS_CLASSES", "load_activity_templates", "validate_templates", "template_ids",
    "role_agents", "normalized_effects", "money_intents", "contest_spec",
]
