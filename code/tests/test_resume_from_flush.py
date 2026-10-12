"""T276：从 flush 前缀续跑 —— **逐字节一致**对照实验。

一次性（0..target）vs 「跑到 K kill 掉 → 从 flush 前缀续到 target」：
两次的最终日志字节必须完全一致（同 state_hash / 逐条事件相同）。
"""

from pathlib import Path

from orchestration.integration import run_e2e


def test_resume_from_flush_byte_identical(tmp_path):
    n, target, fe, cut = 4, 8, 4, 4
    # 一次性跑完
    one = tmp_path / "one.jsonl"
    run_e2e(seed=42, rounds=target, n=n, out_path=one,
            side_root=str(tmp_path / "side1"), flush_every=fe)

    # 前半段：跑到 cut 即"kill"（在 cut 边界 flush 出完整前缀），复用同一 side 根
    side2 = tmp_path / "side2"
    prefix = tmp_path / "prefix.jsonl"
    run_e2e(seed=42, rounds=cut, n=n, out_path=prefix,
            side_root=str(side2), flush_every=fe)

    # 续跑：从 flush 前缀恢复到 target
    two = tmp_path / "two.jsonl"
    rep = run_e2e(seed=42, rounds=target, n=n, out_path=two,
                  side_root=str(side2), flush_every=fe, resume_from=str(prefix))

    assert rep["start_round"] == cut
    assert one.read_bytes() == two.read_bytes(), "续跑与一次性跑不逐字节一致"
