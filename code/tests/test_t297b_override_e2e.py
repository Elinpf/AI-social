"""T297b: life 配置注入 hook —— 端到端（code/tests：经 build_world，可 import orchestration）。

验证：override 经 `run_e2e(config=cfg)` 真生效（sleep 真关）；不 override 时与基线逐字节一致。
"""
from __future__ import annotations

import json

from engine.runner import default_config
from orchestration.integration import run_e2e


def _run(tmp_path, cfg, tag):
    out = tmp_path / f"{tag}.jsonl"
    run_e2e(seed=7, rounds=20, n=2, out_path=str(out), side_root=str(tmp_path / f"s_{tag}"),
            config=cfg)
    return [json.loads(l) for l in open(out)]


def test_override_disables_sleep_end_to_end(tmp_path):
    base = _run(tmp_path, None, "base")
    assert any(r["type"] == "SLEEP_STARTED" for r in base), "baseline should sleep"

    cfg = default_config()
    cfg["life_v2"] = {"sleep": {"enabled": False}, "forgetting": {"enabled": False}}
    ov = _run(tmp_path, cfg, "ov")
    assert not any(r["type"] == "SLEEP_STARTED" for r in ov), "override must disable sleep"


def test_no_override_is_byte_identical(tmp_path):
    a = _run(tmp_path, None, "a")
    b = _run(tmp_path, None, "b")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
