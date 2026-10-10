"""验证 LLM_CALL round=0 污染 bug 与内核侧兜底修法（离线、MockProvider，无网络）。

- 默认（未打补丁）：审计事件 round 取自 freeze（importance 调用无 round→0）→ 某些回合
  `LLM_CALL.round=0` → `apply_event` 把 state.round 置 0 → 该回合 TURN_SEAL 哈希与重放不一致
  → `replay_records(..., verify=True)` 报错。
- `--patch`：monkeypatch `orchestration.integration._make_audit_sink` 为**权威版**
  （round 取 `engine.state.round`）→ round=0 消失 → 重放一致。

用法：
    python3 scripts/verify_round_fix.py            # 复现 bug
    python3 scripts/verify_round_fix.py --patch    # 验证修法
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop("HITT_LLM_PROVIDER", None)  # 强制离线 Mock（无网络）


def authoritative_sink(engine):
    """建议的权威版审计 sink：round 取引擎当前回合（忽略 freeze 传入值）。"""
    from engine.events import spec

    def _sink(kind: str, payload: dict, round_no: int, phase: int) -> int:
        r = int(engine.state.round)
        seqs = engine.emit_specs([spec(r, int(phase), "SYSTEM", kind, payload)])
        return seqs[0] if seqs else -1

    return _sink


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", action="store_true")
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n", type=int, default=3)
    args = ap.parse_args()

    import orchestration.integration as integ
    if args.patch:
        integ._make_audit_sink = authoritative_sink

    world = integ.build_world(seed=args.seed, n=args.n)
    engine = world["engine"]
    for r in range(args.rounds):
        engine.run_round(r)
    records = engine.ledger.records

    zero_round_llm = sum(1 for rec in records
                         if rec["type"] == "LLM_CALL" and int(rec["round"]) == 0)
    types = Counter(rec["type"] for rec in records)

    from engine.replay import replay_records
    try:
        replay_records(records, verify=True, verify_seals=False)
        replay_ok, err = True, None
    except Exception as exc:  # noqa: BLE001
        replay_ok, err = False, f"{type(exc).__name__}: {exc}"

    out = {
        "patched": args.patch,
        "rounds": args.rounds, "n": args.n,
        "llm_call": types.get("LLM_CALL", 0),
        "llm_call_round0": zero_round_llm,
        "replay_ok": replay_ok,
        "replay_error": err,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
