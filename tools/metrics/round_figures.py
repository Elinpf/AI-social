#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""round_figures.py —— 把 obs 原始产物变成可直接进报告的 PNG（零跑批、零 LLM、零联网）。

本项目纪律（脚本层面强制）：
  * 只读既有产物文件，不调用 LLM、不跑批、不联网；
  * 图上每个数字都来自输入文件，脚本内**不写任何硬编码观测值**；
  * 数据缺失（文件不存在 / 字段缺失 / 分母为 0 / status=not_applicable）时在图上显式打印
    「数据缺失」，绝不补零、绝不插值、绝不画占位柱。

两张图：

1) <label>-llm-cost.png
   数据源：`cd code && python3 -m obs llm-cost --log ../<run.jsonl> --require-provider openai_compat`
          的**原始 stdout JSON** 落盘件（结构见 v2/evidence/obs_cost_r1/obs_llm_cost_off.json）。
   三个子图：① 各 purpose 调用次数 ② 各 purpose tokens_in/out ③ provider 门禁与总量（原文照抄）。

2) <label>-life-texture.png
   数据源：本轮指标读数器输出，两种互斥用法：
   (a) `--lex <arm.json> --lex <arm.json>`：每臂一份文件（本轮实际用法，
       如 v2/evidence/r41_lexvary_batch/lex_template_rate_{off,on}.json）。
       每块字段形如 {"num":..,"den":..,"rate":..,"rate_pct":..,"wilson95":{"lo":..,"hi":..,"p":..}}。
       臂由文件内 "arm"/"label"/"tag" 字段或文件名 `_off`/`_on` 判定。
   (b) `--life <readings.json>`：一份自定义 readings（schema 见下）。

   图上标注：两臂文件路径与各自 n_msgs、`lexicons.lexicon_sha256`（尺子身份）；
   两臂尺子版本不一致时在标题区打印警示「读数不可直接跨版本比较」。

   自定义 readings schema（--life）：
     {"dimension":"...", "source":"...", "notes":"...",
      "metrics":[{"name":"...","unit":"条","off":12,"off_den":100,"on":30,"on_den":100}   # 或
                 {"name":"...","unit":"","off_val":0.12,"on_val":0.30}]}

