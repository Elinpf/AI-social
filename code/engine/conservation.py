"""守恒校验（§5.9 / 08 §6 + v2 物理层 goods 守恒）。

货币守恒：
  式(1) `M(t) == money_minted_total − money_burned_total`，`M(t) = money_supply(state)`
  式(2) **`M(t) ≥ μ_floor`**（v2 世界级预算不变量；`μ_floor` 默认 0，读 `config.policy.money_floor_mu`）
        —— `M` 为**有符号**（Σcash+Σdeposits+税池+银行库存，含负余额欠账）。
商品式守恒（v2 物理层，T90）：
  式(3) `Σ PRODUCE.qty == Σ CONSUME.qty + Σ 库存 + Σ PRODUCE_OVERFLOW.qty_dropped + Σ DEPRECIATE.delta_mu`

违规返回结构化列表，由内核落 `ECONOMY_INVARIANT_VIOLATION`（→ 整回合回滚）。
"""

from __future__ import annotations

from .state import WorldState, money_total

CODE_VIOLATION = "ECONOMY_INVARIANT_VIOLATION"


def money_supply(state: WorldState, config: dict | None = None) -> int:
    """在流通货币总量 M(t)（有符号）。口径：Σcash + Σdeposits + 税池 + 银行库存。"""
    return money_total(state)


def net_financial_position(state: WorldState, config: dict | None = None) -> int:
    """净金融头寸（= 有符号 M；含负余额欠账），供报告参考。"""
    return money_total(state)


def money_floor(config: dict | None = None) -> int:
    pol = (config or {}).get("policy", {}) if isinstance(config, dict) else {}
    v = pol.get("money_floor_mu")
    if isinstance(v, dict):
        v = v.get("default")
    return int(v) if v is not None else 0


def _event_sum(state: WorldState, etype: str, key: str) -> int:
    tot = 0
    for rec in state.event_index.values():
        if rec.get("type") == etype:
            tot += int(rec.get("payload", {}).get(key, 0) or 0)
    return tot


def check_goods_conservation(state: WorldState, config: dict | None = None) -> list[dict]:
    """商品式守恒：ΣPRODUCE == ΣCONSUME + Σ库存 + Σ溢出 + Σ折旧耗损。"""
    produced = _event_sum(state, "PRODUCE", "qty")
    consumed = _event_sum(state, "CONSUME", "qty")
    dropped = _event_sum(state, "PRODUCE_OVERFLOW", "qty_dropped")
    depreciated = _event_sum(state, "DEPRECIATE", "delta_mu")
    inv_total = sum(q for goods in state.inventory.values() for q in goods.values())
    lhs = produced
    rhs = consumed + inv_total + dropped + depreciated
    if lhs != rhs:
        return [{
            "code": CODE_VIOLATION,
            "invariant": "goods_conservation",
            "detail": "ΣPRODUCE != ΣCONSUME + 库存 + 溢出 + 折旧耗损",
            "produced": produced, "consumed": consumed, "inventory": inv_total,
            "dropped": dropped, "depreciated": depreciated, "residual": lhs - rhs,
        }]
    return []


def check_conservation(state: WorldState, config: dict | None = None) -> list[dict]:
    """货币守恒（式1）+ 世界级预算下限（式2）。返回违规列表（空=通过）。"""
    violations: list[dict] = []
    supply = money_supply(state, config)
    intended = state.money_minted_total - state.money_burned_total
    if supply != intended:
        violations.append({
            "code": CODE_VIOLATION,
            "invariant": "money_conservation",
            "detail": "money_minted_total - money_burned_total != M(t)",
            "money_minted_total": state.money_minted_total,
            "money_burned_total": state.money_burned_total,
            "money_supply": supply,
            "residual": intended - supply,
        })
    floor = money_floor(config)
    if supply < floor:
        violations.append({
            "code": CODE_VIOLATION,
            "invariant": "money_floor",
            "detail": "M(t) < μ_floor（世界级预算下限被击穿）",
            "money_supply": supply, "money_floor": floor, "residual": supply - floor,
        })
    return violations


def check_all(state: WorldState, config: dict | None = None) -> list[dict]:
    """全部不变量：货币守恒 + 世界预算下限 + 商品式守恒。"""
    return check_conservation(state, config) + check_goods_conservation(state, config)


__all__ = [
    "CODE_VIOLATION", "money_supply", "net_financial_position", "money_floor",
    "check_conservation", "check_goods_conservation", "check_all",
]
