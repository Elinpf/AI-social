#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEQUANT n16r60 两臂「开臂生效」对拍（只读，零 LLM）。

口径与 CYCLE-28 的 v2/evidence/run_dequant_on_n8r16_seed42/prompt_hash_compare.txt 一致：
  取 type=LLM_CALL 且 payload.purpose=dialogue 且 payload.cached=false 的事件，
  比较两臂的 prompt_hash 集合。

用法：
  python3 v2/evidence/dequant_prompt_hash_compare_n16r60_seed42.py \
      --off <off run.jsonl> --on <on run.jsonl> [--out compare.txt]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def dialogue_hashes(log: Path) -> list[str]:
    out: list[str] = []
    with open(log, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "LLM_CALL":
                continue
            p = d.get("payload") or {}
            if p.get("purpose") != "dialogue":
                continue
            if p.get("cached"):
                continue
            h = p.get("prompt_hash")
            if h:
                out.append(h)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    off = dialogue_hashes(Path(a.off))
    on = dialogue_hashes(Path(a.on))
    s_off, s_on = set(off), set(on)
    inter = s_off & s_on

    lines = [
        f"OFF dialogue non-cached LLM_CALL: {len(off)}  distinct prompt_hash: {len(s_off)}",
        f"ON  dialogue non-cached LLM_CALL: {len(on)}  distinct prompt_hash: {len(s_on)}",
        f"intersection(prompt_hash): {len(inter)}",
    ]
    if off:
        lines.append(f"sample OFF[0]: {off[0]}")
    if on:
        lines.append(f"sample ON [0]: {on[0]}")
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
