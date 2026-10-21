#!/usr/bin/env python3
"""L-7 第三臂（DEQUP）读数与预算归因：把「新臂 vs R11 ON 臂」的差异摊到同一张表上。

只读；零 LLM（`obs llm-cost` 只解析日志里的 LLM_CALL 事件，不发起调用）。

用法：
    python3 tools/l7/l7_arm_compare.py \
        --dequp v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl \
        --on    v2/evidence/run_f6_on_n16r60_seed42/run.jsonl \
        --out   v2/evidence/l7_arm_compare.json

产出（每一项都能被第三方照命令复算）：
  - 每臂：MSG 数、L-7 dup 数与率（官方 8-gram 口径）、记忆引用集中度、ctx.dequp 审计累计值；
  - 每臂：`obs llm-cost` 的 total/calls/tokens 与 by_purpose.dialogue 的 calls/tokens；
  - 两臂差值：calls / tokens_in / tokens_out / dialogue calls（用于「多问了一遍 vs 更会说话」的归因）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.l7.l7_baseline_recount import dup_index, load_msgs  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def llm_cost(log_path: Path) -> dict:
    log_path = log_path.resolve()
    """调官方 obs llm-cost（只解析日志，不发起 LLM 调用），返回 JSON。"""
    out = subprocess.run(
        [sys.executable, "-m", "obs", "llm-cost", "--log", str(log_path)],
        cwd=REPO / "code", capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        return {"error": f"rc={out.returncode}", "stderr": out.stderr[-2000:]}
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception as exc:  # pragma: no cover
        return {"error": f"parse: {exc}", "raw": out.stdout[-2000:]}


def arm(path: Path) -> dict:
    msgs = load_msgs(str(path))
    dup = dup_index(msgs)
    refs = [m for m in msgs if m["memory_refs"]]
    all_refs = [mid for m in msgs for mid in m["memory_refs"]]
    per_mem = Counter(all_refs)
    # ctx.dequp：只有 DEQUP 臂才有；取累计值的最后一次（模块内计数单调递增）
    dequp_msgs = 0
    last = {}
    for rec_line in path.open(encoding="utf-8"):
        rec_line = rec_line.strip()
        if not rec_line:
            continue
        r = json.loads(rec_line)
        p = r.get("payload") or {}
        d = ((p.get("ctx") or {}).get("dequp"))
        if d:
            dequp_msgs += 1
            last = d
    cost = llm_cost(path)
    total = ((cost.get("engine_log") or {}).get("total") or cost.get("total") or {})
    dlg = ((cost.get("engine_log") or {}).get("by_purpose") or {}).get("dialogue") or {}
    return {
        "log": str(path),
        "n_msg": len(msgs),
        "L7_dup": len(dup),
        "L7_rate": round(len(dup) / len(msgs), 6) if msgs else None,
        "n_msgs_with_memory_refs": len(refs),
        "n_refs_total": len(all_refs),
        "n_refs_unique": len(set(all_refs)),
        "refs_per_unique_mem_mean": round(len(all_refs) / len(set(all_refs)), 4) if all_refs else None,
        "top_mem_ids": [{"mem_id": k, "refs": v} for k, v in per_mem.most_common(5)],
        "dequp_msgs": dequp_msgs,
        "dequp_last": last,
        "llm": {
            "calls": total.get("calls"),
            "tokens_in": total.get("tokens_in"),
            "tokens_out": total.get("tokens_out"),
            "tokens_total": total.get("tokens_total"),
            "degraded": total.get("degraded"),
            "by_provider": (cost.get("engine_log") or {}).get("by_provider"),
            "dialogue_calls": dlg.get("calls"),
            "dialogue_tokens_in": dlg.get("tokens_in"),
            "dialogue_tokens_out": dlg.get("tokens_out"),
        },
    }


def delta(a: dict, b: dict, keys: list[str]) -> dict:
    out = {}
    for k in keys:
        va, vb = a.get(k), b.get(k)
        out[k] = {"dequp": va, "on": vb,
                  "delta": (va - vb) if isinstance(va, int) and isinstance(vb, int) else None}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dequp", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = arm(Path(a.dequp))
    o = arm(Path(a.on))
    res = {
        "dequp_arm": d,
        "on_arm": o,
        "delta": delta(d["llm"], o["llm"],
                       ["calls", "tokens_in", "tokens_out", "tokens_total",
                        "dialogue_calls", "dialogue_tokens_in", "dialogue_tokens_out"]),
        "delta_shape": {"n_msg": d["n_msg"] - o["n_msg"],
                        "L7_dup": d["L7_dup"] - o["L7_dup"],
                        "L7_rate": (round(d["L7_rate"] - o["L7_rate"], 6)
                                    if d["L7_rate"] is not None and o["L7_rate"] is not None else None),
                        "refs_unique_mem": d["n_refs_unique"] - o["n_refs_unique"],
                        "refs_per_unique_mem_mean": (
                            round(d["refs_per_unique_mem_mean"] - o["refs_per_unique_mem_mean"], 4)
                            if d["refs_per_unique_mem_mean"] and o["refs_per_unique_mem_mean"] else None)},
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
