"""Enumerations & default parameters for the life layer.

Authoritative sources (frozen, do not restate):
  - `v1.1/00-architecture.md` §2 (places/roles), §3 (time), §4 (interfaces)
  - `v1.1/06-life-layer.md` §3 (memory), §4 (schedule), §7 (needs), §10 (enums)
  - `v1.1/08-engine-stats-extension.md` §1.2 (events), §3.1 (time config)

This module only *mirrors* those constants so the life layer can run standalone.
Where the kernel exposes the same function (e.g. `derive_time`) the life layer
prefers the kernel's; this is a fallback / shared reference.
"""
from __future__ import annotations

import json
from pathlib import Path

# ---- Time structure (00 §3.1 / 08 §3.1) --------------------------------------
TIME_CONFIG = {
    "ROUNDS_PER_SLOT": 3,
    "SLOTS_PER_DAY": ["morning", "afternoon", "evening", "night"],
    "DAYS_PER_WEEK": 7,
    "DAY_TYPES": ["workday"] * 5 + ["weekend"] * 2,
    "WEEK_PHASES": ["PLAN", "CONTACT", "ACTIVITY", "REVIEW"],
}

DAY_TYPE_PARAMS = {
    "workday": {"work_required": True, "leisure_weight": 0.3, "social_event_prob": 0.05,
                "sleep_slots": ["night"]},
    "weekend": {"work_required": False, "leisure_weight": 0.7, "social_event_prob": 0.25,
                "sleep_slots": ["night"]},
}


def derive_time(round_no: int, cfg: dict = TIME_CONFIG) -> dict:
    """Pure: round -> {week, day, day_of_week, day_type, slot, tick_in_slot}."""
    rps = cfg["ROUNDS_PER_SLOT"]
    spd = len(cfg["SLOTS_PER_DAY"])
    rounds_per_day = rps * spd
    day = round_no // rounds_per_day
    slot_idx = (round_no % rounds_per_day) // rps
    tick_in_slot = round_no % rps
    week = day // cfg["DAYS_PER_WEEK"]
    day_of_week = day % cfg["DAYS_PER_WEEK"]
    return {
        "week": week,
        "day": day,
        "day_of_week": day_of_week,
        "day_type": cfg["DAY_TYPES"][day_of_week],
        "slot": cfg["SLOTS_PER_DAY"][slot_idx],
        "tick_in_slot": tick_in_slot,
    }


def week_phase(time_coord: dict) -> str:
    """Map a time coordinate to the Agentopia-style weekly phase (06 §4.2)."""
    day = time_coord["day_of_week"]
    slot = time_coord["slot"]
    if day == 0 and slot == "morning":
        return "PLAN"
    if day == 6 and slot in ("evening", "night"):
        return "REVIEW"
    if day <= 4:
        return "CONTACT"
    return "ACTIVITY"


# ---- Needs / goals (06 §7.2, §10) -------------------------------------------
NEED_DIMS = ["energy", "satiety", "social", "esteem", "mastery", "leisure"]
NEED_MIN, NEED_MAX = 0, 100
THETA_DEP = 20

# deterministic per-slot natural decay (06 §10 回填)
NEED_DECAY = {"satiety": 8, "energy": 4, "social": 5, "esteem": 2, "mastery": 1, "leisure": 6}

# activity_type -> satisfaction per need dim (06 §7.2, skeleton values)
ACTIVITY_SATISFACTION = {
    "work":      {"energy": -6, "satiety": -2, "esteem": 4, "mastery": 3},
    "learn":     {"energy": -3, "mastery": 6, "esteem": 1},
    "socialize": {"social": 10, "leisure": 4, "energy": -2},
    "leisure":   {"leisure": 10, "energy": 2, "social": 2},
    "self_care": {"energy": 10, "satiety": 12, "leisure": 3},
    "civic":     {"esteem": 4, "social": 3, "energy": -2},
    "trade":     {"esteem": 2, "satiety": -1, "energy": -2},
    "rest":      {"energy": 14, "satiety": -1},
}

# ---- Activities & places (00 §2.2 / 06 §10) ---------------------------------
ACTIVITY_TYPES = ["work", "learn", "socialize", "leisure", "self_care", "civic", "trade", "rest"]

# activity_type -> allowed place affordance match; places declare `affordances`.
ACTIVITY_TO_PLACES = {
    "work":      ["farm", "workshop", "kitchen", "clinic", "school", "office", "market"],
    "learn":     ["school", "library"],
    "socialize": ["cafe", "plaza", "park", "community_center", "hall"],
    "leisure":   ["park", "cafe", "hall"],
    "self_care": ["residence", "clinic", "kitchen"],
    "civic":     ["town_hall", "plaza"],
    "trade":     ["market", "bank"],
    "rest":      ["residence"],
}

