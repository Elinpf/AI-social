#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-3 机会密度探针（**只读**：不改尺子、不改 code/、不跑批、不调 LLM）。

## 为什么需要它

`repo-scout` 在 R39 预登记里要证明「改尺子后 F-3 判据**可达**」，而不是又造一把必然不可判的尺子。
本脚本把「换一份词表 → 分母会变成多少」这件事做成**可复算**的探针：

- 分母口径与 `v2/evidence/f3_audit_echo.py` **逐行同源**：
  极性 = `sum(w in body for 正词) vs sum(负词)` 多数胜（`dialogue_metrics.py:1043-1051` 同款），
  线程键 = `f4a.mixed_key`，线程内按 `(round, seq)` 排序，取「上一句极性 ≠ 0」的相邻对；
- 两个分母并列：`all_messages`（全部相邻对）与 `reply_path`（**主口径**：当前句 `reply_to` 非空）。

## 用法

    # 用现行 18 词表（tools/d5/emotion_lexicon.txt）看现状
    python3 tools/f3/f3_opportunity_probe.py \
        --run v2/evidence/r38_f3_batch/on/run.jsonl --lexicon tools/d5/emotion_lexicon.txt

    # 用候选 v2 词表看可达性
    python3 tools/f3/f3_opportunity_probe.py \
        --run v2/evidence/r38_f3_batch/on/run.jsonl --lexicon tools/f3/emotion_lexicon_v2_candidate.txt \
        [--word-stats] [--out-json /tmp/probe.json]

    # 多语料一次扫（谁是分母、谁是覆盖，一目了然）
    python3 tools/f3/f3_opportunity_probe.py --run A --run B --lexicon L

## 口径纪律

- **只读**：只 open 文件读，不写除 `--out-json` 之外的任何路径；
- `--word-stats` 给出每个词条的**命中消息数**，用于剔除"从不命中"或"命中即假阳性"的词
  （R38 的实现记录 §4 已经因为 `断了`/`顺当` 两个假阳性删过词）；
- 词表文件格式与 `tools/d5/emotion_lexicon.txt` 完全一致：`#` 注释、`极性<TAB>词`。
- `--metrics` 额外算 F-3 的**分子/分母/接住率**（`loose` 档：极性相同 ∪ 任意 EMPATHY_MARKERS），
  与 `v2/evidence/f3_audit_echo.py` 的 `loose` 档同源；**默认关闭**，保持只出分母的旧行为
  （已有使用者不受影响）。
- `--precision-rules` 开启 R39 预登记的**三条精度排除规则**（默认关；开时必须同屏声明，
  否则读数与 v1 原样不可比）：`[得的地]厉害`（程度副词）、`怕(是|要|会|不|连)`（揣度）、
  `辛苦`（共情词 → 改判正向）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import os
import sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


d5 = _load("dialogue_metrics_probe", os.path.join(REPO, "tools/d5/dialogue_metrics.py"))
f4a = _load("f4_anchor_recompute_probe", os.path.join(REPO, "tools/f4/f4_anchor_recompute.py"))


#: 与 `v2/evidence/f3_audit_echo.py:53` 同源的官方共情标记（loose 档用）
EMPATHY_MARKERS = ("我懂", "我也", "别难过", "恭喜", "辛苦", "真惨", "太好了", "确实", "是啊", "可不是")

#: R39 预登记 §2.1 的三条精度排除规则（`--precision-rules` 才启用）
PRECISION_RULES = (
    (re.compile(r"[得的地]厉害"), "厉害=程度副词"),
    (re.compile(r"厉害(得|透)"), "厉害=程度补语"),
    (re.compile(r"怕(是|要|会|不|连)"), "怕=揣度某结果"),
)
PRECISION_POS_BONUS = (("辛苦", 1), )   # 辛苦 = 共情词，改判正向


def wilson(k: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return None
    import math
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - r) / d, 6), round((c + r) / d, 6)]


def band(n: int) -> str:
    if n == 0:
        return "empty"
    if n < 30:
        return "count_only"
    if n < 68:
        return "probe"
    return "ok"


def load_lexicon(path: str) -> dict:
    """与 f4a.load_emotion 同实现（极性<TAB>词），另返回原文 sha 由调用方算。"""
    return f4a.load_emotion(path)


def group_threads(msgs):
    threads = defaultdict(list)
    for m in msgs:
        threads[f4a.mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))
    return threads


