#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CYCLE-45 ④节案例取证脚本（只读既有冻结日志，不做任何改写）。

用途：按 (run.jsonl, seq) 精确定位 MSG_DM/MSG_PUBLIC 事件，逐字打印原文 + 结构字段 +
逐行 sha256，用于报告的「④可展示案例」栏自查"能在 run.jsonl 按 seq 逐字对上"。

用法：
  python3 v2/evidence/CYCLE-45-cases/extract_cases.py
"""
import hashlib
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# (标签, 跑批目录相对仓库根, 需摘取的 seq 列表)
TARGETS = [
    ("ON  run_weather_on_n16r24_seed42_c28",
     "v2/evidence/run_weather_on_n16r24_seed42_c28", [73, 549, 2090]),
    ("ON  run_weather_on_n16r24_seed42_c28",
     "v2/evidence/run_weather_on_n16r24_seed42_c28", [2230, 3982, 5070]),
    ("ON  run_weather_on_n16r24_seed42_c28",
     "v2/evidence/run_weather_on_n16r24_seed42_c28", [135, 954, 2162]),
    ("OFF run_weather_off_n16r24_seed42_c28",
     "v2/evidence/run_weather_off_n16r24_seed42_c28", [73, 549, 2090]),
]

KEEP = ("thread_id", "msg_uid", "participants", "day", "slot", "turn_index",
        "topic", "from", "to", "author", "reply_to", "scope", "place")


def scan(run_dir, seqs):
    path = os.path.join(REPO, run_dir, "run.jsonl")
    if not os.path.isfile(path):
        print("MISSING run.jsonl: %s" % path)
        return {}
    want = set(seqs)
    found = {}
    with open(path, "rb") as fh:
        for raw in fh:
            # 轻量预筛：仅当该行可能命中才完整解析
            try:
                obj = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            if obj.get("seq") in want and obj.get("type") in ("MSG_DM", "MSG_PUBLIC"):
                found[obj["seq"]] = (raw, obj)
    return found


def main():
    rc = 0
    for label, run_dir, seqs in TARGETS:
        path = os.path.join(REPO, run_dir, "run.jsonl")
        print("=" * 78)
        print("BATCH %s" % label)
        print("RUN_DIR %s" % run_dir)
        if os.path.isfile(path):
            h = hashlib.sha256()
            n = 0
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
                    n += chunk.count(b"\n")
            print("RUN_JSONL_SHA256 %s" % h.hexdigest())
            print("RUN_JSONL_LINES %d" % n)
        else:
            print("MISSING %s" % path)
            rc = 1
        found = scan(run_dir, seqs)
        for seq in seqs:
            if seq not in found:
                print("-- seq %s : NOT FOUND (rc->1)" % seq)
                rc = 1
                continue
            raw, obj = found[seq]
            pl = obj["payload"]
            line_sha = hashlib.sha256(raw).hexdigest()
            print("-- seq %s type=%s round=%s phase=%s line_sha256=%s"
                  % (seq, obj.get("type"), obj.get("round"), obj.get("phase"), line_sha))
            print("   struct %s" % json.dumps({k: pl.get(k) for k in KEEP},
                                              ensure_ascii=False, sort_keys=True))
            print("   ctx.weather %s" % json.dumps((pl.get("ctx") or {}).get("weather"),
                                                   ensure_ascii=False, sort_keys=True))
            print("   ctx.l7struct %s" % json.dumps((pl.get("ctx") or {}).get("l7struct"),
                                                    ensure_ascii=False, sort_keys=True))
            print("   body: %s" % pl.get("body"))
    print("=" * 78)
    print("EXTRACT_RC=%d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