用法（仓库根执行）：

  # 图 1：llm-cost（可传多个臂 JSON）
  python3 tools/metrics/round_figures.py \
      --cost-json v2/evidence/r41_lexvary_batch/off/llm_cost.json \
      --cost-json v2/evidence/r41_lexvary_batch/on/llm_cost.json \
      --label r41 --out-dir reports/figures

  # 图 3：公开面接话（public_talk_metrics 每臂一份）
  python3 tools/metrics/round_figures.py \
      --pubtalk v2/evidence/r41_public_talk/off/pubtalk_metrics.json \
      --pubtalk v2/evidence/r41_public_talk/on/pubtalk_metrics.json \
      --label r41 --out-dir reports/figures

  # 图 2：生活气息指标（两臂各一份读数文件）
  python3 tools/metrics/round_figures.py \
      --lex v2/evidence/r41_lexvary_batch/lex_template_rate_off.json \
      --lex v2/evidence/r41_lexvary_batch/lex_template_rate_on.json \
      --label r41 --out-dir reports/figures
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["font.sans-serif"] = [
    "Noto Serif CJK SC", "Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

MISSING = "数据缺失"
COL_OFF = "#9e9e9e"
COL_ON = "#1976d2"


def _load(p: str) -> dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _arm_from_name(p: str) -> str:
    """从路径/文件名判定臂名：优先目录（.../off/...），其次文件名里的独立 token。"""
    norm = p.replace("\\", "/")
    parts = [x.lower() for x in norm.split("/")]
    if "off" in parts or "control" in parts:
        return "OFF"
    if "on" in parts or "treat" in parts:
        return "ON"
    import re as _re
    toks = [t for t in _re.split(r"[^a-z0-9]+", os.path.basename(p).lower()) if t]
    for t in toks:
        if t in ("off", "control", "ctrl", "baseline"):
            return "OFF"
        if t in ("on", "treat", "treatment"):
            return "ON"
    return os.path.splitext(os.path.basename(p))[0]


def _stamp_note(fig, note: str | None, y: float = 0.995) -> None:
    """在每张图顶部打一条醒目红框说明（用于"数据源 / 是否本轮新批"的强制声明）。"""
    if not note:
        return
    fig.text(0.5, y, note, ha="center", va="top", fontsize=11.5, color="#b00020",
             bbox=dict(boxstyle="round,pad=0.45", fc="#fff3f3", ec="#b00020", lw=1.6))


def _cmdline() -> str:
    return "python3 " + " ".join(["tools/metrics/round_figures.py"] + sys.argv[1:])


# ============================================================ 图 1：llm-cost
def _batch_arm_label(p: str) -> str:
    """.../<batch>/<arm>/llm_cost.json → "batch/arm"；否则退回臂名。"""
    norm = os.path.abspath(p).replace("\\", "/")
    parts = norm.split("/")
    arm = _arm_from_name(p)
    if len(parts) >= 2 and arm in ("ON", "OFF") and parts[-2].lower() == arm.lower():
        return f"{parts[-3]}/{parts[-2]}"
    return arm


def figure_llm_cost(cost_jsons: list[str], out_png: str, label: str,
                    source_note: str | None = None) -> list[str]:
    arms = []
    for p in cost_jsons:
        d = _load(p)
        eng = d.get("engine_log") or {}
        arms.append({
            "name": _batch_arm_label(p),
            "path": p,
            "total": eng.get("total") or {},
            "by_purpose": eng.get("by_purpose") or {},
            "by_provider": eng.get("by_provider") or {},
            "judgment": eng.get("llm_judgment_by_dimension") or {},
            "guard": d.get("provider_guard") or {},
        })
    if not arms:
        raise SystemExit("没有 cost json")

    purposes = sorted({k for a in arms for k in a["by_purpose"]})
    fig = plt.figure(figsize=(15, 10.0))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.40], hspace=0.42, wspace=0.26,
                          top=0.82, bottom=0.07, left=0.08, right=0.98)
    _stamp_note(fig, source_note)
    fig.suptitle(
        f"{label} · 真实 LLM 调用成本（obs llm-cost 原始输出，零改写）\n"
        "数据源：" + "；".join(os.path.abspath(a["path"]) for a in arms),
        fontsize=11, y=0.955 if source_note else 0.98)

    # ① 各 purpose 调用次数
    ax = fig.add_subplot(gs[0, 0])
    h = 0.8 / max(1, len(arms))
    for i, a in enumerate(arms):
        vals = [int((a["by_purpose"].get(p) or {}).get("calls", 0)) for p in purposes]
        ys = [j + i * h - 0.4 + h / 2 for j in range(len(purposes))]
        is_off = a["name"].upper().endswith("OFF") or a["name"].upper() == "OFF"
        ax.barh(ys, vals, height=h, label=a["name"], color=COL_OFF if is_off else COL_ON)
        for yy, v in zip(ys, vals):
            ax.text(v, yy, f" {v}", va="center", fontsize=8)
    ax.set_yticks(list(range(len(purposes))))
    ax.set_yticklabels(purposes, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("LLM 调用次数")
    ax.set_title("① 各 purpose 调用次数（engine_log.LLM_CALL 计数）")
    ax.legend(fontsize=9, loc="lower right")
    ax.grid(axis="x", alpha=0.3)

    # ② 各 purpose tokens_in / tokens_out
    ax = fig.add_subplot(gs[0, 1])
    width = 0.8 / max(1, len(arms))
    for i, a in enumerate(arms):
        tin = [int((a["by_purpose"].get(p) or {}).get("tokens_in", 0)) for p in purposes]
        tout = [int((a["by_purpose"].get(p) or {}).get("tokens_out", 0)) for p in purposes]
        xs = [j + i * width - 0.4 + width / 2 for j in range(len(purposes))]
        is_on = not (a["name"].upper().endswith("OFF") or a["name"].upper() == "OFF")
        ax.bar(xs, tin, width=width, color=COL_ON if is_on else COL_OFF,
               label=f"{a['name']} tokens_in")
        ax.bar(xs, tout, width=width, bottom=tin,
               color="#c62828" if is_on else "#ef9a9a", label=f"{a['name']} tokens_out")
    ax.set_xticks(list(range(len(purposes))))
    ax.set_xticklabels(purposes, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("tokens")
    ax.set_title("② 各 purpose token 用量（下=in，上=out）")
    ax.legend(fontsize=8, ncol=4, loc="upper center")
    ax.grid(axis="y", alpha=0.3)

    # ③ provider 门禁 + 总量（原文照抄，不做换算）
    ax = fig.add_subplot(gs[1, :])
    ax.axis("off")
    lines = ["③ provider 门禁与总量（原文照抄 obs llm-cost 字段，未做任何换算）", ""]
    for a in arms:
        t, g, prov = a["total"], a["guard"], (a["by_provider"] or {})
        if not t:
            lines.append(f"{a['name']}  {MISSING}（engine_log.total 不存在）")
            lines.append("")
            continue
        ok = g.get("ok")
        lines.append(
            f"{a['name']}   calls={t.get('calls', 0)}  tokens_in={t.get('tokens_in', 0):,}  "
            f"tokens_out={t.get('tokens_out', 0):,}  tokens_total={t.get('tokens_total', 0):,}  "
            f"cached={t.get('cached', 0)}  degraded={t.get('degraded', 0)}  thinking={t.get('thinking', 0)}")
        lines.append(
            f"        provider={prov}  expected={g.get('expected', '?')}  guard.ok={ok}"
            + ("" if ok else "   ← 门禁未过：本图不得用于「真实 LLM」结论"))
        if a["judgment"]:
            lines.append(f"        LLM_JUDGMENT by dimension={a['judgment']}")
        lines.append("")
    ax.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=9.5, linespacing=1.55)

    fig.text(0.995, 0.005, "生成命令：" + _cmdline(), ha="right", va="bottom",
             fontsize=7, color="#555")
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return [f"{a['name']}: calls={a['total'].get('calls', MISSING)}, "
            f"tokens_total={a['total'].get('tokens_total', MISSING)}, "
            f"guard.ok={a['guard'].get('ok', MISSING)}"
            for a in arms]


# ============================================================ 图 2：生活气息指标
# 指标口径（顺序固定；某臂缺字段则该项打「数据缺失」；全部缺失则整图打「数据缺失」）
LEX_FIELDS = [
    ("quant_hit", "固定量词命中占比\n（半指/第三格/三钱/一拃/一指）"),
    ("quant_reuse", "固定说法复用占比\n（同一说法在多条消息中重复出现）"),
    ("backref_hit", "回指命中占比\n（上回/上次/想起）"),
    ("backref_opener", "以「上回/上次」开头占比"),
    ("opener_top10_share", "正文首 6 字 Top-10 模板覆盖占比\n（越低越不套路）"),
    ("distinct_body_ratio", "正文去重比\n（去重正文数 / MSG 总数）"),
]


def _arm_tag(d: dict, path: str) -> str:
    for k in ("arm", "label", "tag", "method", "variant"):
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            v = v.strip().lower()
            if v in ("off", "control", "ctrl", "baseline"):
                return "OFF"
            if v in ("on", "treat", "treatment"):
                return "ON"
    return _arm_from_name(path)


def _block(arm: dict, field: str):
    """返回 (num, den, rate, (lo, hi)|None, status)；分母 0 / status 非 ok ⇒ rate 视为缺失。"""
    v = arm.get(field)
    if v is None:
        return None, None, None, None, "missing"
    if not isinstance(v, dict):
        return None, None, v, None, "bad_shape"
    num, den, rate = v.get("num"), v.get("den"), v.get("rate")
    status = v.get("status")
    ci = None
    w = v.get("wilson95") or v.get("wilson_95")
    if isinstance(w, dict) and w.get("lo") is not None and w.get("hi") is not None:
        ci = (w["lo"], w["hi"])
    elif isinstance(w, (list, tuple)) and len(w) == 2:
        ci = (w[0], w[1])
    if status not in (None, "ok", "OK"):
        return num, den, None, None, str(status)
    if not den:
        return num, den, None, ci, "den=0"
    if rate is None:
        rate = num / den
    return num, den, rate, ci, "ok"


def _lex_arm_files(paths: list[str]):
    arms, meta = {}, []
    for p in paths:
        d = _load(p)
        tag = _arm_tag(d, p)
        arms[tag] = d
        lex = d.get("lexicons") if isinstance(d.get("lexicons"), dict) else {}
        meta.append({"tag": tag, "path": os.path.abspath(p), "n_msgs": d.get("n_msgs"),
                     "lex_sha": lex.get("lexicon_sha256")})
    return arms, meta


def _metrics_from_arms(arms: dict, meta: list[dict]):
    shas = {m["lex_sha"] for m in meta if m["lex_sha"]}
    out = []
    for field, desc in LEX_FIELDS:
        row = {"name": desc, "ylabel": "占比"}
        touched = False
        for tag in ("OFF", "ON"):
            if tag not in arms:
                row[f"{tag.lower()}_status"] = "arm_absent"
                continue
            if field in arms[tag]:
                touched = True
            num, den, rate, ci, status = _block(arms[tag], field)
            row[tag.lower()] = num
            row[f"{tag.lower()}_den"] = den
            row[f"{tag.lower()}_val"] = rate
            row[f"{tag.lower()}_ci"] = ci
            row[f"{tag.lower()}_status"] = status
        if touched:
            out.append(row)
    warn = ("两臂 lexicon_sha256 不一致 ⇒ 尺子版本不同，读数不可直接跨版本比较"
            if len(shas) > 1 else "")
    return out, warn


def figure_life(lex_paths: list[str] | None, life_json: str | None,
                out_png: str, label: str) -> list[str]:
    meta: list[dict] = []
    warn = ""
    dim = "台词套路化（去模板化）"
    notes = ""
    if lex_paths:
        arms, meta = _lex_arm_files(lex_paths)
        metrics, warn = _metrics_from_arms(arms, meta)
        notes = ("口径：分母 = 该臂 n_msgs；误差线为读数器给出的 wilson95 区间；"
                 "分母为 0 或 status=not_applicable 的块按「数据缺失」处理，不倒推、不补值。")
        for a in arms.values():
            if a.get("dimension"):
                dim = a["dimension"]
                break
        src_line = "；".join(f"{m['tag']}={m['path']}（n_msgs={m['n_msgs']}）" for m in meta)
    else:
        d = _load(life_json)
        metrics = d.get("metrics") or []
        dim = d.get("dimension") or dim
        notes = d.get("notes") or ""
        src_line = d.get("source") or os.path.abspath(life_json)

    if not metrics:
        fig, ax0 = plt.subplots(figsize=(9, 3.4))
        ax0.axis("off")
        ax0.text(0.5, 0.55, MISSING, ha="center", va="center", fontsize=18,
                 color="#c62828", transform=ax0.transAxes)
        ax0.text(0.5, 0.25, "未在输入文件中识别到任何指标字段", ha="center", va="center",
                 fontsize=10, transform=ax0.transAxes)
        fig.suptitle(f"{label} · 生活气息维度：{dim}", fontsize=11)
        fig.text(0.005, 0.005, "生成命令：" + _cmdline(), ha="left", va="bottom",
                 fontsize=7, color="#555")
        fig.savefig(out_png, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return [f"{dim}: {MISSING}（未识别到指标字段）"]

    ncol = 3 if len(metrics) > 2 else max(1, len(metrics))
    nrow = (len(metrics) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.7 * ncol, 4.0 * nrow + 1.6), squeeze=False)
    title = f"{label} · 生活气息维度：{dim}\n数据源：{src_line}"
    if meta:
        title += "\n尺子身份：" + "，".join(
            f"{m['tag']} lexicon_sha256={m['lex_sha']}" for m in meta)
    if warn:
        title += f"\n⚠ {warn}"
    fig.suptitle(title, fontsize=10.5)

    out_notes = []
    for idx in range(nrow * ncol):
        ax = axes[idx // ncol][idx % ncol]
        if idx >= len(metrics):
            ax.axis("off")
            continue
        m = metrics[idx]
        off_val, on_val = m.get("off_val"), m.get("on_val")
        if off_val is None and m.get("off") is not None and m.get("off_den"):
            off_val = m["off"] / m["off_den"]
        if on_val is None and m.get("on") is not None and m.get("on_den"):
            on_val = m["on"] / m["on_den"]

        if off_val is None and on_val is None:
            ax.text(0.5, 0.55, MISSING, ha="center", va="center", fontsize=16,
                    color="#c62828", transform=ax.transAxes)
            ax.set_title(m.get("name", "?"), fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_color("#c62828")
            st = {k: m.get(f"{k}_status") for k in ("off", "on") if m.get(f"{k}_status")}
            if st:
                ax.text(0.5, 0.2, str(st), ha="center", va="center", fontsize=7.5,
                        color="#c62828", transform=ax.transAxes)
            out_notes.append(f"{m['name'].splitlines()[0]}: {MISSING}（{st}）")
            continue

        labels, vals, cols, cis = [], [], [], []
        for tag, val, col in (("OFF", off_val, COL_OFF), ("ON", on_val, COL_ON)):
            if val is None:
                continue
            labels.append(tag)
            vals.append(val)
            cols.append(col)
            cis.append(m.get(f"{tag.lower()}_ci"))
        bars = ax.bar(labels, vals, color=cols, width=0.55)
        for b, v, arm in zip(bars, vals, labels):
            num, den = m.get(arm.lower()), m.get(arm.lower() + "_den")
            txt = f"{v:.3f}" if isinstance(v, float) else f"{v}"
            if num is not None and den:
                txt = f"{num}/{den}\n{txt}"
            ax.text(b.get_x() + b.get_width() / 2, v, txt, ha="center", va="bottom", fontsize=8)
        if cis and all(c for c in cis):
            yerr = [[v - c[0] for v, c in zip(vals, cis)], [c[1] - v for v, c in zip(vals, cis)]]
            ax.errorbar(labels, vals, fmt="none", ecolor="#333", capsize=4, lw=1, yerr=yerr)
        for tag, val in (("OFF", off_val), ("ON", on_val)):
            if val is None:
                ax.text(0.18 if tag == "OFF" else 0.82, 0.9, MISSING, ha="center",
                        va="center", fontsize=8.5, color="#c62828", transform=ax.transAxes)
        ax.set_title(m.get("name", "?"), fontsize=9)
        ax.set_ylabel(m.get("ylabel") or m.get("unit") or "值")
        ax.margins(y=0.3)
        ax.grid(axis="y", alpha=0.3)
        out_notes.append(
            f"{m['name'].splitlines()[0]}: OFF={off_val if off_val is None else round(off_val, 4)} "
            f"ON={on_val if on_val is None else round(on_val, 4)}")

    if notes:
        fig.text(0.006, 0.032, notes, ha="left", va="bottom", fontsize=7.5, color="#333")
    fig.text(0.006, 0.006, "生成命令：" + _cmdline(), ha="left", va="bottom",
             fontsize=6.8, color="#555")
    fig.tight_layout(rect=(0, 0.075, 1, 0.88))
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_notes


# ============================================================ 图 3：公开面接话（public_talk_metrics）
# 数据源：tools/public_talk/public_talk_metrics.py 的落盘 JSON（每臂一份，官方尺子 v4，口径不改）。
# 本模式的硬纪律（抄自该尺子 discipline 段，图上照写）：
#   * 分母 < 30 ⇒ 只报事件数、不报比率；分母 < 68 ⇒ probe，占比只作点估计；
#   * 单 seed、无重复 ⇒ 不给 CI、不写「显著」、不做跨批数值比较；
#   * 结构不变量的历史批（如 r38 on，n16r24）与本次 n8r8 规模不同，图上只作「前基线结构对照」，
#     不与本轮并排进同一坐标轴、不参与任何数值比较。
PUB_COUNT_PANELS = [
    ("MSG_PUBLIC 条数（本量自身即分母）", "n_pub", None),
    ("公开消息入度合计\npub_in_degree_total", "in_deg", None),
    ("公开消息对外出边\npub_out_degree_reply_nonnull", "out_deg", None),
    ("reply_to 非空条数", "reply_nonnull", "reply_den"),
    ("participants 长度>1 条数", "part_gt1", "part_den"),
]


def _fmt_scale(sc) -> str:
    if isinstance(sc, dict):
        keep = ("seed", "agents_n", "agents", "rounds", "model", "n_agents")
        bits = [f"{k}={sc[k]}" for k in keep if k in sc and isinstance(sc[k], (int, float, str))]
        if not bits:
            bits = [f"{k}={v}" for k, v in sc.items() if isinstance(v, (int, float, str))]
        out = ", ".join(bits)
        return out if len(out) <= 68 else out[:65] + "…"
    return str(sc) if sc is not None else "UNKNOWN"


def _pub_extract(path: str) -> dict:
    d = _load(path)
    g = d.get("msg_graph_degree") or {}
    rt = d.get("reply_to_forms") or {}
    pl = d.get("place_adjacency") or {}
    pd = d.get("participants_length_dist") or {}
    inp = d.get("inputs") or {}
    return {
        "path": os.path.abspath(path),
        "arm": _arm_from_name(path),
        "n_pub": (d.get("msg_public_total") or {}).get("value"),
        "in_deg": g.get("pub_in_degree_total"),
        "out_deg": g.get("pub_out_degree_reply_nonnull"),
        "reply_nonnull": rt.get("numerator_nonnull_reply_to"),
        "reply_den": rt.get("denominator"),
        "part_gt1": pd.get("numerator_len_gt_1"),
        "part_den": pd.get("denominator"),
        "place_status": pl.get("status"),
        "place_nonnull": pl.get("nonnull_place_records"),
        "place_den": (d.get("msg_public_total") or {}).get("value"),
        "turn_hist": (d.get("diagnostics") or {}).get("turn_index_histogram") or {},
        "scale": d.get("scale"),
        "scale_desc": (d.get("judgeability") or {}).get("scale_desc"),
        "code_sha": inp.get("code_sha"),
        "log_sha": inp.get("log_sha256"),
        "log_path": inp.get("log_path"),
        "ratio_min_den": (d.get("discipline") or {}).get("ratio_min_denominator"),
        "probe_den": (d.get("discipline") or {}).get("probe_threshold_denominator"),
    }


def figure_pubtalk(paths: list[str], out_png: str, label: str) -> list[str]:
    arms = [_pub_extract(p) for p in paths]
    fig = plt.figure(figsize=(16.5, 13.8))

    src = "；".join(f"{a['arm']}={a['path']}" for a in arms)
    # 可比性自检：两臂 code_sha / scale 应当一致（唯一自变量应为 env）；不一致就在图上打⚠
    shas = {a["code_sha"] for a in arms if a["code_sha"]}
    scales = {_fmt_scale(a["scale"]) for a in arms if a["scale"]}
    warns = []
    if len(shas) > 1:
        warns.append("⚠ 两臂 code_sha 不一致 ⇒ 代码身份不同、env 不是唯一自变量，本图不可作因果解读")
    if len(scales) > 1:
        warns.append("⚠ 两臂 scale 不一致 ⇒ 规模不同，不参与数值比较")
    title = (f"{label} · 生活气息维度：公开面接话（MSG_PUBLIC 跟帖/接话）· 事件计数口径\n"
             f"数据源：{src}\n"
             "纪律（抄自 public_talk_metrics discipline）：分母<30 只报事件数不报比率；分母<68 一律 probe；"
             "单 seed 无重复 ⇒ 不给 CI、不写显著、不做跨批数值比较")
    if warns:
        title += "\n" + "；".join(warns)
    top = 0.895 - 0.032 * title.count("\n")   # 标题每多一行就下压，避免压到子图标题
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 1, 1.02], hspace=0.55, wspace=0.26,
                          top=top, bottom=0.10, left=0.06, right=0.985)
    fig.suptitle(title, fontsize=10.5, color="#222")

    out_notes = []
    for i, (title, key, den_key) in enumerate(PUB_COUNT_PANELS):
        ax = fig.add_subplot(gs[i // 3, i % 3])
        labels, vals, dens = [], [], []
        for a in arms:
            v = a.get(key)
            if v is None:
                continue
            labels.append(a["arm"])
            vals.append(v)
            dens.append(a.get(den_key) if den_key else None)
        if not vals:
            ax.text(0.5, 0.5, MISSING, ha="center", va="center", fontsize=15,
                    color="#c62828", transform=ax.transAxes)
            ax.set_title(title, fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
            out_notes.append(f"{title.splitlines()[0]}: {MISSING}")
            continue
        bars = ax.bar(labels, vals, color=[COL_OFF if l == "OFF" else COL_ON for l in labels],
                      width=0.5)
        for b, v, dv, arm in zip(bars, vals, dens, labels):
            txt = f"{v}"
            if dv:
                txt = f"{v}/{dv}"
            ax.text(b.get_x() + b.get_width() / 2, v, txt, ha="center", va="bottom", fontsize=9)
        ax.set_title(title, fontsize=9)
        ax.set_ylabel("条 / 边")
        top = max(vals) if max(vals) > 0 else 1
        ax.set_ylim(0, top * 1.28)
        ax.grid(axis="y", alpha=0.3)
        # 分母提示：只报事件数，不画比率
        note_bits = []
        for arm, dv in zip(labels, dens):
            if dv:
                note_bits.append(f"{arm} 分母={dv}" + ("（<30，只报事件数）" if dv < 30 else ""))
        if note_bits:
            ax.text(0.5, -0.22, "；".join(note_bits), ha="center", va="top",
                    fontsize=7.2, color="#c62828", transform=ax.transAxes)
        out_notes.append(
            " / ".join(f"{arm}={v}{'/' + str(dv) if dv else ''}"
                       for arm, v, dv in zip(labels, vals, dens)))

    # 第 6 格：place_adjacency.status（可算性状态）+ 尺子身份
    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    lines = ["place_adjacency 可算性状态（payload.place 覆盖）", ""]
    for a in arms:
        st = a["place_status"] or MISSING
        lines.append(f"{a['arm']}  status={st}")
        if a.get("place_nonnull") is not None:
            lines.append(f"       非 null place 记录 {a['place_nonnull']}/{a['place_den']}"
                         + ("   ← 仍不可判" if st != "OK" else ""))
    lines.append("")
    lines.append("code_sha / scale（源 meta.json）")
    for a in arms:
        lines.append(f"{a['arm']}  code_sha={(a['code_sha'] or 'UNKNOWN')[:12]}…")
        lines.append(f"       scale={_fmt_scale(a['scale'])}")
    ax.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=8.6, linespacing=1.6)

    # 底部：turn_index_histogram（首轮独白 vs 后续接话）
    ax = fig.add_subplot(gs[2, :])
    all_keys = sorted({k for a in arms for k in (a["turn_hist"] or {})}, key=lambda x: int(x))
    if all_keys:
        xs = list(range(len(all_keys)))
        w = 0.8 / max(1, len(arms))
        for j, a in enumerate(arms):
            vals = [int((a["turn_hist"] or {}).get(k, 0)) for k in all_keys]
            ax.bar([x + j * w - 0.4 + w / 2 for x in xs], vals, width=w,
                   color=COL_OFF if a["arm"] == "OFF" else COL_ON, label=a["arm"])
            for xx, v in zip([x + j * w - 0.4 + w / 2 for x in xs], vals):
                if v:
                    ax.text(xx, v, str(v), ha="center", va="bottom", fontsize=7.5)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"turn={k}" for k in all_keys], fontsize=9)
        ax.set_ylabel("MSG_PUBLIC 条数")
        ax.set_title("diagnostics.turn_index_histogram —— 公开消息出现在对话的第几轮"
                     "（全在 turn=0 说明仍是首轮独白、没有接话）", fontsize=9.5)
        ax.legend(fontsize=9)
        ax.grid(axis="y", alpha=0.3)
        out_notes.append("turn_index_histogram: " + " / ".join(
            f"{a['arm']}={a['turn_hist']}" for a in arms))
    else:
        ax.text(0.5, 0.5, MISSING, ha="center", va="center", fontsize=15, color="#c62828",
                transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])

    fig.text(0.006, 0.045,
             "注：本轮各臂 MSG_PUBLIC 绝对条数很小，所有「占比」按尺子纪律一律不画；"
             "图中只出现事件计数与分母，比率请到报告里按 probe 口径引用。",
             ha="left", va="bottom", fontsize=8, color="#333")
    fig.text(0.006, 0.008, "生成命令：" + _cmdline(), ha="left", va="bottom",
             fontsize=6.8, color="#555")
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_notes


