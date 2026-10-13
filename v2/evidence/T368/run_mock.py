#!/usr/bin/env python3
"""T368 核验用 mock 世界 runner —— **每次一个独立进程**（防 T298 型同进程假分叉）。

用法（cwd 任意；T367_CODE 指向 worktree 分支 code）：
    T367_CODE=<repo>/.worktrees/t367/code python run_mock.py --mode on  --seed 7 --out on.jsonl
    T367_CODE=<repo>/.worktrees/t367/code python run_mock.py --mode off --seed 7 --out off.jsonl
    T367_CODE=<repo>/.worktrees/t367/code python run_mock.py --mode dose0 --seed 7 --out dose0.jsonl

mode：on=日历默认开；off=全关（enabled=false）；dose0=enabled=true 但剂量 0（应≡off）。
只读 worktree、不写主树；ledger 落 `--out`。
"""
from __future__ import annotations
import argparse, json, os, sys

os.environ.setdefault("N50_VEC", "0")
CODE = os.environ.get("T367_CODE")
if not CODE:
    sys.exit("需要环境变量 T367_CODE 指向 worktree code 目录")
sys.path.insert(0, CODE)

from engine.runner import default_config            # noqa: E402
from orchestration.integration import build_world    # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["on", "off", "dose0"], default="on")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    cfg = default_config()
    cal = cfg.setdefault("world_director", {}).setdefault("calendar", {})
    for k in ("season", "festival", "abundance"):
        cal.setdefault(k, {})
    if a.mode == "off":
        for k in ("season", "festival", "abundance"):
            cal[k]["enabled"] = False
    elif a.mode == "dose0":
        for k in ("season", "festival", "abundance"):
            cal[k]["enabled"] = True
            cal[k]["amp_bp" if k == "abundance" else "strength_bp"] = 0

    w = build_world(seed=a.seed, n=a.n, config=cfg)
    for r in range(a.rounds):
        w["engine"].run_round(r)
    recs = list(w["engine"].ledger.records)
    with open(a.out, "w", encoding="utf-8") as f:
        for rec in recs:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"OK mode={a.mode} seed={a.seed} n={a.n} rounds={a.rounds} events={len(recs)} out={a.out}")


if __name__ == "__main__":
    main()
