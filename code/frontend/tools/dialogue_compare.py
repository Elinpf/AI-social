#!/usr/bin/env python3
"""dialogue_compare.py — 两个 threads.json 的同结构对照表（每个比率都带分母）。

用途：口径统一、可复算。输出 markdown 表，可直接粘进报告 / D6 / D8。

用法：
    cd code
    python frontend/tools/dialogue_compare.py \\
        --a frontend/sample/dialogue_v0anchor_n16_seed42/threads.json \\
        --b frontend/sample/dialogue_run_d2_after_n16_seed42/threads.json \\
        --label-a "改造前 v0-anchor" --label-b "改造后 A0"

判定口径（与页面、L-13 一致，均可由数据文件复算）：
  * 多轮率        = 多轮线程数 / 线程数
  * ≥3 轮率       = ≥3 条线程数 / 线程数
  * ctx 覆盖率    = 带 payload.ctx 的消息数 / 消息数
  * leak（L-13）  = 正文中出现自身 ctx.topic 原字符串的消息数 / 消息数
  * 最长线程      = 消息条数最多的一条；同时给 turn_index 去重后的回合数
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(p: Path) -> dict:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def leak_count(d: dict) -> tuple[int, list[int]]:
    hits = []
    for t in d.get("threads", []):
        for m in t.get("messages", []):
            topic = (m.get("ctx") or {}).get("topic")
            body = m.get("body") or ""
            if topic and str(topic) in body:
                hits.append(m.get("seq"))
    return len(hits), hits


def ctx_count(d: dict) -> int:
    return sum(1 for t in d.get("threads", []) for m in t.get("messages", []) if m.get("ctx"))


def distinct_turns(t: dict) -> int | None:
    s = {m.get("turn_index") for m in t.get("messages", []) if m.get("turn_index") is not None}
    return len(s) or None


def longest(d: dict) -> dict:
    ts = d.get("threads") or []
    if not ts:
        return {}
    t = max(ts, key=lambda x: x.get("turns") or 0)
    tid = t.get("thread_id") or ("legacy:" + str(((t.get("messages") or [{}])[0]).get("seq")))
    return {"thread_id": tid, "messages": t.get("turns"),
            "distinct_turns": distinct_turns(t), "channel": t.get("channel"),
            "place": t.get("place"), "participants": t.get("participants"),
            "turn_index_counts": _turn_counts(t)}


def _turn_counts(t: dict) -> dict:
    c: dict = {}
    for m in t.get("messages", []):
        k = m.get("turn_index")
        if k is None:
            continue
        c[k] = c.get(k, 0) + 1
    return dict(sorted(c.items()))


def rate(n: int, d: int) -> str:
    return f"{n}/{d} ({n / d * 100:.1f}%)" if d else f"{n}/0 (N/A)"



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    a = ap.parse_args()

    da, db = load(Path(a.a)), load(Path(a.b))
    sa, sb = da.get("stats") or {}, db.get("stats") or {}
    la, la_seq = leak_count(da)
    lb, lb_seq = leak_count(db)
    ca, cb = ctx_count(da), ctx_count(db)
    ma, mb = sa.get("messages") or 0, sb.get("messages") or 0
    ta, tb = sa.get("threads") or 0, sb.get("threads") or 0

    print("| 维度 | %s | %s | 口径（分子/分母） |" % (a.label_a, a.label_b))
    print("|---|---|---|---|")
    print(f"| 数据集 run_label | `{da.get('source', {}).get('run_label')}` | `{db.get('source', {}).get('run_label')}` | 自动派生（批次名+sha8） |")
    print(f"| 日志 run_sha256 | `{da.get('source', {}).get('run_sha256')}` | `{db.get('source', {}).get('run_sha256')}` | 日志字节 sha |")
    print(f"| 事件数 | {da.get('source', {}).get('events_total_in_log')} | {db.get('source', {}).get('events_total_in_log')} | 日志行数 |")
    print(f"| 线程格式 | `{da.get('thread_schema')}` | `{db.get('thread_schema')}` | 有 thread_id ⇒ explicit |")
    print(f"| 消息数 | {ma} | {mb} | MSG_* 条数 |")
    print(f"| 线程数 | {ta} | {tb} | 按 thread_id 聚合（旧格式每条单发） |")
    print(f"| 多轮线程 | {rate(sa.get('multi_turn_threads') or 0, ta)} | {rate(sb.get('multi_turn_threads') or 0, tb)} | 多轮线程/线程数（≥2 条） |")
    print(f"| ≥3 条线程 | {rate(sa.get('threads_ge3_turns') or 0, ta)} | {rate(sb.get('threads_ge3_turns') or 0, tb)} | ≥3 条/线程数 |")
    print(f"| 最长线程（条/去重轮） | {sa.get('max_turns')} 条 | {sb.get('max_turns')} 条 | 消息条数；去重轮见下方样本 |")
    print(f"| ctx 覆盖 | {rate(ca, ma)} | {rate(cb, mb)} | 带 payload.ctx 的消息/消息数 |")
    print(f"| **leak（L-13）** | **{la}/{ma}** | **{lb}/{mb}** | 正文含自身 ctx.topic 原串/消息数 |")
    print()
    print(f"**leak 命中 seq（{a.label_a}）**：{la_seq[:20]}{' …' if len(la_seq) > 20 else ''}")
    print(f"**leak 命中 seq（{a.label_b}）**：{lb_seq[:20]}{' …' if len(lb_seq) > 20 else ''}")
    print()
    for label, d in ((a.label_a, da), (a.label_b, db)):
        lg = longest(d)
        if not lg:
            print(f"- **最长线程（{label}）**：无对话")
            continue
        print(f"- **最长线程（{label}）**：`{lg['thread_id']}` — {lg['messages']} 条"
              f"{' / ' + str(lg['distinct_turns']) + ' 轮（turn_index 去重）' if lg['distinct_turns'] else ''}"
              f" ｜ 渠道 `{lg['channel']}` ｜ 地点 {lg['place']} ｜ 参与者 {len(lg['participants'] or [])} 人"
              f" ｜ turn_index 分布 {lg['turn_index_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
