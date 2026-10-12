"""actor 类型守卫（单一真源）。

`actor` 字段在多数消费方意味着「Agent id」，但自 v2 起可为**非 Agent 一等 actor**
（`SYSTEM`/`OBSERVER`/`DIRECTOR`，以及世界侧哨兵 `MARKET`/`BANK`/`WORLD`/`TAX_POOL`）。
各处**不得把非 Agent actor 当作某个 Agent**（计入 agent 指标 / 渲染为角色）。

口径唯一：**各消费方一律引用本模块**，勿各自复制白名单（同名不同义的风险）。
"""

from __future__ import annotations

#: 非 Agent actor（世界/系统/观测/导演/哨兵账户）—— 可比较大小写敏感
NON_AGENT_ACTORS = frozenset({
    "SYSTEM", "OBSERVER", "DIRECTOR",      # v1/v2 一等系统 actor
    "WORLD", "MARKET", "BANK", "TAX_POOL",  # 世界侧哨兵实体（非 Agent）
})


def is_agent_actor(actor) -> bool:
    """`actor` 是否代表一个真实 Agent id（非空且非 NON_AGENT_ACTORS）。"""
    return isinstance(actor, str) and actor != "" and actor not in NON_AGENT_ACTORS


def agent_or_none(actor):
    """把 actor 归一为 Agent id；非 Agent actor → ``None``。"""
    return actor if is_agent_actor(actor) else None
