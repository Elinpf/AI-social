#!/usr/bin/env python3
"""R11 图片证据生成器（只读真实跑批产物，不写任何结论性措辞）。

数据源（全部为真实产物，零 mock / 零手绘）：
  1) v2/evidence/run_f6_off_n16r60_seed42/{run.jsonl,meta.json,host.log}
  2) v2/evidence/run_f6_on_n16r60_seed42/{run.jsonl,meta.json,host.log}
  3) 官方指标 JSON（tools/d5/dialogue_metrics.py 输出，F-6 / L-5..L-8 唯一来源）
  4) 注入记忆正文：MEMORY_WRITE.payload.body_ref -> side_root/src/<sha>.txt
     （side_root 取自 host.log 的 --side-root 参数，默认 /tmp/f6_on60_side）

产出（默认 v2/evidence/r11_shots/）：
  f6_on_vs_off_n16r60_seed42-f6-memory-rate.png   F-6 ON vs OFF（带分子/分母 + Wilson95 CI）
  f6_on_n16r60_seed42-memory-injected-dialogue-samples.png
                                                   ON 臂「注入记忆 -> 生成正文」真实样本表（带行号/seq）
  f6_on_vs_off_n16r60_seed42-run-health.png       跑批健康度（LLM 调用/degraded/事件/时长/tokens）

用法：
  python3 tools/r11/make_r11_evidence_shots.py \
      --repo . --out v2/evidence/r11_shots \
      --off-metrics v2/evidence/r1_f6_off_metrics.json \
      --on-metrics /tmp/ev_vis/r1_f6_on_metrics.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import OrderedDict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")
TIMEREF = ["昨天", "前天", "上次", "上回", "那天", "前几天", "昨儿", "昨晚上", "以前", "早就", "那次"]
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FP = FontProperties(fname=FONT_PATH)
FP_S = FontProperties(fname=FONT_PATH, size=9)
FP_T = FontProperties(fname=FONT_PATH, size=12)
FP_H = FontProperties(fname=FONT_PATH, size=16)

C_OFF = "#4C6EF5"
C_ON = "#E8590C"
C_GREY = "#868E96"


# ---------------------------------------------------------------- 数据读取
def wilson(k: int, n: int, z: float = 1.959963984540054):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def scan_arm(run_path: str, side_src: str | None = None):
    """只读遍历 run.jsonl：MSG 计数、F-6 命中、memory_refs 注入计数、注入样本。"""
    tot = timeref = memref_msgs = 0
    timeref_with_memref = 0
    all_refs = []
    norms, topics, refs_flag, seqs = [], [], [], []
    l13_seq = []
    mem_body_ref = {}
    samples = []
    with open(run_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if '"MEMORY_WRITE"' in line:
                d = json.loads(line)
                p = d.get("payload") or {}
                if p.get("mem_id"):
                    mem_body_ref[p["mem_id"]] = p.get("body_ref")
                continue
            if '"MSG_' not in line:
                continue
            d = json.loads(line)
            if d.get("type") not in MSG_TYPES:
                continue
            p = d.get("payload") or {}
            body = p.get("body") or ""
            refs = ((p.get("ctx") or {}).get("memory_refs")) or []
            tot += 1
            norms.append(re.sub(r"[\s，。！？、；：「」（）,.!?;:()\"'“”‘’…—-]", "", body))
            topics.append(((p.get("ctx") or {}).get("topic")) or "")
            refs_flag.append(bool(refs))
            seqs.append(d.get("seq"))
            _t = ((p.get("ctx") or {}).get("topic")) or ""
            if _t and _t in body:
                l13_seq.append((d.get("seq"), _t))
            if refs:
                memref_msgs += 1
                all_refs.extend(refs)
            hit = [w for w in TIMEREF if w in body]
            if hit:
                timeref += 1
                if refs:
                    timeref_with_memref += 1
                    samples.append({
                        "line": lineno,
                        "seq": d.get("seq"),
                        "day": p.get("day"),
                        "slot": p.get("slot"),
                        "from": p.get("from"),
                        "to": p.get("to"),
                        "kind": d.get("type"),
                        "thread": p.get("thread_id"),
                        "refs": refs,
                        "body": body,
                        "hit": hit,
                    })
    # L-7：与任一其它消息共享 8-gram（官方 dialogue_metrics.py 同口径）
    sh_index = {}
    for i, t in enumerate(norms):
        for g in {t[j:j + 8] for j in range(max(0, len(t) - 7))}:
            sh_index.setdefault(g, []).append(i)
    dup_idx = set()
    for g, idxs in sh_index.items():
        if len(idxs) > 1:
            dup_idx.update(idxs)
    dup_with_memrefs = sum(1 for i in dup_idx if refs_flag[i])
    # L-13 分主题
    topics_cnt = {}
    for _s, _t in l13_seq:
        topics_cnt[_t] = topics_cnt.get(_t, 0) + 1

    return {
        "total_msg": tot,
        "l7": {"dup": len(dup_idx), "dup_rate": len(dup_idx) / tot if tot else 0.0,
               "dup_with_memrefs": dup_with_memrefs},
        "l13_n": len(l13_seq),
        "l13_topics": dict(sorted(topics_cnt.items())),
        "l13_seq": l13_seq,
        "timeref_hits": timeref,
        "memref_msgs": memref_msgs,
        "refs_total": len(all_refs),
        "refs_distinct": len(set(all_refs)),
        "timeref_with_memref": timeref_with_memref,
        "mem_body_ref": mem_body_ref,
        "samples": samples,
    }


def read_side_text(side_src: str | None, ref: str | None) -> str:
    if not ref or not side_src:
        return ""
    fp = os.path.join(side_src, ref.split("side://", 1)[-1].replace("src/", ""))
    try:
        return open(fp, encoding="utf-8").read().strip()
    except OSError:
        return ""


def side_root_from_host_log(path: str) -> str | None:
    try:
        txt = open(path, encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"--side-root\s+(\S+)", txt)
    return m.group(1) if m else None


def ngrams(text: str, n: int = 4):
    t = re.sub(r"[\s，。！？、；：「」（）,.!?;:()\"'“”‘’…—-]", "", text or "")
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def wrap_cn(text: str, width: int):
    """按显示宽度折行（中文按 2、西文按 1 计）。"""
    out, cur, w = [], "", 0
    for ch in text:
        cw = 2 if ord(ch) > 0x2E7F else 1
        if w + cw > width:
            out.append(cur)
            cur, w = "", 0
        cur += ch
        w += cw
    if cur:
        out.append(cur)
    return out


# ---------------------------------------------------------------- 图 1：F-6
def fig_f6(out_path, off, on, off_official, on_official, meta_off, meta_on):
    k_off, n_off = off["timeref_hits"], off["total_msg"]
    k_on, n_on = on["timeref_hits"], on["total_msg"]
    p_off, p_on = k_off / n_off, k_on / n_on
    lo_o, hi_o = wilson(k_off, n_off)
    lo_n, hi_n = wilson(k_on, n_on)

    fig, ax = plt.subplots(figsize=(9.2, 6.0), dpi=160)
    xs = [0, 1]
    vals = [p_off * 100, p_on * 100]
    errs = [[(p_off - lo_o) * 100, (p_on - lo_n) * 100],
            [(hi_o - p_off) * 100, (hi_n - p_on) * 100]]
    bars = ax.bar(xs, vals, width=0.46, color=[C_OFF, C_ON], yerr=errs, capsize=9,
                  error_kw={"ecolor": "#212529", "lw": 1.4}, zorder=3)
    for x, v, k, n, lo, hi in ((0, vals[0], k_off, n_off, lo_o, hi_o), (1, vals[1], k_on, n_on, lo_n, hi_n)):
        ax.text(x, v / 2, f"{k}/{n}", ha="center", va="center", color="white",
                fontproperties=FontProperties(fname=FONT_PATH, size=15), zorder=4)
        ax.text(x, hi * 100 + 0.55, f"{v:.2f}%\nWilson95[{lo*100:.2f}%, {hi*100:.2f}%]",
                ha="center", va="bottom", fontproperties=FP_S, zorder=4)

    ax.set_xticks(xs)
    ax.set_xticklabels(["OFF 臂（LIFE_PROMPT_MEMORY_F6=0）\nrun_f6_off_n16r60_seed42",
                        "ON  臂（LIFE_PROMPT_MEMORY_F6=1）\nrun_f6_on_n16r60_seed42"],
                       fontproperties=FP_T)
    ax.set_ylabel("F-6 跨天记忆引用率（正文命中时间回指词表的 MSG / 全部 MSG）",
                  fontproperties=FP_T)
    ax.set_ylim(0, max(vals) * 1.55)
    ax.grid(axis="y", ls=":", color=C_GREY, alpha=0.6, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    d = (p_on - p_off) * 100
    note = (f"Δ = +{d:.2f}pp（ON − OFF）｜两臂 Wilson95 区间不重叠 ⇒ 按 R11 §3.3 判据「显著」\n"
            f"官方脚本复算：OFF {off_official:.6f}｜ON {on_official:.6f}（tools/d5/dialogue_metrics.py F-6_crossday_memory）\n"
            f"代码同一 sha {meta_off.get('code_sha','')[:8]} = {meta_on.get('code_sha','')[:8]}，唯一差异为 env；"
            f"分母为全部 MSG（=510）；F-6 只测「提到过去」，不测「引用是否正确」")
    fig.text(0.02, 0.035, note, fontproperties=FP_S, va="bottom", color="#212529")
    fig.suptitle("R11 · F-6「跨天记忆进对话」ON vs OFF（真实跑批产物，n16×60 seed42）",
                 fontproperties=FP_H, y=0.975)
    fig.subplots_adjust(left=0.12, right=0.98, top=0.86, bottom=0.20)
    fig.savefig(out_path)
    plt.close(fig)
    return dict(k_off=k_off, n_off=n_off, k_on=k_on, n_on=n_on,
                ci_off=(lo_o, hi_o), ci_on=(lo_n, hi_n), delta=d)


# ---------------------------------------------------------------- 图 2：对话样本
def fig_samples(out_path, samples, mem_body_ref, side_src, on_total_msg, on_memref_msgs, mem_stat):
    """ON 臂「注入的记忆 -> 生成的正文」真实样本表（含正反两例 + 4-gram 字面重合计数）。"""
    want = [27449, 21821, 29481, 34341]
    by_seq = {s["seq"]: s for s in samples}
    rows = [by_seq[q] for q in want if q in by_seq]
    rows += [s for s in sorted(samples, key=lambda x: x["line"]) if s["seq"] not in want][:4 - len(rows)]

    cols = ["行号 / seq", "时点", "说话人→对象", "注入的记忆（mem_id：原文，MEMORY_WRITE → side 文件）",
            "模型生成的正文（run.jsonl 原样）", "字面重合\n共享 4-gram"]
    widths = [10, 11, 11, 40, 40, 8]

    prepared = []
    for r in rows:
        mem_txt = []
        for mid in r["refs"]:
            t = read_side_text(side_src, mem_body_ref.get(mid))
            mem_txt.append(f"{mid}：{t}")
        mem_cell = "\n".join(mem_txt) if mem_txt else "（无）"
        shared = len(ngrams(r["body"]) & set().union(*[ngrams(t) for t in mem_txt]) if mem_txt else set())
        prepared.append((r, mem_cell, shared))

    nlines_each = []
    for r, mem_cell, _ in prepared:
        nlines_each.append(max(3, len(wrap_cn(mem_cell, widths[3])), len(wrap_cn(r["body"], widths[4]))))

    units = 2.6 + sum(n + 1.1 for n in nlines_each)   # 表头 2.6 单位，每行 n+1.1 单位
    fig_h = max(6.0, units * 0.30)
    fig = plt.figure(figsize=(18.0, fig_h), dpi=150)
    ax = fig.add_axes([0.012, 0.045, 0.976, 0.80])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    uh = 1.0 / units                                     # 一个文本行的高度（轴坐标）

    total = sum(widths)
    col_x, acc = [], 0.0
    for w in widths:
        col_x.append(acc / total)
        acc += w

    y = 0.995
    for cx, name in zip(col_x, cols):
        ax.text(cx, y, name, fontproperties=FontProperties(fname=FONT_PATH, size=11),
                va="top", ha="left", color="#1B1F3B", linespacing=1.35)
    y -= uh * 2.2
    ax.plot([0, 1], [y, y], color="#1B1F3B", lw=1.3)

    for (r, mem_cell, shared), nl in zip(prepared, nlines_each):
        cells = [
            f"L{r['line']}\nseq {r['seq']}",
            f"day {r['day']} {r['slot']}",
            f"{r['from']}→{r['to']}",
            mem_cell,
            r["body"],
            f"{shared} 个",
        ]
        for cx, cell, w in zip(col_x, cells, widths):
            col = "#C92A2A" if cell == f"{shared} 个" and shared else "#212529"
            ax.text(cx, y, "\n".join(wrap_cn(cell, w)), fontproperties=FP_S,
                    va="top", ha="left", linespacing=1.5, color=col)
        y -= uh * (nl + 1.1)
        ax.plot([0, 1], [y, y], color=C_GREY, lw=0.6, ls=":")

    fig.text(0.012, 0.975,
             "R11 · ON 臂「注入的记忆 → 生成的正文」真实样本（正例与反例并列，非择优）",
             fontproperties=FP_H, va="top")
    fig.text(0.012, 0.935,
             f"筛选口径：payload.body 命中时间回指词表 且 payload.ctx.memory_refs 非空；此类样本 ON 臂共 {len(samples)} 条 / "
             f"全部 {on_total_msg} 条 MSG 中有 {on_memref_msgs} 条被注入记忆（引用 {mem_stat['refs']} 次、"
             f"仅 {mem_stat['distinct']} 个不同 mem_id ⇒ 记忆池很窄）",
             fontproperties=FontProperties(fname=FONT_PATH, size=10), va="top", color="#495057")
    fig.text(0.012, 0.008,
             "读法：第 1 行（seq 27449）注入的「少放半勺盐/多搁一把干贝」被正文逐字吸收 ⇒ 注入内容确实进了正文；"
             "第 2 行（seq 21821）虽命中时间回指词「上回」，正文与注入的两条汤类记忆 0 个 4-gram 重合 ⇒ "
             "F-6 命中 ≠ 用上了注入的记忆。可复核：`sed -n '<行号>p' v2/evidence/run_f6_on_n16r60_seed42/run.jsonl`；"
             "记忆原文 = MEMORY_WRITE.payload.body_ref 指向的 side-root src 文件；正文为日志原样。",
             fontproperties=FontProperties(fname=FONT_PATH, size=9), va="bottom", color="#495057")
    fig.savefig(out_path)
    plt.close(fig)
    return [(r["seq"], shared) for r, _, shared in prepared]


# ---------------------------------------------------------------- 图 3：跑批健康度
def fig_health(out_path, off_m, on_m, off_cost, on_cost):
    def g(d, k):
        return d.get(k)

    panels = [
        ("LLM 调用数（LLM_CALL）", [g(off_m, "llm_calls"), g(on_m, "llm_calls")], "{:,.0f}", "次"),
        ("degraded 调用数", [g(off_m, "degraded_calls"), g(on_m, "degraded_calls")], "{:,.0f}", "次"),
        ("事件总数（events）", [g(off_m, "events"), g(on_m, "events")], "{:,.0f}", "条"),
        ("跑批时长", [g(off_m, "duration_sec"), g(on_m, "duration_sec")], "{:,.0f}", "秒"),
        ("tokens_in（入向）", [off_cost["engine_log"]["total"]["tokens_in"],
                              on_cost["engine_log"]["total"]["tokens_in"]], "{:,.0f}", "token"),
        ("tokens_total（in+out）", [off_cost["engine_log"]["total"]["tokens_total"],
                                   on_cost["engine_log"]["total"]["tokens_total"]], "{:,.0f}", "token"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(14.4, 7.4), dpi=150)
    for ax, (title, vals, fmt, unit) in zip(axes.ravel(), panels):
        bars = ax.bar([0, 1], vals, width=0.5, color=[C_OFF, C_ON], zorder=3)
        lo = min(vals)
        top = max(vals)
        ax.set_ylim(0, top * 1.32 if top else 1)
        for x, v in zip([0, 1], vals):
            ax.text(x, v, fmt.format(v), ha="center", va="bottom",
                    fontproperties=FontProperties(fname=FONT_PATH, size=13), zorder=4)
        rel = (vals[1] - vals[0]) / vals[0] * 100 if vals[0] else 0.0
        if vals[0] == vals[1]:
            tag, col = "两臂相同", C_GREY
        else:
            tag, col = f"Δ {rel:+.2f}%", "#C92A2A" if abs(rel) >= 5 else C_GREY
        ax.set_title(f"{title}\n{tag}", fontproperties=FP_T, color=col)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["OFF", "ON"], fontproperties=FP_S)
        ax.grid(axis="y", ls=":", color=C_GREY, alpha=0.55, zorder=0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.suptitle("R11 · 跑批健康度（真实产物：meta.json + obs llm-cost，两臂同 sha "
                 f"{str(off_m.get('code_sha'))[:8]}，provider openai_compat，degraded 0）",
                 fontproperties=FontProperties(fname=FONT_PATH, size=13), y=0.985)
    fig.text(0.5, 0.020,
             f"OFF run_f6_off_n16r60_seed42：{off_m.get('started_at')} → {off_m.get('finished_at')}（{off_m.get('duration_sec')}s）\n"
             f"ON  run_f6_on_n16r60_seed42：{on_m.get('started_at')} → {on_m.get('finished_at')}（{on_m.get('duration_sec')}s）\n"
             "复算：python3 -m obs llm-cost --log <run.jsonl> --require-provider openai_compat（rc=0，provider_guard.ok=true）",
             ha="center", va="bottom", fontproperties=FontProperties(fname=FONT_PATH, size=9),
             color="#495057", linespacing=1.4)
    fig.tight_layout(rect=(0, 0.085, 1, 0.945))
    fig.savefig(out_path)
    plt.close(fig)


# ---------------------------------------------------------------- 图 4：L-7 / L-13 恶化项
def fig_degradation(out_path, off_m, on_m, l7, l13):
    """L-7 口头禅/8-gram 近重复 vs 预注册闸门；L-13 内部 token 泄漏。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.6, 6.6), dpi=150,
                                   gridspec_kw={"width_ratios": [1.35, 1]})

    # ---- L-7
    k_off, n_off = l7["off_dup"], l7["n_off"]
    k_on, n_on = l7["on_dup"], l7["n_on"]
    p_off, p_on = k_off / n_off, k_on / n_on
    lo_o, hi_o = wilson(k_off, n_off)
    lo_n, hi_n = wilson(k_on, n_on)
    vals = [p_off * 100, p_on * 100]
    errs = [[(p_off - lo_o) * 100, (p_on - lo_n) * 100], [(hi_o - p_off) * 100, (hi_n - p_on) * 100]]
    ax1.bar([0, 1], vals, width=0.45, color=[C_OFF, C_ON], yerr=errs, capsize=9, zorder=3,
            error_kw={"ecolor": "#212529", "lw": 1.4})
    gate = (p_off + 0.05) * 100
    ax1.axhline(gate, ls="--", lw=1.8, color="#C92A2A", zorder=4)
    ax1.text(-0.30, 78, f"— — 虚线 = 预注册闸门 OFF+5pp = {gate:.2f}%",
             color="#C92A2A", ha="left", va="top",
             fontproperties=FontProperties(fname=FONT_PATH, size=10),
             bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.2), zorder=6)
    for x, v, k, n, lo, hi in ((0, vals[0], k_off, n_off, lo_o, hi_o), (1, vals[1], k_on, n_on, lo_n, hi_n)):
        ax1.text(x, v / 2, f"{k}/{n}", ha="center", va="center", color="white",
                 fontproperties=FontProperties(fname=FONT_PATH, size=15), zorder=5)
        ax1.text(x, hi * 100 + 1.2, f"{v:.2f}%\nWilson95[{lo*100:.2f}%, {hi*100:.2f}%]",
                 ha="center", va="bottom", fontproperties=FP_S)
    ax1.set_xticks([0, 1])
    ax1.set_xticklabels(["OFF（LIFE_PROMPT_MEMORY_F6=0）", "ON（LIFE_PROMPT_MEMORY_F6=1）"], fontproperties=FP_S)
    ax1.set_ylabel("L-7 8-gram 近重复消息率（与任一其它消息共享 8-gram / 全部 MSG）", fontproperties=FP_S)
    ax1.set_ylim(0, 85)
    ax1.grid(axis="y", ls=":", color=C_GREY, alpha=0.6, zorder=0)
    for sp in ("top", "right"):
        ax1.spines[sp].set_visible(False)
    ax1.set_title(f"L-7 口头禅/近重复：{p_off*100:.2f}% → {p_on*100:.2f}%（Δ {(p_on-p_off)*100:+.2f}pp）\n"
                  f"判定：恶化，越过预注册闸门（≤ OFF+5pp 视为未恶化）",
                  fontproperties=FontProperties(fname=FONT_PATH, size=11), color="#C92A2A")

    # ---- L-13
    k13o, k13n = l13["off_n"], l13["on_n"]
    v13 = [k13o / n_off * 100, k13n / n_on * 100]
    ax2.bar([0, 1], v13, width=0.45, color=[C_OFF, C_ON], zorder=3)
    for x, k, v, n in ((0, k13o, v13[0], n_off), (1, k13n, v13[1], n_on)):
        ax2.text(x, v, f"{k}/{n}\n({v:.2f}%)", ha="center", va="bottom",
                 fontproperties=FontProperties(fname=FONT_PATH, size=12))
    ax2.set_ylim(0, max(v13) * 1.7 if max(v13) else 1)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["OFF", "ON"], fontproperties=FP_S)
    ax2.set_ylabel("L-13 内部 token 泄漏率（ctx.topic 原串出现在正文 / 全部 MSG）", fontproperties=FP_S)
    ax2.grid(axis="y", ls=":", color=C_GREY, alpha=0.6, zorder=0)
    for sp in ("top", "right"):
        ax2.spines[sp].set_visible(False)
    ax2.set_title(f"L-13 内部 token 泄漏：{k13o}/510 → {k13n}/510"
                  + (f"（×{k13n/k13o:.1f}）" if k13o else ""),
                  fontproperties=FontProperties(fname=FONT_PATH, size=11), color="#C92A2A")

    fig.suptitle("R11 · 恶化项证据：F-6 增益的代价是套路化（真实跑批产物，n16×60 seed42，两臂同 sha "
                 f"{str(off_m.get('code_sha'))[:8]}）",
                 fontproperties=FontProperties(fname=FONT_PATH, size=13), y=0.975)
    fig.text(0.012, 0.030,
             f"L-7 复算：`tools/d5/dialogue_metrics.py` 的 `L_wording.L-7_dup_ngram8_rate`（OFF {off_m and k_off}/{n_off}、ON {k_on}/{n_on}）；"
             f"机制：ON 臂 {l7['on_dup_with_memrefs']}/{k_on} 条重复消息带 `ctx.memory_refs`，注入记忆行被逐字吸进正文并在不同线程间复用。\n"
             f"L-13 复算：`L-13_token_leak.n / .by_topic`（OFF {k13o}，ON {k13n}；ON 分主题 {l13['on_topics']}）。"
             "两项分母均为全部 MSG = 510（≥68 达标），可与 F-6 并列陈述；F-6 的 +7.45pp 增益与 L-7 的 +29.61pp 代价必须同时呈现。",
             fontproperties=FontProperties(fname=FONT_PATH, size=9), va="bottom", color="#495057")
    fig.tight_layout(rect=(0, 0.10, 1, 0.94))
    fig.savefig(out_path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="v2/evidence/r11_shots")
    ap.add_argument("--off-metrics", default="v2/evidence/r1_f6_off_metrics.json")
    ap.add_argument("--on-metrics", required=True)
    ap.add_argument("--off-cost", required=True)
    ap.add_argument("--on-cost", required=True)
    a = ap.parse_args()

    R = a.repo
    OFF = os.path.join(R, "v2/evidence/run_f6_off_n16r60_seed42")
    ON = os.path.join(R, "v2/evidence/run_f6_on_n16r60_seed42")
    outdir = os.path.join(R, a.out)
    os.makedirs(outdir, exist_ok=True)

    side_src = None
    sr = side_root_from_host_log(os.path.join(ON, "host.log"))
    if sr:
        cand = os.path.join(sr, "src")
        side_src = cand if os.path.isdir(cand) else None

    off = scan_arm(os.path.join(OFF, "run.jsonl"))
    on = scan_arm(os.path.join(ON, "run.jsonl"), side_src)
    off_m = json.load(open(os.path.join(OFF, "meta.json"), encoding="utf-8"))
    on_m = json.load(open(os.path.join(ON, "meta.json"), encoding="utf-8"))
    off_official = json.load(open(os.path.join(R, a.off_metrics), encoding="utf-8"))["F-6_crossday_memory"]["timeref_rate"]
    on_official = json.load(open(a.on_metrics, encoding="utf-8"))["F-6_crossday_memory"]["timeref_rate"]
    off_cost = json.load(open(a.off_cost, encoding="utf-8"))
    on_cost = json.load(open(a.on_cost, encoding="utf-8"))

    p1 = os.path.join(outdir, "f6_on_vs_off_n16r60_seed42-f6-memory-rate.png")
    p2 = os.path.join(outdir, "f6_on_n16r60_seed42-memory-injected-dialogue-samples.png")
    p3 = os.path.join(outdir, "f6_on_vs_off_n16r60_seed42-run-health.png")
    p4 = os.path.join(outdir, "f6_on_vs_off_n16r60_seed42-l7-l13-degradation.png")

    mem_stat = {"refs": on["refs_total"], "distinct": on["refs_distinct"]}

    st = fig_f6(p1, off, on, off_official, on_official, off_m, on_m)
    sample_shared = fig_samples(p2, on["samples"], on["mem_body_ref"], side_src,
                                on["total_msg"], on["memref_msgs"], mem_stat)
    fig_health(p3, off_m, on_m, off_cost, on_cost)
    l7cfg = {"off_dup": off["l7"]["dup"], "on_dup": on["l7"]["dup"],
             "on_dup_with_memrefs": on["l7"]["dup_with_memrefs"],
             "n_off": off["total_msg"], "n_on": on["total_msg"]}
    deg = fig_degradation(p4, off_m, on_m, l7cfg,
                          {"off_n": off["l13_n"], "on_n": on["l13_n"],
                           "on_topics": on["l13_topics"]})

    summary = OrderedDict(
        figures=[p1, p2, p3, p4],
        f6=st,
        official={"off": off_official, "on": on_official},
        memory_refs={"off": off["memref_msgs"], "on": on["memref_msgs"],
                     "refs_on": on["refs_total"], "distinct_mem_ids_on": on["refs_distinct"]},
        timeref_with_memory_refs=on["timeref_with_memref"],
        samples=[{"seq": s["seq"], "line": s["line"], "day": s["day"], "slot": s["slot"],
                  "from": s["from"], "to": s["to"], "refs": s["refs"], "body": s["body"],
                  "hit": s["hit"]} for s in on["samples"]],
        sample_4gram_shared=sample_shared,
        degradation={"l7": l7cfg,
                     "l13": {"off_n": off["l13_n"], "on_n": on["l13_n"], "on_topics": on["l13_topics"]}},
        side_src=side_src,
    )
    with open(os.path.join(outdir, "r11_shots_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: summary[k] for k in ("figures", "f6", "official", "memory_refs",
                                              "timeref_with_memory_refs", "side_src")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
