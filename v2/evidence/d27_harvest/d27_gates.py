#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""d27_gates.py —— D2.7（旁白放开）判据复算器（**只读**：零 LLM、零跑批、不改 code/）

口径纪律（全部**调用仓内既有官方工具**，本脚本只做"取数 + 求差 + 对照预登记阈值"）：
  · P1 二元 / P2 / paren / n_msgs / n_threads / len_p50 ← `v2/evidence/d12c_metrics.py`（冻结）
  · P1 连续口径（count_mean/p50/zero_share）        ← `v2/evidence/d27_harvest/p1_count.py`
  · M1-b 短旁白占比 / 旁白字数 / 心理描写占比        ← `v2/evidence/d27_run_scripts/d27_metrics.py`
  · Q1 L-15 restate_rate                            ← `tools/d5/l15_restate_rate.py`
  · Q2 L-7 norm8 / Q3 F-2_content_drift             ← `tools/d5/dialogue_metrics.py`
  · T  len_p50_excl                                 ← `tools/d12h/shape_gate.py`
  · ge6（线程级比例）分母 = **全部 thread_id 去重**（含无 from 的匿名旁白线程，runbook §3.119），
    并与 `dialogue_metrics.meta`/结构性 `n_threads` 对账。

预登记阈值原样写死在 THRESH（不得在跑完后改）：
  v2/refs/D27-amendment1-merge-duplicate-prereg.md §3

用法：
  python3 v2/evidence/d27_harvest/d27_gates.py \
      --C v2/evidence/run_d27_C_n16r60_seed42 \
      --B .worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42 \
      --out-dir v2/evidence/d27_harvest
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PY = sys.executable
MSG = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
LEAD = re.compile(r"^\s*[（(]")
PAREN_FULL = re.compile(r"^\s*[（(]([^）)]{1,200})[）)]")

# ---- 预登记阈值（D27-amendment1 §3，一字不改）----
THRESH = {
    "M1_paren_min_pct": 30.0,
    "M1b_short_share_min_pct": 80.0,
    "P_delta_pp_min": 5.0,
    "Q1_delta_pp_max": 2.0,
    "Q2_worse_pp_max": 3.0,
    "Q2_gain_pp_min": 3.0,
    "Q3_delta_pp_max": 2.0,
    "S_rel_tol_pct": 10.0,
    "T_rel_tol_pct": 10.0,
    "cost_calls_rel_max_pct": 10.0,
    "cost_tokens_rel_max_pct": 40.0,
}