# role_id -> primary work place (00 §2.5)
ROLE_WORKPLACE = {
    "farmer": "farm", "craftsman": "workshop", "cook": "kitchen", "merchant": "market",
    "healer": "clinic", "teacher": "school", "public_servant": "town_hall", "banker": "bank",
    "artist": "hall", "student": "school", "unemployed": "plaza",
}

# ---- Memory (06 §3) ----------------------------------------------------------
MEMORY_KINDS = ["observation", "plan", "reflection", "chat"]
RETRIEVAL_DEFAULTS = {
    "top_k": 8,
    "decay": 0.995,
    "w_rec": 1.0,
    "w_imp": 1.0,
    "w_rel": 1.0,
}
THETA_REFLECT = 150          # accumulated importance trigger
R_MAX_PER_WEEK = 7           # max reflections per agent per week
IMPORTANCE_MIN, IMPORTANCE_MAX = 0, 10

# ---- Relations (06 §6) -------------------------------------------------------
RELATION_DIMS = ["affinity", "trust", "respect"]
RELATION_RANGE = {"affinity": (-100, 100), "trust": (-100, 100), "respect": (0, 100),
                  "familiarity": (0, 100)}
W_MIN, W_MAX = -100, 100
EPS, EPS_STRONG = 20, 50
RELATION_DELTA_MAX = 10          # 单次交互幅度上限 Δ_max

# ---- M6 critical-only 维度价值表（T213↔T215↔T221 的**单一语义源**）-----------
# `LLM_JUDGMENT.dimension` 中，在 L3（critical-only 降级）时**不可跳过**的维度。
#   * 发布投影 = `config/policy.json::llm_budget.critical_dimensions`（引擎不 import life，
#     只能读 config）；由 `code/tests/test_dimension_alias_guard.py` 断言两者相等（防漂移）。
#   * ⚠️ `rel_respect`（关系四维之一）≠ `respect`（T127 社交评价维）——**不得归一**。
#   * `importance` 属**另一条轴**（`_score_importance` → `llm.call`，非 judge），
#     不在此表；它由 `llm_budget.critical_importance` 独立控制。
CRITICAL_DIMENSIONS = ("weekly_focus", "rel_affinity", "rel_trust", "rel_respect")

# ---- M2b 判别式候选枚举（**单一真源**；T222）---------------------------------
# 「受限选择」路径下每个 judge 维度的合法候选。**由 life 代码确定性枚举、LLM 只“选”不“造枚举”**
# （T213 §1 的安全阀）：候选表不完备 → 判别式会**系统性看不见真实可能性**。
#
# 逃生项（escape）：每个维度**必须**含一个逃生项 `undecidable`，
# 保证「说不清 / 不合任何既定类别」时**不被强迫瞎选**。命中逃生项的比率 = `escape_rate`：
#   **偏高 = 我们的枚举漏了东西 → 回去补 §枚举，而不是调阈值**（设计缺陷的早期信号）。
ESCAPE_OPTION = "undecidable"

# 维度 -> 合法候选（末位恒为逃生项）。订单/口径：
#   * relation 四维用 `rel_<dim>` 前缀（与 `agent._maybe_soft_judge` 一致）；
#   * `respect`（T127 社交评价维）**不含前缀**，与 `rel_respect` 是不同维度，**不得归一**；
#   * `weekly_focus` 的语义候选 = `planner.FOCUS_OPTIONS`（此处复制其值，实施时收敛为引用）；
#   * `mentor_relation` 属**登记维**（`config/activity_templates.json` 已声明）但 **life 无调用点** → 见 `MENTOR_DIMENSION_WIRED`；
#   * `importance` 属**另一条轴**（`_score_importance` → `llm.call`，非 judge），在此仅为“候选集单一真源”。
JUDGMENT_OPTIONS: dict[str, tuple[str, ...]] = {
    "rel_affinity":    ("formed", "not_formed", ESCAPE_OPTION),
    "rel_trust":       ("formed", "not_formed", ESCAPE_OPTION),
    "rel_respect":     ("formed", "not_formed", ESCAPE_OPTION),
    "rel_familiarity": ("formed", "not_formed", ESCAPE_OPTION),
    "weekly_focus":    ("work", "social", "study", "leisure", "balance", ESCAPE_OPTION),
    "stance":          ("accept", "reject", ESCAPE_OPTION),
    "respect":         ("high", "low", ESCAPE_OPTION),
    "affection":       ("high", "low", ESCAPE_OPTION),
    "importance":      tuple(str(i) for i in range(1, 11)) + (ESCAPE_OPTION,),  # T213 §5
    "mentor_relation": ("formed", "not_formed", ESCAPE_OPTION),  # 登记维（未接线）
}

