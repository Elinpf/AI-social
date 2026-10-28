#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「句式模板化 / 记忆回指」读数图（matplotlib，只读 JSON，零联网）。

输入：`tools/metrics/template_repetition.py` 产出的 JSON。
输出：PNG（默认两图）——
  fig1 = 回指词族命中率（M2）+ 量化词 top-10（M3）
  fig2 = 句式骨架占比（M4）+ 作者维度 M1 命中率（M6，probe 格只画浅色不画率）

用法：
    python3 tools/metrics/template_repetition_plot.py \
        --json v2/evidence/template_ruler_r32/template_repetition_d12d_on.json \
        --out-dir v2/evidence/template_ruler_r32
"""

from __future__ import annotations

import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

CJK_CANDIDATES = ("Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Zen Hei",
                  "SimHei", "Source Han Sans SC", "Noto Serif CJK SC")


def setup_font() -> str:
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in CJK_CANDIDATES:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    plt.rcParams["axes.unicode_minus"] = False
    return "(no CJK font; labels may be boxes)"


def _layer(rep: dict, layer_id: str) -> dict:
    for l in rep["layers"]:
        if l["id"] == layer_id:
            return l
    raise SystemExit("缺少图层：" + layer_id)


def fig1(rep: dict, out_path: str) -> None:
    m2 = _layer(rep, "M2_backref_family")
    m3 = _layer(rep, "M3_qty_word_reuse")
    m1 = _layer(rep, "M1_backref_hit_rate")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))

    ax = axes[0]
    words = [r["word"] for r in m2["rows"]]
    rates = [r["rate_pct"] for r in m2["rows"]]
    ax.barh(range(len(words)), rates, color="#4C78A8")
    ax.set_yticks(range(len(words)))
    ax.set_yticklabels(words)
    ax.invert_yaxis()
    ax.set_xlabel("命中率 %（分母 = body 非空 MSG_* 条数）")
    ax.set_title("M2 回指词族逐词命中率（各词独立，禁止相加）")
    for i, r in enumerate(m2["rows"]):
        ax.text(rates[i] + 1.0, i, f"{r['numerator']}/{r['denominator']}",
                va="center", fontsize=8)
    ax.axvline(m1["rate_pct"], color="#E45756", linestyle="--", linewidth=1.2)
    ax.text(m1["rate_pct"] + 1.0, len(words) - 0.6,
            f"M1 锚点「上回」= {m1['numerator']}/{m1['denominator']} = {m1['rate_pct']:.2f}%",
            color="#E45756", fontsize=9)
    ax.set_xlim(0, 100)

    ax = axes[1]
    toks = [t["token"] for t in m3["top"]]
    cnts = [t["count"] for t in m3["top"]]
    ax.barh(range(len(toks)), cnts, color="#F58518")
    ax.set_yticks(range(len(toks)))
    ax.set_yticklabels(toks)
    ax.invert_yaxis()
    ax.set_xlabel("词次（出现次数）")
    ax.set_title(f"M3 量化词 top-{len(toks)}（词次 {m3['pair_tokens_total']} / 词型 "
                 f"{m3['pair_types_distinct']} / 复用率 {m3['reuse_rate']*100:.2f}%）")
    for i, c in enumerate(cnts):
        ax.text(c + 1.0, i, str(c), va="center", fontsize=8)

    fig.suptitle(f"句式模板化 / 记忆回指污染 · 批次 {rep.get('batch_id')} · "
                 f"日志 {rep['inputs']['log_sha256'][:12]}…", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig2(rep: dict, out_path: str) -> None:
    m4 = _layer(rep, "M4_skeleton_share")
    m6 = _layer(rep, "M6_by_from")
    m5 = _layer(rep, "M5_backref_frames")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))

    ax = axes[0]
    labels = [r["id"].split("_", 1)[1] for r in m4["rows"]]
    rates = [r["rate_pct"] for r in m4["rows"]]
    labels.append("S5_first6_distinct_ratio")
    s5 = m4["S5_first6"]
    rates.append(100.0 * s5["distinct_over_denominator"])
    colors = ["#54A24B"] * (len(rates) - 1) + ["#B279A2"]
    ax.bar(range(len(rates)), rates, color=colors)
    ax.set_xticks(range(len(rates)))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("%")
    ax.set_title("M4 句式骨架占比（S1–S4 占比；S5 = 首6字 distinct/条数）")
    for i, r in enumerate(m4["rows"]):
        ax.text(i, rates[i] + 0.8, f"{r['numerator']}/{r['denominator']}", ha="center", fontsize=8)
    ax.text(len(rates) - 1, rates[-1] + 0.8, f"{s5['distinct']}/{s5['denominator']}",
            ha="center", fontsize=8)
    ax.set_ylim(0, max(rates) + 8)

    ax = axes[1]
    ok = [r for r in m6["rows"] if r["label"] == "ok"]
    probe = [r for r in m6["rows"] if r["label"] != "ok"]
    keys = [r["key"] for r in ok]
    vals = [r["rate_pct"] for r in ok]
    ax.bar(range(len(ok)), vals, color="#4C78A8")
    ax.set_xticks(range(len(ok)))
    ax.set_xticklabels(keys, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("M1 命中率 %")
    ax.set_title(f"M6 作者维度 M1 命中率（probe 格 {len(probe)} 个只计数不画率）")
    for i, r in enumerate(ok):
        ax.text(i, vals[i] + 1.0, f"{r['numerator']}/{r['denominator']}", ha="center", fontsize=7)
    if probe:
        ax.text(0.02, 0.98, "probe（分母<30，未画）：" + ", ".join(
            f"{r['key']}={r['hit']}/{r['n']}" for r in probe),
            transform=ax.transAxes, va="top", fontsize=7, color="#666666")
    ax.set_ylim(0, 110)

    fig.suptitle(f"M5 回指帧去重：{m5['frames_distinct']} 帧 / {m5['backref_messages']} 条命中"
                 f"（distinct/hit = {m5['distinct_frames_per_hit']:.4f}）", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="句式模板化读数图（只读 JSON）")
    ap.add_argument("--json", required=True, help="template_repetition.py 的输出 JSON")
    ap.add_argument("--out-dir", required=True, help="PNG 输出目录")
    args = ap.parse_args(argv)

    if not os.path.exists(args.json):
        raise SystemExit("JSON 不存在: " + args.json)
    rep = json.load(open(args.json, encoding="utf-8"))
    os.makedirs(args.out_dir, exist_ok=True)
    f1 = os.path.join(args.out_dir, "fig1_backref_family_and_qty_reuse.png")
    f2 = os.path.join(args.out_dir, "fig2_skeleton_share_and_author_rate.png")
    font = setup_font()
    fig1(rep, f1)
    fig2(rep, f2)
    print(f"[plot] font={font}")
    for p in (f1, f2):
        print(f"[plot] {p} bytes={os.path.getsize(p)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
