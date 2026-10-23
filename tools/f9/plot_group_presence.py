#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""群体聚集 / 同场共处 / 独处-空闲 —— 只读读数作图器（CYCLE-16 用）。

只读：输入为 r1-measure 落盘的读数 JSON，不读 run.jsonl 之外的任何东西，
      不写日志、不跑批、不修改 code/ 任何文件。

用法（仓库根 social-experiment/ 下）：
    python3 tools/f9/plot_group_presence.py \
        --metrics v2/evidence/group_presence_20261024/group_presence_metrics.json \
        --outdir  v2/evidence/group_presence_20261024/charts

输出（3 张独立 PNG，不拼接、不合图、不复用历史旧图）：
    fig1_activity_participants_size.png   ACTIVITY_STARTED 的 participants 人数分布
    fig2_copresence_group_size.png        同场共处 (day,slot,place) 三元组的人数分布（不含 residence 主口径）
    fig3_place_arrived_by_place.png       PLACE_ARRIVED 按地点频次

每张图的标题里都写了「数据来源 = metrics JSON 的哪个字段」，便于溯源。
"""
import argparse
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# 中文字体：优先用系统里的 Noto CJK；找不到就退回英文标题（图内仍可读）
CJK_CANDIDATES = [
    "Noto Sans CJK SC",
    "Noto Serif CJK SC",
    "WenQuanYi Zen Hei",
    "Source Han Sans SC",
    "SimHei",
]
FIG_DPI = 150


def setup_font():
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in CJK_CANDIDATES:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    return None


def fig1(metrics, outdir, cjk):
    dist = metrics["gathering"]["activity_started"]["participants_size_distribution"]
    ratio = metrics["gathering"]["activity_started"]["multi_person_ratio"]
    keys = sorted(int(k) for k in dist)
    vals = [dist[str(k)] for k in keys]
    total = sum(vals)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    bars = ax.bar([str(k) for k in keys], vals, color="#4a7ebb", width=0.55)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 4,
            f"{v}\n({v / total * 100:.2f}%)",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_ylim(0, max(vals) * 1.30)
    ax.set_xlabel(("participants 人数" if cjk else "len(participants)"))
    ax.set_ylabel(("ACTIVITY_STARTED 行数" if cjk else "ACTIVITY_STARTED rows"))
    ax.set_title(
        (
            f"ACTIVITY_STARTED 的 participants 人数分布（N={total} agent-槽）\n"
            f"多人(>=2) {ratio['numerator']}/{ratio['denominator']} = {ratio['value']*100:.2f}%"
        )
        if cjk
        else (
            f"participants size distribution (N={total} agent-slots); "
            f"multi-person {ratio['numerator']}/{ratio['denominator']} = {ratio['value']*100:.2f}%"
        ),
        fontsize=10,
    )
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    fig.text(
        0.01,
        0.01,
        "source field: gathering.activity_started.participants_size_distribution",
        fontsize=7,
        alpha=0.7,
    )
    out = os.path.join(outdir, "fig1_activity_participants_size.png")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out, dpi=FIG_DPI)
    plt.close(fig)
    return out


def fig2(metrics, outdir, cjk):
    cp = metrics["copresence"]
    excl = cp["variant_excluding_residence"]
    incl = cp["variant_including_residence"]
    h = {int(k): v for k, v in excl["place_groups_size_histogram"].items()}
    keys = sorted(h)
    vals = [h[k] for k in keys]
    total = excl["place_groups_total"]

    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    bars = ax.bar([str(k) for k in keys], vals, color="#5f9ea0" if False else "#3f8f6b", width=0.62)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.5,
            str(v),
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_ylim(0, max(vals) * 1.28)
    ax.set_xlabel(("同处人数（(day,slot,place) 三元组内人数）" if cjk else "co-present persons per (day,slot,place) group"))
    ax.set_ylabel(("三元组个数" if cjk else "number of groups"))
    ge2 = excl["ratio_of_place_groups_ge2"]
    per = excl["ratio_of_persons_in_ge2_group"]
    title = (
        f"同场共处三元组人数分布（不含 residence；三元组 N={total}）\n"
        f">=2 人三元组 {ge2['numerator']}/{ge2['denominator']} = {ge2['value']*100:.2f}%；"
        f"身处 >=2 人地点 {per['numerator']}/{per['denominator']} = {per['value']*100:.2f}%"
        if cjk
        else (
            f"co-presence group size (excl. residence, N={total}); "
            f">=2 persons {ge2['numerator']}/{ge2['denominator']} = {ge2['value']*100:.2f}%; "
            f"persons in >=2 groups {per['numerator']}/{per['denominator']} = {per['value']*100:.2f}%"
        )
    )
    ax.set_title(title, fontsize=10)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    fig.text(
        0.01,
        0.01,
        "source field: copresence.variant_excluding_residence.place_groups_size_histogram"
        f" | incl.residence groups={incl['place_groups_total']} (not plotted)",
        fontsize=7,
        alpha=0.7,
    )
    out = os.path.join(outdir, "fig2_copresence_group_size.png")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out, dpi=FIG_DPI)
    plt.close(fig)
    return out


def fig3(metrics, outdir, cjk):
    by_place = metrics["gathering"]["place_arrived"]["by_place"]
    total = metrics["gathering"]["place_arrived"]["total"]
    items = sorted(by_place.items(), key=lambda kv: (-kv[1], kv[0]))
    labels = [k for k, _ in items]
    vals = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    bars = ax.barh(labels[::-1], vals[::-1], color="#b5651d")
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 0.8, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=8.5)
    ax.set_xlim(0, max(vals) * 1.18)
    ax.set_xlabel(("PLACE_ARRIVED 次数" if cjk else "PLACE_ARRIVED count"))
    ax.set_title(
        (
            f"PLACE_ARRIVED 按地点频次（N={total}；21 个 agent-槽原地未移动）"
            if cjk
            else f"PLACE_ARRIVED by place (N={total}; 21 agent-slots did not move)"
        ),
        fontsize=10,
    )
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    fig.text(
        0.01,
        0.01,
        "source field: gathering.place_arrived.by_place",
        fontsize=7,
        alpha=0.7,
    )
    out = os.path.join(outdir, "fig3_place_arrived_by_place.png")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out, dpi=FIG_DPI)
    plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser(description="只读作图：群体聚集/同场共处/独处-空闲读数")
    ap.add_argument("--metrics", required=True, help="group_presence_metrics.json 路径")
    ap.add_argument("--outdir", required=True, help="PNG 输出目录")
    args = ap.parse_args()

    if not os.path.isfile(args.metrics):
        print(f"metrics not found: {args.metrics}", file=sys.stderr)
        return 2
    with open(args.metrics, encoding="utf-8") as f:
        metrics = json.load(f)
    os.makedirs(args.outdir, exist_ok=True)

    cjk = setup_font()
    outs = [fig1(metrics, args.outdir, cjk), fig2(metrics, args.outdir, cjk), fig3(metrics, args.outdir, cjk)]
    print(f"cjk_font={cjk}")
    for o in outs:
        print(f"wrote {o} ({os.path.getsize(o)} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
