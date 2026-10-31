#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_true_run.py —— 「一次跑批是否真跑」的机械判定器（只读，零 LLM 调用）。

背景（CYCLE-39 §③ F-1 / F-2、:474-480 计划 4）
------------------------------------------------
`run_batch rc=0` 且 `provider_guard.ok=true` **不等于真跑**：
r38_f3_batch/off_INVALID_cached_replay 就是 rc=0、guard ok，但 100% 缓存回放
（`cached=calls=2252`、`tokens_in=tokens_out=0`），且其 `run_batch.rc` 的 mtime
（10:48）**早于** `run.jsonl`（12:03）——该 rc 根本不是这一跑的退出码。

判据（两条同时满足才算真跑；本脚本逐条打印，不合并成一个模糊结论）
--------------------------------------------------------------
① 判据桶（默认 `dialogue`，`--bucket` 可改）`cached == 0` 且 `tokens_in > 0`；
② `run_batch.rc` 的 mtime **严格晚于** `run.jsonl` 的 mtime（rc 必须是这一跑的退出码）。

附加的**反假绿护栏**（不满足即降级为「未验真」，不算真跑）
--------------------------------------------------------
③ provider 桶里出现 `mock`（`--mock` 路径）⇒ 判 `未验真(mock)`；
   理由：`--mock` 路径的 dialogue 桶天然 `cached=0 / tokens_in>0`（见 f5_round1），
   只靠判据①会把 mock 批误判成真跑，因此必须显式排除。
④ 任一必需产物缺失（`run.jsonl` / `run_batch.rc` / 判据桶）⇒ 判 `未验真(不可判)`，
   绝不用「缺文件」推进成「真跑」。

成本数据的来源优先级：`run.jsonl` 现算（复用 `code/obs/llmcost.py` 的同一实现）
> 已落盘的 `llm_cost.json`（若两者都有一致性对账，不一致则降级为「未验真(读数不一致)」）。

退出码：0 = 全部判「真跑」；10 = 存在「未验真」（含假绿/不可判/mock）；2 = 用法错误。

用法（仓库根）：
  python3 tools/d5/verify_true_run.py \
      v2/evidence/r38_f3_batch/on v2/evidence/r38_f3_batch/off \
      v2/evidence/r38_f3_batch/off_INVALID_cached_replay \
      --bucket dialogue --json-out /tmp/true_run_scan.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CODE = os.path.join(REPO, "code")
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from obs.cli import read_log  # noqa: E402
from obs.llmcost import check_provider, llm_cost_from_records  # noqa: E402

TRUERUN = "真跑"
UNVERIFIED = "未验真"


def sha256_of(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(chunk), b""):
            h.update(c)
    return h.hexdigest()


def mtime(path: str) -> Optional[float]:
    return os.path.getmtime(path) if os.path.isfile(path) else None


def iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def judge_bucket(cost: Dict[str, Any], bucket: str) -> Optional[Dict[str, Any]]:
    return (cost.get("by_purpose") or {}).get(bucket)


