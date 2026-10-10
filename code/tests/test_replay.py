"""复现门禁测试（T29 验收②）：同一日志重放两次状态哈希相等。

同时校验首跑最终状态 == 重放最终状态（更强的 P2 不变量）。
"""

from engine.replay import replay_records
from engine.runner import run, write_log, read_log
from engine.state import state_hash


def test_run_20_rounds_empty_world():
    """验收①：能跑通 20 回合空世界。"""
    res = run(seed=12345, rounds=20)
    assert res["chain_ok"] is True
    assert len(res["records"]) > 0
    # 20 个回合各一条 TURN_SEAL
    assert sum(1 for r in res["records"] if r["type"] == "TURN_SEAL") == 20


def test_replay_twice_equal_state_hash():
    """验收②：同一日志重放两次状态哈希相等（门禁）。"""
    res = run(seed=12345, rounds=20)
    s1 = replay_records(res["records"])
    s2 = replay_records(res["records"])
    assert state_hash(s1) == state_hash(s2)


def test_first_run_equals_replay():
    """P2：State = reduce(apply, EventLog, InitialState) —— 首跑 == 重放。"""
    res = run(seed=12345, rounds=20)
    replayed = replay_records(res["records"])
    assert state_hash(replayed) == res["final_state_hash"]


def test_replay_from_disk_roundtrip(tmp_path):
    res = run(seed=2026, rounds=12)
    log_path = tmp_path / "run.jsonl"
    write_log(res["records"], log_path)
    loaded = read_log(log_path)
    assert state_hash(replay_records(loaded)) == res["final_state_hash"]


def test_different_seed_different_state():
    a = run(seed=1, rounds=5)["final_state_hash"]
    b = run(seed=2, rounds=5)["final_state_hash"]
    assert a != b


def test_same_seed_same_result_pure_deterministic():
    """骨架阶段无 LLM 判定，故同 seed 两次首跑也应逐位一致。"""
    a = run(seed=999, rounds=10)["final_state_hash"]
    b = run(seed=999, rounds=10)["final_state_hash"]
    assert a == b
