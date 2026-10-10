#!/usr/bin/env python3
"""生成前端回放样例日志（确定性、只读导出）。

产出 `frontend/sample/demo_run.jsonl`：一个**含 PLACE_MOVE / PLACE_ARRIVED /
ACTIVITY_* / TIME_MARK** 的事件日志，用来验证「按回合步进能看到 Agent 移动」。

数据来源：`life` 层（人格生活层）在 MiniKernel 上的确定性运行——**不是**前端伪造。
`life` 层的 ledger 记录格式与 `engine` 完全一致（seq/round/phase/actor/type/payload/
mono_ts/prev_hash/hash），因此前端可无缝读入，真实执行时替换为
`engine run --out logs/run.jsonl` 的产物即可。

用法（从 `code/` 运行）：
    python frontend/tools/gen_demo_log.py                 # 默认 seed=7, rounds=20
    python frontend/tools/gen_demo_log.py --seed 7 --rounds 20
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parents[1] / "sample" / "demo_run.jsonl"

sys.path.insert(0, str(CODE_DIR))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    from life.run_demo import build

    with tempfile.TemporaryDirectory() as d:
        kernel, agents = build(args.seed, Path(d))
        for _ in range(args.rounds):
            kernel.tick(agents)
        ledger = kernel.ledger

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in ledger:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    from collections import Counter
    census = Counter(e["type"] for e in ledger)
    moves = census.get("PLACE_MOVE", 0)
    print(f"wrote {out}  events={len(ledger)}  seed={args.seed} rounds={args.rounds}")
    for t, n in sorted(census.items()):
        print(f"  {t:<22} {n}")
    if moves == 0:
        print("WARN: 样例不含 PLACE_MOVE，前端将看不到移动", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