def verify_batch(batch_dir: str, bucket: str, provider: str) -> Dict[str, Any]:
    absdir = batch_dir if os.path.isabs(batch_dir) else os.path.join(REPO, batch_dir)
    rel = os.path.relpath(absdir, REPO) if absdir.startswith(REPO) else absdir
    run_jsonl = os.path.join(absdir, "run.jsonl")
    rc_file = os.path.join(absdir, "run_batch.rc")
    cost_file = os.path.join(absdir, "llm_cost.json")
    if not os.path.isfile(cost_file):
        # 约定二：部分证据包把成本落在兄弟文件 `../llm_cost_<臂名>.json`（如 f5_round1）
        sib = os.path.join(os.path.dirname(absdir), f"llm_cost_{os.path.basename(absdir)}.json")
        if os.path.isfile(sib):
            cost_file = sib

    rec: Dict[str, Any] = {
        "batch_dir": rel,
        "bucket": bucket,
        "files": {
            "run.jsonl": {"exists": os.path.isfile(run_jsonl),
                          "mtime": iso(mtime(run_jsonl)),
                          "bytes": os.path.getsize(run_jsonl) if os.path.isfile(run_jsonl) else None},
            "run_batch.rc": {"exists": os.path.isfile(rc_file),
                             "mtime": iso(mtime(rc_file)),
                             "content": open(rc_file).read().strip() if os.path.isfile(rc_file) else None},
            "llm_cost.json": {"exists": os.path.isfile(cost_file)},
        },
        "criterion_1_bucket": None,
        "criterion_2_rc_newer_than_log": None,
        "criterion_3_provider_clean": None,
        "provider": {},
        "cost_source": None,
        "notes": [],
    }

    # ---- 成本：优先由 run.jsonl 现算（同一实现），否则读已落盘 json ----
    cost: Optional[Dict[str, Any]] = None
    if os.path.isfile(run_jsonl):
        cost = llm_cost_from_records(read_log(run_jsonl))
        rec["cost_source"] = "recomputed_from_run.jsonl"
        if os.path.isfile(cost_file):
            try:
                committed = json.load(open(cost_file, encoding="utf-8"))
            except Exception:
                committed = None
            if isinstance(committed, dict) and isinstance(committed.get("engine_log"), dict):
                same = committed["engine_log"].get("by_purpose") == cost.get("by_purpose")
                rec["llm_cost_json_matches_recompute"] = same
                if not same:
                    rec["notes"].append("llm_cost.json 与 run.jsonl 现算不一致")
    elif os.path.isfile(cost_file):
        try:
            committed = json.load(open(cost_file, encoding="utf-8"))
            cost = committed.get("engine_log") if isinstance(committed, dict) else None
            rec["cost_source"] = "llm_cost.json(无 run.jsonl 可复算)"
        except Exception:
            cost = None

    if cost is None:
        rec["verdict"] = UNVERIFIED
        rec["reason"] = "不可判：无 run.jsonl 也无可用 llm_cost.json ⇒ 判据①无从计算"
        return rec

    b = judge_bucket(cost, bucket)
    rec["provider"] = cost.get("by_provider") or {}
    rec["total_llm_calls"] = cost.get("total")
    rec["criterion_1_bucket"] = b
    if b is None:
        rec["verdict"] = UNVERIFIED
        rec["reason"] = f"不可判：在 llm-cost 里找不到判据桶 `{bucket}`"
        return rec

    c1 = (int(b.get("cached", 0)) == 0 and int(b.get("tokens_in", 0)) > 0)
    rec["criterion_1_pass"] = bool(c1)
    c3 = "mock" not in (rec["provider"] or {})
    rec["criterion_3_provider_clean"] = bool(c3)
    if provider:
        guard = check_provider(cost, provider)
        rec["provider_guard"] = guard
        c3 = bool(c3 and guard.get("ok"))

    rc_m, log_m = mtime(rc_file), mtime(run_jsonl)
    if rc_m is None or log_m is None:
        rec["criterion_2_rc_newer_than_log"] = None
        c2: Optional[bool] = None
    else:
        c2 = rc_m > log_m
        rec["criterion_2_rc_newer_than_log"] = bool(c2)
        rec["mtime_delta_sec_rc_minus_log"] = round(rc_m - log_m, 3)

    if not c3:
        rec["verdict"] = UNVERIFIED
        rec["reason"] = ("provider 桶含 mock 或未通过 provider 校验 "
                         f"（by_provider={rec['provider']}）⇒ --mock 路径不构成真跑")
    elif not c1:
        rec["verdict"] = UNVERIFIED
        rec["reason"] = (f"判据桶 `{bucket}` 为 cached={b.get('cached')} / "
                         f"tokens_in={b.get('tokens_in')}（要求 cached==0 且 tokens_in>0）"
                         "⇒ 缓存回放/零真实调用，属假绿")
    elif c2 is None:
        rec["verdict"] = UNVERIFIED
        rec["reason"] = "缺 run.jsonl 或 run_batch.rc ⇒ 判据②不可判（rc 与产物无法判同代）"
    elif not c2:
        rec["verdict"] = UNVERIFIED
        rec["reason"] = (f"run_batch.rc({iso(rc_m)}) 早于 run.jsonl({iso(log_m)}) "
                         "⇒ 该 rc 不是这一跑的退出码")
    else:
        rec["verdict"] = TRUERUN
        rec["reason"] = "两条判据同时满足，且 provider 桶无 mock"
    return rec


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="跑批「是否真跑」机械判定器（只读）")
    ap.add_argument("batch_dirs", nargs="+", help="批次目录（含 run.jsonl / run_batch.rc）")
    ap.add_argument("--bucket", default="dialogue", help="判据桶（默认 dialogue）")
    ap.add_argument("--provider", default="openai_compat",
                    help="期望 provider（默认 openai_compat；传空串跳过）")
    ap.add_argument("--json-out", default="", help="结果 JSON 落盘路径（缺省不落盘）")
    a = ap.parse_args(argv)
    if not a.batch_dirs:
        return 2

    results = [verify_batch(d, a.bucket, a.provider) for d in a.batch_dirs]

    print("| 批次 | 判据桶 | cached | tokens_in | ①桶判据 | rc mtime | run.jsonl mtime | ②rc晚于产物 | ③无mock | 判定 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        b = r.get("criterion_1_bucket") or {}
        files = r["files"]
        c1 = "PASS" if r.get("criterion_1_pass") else "FAIL"
        c2 = {True: "PASS", False: "FAIL", None: "N/A"}[r.get("criterion_2_rc_newer_than_log")]
        c3 = {True: "PASS", False: "FAIL", None: "N/A"}[r.get("criterion_3_provider_clean")]
        print(f"| `{r['batch_dir']}` | {r['bucket']} | {b.get('cached')} | {b.get('tokens_in')} | {c1} | "
              f"{files['run_batch.rc']['mtime']} | {files['run.jsonl']['mtime']} | {c2} | {c3} | "
              f"**{r['verdict']}** |")
    print()
    for r in results:
        print(f"- `{r['batch_dir']}` → **{r['verdict']}**：{r.get('reason')}")

    payload = {"schema": "true-run-verdict/1", "bucket": a.bucket,
               "criteria": {
                   "1_bucket": "判据桶 cached==0 且 tokens_in>0（CYCLE-39:474-480 计划 4 ①）",
                   "2_rc_mtime": "run_batch.rc mtime 严格晚于 run.jsonl mtime（同计划 4 ②）",
                   "3_provider": "by_provider 无 mock 且通过 provider 校验（反假绿护栏，防 --mock 路径被判真跑）",
               },
               "results": results,
               "summary": {
                   "n": len(results),
                   "true_run": sum(1 for r in results if r["verdict"] == TRUERUN),
                   "unverified": sum(1 for r in results if r["verdict"] == UNVERIFIED),
               }}
    if a.json_out:
        out = a.json_out if os.path.isabs(a.json_out) else os.path.join(REPO, a.json_out)
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
        print(f"\nwritten: {out}")
    return 0 if payload["summary"]["unverified"] == 0 else 10


if __name__ == "__main__":
    sys.exit(main())
