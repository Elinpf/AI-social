#!/usr/bin/env python3
"""T355 override E2E —— 非作者独立复核（sandbox-test-lead；kernel 为 mock 作者）。

复现 kernel 的 small mock：life 业态（build_world 带 life agents → KernelAdapter）×2，
cfg["time"]["ongoing"]["enabled"]=True|False，同 seed/n/rounds；断言两条消费者 + 族差。
只读；不改 code/。
"""
import os
import sys
from collections import Counter

os.environ.setdefault("N50_VEC", "0")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "code"))

from orchestration.integration import build_world       # noqa: E402
from engine.runner import default_config                # noqa: E402
from engine import perceive as _P                       # noqa: E402


def arm(ongoing, seed=42, rounds=24, n=4):
    cfg = default_config()
    cfg.setdefault("time", {}).setdefault("ongoing", {})["enabled"] = ongoing
    w = build_world(seed=seed, config=cfg, n=n)
    eng = w["engine"]
    adapter = eng.kernel
    a_on = adapter._ongoing
    fl = _P._load_time_flags(cfg)["ongoing_enabled"]
    for r in range(rounds):
        eng.run_round(r)
    fams = Counter(r.get("type") for r in eng.ledger.records)
    return {"adapter._ongoing": a_on, "_load_time_flags(cfg)": fl, "fams": fams}


def main():
    on = arm(True)
    off = arm(False)
    print("=== T355 override E2E · 非作者独立复核（life 业态）===")
    print(f"arm ongoing=True : _load_time_flags(cfg)={on['_load_time_flags(cfg)']} adapter._ongoing={on['adapter._ongoing']}")
    print(f"arm ongoing=False: _load_time_flags(cfg)={off['_load_time_flags(cfg)']} adapter._ongoing={off['adapter._ongoing']}")
    cons = (on["adapter._ongoing"] is True and on["_load_time_flags(cfg)"] is True
            and off["adapter._ongoing"] is False and off["_load_time_flags(cfg)"] is False)
    print(f"两条消费者一致（True→True / False→False）: {'PASS' if cons else 'FAIL'}")
    fams = sorted(set(on["fams"]) | set(off["fams"]))
    show = {f: (on["fams"].get(f, 0), off["fams"].get(f, 0)) for f in fams
            if on["fams"].get(f, 0) != off["fams"].get(f, 0) or f in ("PLACE_MOVE", "ACTIVITY_STARTED")}
    print(f"族 (on, off): {show}")
    differ = {f for f in fams if on["fams"].get(f, 0) != off["fams"].get(f, 0)}
    print(f"arms_differ: {bool(differ)}  非零族={sorted(differ)}")
    print(f"→ 覆盖真生效: {'PASS（非静默丢弃）' if (cons and differ) else 'FAIL'}")
    return 0 if (cons and differ) else 1


if __name__ == "__main__":
    sys.exit(main())
