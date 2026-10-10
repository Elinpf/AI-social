#!/usr/bin/env python3
"""live_run.py — 「正在运行的小镇」节流运行器（T75）。

以**节流**方式在真内核上逐回合推进（`orchestration.build_world` + `engine.run_round`），
每回合把**新增事件**追加到 `sample/live/live.jsonl`，并更新 `sample/live/latest_state.json`。
前端用 `?live=sample/live/live.jsonl&follow=1` 轮询跟随。

**纪律**：只读世界/不参与判定；**不改 engine/config**；引擎代码不动，确定性不受影响——
本产物就是引擎首跑日志的**增量落地**，事后仍可 `python -m engine verify`。

零网络：`build_world` 默认用离线 MockProvider（除非显式 `HITT_LLM_PROVIDER=openai_compat`）。

用法（从 `code/` 运行）：
    python frontend/tools/live_run.py --n 6 --rounds 24 --throttle 0.6
    python frontend/tools/live_run.py --n 20 --rounds 84 --throttle 1.0 --seed 42
参数：
    --n / --rounds / --seed / --throttle(秒/回合) / --out-dir（默认 frontend/sample/live）
    --reset 覆盖已有 live.jsonl（默认覆盖，保证从 round 0 开始）
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CODE_DIR))


def _dump(rec: dict) -> str:
    return json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="节流运行小镇（live 跟随）")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--rounds", type=int, default=24)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--throttle", type=float, default=0.6, help="每回合间隔秒（节流）")
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parents[1] / "sample" / "live"))
    ap.add_argument("--reset", action="store_true", help="清空已有 live.jsonl（默认也清空）")
    args = ap.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    live = out_dir / "live.jsonl"
    latest = out_dir / "latest_state.json"
    meta = out_dir / "meta.json"
    live.write_text("", encoding="utf-8")   # 从 round 0 开始

    from orchestration.integration import build_world
    from engine.state import state_hash

    world = build_world(args.seed, n=args.n)
    engine = world["engine"]
    meta.write_text(json.dumps({
        "schema": "hitt.live/1",
        "note": "节流运行的增量日志；权威确定性由 engine 保证，可 verify。只读派生。",
        "seed": args.seed, "n": args.n, "rounds": args.rounds,
        "engine_version": getattr(engine, "engine_version", ""),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    seen = 0
    print(f"live: seed={args.seed} n={args.n} rounds={args.rounds} throttle={args.throttle}s -> {live}")
    try:
        with live.open("a", encoding="utf-8") as f:
            for r in range(args.rounds):
                engine.run_round(r)
                recs = engine.ledger.records
                new = recs[seen:]
                seen = len(recs)
                for rec in new:
                    f.write(_dump(rec))
                f.flush()
                sh = state_hash(engine.state)
                latest.write_text(json.dumps({
                    "round": r, "max_round": args.rounds - 1, "events": seen,
                    "state_hash": sh, "ts": time.time(),
                }, ensure_ascii=False), encoding="utf-8")
                print(f"  round {r:>3}  +{len(new):>4} events  total={seen}  state_hash={sh[:22]}…")
                time.sleep(args.throttle)
    except KeyboardInterrupt:
        print("\nstopped by user")
    print(f"done: rounds={args.rounds} events={seen} -> {live}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
