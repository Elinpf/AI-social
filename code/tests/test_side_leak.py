"""T232：临时 side 目录卫生——归属标记 / 异常释放 / 孤儿 sweeper（含实测）。"""

import glob
import os
import tempfile

import pytest

from orchestration import integration as I


def test_side_marker_written():
    root = I.make_side_root()
    try:
        assert os.path.exists(os.path.join(root, ".owner"))
        assert os.path.exists(os.path.join(root, ".started_at"))
    finally:
        I._safe_rmtree(root)


def test_managed_side_root_cleans_on_exception():
    """关键验收：异常路径也释放（不是"看代码觉得会清"）。"""
    with pytest.raises(RuntimeError):
        with I.managed_side_root() as root:
            assert os.path.isdir(root)
            raise RuntimeError("boom")
    assert not os.path.exists(root)  # 异常后确实被清理


def test_explicit_side_root_is_preserved(tmp_path):
    d = tmp_path / "keep"
    d.mkdir()
    I.run_e2e(seed=7, n=3, rounds=2, side_root=str(d))
    assert d.exists()  # 显式传入的目录不被删除（调用方负责）


def test_sweeper_removes_stale_orphan_keeps_live(tmp_path):
    orphan = tmp_path / "hitt_side_orphan"
    orphan.mkdir()
    (orphan / ".owner").write_text("pid=999999")   # 远超 pid_max → 已死
    (orphan / ".started_at").write_text("0")
    live = tmp_path / "hitt_side_live"
    live.mkdir()
    (live / ".owner").write_text(f"pid={os.getpid()}")  # 本进程存活
    (live / ".started_at").write_text("0")

    res = I.sweep_orphan_side_dirs(base_dir=str(tmp_path), ttl_seconds=1, now=10 ** 9)
    assert not orphan.exists() and str(orphan) in res["removed"]     # 孤儿被清
    assert live.exists() and str(live) in res["kept"]                # 活着的**不动**
    assert res["warned"], "清理必须告警（不静默删）"                  # 告警可见


def test_sweeper_no_marker_stale_is_removed(tmp_path):
    d = tmp_path / "hitt_side_nomarker"
    d.mkdir()
    res = I.sweep_orphan_side_dirs(base_dir=str(tmp_path), ttl_seconds=0, now=10 ** 10)
    assert not d.exists() and str(d) in res["removed"]


def test_run_e2e_leaves_no_new_side_dirs():
    base = tempfile.gettempdir()
    before = set(glob.glob(os.path.join(base, "hitt_side_*")))
    I.run_e2e(seed=7, n=3, rounds=2)
    after = set(glob.glob(os.path.join(base, "hitt_side_*")))
    assert after <= before, f"run_e2e 遗留 side 目录：{after - before}"