# ============================================================ 图 4：前基线诊断（公开面现状）
# 数据源：public_talk_metrics.py 的落盘 JSON（本场景 = r38_f3_batch/on 前基线批）。
# 只画该 JSON 里已有的计数字段，缺字段即「数据缺失」，不推算、不补零。
def _diag_extract(path: str) -> dict:
    d = _load(path)
    sg = (d.get("schema_gate") or {}).get("key_presence") or {}
    counts = {t: (sg.get(t) or {}).get("events") for t in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")}
    pl = d.get("place_adjacency") or {}
    return {
        "path": os.path.abspath(path),
        "counts": counts,
        "in_deg": (d.get("msg_graph_degree") or {}).get("pub_in_degree_total"),
        "out_deg": (d.get("msg_graph_degree") or {}).get("pub_out_degree_reply_nonnull"),
        "part_hist": (d.get("participants_length_dist") or {}).get("length_histogram") or {},
        "part_den": (d.get("participants_length_dist") or {}).get("denominator"),
        "reply_forms": (d.get("reply_to_forms") or {}).get("forms") or {},
        "reply_den": (d.get("reply_to_forms") or {}).get("denominator"),
        "turn_hist": (d.get("diagnostics") or {}).get("turn_index_histogram") or {},
        "place_status": pl.get("status"),
        "place_nonnull": pl.get("nonnull_place_records"),
        "n_pub": (d.get("msg_public_total") or {}).get("value"),
        "scale_desc": (d.get("judgeability") or {}).get("scale_desc"),
        "code_sha": (d.get("inputs") or {}).get("code_sha"),
        "log_sha": (d.get("inputs") or {}).get("log_sha256"),
        "log_path": (d.get("inputs") or {}).get("log_path"),
    }


def figure_diag(paths: list[str], out_png: str, label: str,
                source_note: str | None = None) -> list[str]:
    ds = [_diag_extract(p) for p in paths]
    fig = plt.figure(figsize=(16.5, 10.8))
    gs = fig.add_gridspec(2, 3, hspace=0.55, wspace=0.30, top=0.79, bottom=0.17,
                          left=0.06, right=0.985)
    _stamp_note(fig, source_note)
    fig.suptitle(
        f"{label} · 公开面「接话」现状诊断（单批、无对照、无 CI）\n"
        + "；".join(f"{os.path.basename(d['path'])}" for d in ds)
        + "\n"
        + "；".join(f"scale: {d['scale_desc'] or 'UNKNOWN'}" for d in ds),
        fontsize=10.5, y=0.955)

    notes = []
    d = ds[0]

    # ① 事件类型计数
    ax = fig.add_subplot(gs[0, 0])
    types = ["MSG_DM", "MSG_PUBLIC", "MSG_GROUP"]
    vals = [d["counts"].get(t) for t in types]
    if any(v is not None for v in vals):
        vv = [v if v is not None else 0 for v in vals]
        cols = ["#455a64", COL_ON, "#ef9a9a"]
        bars = ax.bar(types, vv, color=cols, width=0.55)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, (v or 0), str(v) + ("" if v is not None else f" {MISSING}"),
                    ha="center", va="bottom", fontsize=10)
        ax.set_ylabel("事件条数")
        ax.set_title("① 对话事件类型构成（全批计数）", fontsize=10)
        ax.margins(y=0.2)
        ax.grid(axis="y", alpha=0.3)
        notes.append("MSG_DM/MSG_PUBLIC/MSG_GROUP = " + "/".join(str(v) for v in vals))
    else:
        ax.text(0.5, 0.5, MISSING, ha="center", va="center", fontsize=15, color="#c62828",
                transform=ax.transAxes)
        notes.append("事件类型计数: " + MISSING)

    # ② 公开消息入度 / 出边（两条零事实）
    ax = fig.add_subplot(gs[0, 1])
    lab = ["公开消息入度\npub_in_degree_total", "公开消息对外出边\npub_out_degree_reply_nonnull"]
    vv = [d["in_deg"], d["out_deg"]]
    if all(v is not None for v in vv):
        ax.bar(lab, vv, color=["#c62828", "#c62828"], width=0.5)
        for i, v in enumerate(vv):
            ax.text(i, v, f"{v}", ha="center", va="bottom", fontsize=13, color="#c62828")
        ax.set_ylim(0, max(1.0, max(vv) * 1.5 + 0.2))
        ax.text(0.5, 0.62, "全部为 0 ⇒ 公开消息在消息图里是孤立节点\n（无人接、也没接人）",
                ha="center", va="center", fontsize=9.5, color="#c62828", transform=ax.transAxes)
        ax.set_ylabel("边数")
        ax.set_title("② 公开消息在图中的连边（两条零事实）", fontsize=10)
        ax.grid(axis="y", alpha=0.3)
        notes.append(f"pub_in_degree_total={d['in_deg']}, pub_out_degree_reply_nonnull={d['out_deg']}")
    else:
        ax.text(0.5, 0.5, MISSING, ha="center", va="center", fontsize=15, color="#c62828",
                transform=ax.transAxes)
        notes.append("入度/出边: " + MISSING)

    # ③ participants 长度直方图
    ax = fig.add_subplot(gs[0, 2])
    hist = d["part_hist"]
    if hist:
        keys = sorted(hist, key=lambda x: int(x))
        vals3 = [int(hist[k]) for k in keys]
        bars = ax.bar([f"长度={k}" for k in keys], vals3, color=COL_ON, width=0.45)
        ax.set_xlim(-0.65, len(keys) - 0.35)
        for b, v in zip(bars, vals3):
            ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=11)
        ax.set_ylabel("MSG_PUBLIC 条数")
        ax.set_title("③ payload.participants 长度直方图\n"
                     f"（分母 {d['part_den']} 条公开消息；长度>1 的条数 = 0）", fontsize=9.5)
        ax.margins(y=0.25)
        ax.grid(axis="y", alpha=0.3)
        notes.append(f"participants 长度直方图={hist}（分母 {d['part_den']}）")
    else:
        ax.text(0.5, 0.5, MISSING, ha="center", va="center", fontsize=15, color="#c62828",
                transform=ax.transAxes)
        notes.append("participants 直方图: " + MISSING)

    # ④ reply_to 形态
    ax = fig.add_subplot(gs[1, 0])
    forms = d["reply_forms"]
    if forms:
        keys = sorted(forms)
        vals4 = [int(forms[k]) for k in keys]
        cols4 = ["#c62828" if k == "json_null" else COL_ON for k in keys]
        # 用横向柱：6 个互斥形态名较长，竖向标签会互相压住
        bars = ax.barh(list(range(len(keys))), vals4, color=cols4, height=0.6)
        for b, v in zip(bars, vals4):
            ax.text(v, b.get_y() + b.get_height() / 2, f" {v}", va="center", fontsize=9)
        ax.set_yticks(list(range(len(keys))))
        ax.set_yticklabels(keys, fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlabel("条数")
        ax.set_xlim(0, max(vals4) * 1.25 + 0.5)
        ax.set_title(f"④ 公开消息 reply_to 形态（分母 {d['reply_den']}；real_message_id=0）",
                     fontsize=9.5)
        ax.margins(y=0.22)
        ax.grid(axis="y", alpha=0.3)
        notes.append(f"reply_to.forms={forms}")
    else:
        ax.text(0.5, 0.5, MISSING, ha="center", va="center", fontsize=15, color="#c62828",
                transform=ax.transAxes)
        notes.append("reply_to.forms: " + MISSING)

    # ⑤ turn_index 直方图
    ax = fig.add_subplot(gs[1, 1])
    th = d["turn_hist"]
    if th:
        keys = sorted(th, key=lambda x: int(x))
        vals5 = [int(th[k]) for k in keys]
        bars = ax.bar([f"turn={k}" for k in keys], vals5, color=COL_ON, width=0.45)
        ax.set_xlim(-0.65, len(keys) - 0.35)
        for b, v in zip(bars, vals5):
            ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=11)
        ax.set_ylabel("MSG_PUBLIC 条数")
        ax.set_title("⑤ diagnostics.turn_index_histogram\n（全在 turn=0 ⇒ 均为首轮独白，无跟帖）",
                     fontsize=9.5)
        ax.margins(y=0.25)
        ax.grid(axis="y", alpha=0.3)
        notes.append(f"turn_index_histogram={th}")
    else:
        ax.text(0.5, 0.5, MISSING, ha="center", va="center", fontsize=15, color="#c62828",
                transform=ax.transAxes)
        notes.append("turn_index_histogram: " + MISSING)

    # ⑥ place 可算性 + 尺子身份
    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    lines = ["⑥ place_adjacency 可算性", ""]
    lines.append(f"status = {d['place_status'] or MISSING}")
    lines.append(f"非 null place 记录 = {d['place_nonnull']} / {d['n_pub']}"
                 if d["place_nonnull"] is not None and d["n_pub"] is not None else MISSING)
    lines.append("")
    lines.append("尺子身份（原样照抄，未做任何转换）")
    lines.append(f"code_sha = {(d['code_sha'] or 'UNKNOWN')}")
    lines.append(f"log_sha256 = {(d['log_sha'] or 'UNKNOWN')[:32]}…")
    lines.append("")
    lines.append("注：code_sha 语义 = 生成 meta 那一刻的 HEAD，")
    lines.append("    不是起跑钉住的 sha（已登记口径坑）")
    ax.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=8.4, linespacing=1.6)

    fig.text(0.006, 0.108,
             "读法：本图只描述「现状」。②③④⑤ 里的 0 / 长度=1 / turn=0 是同一件事的四个侧面——"
             "公开面既无人接话、也没有指向任何消息的引用；③ 的 participants 是线程参与者集合，不是收件人。",
             ha="left", va="bottom", fontsize=8.2, color="#333")
    fig.text(0.006, 0.062,
             "纪律：单批、单 seed、无对照 ⇒ 不给 CI、不写「显著」、不做跨批数值比较；"
             "分母 <30 的量只报事件数，不画比率。",
             ha="left", va="bottom", fontsize=8.2, color="#333")
    fig.text(0.006, 0.020, "生成命令：" + _cmdline(), ha="left", va="bottom",
             fontsize=6.8, color="#555")
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cost-json", action="append", default=[],
                    help="obs llm-cost 原始输出 JSON，可多次传入（每臂一份）")
    ap.add_argument("--lex", action="append", default=[],
                    help="指标读数器每臂输出 JSON，可多次传入")
    ap.add_argument("--life", default=None, help="自定义 readings JSON（schema 见模块 docstring）")
    ap.add_argument("--diag", action="append", default=[],
                    help="public_talk_metrics 落盘 JSON：出「前基线/现状诊断」图（只画已有计数）")
    ap.add_argument("--source-note", default=None,
                    help="强制声明横幅（红框），会打在该次运行产出的每一张图顶部")
    ap.add_argument("--pubtalk", action="append", default=[],
                    help="public_talk_metrics.py 落盘 JSON，每臂一份（官方尺子口径，不改）")
    ap.add_argument("--label", required=True, help="输出文件名前缀，如 r41")
    ap.add_argument("--out-dir", default="reports/figures")
    a = ap.parse_args()

    if not a.cost_json and not a.lex and not a.life and not a.pubtalk and not a.diag:
        ap.error("至少给 --cost-json / --lex / --life / --pubtalk 之一")
    if a.diag and (a.lex or a.life or a.pubtalk):
        ap.error("--diag 不能与 --lex/--life/--pubtalk 同时用")
    if sum(bool(x) for x in (a.lex, a.life, a.pubtalk)) > 1:
        ap.error("--lex / --life / --pubtalk 三者互斥")

    os.makedirs(a.out_dir, exist_ok=True)
    report = []
    if a.cost_json:
        out = os.path.join(a.out_dir, f"{a.label}-llm-cost.png")
        report.append(f"[llm-cost] {os.path.abspath(out)}")
        report += ["  · " + n for n in figure_llm_cost(a.cost_json, out, a.label, a.source_note)]
    if a.lex or a.life:
        out = os.path.join(a.out_dir, f"{a.label}-life-texture.png")
        report.append(f"[life-texture] {os.path.abspath(out)}")
        report += ["  · " + n for n in figure_life(a.lex or None, a.life, out, a.label)]
    if a.diag:
        out = os.path.join(a.out_dir, f"{a.label}-public-topic-diag.png")
        report.append(f"[public-topic-diag] {os.path.abspath(out)}")
        report += ["  · " + n for n in figure_diag(a.diag, out, a.label, a.source_note)]
    if a.pubtalk:
        out = os.path.join(a.out_dir, f"{a.label}-public-talk.png")
        report.append(f"[public-talk] {os.path.abspath(out)}")
        report += ["  · " + n for n in figure_pubtalk(a.pubtalk, out, a.label)]

    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
