#!/usr/bin/env python3
"""L-7 缺口零跑批复算（只读 run.jsonl，零 LLM、零批次）。

用途：在花钱跑「第三臂」之前，先用 R11 已入库的两臂日志把缺口三数独立复算一遍，
证明 L-7 恶化与「记忆注入复用集中度」两个事实都是可复现的，而不是抄报告。
判据口径全部沿用 `tools/d5/dialogue_metrics.py` 的既有定义（normalize_body + 8-gram
shingle 任意重合即记 dup），不新造指标。

用法：
    python3 tools/l7/l7_baseline_recount.py \
        --on  v2/evidence/run_f6_on_n16r60_seed42/run.jsonl \
        --off v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
        --out v2/evidence/l7_baseline_recount.json

期望（R11 报告给出的对照值）：
    ON  臂：带 ctx.memory_refs 的消息 412、引用总数 824、唯一 mem_id 128、均值 6.4；
            有 8-gram 近重复的 MSG 332，其中 315 条带 memory_refs；
    OFF 臂：无 memory_refs；有近重复的 MSG 181。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.d5.dialogue_metrics import MSG_TYPES, normalize_body  # noqa: E402


def load_msgs(path: str) -> list[dict]:
    msgs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("type") in MSG_TYPES:
                p = rec.get("payload") or {}
                msgs.append({
                    "seq": rec.get("seq"),
                    "type": rec.get("type"),
                    "from": p.get("from"),
                    "body": p.get("body") or "",
                    "memory_refs": list((p.get("ctx") or {}).get("memory_refs") or []),
                })
    return msgs


def dup_index(msgs: list[dict]) -> set[int]:
    """官方 L-7 口径：normalize 后 8-gram shingle，任一 shingle 与他人重合即算 dup。"""
    shingles = []
    for m in msgs:
        t = normalize_body(m["body"])
        shingles.append({t[i:i + 8] for i in range(max(0, len(t) - 7))})
    sh_index: dict[str, list[int]] = defaultdict(list)
    for i, sh in enumerate(shingles):
        for g in sh:
            sh_index[g].append(i)
    dup = set()
    for g, idxs in sh_index.items():
        if len(idxs) > 1:
            dup.update(idxs)
    return dup


def arm_summary(path: str) -> dict:
    msgs = load_msgs(path)
    n_msg = len(msgs)
    dup = dup_index(msgs)
    with_refs = [m for m in msgs if m["memory_refs"]]
    all_refs = [mid for m in msgs for mid in m["memory_refs"]]
    uniq = sorted(set(all_refs))
    per_mem = Counter(all_refs)
    return {
        "log": path,
        "n_msg": n_msg,
        "n_msgs_with_memory_refs": len(with_refs),
        "n_refs_total": len(all_refs),
        "n_refs_unique_mem_ids": len(uniq),
        "refs_per_msg_mean": round(len(all_refs) / len(with_refs), 4) if with_refs else None,
        "refs_per_unique_mem_mean": round(len(all_refs) / len(uniq), 4) if uniq else None,
        "top_mem_ids": [{"mem_id": k, "refs": v} for k, v in per_mem.most_common(5)],
        "n_dup_msgs_L7": len(dup),
        "L7_rate": round(len(dup) / n_msg, 6) if n_msg else None,
        "n_dup_msgs_with_memory_refs": sum(1 for i in dup if msgs[i]["memory_refs"]),
        "dup_examples": [
            {"seq": msgs[i]["seq"], "from": msgs[i]["from"], "body": msgs[i]["body"][:60]}
            for i in sorted(dup)[:5]
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--on", required=True)
    ap.add_argument("--off", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {"on": arm_summary(a.on), "off": arm_summary(a.off)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
