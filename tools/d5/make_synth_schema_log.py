#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「D2 风格（explicit schema）」合成日志，用于验证指标脚本在 thread_id/reply_to/ctx 下的行为。

为什么需要：D2 落地后事件结构从 legacy 变为 explicit。若指标脚本在 explicit 分支上有 bug，
要等几小时后真日志回来才发现，代价很大。本脚本用**完全虚构**的 4 条消息造一份确定性日志，
配合 `--assert` 自检关键读数（线程数、turns_A、B_roundtrips、指针分类、cont_same_topic），
把风险提前清掉。

用法：
    python3 tools/d5/make_synth_schema_log.py --out-dir v2/evidence/d5_synth_schema_test --assert

输出：`run.jsonl` / `meta.json` / `synth_assert.json`（含断言明细与两侧 sha256）。
注意：本日志**仅用于脚本自检**，不含任何真实 LLM 调用，**不得**计入任何指标读数或报告数据。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

MSG_PLACE = "cafe"
THREAD = "TH-P001-P002-0"


def _h(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def build() -> List[Dict[str, Any]]:
    recs: List[Dict[str, Any]] = []
    prev = "sha256:" + "0" * 64

    def add(type_: str, payload: Dict[str, Any], seq: int, rnd: int = 0, actor: str = "P001") -> None:
        nonlocal prev
        h = _h(f"{type_}:{seq}")
        recs.append({"type": type_, "payload": payload, "seq": seq, "round": rnd,
                     "actor": actor, "hash": h, "prev_hash": prev, "mono_ts": seq})
        prev = h

    add("WORLD_INIT", {"seed": 42}, 0)
    msgs = [
        ("P001", "P002", "你昨天说的那个集市，今天还开吗？", 0, None,
         {"topic": "集市", "relation": 3, "mood": "calm", "need": {"social": 2}}),
        ("P002", "P001", "开着呢，我刚从那儿回来。你要买什么？", 1, "D-0-P001-0",
         {"topic": "集市", "relation": 3, "mood": "happy", "need": {"social": 2}}),
        ("P001", "P002", "想给老周带块糕，他昨天帮了我大忙。", 2, "D-0-P002-1",
         {"topic": "送糕", "relation": 3, "mood": "warm", "need": {"social": 1}}),
        ("P002", "P001", "那你去东头那家，秀娘的糕最实在。", 3, "D-0-P001-2",
         {"topic": "送糕", "relation": 3, "mood": "calm", "need": {"social": 1}}),
    ]
    seq = 1
    for f, t, body, ti, reply_to, ctx in msgs:
        add("MSG_DM", {"from": f, "to": t, "body": body, "msg_id": f"D-0-{f}-{ti}",
                       "thread_id": THREAD, "turn_index": ti, "reply_to": reply_to,
                       "participants": ["P001", "P002"], "ctx": ctx,
                       "day": 0, "slot": "morning", "place": MSG_PLACE,
                       "tag_hints": ["ice_break"] if ti == 0 else ["rel_maintain"]}, seq)
        seq += 1
    add("TURN_SEAL", {"money_supply": 1000, "state_hash": "sha256:synth"}, seq, 0, "SYSTEM")
    add("LLM_CALL", {"purpose": "dialogue", "provider": "openai_compat", "model": "DeepSeek-Flash",
                     "tokens_in": 100, "tokens_out": 20, "cached": False, "degraded": False},
        seq + 1, 0, "SYSTEM")
    return recs


EXPECTED = {
    "thread_schema": "explicit",
    "n_threads": 1,
    "turns_A": 4,
    "B_roundtrips": 3,
    "chain_by_alternation": 4,
    "ptr_ok": 3,
    "ptr_dangling": 0,
    "ptr_cross_thread": 0,
    "reply_pointer_rate": 1.0,
    "cont_same_topic": 2 / 3,
    "single_msg_thread_ratio": 0.0,
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="生成 D2 风格合成日志并自检指标脚本")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--assert", dest="do_assert", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    recs = build()
    run_path = os.path.join(args.out_dir, "run.jsonl")
    meta_path = os.path.join(args.out_dir, "meta.json")
    with open(run_path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta = {"provider": "openai_compat", "model_requested": "DeepSeek-Flash", "seed": 42,
            "n": 2, "rounds": 1, "rounds_effective": 1, "rounds_per_slot_effective": "3",
            "code_sha": "SYNTH-NOT-A-REAL-RUN", "git_dirty_files": [],
            "events": len(recs), "msg_counts": {"MSG_DM": 4, "MSG_PUBLIC": 0, "MSG_GROUP": 0},
            "llm_calls": 1, "degraded_calls": 0, "mock_precalib_msg_count": 4,
            "batch_status": "synthetic", "started_at": "synthetic", "finished_at": "synthetic",
            "note": "合成日志，仅用于指标脚本 explicit-schema 自检；不得计入任何读数或报告数据"}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
        f.write("\n")

    tools = os.path.dirname(os.path.abspath(__file__))
    metrics = os.path.join(tools, "dialogue_metrics.py")
    out_json = os.path.join(args.out_dir, "synth_metrics.json")
    out_md = os.path.join(args.out_dir, "synth_metrics.md")
    subprocess.run([sys.executable, metrics, "--log", run_path, "--meta", meta_path,
                    "--out-json", out_json, "--out-md", out_md], check=True,
                   stdout=subprocess.DEVNULL)

    m = json.load(open(out_json, encoding="utf-8"))
    actual = {
        "thread_schema": m["meta"]["thread_schema"],
        "n_threads": m["meta"]["n_threads"],
        "turns_A": m["S-1_turns_per_thread"]["A_speaker_turns"]["max"],
        "B_roundtrips": m["S-1_turns_per_thread"]["B_roundtrips"]["max"],
        "chain_by_alternation": m["S-3_longest_chain"]["chain_by_alternation"]["max"],
        "ptr_ok": m["S-4_reply_pointer_coverage"]["ptr_ok"],
        "ptr_dangling": m["S-4_reply_pointer_coverage"]["ptr_dangling"],
        "ptr_cross_thread": m["S-4_reply_pointer_coverage"]["ptr_cross_thread"],
        "reply_pointer_rate": m["S-4_reply_pointer_coverage"]["rate"],
        "cont_same_topic": m["K-1_topic_continuation"]["cont_same_topic"],
        "single_msg_thread_ratio": m["S-2_thread_scale"]["single_msg_thread_ratio"],
    }
    checks = []
    ok_all = True
    for k, want in EXPECTED.items():
        got = actual[k]
        ok = (abs(float(got) - float(want)) < 1e-6) if isinstance(want, float) and isinstance(got, (int, float)) else (got == want)
        ok_all = ok_all and ok
        checks.append({"metric": k, "expected": want, "actual": got, "pass": bool(ok)})
    res = {
        "schema_version": "d5-synth-schema-test/1.0",
        "purpose": "验证 dialogue_metrics.py 在 explicit schema（thread_id/turn_index/reply_to/ctx）下行为正确",
        "inputs": {
            "run_jsonl": run_path, "run_sha256": _h(open(run_path, encoding="utf-8").read()),
            "run_sha8": _h(open(run_path, encoding="utf-8").read())[7:15],
            "meta_json": meta_path,
            "metrics_script_sha256": _h(open(metrics, encoding="utf-8").read()),
        },
        "warning": "合成日志，不含真实 LLM 调用，不得计入任何读数/报告数据",
        "checks": checks,
        "all_pass": ok_all,
    }
    res_path = os.path.join(args.out_dir, "synth_assert.json")
    with open(res_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"all_pass": ok_all, "run_sha8": res["inputs"]["run_sha8"],
                      "out": res_path}, ensure_ascii=False, indent=1))
    if args.do_assert and not ok_all:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
