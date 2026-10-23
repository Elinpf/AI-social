#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-H 证据自洽核验：**落盘 hash ↔ 正文** 全量比对（真跑日志，510 条）。

为什么必须做这条：D12-E 那次假阴性（`scores` 恒 0 而接线全 PASS）的同族隐患是
「**落盘字段与正文不是同一份**」——接线只证明"字段存在、形状对"，证明不了"字段描述的就是这条正文"。
本脚本对每条 D12-H 消息做三件事：

1. 用 `payload.body` **重新计算** 8-gram `blake2b(digest_size=8)` 排序 hex 列表；
2. 与 `ctx.d12h.on.cand_shingle_hashes[ctx.d12h.on.picked]` **逐项比对**（顺序敏感，两边都排序）；
3. 核 `ctx.d12h.on.cand_shingle_counts[on.picked] == len(重算列表)`。

**可验证范围（必须写明）**：只有 **ON 组被选中那条** 落库，因此只有它能做"hash↔正文"互证；
OFF 组三条候选不落库（设计如此）⇒ **无法**从日志反查，本脚本对其只报"不可验证"。

用法：
    python3 tools/d12h/hash_body_consistency.py --log <run.jsonl> [--out-json x.json]
退出码：0 = 全部一致；3 = 存在不一致（并打印首个不一致样例）；2 = 日志里没有 D12-H 消息。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

sys.path.insert(0, "code")

from life import d12e_shingles as D  # noqa: E402  （与 agent 落盘用同一实现）


def hashes_of(text: str) -> list:
    hs = [hashlib.blake2b(sh.encode("utf-8"), digest_size=8).digest()
          for sh in D.shingles(text or "")]
    return [h.hex() for h in sorted(set(hs))]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args(argv)

    n_msgs = 0
    n_ok = n_bad = 0
    bad_samples = []
    miss_count = 0
    with open(a.log, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if not r.get("type", "").startswith("MSG"):
                continue
            p = r.get("payload") or {}
            ctx = p.get("ctx")
            if not (isinstance(ctx, dict) and "d12h" in ctx):
                continue
            n_msgs += 1
            c = ctx["d12h"]
            body = (p.get("body") or "").strip()
            want = c["on"]["cand_shingle_hashes"][c["on"]["picked"]]
            got = hashes_of(body)
            ok_hash = got == want
            cnt_ok = c["on"]["cand_shingle_counts"][c["on"]["picked"]] == len(got)
            if not cnt_ok:
                miss_count += 1
            if ok_hash and cnt_ok:
                n_ok += 1
            else:
                n_bad += 1
                if len(bad_samples) < 3:
                    bad_samples.append({
                        "round": r.get("round"), "seq": r.get("seq"),
                        "thread_id": p.get("thread_id"),
                        "on_picked": c["on"]["picked"],
                        "hash_equal": ok_hash, "count_equal": cnt_ok,
                        "len_recomputed": len(got), "len_logged": len(want),
                        "body_head": body[:40],
                        "first_diff_index": next(
                            (i for i, (x, y) in enumerate(zip(got, want)) if x != y), None),
                    })

    out = {
        "log": a.log,
        "spec": "8-gram(blake2b digest_size=8, sorted unique hex) of payload.body vs ctx.d12h.on.cand_shingle_hashes[on.picked]",
        "n_msgs_with_ctx_d12h": n_msgs,
        "n_consistent": n_ok,
        "n_inconsistent": n_bad,
        "n_count_mismatch": miss_count,
        "verifiable_scope": "仅 ON 组被选中那条（唯一落库的候选）；OFF 组三条不落库 ⇒ 不可验证",
        "bad_samples": bad_samples,
    }
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    print(txt)
    if a.out_json:
        with open(a.out_json, "w", encoding="utf-8") as fh:
            fh.write(txt + "\n")

    if n_msgs == 0:
        print("[FAIL] 日志里没有任何 ctx.d12h 消息", file=sys.stderr)
        return 2
    print(f"[{'PASS' if n_bad == 0 else 'FAIL'}] 落盘 hash ↔ 正文 一致 {n_ok}/{n_msgs}"
          f"（不一致 {n_bad}，count 不符 {miss_count}）", file=sys.stderr)
    return 0 if n_bad == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
