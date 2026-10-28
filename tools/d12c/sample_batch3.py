#!/usr/bin/env python3
"""sample_batch3.py — D12-C 第三批抽样（方案 A：同臂、只用 4–6 轮层、12 条）

背景（leader 2026-10-28 裁决 A）：
  `run_a5_real_n16r42_seed42` 共 140 线程：1 轮 55 / 2–3 轮 8 / 4–6 轮 77；
  batch1 用 12、batch2 用 12 ⇒ **剩余 2–3 轮 = 0**（该层 8 条已被两批吃干）、剩余 4–6 轮 = 61。
  故本批 12 条**全部取自 4–6 轮层**，不再声明"与 batch2 同构"。

为什么否 B（换数据源）：别的臂是另一棵树/另一套配置期望，换臂后 κ 变动的解释有两个
（判据改了 + 臂改了），无法归因；**验证判据必须只动一个变量：判据**。
为什么否 C（放宽层定义）：事后改判据适用域，正是本轮反对的事。

抽样口径（可复算）
  - turns   = 线程内**唯一 turn_index 数**
  - 池       = turns ∈ [4,6] 且 thread_id ∉ (batch1 ∪ batch2)
  - 随机     = thread_id 升序排序 → `random.Random(SEED).shuffle` → 取前 N
  - SEED     = 42
  - N        = 12

输出
  - `v2/evidence/d12c_batch3_sampled_raw.txt`：**只含原文与 thread_id**，无任何档位/判读
  - 文件头写死 leader 指定的限制段（原样）

用法
  python3 tools/d12c/sample_batch3.py            # 生成（默认路径）
  python3 tools/d12c/sample_batch3.py --dry-run  # 只打印池与抽样结果，不写文件
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import re
from pathlib import Path

RUN = "v2/evidence/run_a5_real_n16r42_seed42/run.jsonl"
BATCH1_RAW = "v2/evidence/d12c_a5_sampled_threads_raw.txt"
BATCH2_RAW = "v2/evidence/d12c_a5_batch2_sampled_threads_raw.txt"
OUT = "v2/evidence/d12c_batch3_sampled_raw.txt"
SEED = 42
N = 12

HEADER_LIMITATION = (
    "本批无 2–3 轮样本（该层在本臂共 8 条、已由 batch1/batch2 全部用尽）"
    "⇒ **本批 κ 不能与 batch2 的 κ 直接对比**；且 v3 的短线程 C 判据在本臂上"
    "**永远无法用盲评 κ 验证**，需另跑一批（不同 seed 或不同规模）方可验证。"
)


def ids_of(path: str) -> set[str]:
    txt = Path(path).read_text(encoding="utf-8")
    return set(re.findall(r"thread=(TH-[A-Za-z0-9-]+)", txt))


def load_threads(run: str):
    th: dict[str, list] = collections.defaultdict(list)
    with open(run, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if not str(r.get("type", "")).startswith("MSG_"):
                continue
            pl = r.get("payload") or {}
            tid = pl.get("thread_id")
            if tid:
                th[tid].append((r.get("round"), r.get("seq"), pl))
    return th


def turns_of(items) -> int:
    return len({p.get("turn_index") for _, _, p in items if isinstance(p.get("turn_index"), int)})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=RUN)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--n", type=int, default=N)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    th = load_threads(a.run)
    b1, b2 = ids_of(BATCH1_RAW), ids_of(BATCH2_RAW)
    excl = b1 | b2
    print(f"[pool] threads={len(th)}  batch1={len(b1)} batch2={len(b2)} exclude={len(excl)}")
    for lo, hi, label in ((1, 1, "1 轮"), (2, 3, "2–3 轮"), (4, 6, "4–6 轮")):
        pool = [t for t in th if lo <= turns_of(th[t]) <= hi]
        left = [t for t in pool if t not in excl]
        print(f"       {label}: 共 {len(pool)}，排除后剩 {len(left)}")

    pool46 = sorted(t for t in th if 4 <= turns_of(th[t]) <= 6 and t not in excl)
    if len(pool46) < a.n:
        print(f"[FAIL] 4–6 轮层可用仅 {len(pool46)} 条 < {a.n}，方案 A 不可执行")
        return 2
    rng = random.Random(a.seed)
    rng.shuffle(pool46)
    pick = pool46[: a.n]
    print(f"[pick] seed={a.seed} n={a.n} 从 {len(pool46)} 条中取: {pick}")
    if a.dry_run:
        return 0

    lines = [
        f"batch3 sampled threads: {len(pick)}（方案 A：全部取自 4–6 轮层；seed={a.seed}；exclude=batch1∪batch2 共 {len(excl)} 个 thread_id）",
        "=" * 88,
        f"【限制·原样写死】{HEADER_LIMITATION}",
        "=" * 88,
    ]
    for i, t in enumerate(pick, 1):
        items = sorted(th[t], key=lambda x: (x[0] if x[0] is not None else -1, x[1] if x[1] is not None else -1))
        rs = [r for r, _, _ in items]
        lines.append(f"[#{i}] thread={t} 轮数={turns_of(th[t])}  rounds={min(rs)}->{max(rs)} type=MSG_DM")
        for r, _s, pl in items:
            lines.append(f"  [r{r} turn={pl.get('turn_index')}] {pl.get('from')}->{pl.get('to')}: {pl.get('body')}")
        lines.append("=" * 88)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[write] {out} ({out.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
