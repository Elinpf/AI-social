"""哈希链与 turn_seal 测试。"""

from engine.ledger import Ledger
from engine.runner import run


def test_chain_links_and_verifies():
    led = Ledger()
    led.append(0, 0, "SYSTEM", "WORLD_INIT", {"seed": 1})
    led.append(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": "A000", "birth_round": 0})
    ok, err = led.verify_chain()
    assert ok, err
    assert led.records[0]["prev_hash"].startswith("sha256:")
    assert led.records[1]["prev_hash"] == led.records[0]["hash"]


def test_tampering_breaks_chain():
    led = Ledger()
    led.append(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": 10, "reason": "x"})
    led.append(0, 0, "SYSTEM", "MONEY_MINTED", {"amount": 20, "reason": "y"})
    led.records[0]["payload"]["amount"] = 999  # 篡改
    ok, err = led.verify_chain()
    assert not ok and "哈希" in err


def test_turn_seal_present_each_round():
    res = run(seed=7, rounds=5)
    records = res["records"]
    seals = [r for r in records if r["type"] == "TURN_SEAL"]
    assert len(seals) == 5
    for r in range(5):
        assert any(s["round"] == r and s["payload"].get("state_hash") for s in seals)
    assert res["chain_ok"]


def test_seal_commits_state_hash_matching_fold():
    res = run(seed=7, rounds=3)
    # replay 内部会校验 TurnSeal.state_hash 与逐步重放一致（verify_seals=True）
    from engine.replay import replay_records
    state = replay_records(res["records"])  # 不抛异常即通过
    assert state.round == 2
