"""T354 期②a：`current_activity` 纯派生 + `time.ongoing.enabled`（默认开）。"""

import os

os.environ.setdefault("N50_VEC", "0")

from orchestration.integration import build_world  # noqa: E402
from engine.perceive import current_activity  # noqa: E402
from engine import version  # noqa: E402


def _run(n=6, rounds=24, seed=42):
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return w, eng


def test_time_flags_default_ongoing_true():
    f = version.load_time_flags()
    assert f["ongoing_enabled"] is True      # 默认开（用户拍板功能不得默认关）


def test_current_activity_derived_from_log():
    """开：`current_activity` 可由日志重建（STARTED 无 COMPLETED），至少出现一次。"""
    w, eng = _run(rounds=30)
    recs = eng.ledger.records
    seen = False
    for aid in sorted(eng.state.agents):
        for r in range(eng.state.round + 1):
            if current_activity(recs, aid, r) is not None:
                seen = True
                break
        if seen:
            break
    assert seen, "应有某 agent 在某回合处于'进行中'"
    # WorldView 暴露（adapter 路径）
    wv = w["adapter"].perceive(sorted(eng.state.agents)[0])
    assert hasattr(wv, "current_activity")


def test_off_means_none():
    """关：`time.ongoing.enabled=False` ⇒ WorldView.current_activity 恒 None。"""
    w = build_world(seed=42, n=4)
    ad = w["adapter"]
    ad._ongoing = False
    eng = w["engine"]
    for r in range(6):
        eng.run_round(r)
    for aid in sorted(eng.state.agents):
        assert ad.perceive(aid).current_activity is None


def test_purity_no_new_forward_state():
    """纯派生：不新增 state 字段（`current_activity` 只由 ledger 记录推导）。"""
    w, eng = _run(rounds=6)
    # 无 'current_activity' 类 state 字段
    assert "current_activity" not in eng.state.to_dict()
