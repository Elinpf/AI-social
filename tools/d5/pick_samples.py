#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D6 样本挑选器（纯只读、零 LLM 调用）。

用途：从 run.jsonl 里**确定性**挑出报告需要的原文样本，避免临场手挑（手挑=选择性偏差）：
1. **最长 / 最短**线程（按消息条数、按 turns_A）；
2. **好 / 中 / 差**三档候选（按客观指标分档，分档规则写死、可复算）；
3. 每档给「线程 key + 消息 seq 列表 + 说话人 + 原文」，可直接贴进报告或喂给前端深链。

分档规则（写死，避免主观）：
- 每条线程计算 3 个 0/1 信号：`has_pointer`（线程内 ≥1 条 reply_to 非空）、
  `multi_turn`（turns_A ≥ 3）、`names_used`（线程内 ≥1 条正文出现对端 persona 主干名）。
- 档位 = 信号数：3 → 好；1–2 → 中；0 → 差。同档内按线程长度降序、key 升序取前 N（确定性）。
- 输出同时给「该线程的客观读数」：turns_A、条数、指针命中数、L-12 命中数，便于报告并排。

用法：
    python3 tools/d5/pick_samples.py --log <RUN>/run.jsonl --out-dir v2/evidence/samples_<tag> \
        --top 3 [--meta <RUN>/meta.json]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))


