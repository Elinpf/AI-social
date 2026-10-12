"""世界 AI 导演 v1 · WD-Core（机制表 / 判定树 R1–R6 / 剂量曲线 / RNG 先定 / 审计）。

权威：`v2/refs/world-director-design.md`（T210）、`v2/refs/world-event-mechanisms.md`（T216）、
`08 §1.2 T`（T238 登记）。三条保底：**(a) 显式 directed 事件** / **(b) 独立开关+剂量曲线** / **(c) 只对未来**。
本模块**纯函数为主**：不 emit、不改 state；事件封装由 `engine/hooks/world_director.py` 完成。
"""

from __future__ import annotations

from .events import EVENT_TYPES, spec
from .rng import draw_u64

# `WORLD_GROUP_EVENT.kind` 权威枚举（14，见 world-event-mechanisms §2.1）
WD_KINDS = frozenset({
    "season", "festival", "opportunity", "public_works", "supply_shock", "scarcity",
    "tension", "incident", "disaster", "epidemic", "visitor", "edict", "agenda", "mass_event",
})

# 剂量曲线（保守/中/激进）——全部**万分比整数**（bp），禁止浮点（P1）
DOSE_CURVES = {
    "conservative": {"prob_bp": 5000, "mag_bp": 5000, "dur_bp": 5000},    # 默认（最小剂量）
    "moderate":     {"prob_bp": 10000, "mag_bp": 10000, "dur_bp": 10000},
    "aggressive":   {"prob_bp": 20000, "mag_bp": 20000, "dur_bp": 20000},  # 灾难级：默认 OFF
}

# R5/R6：不得出现的键（金额/死亡/胜负等硬内核数字；指定个体行为/结果）
_HARD_NUM_KEYS = frozenset({
    "amount_mu", "price_mu", "tax_bp", "wage_mu", "fee_mu", "ubi_mu", "penalty_mu",
    "died", "deaths", "death", "winner", "loser", "score", "reward_mu", "grant_mu",
})
_INDIV_TARGET_KEYS = frozenset({
    "target_agent", "target", "assign", "assign_behavior", "force", "forced_behavior",
    "result", "outcome", "winner_agent",
})


def cfg_of(config: dict | None) -> dict:
    return (config or {}).get("world_director", {}) or {}


def dose_curve_of(cfg: dict) -> str:
    return str(cfg.get("dose_curve", "conservative"))


def resolve_dose(cfg: dict, mechanism_id: str) -> dict:
    """机制基础剂量 × 剂量曲线缩放（整数 bp 运算）。"""
    mech = (cfg.get("mechanisms", {}) or {}).get(mechanism_id, {}) or {}
    base = dict(mech.get("dose", {}) or {})
    curve = DOSE_CURVES.get(dose_curve_of(cfg), DOSE_CURVES["conservative"])
    out = {}
    for k, v in base.items():
        if isinstance(v, int) and k.endswith("_bp"):
            out[k] = int(v) * int(curve["prob_bp"]) // 10000
        elif isinstance(v, int) and k in ("prob_bp",):
            out[k] = int(v) * int(curve["prob_bp"]) // 10000
        else:
            out[k] = v
    return out


def mechanism_enabled(cfg: dict, mechanism_id: str) -> bool:
    if not cfg.get("enabled", False):
        return False
    mech = (cfg.get("mechanisms", {}) or {}).get(mechanism_id, {}) or {}
    if not mech.get("enabled", False):
        return False
    return int(resolve_dose(cfg, mechanism_id).get("prob_bp", 0)) > 0  # 剂量 0 ≡ 关闭


def _scope_of(cfg: dict, mech: dict) -> dict:
    return {"level": mech.get("scope_level", "global"), "place": mech.get("place")}


def rng_branch(global_seed: int, round_no: int, mech_index: int, n: int = 1) -> list:
    return draw_u64(global_seed, "world_director", round_no, mech_index, n)


def plan_directives(state, round_no: int, ctx, cfg: dict, mechanism_index: dict) -> list:
    """按机制表 + 剂量曲线，**RNG 先定**产出 directive 草案（不 emit、不改 state）。"""
    if not cfg.get("enabled", False):
        return []  # 保底 (b)：总开关关 → 零草案
    seed = int(getattr(ctx, "global_seed", 0))
    out = []
    for mid in sorted(cfg.get("mechanisms", {}) or {}):
        if not mechanism_enabled(cfg, mid):
            continue
        mech = cfg["mechanisms"][mid]
        dose = resolve_dose(cfg, mid)
        prob = int(dose.get("prob_bp", 0))
        idx = int(mechanism_index.get(mid, 0))
        roll = rng_branch(seed, round_no, idx, 1)[0] % 10000
        if roll >= prob:
            continue
        dur = int(dose.get("slots", 1))
        draft = {
            "mechanism_id": mid,
            "kind": str(mech.get("kind", "")).lower(),
            "scope": _scope_of(cfg, mech),
            "params": {k: v for k, v in dose.items() if k != "prob_bp"},
            "dose": dose,
            "dose_curve": dose_curve_of(cfg),
            "issued_round": int(round_no),
            "effective_from_round": int(round_no),  # 保底 (c)：只对未来（≥ issued）
            "expires_round": int(round_no) + dur,
            "directed": True,                        # 保底 (a)
            "rng_branch": {"roll_bp": roll, "prob_bp": prob, "idx": idx},
        }
        out.append((mid, draft))
    return out


def validate_directive(draft: dict, cfg: dict) -> dict:
    """判定树 R1–R6 的**真实现**；返回 {ok, reason, severity}。

    R1 作用对象/R2 粒度：`scope.level` 合法；不得出现个体目标键（targets_individual）
    R3 可观测：`directed=true`
    R4 时间性：`effective_from_round ≥ issued_round`（否则 rewrites_past）
    R5 数值归属：params/dose 不得含金额/死亡/胜负键
    R6 与个体决策：不得含强制/指定结果键
    WD-D1：`scope.level=agents` 且规模 < K → 审计告警(warn)，**非拒绝**
    """
    mech = draft.get("mechanism_id")
    if mech not in (cfg.get("mechanisms", {}) or {}):
        return {"ok": False, "reason": "invalid_mechanism", "severity": "reject"}
    if draft.get("dose_curve") not in DOSE_CURVES:
        return {"ok": False, "reason": "dose_curve_unknown", "severity": "reject"}
    scope = draft.get("scope") or {}
    if scope.get("level") not in ("global", "place", "group", "agents"):
        return {"ok": False, "reason": "invalid_scope_level", "severity": "reject"}
    keys = set((draft.get("params") or {}).keys()) | set((draft.get("dose") or {}).keys())
    if keys & _INDIV_TARGET_KEYS:
        return {"ok": False, "reason": "targets_individual", "severity": "reject"}   # R1/R2/R6
    if keys & _HARD_NUM_KEYS:
        return {"ok": False, "reason": "contains_hard_kernel_number", "severity": "reject"}  # R5
    if not draft.get("directed", False):
        return {"ok": False, "reason": "no_directed_marker", "severity": "reject"}   # R3
    if int(draft.get("effective_from_round", 0)) < int(draft.get("issued_round", 0)):
        return {"ok": False, "reason": "rewrites_past", "severity": "reject"}        # R4
    severity = "ok"
    if scope.get("level") == "agents" and len(scope.get("agents") or []) < int(cfg.get("K_warn", 3)):
        severity = "warn"                                                            # WD-D1
    return {"ok": True, "reason": None, "severity": severity}
