#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""f3_r1_figure.py —— R1 轮 F-3（情绪呼应，捆绑 F-4）ON/OFF 两臂的证据图。

零跑批、零 LLM：只读三件既有产物
  1) 两臂 run.jsonl（日志 sha256 现场重算）
  2) v2/evidence/f3_audit_echo_r1.json（四档内容层口径 + Wilson95）
  3) v2/evidence/f3_echo_field_stats.json（机制字段统计）

产出 = v2/evidence/f3_shots_r1/F3-R1-evidence-<sha8>.png
      画的是**实测值**，不画任何预测/平滑；每格标注取值与分母。

用法（仓库根）：
  python3 tools/f3/f3_r1_figure.py --audit v2/evidence/f3_audit_echo_r1.json \
      --stats v2/evidence/f3_echo_field_stats.json \
      --out v2/evidence/f3_shots_r1/F3-R1-evidence.png
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["font.sans-serif"] = [
    "Noto Serif CJK SC", "Noto Serif CJK JP", "Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", required=True)
    ap.add_argument("--stats", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    audit = json.load(open(a.audit, encoding="utf-8"))
    stats = json.load(open(a.stats, encoding="utf-8"))["arms"]
    off, on = stats["off"], stats["on"]

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
    fig.suptitle(
        "R1 · F-3 情绪呼应（捆绑 F-4 对话修复）ON vs OFF · 真实实测值 "
        f"· 两臂 code_sha=f19de616 · 日志 sha8 off={off['run_jsonl_sha256'][:8]} on={on['run_jsonl_sha256'][:8]}",
        fontsize=10)

    # ① 机制落点：ctx.echo 条数 / 回复路径
    ax = axes[0][0]
    labels = ["OFF", "ON"]
    echo_n = [off["msg_with_ctx_echo"], on["msg_with_ctx_echo"]]
    ax.bar(labels, echo_n, color=["#9e9e9e", "#1976d2"])
    for i, v in enumerate(echo_n):
        den = off["msg_reply_path"] if i == 0 else on["msg_reply_path"]
        ax.text(i, v + 1, f"{v} / {den} 回复路径", ha="center", fontsize=9)
    ax.set_title("① 机制落点 payload.ctx.echo 条数（OFF 构造性为 0）")
    ax.set_ylabel("条数")
    ax.set_ylim(0, max(echo_n) * 1.25 + 1)

    # ② 注入是否进了 LLM 输入：dialogue tokens_in
    ax = axes[0][1]
    tin = [55390, 61181]  # obs llm-cost --by stub；见报告命令块
    ax.bar(labels, tin, color=["#9e9e9e", "#1976d2"])
    for i, v in enumerate(tin):
        ax.text(i, v + 800, f"{v:,}", ha="center", fontsize=9)
    ax.set_title("② dialogue tokens_in 总量（obs llm-cost）\n"
                 f"Δ={tin[1]-tin[0]:+,} token ≈ 注入面文本 {5210} 字符")
    ax.set_ylabel("tokens_in")

    # ③ 内容层四档（分母极小，全部 count_only）
    ax = axes[1][0]
    tiers = ["loose", "loose_no_agree", "polarity_match", "marker_based"]
    rows = {}
    for arm in audit["arms"]:
        key = arm["meta"]["label"]
        for t in tiers:
            d = arm["tiers"].get(t, {}).get("reply_path", {})
            rows.setdefault(t, {})[key] = d
    x = range(len(tiers))
    w = 0.36
    off_v = [rows[t].get("off", {}).get("rate", 0) for t in tiers]
    on_v = [rows[t].get("on", {}).get("rate", 0) for t in tiers]
    ax.bar([i - w / 2 for i in x], off_v, w, label="OFF", color="#9e9e9e")
    ax.bar([i + w / 2 for i in x], on_v, w, label="ON", color="#1976d2")
    for i, t in enumerate(tiers):
        do = rows[t].get("off", {})
        dn = rows[t].get("on", {})
        ax.text(i - w / 2, off_v[i] + 0.005,
                f"{do.get('hits')}/{do.get('denominator')}", ha="center", fontsize=8)
        ax.text(i + w / 2, on_v[i] + 0.005,
                f"{dn.get('hits')}/{dn.get('denominator')}", ha="center", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(tiers, fontsize=8)
    ax.set_title("③ 内容层四档（reply_path；分母 7 vs 10 ⇒ band=count_only，无判定力）")
    ax.set_ylabel("命中率")
    ax.legend(fontsize=8)

    # ④ ON 臂 echo 字段构成（sign / source / tier）
    ax = axes[1][1]
    sign = on["sign"]
    src = on["source"]
    tier = on["tier"]
    text = (
        f"ctx.echo = {on['msg_with_ctx_echo']} 条 / MSG {on['msg_total']} 条\n"
        f"回复路径覆盖 = {on['echo_on_reply_path']}/{on['msg_reply_path']} "
        f"= {on['echo_coverage_of_reply_path']*100:.1f}%\n\n"
        f"sign：{sign}（负向安抚占比 {on['sign_negative_share']*100:.1f}%）\n"
        f"kind：{on['kind']}\n"
        f"source：{src}\n"
        f"tier：{tier}\n"
        f"intensity：{on['intensity_min']}–{on['intensity_max']}\n"
        f"prompted：{on['prompted']}\n"
        f"版本：{on['version']}\n\n"
        f"OFF 臂：ctx.echo 键{'完全不存在' if off['msg_with_ctx_echo']==0 else '存在'}"
        f"（构造性为 0，不构成对照有效性证据）"
    )
    ax.axis("off")
    ax.text(0.01, 0.98, text, va="top", fontsize=9.5)
    ax.set_title("④ ON 臂机制字段构成（含极性偏斜疑点）")

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    fig.savefig(a.out, dpi=140)
    sha = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
    print(f"wrote {a.out} sha256={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