# 逃生项命中后的**确定性兜底**（不静默：落 `method="rule"` / `fallback="escape_option"`）。
ESCAPE_FALLBACK: dict[str, str] = {
    "rel_affinity": "not_formed", "rel_trust": "not_formed",
    "rel_respect": "not_formed", "rel_familiarity": "not_formed",
    "weekly_focus": "balance",
    "stance": "reject", "respect": "low", "affection": "low",
    "importance": "5",
    "mentor_relation": "not_formed",   # 更严格：无强证据不结师（T212 观察到判别式偏宽松）
}

# `mentor_relation` 是**登记维**：`config/activity_templates.json` 声明了它，但 life 当前
# **没有对应的 `LLM_JUDGMENT` 调用点**（`_maybe_soft_judge` 只发 `rel_*`）。任何“对该维做兜底”
# 的机制在此阶段都是 **inert**（等 E1 Mentorship 真正接线才生效）。**不得假装它有活。**
MENTOR_DIMENSION_WIRED = False



# ---- Goals (06 §7.1) ---------------------------------------------------------
GOAL_LAYERS = ["survival", "growth", "social", "meaning"]
KIND_TO_LAYER = {"security": "survival", "wealth": "survival", "mastery": "growth",
                 "achievement": "growth", "social": "social", "meaning": "meaning"}
GOAL_PROGRESS_PER_ACTIVITY = 0.15   # deterministic per matching activity

# ---- Norms / tags (06 §10, 08 §1.2 F/L) --------------------------------------
NORM_DEFAULT_THRESHOLD = 3          # supporters required to adopt (deterministic)
ACTIVITY_TAG_TOPIC = {"work": "labor", "learn": "study", "socialize": "gossip",
                      "leisure": "fun", "self_care": "home", "civic": "governance",
                      "trade": "commerce", "rest": "rest"}

# ---- Perception (08 §3.5 R1/R2) ---------------------------------------------
# SINGLE SOURCE OF TRUTH = the engine's `config/perception_scope.json` (T41 / Leader
# ruling). The life layer reads that file strictly: missing / malformed / version
# mismatch -> hard error (NO silent fallback), so there is exactly one definition.
_PERCEPTION_SCOPE_REQUIRED_VERSION = "v1.2-r2"
_VALID_VISIBILITY = frozenset({"global", "place_local", "members", "private",
                               "participants_only", "subject_only"})


def load_perception_scope(path: str | Path | None = None) -> tuple[dict, str, str]:
    """Return (scope, default_visibility_class, source). Strict; no fallback."""
    p = Path(path) if path else (Path(__file__).resolve().parents[1] / "config" /
                                 "perception_scope.json")
    if not p.exists():
        raise RuntimeError(f"PERCEPTION_SCOPE 单一来源缺失：{p}（T41：不得静默回退）")
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("version") != _PERCEPTION_SCOPE_REQUIRED_VERSION:
        raise RuntimeError(
            f"PERCEPTION_SCOPE 版本不匹配：{data.get('version')!r} != "
            f"{_PERCEPTION_SCOPE_REQUIRED_VERSION!r}")
    scope = dict(data["scope"])
    default_cls = data.get("default_visibility_class", "place_local")
    bad = {k: v for k, v in scope.items() if v not in _VALID_VISIBILITY}
    if bad or default_cls not in _VALID_VISIBILITY:
        raise RuntimeError(f"PERCEPTION_SCOPE 含非法 visibility_class：{bad} / 默认 {default_cls}")
    return scope, default_cls, "engine-config"


PERCEPTION_SCOPE, DEFAULT_VISIBILITY, PERCEPTION_SCOPE_SOURCE = load_perception_scope()


def load_visibility_flags(path: str | Path | None = None) -> dict:
    """G1 可见性开关（默认 false；进 engine_version 指纹）。"""
    p = Path(path) if path else (Path(__file__).resolve().parents[1] / "config" /
                                 "perception_scope.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    return {"place_local_actor_fallback": bool(data.get("place_local_actor_fallback", False))}


PLACE_LOCAL_ACTOR_FALLBACK = load_visibility_flags()["place_local_actor_fallback"]

PHASE_LIFE = 35  # integer encoding of Phase 3.5 (08 §2.1)
