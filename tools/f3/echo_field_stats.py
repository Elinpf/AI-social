#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""echo_field_stats.py —— F-3「情绪呼应」机制字段（payload.ctx.echo）的多臂只读统计器。

零跑批、零 LLM：只解析各臂 run.jsonl 里已落的 MSG 事件。
用途：R1 轮把「OFF / ON（捆绑 F-3+F-4）」两臂的机制落点字段并列报数，
      并给出**回复路径覆盖率**（分母 = 带 payload.reply_to 的 MSG 条数；
      因为 F-3 只在 `_send_reply` 生效，`_initiate` 路径构造上不可能产 echo）。

严格纪律：
  * OFF 臂的 echo 计数**构造性为 0**（关闭时实现不写该键），本脚本照实打印，
    不把它当作「对照有效性」证据（判定力只来自内容层指标，见 v2/evidence/f3_audit_echo.py）。
  * 不做任何推断/插补；缺文件、缺键都原样报。

用法（仓库根）：
  python3 tools/f3/echo_field_stats.py \
      --arm off=v2/evidence/emo-off-20261030/run.jsonl \
      --arm on=v2/evidence/emo-on-20261029/run.jsonl \
      --out v2/evidence/f3_echo_field_stats.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter

MSG_PREFIX = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def event_type(rec: dict) -> str:
    for k in ("type", "event", "kind_of"):
        v = rec.get(k)
        if isinstance(v, str):
            return v
    return ""


def payload_of(rec: dict) -> dict:
    p = rec.get("payload")
    return p if isinstance(p, dict) else {}


def read_messages(path: str):
    msgs = []
    bad = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                bad += 1
                continue
            if not isinstance(rec, dict):
                continue
            if event_type(rec).startswith(MSG_PREFIX):
                msgs.append(rec)
    return msgs, bad


def summarize(path: str) -> dict:
    if not os.path.isfile(path):
        return {"run_jsonl": path, "exists": False}
    msgs, bad = read_messages(path)
    echo_rows = []
    for r in msgs:
        e = payload_of(r).get("ctx", {}).get("echo")
        if isinstance(e, dict):
            echo_rows.append((r, e))
    reply_msgs = [r for r in msgs if payload_of(r).get("reply_to")]
    reply_with_echo = [1 for r, _ in echo_rows if payload_of(r).get("reply_to")]
    signs = Counter(e.get("sign") for _, e in echo_rows)
    return {
        "run_jsonl": path,
        "exists": True,
        "run_jsonl_sha256": sha256_of(path),
        "unparsable_lines": bad,
        "msg_total": len(msgs),
        "msg_reply_path": len(reply_msgs),
        "msg_with_ctx_echo": len(echo_rows),
        "echo_on_reply_path": len(reply_with_echo),
        "echo_coverage_of_reply_path": (
            (len(reply_with_echo) / len(reply_msgs)) if reply_msgs else None
        ),
        "sign": {str(k): v for k, v in sorted(signs.items(), key=lambda kv: str(kv[0]))},
        "sign_negative_share": (
            (signs.get(-1, 0) / len(echo_rows)) if echo_rows else None
        ),
        "kind": dict(Counter(e.get("kind") for _, e in echo_rows)),
        "tier": dict(Counter(e.get("tier") for _, e in echo_rows)),
        "source": dict(Counter(e.get("source") for _, e in echo_rows)),
        "prompted": {str(k): v for k, v in Counter(e.get("prompted") for _, e in echo_rows).items()},
        "intensity_min": min((e.get("intensity") for _, e in echo_rows), default=None),
        "intensity_max": max((e.get("intensity") for _, e in echo_rows), default=None),
        "version": sorted({str(e.get("v")) for _, e in echo_rows}),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True,
                    help="label=path/to/run.jsonl，可重复")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    arms = {}
    for item in a.arm:
        if "=" not in item:
            print(f"[echo-stats] FATAL: --arm 需要 label=path，收到 {item}", file=sys.stderr)
            return 2
        label, path = item.split("=", 1)
        arms[label] = summarize(path)

    doc = {"spec": "F-3 echo field stats (read-only, zero-LLM)", "arms": arms}
    text = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"[echo-stats] wrote {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