def run(cmd, allow_rc=(0,)):
    """allow_rc：shape_gate 在本树上对 T5 内置基线必然 rc=1（F1/F2/F3 FAIL，属设计行为），
    dialogue_metrics 在准入 FAIL 时 rc=2 但指标已算出 ⇒ 这两处必须放宽，否则复算器自己会假红。"""
    p = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    if p.returncode not in allow_rc:
        raise SystemExit(f"FAIL rc={p.returncode}: {' '.join(map(str, cmd))}\n{p.stdout}\n{p.stderr}")
    return p.stdout


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def dialogue_token_evidence(C: Path, B: Path) -> dict:
    """运行期「新提示词真的生效」的量化证据（替代 prompt_hash 方案）。

    判据表来源（**事前冻结**）：`v2/evidence/d27_gate_prediction_prereg.md`
    （evidence-gate 落笔 2026-10-24T16:12:20+08:00，B 臂 round 45/60 时写，早于任何 B 指标出数）。
    淡化：两树 prompt 尾段各 +35 字符（initiate 258→293 / reply 271→306，见 d27_prompt_wiring.json）。
    判定**一律取 uncached 均值**（若 B 有 cached，命中调用 tokens_in 偏低会向下拽均值 ⇒ 假阴性陷阱）。
    """
    def stats(p):
        n = cached = tin = tout = 0
        tin_u = n_u = 0
        for line in open(p, encoding="utf-8"):
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") != "LLM_CALL":
                continue
            pl = e.get("payload") or {}
            if (pl.get("purpose") or "") != "dialogue":
                continue
            n += 1
            t = int(pl.get("tokens_in") or 0)
            tin += t
            tout += int(pl.get("tokens_out") or 0)
            if pl.get("cached"):
                cached += 1
            else:
                n_u += 1
                tin_u += t
        return {"calls": n, "cached": cached, "uncached": n_u,
                "tokens_in": tin, "tokens_out": tout,
                "tokens_in_mean_all": round(tin / n, 2) if n else None,
                "tokens_in_mean_uncached": round(tin_u / n_u, 2) if n_u else None,
                "tokens_out_mean": round(tout / n, 2) if n else None}

    def band(v):
        if v is None:
            return "不可判（无 uncached dialogue 调用）"
        if v < 302:
            return "未生效（≈C 或更低）⇒ 接线作废，即使 M1 达标也须重查"
        if v < 320:
            return "灰区：既不得判强证据也不得判失败 ⇒ 须补①实际分词器/usage 核 35 字符折算、②B vs C 对话历史长度分布；仍落灰区则写『运行期证据不足，结论降级』"
        if v < 335:
            return "强证据：新 prompt 确已进入运行时"
        if v <= 360:
            return "仍判生效（偏上归因于历史更长，不得判失败）"
        return "判生效，但须单独说明为何远超预测（多半历史膨胀）"

    c, b = stats(C / "run.jsonl"), stats(B / "run.jsonl")
    v = b["tokens_in_mean_uncached"]
    out = {"prereg": "v2/evidence/d27_gate_prediction_prereg.md（2026-10-24T16:12:20+08:00 事前冻结）",
           "C": c, "B": b,
           "B_tokens_in_mean_uncached": v,
           "delta_vs_C_uncached": (round(v - c["tokens_in_mean_uncached"], 2)
                                   if v is not None and c["tokens_in_mean_uncached"] is not None else None),
           "band_table": {"<302": "未生效", "[302,320)": "灰区", "[320,335)": "强证据",
                          "[335,360]": "仍判生效", ">360": "生效但需说明"},
           "verdict": band(v)}
    return out


