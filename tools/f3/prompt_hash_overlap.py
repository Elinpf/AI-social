#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两臂 `prompt_hash` 交集复算器（**只读**，零跑批、零 LLM）。

## 用途（R38 / F-3 可比性证据块第 1 条）

给两臂 `run.jsonl`，直接复算「两臂实际送给 LLM 的提示词是不是同一批」：
从 `LLM_CALL` 事件里按 `purpose` 取 `payload.prompt_hash`，输出每臂调用数、
去重数、以及两臂的集合交集 / 多重集交集 / Jaccard。

**为什么需要它**：`engine_version` 指纹与 `config_components` 在 OFF/ON 两臂**必然相同**
（`code/config/emotion_echo.json` 不在 `code/engine/version.py::FINGERPRINT_FILES` 里），
所以「指纹相同」不能用来证明可比性；能证明「开关真的只改了这一个变量」的，是
**`prompt_hash` 在 dialogue 这一 purpose 上大面积不同、而在其它 purpose 上完全相同**。

## 用法

    python3 tools/f3/prompt_hash_overlap.py \
        --arm off=v2/evidence/r38_f3_batch/off/run.jsonl \
        --arm on=v2/evidence/r38_f3_batch/on/run.jsonl \
        [--purpose dialogue] [--out-json /tmp/prompt_hash_overlap.json]

退出码：0 正常 / 2 前置条件缺失（文件不存在或 --arm 不足 2 个）

## 口径

- `calls`：该 purpose 的 `LLM_CALL` 条数（含缓存命中，`cached` 不影响计数）；
- `unique`：`prompt_hash` 去重后的个数；
- `set_intersection`：两臂 `prompt_hash` 集合交集的元素个数（**推荐口径**，对重复调用不敏感）；
- `multiset_intersection`：`sum(min(count_a[h], count_b[h]))`（重复调用也计入，用于发现"重复相同提示词"）；
- `jaccard`：`|A∩B| / |A∪B|`（集合口径）。
- 纯确定性：输出键按字典序排序、无时间戳，同输入必得同输出。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def read_prompt_hashes(path: str, purposes: set[str] | None) -> Counter:
    """从 run.jsonl 收集 LLM_CALL 的 prompt_hash 计数（跳过无 hash / purpose 不匹配的行）。"""
    c: Counter = Counter()
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or '"prompt_hash"' not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "LLM_CALL":
                continue
            p = rec.get("payload") or {}
            if purposes is not None and str(p.get("purpose")) not in purposes:
                continue
            h = p.get("prompt_hash")
            if h:
                c[str(h)] += 1
    return c


def compare(a: Counter, b: Counter) -> dict:
    sa, sb = set(a), set(b)
    inter = sa & sb
    mini = sum(min(a[h], b[h]) for h in inter)
    union = sa | sb
    return {
        "calls": sum(a.values()),
        "unique": len(sa),
        "set_intersection": len(inter),
        "multiset_intersection": mini,
        "only_in_first": len(sa - sb),
        "only_in_second": len(sb - sa),
        "union": len(union),
        "jaccard": (len(inter) / len(union)) if union else None,
        "identical_set": sa == sb,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="两臂 prompt_hash 交集复算（只读）")
    ap.add_argument("--arm", action="append", default=[], metavar="NAME=PATH",
                    help="臂名=run.jsonl 路径，至少两个（可重复）")
    ap.add_argument("--purpose", default="dialogue",
                    help="只统计该 purpose，逗号分隔；传 all 表示不过滤（默认 dialogue）")
    ap.add_argument("--out-json", default=None, help="把结果写到该 JSON 路径")
    args = ap.parse_args(argv)

    arms: list[tuple[str, str]] = []
    for item in args.arm:
        if "=" not in item:
            print(f"--arm 需要 NAME=PATH 形式，收到: {item}", file=sys.stderr)
            return 2
        name, path = item.split("=", 1)
        if not Path(path).is_file():
            print(f"文件不存在: {path}", file=sys.stderr)
            return 2
        arms.append((name, path))
    if len(arms) < 2:
        print("至少需要两个 --arm", file=sys.stderr)
        return 2

    purposes = None if args.purpose.strip().lower() == "all" else {
        s.strip() for s in args.purpose.split(",") if s.strip()}

    counts = {name: read_prompt_hashes(path, purposes) for name, path in arms}
    out: dict = {
        "purpose": "all" if purposes is None else sorted(purposes),
        "arms": {name: {"path": path, "calls": sum(c.values()), "unique": len(c)}
                 for name, (c, (n, path)) in
                 {n: (counts[n], (n, p)) for n, p in arms}.items()},
        "pairs": [],
    }
    for i in range(len(arms)):
        for j in range(i + 1, len(arms)):
            na, nb = arms[i][0], arms[j][0]
            res = compare(counts[na], counts[nb])
            res.update({"first": na, "second": nb})
            out["pairs"].append(res)

    text = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.out_json:
        Path(args.out_json).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
