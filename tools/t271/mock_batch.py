#!/usr/bin/env python3
"""T271 mock 小批 —— 只模拟长跑批的形态（增量 flush + 断点续跑 + 心跳），
不碰 code/engine|life|freeze|config，不碰世界语义。

用途：验证「跑批托管（脱离 jiuwenswarm.service cgroup）能在平台重启中存活」。
真批 NEVER 用它 —— 它只是形态替身。
"""
import argparse
import json
import os
import re
import sys
import threading
import time


def rss_mb(pid=None):
    path = f"/proc/{pid}/status" if pid else "/proc/self/status"
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return -1


def resume_prefix(out):
    """断点续跑：只信任到最后一个完整 ROUND_END 行为止的前缀；截掉未完成尾巴。"""
    if not os.path.exists(out):
        return 0
    with open(out, "rb") as f:
        data = f.read()
    if not data:
        return 0
    lines = data.split(b"\n")
    pos = 0
    last_round = 0
    good_end = 0
    for ln in lines[:-1]:          # 完整的（换行结尾）行
        pos += len(ln) + 1
        if b'"ROUND_END"' in ln:
            m = re.search(rb'"round":\s*(\d+)', ln)
            if m:
                last_round = int(m.group(1))
                good_end = pos
    if good_end and good_end != len(data):
        with open(out, "r+b") as f:
            f.truncate(good_end)
        print(f"[resume] 截断未完成尾巴 {len(data)-good_end}B → 从 round {last_round} 之后续跑", flush=True)
    elif last_round:
        print(f"[resume] 完整前缀到 round {last_round} → 续跑", flush=True)
    else:
        print("[resume] 无可信前缀 → 从 0 重来", flush=True)
    return last_round


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--agents", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--flush-every", type=int, default=5)
    ap.add_argument("--round-seconds", type=float, default=0.2)
    ap.add_argument("--heartbeat-log", default=None)
    ap.add_argument("--heartbeat-seconds", type=float, default=600.0)
    args = ap.parse_args()

    out = args.out
    hb = args.heartbeat_log or (out + ".hb")
    start_round = resume_prefix(out)
    state = {"round": start_round, "done": False}
    stop = threading.Event()

    def hb_loop():
        while True:
            try:
                size = os.path.getsize(out)
            except OSError:
                size = -1
            line = "%s\t%d\t%s\t%d" % (time.strftime("%F %T"), size,
                                       state["round"], rss_mb())
            with open(hb, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            if stop.wait(args.heartbeat_seconds):
                break

    t = threading.Thread(target=hb_loop, daemon=True)
    t.start()

    with open(out, "a", encoding="utf-8") as f:
        for r in range(start_round + 1, args.rounds + 1):
            state["round"] = r
            time.sleep(args.round_seconds)              # 模拟每回合工作量
            for a in range(args.agents):
                rec = {"type": "MOCK_EVENT", "round": r, "agent_id": f"agent{a:02d}",
                       "seq": r * args.agents + a, "payload": {"x": (r * 7 + a) % 13}}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.write(json.dumps({"type": "ROUND_END", "round": r}, ensure_ascii=False) + "\n")
            if args.flush_every and r % args.flush_every == 0:
                f.flush()
                os.fsync(f.fileno())
        f.flush()
        os.fsync(f.fileno())

    stop.set()
    state["done"] = True
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "RUN_END", "round": args.rounds}, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(f"[done] rounds={args.rounds}", flush=True)


if __name__ == "__main__":
    main()