def structural(run_dir: Path) -> dict:
    """ge6 / 线程长度分布：分母 = 全部 thread_id 去重（含匿名旁白线程）"""
    th = Counter()
    n_msg = 0
    anon_threads = set()
    for line in open(run_dir / "run.jsonl", encoding="utf-8"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG:
            continue
        pl = e.get("payload") or {}
        tid = pl.get("thread_id") or f"legacy-{pl.get('msg_uid')}"
        th[tid] += 1
        n_msg += 1
        if not (pl.get("from") or pl.get("author")):
            anon_threads.add(tid)
    ge6 = sum(1 for v in th.values() if v >= 6)
    one = sum(1 for v in th.values() if v == 1)
    return {
        "n_msgs": n_msg,
        "n_threads_all": len(th),
        "n_threads_dm_only": None,  # 见 dm_only 字段（另算）
        "n_single_msg_threads": one,
        "n_anon_threads": len(anon_threads),
        "n_ge6": ge6,
        "threads_ge6_rate_pct_all": round(100.0 * ge6 / len(th), 2) if th else None,
    }


def paren_template(run_dir: Path, top: int = 8) -> dict:
    """旁白模板重复检查：括号内文字的出现次数分布（判「每句都是同一个动作」）"""
    c = Counter()
    n_lead = 0
    for line in open(run_dir / "run.jsonl", encoding="utf-8"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG:
            continue
        b = ((e.get("payload") or {}).get("body") or "")
        if not LEAD.match(b):
            continue
        n_lead += 1
        m = PAREN_FULL.match(b)
        inner = (m.group(1).strip() if m else "")[:40]
        c[inner] += 1
    items = [{"paren": k, "n": v, "share_of_lead_pct": round(100.0 * v / n_lead, 2) if n_lead else None}
             for k, v in c.most_common(top)]
    return {"n_lead_messages": n_lead, "n_distinct_paren": len(c), "top_parens": items,
            "top1_share_pct": round(100.0 * c.most_common(1)[0][1] / n_lead, 2) if n_lead else None}


def diff_pp(b, c):
    if b is None or c is None:
        return None
    return round(b - c, 2)


def rel(b, c):
    if b is None or c is None or c == 0:
        return None
    return round(100.0 * (b - c) / c, 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--C", required=True, help="C 臂 run 目录")
    ap.add_argument("--B", required=True, help="B 臂 run 目录")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    C = (REPO / a.C).resolve() if not Path(a.C).is_absolute() else Path(a.C)
    B = (REPO / a.B).resolve() if not Path(a.B).is_absolute() else Path(a.B)
    out = (REPO / a.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    clog, blog = C / "run.jsonl", B / "run.jsonl"
    for p in (clog, blog):
        if not p.is_file():
            raise SystemExit(f"缺日志：{p}")

    # ---------- 1) 官方工具取数（逐个落盘，可审计） ----------
    run([PY, "v2/evidence/d12c_metrics.py", "--run", f"C={clog}", "--run", f"B={blog}",
         "--out-json", str(out / "d12c_c_b.json")])
    run([PY, "v2/evidence/d27_harvest/p1_count.py", "--run", f"C={clog}", "--run", f"B={blog}",
         "--out-json", str(out / "p1_count_c_b.json")])
    # d27_metrics.py 是 B 臂 worktree 里的只读读数器（未入库）。为可复算，copy 了一份到
    # v2/evidence/d27_harvest/d27_metrics.py，二者 sha256 = 46d527d8e70164966f3bbfaf5e80248284966b727567279108e5907d5b589d65
    d27m_py = REPO / "v2" / "evidence" / "d27_harvest" / "d27_metrics.py"
    if not d27m_py.is_file():
        raise SystemExit(f"缺 d27_metrics.py：{d27m_py}")
    run([PY, str(d27m_py), "--run", f"C={clog}", "--run", f"B={blog}",
         "--out-json", str(out / "d27_metrics_c_b.json")])
    run([PY, "tools/d5/l15_restate_rate.py", "--run", f"C={clog}", "--run", f"B={blog}",
         "--out-json", str(out / "l15_c_b.json")])
    for tag, logd in (("C", C), ("B", B)):
        meta = logd / "meta.json"
        cmd = [PY, "tools/d5/dialogue_metrics.py", "--log", str(logd / "run.jsonl"),
               "--out-json", str(out / f"dm_{tag}.json"), "--out-md", str(out / f"dm_{tag}.md")]
        if meta.is_file():
            cmd += ["--meta", str(meta)]
        run(cmd, allow_rc=(0, 2))
        run([PY, "tools/d12h/shape_gate.py", "--log", str(logd / "run.jsonl"),
             "--out-json", str(out / f"shape_{tag}.json")], allow_rc=(0, 1))

    d12c = load(out / "d12c_c_b.json")
    p1c = load(out / "p1_count_c_b.json")
    d27m = load(out / "d27_metrics_c_b.json")
    l15 = load(out / "l15_c_b.json")
    dmc, dmb = load(out / "dm_C.json"), load(out / "dm_B.json")
    sgc, sgb = load(out / "shape_C.json"), load(out / "shape_B.json")
    stc, stb = structural(C), structural(B)
    tpc, tpb = paren_template(C), paren_template(B)

    # dialogue_metrics 的线程数与结构性线程数对账（§3.119 第 3 条）
    recon = {"C": {"structural_all": stc["n_threads_all"],
                   "dialogue_metrics_threads": (dmc.get("meta") or {}).get("n_threads"),
                   "d12c_n_threads": d12c["C"]["n_threads"]},
             "B": {"structural_all": stb["n_threads_all"],
                   "dialogue_metrics_threads": (dmb.get("meta") or {}).get("n_threads"),
                   "d12c_n_threads": d12c["B"]["n_threads"]}}

    # ---------- 2) 逐判据对照 ----------
    c, b = d12c["C"], d12c["B"]
    gates = {}

    # M1
    gates["M1"] = {
        "rule": f"paren_rate 0.00%→>={THRESH['M1_paren_min_pct']}% 且 短旁白(len<=80)占比>={THRESH['M1b_short_share_min_pct']}%",
        "paren_rate_C": c["paren_rate"], "paren_rate_B": b["paren_rate"],
        "M1a_pass": b["paren_rate"] is not None and b["paren_rate"] >= THRESH["M1_paren_min_pct"],
        "short_paren_share_pct": d27m["B"]["M1b_short_paren_share_pct"],
        "M1b_denominator": d27m["B"]["M1b_denominator"],
        "paren_inner_len_p50": d27m["B"]["paren_inner_len_p50"],
        "paren_inner_len_max": d27m["B"]["paren_inner_len_max"],
        "paren_mental_share_pct": d27m["B"]["paren_mental_share_pct"],
        "M1b_pass": (d27m["B"]["M1b_short_paren_share_pct"] or 0) >= THRESH["M1b_short_share_min_pct"],
    }
    gates["M1"]["pass"] = gates["M1"]["M1a_pass"] and gates["M1"]["M1b_pass"]

    # P（主判据：二元 + 连续口径并列）
    dp = diff_pp(b["P1_specificity_rate"], c["P1_specificity_rate"])
    gates["P"] = {
        "rule": f"P1 具体性 相对 C ↑>={THRESH['P_delta_pp_min']}pp（二元口径；天花板效应并列连续口径）",
        "P1_binary_C": c["P1_specificity_rate"], "P1_binary_B": b["P1_specificity_rate"],
        "P1_binary_delta_pp": dp,
        "ceiling_headroom_pp": round(100.0 - c["P1_specificity_rate"], 2),
        "P1_count_mean_C": p1c["C"]["P1_count_mean"], "P1_count_mean_B": p1c["B"]["P1_count_mean"],
        "P1_count_mean_rel_pct": rel(p1c["B"]["P1_count_mean"], p1c["C"]["P1_count_mean"]),
        "P1_count_p50_C": p1c["C"]["P1_count_p50"], "P1_count_p50_B": p1c["B"]["P1_count_p50"],
        "P1_count_zero_share_C": p1c["C"]["P1_count_zero_share_pct"],
        "P1_count_zero_share_B": p1c["B"]["P1_count_zero_share_pct"],
        "pass": dp is not None and dp >= THRESH["P_delta_pp_min"],
    }
    gates["P_observe"] = {
        "P2_thirdparty_C": c["P2_thirdparty_rate"], "P2_thirdparty_B": b["P2_thirdparty_rate"],
        "delta_pp": diff_pp(b["P2_thirdparty_rate"], c["P2_thirdparty_rate"]),
        "note": "仅观察，不作判据",
    }

    # Q1
    q1c = (l15["C"] or {}).get("restate_rate")
    q1b = (l15["B"] or {}).get("restate_rate")
    d1 = diff_pp(q1b, q1c)
    gates["Q1"] = {"rule": f"L-15 restate_rate 相对 C ↑<={THRESH['Q1_delta_pp_max']}pp",
                   "C": q1c, "B": q1b, "delta_pp": d1,
                   "strong_C": (l15["C"] or {}).get("restate_strong_rate"),
                   "strong_B": (l15["B"] or {}).get("restate_strong_rate"),
                   "by_turn_B": (l15["B"] or {}).get("by_turn"),
                   "pass": d1 is not None and d1 <= THRESH["Q1_delta_pp_max"]}

    # Q2 —— Δ 必须用**未四舍五入的原始分数**求差（D2.7 实测：28.4861-25.4902=2.9959，
    #      若先各自 round(...,2) 会变成 3.00，把"擦线过"写成"正好 3pp"，属口径事故）
    q2c_raw = 100.0 * dmc["L_wording"]["L-7_dup_ngram8_rate"]
    q2b_raw = 100.0 * dmb["L_wording"]["L-7_dup_ngram8_rate"]
    q2c, q2b = round(q2c_raw, 4), round(q2b_raw, 4)
    d2 = round(q2b_raw - q2c_raw, 4)
    gates["Q2"] = {"rule": f"L-7 norm8 恶化<={THRESH['Q2_worse_pp_max']}pp；下降>={THRESH['Q2_gain_pp_min']}pp 记增益",
                   "C": q2c, "B": q2b, "delta_pp": d2,
                   "pass": d2 is not None and d2 <= THRESH["Q2_worse_pp_max"],
                   "margin_pp": round(THRESH["Q2_worse_pp_max"] - d2, 4) if d2 is not None else None,
                   "is_gain": d2 is not None and d2 <= -THRESH["Q2_gain_pp_min"]}

    # Q3
    q3c_raw = 100.0 * dmc["F-2_content_drift"]["drift_rate"]
    q3b_raw = 100.0 * dmb["F-2_content_drift"]["drift_rate"]
    q3c, q3b = round(q3c_raw, 4), round(q3b_raw, 4)
    d3 = round(q3b_raw - q3c_raw, 4)
    gates["Q3"] = {"rule": f"F-2_content_drift 相对 C 升<={THRESH['Q3_delta_pp_max']}pp",
                   "C": q3c, "B": q3b, "delta_pp": d3,
                   "denominator_adjacent_pairs": {"C": dmc["F-2_content_drift"]["denominator_adjacent_pairs"],
                                                  "B": dmb["F-2_content_drift"]["denominator_adjacent_pairs"]},
                   "pass": d3 is not None and d3 <= THRESH["Q3_delta_pp_max"]}

    # S
    s_nmsgs = rel(b["n_msgs"], c["n_msgs"])
    s_nthr = rel(stb["n_threads_all"], stc["n_threads_all"])
    gates["S"] = {"rule": f"n_msgs / n_threads 相对 C ±{THRESH['S_rel_tol_pct']}%",
                  "n_msgs": {"C": c["n_msgs"], "B": b["n_msgs"], "rel_pct": s_nmsgs},
                  "n_threads": {"C": stc["n_threads_all"], "B": stb["n_threads_all"], "rel_pct": s_nthr},
                  "ge6": {"C": stc["threads_ge6_rate_pct_all"], "B": stb["threads_ge6_rate_pct_all"],
                          "n_ge6": {"C": stc["n_ge6"], "B": stb["n_ge6"]},
                          "delta_pp": diff_pp(stb["threads_ge6_rate_pct_all"], stc["threads_ge6_rate_pct_all"])},
                  "pass": all(v is not None and abs(v) <= THRESH["S_rel_tol_pct"] for v in (s_nmsgs, s_nthr))}

    # T
    t_c = sgc["metrics"]["len_p50_excl"]
    t_b = sgb["metrics"]["len_p50_excl"]
    t_rel = rel(t_b, t_c)
    gates["T"] = {"rule": f"len_p50_excl（去括号后台词长度）相对 C ±{THRESH['T_rel_tol_pct']}%",
                  "C": t_c, "B": t_b, "rel_pct": t_rel,
                  "dn_p50_excl_from_d27metrics": {"C": d27m["C"]["len_p50_excl_paren"],
                                                  "B": d27m["B"]["len_p50_excl_paren"]},
                  "pass": t_rel is not None and abs(t_rel) <= THRESH["T_rel_tol_pct"]}

    # 代价
    def llm_of(m):
        llm = m.get("llm") or {}
        return llm
    lc, lb = llm_of(dmc), llm_of(dmb)
    gates["cost"] = {"rule": f"calls ≤+{THRESH['cost_calls_rel_max_pct']}%；tokens ≤+{THRESH['cost_tokens_rel_max_pct']}%",
                     "llm_C": lc, "llm_B": lb, "note": "权威 = tools / obs llm-cost；此处仅日志内记账交叉核对"}

    # 旁白模板检查
    gates["narration_template"] = {"C": tpc, "B": tpb}
    # 运行期 prompt 接线证据
    gates["dialogue_token_runtime"] = dialogue_token_evidence(C, B)

    # ---------- 附录：若沿用「跨批污染基线」结论会变成什么（审计项，不是可选） ----------
    # 污染值 = D2.5a 的 C 臂（另一棵树 e2e7131），被误写进 d27_C_baseline_readings.md §1
    LEGACY_C = {"Q1_L15_restate_rate_pct": 4.12, "Q1_restate_strong_pct": 2.16,
                "Q2_L-7_norm8_pct": 20.59, "Q3_F-2_content_drift_pct": 66.28,
                "T_len_p50_excl": 40.0}
    appendix = {
        "note": "审计项：证明『换基线』不是为了让结论变好看。阈值一个未动，只换基线来源。",
        "legacy_baseline_source": "v2/evidence/d25a_result.md:26-28（D2.5a C 臂，code_sha e2e7131，另一棵树）",
        "legacy_baseline": LEGACY_C,
        "Q1": {"delta_pp_if_legacy": diff_pp(q1b, LEGACY_C["Q1_L15_restate_rate_pct"]),
               "delta_pp_corrected": d1,
               "verdict_if_legacy": "PASS" if (diff_pp(q1b, LEGACY_C["Q1_L15_restate_rate_pct"]) or 99) <= THRESH["Q1_delta_pp_max"] else "FAIL",
               "verdict_corrected": "PASS" if gates["Q1"]["pass"] else "FAIL"},
        "Q2": {"delta_pp_if_legacy": diff_pp(q2b, LEGACY_C["Q2_L-7_norm8_pct"]),
               "delta_pp_corrected": d2,
               "verdict_if_legacy": "PASS" if (diff_pp(q2b, LEGACY_C["Q2_L-7_norm8_pct"]) or 99) <= THRESH["Q2_worse_pp_max"] else "FAIL（重复恶化）",
               "verdict_corrected": "PASS" if gates["Q2"]["pass"] else "FAIL（重复恶化）"},
        "Q3": {"delta_pp_if_legacy": diff_pp(q3b, LEGACY_C["Q3_F-2_content_drift_pct"]),
               "delta_pp_corrected": d3,
               "verdict_if_legacy": "PASS" if (diff_pp(q3b, LEGACY_C["Q3_F-2_content_drift_pct"]) or 99) <= THRESH["Q3_delta_pp_max"] else "FAIL（内容漂移）",
               "verdict_corrected": "PASS" if gates["Q3"]["pass"] else "FAIL（内容漂移）"},
        "T": {"rel_pct_if_legacy": rel(t_b, LEGACY_C["T_len_p50_excl"]),
              "rel_pct_corrected": t_rel,
              "verdict_if_legacy": "PASS" if abs(rel(t_b, LEGACY_C["T_len_p50_excl"]) or 99) <= THRESH["T_rel_tol_pct"] else "FAIL（作废）",
              "verdict_corrected": "PASS" if gates["T"]["pass"] else "FAIL（作废）"},
        "M1_P_unchanged": "M1/P 的 C 值（0.00% / 93.53% / 3.1941）本就属于 run_d27_C，不受本次污染影响，两套基线同值。",
    }
    gates["appendix_legacy_baseline"] = appendix

    # 判定合成
    hard = ["M1", "P", "Q1", "Q2", "Q3", "S", "T"]
    allpass = all(gates[k]["pass"] for k in hard)
    verdict = "有效" if allpass else "未达（见各项）"
    tail = []
    if gates["Q2"].get("is_gain"):
        tail.append("L-7 同时下降≥3pp（并列增益）")
    if not gates["P"]["pass"] and gates["P"]["P1_binary_delta_pp"] is not None \
            and gates["P"]["ceiling_headroom_pp"] < 7:
        tail.append("P1 二元口径受天花板限制（可用空间 %.2fpp）" % gates["P"]["ceiling_headroom_pp"])
    result = {"verdict": verdict, "gates": gates, "reconciliation": recon,
              "thresholds": THRESH,
              "inputs": {"C": str(C), "B": str(B)},
              "note": "；".join(tail)}
    (out / "d27_gates.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
