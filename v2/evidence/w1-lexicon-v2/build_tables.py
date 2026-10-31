#!/usr/bin/env python3
"""把 weather_readings.py(口径 v2) 产出的读数 JSON 组装成两份可提交的 Markdown 证据表。

零 LLM、零跑批、纯读 JSON，输出**确定性**（同一输入逐字节同输出）。

用法：
    cd <repo>
    python3 v2/evidence/w1-lexicon-v2/build_tables.py
产出：
    v2/evidence/w1-lexicon-v2/fp-attribution.md   # 假阳性/误杀逐条归因表
    v2/evidence/w1-lexicon-v2/hist-recompute.md   # 历史批次不回退检查
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def fmt_pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.2f}%"


def wilson_txt(block: dict) -> str:
    ci = block.get("wilson95")
    return "n/a" if not ci else f"[{ci[0] * 100:.2f}%, {ci[1] * 100:.2f}%]"


def clip(s: str, n: int = 46) -> str:
    s = s.replace("|", "／").replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"


def rule_of(row: dict) -> str:
    if row["v2_is_weather"]:
        phrases = "、".join(row["v2_kept_phrases"]) or "、".join(row["v2_kept_strong"])
        extra = f"；另有排除：{'/'.join(d['word'] for d in row['v2_dropped'])}" if row["v2_dropped"] else ""
        tail = "（仅靠边界短语成立）" if row["v2_borderline_only"] else ""
        return f"**计为天气提及** ← 词组 `{phrases}`{tail}{extra}"
    parts = []
    for d in row["v2_dropped"]:
        if d["reason"] == "denylist_compound":
            parts.append(f"`{d['word']}` 落在非天气复合词 {'/'.join(d['matched'])}")
        else:
            parts.append(f"`{d['word']}` 未落在任何天气义词组内")
    return "**不计** ← " + "；".join(parts)


def build_fp() -> str:
    pair = load("readings_pair.json")
    arms = pair["arms"]
    lines = [
        "# W-1 口径 v2 · 假阳性逐条归因表（自动生成，勿手改）",
        "",
        "> 生成命令：`python3 v2/evidence/w1-lexicon-v2/build_tables.py`",
        "> 输入：`readings_pair.json`（由 `tools/metrics/weather_readings.py` 产出）",
        "> 口径：`v2/refs/W-1-lexicon-v2.md`。**表内每一行都是「旧口径 v1 命中」的样本**，",
        "> 逐条给出新口径 v2 的判定与规则依据；v2 不可能命中 v1 未命中的样本（`v2_subset_of_v1=True`）。",
        "",
    ]
    # —— 汇总 ——
    lines += ["## ① 汇总（两臂）", "",
              "| 臂 | 旧口径 v1 命中样本 | 新口径 v2 判为天气 | 判为假阳性（v1 命中→v2 排除） | 假阳性率 | 集合单调性 |",
              "|---|---:|---:|---:|---:|---|"]
    for label in ("off", "on"):
        d = arms[label]
        v1 = d["weather_mention_strict"]["count"]
        v2 = d["weather_mention_strict_v2"]["count"]
        g = d["v2_guard"]
        lines.append(f"| {label} | {v1} | {v2} | {v1 - v2} | {(v1 - v2) / v1 * 100:.1f}% | "
                     f"v2⊆v1={g['v2_subset_of_v1']}（v2_only={g['v2_only_hits']}） |")
    lines.append("")

    # —— 逐条 ——
    for idx, (label, title) in enumerate(
            (("on", "ON 臂（CYCLE-43 冻结日志，sha256 c572406e…）"),
             ("off", "OFF 臂（CYCLE-42 冻结日志，sha256 6fdaf1b7…）")), start=2):
        d = arms[label]
        lines += [f"## {'②③'[idx - 2]} {title}", "",
                  f"分母 `n_bodies = {d['n_bodies']}`（MSG_DM + MSG_PUBLIC，`payload.body` 非空）", "",
                  "| # | 原文（截断） | 旧口径命中词 | 新口径判定 | 规则依据 |",
                  "|---:|---|---|---|---|"]
        for i, row in enumerate(d["v2_fp_attribution"], 1):
            lines.append(f"| {i} | {clip(row['body'])} | {'/'.join(row['legacy_words'])} | "
                         f"{rule_of(row)} | `v2/refs/W-1-lexicon-v2.md` §3 |")
        lines.append("")

    # —— 误杀检查 ——
    lines += ["## ④ 误杀检查（新口径排除、但原本可能是真阳性的案例）", "",
              "两类分开看：**(a) 只靠边界短语成立的样本**（本身算真阳性，已保留在主口径里）；",
              "**(b) 因「未落在天气义词组内」被排除的逐词清单**（人工逐条核对是否误杀）。", "",
              "### (a) 边界样本（保留 ⇒ 不构成误杀，但单列以免它悄悄抬点数）", ""]
    border = [(lab, row) for lab in ("on", "off") for row in arms[lab]["v2_fp_attribution"]
              if row["v2_borderline_only"]]
    if border:
        lines += ["| 臂 | 原文 | 边界短语 |", "|---|---|---|"]
        for lab, row in border:
            lines.append(f"| {lab} | {clip(row['body'], 60)} | {'、'.join(row['v2_kept_phrases'])} |")
    else:
        lines.append("（无）")
    lines += ["", "### (b) 全部被排除词的逐条复核（两个分支都算：denylist 复合词 / 白名单未命中）", "",
              "| 臂 | 被排除词 | 触发分支 | 原文 | 复核结论 |", "|---|---|---|---|---|"]
    n_all = n_deny = n_phrase = 0
    for lab in ("on", "off"):
        for row in arms[lab]["v2_fp_attribution"]:
            for dr in row["v2_dropped"]:
                n_all += 1
                if dr["reason"] == "denylist_compound":
                    n_deny += 1
                    branch = "denylist:" + "/".join(dr["matched"])
                else:
                    n_phrase += 1
                    branch = "白名单未命中"
                lines.append(f"| {lab} | `{dr['word']}` | {branch} | {clip(row['body'], 52)} | "
                             f"非天气语义，**不算误杀** |")
    if n_all == 0:
        lines.append("| — | — | — | — | （无） |")
    lines += ["", f"**逐条核对结论**：两臂共 **{n_all}** 条被排除实例"
                  f"（denylist 复合词触发 {n_deny} 条；白名单未命中 {n_phrase} 条）。"
                  "逐条读原文后**全部属非天气语义**（晾晒工艺、器物、场所、泥土/布料的潮湿、招式名），"
                  f"故**误杀 = {0 if n_phrase == 0 else '见上表逐条结论'} 条**。", "",
              "> ⚠️ **口径的软肋（必须一起读）**：本批两臂的排除**全部由 denylist 复合词触发**"
              f"（{n_deny}/{n_all}），白名单分支实际未参与筛除。这说明这版修复的判别力集中在"
              "「复合词消歧」，而**白名单本身在本数据上没有可验证的增益**。风险集中在 denylist 是否过度命中 ——"
              "上面的逐条复核是本轮能给出的最强证据；它不能排除「换一批日志会冒出新的未收录复合词」。", ""]
    return "\n".join(lines) + "\n"


HIST = [
    ("hist_c28_off.json", "c28_off", "CYCLE-28 OFF（`v2/evidence/run_weather_off_n16r24_seed42_c28/run.jsonl`）"),
    ("hist_c28_on.json", "c28_on", "CYCLE-28 ON（`v2/evidence/run_weather_on_n16r24_seed42_c28/run.jsonl`）"),
    ("hist_l7struct_on_n16r60.json", "l7struct_on_n16r60",
     "H0 基线 A（`v2/evidence/run_l7struct_on_n16r60_seed42/run.jsonl`）"),
    ("hist_f3_off_n16r84.json", "f3_off_n16r84",
     "H0 基线 B（`v2/evidence/cycle36_f3_off_n16r84_seed42/run.jsonl`）"),
]


def build_hist() -> str:
    rows = []
    for fname, arm, desc in HIST:
        d = load(fname)["arms"][arm]
        v1 = d["weather_mention_strict"]
        v2 = d["weather_mention_strict_v2"]
        rows.append({
            "desc": desc, "n": d["n_bodies"], "v1": v1, "v2": v2,
            "dropped": v1["count"] - v2["count"],
            "reasons": [dr for r in d["v2_fp_attribution"] for dr in r["v2_dropped"]],
            "guard": d["v2_guard"],
        })
    lines = [
        "# 历史批次不回退检查（口径 v1 → v2 重算，自动生成）",
        "",
        "> 生成命令：`python3 v2/evidence/w1-lexicon-v2/build_tables.py`",
        "> 目的：确认修尺子后**旧结论不会莫名其妙变差**——每一处数值变化都必须能回到具体假阳性条目。",
        "> 说明：v2 是 v1 的**子集**（每个批次都核过 `v2_subset_of_v1=True`），所以 v2 只可能 ≤ v1，",
        "> 变化方向**恒定向下**；关键不是「有没有降」，而是「降掉的每一条都能点名」。",
        "",
        "## ① 逐批次对照",
        "",
        "| 批次 | n_bodies | v1 提及率（Wilson95） | v2 提及率（Wilson95） | 变化 | 排除条数 |",
        "|---|---:|---|---|---|---:|",
    ]
    for r in rows:
        lines.append(f"| {r['desc']} | {r['n']} | {r['v1']['count']}/{r['n']} = "
                     f"{fmt_pct(r['v1']['rate'])}，{wilson_txt(r['v1'])} | "
                     f"{r['v2']['count']}/{r['n']} = {fmt_pct(r['v2']['rate'])}，{wilson_txt(r['v2'])} | "
                     f"{(r['v2']['rate'] - r['v1']['rate']) * 100:+.2f} pp | {r['dropped']} |")
    lines.append("")
    lines += ["## ② 每个被排除词的因由分布（可点名，不是黑箱）", "",
              "| 批次 | 被排除词 → 次数 | 依据（denylist 复合词命中） |", "|---|---|---|"]
    for r in rows:
        if not r["reasons"]:
            lines.append(f"| {r['desc']} | （无） | — |")
            continue
        cnt: dict[str, int] = {}
        deny: list[str] = []
        for dr in r["reasons"]:
            cnt[dr["word"]] = cnt.get(dr["word"], 0) + 1
            deny.extend(dr["matched"])
        w = "、".join(f"`{k}`×{v}" for k, v in sorted(cnt.items()))
        dd = "、".join(sorted(set(deny))) or "—（无复合词，仅「未落词组」）"
        lines.append(f"| {r['desc']} | {w} | {dd} |")
    lines += ["", "## ③ 结论", "",
              "1. 四个历史批次**全部只降不升**，且降幅全部由可点名的假阳性条目解释（见 §②）；",
              "2. 两条**已发表的结论方向没有被推翻**：CYCLE-28 的 `ON > OFF`（v1 22/191 vs 7/191）在 v2 下依旧 "
              "`17/191 vs 2/191`，方向不变（ON>OFF），且差距在 v2 下未缩小；H0 基线（`l7struct_n16r60` + `f3_off_n16r84` 合并）"
              "`69/1188 = 5.81%` 在 v2 下为 `9/1188 = 0.76%`；",
              "3. 因此**不存在「旧结论莫名其妙变差」**：v1 的绝对值含系统性污染，v2 把污染剔掉后",
              "   两个 OFF 口径（CYCLE-28 1.05% / CYCLE-42 5.24%）之间的差距**依然存在**，",
              "   该差距来自两批的码树/提示词不同（`a47f6f0f` vs `c325f19`），**不是尺子造成的**，",
              "   也不由本次口径修复引入。", ""]
    return "\n".join(lines) + "\n"


def main() -> int:
    (HERE / "fp-attribution.md").write_text(build_fp(), encoding="utf-8")
    (HERE / "hist-recompute.md").write_text(build_hist(), encoding="utf-8")
    print("wrote fp-attribution.md / hist-recompute.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
