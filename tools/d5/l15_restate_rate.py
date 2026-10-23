#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L-15 复述率（restate rate）——把「多轮里有多少条在重复前文」做成可复算指标。

## 为什么要有它（指标盲点，2026-10-23 由用户质疑触发）

项目里所有"多轮/承接"指标都能被**复述**满足，因而证明不了"有逻辑"：

| 已有指标 | 它能证明什么 | 它**不能**证明什么 |
|---|---|---|
| `is_reply` / `S-4` 指针覆盖（100%） | 这条消息**指向**了前一条 | 指的是前一条，说的是同一件事 |
| `K-1 cont_lexical`（≈0.99） | 前后两条**共享词汇** | 共享的是新信息，还是把旧话又说一遍 |
| 线程轮数 `p50` | 聊了 N 条 | N 条里有几条在推进 |
| `L-7` 8-gram 近重复 | 跨消息共享片段的**总量** | 共享发生在**第几轮**、是否只发生在同一条线程内 |

⇒ 用户看页面时的直觉是："越往后越像在原地打转"。本指标就是把这句话变成数字。

## 定义（**冻结，不得在跑批中途修改**）

- 分母 = 该批全部 `MSG_*`（`MSG_DM` / `MSG_PUBLIC` / `MSG_GROUP`）；
- 逐线程（`thread_id`）按 `(turn_index, seq)` 升序累计 `seen` 8-gram 集合；
- 对每条消息：`sh = {t[i:i+8]}`（`t = normalize_body(body)`，**与 `L-7` / D5 完全同口径，不自创**）；
- **`restate`**：`sh ∩ seen ≠ ∅` 即记 1（它与**本线程前文**共享了至少一个 8-gram 片段）；
- **`restate_strong`**：`|sh ∩ seen| ≥ 3` 才记 1（更严：共享 3 条以上，通常意味着整句复用）；
- `restate_rate = 100 × Σrestate / n`；`restate_strong_rate` 同理；
- **`by_turn`**：按 `turn_index + 1` 分层给上述两个率（这是本指标最有用的部分：看**从第几轮开始打转**）；
- `top_shared`：被复用次数最多的 8-gram（人工抽样时可据此找"骨架"）。

> 注意：`restate` 是**同线程内**的前向引用（只看该线程更早的消息），因此**不会被跨线程的正常重复污染**。

## 用法

    python3 tools/d5/l15_restate_rate.py \
        --run v0=v2/evidence/run_d2_before_n16_seed42/run.jsonl \
        --run A5=v2/evidence/run_a5_real_n16r42_seed42/run.jsonl \
        --run D12C_ON=v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
        --out-json v2/evidence/l15_restate_baselines.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from dialogue_metrics import normalize_body  # noqa: E402  （冻结实现，8-gram 口径同源）

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
NGRAM = 8
STRONG = 3


def shingles(text: str) -> set[str]:
    t = normalize_body(text)
    return {t[i:i + NGRAM] for i in range(max(0, len(t) - (NGRAM - 1)))} if t else set()


def analyze(path: str) -> dict:
    threads: dict[str, list[dict]] = defaultdict(list)
    n = 0
    missing_tid = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") not in MSG_TYPES:
                continue
            p = e.get("payload") or {}
            tid = p.get("thread_id")
            if not tid:
                missing_tid += 1
                tid = f"__notid__{p.get('msg_uid') or n}"
            threads[tid].append(p)
            n += 1

    by_turn: dict[int, dict[str, int]] = defaultdict(lambda: {"n": 0, "restate": 0, "strong": 0})
    shared_counter: Counter[str] = Counter()
    tot_restate = tot_strong = 0

    for _tid, msgs in threads.items():
        msgs.sort(key=lambda m: (m.get("turn_index") or 0, m.get("seq") or 0))
        seen: set[str] = set()
        for m in msgs:
            sh = shingles(m.get("body") or "")
            inter = sh & seen
            turn = (m.get("turn_index") or 0) + 1
            by_turn[turn]["n"] += 1
            if inter:
                tot_restate += 1
                by_turn[turn]["restate"] += 1
                for g in inter:
                    shared_counter[g] += 1
            if len(inter) >= STRONG:
                tot_strong += 1
                by_turn[turn]["strong"] += 1
            seen |= sh

    rate = lambda a, b: round(100 * a / b, 2) if b else None  # noqa: E731
    # 硬边界：无 thread 元数据的批（如 v0）不能算本指标 —— 否则会把"全批任意共享"
    # 误当成"同线程前向复述"（2026-10-23 v0 误算 33.69% 即此故，已作废）。
    if missing_tid:
        return {
            "n_msgs": n,
            "thread_meta_missing": missing_tid,
            "verdict": "NOT_APPLICABLE",
            "reason": f"{missing_tid}/{n} 条消息缺 thread_id ⇒ 无法确定线程边界，"
                      f"任何 restate 数值都会把跨线程共享误算成同线程复述 ⇒ 本批不可算",
            "rule": {"denominator": "全部 MSG_*",
                     "restate": "与本线程更早消息共享 ≥1 个 8-gram",
                     "restate_strong": f"共享 ≥{STRONG} 个 8-gram",
                     "ngram": f"normalize_body + {NGRAM}-gram（与 L-7 同口径）",
                     "scope": "同线程内前向引用（不跨线程）"},
        }
    return {
        "n_msgs": n,
        "thread_meta_missing": 0,
        "restate_rate": rate(tot_restate, n),
        "restate_strong_rate": rate(tot_strong, n),
        "by_turn": {
            str(t): {
                "n": v["n"],
                "restate_rate": rate(v["restate"], v["n"]),
                "restate_strong_rate": rate(v["strong"], v["n"]),
            }
            for t, v in sorted(by_turn.items())
        },
        "top_shared": [[g, c] for g, c in shared_counter.most_common(8)],
        "rule": {
            "denominator": "全部 MSG_*",
            "restate": "与本线程更早消息共享 ≥1 个 8-gram",
            "restate_strong": f"共享 ≥{STRONG} 个 8-gram",
            "ngram": f"normalize_body + {NGRAM}-gram（与 L-7 同口径）",
            "scope": "同线程内前向引用（不跨线程）",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="arm=path，可多次")
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    out = {}
    for spec in a.run:
        arm, _, path = spec.partition("=")
        out[arm] = analyze(path)
        r = out[arm]
        if r.get("verdict") == "NOT_APPLICABLE":
            print(f"[{arm}] n={r['n_msgs']} **NOT_APPLICABLE**：{r['reason']}")
            continue
        print(f"[{arm}] n={r['n_msgs']} restate={r['restate_rate']}% "
              f"strong={r['restate_strong_rate']}% "
              f"by_turn={ {k: v['restate_rate'] for k, v in r['by_turn'].items()} }")
    Path(a.out_json).write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
