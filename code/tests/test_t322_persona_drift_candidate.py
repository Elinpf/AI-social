"""T322：登记 `PERSONA_DRIFT_CANDIDATE`（EVENT_TYPES + identity fold）与 orchestration 落点。"""

import os

os.environ.setdefault("N50_VEC", "0")

from orchestration.integration import build_world  # noqa: E402

from engine.events import EVENT_TYPES, spec  # noqa: E402
from engine.kernel import Engine  # noqa: E402
from engine.replay import replay_records  # noqa: E402
from engine.runner import default_config  # noqa: E402
from engine.state import state_hash  # noqa: E402


def _eng():
    eng = Engine(seed=1, config=default_config())
    eng.genesis()
    for r in range(3):
        eng.run_round(r)
    return eng


def test_registered_in_event_types():
    assert "PERSONA_DRIFT_CANDIDATE" in EVENT_TYPES


def test_identity_fold_no_state_hash_change_and_replays():
    eng = _eng()
    payload = {"agent_id": "A", "dim": "warmth", "sign": 1, "window": 5,
               "mem_id": "M-1", "reached_threshold": True, "day": 0, "slot": "morning"}
    rec = eng.ledger.append_spec(spec(2, 35, "A", "PERSONA_DRIFT_CANDIDATE", payload))
    h1 = state_hash(eng.state)
    from engine.replay import apply_event
    apply_event(eng.state, rec)          # 就地折叠
    assert state_hash(eng.state) == h1   # identity fold：不改 state_hash
    assert rec["type"] == "PERSONA_DRIFT_CANDIDATE"
    # 重放不报错（已登记 no-op 折叠）
    replay_records(eng.ledger.records)


def test_adapter_op_drift_candidate_lands():
    w = build_world(seed=1, n=2)
    ad = w["adapter"]
    res = ad._do_memory("A", {"op": "drift_candidate", "dim": "warmth", "sign": -1,
                              "window": 5, "mem_id": "M-1", "reached_threshold": False,
                              "day": 0, "slot": "morning"})
    assert res is not None and res.ok
    # 非法 sign ⇒ 拒绝（None）
    assert ad._do_memory("A", {"op": "drift_candidate", "dim": "warmth", "sign": 0}) is None
    assert ad._do_memory("A", {"op": "drift_candidate", "sign": 1}) is None
