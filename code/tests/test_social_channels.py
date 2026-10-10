"""T97：INTENT.SOCIAL 三通道（DM/PUBLIC/GROUP）+ 配额/去重 + ADR-08。"""

from engine.constants import PHASE_COMMUNICATE
from engine.events import spec
from engine.state import state_hash
from engine.replay import replay_records
from life.ports import Intent
from orchestration.integration import build_world


def _open_round(eng, r):
    eng.state.round = r
    eng.ctx = eng.ctx.at(r, 0)
    eng.arbiter.discard()


def _world(seed=7, n=3):
    return build_world(seed=seed, n=n)


def _commit(eng):
    eng.state, _ = eng.arbiter.commit(eng.state)


def test_dm_private_visible_only_to_parties():
    w = _world(); eng = w["engine"]; ad = w["adapter"]
    pids = sorted(w["personas"]); a, b, c = pids[0], pids[1], pids[2]
    _open_round(eng, 1)
    res = ad.submit_intent(a, Intent("INTENT.SOCIAL", a, {
        "scope": "private", "to": b, "body": "hi", "refs": [], "tag_hints": []}))
    assert res.ok
    assert not any(x["type"] == "MSG_DM" for x in eng.ledger.records)  # ADR-08：缓冲未落盘
    _commit(eng)
    assert any(x["type"] == "MSG_DM" for x in eng.ledger.records)
    assert any(ev.type == "MSG_DM" for ev in ad.perceive(b).visible_events)
    assert not any(ev.type == "MSG_DM" for ev in ad.perceive(c).visible_events)


def test_public_global_visible_to_all_alive():
    w = _world(); eng = w["engine"]; ad = w["adapter"]
    pids = sorted(w["personas"]); a, c = pids[0], pids[2]
    _open_round(eng, 1)
    assert ad.submit_intent(a, Intent("INTENT.SOCIAL", a, {
        "scope": "global", "body": "公告", "refs": [], "tag_hints": []})).ok
    _commit(eng)
    for aid in (pids[0], pids[1], pids[2]):
        assert any(ev.type == "MSG_PUBLIC" for ev in ad.perceive(aid).visible_events)


def test_group_members_visibility():
    w = _world(); eng = w["engine"]; ad = w["adapter"]
    pids = sorted(w["personas"]); a, b, c = pids[0], pids[1], pids[2]
    _open_round(eng, 1)
    eng.emit_specs([spec(1, PHASE_COMMUNICATE, "SYSTEM", "GROUP_CREATED",
                         {"group_id": "g1", "members": [a, b], "created_round": 1})])
    _commit(eng)
    assert eng.state.groups["g1"]["members"] == sorted([a, b])
    _open_round(eng, 2)
    assert ad.submit_intent(a, Intent("INTENT.SOCIAL", a, {
        "scope": "place_group", "group_id": "g1", "body": "群聊", "refs": [], "tag_hints": []})).ok
    # 非成员发群聊 -> not_group_member
    r2 = ad.submit_intent(c, Intent("INTENT.SOCIAL", c, {
        "scope": "place_group", "group_id": "g1", "body": "x", "refs": [], "tag_hints": []}))
    assert r2.ok is False and r2.reason == "not_group_member"
    _commit(eng)
    assert any(ev.type == "MSG_GROUP" for ev in ad.perceive(b).visible_events)
    assert not any(ev.type == "MSG_GROUP" for ev in ad.perceive(c).visible_events)


def test_dm_quota_agent_rejects_4th():
    w = _world(); eng = w["engine"]; ad = w["adapter"]
    pids = sorted(w["personas"]); a, b = pids[0], pids[1]
    _open_round(eng, 1)
    ok = [ad.submit_intent(a, Intent("INTENT.SOCIAL", a, {
        "scope": "private", "to": b, "body": f"m{i}", "refs": [], "tag_hints": []})).ok
        for i in range(4)]
    assert ok == [True, True, True, False]
    _commit(eng)
    assert sum(1 for x in eng.ledger.records if x["type"] == "MSG_DM") == 3
    assert any(x["type"] == "INTENT_REJECTED" and x["payload"].get("reason") == "quota_agent"
               for x in eng.ledger.records)


def test_dedup_same_author_body_same_slot():
    w = _world(); eng = w["engine"]; ad = w["adapter"]
    pids = sorted(w["personas"]); a, b = pids[0], pids[1]
    _open_round(eng, 1)
    assert ad.submit_intent(a, Intent("INTENT.SOCIAL", a, {
        "scope": "private", "to": b, "body": "same", "refs": [], "tag_hints": []})).ok
    r = ad.submit_intent(a, Intent("INTENT.SOCIAL", a, {
        "scope": "private", "to": b, "body": "same", "refs": [], "tag_hints": []}))
    assert r.ok is False and r.reason == "dup"
    _commit(eng)
    assert sum(1 for x in eng.ledger.records if x["type"] == "MSG_DM") == 1
    assert any(x["type"] == "DROPPED" and x["payload"].get("reason") == "dup"
               for x in eng.ledger.records)


def test_channel_alias_and_replay_parity():
    w = _world(); eng = w["engine"]; ad = w["adapter"]
    pids = sorted(w["personas"]); a, b = pids[0], pids[1]
    for r in range(6):
        eng.run_round(r)
    _open_round(eng, 6)
    assert ad.submit_intent(a, Intent("INTENT.SOCIAL", a, {
        "channel": "dm", "to": b, "body": "alias", "refs": [], "tag_hints": []})).ok
    _commit(eng)
    assert any(x["type"] == "MSG_DM" for x in eng.ledger.records)
    assert state_hash(replay_records(eng.ledger.records)) == state_hash(eng.state)


def test_unknown_scope_rejected():
    w = _world(); eng = w["engine"]; ad = w["adapter"]
    a = sorted(w["personas"])[0]
    _open_round(eng, 1)
    r = ad.submit_intent(a, Intent("INTENT.SOCIAL", a, {
        "scope": "bogus", "body": "x", "refs": [], "tag_hints": []}))
    assert r.ok is False and r.reason == "unknown_channel"
