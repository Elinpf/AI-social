"""T91 预备：A 物理层纯内核（engine/production.py）单元测试。

覆盖：生产函数定点正确性、资源丰度确定性、库存上限/溢出与原子出库、折旧、
`M(t)≥0` 销毁地板、兜底铸币、保底参考价带宽。全部整数、确定性。
"""

from __future__ import annotations

from engine import production as P


def test_produce_qty_fixed_point_milli():
    # 定点 milli-单位：food base 2.0, lv0, res=1.0, 无工具 → 2000 milli (=2 单位)
    assert P.produce_qty("food", 0, 1000, 0) == 2000
    # lv=10 → 技能因子 2.0 → 4000
    assert P.produce_qty("food", 10, 1000, 0) == 4000
    # 工具 1（+0.2）→ 2400
    assert P.produce_qty("food", 0, 1000, 1) == 2400
    # 工具 3（封顶 +0.6）→ 3200
    assert P.produce_qty("food", 0, 1000, 3) == 3200
    assert P.produce_qty("food", 0, 1000, 99) == 3200     # 封顶
    # 低资源 0.2 → 400 milli
    assert P.produce_qty("food", 0, 200, 0) == 400
    # 工具类 base 0.3 → 300 milli
    assert P.produce_qty("tool", 0, 1000, 0) == 300


def test_skill_and_tool_factors_clamped():
    assert P.skill_factor_milli(0) == 1000
    assert P.skill_factor_milli(10) == 2000
    assert P.skill_factor_milli(20) == 3000
    assert P.skill_factor_milli(99) == 3000            # 限幅
    assert P.tool_bonus_milli(0) == 1000
    assert P.tool_bonus_milli(1) == 1200
    assert P.tool_bonus_milli(3) == 1600
    assert P.tool_bonus_milli(9) == 1600               # 封顶


def test_resource_factor_deterministic_and_bounded():
    a = P.resource_factor_milli(42, 7, "farmland", 800)
    b = P.resource_factor_milli(42, 7, "farmland", 800)
    assert a == b                                       # 同参恒等（可重放）
    for r in range(20):
        v = P.resource_factor_milli(42, r, "farmland", 800)
        assert 200 <= v <= 1000


def test_inventory_add_overflow_and_remove_atomic():
    inv = {}
    r = P.inv_add(inv, "A", "food", 3000, cap_milli=5000)
    assert r == {"added": 3000, "dropped": 0, "qty_after": 3000}
    r = P.inv_add(inv, "A", "food", 3000, cap_milli=5000)
    assert r == {"added": 2000, "dropped": 1000, "qty_after": 5000}   # 溢出丢弃
    # 原子出库：不足则不变
    bad = P.inv_remove(inv, "A", "food", 6000)
    assert bad["ok"] is False and P.inv_get(inv, "A", "food") == 5000
    ok = P.inv_remove(inv, "A", "food", 4000)
    assert ok["ok"] is True and P.inv_get(inv, "A", "food") == 1000


def test_recipe_gate_atomic():
    inv = {}
    assert P.can_produce(inv, "A", "service") is True    # 无投入
    assert P.can_produce(inv, "A", "food") is True        # food 无外购投入
    assert P.can_produce(inv, "A", "tool") is False       # 缺 material
    P.inv_add(inv, "A", "material", 2000)
    assert P.can_produce(inv, "A", "tool") is True


def test_depreciate_floor_zero():
    assert P.depreciate(100, 200) == {"qty_after": 98, "loss": 2}
    assert P.depreciate(1, 200) == {"qty_after": 1, "loss": 0}   # floor 0
    assert P.depreciate(0) == {"qty_after": 0, "loss": 0}


def test_burn_floor_never_negative():
    # 只销毁可得部分，保证 M>=floor
    assert P.burn_floor(10, 100) == 10
    assert P.burn_floor(10, 5) == 5
    assert P.burn_floor(-5, 5) == 0
    assert P.burn_floor(0, 5) == 0
    assert P.burn_floor(100, 30, mu_floor=90) == 10     # 保留地板 90
    # 模拟连续 10 回合销毁，M 始终 >=0
    m = 25
    for _ in range(10):
        m -= P.burn_floor(m, 10)
        assert m >= 0


def test_fallback_mint_capped_and_triggered():
    # M=1000 < 0.9×2000 → 补足差距，但 ≤ issue_max
    assert P.fallback_mint(1000, 2000, 500) == 500
    assert P.fallback_mint(1900, 2000, 500) == 0        # 未低于 0.9 锚
    assert P.fallback_mint(0, 2000, 10000) == 2000
    assert P.fallback_mint(1000, 0, 500) == 0           # 无锚


def test_market_ref_band():
    assert P.market_ref_band(100, 1000) == (90, 110)
    assert P.market_ref_band(100, 0) == (100, 100)


def test_world_burns_shared_budget():
    # 世界预算 = max(0, M - floor)；按全序分配，超额置 0（个体可负，仅世界总量受约束）
    assert P.burn_budget(1000, 0) == 1000
    assert P.world_burns(1000, [400, 400, 400]) == [400, 400, 200]
    assert P.world_burns(1000, [1500, 500]) == [1000, 0]
    assert P.world_burns(-5, [10, 10]) == [0, 0]
    assert P.world_burns(100, [10, 10], mu_floor=100) == [0, 0]   # 留地板
    # 单笔 burn_floor 与世界预算一致
    assert P.burn_floor(1000, 1500) == 1000

