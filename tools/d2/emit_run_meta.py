#!/usr/bin/env python3
"""从「跑批目录 + 实际生效配置」生成 meta.json，并做真跑判定（exit 非零 = 非真跑）。

为什么单独一个脚本：`python -m orchestration run` 链路（世界层）不写 meta.json，
而 `code/` 属冻结区，不宜为了落 meta 去改 run 链路。本脚本只**读**日志与配置。

**单一真源**：`provider` 只从运行期写入的 `LLM_CALL.payload.provider` 推导，
绝不采用命令行/人填声明（Leader 裁决：meta.provider 不是事实）。

断言（任一不满足 → 非零退出）：
  exit 2  run.jsonl 不存在
  exit 3  行数 != 事件条数（读不完整）
  exit 4  非真跑：LLM_CALL==0，或 provider 出现非 openai_compat，或 model 含 mock/空
  exit 5  日志内 spec 与声明不一致（仅当显式给 --seed/--n/--rounds 时才校验）
  * seed/n/rounds 的**权威值一律从日志派生**（WORLD_INIT.seed / AGENT_BORN 计数 / max(round)+1），
    命令行参数只用于交叉校验；不带参数也能生成 meta（用于「跑完补 meta」场景）。

用法：
  python3 tools/d2/emit_run_meta.py --run-dir v2/evidence/run_d2_before_n16_seed42 \
      --seed 42 --n 16 --rounds 84 [--mock-precalib-msg 190] [--mock] \
      [--started-at ...] [--finished-at ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=str(ROOT), text=True).strip()
    except Exception:
        return ""


def _rounds_per_slot() -> int | None:
    try:
        src = (CODE / "life" / "constants.py").read_text(encoding="utf-8")
        m = re.search(r'"ROUNDS_PER_SLOT":\s*(\d+)', src)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--n", type=int)
    ap.add_argument("--rounds", type=int)
    ap.add_argument("--mock-precalib-msg", type=int, default=0)
    ap.add_argument("--mock", action="store_true", help="本臂即 mock（跳过真跑判定）")
    ap.add_argument("--started-at", default=None)
    ap.add_argument("--finished-at", default=None)
    ap.add_argument("--duration-sec", type=int, default=None)
    a = ap.parse_args(argv)

    run_dir = (ROOT / a.run_dir).resolve() if not Path(a.run_dir).is_absolute() else Path(a.run_dir)
    run = run_dir / "run.jsonl"
    if not run.exists():
        print(f"[meta] run.jsonl 不存在: {run}", file=sys.stderr)
        return 2

    recs, bad_lines = [], 0
    with open(run, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                bad_lines += 1
    if bad_lines:
        print(f"[meta] FAIL: {bad_lines} 行不可解析", file=sys.stderr)
        return 3

    types = Counter(r["type"] for r in recs)
    llm = [r for r in recs if r["type"] == "LLM_CALL"]
    providers = Counter(r["payload"].get("provider") for r in llm)
    models = Counter(r["payload"].get("model") for r in llm)
    purposes = Counter(r["payload"].get("purpose") for r in llm)
    degraded = sum(1 for r in llm if r["payload"].get("degraded") is True)
    cached = sum(1 for r in llm if r["payload"].get("cached") is True)
    rr = sorted({int(r["round"]) for r in recs})

    seed_in_log = next((r["payload"].get("seed") for r in recs if r["type"] == "WORLD_INIT"), None)
    n_in_log = sum(1 for r in recs if r["type"] == "AGENT_BORN")
    rounds_from_log = (rr[-1] + 1) if rr else 0
    # 权威值来自日志；命令行参数仅作声明/交叉校验
    seed_authoritative = seed_in_log if seed_in_log is not None else a.seed
    n_authoritative = n_in_log if n_in_log else a.n
    rounds_authoritative = rounds_from_log if rounds_from_log else a.rounds

    cfg = {}
    try:
        cfg = json.loads((CODE / "config" / "llm.json").read_text(encoding="utf-8"))
    except Exception:
        pass

    bad_provider = [k for k in providers if k not in ("openai_compat",)]
    bad_model = [k for k in models if str(k).lower().startswith("mock") or k in (None, "")]
    meta = {
        "run_dir": str(run_dir),
        "run_file": str(run),
        "run_sha256": _sha256(run),
        "derived_from_log_sha256": _sha256(run),
        "generated_after_run": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_bytes": run.stat().st_size,
        # provider/model 一律由运行期 LLM_CALL payload 推导（单一真源）
        "provider": "openai_compat" if not (bad_provider or bad_model) else "NON-REAL",
        "llm_provider_in_events": {str(k): v for k, v in providers.items()},
        "llm_model_in_events": {str(k): v for k, v in models.items()},
        "model_requested": cfg.get("model"),
        "endpoint_host": (cfg.get("endpoint") or "").split("//")[-1].split("/")[0],
        "seed": seed_authoritative,
        "seed_declared": a.seed,
        "seed_in_log": seed_in_log,
        "n": n_authoritative,
        "n_declared": a.n,
        "n_in_log": n_in_log,
        "rounds": rounds_authoritative,
        "rounds_declared": a.rounds,
        "rounds_effective": rounds_from_log,
        "rounds_seen_min": rr[0] if rr else None,
        "rounds_seen_max": rr[-1] if rr else None,
        "rounds_contiguous": bool(rr) and rr == list(range(rr[0], rr[0] + len(rr))),
        "rounds_per_slot_effective": _rounds_per_slot(),
        "code_sha": _git("rev-parse", "HEAD"),
        "git_dirty_files": [ln for ln in _git("status", "--porcelain").splitlines() if ln],
        # 说明：本字段是**生成 meta 时刻**的全仓快照（共享仓库里可能有其他成员的未跟踪产物）。
        # 跑批时刻的「代码身份」以 `code_sha` + 日志内 `WORLD_INIT.config_components` 为硬证据：
        #   git diff <code_sha> -- code/life code/orchestration code/config 应为空。
        "git_dirty_code_files": [ln for ln in _git("status", "--porcelain").splitlines()
                                 if ln and (" code/" in ln or ln.endswith("code/"))],
        "code_identity_note": ("代码身份硬证据 = code_sha + WORLD_INIT.config_components；"
                               "git_dirty_code_files 为空表示 code/ 无未提交改动"),
        "events": len(recs),
        "wc_l": len(recs),
        "msg_counts": {k: v for k, v in types.items() if k.startswith("MSG")},
        "dropped_counts": {
            str((r["payload"].get("reason"), r["payload"].get("type"))): 0 for r in ()  # placeholder
        },
        "llm_calls": len(llm),
        "llm_cached": cached,
        "llm_cached_ratio": round(cached / len(llm), 4) if llm else 0.0,
        "degraded_calls": degraded,
        "llm_purposes": {str(k): v for k, v in purposes.items()},
        "mock_precalib_msg_count": a.mock_precalib_msg,
        "mock_precalib_note": ("mock 预校准（同 n/rounds、MockProvider）的 MSG 总条数，仅用于跑前估规模；"
                               "其日志另存 v2/evidence/run_d2_mock_precalib_*.jsonl，不混入本臂任何统计"),
        "fallback_detected": bool(bad_provider or bad_model),
        "started_at": a.started_at,
        "finished_at": a.finished_at or datetime.now().isoformat(timespec="seconds"),
        "duration_sec": a.duration_sec,
    }
    drops = Counter((r["payload"].get("reason"), r["payload"].get("type"))
                    for r in recs if r["type"] == "DROPPED")
    meta["dropped_counts"] = {f"{k[0]}|{k[1]}": v for k, v in sorted(drops.items(), key=lambda kv: str(kv[0]))}
    meta["msg_dropped_unknown_intent_field"] = sum(
        v for k, v in drops.items() if k[0] == "unknown_intent_field" and str(k[1]).startswith("MSG"))

    out = run_dir / "meta.json"
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"[meta] {out}")
    print(f"[meta] events={meta['events']} llm_calls={meta['llm_calls']} "
          f"cached_ratio={meta['llm_cached_ratio']} provider={meta['llm_provider_in_events']} "
          f"model={meta['llm_model_in_events']}")
    print(f"[meta] seed_in_log={seed_in_log} n_in_log={n_in_log} rounds_effective={meta['rounds_effective']}")

    if a.rounds and meta["rounds_effective"] != a.rounds:
        print(f"[meta] FAIL: rounds_effective={meta['rounds_effective']} != 声明 {a.rounds}", file=sys.stderr)
        return 5
    if a.seed is not None and seed_in_log is not None and int(seed_in_log) != a.seed:
        print(f"[meta] FAIL: seed_in_log={seed_in_log} != 声明 {a.seed}", file=sys.stderr)
        return 5
    if a.n is not None and n_in_log != a.n:
        print(f"[meta] FAIL: n_in_log={n_in_log} != 声明 {a.n}", file=sys.stderr)
        return 5
    if a.mock:
        print("[meta] OK (mock 臂：跳过真跑判定)")
        return 0
    if not llm:
        print("[meta] FAIL(真跑判定): LLM_CALL 为 0", file=sys.stderr)
        return 4
    if bad_provider or bad_model:
        print(f"[meta] FAIL(真跑判定): provider={dict(providers)} model={dict(models)}", file=sys.stderr)
        return 4
    print("[meta] OK: 真跑判定通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
