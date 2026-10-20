#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D5 噪声带两级估计：B1 观测对差 + B2 抽样噪声带（bootstrap）。

背景：t300 与 t355 是「同 seed、同 provider、同模型、temperature=0、同 n/rounds、
只差无关树改动」的两批；MSG 条数相同、收发对 100% 对齐，但正文逐条一致仅 21.3%。
它们的**单次观测差（B1）不是阈值**——一次观测不能代表「什么都不改也会有多大波动」。

B2 给的是：两臂视为同分布时，**给定分母 m 下比率差能有多大**。
做法（与 prompt-linguist 独立实现同一方法，用于交叉验证）：
  1. 每臂各自计算逐项 0/1 标记（per-message 或 per-adjacent-pair）；
  2. 各自有放回重采样 m 项，算比率；
  3. Δ = 100*(rate_A − rate_B)，重复 B=2000 次（random.Random(42)）；
  4. 取 Δ 的 2.5% / 97.5% 分位 ⇒ 该分母下的噪声带半宽（pp）。

用法：
    python3 artifacts/code/dialogue_noiseband_bootstrap.py \
        --log-a /root/t271/runs/t300/run.jsonl --log-b /root/t271/runs/t355/run.jsonl \
        --denoms 68 100 150 170 188 230 --boot 2000 --seed 42 \
        --out-json v2/evidence/d5_noiseband_bootstrap_t300_t355.json \
        --out-md   v2/evidence/d5_noiseband_bootstrap_t300_t355.md
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import sys
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))


def load_dm():
    spec = importlib.util.spec_from_file_location("dm", os.path.join(HERE, "dialogue_metrics.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def load_words(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    return [ln.strip() for ln in open(path, encoding="utf-8")
            if ln.strip() and not ln.strip().startswith("#")]


def item_flags(dm, log_path: str, lexicon_path: str, tmpl_path: str, personas_path: str,
               emotion_path: str) -> Tuple[Dict[str, List[int]], Dict[str, List[float]]]:
    """返回 (per-item 0/1 标记, per-thread 数值) —— 定义与 dialogue_metrics.py 完全一致。"""
    recs, _ = dm.read_run(log_path)
    msgs = dm.extract_messages(recs)
    lexicon = load_words(lexicon_path)
    templates = [__import__("re").compile(t) for t in load_words(tmpl_path)]
    names, _ = dm.load_personas(personas_path)
    emotion = {}
    for ln in load_words(emotion_path):
        parts = ln.split()
        if len(parts) >= 2:
            try:
                emotion[" ".join(parts[1:])] = int(parts[0])
            except ValueError:
                pass

    threads, _ = dm.group_threads(msgs)
    th_mixed: Dict[str, List[dict]] = {}
    for m in msgs:
        if m["channel"] == "dm":
            k = "-".join(sorted({str(m["from"]), str(m["to"])}))
        elif m["channel"] == "public":
            k = "-"
        else:
            k = str(m.get("thread_id") or m.get("place") or "-")
        th_mixed.setdefault("m:%s|%s|%s" % (m["day"], m["channel"], k), []).append(m)
    for k in th_mixed:
        th_mixed[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                        m["seq"] if m["seq"] is not None else -1))

    flags: Dict[str, List[int]] = {k: [] for k in
                                   ["L-2", "L-3", "L-5", "L-7", "L-8", "L-9", "L-6flag", "L-11", "L-12"]}
    norm = [dm.normalize_body(m["body"]) for m in msgs]
    from collections import Counter
    cnt = Counter(norm)
    # 8-gram
    sh = [{t[i:i + 8] for i in range(max(0, len(t) - 7))} for t in norm]
    idx: Dict[str, List[int]] = {}
    for i, s in enumerate(sh):
        for g in s:
            idx.setdefault(g, []).append(i)
    dup8 = {i for g, ids in idx.items() if len(ids) > 1 for i in ids}
    meta_rx = __import__("re").compile(r"作为(一个)?(AI|人工智能|语言模型|助手)|我是一个语言模型")
    for i, m in enumerate(msgs):
        body = m["body"]
        flags["L-2"].append(1 if body.lstrip()[:1] in ("（", "(") else 0)
        flags["L-3"].append(1 if dm.PAREN_ANY_RE.search(body) else 0)
        flags["L-5"].append(1 if any(t.search(body) for t in templates) else 0)
        flags["L-7"].append(1 if i in dup8 else 0)
        flags["L-8"].append(1 if dm.AGENT_ID_RE.search(body) else 0)
        flags["L-9"].append(1 if meta_rx.search(body) else 0)
        flags["L-6flag"].append(1 if cnt[norm[i]] > 1 else 0)
        if m["channel"] in ("dm", "group"):
            flags["L-11"].append(1 if ("你" in body or "您" in body) else 0)
            peer = names.get(str(m["to"]))
            flags["L-12"].append(1 if (peer and peer in body) else 0)

    pair_flags: Dict[str, List[int]] = {"K1_backref": [], "K1_lexical": [], "K1_tag": []}
    for k in sorted(th_mixed):
        seq = th_mixed[k]
        for i in range(1, len(seq)):
            prev, cur = seq[i - 1], seq[i]
            pair_flags["K1_backref"].append(1 if any(w in cur["body"] for w in lexicon) else 0)
            a, b = dm.content_bigrams(prev["body"]), dm.content_bigrams(cur["body"])
            pair_flags["K1_lexical"].append(1 if (a & b) else 0)
            pair_flags["K1_tag"].append(1 if (set(prev["tags"]) & set(cur["tags"])) else 0)

    thread_flags: Dict[str, List[int]] = {"single_msg_thread": [], "multi_turn_thread": [], "single_speaker_thread": []}
    threads_vals: Dict[str, List[float]] = {"turns_A": [], "msgs_per_thread": []}
    for k in sorted(threads):
        th = threads[k]
        spk = [str(m["from"]) for m in th]
        ta = 1 + sum(1 for i in range(1, len(spk)) if spk[i] != spk[i - 1])
        threads_vals["turns_A"].append(ta)
        threads_vals["msgs_per_thread"].append(len(th))
        thread_flags["single_msg_thread"].append(1 if len(th) == 1 else 0)
        thread_flags["multi_turn_thread"].append(1 if ta >= 3 else 0)
        thread_flags["single_speaker_thread"].append(1 if len(set(spk)) == 1 else 0)
    return ({"item:" + k: v for k, v in flags.items()} | {"pair:" + k: v for k, v in pair_flags.items()}
            | {"thread:" + k: v for k, v in thread_flags.items()}), threads_vals


