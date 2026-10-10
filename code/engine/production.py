"""A 物理层 · 生产/库存/折旧 纯内核（v2 P1，schema 无关部分）。

依据 `v2/01-economy-substrate.md §2`（A 层公式「写死」）：
  qty(g, agent, t) = floor( base_rate[g] × (1 + 0.1·skill_level) × resource_factor × (1 + tool_bonus) )

本模块**只含确定性纯函数**（无 I/O、无 LLM、整数运算、禁浮点记账）：
生产函数、资源丰度（固定种子抖动）、库存增删/上限溢出、消耗（生存/上游投入）、折旧、`M(t)≥0` 销毁地板、保底铸币。

> 事件发射（`PRODUCE/CONSUME/DEPRECIATE/PRODUCE_OVERFLOW`）与 Phase4 hook 接线**待 T90 schema 登记完成后**
> 放在 `engine/hooks/production.py`；本模块不含事件，先独立可测。

定点约定：比例一律「千分比 milli」（1000 == 1.0），金额/数量一律整数。
"""

from __future__ import annotations

from engine.rng import draw_u64

MILLI = 1000

# ---- 商品注册表（base_rate 以 milli 表示；p_ref_mu 仅统计计价，非成交价）----
GOODS: dict[str, dict] = {
    "food":     {"kind": "food",     "base_milli": 2000, "p_ref_mu": 100,  "shelf_life": 8},
    "material": {"kind": "material", "base_milli": 1000, "p_ref_mu": 150,  "shelf_life": None},
    "tool":     {"kind": "tool",     "base_milli": 300,  "p_ref_mu": 500,  "shelf_life": None},
    "service":  {"kind": "service",  "base_milli": 1000, "p_ref_mu": 200,  "shelf_life": None},
    "art":      {"kind": "art",      "base_milli": 200,  "p_ref_mu": 1000, "shelf_life": None},
}

# ---- 配方：产出 -> 上游投入（good_id, qty_milli）；labor_ticks=1（每回合一次劳动 tick）----
#    数量一律**定点 milli-单位**（1000 == 1 单位），使分数 base_rate（如 tool=0.3）仍为整数可算。
RECIPES: dict[str, dict] = {
    "food":     {"inputs": [],                  "labor_ticks": 1},   # 耕作（无需外购投入）
    "material": {"inputs": [],                  "labor_ticks": 1},   # 采集
    "tool":     {"inputs": [("material", 2000)], "labor_ticks": 1},  # tool ← 2 单位 material
    "service":  {"inputs": [],                  "labor_ticks": 1},   # service ← 无
    "art":      {"inputs": [("material", 1000)], "labor_ticks": 1},
}

DEFAULTS = {
    "jitter_bp": 500,        # 资源丰度每回合 ±5%
    "res_min_milli": 200,    # 资源因子下界 0.2
    "res_max_milli": 1000,   # 资源因子上界 1.0
    "tool_bonus_bp": 2000,   # 每件工具 +0.2
    "tool_bonus_max_milli": 1600,  # 上限 +0.6
    "skill_per_level_milli": 100,  # 每级 +0.1 → +100 milli
    "skill_max": 20,
    "depreciate_bp": 200,    # 折旧 2%/回合
    "need_food_milli": 1000,  # 生存消费 1 单位/回合（milli）
    "cap_milli": 100000,     # 库存上限（milli；=100 单位）
    "mu_floor": 0,           # 货币总量地板
}


# ------------------------------------------------------------------ 因子
def skill_factor_milli(skill_level: int, skill_max: int = 20) -> int:
    """(1 + 0.1·lv) → milli；lv 限幅 [0, skill_max]。"""
    lv = max(0, min(int(skill_max), int(skill_level)))
    return MILLI + int(DEFAULTS["skill_per_level_milli"]) * lv


def tool_bonus_milli(tool_count: int, params: dict | None = None) -> int:
    """(1 + 0.2·件数) → milli，上限 +0.6。"""
    p = {**DEFAULTS, **(params or {})}
    n = max(0, int(tool_count))
    per_tool_milli = int(p["tool_bonus_bp"]) // 10   # 0.2/件 = 2000bp → 200 milli
    v = MILLI + per_tool_milli * n
    return min(int(p["tool_bonus_max_milli"]), max(MILLI, v))


def resource_factor_milli(seed: int, round_no: int, place_id: str, base_milli: int,
                          params: dict | None = None) -> int:
    """场所资源丰度：base ± jitter，确定性（`draw_u64(seed,"resource",round,place)`）。"""
    p = {**DEFAULTS, **(params or {})}
    base = max(int(p["res_min_milli"]), min(int(p["res_max_milli"]), int(base_milli)))
    j = int(p["jitter_bp"])
    # 在 [-j, +j] 上取一个确定性整数偏移
    span = 2 * j + 1
    v = draw_u64(int(seed), "resource", int(round_no), _place_seq(place_id), 1)[0] % span
    off = v - j
    val = base + base * off // 10000
    return max(int(p["res_min_milli"]), min(int(p["res_max_milli"]), val))


def _place_seq(place_id: str) -> int:
    """把 place_id 映射为确定性 seq（FNV-1a，整数）。"""
    h = 2166136261
    for ch in str(place_id):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h & 0xFFFF


