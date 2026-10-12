"""T262：run_e2e 周期 flush —— 中途 kill 保留可消费的已提交前缀。"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from engine.replay import replay_records
from engine.runner import write_log
from orchestration.integration import _flush_log_atomic, run_e2e

_CODE = Path(__file__).resolve().parents[1]


def read_all(p):
    out = []
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def test_flush_helper_matches_write_log_bytes(tmp_path):
    from engine.runner import run
    records = run(seed=3, rounds=4)["records"]
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    write_log(records, a)
    _flush_log_atomic(records, b)
    assert a.read_bytes() == b.read_bytes()          # 同序列化口径（键排序/紧凑/ascii=False）
    assert replay_records(read_all(b)) is not None   # 前缀可被 replay 消费（链校验通过）


def test_default_and_flush_produce_identical_bytes(tmp_path):
    """默认行为不变：flush_every=0 与 flush_every=5 的最终产物字节一致。"""
    o0 = tmp_path / "off.jsonl"
    o5 = tmp_path / "on.jsonl"
    run_e2e(seed=42, n=3, rounds=12, out_path=o0, side_root=str(tmp_path / "s0"))
    run_e2e(seed=42, n=3, rounds=12, out_path=o5, side_root=str(tmp_path / "s1"), flush_every=5)
    assert o0.read_bytes() == o5.read_bytes()


def _spawn(script: str):
    return subprocess.Popen([sys.executable, "-c", script], cwd=str(_CODE),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_kill_mid_run_preserves_consumable_prefix(tmp_path):
    """① 前置：用周期 flush 跑，中途 SIGKILL；日志非空、无半条、可 replay。"""
    out = tmp_path / "fwd.jsonl"
    side = tmp_path / "side_fwd"
    script = (
        "from orchestration.integration import run_e2e;"
        f"run_e2e(seed=42, rounds=1500, n=6, out_path=r'{out}', side_root=r'{side}', flush_every=1)"
    )
    proc = _spawn(script)
    try:
        deadline = time.time() + 30
        while time.time() < deadline and not (out.exists() and out.stat().st_size > 0):
            time.sleep(0.05)
        assert out.exists() and out.stat().st_size > 0, "周期 flush 未产生任何前缀"
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
    recs = read_all(out)                       # 每行都是完整 JSON（无半条）
    assert len(recs) > 0
    st = replay_records(recs)                  # 前缀可被 replay/verify 消费
    assert st.round >= 0


def test_without_flush_kill_loses_everything(tmp_path):
    """② 反向验证：不改前的行为（只在末尾写）中途 kill -> 日志不存在/为空。"""
    out = tmp_path / "rev.jsonl"
    side = tmp_path / "side_rev"
    script = (
        "from orchestration.integration import run_e2e;"
        f"run_e2e(seed=42, rounds=1500, n=6, out_path=r'{out}', side_root=r'{side}')"
    )
    proc = _spawn(script)
    try:
        time.sleep(3.0)                        # 跑一段（远不到末尾）
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert (not out.exists()) or out.stat().st_size == 0, "旧行为竟留下日志？反向验证失败"