def boot_rate_diff(a: List[int], b: List[int], m: int, boot: int, rng: random.Random) -> Dict[str, float]:
    if not a or not b:
        return {}
    diffs = []
    for _ in range(boot):
        ra = sum(rng.choice(a) for _ in range(m)) / m
        rb = sum(rng.choice(b) for _ in range(m)) / m
        diffs.append(100.0 * (ra - rb))
    diffs.sort()
    def q(p):
        pos = (len(diffs) - 1) * p
        lo = int(pos); hi = min(lo + 1, len(diffs) - 1)
        return round(diffs[lo] + (diffs[hi] - diffs[lo]) * (pos - lo), 3)
    return {"lo_2.5": q(0.025), "hi_97.5": q(0.975), "halfwidth_pp": round((q(0.975) - q(0.025)) / 2, 3)}


def median(v: List[float]) -> float:
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def boot_median_diff(a: List[float], b: List[float], m: int, boot: int, rng: random.Random) -> Dict[str, float]:
    if not a or not b:
        return {}
    diffs = []
    for _ in range(boot):
        ra = median([rng.choice(a) for _ in range(m)])
        rb = median([rng.choice(b) for _ in range(m)])
        diffs.append(ra - rb)
    diffs.sort()
    def q(p):
        pos = (len(diffs) - 1) * p
        lo = int(pos); hi = min(lo + 1, len(diffs) - 1)
        return round(diffs[lo] + (diffs[hi] - diffs[lo]) * (pos - lo), 3)
    return {"lo_2.5": q(0.025), "hi_97.5": q(0.975), "halfwidth": round((q(0.975) - q(0.025)) / 2, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D5 两级噪声带（B1 观测差 + B2 bootstrap 抽样带）")
    ap.add_argument("--log-a", required=True)
    ap.add_argument("--log-b", required=True)
    ap.add_argument("--denoms", nargs="+", type=int, default=[68, 100, 150, 170, 188, 230])
    ap.add_argument("--thread-denoms", nargs="+", type=int, default=[20, 30, 50, 68, 100])
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args(argv)

    dm = load_dm()
    lex = os.path.join(HERE, "backref_lexicon.txt")
    tpl = os.path.join(HERE, "template_patterns.txt")
    per = os.path.join(HERE, "..", "..", "code", "config", "personas.json")
    emo = os.path.join(HERE, "emotion_lexicon.txt")

    fa, ta = item_flags(dm, args.log_a, lex, tpl, per, emo)
    fb, tb = item_flags(dm, args.log_b, lex, tpl, per, emo)
    rng = random.Random(args.seed)

    res: Dict[str, Any] = {
        "schema_version": "d5-noiseband-bootstrap/1.0",
        "method": {
            "B1": "两批指标单次观测差（|metric_A - metric_B|），只作实测量级参照，不作阈值",
            "B2": ("两臂各自有放回重采样 m 项 → 比率/中位数差 → Δ=100*(A-B) 的 2.5/97.5 分位；"
                   "B=2000，Random(seed)；表示「两臂同分布时，给定分母下差异能有多大」"),
            "caveat": "B2 是抽样噪声带，不是效应检验，也不是总体差 CI；不可跨规模/模型/提示词版本外推",
            "boot": args.boot, "seed": args.seed, "denoms": args.denoms,
            "thread_denoms": args.thread_denoms,
        },
        "inputs": {
            "log_a": {"path": args.log_a, "sha256": dm.sha256_file(args.log_a)},
            "log_b": {"path": args.log_b, "sha256": dm.sha256_file(args.log_b)},
            "script_sha256": dm.sha256_file(os.path.abspath(__file__)),
        },
        "item_counts": {k: {"a": len(v), "b": len(fb.get(k, []))} for k, v in fa.items()},
        "B1_observed": {},
        "B2_band_by_denom": {},
        "B2_structural_by_denom": {},
    }
    for k, va in sorted(fa.items()):
        vb = fb.get(k, [])
        if not va or not vb:
            continue
        ra = sum(va) / len(va)
        rb = sum(vb) / len(vb)
        res["B1_observed"][k] = {"a_rate": round(ra, 6), "b_rate": round(rb, 6),
                                 "diff_pp": round(100 * (ra - rb), 3)}
        dens = args.thread_denoms if k.startswith("thread:") else args.denoms
        res["B2_band_by_denom"][k] = {str(m): boot_rate_diff(va, vb, m, args.boot, rng)
                                      for m in dens}
    for k in ("turns_A", "msgs_per_thread"):
        if ta[k] and tb[k]:
            res["B2_structural_by_denom"][k] = {str(m): boot_median_diff(ta[k], tb[k], m, args.boot, rng)
                                                for m in args.denoms}

    txt = json.dumps(res, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if args.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
        open(args.out_json, "w", encoding="utf-8").write(txt + "\n")

    lines = ["# 噪声带两级估计（B1 观测差 + B2 bootstrap 抽样带）\n",
             f"- A: `{args.log_a}` (sha `{res['inputs']['log_a']['sha256']}`)",
             f"- B: `{args.log_b}` (sha `{res['inputs']['log_b']['sha256']}`)",
             f"- B={args.boot}，seed={args.seed}；分母档：{args.denoms}",
             "- **B1 只作参照；判定用 B2 同分母上界**。B2 = 两臂同分布时给定分母下差异的 2.5–97.5 分位。\n",
             "## B1 观测差（pp）\n", "| 指标 | A | B | Δ(A−B) pp |", "|---|---|---|---|"]
    for k, v in sorted(res["B1_observed"].items()):
        lines.append(f"| `{k}` | {v['a_rate']} | {v['b_rate']} | {v['diff_pp']} |")
    lines += ["\n## B2 抽样噪声带半宽（pp，分母档）\n",
              "| 指标 | " + " | ".join(f"m={m}" for m in args.denoms) + " |",
              "|---|" + "---|" * len(args.denoms)]
    for k, v in sorted(res["B2_band_by_denom"].items()):
        cells = [str(v.get(str(m), {}).get("halfwidth_pp")) for m in args.denoms]
        lines.append(f"| `{k}` | " + " | ".join(cells) + " |")
    lines += ["\n## B2 线程级比率（分母 = 线程数；**不得用消息级上界替代**）\n",
              "| 指标 | " + " | ".join(f"m={m}" for m in args.thread_denoms) + " |",
              "|---|" + "---|" * len(args.thread_denoms)]
    for k, v in sorted(res["B2_band_by_denom"].items()):
        if not k.startswith("thread:"):
            continue
        cells = [str(v.get(str(m), {}).get("halfwidth_pp")) for m in args.thread_denoms]
        lines.append(f"| `{k}` | " + " | ".join(cells) + " |")
    lines += ["\n## B2 结构类（per-thread 中位数差半宽）\n",
              "| 指标 | " + " | ".join(f"m={m}" for m in args.denoms) + " |",
              "|---|" + "---|" * len(args.denoms)]
    for k, v in sorted(res["B2_structural_by_denom"].items()):
        cells = [str(v.get(str(m), {}).get("halfwidth")) for m in args.denoms]
        lines.append(f"| `{k}` | " + " | ".join(cells) + " |")
    md = "\n".join(lines) + "\n"
    if args.out_md:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
        open(args.out_md, "w", encoding="utf-8").write(md)
    print(json.dumps({k: v for k, v in list(res["B1_observed"].items())[:4]}, ensure_ascii=False, indent=1))
    print(json.dumps({"out_json": args.out_json, "out_md": args.out_md}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
