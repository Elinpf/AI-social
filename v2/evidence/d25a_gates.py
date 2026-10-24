#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.5a 七闸复算器（**只读**：零 LLM、零跑批、不改任何 code/ 文件）。

单一目的：把 `v2/refs/D25a-prereg-slot-quota.md` §4 的 M1 / P / Q1 / Q2 / Q3 / S / T / 代价
从两条 `run.jsonl` 原地复算出来，**口径不自创**：
  - Q1 / Q2 / Q3 / T 一律 **shell 调用仓内既有官方工具**，
    本脚本只做转述与求差，**不重写**它们的算法（审计抽查用下表定位调用来源）；
  - M1 / P / S 是**结构读数**（数 `thread_id` 与 `(agent,day,slot)` 格），
    与 `v2/evidence/d24_flow_limits.md` / `d25_quota_bottleneck.md` 的判法逐字同口径，
    并在输出里把**分子 / 分母 / 口径来源**三者写在一起。

## 每个闸的取数来源（官方工具文件路径，审计逐项可核）

| 闸 | 指标键 | 官方工具（相对仓库根） | 本脚本做的事 |
|---|---|---|---|
| **M1** | `n_msgs_total` / `slot_saturated_rate(>=3)` | 无（结构计数，判法抄 `v2/evidence/d24_flow_limits.md` §1 与 `v2/evidence/d25_quota_bottleneck.md`） | 自行数格；分子/分母/两档灵敏度全落盘 |
| **P** | `threads_ge6_rate` | 无（同上，与 `d24` §1 的 `114` 分母同口径） | 自行数线程长度分布 |
| **Q1** | `restate_rate` | `tools/d5/l15_restate_rate.py`（**输出已是百分数**） | 仅取数 + 折算 pp + 求差 |
| **Q2** | `L-7_dup_ngram8_rate` | `tools/d5/dialogue_metrics.py`（键路径 `L_wording.L-7_dup_ngram8_rate`，**分数制**） | 同上 |
| **Q3** | `F-2_content_drift.drift_rate` | `tools/d5/dialogue_metrics.py`（键路径 `F-2_content_drift.drift_rate`，**分数制**；对应 JSON 内 `denominator_adjacent_pairs`） | 同上 |
| **S** | `n_threads` | 无（结构计数） | 自行数；并给出 `dialogue_metrics` 的 `meta.n_threads` 作灵敏度 |
| **T** | F1 `paren_rate` / F2 `addr_head_strict` / F3 `len_p50_excl` | `tools/d12h/shape_gate.py`（其内部 F1/F3 口径复用于 `tools/d9/arm_state_check.py::metrics`，运行时打印 `impl_metrics_sha256`） | 仅取数 + 求差；**字面读法与相对读法分开落盘** |
| **代价** | `llm_cost.calls` | **权威 = `obs llm-cost`**（本脚本不调用它）；本脚本只从 `dialogue_metrics` 的 `llm` 段取日志内记账做交叉核对 | 只记数、不换算金额 |

**T 闸的口径事实（务必连读，否则会误读判定词）**：`shape_gate.py` 的内置基线是**很早的 T5 批次**，
当前树上任何批次对 T5 都必然 F1/F2/F3 越界（本脚本在 `run_d12c_off` 上实测 +24.51pp / −21.76pp / −24.53%）。
⇒ `gates.T.literal_verdict` 只作**失效证据**保留，**不作为对 D2.5a 的判定**；
`gates.T.relative`（C vs B 同树自基线）是**补充读数，非预登记判据，不参与最终判定**
（Leader 裁决 2026-10-24：T 闸最终判定词 =「不可判（预登记基线 T5 与本树不可比，闸无判别力）」）。

用法：
    python3 v2/evidence/d25a_gates.py \
        --C v2/evidence/run_d25a_C_xxx \
        --B v2/evidence/run_d25a_B_xxx \
        --out-json v2/evidence/d25a_gates.json

每个 `--X` 参数给的是 **run 目录**（含 `run.jsonl`），不是文件路径。
退出码：0 全算出 / 2 输入不可用。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

