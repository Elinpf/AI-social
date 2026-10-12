"""T224 人格抗漂移（persona_drift）单元测试 —— 指纹 / 有界更新 / 漂移度量。

判据降规模验证：稀疏漂移事件（每周 ≤ k 次）下，`within_bounds` 恒成立；
「1000 回合」的长期判据标 `【未验证】`（见 v2/evidence/T224-...md）。
"""
from __future__ import annotations

from life import persona_drift as PD


def _anchor(**over) -> dict:
    b5 = {d: 50 for d in PD.BIG5_DIMS}
    b5.update(over)
    return {"persona_id": "P003", "personality_big5": b5,
            "values": {"security": 65, "benevolence": 70}, "skills": [{"skill_id": "farming", "level": 3}]}


def _params() -> dict:
    return dict(PD.DEFAULTS)


def test_fingerprint_stable_and_anchored():
    a = _anchor()
    assert PD.persona_fingerprint(a) == PD.persona_fingerprint(_anchor())
    a2 = _anchor(openness=51)
    assert PD.persona_fingerprint(a2) != PD.persona_fingerprint(a)


def test_init_state_equals_anchor():
    a = _anchor(extraversion=40)
    st = PD.init_state(a)
    assert st == {d: a["personality_big5"][d] for d in PD.BIG5_DIMS}


def test_bounded_update_clamps_delta():
    p = _params()
    a = _anchor()
    st = PD.init_state(a)
    # 单步 delta=+10 被 clamp 到 +1；且不能越过 100
    nxt = PD.bounded_update(st, a, "openness", 10, p)
    assert st["openness"] < nxt <= min(100, st["openness"] + 1)


def test_mean_reversion_pulls_back_toward_anchor():
    p = _params()
    a = _anchor()
    st = PD.init_state(a)
    st["openness"] = 90                     # 人为推高
    for _ in range(200):                    # 无事件、纯回归
        st["openness"] = PD.bounded_update(st, a, "openness", 0, p)
    assert abs(st["openness"] - 50) < 5, st["openness"]


def test_drift_metric_zero_when_equal():
    a = _anchor()
    st = PD.init_state(a)
    assert PD.drift_permille(st, st) == 0
    assert all(v == 0 for v in PD.drift_dims_permille(st, a).values())


def test_sparse_drift_stays_within_bounds():
    """稀疏事件（每 12 回合一次 +1）下漂移有界（模拟"每周 ≤k 次"）。"""
    p = _params()
    a = _anchor()
    st = PD.init_state(a)
    p0 = dict(st)
    events = [{"dim": "openness", "delta": 1}, {"dim": "extraversion", "delta": 1}]
    for step in range(1, 601):
        if step % 12 == 0:
            st = PD.apply_drift_events(st, a, events, p)
        else:
            st = PD.apply_drift_events(st, a, [], p)   # 纯回归
    assert PD.within_bounds(st, p0, a, p), (
        PD.drift_permille(st, p0), PD.drift_dims_permille(st, a))


def test_fingerprint_changes_after_drift():
    a = _anchor()
    st = PD.init_state(a)
    f0 = PD.dynamic_fingerprint("P003", st)
    st2 = PD.apply_drift_events(st, a, [{"dim": "openness", "delta": 1}], _params())
    assert PD.dynamic_fingerprint("P003", st2) != f0
