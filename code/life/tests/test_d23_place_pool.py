"""D2.3 单测：**候选池口径「同地点优先」**（`life/place_pool.py`）——不依赖 LLM。

钉住的事实（对应任务卡"确定性校验"要求与 `v2/refs/D23-prereg-place-affinity.md` §2）：

1. **同地点候选存在 ⇒ 必选中同地点**（跨 200 个种子穷举，不容一次例外）；
2. **同地点候选不存在 ⇒ 退化原池**，且与"累积等权轴在原池上抽"逐项相同（不得静默改变映射）；
3. **`place` 为空** ⇒ 不切分（保守退化）；
4. **`peer_places` 缺失该 peer** ⇒ 视为不同地点（不猜）；
5. **确定性**：同 seed 同结果；
6. **切分保序**：`split_pool_by_place` 两段都保持输入顺序（否则映射会漂）。
"""
from __future__ import annotations

from life.place_pool import pick_same_place_first, split_pool_by_place
from life.planner import _weighted_pick

POOL = ["P%03d" % i for i in range(1, 9)]          # P001..P008
PLACE = "cafe"
# 同地点的只有 P002 / P005 / P007
PEER_PLACES = {"P001": "park", "P002": PLACE, "P003": "market", "P004": "school",
               "P005": PLACE, "P006": "residence", "P007": PLACE, "P008": "plaza"}
SAME = ["P002", "P005", "P007"]


def test_same_place_pool_is_split_in_order():
    same, others = split_pool_by_place(POOL, PLACE, PEER_PLACES)
    assert same == SAME                                  # 保序
    assert others == ["P001", "P003", "P004", "P006", "P008"]


def test_same_place_always_wins_when_present():
    """**核心判据**：同地点候选存在时，任何种子都必须落在同地点候选上。"""
    hits = [pick_same_place_first(f"seed-{i}", POOL, PLACE, PEER_PLACES) for i in range(200)]
    assert set(hits) <= set(SAME), f"越界选中非同地点：{sorted(set(hits) - set(SAME))}"
    assert hits == [pick_same_place_first(f"seed-{i}", POOL, PLACE, PEER_PLACES)
                    for i in range(200)]                 # 确定性


def test_never_picks_missing_peer_when_same_place_present():
    """缺失 `peer_places` 的 peer（P008）不得被当成同地点。"""
    hits = {pick_same_place_first(f"s{i}", POOL, PLACE, PEER_PLACES) for i in range(300)}
    assert "P008" not in hits


def test_fallback_equals_axis_pick_over_full_pool():
    """无同地点候选 ⇒ 精确退化到"原池 + 同映射"，不得改变映射。"""
    peer_places = {p: "park" for p in POOL}               # 无人在 cafe
    for i in range(100):
        seed = f"fb-{i}"
        assert (pick_same_place_first(seed, POOL, PLACE, peer_places)
                == _weighted_pick(seed, POOL, [1.0] * len(POOL)))


def test_empty_place_does_not_split():
    same, others = split_pool_by_place(POOL, None, PEER_PLACES)
    assert same == [] and others == list(POOL)
    assert (pick_same_place_first("x", POOL, "", PEER_PLACES)
            == _weighted_pick("x", POOL, [1.0] * len(POOL)))


def test_empty_pool_returns_none():
    assert pick_same_place_first("x", [], PLACE, PEER_PLACES) is None