SLOTS = ["morning", "afternoon", "evening", "night"]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = sys.executable


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slot_key(d):
    """(day, slot)。时段由 round 反推：round//12 = day, (round%12)//3 -> slot。
    与 d24/d25 的 sk() 同口径（3 轮/时段、4 时段/天）。"""
    r = d["round"]
    return (r // 12, SLOTS[(r % 12) // 3])


def load_msgs(path):
    msgs = []
    n_lines = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("type") in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
                msgs.append(rec)
    return msgs, n_lines


def structural(run_dir):
    """M1 / P / S 的结构读数。全部自 run.jsonl 现算。"""
    log = os.path.join(run_dir, "run.jsonl")
    msgs, n_lines = load_msgs(log)
    dm = [m for m in msgs if m["type"] == "MSG_DM"]

    # --- 每 (author, day, slot) 的 DM 条数 —— 与 d24 §1 同口径
    cell = Counter()
    for m in dm:
        p = m["payload"]
        author = p.get("author") or p.get("from")
        cell[(author,) + slot_key(m)] += 1
    n_cells_active = len(cell)                       # 有 >=1 条 DM 的格数
    n_cells_possible = 16 * 7 * 4                    # agents × days × slots（480? 见输出说明）

    sat2 = sum(1 for v in cell.values() if v >= 2)
    sat3 = sum(1 for v in cell.values() if v >= 3)
    dist = dict(sorted(Counter(cell.values()).items()))

    # --- 线程长度 —— 与 d24 §1 / B-4 同口径（MSG_DM 的 thread_id 去重）
    th = defaultdict(list)
    for m in dm:
        th[m["payload"]["thread_id"]].append(m)
    lens = Counter(len(v) for v in th.values())
    n_threads_dm = len(th)
    ge6 = sum(1 for v in th.values() if len(v) >= 6)

    return {
        "input": {"run_jsonl": log, "sha256": sha256_file(log), "lines": n_lines},
        "n_msgs_total_MSG_all": len(msgs),
        "n_msgs_dm": len(dm),
        "n_msgs_public": sum(1 for m in msgs if m["type"] == "MSG_PUBLIC"),
        "slot_cells": {
            "denominator_active_cells": n_cells_active,
            "denominator_active_cells_note": "有 >=1 条 MSG_DM 的 (author,day,slot) 格数（d24 用的分母）",
            "denominator_all_cells_if_16x7x4": n_cells_possible,
            "denominator_all_cells_note": ("16 agents × 7 days × 4 slots = 448 为理论格数；"
                                           "本批次每 day 只有 4 时段各 3 轮，全部 day 均被跑到，"
                                           "故 448 亦可作灵敏度分母"),
            "dist_msgs_per_cell": dist,
            "max_msgs_per_cell": max(cell.values()) if cell else 0,
            "cells_ge2": sat2,
            "cells_ge3": sat3,
            "slot_saturated_rate_ge2_over_active": round(100.0 * sat2 / n_cells_active, 4) if n_cells_active else None,
            "slot_saturated_rate_ge3_over_active": round(100.0 * sat3 / n_cells_active, 4) if n_cells_active else None,
            "slot_saturated_rate_ge3_over_448": round(100.0 * sat3 / 448, 4),
        },
        "threads": {
            "n_threads_dm_threadid_dedup": n_threads_dm,
            "denominator_note": "分母 = MSG_DM 的 thread_id 去重数（d24/d25/P 判据同口径）",
            "len_dist": dict(sorted(lens.items())),
            "n_ge6": ge6,
            "threads_ge6_rate": round(100.0 * ge6 / n_threads_dm, 4) if n_threads_dm else None,
        },
    }


def run_tool(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return {"cmd": " ".join(cmd), "rc": p.returncode,
            "stdout_tail": p.stdout.strip().splitlines()[-3:],
            "stderr_tail": p.stderr.strip().splitlines()[-3:]}


def official_metrics(run_dir, tag, workdir):
    """调用仓内官方工具，返回 {Q1,Q2,Q3,T} 的取数与工具原始 rc。"""
    log = os.path.join(run_dir, "run.jsonl")
    out = {"tools": {}}

    # --- dialogue_metrics.py：Q2 = L-7_dup_ngram8_rate，Q3 = F-2_content_drift.drift_rate
    dm_json = os.path.join(workdir, f"metrics_{tag}.json")
    r = run_tool([PY, "tools/d5/dialogue_metrics.py", "--log", log,
                  "--out-json", dm_json, "--out-md", os.path.join(workdir, f"metrics_{tag}.md")],
                 REPO)
    out["tools"]["dialogue_metrics"] = r
    d = json.load(open(dm_json, encoding="utf-8"))
    out["Q2_L-7_dup_ngram8_rate"] = d["L_wording"]["L-7_dup_ngram8_rate"]
    out["Q3_F-2_content_drift"] = {
        "drift_rate": d["F-2_content_drift"]["drift_rate"],
        "denominator_adjacent_pairs": d["F-2_content_drift"]["denominator_adjacent_pairs"],
        "rule": d["F-2_content_drift"]["rule"],
        "legacy_F-2_topic_drift": d["F-2_topic_drift"]["drift_rate"],
        "legacy_status": d["F-2_topic_drift"]["status"],
    }
    out["dialogue_metrics_meta"] = d["meta"]
    out["dialogue_metrics_admission"] = d["admission"].get("checks", {}).get("B-10_provider")
    out["llm_calls_in_log"] = d["llm"]

    # --- l15_restate_rate.py：Q1
    l15_json = os.path.join(workdir, f"l15_{tag}.json")
    r = run_tool([PY, "tools/d5/l15_restate_rate.py", "--run", f"{tag}={log}",
                  "--out-json", l15_json], REPO)
    out["tools"]["l15_restate_rate"] = r
    if os.path.exists(l15_json):
        l = json.load(open(l15_json, encoding="utf-8"))
        blk = l.get(tag) or list(l.values())[0]
        out["Q1_L15_restate"] = {
            # 量纲：L-15 输出**已是百分数**（例：4.31 表示 4.31%），与 Q2/Q3 的分数制不同
            "restate_rate": blk.get("restate_rate"),
            "restate_strong_rate": blk.get("restate_strong_rate"),
            "unit": "percent",
            "n_msgs": blk.get("n_msgs"),
            "denominator": (blk.get("rule") or {}).get("denominator"),
            "by_turn": blk.get("by_turn"),
            "top_shared": blk.get("top_shared"),
        }

    # --- shape_gate.py：T
    sg_json = os.path.join(workdir, f"shape_{tag}.json")
    r = run_tool([PY, "tools/d12h/shape_gate.py", "--log", log, "--out-json", sg_json], REPO)
    out["tools"]["shape_gate"] = r
    if os.path.exists(sg_json):
        out["T_shape_gate"] = json.load(open(sg_json, encoding="utf-8"))
    return out


def diff_pp(b, c):
    if b is None or c is None:
        return None
    return round(b - c, 4)


def diff_rel(b, c):
    if b is None or not c:
        return None
    return round(100.0 * (b - c) / c, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--C", required=True, help="C 基线 run 目录")
    ap.add_argument("--B", required=True, help="B 本臂 run 目录")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--workdir", default="/tmp/d25a_gates_work")
    a = ap.parse_args()
    os.makedirs(a.workdir, exist_ok=True)

    res = {"prereg": "v2/refs/D25a-prereg-slot-quota.md", "arms": {}}
    for tag, rd in (("C", a.C), ("B", a.B)):
        st = structural(rd)
        off = official_metrics(rd, tag, a.workdir)
        meta_path = os.path.join(rd, "meta.json")
        meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else None
        res["arms"][tag] = {"run_dir": rd, "structural": st, "official": off, "meta": meta}

    C, B = res["arms"]["C"], res["arms"]["B"]
    cs, bs = C["structural"], B["structural"]
    co, bo = C["official"], B["official"]

    gates = {}
    # M1 机制生效
    m1a_c, m1a_b = cs["n_msgs_total_MSG_all"], bs["n_msgs_total_MSG_all"]
    m1b_c = cs["slot_cells"]["slot_saturated_rate_ge3_over_active"]
    m1b_b = bs["slot_cells"]["slot_saturated_rate_ge3_over_active"]
    gates["M1"] = {
        "rule": "n_msgs_total 相对 C ↑ >= 10% 且 slot_saturated_rate(>=3) >= 20%",
        "n_msgs_total": {"C": m1a_c, "B": m1a_b, "rel_pct": diff_rel(m1a_b, m1a_c)},
        "n_msgs_total_pass": (diff_rel(m1a_b, m1a_c) or 0) >= 10.0,
        "slot_saturated_rate_ge3": {"C": m1b_c, "B": m1b_b},
        "slot_saturated_rate_pass": (m1b_b or 0) >= 20.0,
        "verdict": None,
    }
    gates["M1"]["verdict"] = "PASS" if (gates["M1"]["n_msgs_total_pass"]
                                        and gates["M1"]["slot_saturated_rate_pass"]) else "FAIL"

    # P 主判据
    pc = cs["threads"]["threads_ge6_rate"]
    pb = bs["threads"]["threads_ge6_rate"]
    gates["P"] = {"rule": "threads_ge6_rate 相对 C ↑ >= 15pp",
                  "threads_ge6_rate": {"C": pc, "B": pb, "delta_pp": diff_pp(pb, pc)},
                  "numerator": {"C": cs["threads"]["n_ge6"], "B": bs["threads"]["n_ge6"]},
                  "denominator": {"C": cs["threads"]["n_threads_dm_threadid_dedup"],
                                  "B": bs["threads"]["n_threads_dm_threadid_dedup"]},
                  "verdict": "PASS" if (diff_pp(pb, pc) or 0) >= 15.0 else "FAIL"}

    # Q1 / Q2 / Q3 —— 量纲统一成「百分点(pp)」后再求差，量纲折算逐项落盘
    #   Q1 `L-15 restate_rate`：工具输出**已是百分数**（4.31 = 4.31%）
    #   Q2 `L-7_dup_ngram8_rate` / Q3 `F-2_content_drift.drift_rate`：工具输出是**分数**（0.441 = 44.1%）
    def q(name, rule, cv, bv, tol_pp, cunit, bunit, to_pp):
        cp = to_pp(cv, cunit)
        bp = to_pp(bv, bunit)
        d = diff_pp(bp, cp)
        gates[name] = {"rule": rule, "unit_normalization": {"C_raw": cv, "C_unit": cunit,
                                                            "B_raw": bv, "B_unit": bunit,
                                                            "C_pp": cp, "B_pp": bp},
                       "delta_pp": d,
                       "verdict": ("PASS" if (d is not None and d <= tol_pp) else "FAIL")
                       if d is not None else "UNDECIDABLE"}

    def frac_to_pct(v, unit):
        if v is None:
            return None
        return round(v * 100.0, 4) if unit == "fraction" else round(v, 4)

    q("Q1", "L-15 restate_rate 相对 C 升高 <= 2.0pp",
      (co.get("Q1_L15_restate") or {}).get("restate_rate"),
      (bo.get("Q1_L15_restate") or {}).get("restate_rate"),
      2.0, "percent", "percent", frac_to_pct)
    q("Q2", "L-7 norm8 相对 C 恶化 <= 3.0pp",
      co.get("Q2_L-7_dup_ngram8_rate"), bo.get("Q2_L-7_dup_ngram8_rate"),
      3.0, "fraction", "fraction", frac_to_pct)
    q("Q3", "F-2_content_drift 相对 C 升高 <= 2.0pp",
      (co.get("Q3_F-2_content_drift") or {}).get("drift_rate"),
      (bo.get("Q3_F-2_content_drift") or {}).get("drift_rate"),
      2.0, "fraction", "fraction", frac_to_pct)

    # S 保结构
    sc = cs["threads"]["n_threads_dm_threadid_dedup"]
    sb = bs["threads"]["n_threads_dm_threadid_dedup"]
    gates["S"] = {"rule": "n_threads 相对 C ±10%",
                  "n_threads_dm": {"C": sc, "B": sb, "rel_pct": diff_rel(sb, sc)},
                  "sensitivity_dialogue_metrics_n_threads": {
                      "C": (co.get("dialogue_metrics_meta") or {}).get("n_threads"),
                      "B": (bo.get("dialogue_metrics_meta") or {}).get("n_threads")},
                  "verdict": "PASS" if (diff_rel(sb, sc) is not None and abs(diff_rel(sb, sc)) <= 10.0) else "FAIL"}

    # T 文体闸 —— **两种读法都落盘**（这是预登记口径缺陷，见报告 §3）：
    #   ① 字面读法：shape_gate 默认基线是 T5，判「全 PASS」——T5 是很早的批次，
    #      当前树跑出来的任何批次都会在 F1/F2/F3 上偏离 T5 ⇒ 字面闸**无判别力**；
    #   ② 可用读法：C vs B 的相对漂移（同一棵树、同一基线，只差 override），
    #      容许带沿用 shape_gate 的 tol（F1 5pp / F2 15pp / F3 10% 相对）。
    def sg(o):
        t = o.get("T_shape_gate") or {}
        return t.get("gate") or {}, t.get("metrics") or {}, t.get("n_bodies")

    cg, cm, cn = sg(co)
    bg, bm, bn = sg(bo)
    rel = {}
    for k, tol in (("F1_paren", 5.0), ("F2_addr_head", 15.0), ("F3_len_p50_excl", 0.1)):
        if k not in cg or k not in bg:
            rel[k] = {"error": "shape_gate 输出缺该键"}
            continue
        if k == "F1_paren":
            cv, bv = cm.get("paren_rate"), bm.get("paren_rate")
            d = round((bv - cv) * 100.0, 4) if (bv is not None and cv is not None) else None
            rel[k] = {"metric": "paren_rate", "C": cv, "B": bv, "delta_pp": d, "tol_pp": tol,
                      "verdict": "PASS" if (d is not None and abs(d) <= tol) else "FAIL"}
        elif k == "F2_addr_head":
            cv, bv = cm.get("addr_head_strict"), bm.get("addr_head_strict")
            d = round((bv - cv) * 100.0, 4) if (bv is not None and cv is not None) else None
            rel[k] = {"metric": "addr_head_strict（判据口径；upper 仅参照）",
                      "C": cv, "B": bv, "delta_pp": d, "tol_pp": tol,
                      "verdict": "PASS" if (d is not None and abs(d) <= tol) else "FAIL"}
        else:
            cv, bv = cm.get("len_p50_excl"), bm.get("len_p50_excl")
            d = round((bv - cv) / cv, 6) if (cv and bv) else None
            rel[k] = {"metric": "len_p50_excl", "C": cv, "B": bv, "delta_rel": d, "tol_rel": tol,
                      "verdict": "PASS" if (d is not None and abs(d) <= tol) else "FAIL"}
    gates["T"] = {
        "rule_literal": "shape_gate F1/F2/F3 全 PASS（默认基线 T5）",
        "literal_verdict": {"C_tool_rc": C["official"]["tools"]["shape_gate"]["rc"],
                            "B_tool_rc": B["official"]["tools"]["shape_gate"]["rc"],
                            "C_gate_vs_T5": cg, "B_gate_vs_T5": bg},
        "rule_relative": "C vs B 相对漂移落在 shape_gate 同容许带内（同树同基线，只差 override）",
        "relative": rel,
        "relative_verdict": ("PASS" if all(v.get("verdict") == "PASS" for v in rel.values())
                             else "FAIL"),
        "n_bodies": {"C": cn, "B": bn},
    }

    # 代价闸（来自日志内 llm 记账；权威仍是 obs llm-cost，本脚本不替代它）
    cl = (co.get("llm_calls_in_log") or {}).get("llm_calls")
    bl = (bo.get("llm_calls_in_log") or {}).get("llm_calls")
    cdl = (co.get("llm_calls_in_log") or {}).get("dialogue_calls")
    bdl = (bo.get("llm_calls_in_log") or {}).get("dialogue_calls")
    gates["COST"] = {"rule": "llm_cost.calls 相对 C <= +50%（只记数不换算金额）",
                     "llm_calls_from_log": {"C": cl, "B": bl, "rel_pct": diff_rel(bl, cl)},
                     "dialogue_calls_from_log": {"C": cdl, "B": bdl, "rel_pct": diff_rel(bdl, cdl)},
                     "note": "本项以 obs llm-cost 输出为准；此处仅给日志内记账做交叉核对"}

    res["gates"] = gates
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    brief = {k: {kk: vv for kk, vv in v.items() if kk not in ("literal_verdict",)}
             for k, v in gates.items()}
    print(json.dumps(brief, ensure_ascii=False, indent=1))
    print("out_json", a.out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
