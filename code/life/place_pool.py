"""D2.3 候选池口径：**同地点优先选对端**（place-pool partner choice）——纯函数、**未接线**。

⚠ **本模块目前是 inert（登记 ≠ 生效）**，登记于 `tools/inert_registry.json`
（`name=place_pool_same_place_first`, `expected_status=missing_wiring`）。原因见 §为什么未接线。

## 为什么需要它

`planner._participants()` 现在从**该居民的全部 peers** 里抽对端，`place` 完全不参与，
而 `place` 是在抽完对端之后才由 `_pick(f"{agent}|{slot_id}|place", places)` 决定的
（`plan_slot` 里）。离线实测：现状 **70.18% 的发起是"跨地点约人"**
（`v2/evidence/d23_place_offline_verdict.md` §2）。

把候选池收窄到"同地点的人"，离线净效应 `mechanism_pp = B − C = +2.63pp`（同上 §1）。

## 口径（与离线工具逐字对齐，不自造）

- 同地点候选 = `[p for p in pool if peer_places.get(p) == place]`；
- 同地点候选**存在** ⇒ **只在同地点候选里抽**（这就是"必须优先选中同地点"）；
  不存在 ⇒ 退化为原池；
- 抽样映射 = **累积等权轴** `_weighted_pick(seed, opts, w≡1)`，
  与 `tools/d21/d22_place_feasibility.py::axis_pick` 同一映射（离线 B 臂即此口径）。

## 为什么**未接线**（不许假装它有活）

`Planner` 在计划期只拿得到**自己的** `peers` 与 `places`，**拿不到同 slot 下别人会待在哪儿**：

- `plan_slot` 的 `place` 对同一模板是"`sorted(open_places)` + 独立种子"，但 `tid` 先要过
  `_self_cash_ok()`（读**本居民私有**现金）与 `focus`（**LLM 判定标签**，每居民不同）；
- ⇒ 想在内核里算出"别人在哪"，必须读别人的私有状态 ⇒ 单变量论证不成立。

⇒ 接线的**正确前提是改"何时算"**：先全城定 `place`（两阶段计划），再把 `peer_places` 传给本模块。
这正是 `v2/evidence/d23_mock_verdict.md` §4 给出的结论（"真正该改的不是权重，而是何时算"）。
**在两阶段计划落地前，生产侧没有任何 `peer_places` 来源，故不接线**；
本模块 + 单测只把**口径**钉死，等接线时不至于再吵一次定义。
"""
from __future__ import annotations

from .planner import _weighted_pick


def split_pool_by_place(pool, place, peer_places) -> tuple[list, list]:
    """把候选池切成 (同地点, 其它)，各自**保持输入顺序**。

    `peer_places: {peer: place}` —— 缺失的 peer 视为"不同地点"（保守：不靠猜）。
    `place` 为 None/空 ⇒ 不切分（全部归"其它"），等价于原池。
    """
    pool = list(pool or [])
    if not place:
        return [], pool
    same, others = [], []
    for p in pool:
        (same if (peer_places or {}).get(p) == place else others).append(p)
    return same, others


def pick_same_place_first(seed: str, pool, place, peer_places):
    """同地点优先抽一个对端：同地点候选存在 ⇒ 只在那里面抽；否则在**原池**里抽。

    映射 = 累积等权轴（`w≡1`），与离线工具 `axis_pick` 同映射。
    """
    same, others = split_pool_by_place(pool, place, peer_places)
    opts = same or others
    if not opts:
        return None
    return _weighted_pick(seed, opts, [1.0] * len(opts))
