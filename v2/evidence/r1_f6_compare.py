#!/usr/bin/env python3
"""R1 · F-6 ON/OFF 两臂只读对比（确定性，不调 LLM，不写 run.jsonl）

口径（先写死，勿事后改）：
  ① msgs_total          = 日志中 MSG_DM/MSG_PUBLIC/MSG_GROUP 条数（=官方 F-6 的分母口径）
  ② msgs_with_refs      = payload.ctx 里出现 `memory_refs` 键的消息数（F-6 审计字段；OFF 臂应为 0）
  ③ refs_total          = 上述 memory_refs 列表长度之和（注入了几条跨天记忆）
  ④ mem_echo_msgs       = 在 ② 的消息中，「正文」与其被注入记忆正文存在 **≥1 个共享字符 6-gram** 的消息数
                          （只测"顺口提到了被注入的内容"，不测对错；与官方 F-6 timeref 不同口径，**不得混称**）
  ⑤ mem_echo_ngram_ratio= ④ 的共享 6-gram 数 / 被注入记忆正文的 6-gram 数（按消息取均值，仅描述）
  ⑥ timeref_rate        = **不由本脚本计算**；必用官方 `tools/d5/dialogue_metrics.py` 的
                          F-6_crossday_memory.timeref_rate（单一真源，禁止另写一份）

用法：
  python3 v2/evidence/r1_f6_compare.py \
      --on-log  v2/evidence/run_f6_on_n16r60_seed42/run.jsonl  --on-side /tmp/f6_on60_side \
      --off-log v2/evidence/run_f6_off_n16r60_seed42/run.jsonl --off-side /tmp/f6_off60_side \
      --out v2/evidence/r1_f6_refs_audit.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def _ngrams(text: str, n: int = 6) -> set:
    t = "".join((text or "").split())
    return {t[i:i + n] for i in range(0, max(0, len(t) - n + 1))}


def _read_side(side_root: str, body_ref: str) -> str:
    """side://src/<sha>.txt -> <side_root>/src/<sha>.txt"""
    if not body_ref or not body_ref.startswith("side://"):
        return ""
    rel = body_ref[len("side://"):]
    path = os.path.join(side_root, rel)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def scan(log_path: str, side_root: str) -> Dict[str, object]:
    mem_text: Dict[str, str] = {}
    msgs: List[dict] = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = rec.get("type")
            if t == "MEMORY_WRITE":
                p = rec.get("payload") or {}
                mid = p.get("mem_id")
                if mid:
                    mem_text[mid] = _read_side(side_root, p.get("body_ref") or "")
            elif t in MSG_TYPES:
                p = rec.get("payload") or {}
                msgs.append({
                    "round": rec.get("round"),
                    "seq": rec.get("seq"),
                    "from": p.get("from"),
                    "body": (p.get("body") or "").strip(),
                    "ctx": p.get("ctx") or {},
                })

    with_refs = [m for m in msgs if "memory_refs" in m["ctx"]]
    refs_total = sum(len(m["ctx"].get("memory_refs") or []) for m in with_refs)

    echo_msgs = 0
    echo_ratios: List[float] = []
    missing_text = 0
    for m in with_refs:
        body_g = _ngrams(m["body"])
        joined = ""
        for mid in (m["ctx"].get("memory_refs") or []):
            txt = mem_text.get(mid, "")
            if not txt:
                missing_text += 1
            joined += txt
        mem_g = _ngrams(joined)
        if not mem_g:
            continue
        shared = len(body_g & mem_g)
        if shared > 0:
            echo_msgs += 1
        echo_ratios.append(shared / len(mem_g))

    return {
        "log": log_path,
        "side_root": side_root,
        "msgs_total": len(msgs),
        "msgs_with_refs": len(with_refs),
        "refs_total": refs_total,
        "mem_echo_msgs": echo_msgs,
        "mem_echo_ngram_ratio_mean": (sum(echo_ratios) / len(echo_ratios)) if echo_ratios else None,
        "memory_text_missing": missing_text,
        "notes": {
            "msgs_denominator": "MSG_DM/MSG_PUBLIC/MSG_GROUP 条数（=官方 F-6 分母口径）",
            "mem_echo_rule": "正文与被注入记忆正文共享 >=1 个字符 6-gram 即记一条（只测「提到了被注入内容」）",
            "timeref_rate": "必须取官方 tools/d5/dialogue_metrics.py 的 F-6_crossday_memory.timeref_rate，本脚本不算",
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F-6 ON/OFF 两臂 memory_refs 审计对比（只读）")
    ap.add_argument("--on-log", required=True)
    ap.add_argument("--on-side", required=True)
    ap.add_argument("--off-log", required=True)
    ap.add_argument("--off-side", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    out = {"on": scan(a.on_log, a.on_side), "off": scan(a.off_log, a.off_side)}
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
