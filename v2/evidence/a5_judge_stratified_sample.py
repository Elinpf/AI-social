#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A5 judge 分层配平抽样（leader 2026-10-22 口径）

要求：
  * 分三层 turns=2–3 / 4–6 / ≥7（以 A5 实际分布为准）
  * 每层两臂各抽同样条数（默认每层 4 线程；每线程取首条 + 末条）
  * 层内随机、seed 固定、两臂不同随机流
  * 某臂某层不足 ⇒ 如实报实际条数并标注"该层两臂不等量，只作观察"
输出：{"arm": ..., "layers": {...}, "samples": [...]}（可直接喂 d4_judge_run.py --sample ARM=file）
"""
import argparse, json, random
from collections import defaultdict

MSG = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
# 注：D2 结构上限 max_turns=6 ⇒ ≥7 层在两臂中**结构上不可能存在**（实测 max=6），
# 保留该层以"如实报 0"，不伪造样本、不合并层。
DEFAULT_LAYERS = [("t2_3", 2, 3), ("t4_6", 4, 6), ("t7p", 7, 10**9)]


def load_threads(path):
    th = defaultdict(list)
    for line in open(path, encoding="utf-8"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG:
            continue
        p = e.get("payload") or {}
        if not (p.get("body") or "").strip():
            continue
        tid = p.get("thread_id") or f"legacy-{p.get('msg_uid') or p.get('msg_id')}"
        th[tid].append({"seq": e.get("seq"), "round": e.get("round"), "payload": p})
    for v in th.values():
        v.sort(key=lambda m: (m["round"] or 0, m["seq"] or 0))
    return th


def pick(threads, layers, k_per_layer, rng):
    out, stats = [], []
    for name, lo, hi in layers:
        pool = sorted([t for t in threads.items() if lo <= len(t[1]) <= hi],
                      key=lambda kv: str(kv[0]))
        rng.shuffle(pool)
        chosen = pool[:k_per_layer]
        stats.append({"layer": name, "range": [lo, hi], "n_threads_in_pool": len(pool),
                      "n_threads_chosen": len(chosen)})
        for tid, msgs in chosen:
            for m in ([msgs[0], msgs[-1]] if len(msgs) > 1 else [msgs[0]]):
                p = m["payload"]
                out.append({"thread_id": tid, "msg_uid": p.get("msg_uid") or p.get("msg_id"),
                            "round": m["round"], "turn_index": p.get("turn_index"),
                            "from": p.get("from") or p.get("author"),
                            "to": p.get("to") or p.get("group_id"),
                            "topic": p.get("topic"), "body": p.get("body"),
                            "thread_len": len(msgs), "layer": name})
    return out, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="ARM=path")
    ap.add_argument("--arm-index", required=True, help="ARM=int")
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    arm, _, path = a.run.partition("=")
    _, _, idx = a.arm_index.partition("=")
    th = load_threads(path)
    dist = defaultdict(int)
    for _, v in th.items():
        n = len(v)
        for name, lo, hi in DEFAULT_LAYERS:
            if lo <= n <= hi:
                dist[name] += 1
                break
    samples, stats = pick(th, DEFAULT_LAYERS, a.k, random.Random(a.seed + int(idx)))
    json.dump({"arm": arm, "source": path, "seed": a.seed, "k_per_layer": a.k,
               "thread_count": len(th), "layer_distribution_all_threads": dict(dist),
               "layers": stats, "n_samples": len(samples), "samples": samples},
              open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[{arm}] threads={len(th)} dist={dict(dist)} samples={len(samples)}")
    for s in stats:
        print("   ", s)


if __name__ == "__main__":
    main()