# ------------------------------------------------------------------ 生产函数
def produce_qty(good_id: str, skill_level: int, resource_milli: int,
                tool_count: int, params: dict | None = None) -> int:
    """`floor(base_rate × (1+0.1lv) × resource × (1+tool_bonus))`，**定点 milli-单位**（整数）。

    分子 base_milli × skill × res × tool 的量纲为 10^?；除以 `MILLI**3` 得 milli-单位。
    例：food（base 2.0）lv0 res=1.0 无工具 → 2000 milli = 2 单位。
    """
    g = GOODS[good_id]
    p = {**DEFAULTS, **(params or {})}
    num = int(g["base_milli"]) * skill_factor_milli(skill_level) \
        * int(resource_milli) * tool_bonus_milli(tool_count, p)
    return num // (MILLI ** 3)


# ------------------------------------------------------------------ 库存
def inv_get(inv: dict, owner_id: str, good_id: str) -> int:
    """库存表结构 = `{owner_id: {good_id: qty}}`（与 kernel `state.inventory` 折叠一致）。"""
    return int((inv.get(owner_id) or {}).get(good_id, 0))


def inv_add(inv: dict, owner_id: str, good_id: str, qty: int,
            cap_milli: int = DEFAULTS["cap_milli"]) -> dict:
    """入库（带上限）：返回 {added, dropped, qty_after}。不改世界、只改传入字典。"""
    qty = int(qty)
    if qty <= 0:
        return {"added": 0, "dropped": 0, "qty_after": inv_get(inv, owner_id, good_id)}
    d = inv.setdefault(owner_id, {})
    before = int(d.get(good_id, 0))
    cap = int(cap_milli)
    after = min(cap, before + qty)
    d[good_id] = after
    added = after - before
    return {"added": added, "dropped": qty - added, "qty_after": after}


def inv_remove(inv: dict, owner_id: str, good_id: str, qty: int) -> dict:
    """出库（不足则拒绝，原子）：返回 {ok, removed, qty_after}。"""
    qty = int(qty)
    before = inv_get(inv, owner_id, good_id)
    if qty < 0 or before < qty:
        return {"ok": False, "removed": 0, "qty_after": before}
    inv.setdefault(owner_id, {})[good_id] = before - qty
    return {"ok": True, "removed": qty, "qty_after": before - qty}


def can_produce(inv: dict, owner_id: str, good_id: str) -> bool:
    """上游投入是否齐备（原子前置）。"""
    for gid, need in RECIPES[good_id]["inputs"]:
        if inv_get(inv, owner_id, gid) < int(need):
            return False
    return True


# ------------------------------------------------------------------ 折旧 / 消耗
def depreciate(qty: int, delta_bp: int = DEFAULTS["depreciate_bp"]) -> dict:
    """折旧：`loss = floor(qty·δ)`，floor 0。返回 {qty_after, loss}。"""
    q = max(0, int(qty))
    loss = q * int(delta_bp) // 10000
    loss = min(loss, q)
    return {"qty_after": q - loss, "loss": loss}


# ------------------------------------------------------------------ 保底：M(t)≥0
def burn_floor(money_total_mu: int, desired_burn_mu: int,
               mu_floor: int = DEFAULTS["mu_floor"]) -> int:
    """销毁地板（单笔）：**只销毁可得部分**，保证 `M(t) ≥ mu_floor`。

    返回本回合**实际**销毁额（≤ desired，且使 `M - burn ≥ mu_floor`）。
    注意：`M(t)≥0` 是**世界级**不变量；个体账户现金**允许变负**（v1/02 §0）。
    多笔销毁请用 `world_burns` 按全序分配同一世界预算，勿逐账户钳制。
    """
    m = int(money_total_mu)
    d = max(0, int(desired_burn_mu))
    floor = int(mu_floor)
    available = max(0, m - floor)
    return min(d, available)


def burn_budget(money_total_mu: int, mu_floor: int = DEFAULTS["mu_floor"]) -> int:
    """本回合可销毁的世界预算 `max(0, M − μ_floor)`。"""
    return max(0, int(money_total_mu) - int(mu_floor))


def world_burns(money_total_mu: int, desired_list, mu_floor: int = DEFAULTS["mu_floor"]):
    """世界级销毁分配：按 `desired_list` 的**给定全序**依次扣减同一世界预算。

    返回与输入等长的「实际销毁额」列表：`Σ 实扣 ≤ max(0, M − μ_floor)`；
    预算耗尽后其余置 0（个体 cash 仍可由调用方允许变负，仅世界总量受约束）。
    """
    budget = burn_budget(money_total_mu, mu_floor)
    out = []
    for d in desired_list:
        take = min(max(0, int(d)), budget)
        out.append(take)
        budget -= take
    return out


def fallback_mint(money_total_mu: int, m_target_mu: int, issue_max_mu: int,
                  trigger_bp: int = 9000) -> int:
    """兜底铸币（最后一手段）：仅当 `M < trigger_bp%·M_target` 时补至锚，且 ≤ issue_max。"""
    m = int(money_total_mu)
    target = int(m_target_mu)
    if target <= 0:
        return 0
    if m * 10000 >= int(trigger_bp) * target:
        return 0
    need = target - m
    return max(0, min(int(issue_max_mu), need))


def market_ref_band(p_ref_mu: int, band_bp: int = 1000) -> tuple[int, int]:
    """最小市场参考价带宽（不强制成交价）：[p_ref·(1−band), p_ref·(1+band)]。"""
    p = int(p_ref_mu)
    lo = p - p * int(band_bp) // 10000
    hi = p + p * int(band_bp) // 10000
    return max(0, lo), hi


__all__ = [
    "GOODS", "RECIPES", "DEFAULTS", "MILLI",
    "skill_factor_milli", "tool_bonus_milli", "resource_factor_milli",
    "produce_qty", "inv_get", "inv_add", "inv_remove", "can_produce",
    "depreciate", "burn_floor", "burn_budget", "world_burns",
    "fallback_mint", "market_ref_band",
]
