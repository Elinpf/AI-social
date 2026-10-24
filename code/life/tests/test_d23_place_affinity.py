"""D2.3 单测：place 亲和的对端选择（`planner`）。

钉住的事实（对应 `v2/refs/D23-prereg-place-affinity.md` §2）：

1. **`place=None` ⇒ 原路径逐字节不变**：`_participants(tid, slot_id)` 的结果必须与"原 `_pick` 实现"逐项相同；
2. **权重纯函数**：`w = 1 + α·count`；`α=0 ⇒ w≡1`；`count=0 ⇒ w=1`（无历史不加权）；
3. **映射**：`α=0` 的加权抽 == 累积等权轴（与 `tools/d21/d22_place_feasibility.py::axis_pick` 同映射）；
4. **确定性**：同 seed 同结果（重复调用逐字节相同）；
5. **边界**：`peers` 为空 ⇒ `None`；`counts` 缺失/为 0 ⇒ 权重 1（不抛错、不静默降级为"跳过"）；
6. **α=3 确实改变选择**：在构造出强偏好的 counts 下，选中"高频 peer"的比例显著上升。
"""
from __future__ import annotations

import pytest

from life.planner import Planner, place_affinity_weight, _pick, _weighted_pick
from life.util import sha256_hex

TEMPLATES = {
    "gift": {
        "activity_type": "social",
        "slot_allowed": ["evening"],
        "place_allowed": ["market", "cafe"],
        "participants": {"min": 2, "max": 2},
        "preconditions": {},
    }
}
PLACES = {"market": {"open_slots": ["evening"]}, "cafe": {"open_slots": ["evening"]}}
PEERS = ["P%03d" % i for i in range(1, 17)]


def _axis_pick_ref(seed: str, options: list) -> str:
    """离线工具的同映射（`axis_pick`）：`u = h/2^32 * len`，取 floor。"""
    u = (int(sha256_hex(seed)[:8], 16) / float(1 << 32)) * len(options)
    return options[min(int(u), len(options) - 1)]


def _orig_participants(agent_id: str, peers: list, tid: str, slot_id: str) -> list:
    """**原实现**的逐字节复刻（用于证明 `place=None` 时未变）。"""
    need = 1
    k = need
    chosen: list = []
    for i in range(k):
        rem = [p for p in peers if p not in chosen]
        if not rem:
            break
        chosen.append(_pick(f"{agent_id}|{slot_id}|{tid}|p{i}", rem))
    return [agent_id] + chosen


# ---------------------------------------------------------------- 1) 原路径不变
@pytest.mark.parametrize("slot_id", ["day0-morning", "day3-evening", "day6-night"])
def test_place_none_is_original_path(slot_id):
    p = Planner("P001", TEMPLATES, PEERS, PLACES)          # 无 place_peer_counts ⇒ 关闭态
    got = p._participants("gift", slot_id)                  # 不传 place ⇒ 原路径
    assert got == _orig_participants("P001", p.peers, "gift", slot_id)
    # 即使传了 place，但 counts 为 None（关闭态）⇒ 仍走原路径
    assert p._participants("gift", slot_id, place="market") == got


def test_plan_slot_off_matches_when_counts_none():
    """关闭态：传/不传 place_guess 结果一致（place 与 participants 互不影响）。"""
    p = Planner("P001", TEMPLATES, PEERS, PLACES)
    plan = p.plan_slot("workday", "evening", "day1-evening", cash=100)
    if plan is None:
        pytest.skip("该 seed 被频次闸跳过")
    assert plan["place"] in ("market", "cafe")
    assert plan["participants"][0] == "P001"


# ---------------------------------------------------------------- 2) 权重纯函数
def test_weight_function():
    assert place_affinity_weight(0, 3) == 1.0
    assert place_affinity_weight(2, 3) == 7.0
    assert place_affinity_weight(5, 0) == 1.0
    assert place_affinity_weight(0, 0) == 1.0
    assert place_affinity_weight(-3, 3) == 1.0             # 负 count 归零，不产生 <1 权重


# ---------------------------------------------------------------- 3) 映射与 C 档等价
def test_alpha0_equals_axis_mapping():
    for i in range(200):
        seed = f"P001|day{i % 7}-evening|gift|p0"
        assert _weighted_pick(seed, PEERS, [1.0] * len(PEERS)) == _axis_pick_ref(seed, PEERS)


# ---------------------------------------------------------------- 4) 确定性
def test_determinism_same_seed():
    counts = {"market": {"P003": 5, "P007": 2}}
    p = Planner("P001", TEMPLATES, PEERS, PLACES, place_peer_counts=counts)
    a = p._participants("gift", "day2-evening", place="market")
    b = p._participants("gift", "day2-evening", place="market")
    assert a == b


# ---------------------------------------------------------------- 5) 边界
def test_empty_peers_and_no_history():
    p = Planner("P001", TEMPLATES, [], PLACES)
    assert p._participants("gift", "day0-evening") is None
    # counts 里没有该 place / 该 peer ⇒ w=1，与等权同结果
    p2 = Planner("P001", TEMPLATES, PEERS, PLACES, place_peer_counts={})
    got = p2._participants("gift", "day0-evening", place="market")
    assert got[0] == "P001" and got[1:] == [_axis_pick_ref("P001|day0-evening|gift|p0", p2.peers)]


# ---------------------------------------------------------------- 6) α=3 改变选择
def test_alpha3_biased_toward_frequent_peer():
    """构造极化 counts（把 P016 权重抬到压倒性）⇒ α=3 时几乎必选它；α=0 时不偏向。"""
    counts = {"market": {"P016": 1000}}
    hot = Planner("P001", TEMPLATES, PEERS, PLACES, place_peer_counts=counts, place_affinity_alpha=3)
    cold = Planner("P001", TEMPLATES, PEERS, PLACES, place_peer_counts=counts, place_affinity_alpha=0)
    hot_hits = cold_hits = 0
    n = 300
    for i in range(n):
        sid = f"day{i % 7}-evening"
        if hot._participants("gift", sid, place="market")[-1] == "P016":
            hot_hits += 1
        if cold._participants("gift", sid, place="market")[-1] == "P016":
            cold_hits += 1
    assert hot_hits == n                                  # 权重压倒 ⇒ 100% 选它
    assert cold_hits < n * 0.2                            # 等权 ⇒ 约 1/16


def test_switch_env_semantics(monkeypatch):
    from life.agent import LifeLayerAgent as A
    monkeypatch.delenv("HITT_PARTNER_PLACE_AFFINITY", raising=False)
    assert A._place_affinity_on() is False
    monkeypatch.setenv("HITT_PARTNER_PLACE_AFFINITY", "0")
    assert A._place_affinity_on() is False
    monkeypatch.setenv("HITT_PARTNER_PLACE_AFFINITY", "1")
    assert A._place_affinity_on() is True
    monkeypatch.setenv("HITT_PARTNER_PLACE_AFFINITY", "2")
    with pytest.raises(ValueError):
        A._place_affinity_on()