def probe(path: str, emo: dict, word_stats: bool = False,
          precision_rules: bool = False, metrics: bool = False) -> dict:
    def polarity(body: str) -> int:
        b = body
        if precision_rules:
            for rx, _ in PRECISION_RULES:
                b = rx.sub("＿", b)
        pos = sum(1 for w, p in emo.items() if p > 0 and w in b)
        neg = sum(1 for w, p in emo.items() if p < 0 and w in b)
        if precision_rules:
            for w, add in PRECISION_POS_BONUS:
                if w in b:
                    pos += add
        if pos > neg:
            return 1
        if neg > pos:
            return -1
        return 0

    recs, bad = d5.read_run(path)
    msgs = d5.extract_messages(recs)
    threads = group_threads(msgs)

    n_msg = len(msgs)
    n_reply_path_msgs = sum(1 for m in msgs if m.get("reply_to"))
    n_pol_nonzero = 0
    n_reply_pol_nonzero = 0
    den_all = den_reply = num_reply = 0
    pos_msgs = neg_msgs = 0
    wc: Counter = Counter()

    for m in msgs:
        p = polarity(m["body"])
        if p != 0:
            n_pol_nonzero += 1
            if m.get("reply_to"):
                n_reply_pol_nonzero += 1
        if p > 0:
            pos_msgs += 1
        elif p < 0:
            neg_msgs += 1
        if word_stats:
            for w in emo:
                if w in m["body"]:
                    wc[w] += 1

    for key in sorted(threads):
        th = threads[key]
        for i in range(1, len(th)):
            prev, cur = th[i - 1], th[i]
            if polarity(prev["body"]) == 0:
                continue
            den_all += 1
            if cur.get("reply_to"):
                den_reply += 1
                if metrics:
                    p_prev = polarity(prev["body"])
                    p_cur = polarity(cur["body"])
                    if p_cur == p_prev or any(w in cur["body"] for w in EMPATHY_MARKERS):
                        num_reply += 1

    out = {
        "run": path,
        "n_messages": n_msg,
        "n_threads": len(threads),
        "n_reply_path_msgs": n_reply_path_msgs,
        "n_polarity_nonzero_msgs": n_pol_nonzero,
        "n_reply_path_polarity_nonzero_msgs": n_reply_pol_nonzero,
        "polarity_nonzero_density_per_message": round(n_pol_nonzero / n_msg, 6) if n_msg else None,
        "den_all_messages": den_all,
        "den_reply_path": den_reply,
        "opportunity_density_per_message_main": round(den_reply / n_msg, 6) if n_msg else None,
        "pos_msgs": pos_msgs,
        "neg_msgs": neg_msgs,
        "descriptions": {
            "den_all_messages": "线程内相邻对中『上一句极性≠0』的对数",
            "den_reply_path": "同上，且当前句 payload.reply_to 非空（F-3 主口径）",
            "opportunity_density_per_message_main": "den_reply_path / n_messages",
        },
        "bad_lines": bad,
    }
    if metrics:
        out["f3_loose"] = {
            "den_reply_path": den_reply,
            "num_reply_path": num_reply,
            "rate": round(num_reply / den_reply, 6) if den_reply else None,
            "wilson95": wilson(num_reply, den_reply),
            "band": band(den_reply),
            "rule": "loose 档：下一句极性==上一句极性 或 下一句含任意 EMPATHY_MARKERS（与 f3_audit_echo.loose 同源）",
            "precision_rules": precision_rules,
        }
    if word_stats:
        out["word_hits"] = {w: wc.get(w, 0) for w in sorted(emo)}
        out["words_never_hit"] = sorted(w for w in emo if wc.get(w, 0) == 0)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F-3 机会密度探针（只读）")
    ap.add_argument("--run", action="append", required=True, help="run.jsonl 路径（可重复）")
    ap.add_argument("--lexicon", required=True, help="极性<TAB>词 词表路径")
    ap.add_argument("--word-stats", action="store_true", help="统计每个词条命中消息数")
    ap.add_argument("--metrics", action="store_true",
                    help="额外出 F-3 loose 档分子/分母/接住率（默认关，与 f3_audit_echo.loose 同源）")
    ap.add_argument("--precision-rules", action="store_true",
                    help="启用 R39 预登记 §2.1 三条精度排除规则（默认关）")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args(argv)

    lex = args.lexicon if os.path.isabs(args.lexicon) else os.path.join(REPO, args.lexicon)
    emo = load_lexicon(lex)
    import hashlib
    sha = hashlib.sha256(open(lex, "rb").read()).hexdigest()
    n_pos = sum(1 for p in emo.values() if p > 0)
    n_neg = sum(1 for p in emo.values() if p < 0)

    out = {"lexicon": {"path": os.path.relpath(lex, REPO), "sha256": sha,
                       "n_words": len(emo), "n_pos": n_pos, "n_neg": n_neg},
           "options": {"metrics": args.metrics, "precision_rules": args.precision_rules},
           "runs": [probe(r if os.path.isabs(r) else os.path.join(REPO, r), emo,
                          args.word_stats, args.precision_rules, args.metrics)
                    for r in args.run]}
    text = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.out_json:
        open(args.out_json, "w", encoding="utf-8").write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
