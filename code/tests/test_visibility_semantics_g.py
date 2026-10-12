"""G1/G3：可见性语义（08 §8–§10）。"""

from contracts.visibility import visible


def test_g1_place_local_actor_fallback():
    """G1：place 未知/不等时，actor 本人对自己 place_local 事件可见（开关开）。"""
    p = {"agent_id": "A", "from_place": "x", "to_place": "y"}  # 无 place
    assert visible("place_local", "A", "A", p, "residence", {}) is False       # 默认 off
    assert visible("place_local", "A", "A", p, "residence", {}, True) is True  # 开
    assert visible("place_local", "B", "A", p, "residence", {}, True) is False


def test_g3_subject_only_from_removed():
    """G3：subject_only 不再因 payload.from 而可见（等价；from 属 private）。"""
    assert visible("subject_only", "A", "SYSTEM", {"from": "A"}, "residence", {}) is False
    assert visible("subject_only", "A", "SYSTEM", {"agent_id": "A"}, "residence", {}) is True
    assert visible("subject_only", "A", "A", {}, "residence", {}) is True
