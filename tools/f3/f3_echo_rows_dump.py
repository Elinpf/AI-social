#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""f3_echo_rows_dump.py —— 把某一臂 `payload.ctx.echo` 的**全部**线索行摊平成可标注表。

为什么要单独摊平：`v2/evidence/f3_audit_echo.py` 的四档判定只在「机会集」
（线程内相邻对、且上一句极性 ≠ 0）上求值。r38 ON 臂的 110 条 echo 里只有 **4** 条
落进机会集，其余 106 条既不进分母也不进分子——所以「四档一条都没接住」这句话
必须连同分母（4，不是 110）一起说。本脚本把 110 条**逐条**连同上一句原文摊出来，
供逐行标注（标注者是人/LLM 辅助，不是词表）。

零跑批、零 LLM：只读 run.jsonl。

用法（仓库根）：
  python3 tools/f3/f3_echo_rows_dump.py \
      --run v2/evidence/r38_f3_batch/on/run.jsonl \
      --audit v2/evidence/r38_f3_batch/f3_audit_echo.json --arm on \
      --out-csv v2/evidence/r38_f3_batch/f3_echo_rows_110.csv \
      --out-json v2/evidence/r38_f3_batch/f3_echo_rows_110.json
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

TIERS = ("loose", "loose_no_agree", "polarity_match", "marker_based")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


d5 = _load("dialogue_metrics_echodump", os.path.join(REPO, "tools/d5/dialogue_metrics.py"))
f4a = _load("f4_anchor_recompute_echodump", os.path.join(REPO, "tools/f4/f4_anchor_recompute.py"))


def polarity(body, emo):
    """照 `tools/d5/dialogue_metrics.py:1043-1051` 的 polaricity 逐行复制（词表子串计数多数胜）。"""
    pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
    neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def body_of(m):
    if not m:
        return ""
    p = m.get("payload") or {}
    return p.get("body") or p.get("text") or m.get("body") or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--audit", default="", help="f3_audit_echo.json（用于回填四档判定）")
    ap.add_argument("--arm", default="on")
    ap.add_argument("--annotation", default="", help="已有的逐行标注 JSON（按 seq 回填 gold_label/gold_confidence/gold_note）")
    ap.add_argument("--out-csv", default="")
    ap.add_argument("--out-json", default="")
    a = ap.parse_args()

    run = a.run if os.path.isabs(a.run) else os.path.join(REPO, a.run)
    recs, bad = d5.read_run(run)
    raw = [r for r in recs if str(r.get("type", "")) in ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")]
    msgs = d5.extract_messages(recs)
    emo = f4a.load_emotion(os.path.join(REPO, "tools/d5/emotion_lexicon.txt"))
    body_by_seq = {m.get("seq"): m.get("body") for m in msgs}

    # 线程内排序，取「上一句」；线程键沿用仓库既有实现（要求 extract_messages 的扁平结构）
    threads = defaultdict(list)
    for m in msgs:
        threads[f4a.mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m.get("round") or 0, m.get("seq") or 0))
    prev_of = {}
    for k, lst in threads.items():
        for i, m in enumerate(lst):
            prev_of[m.get("seq")] = lst[i - 1] if i > 0 else None

    # 四档判定（只在机会集里有值；其余为 None = 未进判定）
    tier_flags = {}
    if a.audit:
        ad = json.load(open(a.audit if os.path.isabs(a.audit) else os.path.join(REPO, a.audit),
                            encoding="utf-8"))
        arm = [x for x in ad["arms"] if x["meta"]["label"] == a.arm][0]
        for r in arm["rows"]:
            tier_flags[r["cur_seq"]] = {t: bool(r.get(f"tier_{t}")) for t in TIERS}
        mechanism_rows = arm["mechanism"]["rows"]
    else:
        mechanism_rows = []
        for r in raw:
            e = (r.get("payload") or {}).get("ctx", {}).get("echo")
            if isinstance(e, dict):
                mechanism_rows.append({"seq": r.get("seq"), "round": r.get("round"),
                                       "thread": f4a.mixed_key(r), **e})

    rows = []
    for i, e in enumerate(mechanism_rows, 1):
        seq = e["seq"]
        cur = next((r for r in msgs if r.get("seq") == seq), None)
        prev = prev_of.get(seq)
        pb = body_of(prev)
        cb = body_of(cur) or (body_by_seq.get(seq) or "")
        cur_echo = next((r for r in raw if r.get("seq") == seq), None)
        p_prev = polarity(pb, emo) if prev else None
        tf = tier_flags.get(seq)
        rows.append({
            "row_no": i,
            "seq": seq,
            "thread": e.get("thread"),
            "round": e.get("round"),
            "echo_tier": e.get("tier"),
            "echo_kind": e.get("kind"),
            "echo_sign": e.get("sign"),
            "echo_intensity": e.get("intensity"),
            "echo_source": e.get("source"),
            "echo_mood": e.get("mood"),
            "prev_seq": (prev or {}).get("seq"),
            "prev_polarity": p_prev,
            "prev_body": pb,
            "cur_body": cb,
            "cur_is_reply": bool((cur_echo.get("payload") or {}).get("reply_to")) if cur_echo else None,
            "in_opportunity_set": tf is not None,
            "tier_loose": (tf or {}).get("loose"),
            "tier_loose_no_agree": (tf or {}).get("loose_no_agree"),
            "tier_polarity_match": (tf or {}).get("polarity_match"),
            "tier_marker_based": (tf or {}).get("marker_based"),
            "gold_label": "",
            "gold_confidence": "",
            "gold_note": "",
        })

    if a.annotation and os.path.isfile(a.annotation if os.path.isabs(a.annotation)
                                       else os.path.join(REPO, a.annotation)):
        ann = json.load(open(a.annotation if os.path.isabs(a.annotation)
                             else os.path.join(REPO, a.annotation), encoding="utf-8"))
        by_seq = {r["seq"]: r for r in ann.get("rows", [])}
        hit = 0
        for r in rows:
            g = by_seq.get(r["seq"])
            if g:
                r["gold_label"] = g.get("gold_label", "")
                r["gold_confidence"] = g.get("gold_confidence", "")
                r["gold_note"] = g.get("gold_note", "")
                hit += 1
        print(f"annotation merged: {hit}/{len(rows)}")

    if a.out_json:
        p = a.out_json if os.path.isabs(a.out_json) else os.path.join(REPO, a.out_json)
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"schema": "f3-echo-rows/1", "run": os.path.relpath(run, REPO),
                       "run_sha8": f4a.sha8(run), "bad_lines": bad.get("n_bad"),
                       "n_rows": len(rows), "rows": rows}, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("written:", p)
    if a.out_csv:
        p = a.out_csv if os.path.isabs(a.out_csv) else os.path.join(REPO, a.out_csv)
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print("written:", p)
    print(f"rows={len(rows)} opportunity={sum(1 for r in rows if r['in_opportunity_set'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