def load_dm():
    spec = importlib.util.spec_from_file_location("dm", os.path.join(HERE, "dialogue_metrics.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D6 原文样本挑选器（只读、零 LLM）")
    ap.add_argument("--log", required=True)
    ap.add_argument("--meta", default=None)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--top", type=int, default=3, help="每档取几条线程")
    args = ap.parse_args(argv)

    dm = load_dm()
    recs, parse = dm.read_run(args.log)
    msgs = dm.extract_messages(recs)
    if not msgs:
        print("[FAIL] 无消息事件", file=sys.stderr)
        return 2
    names, _ = dm.load_personas(dm.DEFAULT_PERSONAS)
    threads, schema = dm.group_threads(msgs)

    rows: List[Dict[str, Any]] = []
    for key in sorted(threads):
        th = threads[key]
        spk = [str(m["from"]) for m in th]
        turns = 1 + sum(1 for i in range(1, len(spk)) if spk[i] != spk[i - 1])
        ptr = sum(1 for m in th if (m.get("reply_to") or m.get("refs")))
        named = 0
        for m in th:
            peer = names.get(str(m.get("to")))
            if peer and peer in (m.get("body") or ""):
                named += 1
        # 指针链 vs 交替链（不一致 = reply_to 装配/语义可疑）
        best_alt = 1; cur = 1
        for i in range(1, len(spk)):
            if spk[i] != spk[i - 1]:
                cur += 1; best_alt = max(best_alt, cur)
            else:
                cur = 1
        by_uid = {}
        for i, m in enumerate(th):
            if m.get("msg_uid"):
                by_uid[m["msg_uid"]] = i
            if m["msg_id"]:
                by_uid.setdefault(m["msg_id"], i)
        depth = [1] * len(th)
        for i, m in enumerate(th):
            tgt = m.get("reply_to")
            if tgt and tgt in by_uid and by_uid[tgt] < i:
                depth[i] = depth[by_uid[tgt]] + 1
        best_ptr = max(depth) if depth else 0
        sig = (1 if ptr else 0) + (1 if turns >= 3 else 0) + (1 if named else 0)
        grade = "good" if sig == 3 else ("mid" if sig >= 1 else "bad")
        rows.append({
            "thread_key": key, "n_msgs": len(th), "turns_A": turns,
            "ptr_msgs": ptr, "peer_named_msgs": named, "signals": sig, "grade": grade,
            "chain_alternation": best_alt, "chain_pointer": best_ptr,
            "chain_mismatch": (best_alt - best_ptr),
            "messages": [{
                "seq": m.get("seq"), "round": m.get("round"), "channel": m["channel"],
                "msg_uid": m.get("msg_uid"), "from": m["from"], "to": m["to"],
                "reply_to": m.get("reply_to"),
                "speaker": names.get(str(m["from"]), str(m["from"])),
                "hearer": names.get(str(m["to"]), str(m["to"])) if m.get("to") else None,
                "body": m["body"], "tags": m["tags"], "place": m.get("place"), "slot": m.get("slot"),
                "day": m.get("day"),
            } for m in th],
        })

    def pick(key, n, reverse=False):
        return sorted(rows, key=lambda r: ((-r[key]) if not reverse else r[key], r["thread_key"]))[:n]

    out = {
        "schema_version": "d6-samples/1.0",
        "inputs": {"log": os.path.abspath(args.log), "log_sha256": dm.sha256_file(args.log),
                   "log_sha8": dm.sha256_file(args.log)[7:15],
                   "meta": os.path.abspath(args.meta) if args.meta else None,
                   "script_sha256": dm.sha256_file(os.path.abspath(__file__))},
        "grading_rule": {
            "signals": ["has_pointer", "multi_turn(turns_A>=3)", "names_used(对端名出现)"],
            "good": "3 信号全中", "mid": "1–2 个", "bad": "0 个",
            "order_in_grade": "线程长度降序 → thread_key 升序（确定性）",
            "warning": "这是**结构分档**，不等于「读起来自然」；自然度由 judge/人评给，样本表只做候选池",
        },
        "meta": {"n_messages": len(msgs), "n_threads": len(rows), "thread_schema": schema,
                 "grade_counts": {g: sum(1 for r in rows if r["grade"] == g) for g in ("good", "mid", "bad")}},
        "longest_by_msgs": pick("n_msgs", args.top),
        "shortest_by_msgs": pick("n_msgs", args.top, reverse=True),
        "longest_by_turns": pick("turns_A", args.top),
        "chain_mismatch": {
            "rule": "chain_alternation − chain_pointer ≥ 2 记不一致（指针链应覆盖说话人交替链）；无任何指针时标 not_applicable",
            "applicable": any(r["ptr_msgs"] for r in rows),
            "mismatch_threads": [r for r in sorted(rows, key=lambda r: (-r["chain_mismatch"], r["thread_key"]))
                                 if r["ptr_msgs"] and r["chain_mismatch"] >= 2][: max(args.top, 5)],
            "n_mismatch": sum(1 for r in rows if r["ptr_msgs"] and r["chain_mismatch"] >= 2),
            "n_threads_with_ptr": sum(1 for r in rows if r["ptr_msgs"]),
        },
        "grades": {g: [r for r in sorted(rows, key=lambda r: (-r["n_msgs"], r["thread_key"]))
                       if r["grade"] == g][: args.top] for g in ("good", "mid", "bad")},
    }
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, "samples.json")
    open(path, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    md = ["# D6 原文样本候选（结构分档，非自然度）\n",
          f"- 日志 `{out['inputs']['log']}` (sha8 `{out['inputs']['log_sha8']}`)",
          f"- 消息 {len(msgs)} / 线程 {len(rows)} / schema `{schema}`",
          f"- 分档：good={out['meta']['grade_counts']['good']} mid={out['meta']['grade_counts']['mid']} bad={out['meta']['grade_counts']['bad']}",
          f"- 规则：{json.dumps(out['grading_rule'], ensure_ascii=False)}\n"]
    for title, subset in (("最长线程", out["longest_by_msgs"]), ("最短线程", out["shortest_by_msgs"])):
        md.append(f"## {title}\n")
        for r in subset:
            md.append(f"### `{r['thread_key']}`（{r['n_msgs']} 条 / turns_A={r['turns_A']} / 指针 {r['ptr_msgs']} / 点名 {r['peer_named_msgs']}）")
            md.append("```text")
            for m in r["messages"]:
                md.append(f"[seq {m['seq']} r{m['round']} {m['slot']} {m['place']}] {m['speaker']} → {m['hearer']}: {m['body']}")
            md.append("```\n")
    cm = out["chain_mismatch"]
    md.append("## 指针链 vs 交替链 一致性（反例候选）\n")
    if not cm["applicable"]:
        md.append("**不适用**：本批无任何 `reply_to`（legacy 单发），该检查对 v0-anchor 无意义。\n")
    else:
        md.append(f"- 有指针线程数：{cm['n_threads_with_ptr']}；**不一致线程数：{cm['n_mismatch']}**（规则：`chain_alternation − chain_pointer ≥ 2`）")
        if cm["n_mismatch"] == 0:
            md.append("- **未发现不一致**（正面证据：`reply_to` 装配与说话人交替链一致）\n")
        for r in cm["mismatch_threads"]:
            md.append(f"### `{r['thread_key']}` 交替链 {r['chain_alternation']} vs 指针链 {r['chain_pointer']}（差 {r['chain_mismatch']}）")
            md.append("```text")
            for m in r["messages"]:
                md.append(f"[seq {m['seq']} reply_to={m['reply_to']}] {m['speaker']} → {m['hearer']}: {m['body']}")
            md.append("```\n")
    for g in ("good", "mid", "bad"):
        md.append(f"## 档位 `{g}`\n")
        for r in out["grades"][g]:
            md.append(f"### `{r['thread_key']}`（{r['n_msgs']} 条 / turns_A={r['turns_A']}）")
            md.append("```text")
            for m in r["messages"]:
                md.append(f"[seq {m['seq']} r{m['round']} {m['slot']} {m['place']}] {m['speaker']} → {m['hearer']}: {m['body']}")
            md.append("```\n")
    open(os.path.join(args.out_dir, "samples.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(json.dumps({"n_threads": len(rows), "grades": out["meta"]["grade_counts"],
                      "out_dir": args.out_dir}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
