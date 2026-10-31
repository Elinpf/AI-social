#!/usr/bin/env python3
"""R43 离线复算：用**同一套计数口径**重算 R41b 的场所配额越界（不跑批、不联网、不调 LLM）。

用法：
    python3 tools/public_talk/recount_place_quota_r43.py <run.jsonl> [--json]

输出四组粒度（与 `reports/R41b-public-talk-verify.md` §2.3 完全一致）：
  1. `round × day × slot × place`（全部 MSG_PUBLIC）
  2. `day × slot × place`（跨 round 累计）
  3. `place × slot`（**忽略 day**，= R41 `public_count_at` 的代码语义）
  4. `place × slot`（只数接话：`reply_to` 非空）
  另给：`author × slot`（`MAX_PER_AGENT_PER_SLOT` 侧，应与 R41b 一样「未越界」）。

并额外给一份**静态反事实**（`--counterfactual`，默认开）：
  按落账顺序把 MSG_PUBLIC 逐条喂给 `life.public_talk.place_quota_gate()`，
  满 2 条即记 "would_drop"。这是「若 R43 闸在那批之前就存在」的上界估计，
  **不是新批实测**——被丢的消息会改变后续接话对象的选取，只能靠新批验证。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

CODE = Path(__file__).resolve().parents[2] / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from life import public_talk as PT  # noqa: E402

MAX_PLACE = PT.MAX_PER_PLACE_PER_SLOT


def load_public(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if ev.get("type") == "MSG_PUBLIC":
                out.append(ev)
    out.sort(key=lambda e: int(e["seq"]))
    return out


def _places_of(pub) -> list:
    return [p for _e, p in pub]


def calibers(pub: list[dict]) -> dict:
    c = {
        "round_day_slot_place": Counter(),
        "day_slot_place": Counter(),
        "slot_place_ignore_day": Counter(),
        "slot_place_replies_only": Counter(),
        "author_slot_replies": Counter(),
    }
    for ev in pub:
        p = ev["payload"]
        site = p.get("place")
        day, slot = p.get("day"), p.get("slot")
        c["round_day_slot_place"][(ev["round"], day, slot, site)] += 1
        c["day_slot_place"][(day, slot, site)] += 1
        c["slot_place_ignore_day"][(slot, site)] += 1
        if p.get("reply_to"):
            c["slot_place_replies_only"][(slot, site)] += 1
            c["author_slot_replies"][(p.get("author"), slot)] += 1
    return c


def top(counter: Counter, n: int = 3):
    return [{"key": list(k) if isinstance(k, tuple) else k, "n": v}
            for k, v in counter.most_common(n)]


def counterfactual(pub: list[dict]) -> dict:
    accepted: list[dict] = []
    dropped = []
    for ev in pub:
        p = ev["payload"]
        ok, n = PT.place_quota_gate(accepted, p.get("place"), p.get("day"), p.get("slot"))
        if ok:
            accepted.append({"round": ev["round"], "type": ev["type"], "payload": p})
        else:
            dropped.append({"seq": ev["seq"], "author": p.get("author"),
                            "round": ev["round"], "day": p.get("day"),
                            "slot": p.get("slot"), "place": p.get("place"),
                            "n_place": n})
    return {"accepted": len(accepted), "would_drop": len(dropped), "drops": dropped}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_jsonl")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    pub = load_public(Path(a.run_jsonl))
    c = calibers(pub)
    report = {
        "file": str(a.run_jsonl),
        "msg_public": len(pub),
        "max_per_place_per_slot": MAX_PLACE,
        "maxima": {
            "round_day_slot_place": max(c["round_day_slot_place"].values(), default=0),
            "day_slot_place": max(c["day_slot_place"].values(), default=0),
            "slot_place_ignore_day": max(c["slot_place_ignore_day"].values(), default=0),
            "slot_place_replies_only": max(c["slot_place_replies_only"].values(), default=0),
            "author_slot_replies": max(c["author_slot_replies"].values(), default=0),
        },
        "worst": {
            "round_day_slot_place": top(c["round_day_slot_place"]),
            "day_slot_place": top(c["day_slot_place"]),
            "slot_place_ignore_day": top(c["slot_place_ignore_day"]),
            "slot_place_replies_only": top(c["slot_place_replies_only"]),
        },
        "counterfactual_r43_gate": counterfactual(pub),
    }
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(f"file = {report['file']}")
    print(f"MSG_PUBLIC = {report['msg_public']}   MAX_PER_PLACE_PER_SLOT = {MAX_PLACE}")
    for k, v in report["maxima"].items():
        print(f"  max[{k}] = {v}   worst={report['worst'].get(k)}")
    cf = report["counterfactual_r43_gate"]
    print(f"counterfactual(R43 gate, 静态) : accepted={cf['accepted']} would_drop={cf['would_drop']}")
    for d in cf["drops"]:
        print("  drop", d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
