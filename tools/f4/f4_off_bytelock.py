#!/usr/bin/env python3
"""OFF 路径字节级锁：同一 mock 世界、同一 seed，改造前 vs 改造后日志必须逐字节一致（零跑批）。

做法（可复算）：
  1. `git stash push -- code/life/agent.py code/life/dialogue_repair.py \
         code/orchestration/integration.py code/tests/test_dialogue_repair.py`
  2. `python3 tools/f4/f4_off_bytelock.py --out /tmp/f4_off_before.jsonl`
  3. `git stash pop`
  4. `python3 tools/f4/f4_off_bytelock.py --out /tmp/f4_off_after.jsonl`
  5. `cmp /tmp/f4_off_before.jsonl /tmp/f4_off_after.jsonl && echo IDENTICAL`
  6. `grep -c '"dialogue_repair"' /tmp/f4_off_after.jsonl` → 必须为 0（grep 无命中 rc=1）

世界：`build_world(seed=7, n=6)` + 负向/中性交替 stub LLM（不联网、不读冻结配置以外的状态），
跑 40 回合，把 `engine.ledger.records` 按仓库 canonical_json 逐行写出（与 run.jsonl 同序列化口径）。
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "code"))


class _AltLLM:
    """负向 / 后续句交替：制造「张力 → 后续回合」的序列，同时保证 OFF 路径有真实 MSG 产出。

    `--stub scripted_repair` 时把后续句换成和解句（契约级证据：证明**链路**能把张力收口，
    而不是证明真 LLM 会这么说——后者只能靠真跑批）。
    """
    name = "stub"
    TEXTS = ("算了，你什么意思。", "今天天气不错，真好。")
    TEXTS_REPAIR = ("算了，你什么意思。", "抱歉，我不是那个意思。")

    def __init__(self) -> None:
        self.i = 0

    def call(self, purpose, prompt, *, model=None, meta=None):
        from life.llm import LLMResult
        t = self.TEXTS[self.i % len(self.TEXTS)]
        self.i += 1
        return LLMResult(text=t)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--rounds", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--stub", choices=("alternate", "scripted_repair"), default="alternate")
    ap.add_argument("--allow-on", action="store_true",
                    help="允许在 HITT_DIALOGUE_REPAIR=1 下运行（用于产出 ON 臂 mock 证据，不用于 OFF 字节锁）")
    args = ap.parse_args(argv)

    if not args.allow_on:
        assert os.environ.get("HITT_DIALOGUE_REPAIR") in (None, "", "0", "false", "off"), \
            "本脚本只用于 OFF 路径；请先 unset HITT_DIALOGUE_REPAIR（或用 --allow-on 跑 ON 证据）"

    from engine.integration import build_world
    from engine.canon import canonical_json

    llm = _AltLLM()
    if args.stub == "scripted_repair":
        llm.TEXTS = _AltLLM.TEXTS_REPAIR
    w = build_world(seed=args.seed, n=args.n, llm=llm)
    eng = w["engine"]
    for r in range(args.rounds):
        eng.run_round(r)
    recs = list(eng.ledger.records)
    out = args.out if os.path.isabs(args.out) else os.path.join(REPO, args.out)
    with open(out, "w", encoding="utf-8") as f:
        for rec in recs:
            f.write(canonical_json(rec))
            f.write("\n")
    n_msg = sum(1 for r in recs if r.get("type") in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"))
    n_repair = sum(1 for r in recs if "dialogue_repair" in ((r.get("payload") or {})))
    print("written:", out, "records:", len(recs), "msgs:", n_msg, "dialogue_repair:", n_repair)
    return 0


if __name__ == "__main__":
    sys.exit(main())
