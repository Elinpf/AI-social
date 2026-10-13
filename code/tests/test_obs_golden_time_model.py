"""T300 加固：golden 基线元数据 `time_model`（T339 §4 / 08 §5.10）。

要求（Leader——"分界线只写文档不够，必须落进基线元数据"）：
  1. `compute_baseline` 产出带 `time_model`；
  2. 更早（分界线 A 前）无戳日志 ⇒ 归并 `atomic`；
  3. 同一份日志两次调用**字节相等**（obs 层确定性红线）；
  4. 既有 `golden_baseline.json` 条目均带 `time_model`（既有基线标 `atomic`）。
"""

import json

from obs.golden import compute_baseline, load_baselines, log_meta
from obs.testsupport import build_log


def _stamped_log(stamp: str):
    """含 `WORLD_INIT.payload.time_model` 戳的日志（T287 期① 起引擎总写）。"""
    lb = build_log(seed=42, agents=("A000", "A001"))
    # build_log 的 WORLD_INIT 无 time_model；这里直接构造一条带戳的替代记录集
    recs = lb.records()
    for r in recs:
        if r["type"] == "WORLD_INIT":
            r["payload"] = {**r["payload"], "time_model": stamp}
            break
    return recs


def test_log_meta_reads_time_model_stamp():
    assert log_meta(_stamped_log("interval-U6"))["time_model"] == "interval-U6"
    # 无戳（旧日志/分界线 A 前）⇒ None，由 compute_baseline 归并为 atomic
    assert log_meta(build_log(seed=42).records())["time_model"] is None


def test_compute_baseline_time_model_defaults_atomic_for_unstamped():
    b = compute_baseline(build_log(seed=42).records(), "t_unstamped")
    assert b["time_model"] == "atomic"


def test_compute_baseline_preserves_interval_stamp():
    b = compute_baseline(_stamped_log("interval-U6"), "t_stamped")
    assert b["time_model"] == "interval-U6"


def test_compute_baseline_byte_equal_two_calls():
    recs = _stamped_log("interval-U6")
    a = json.dumps(compute_baseline(recs, "t"), sort_keys=True)
    b = json.dumps(compute_baseline(recs, "t"), sort_keys=True)
    assert a == b


def test_existing_baselines_all_carry_time_model():
    data = load_baselines()
    for bid, entry in data.items():
        if bid.startswith("_"):
            continue
        assert "time_model" in entry, bid
        assert entry["time_model"] == "atomic", bid  # 既有基线 = 分界线 A 前
