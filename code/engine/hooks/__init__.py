"""Phase 3.5（LIFE）与 Phase 4（ARBITRATE）hook 链注册表。

设计（对齐 08 §2）：
  - Phase 4 hook 链 4.1–4.8 **顺序与语义冻结**（X2），默认全部为空实现占位；
  - Phase 3.5 hook 链 L1–L7 顺序固定，默认空实现占位；
  - 生活层（life-layer-dev）通过 register_phase35_hook(name, fn) 注入实现，
    内核不硬编码、不改 life/ 目录。

hook 契约（纯函数，I1–I5）：
  fn(state, round_no, ctx) -> list[EventSpec]
  - 不返回货币 delta；生活/活动产生的货币后果放入 spec 的 pending_intents（交 4.x）；
  - 不得直写 state；随机只能经 ctx.rng(stream_id, seq, n)；
  - 不得读墙钟/环境变量/网络。
"""

from __future__ import annotations

from .econ import settle_market, settle_obligations, apply_tax
from .lifecycle import (
    apply_metabolism, apply_penalty, check_lifecycle, resolve_revival, check_death,
)
# v2 物理层：生产先更新库存 → 4.1 市场再用新库存（首项，不改 4.1–4.8 相对序）
# 防御式挂载：production 模块若尚未就绪（如 DEFAULTS 键不匹配），退化为 no-op，
# 不阻断内核 import（待 econ-dev 修正后自动启用真实实现）。
try:
    from .production import apply_production
    PRODUCTION_HOOK_AVAILABLE = True
    PRODUCTION_HOOK_ERROR = None
except Exception as _prod_exc:  # pragma: no cover
    PRODUCTION_HOOK_AVAILABLE = False
    PRODUCTION_HOOK_ERROR = repr(_prod_exc)

    def apply_production(state, round_no, ctx):
        return []
from .life_hooks import (
    advance_time, resolve_schedule, settle_activities, apply_needs,
    update_relations, write_memories, emit_tags,
)

# ---- Phase 4 ARBITRATE：4.1–4.8（顺序冻结，X2）----
PHASE4_CHAIN = [
    ("apply_production", apply_production),    # v2 首项：生产/库存（4.1 前）
    ("settle_market", settle_market),          # 4.1
    ("settle_obligations", settle_obligations),  # 4.2
    ("apply_tax", apply_tax),                  # 4.3
    ("apply_metabolism", apply_metabolism),    # 4.4
    ("apply_penalty", apply_penalty),          # 4.5
    ("check_lifecycle", check_lifecycle),      # 4.6
    ("resolve_revival", resolve_revival),      # 4.7
    ("check_death", check_death),              # 4.8
]

# ---- Phase 3.5 LIFE：L1–L7（顺序固定）----
PHASE35_CHAIN = [
    ("advance_time", advance_time),            # L1
    ("resolve_schedule", resolve_schedule),    # L2
    ("settle_activities", settle_activities),  # L3
    ("apply_needs", apply_needs),              # L4
    ("update_relations", update_relations),    # L5
    ("write_memories", write_memories),        # L6
    ("emit_tags", emit_tags),                  # L7
]


def _as_name_map(chain):
    return {name: fn for name, fn in chain}


_PHASE35_MAP = _as_name_map(PHASE35_CHAIN)
_PHASE4_MAP = _as_name_map(PHASE4_CHAIN)
_PHASE35_ORDER = [name for name, _ in PHASE35_CHAIN]
_PHASE4_ORDER = [name for name, _ in PHASE4_CHAIN]


def assert_production_available(config) -> None:
    """fail-loud 三态协同（T114；防线不得削弱）：

    - `economy.enabled=true` 且 `production.enabled=true` 且 hook 未挂载 → **raise**（T35 同型静默停摆防线）；
    - `production.enabled=false`（**显式声明关闭**）→ **永不 raise**（哪怕未挂载——这是有意消融，非事故）；
    - `economy.enabled=false` → 允许 no-op（既有行为）。
    读键：`policy.production.enabled` / runtime `config.production.enabled`，**默认 true**。
    `production.enabled` 读取失败时按 true（保守：宁可 fail-loud）。
    """
    pol = (config or {}).get("policy", {}) if isinstance(config, dict) else {}
    econ = pol.get("economy", {}) if isinstance(pol, dict) else {}
    econ_on = bool(econ.get("enabled", False)) if isinstance(econ, dict) else False
    if isinstance(config, dict):
        rt_e = config.get("economy")
        if isinstance(rt_e, dict) and "enabled" in rt_e:      # runtime 覆盖优先（同 econ._econ_enabled）
            econ_on = bool(rt_e["enabled"])
    prod_on = True
    if isinstance(config, dict):
        rt = config.get("production")
        if isinstance(rt, dict) and "enabled" in rt:
            prod_on = bool(rt["enabled"])
        elif isinstance(pol, dict) and isinstance(pol.get("production"), dict) \
                and "enabled" in pol["production"]:
            prod_on = bool(pol["production"]["enabled"])
    if econ_on and prod_on and not PRODUCTION_HOOK_AVAILABLE:
        raise RuntimeError(
            "economy.enabled=true 且 production.enabled=true 但 `apply_production` 未挂载"
            f"（生产将静默停摆）：{PRODUCTION_HOOK_ERROR}")


def register_phase35_hook(name: str, fn) -> None:
    """注入/覆盖 Phase 3.5 某个 hook（life 层用）。name ∈ L1–L7 名。"""
    if name not in _PHASE35_MAP:
        raise KeyError(f"未知 Phase 3.5 hook 名: {name!r}（合法：{_PHASE35_ORDER}）")
    _PHASE35_MAP[name] = fn


def register_phase4_hook(name: str, fn) -> None:
    """注入/覆盖 Phase 4 某个 hook（econ/lifecycle 层用）。顺序不可变。"""
    if name not in _PHASE4_MAP:
        raise KeyError(f"未知 Phase 4 hook 名: {name!r}（合法：{_PHASE4_ORDER}）")
    _PHASE4_MAP[name] = fn


def get_phase35_hooks():
    return [_PHASE35_MAP[n] for n in _PHASE35_ORDER]


def get_phase4_hooks():
    return [_PHASE4_MAP[n] for n in _PHASE4_ORDER]


def phase4_order() -> list:
    return list(_PHASE4_ORDER)


def phase35_order() -> list:
    return list(_PHASE35_ORDER)
