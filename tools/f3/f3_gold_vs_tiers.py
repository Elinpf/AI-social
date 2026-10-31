#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""f3_gold_vs_tiers.py —— 把「逐行标注」与「四档词表判定」对照，算 precision/recall（零跑批、零 LLM）。

两个层次，刻意分开报，不许混：
  (A) 仓内审查器口径（`v2/evidence/f3_audit_echo.py`）：四档只在「机会集」
      （线程内相邻对、上一句极性 ≠ 0）上求值。本脚本从审计 JSON 读回它的
      `in_opportunity_set` 与 `tier_*`，只做对照，不改它的口径。
  (B) 本脚本扩展口径：把四档规则**直接施加到全部 N 行 echo 线索**（不要求进机会集），
      这样 recall 的金标注分母才够得到 30。扩展口径是本脚本自己的重算，
      与 (A) 并列登记、不替换 (A)，报告里必须写清是哪一个口径。

分母纪律（沿用 CYCLE-39:472 预案）：
  任何比率的分母 < 30 ⇒ 打印「分母不足，停用该比率」，不凑数、不补样。

标注者身份：`--annotator` 必须显式传（本文件不写死），且 `--annotator-kind`
只能是 `llm_assisted`（本流程无人工金标注）。禁止把它写成「人工金标注」。

用法（仓库根）：
  python3 tools/f3/f3_gold_vs_tiers.py \
      --annotation v2/evidence/r38_f3_batch/f3_echo_gold_annotation.json \
      --audit v2/evidence/r38_f3_batch/f3_audit_echo.json --arm on \
      --annotator "town-implementer (DeepSeek-V4.1-Flash-1017)" \
      --json-out v2/evidence/r38_f3_batch/f3_gold_vs_tiers.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

EMPATHY_MARKERS = ("我懂", "我也", "别难过", "恭喜", "辛苦", "真惨", "太好了", "确实", "是啊", "可不是")
AGREEMENT_ONLY = ("我懂", "确实", "是啊", "可不是")
GENUINE = tuple(m for m in EMPATHY_MARKERS if m not in AGREEMENT_ONLY)
TIERS = ("loose", "loose_no_agree", "polarity_match", "marker_based")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


f4a = _load("f4_anchor_recompute_gold", os.path.join(REPO, "tools/f4/f4_anchor_recompute.py"))
EMO = f4a.load_emotion(os.path.join(REPO, "tools/d5/emotion_lexicon.txt"))


def polarity(body, emo=None):
    """照 `tools/d5/dialogue_metrics.py:1043-1051` 逐行复制（词表子串计数多数胜）。"""
    emo = emo or EMO
    pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
    neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def wilson(k, n, z=1.959963984540054):
    """二项比例 Wilson 95% 区间（与 tools/f3/f3_metrics.py 同式）。"""
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [round((c - r) / d, 6), round((c + r) / d, 6)]


def r6(x):
    return None if x is None else round(float(x), 6)


def tier_of(row: dict) -> dict:
    """把四档规则施加到单行（扩展口径 B）。极性判定沿用审计器给出的 prev_polarity。"""
    cur = row.get("cur_body") or ""
    p_prev = row.get("prev_polarity")
    p_cur = polarity(cur)
    any_marker = [m for m in EMPATHY_MARKERS if m in cur]
    genuine = [m for m in GENUINE if m in cur]
    no_agree = [m for m in EMPATHY_MARKERS if m in cur and m not in ("我懂",)]
    # 当前句极性：审计 JSON 未必带 p_cur，这里用同一词表由 cur_body 重算
    same_polarity = (p_prev is not None and p_prev != 0 and p_cur == p_prev)
    return {
        "any_marker": any_marker,
        "genuine_marker": genuine,
        "no_agree_marker": no_agree,
        "p_prev": p_prev,
        "p_cur": p_cur,
        "same_polarity": same_polarity,
        "loose": bool(same_polarity) or bool(any_marker),
        "loose_no_agree": bool(same_polarity) or bool(no_agree),
        "polarity_match": bool(same_polarity),
        "marker_based": bool(genuine),
    }


def prf(hit_rows: int, gold_pos: int, n: int) -> dict:
    tp = hit_rows  # 本对照里「命中行」全部按 gold 正例计（命中集与 gold 正例的交集下面单独算）
    return {"hits": hit_rows, "gold_pos": gold_pos, "n": n}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotation", required=True)
    ap.add_argument("--audit", default="")
    ap.add_argument("--arm", default="on")
    ap.add_argument("--annotator", required=True)
    ap.add_argument("--annotator-kind", default="llm_assisted",
                    choices=["llm_assisted"], help="本流程只有 LLM 辅助标注，禁止改成人工金标注")
    ap.add_argument("--min-den", type=int, default=30)
    ap.add_argument("--json-out", default="")
    a = ap.parse_args()

    ann = json.load(open(a.annotation if os.path.isabs(a.annotation) else os.path.join(REPO, a.annotation),
                         encoding="utf-8"))
    rows = ann["rows"]
    n = len(rows)
    gold_pos = sum(1 for r in rows if r["gold_label"] == "y")
    gold_neg = sum(1 for r in rows if r["gold_label"] == "n")
    gold_na = sum(1 for r in rows if r["gold_label"] == "x")

    # 扩展口径：对全部行重算四档
    for r in rows:
        r["tier_ext"] = tier_of(r)

    # (A) 仓内审查器口径
    audit = None
    if a.audit:
        ad = json.load(open(a.audit if os.path.isabs(a.audit) else os.path.join(REPO, a.audit),
                            encoding="utf-8"))
        arm = [x for x in ad["arms"] if x["meta"]["label"] == a.arm][0]
        mech = arm["mechanism"]
        audit = {
            "source": "v2/evidence/f3_audit_echo.py（机会集口径）",
            "n_echo_rows": mech["echo_rows_n"],
            "n_in_opportunity_set": mech.get("echo_rows_in_opportunities"),
            "tier_hit": mech.get("echo_rows_tier_hit"),
            "never_hit_any_tier": mech.get("echo_rows_never_hit_any_tier"),
            "coverage_of_echo_rows": r6((mech.get("echo_rows_in_opportunities") or 0) / mech["echo_rows_n"]),
        }
        opp = [r for r in rows if r.get("in_opportunity_set")]
        audit["gold_pos_in_opportunity_set"] = sum(1 for r in opp if r["gold_label"] == "y")
        audit["gold_labels_in_opportunity_set"] = [{"row_no": r["row_no"], "seq": r["seq"],
                                                    "gold": r["gold_label"]} for r in opp]
        audit["recall_on_opportunity_set"] = (
            {"num": sum(1 for r in opp if any(r.get(f"tier_{t}") for t in TIERS)),
             "den": len(opp),
             "reportable": len(opp) >= a.min_den}
        )

    # (B) 扩展口径：逐档 confusion
    ext = {}
    for t in TIERS:
        hit = [r for r in rows if r["tier_ext"][t]]
        tp = sum(1 for r in hit if r["gold_label"] == "y")
        fp = sum(1 for r in hit if r["gold_label"] == "n")
        na_hit = sum(1 for r in hit if r["gold_label"] == "x")
        ext[t] = {
            "hits": len(hit),
            "tp": tp,
            "fp": fp,
            "hit_on_na": na_hit,
            "precision": r6(tp / len(hit)) if hit else None,
            "precision_den": len(hit),
            "precision_reportable": len(hit) >= a.min_den,
            "recall": r6(tp / gold_pos) if gold_pos else None,
            "recall_wilson95": wilson(tp, gold_pos) if gold_pos else None,
            "hit_rows": [{"row_no": r["row_no"], "seq": r["seq"], "gold": r["gold_label"],
                          "markers": r["tier_ext"]["genuine_marker"]} for r in hit],
            "recall_den": gold_pos,
            "recall_reportable": gold_pos >= a.min_den,
        }
        if not ext[t]["precision_reportable"]:
            ext[t]["precision_verdict"] = f"分母不足（{len(hit)} < {a.min_den}）⇒ 停用该精确率"
        if not ext[t]["recall_reportable"]:
            ext[t]["recall_verdict"] = f"分母不足（{gold_pos} < {a.min_den}）⇒ 停用该召回率"

    print(f"标注者 = {a.annotator}（kind={a.annotator_kind}，**非人工金标注**）")
    print(f"行数 n={n} | gold: 接住(y)={gold_pos} 未接住(n)={gold_neg} 无可呼应(x)={gold_na}")
    print(f"y+n（可判定集 E）={gold_pos + gold_neg}")
    print("\n### (A) 仓内审查器口径（机会集）")
    if audit:
        print(f"- echo 行={audit['n_echo_rows']}，落进机会集={audit['n_in_opportunity_set']} "
              f"（覆盖率 {audit['coverage_of_echo_rows']}）")
        print(f"- 四档命中={json.dumps(audit['tier_hit'], ensure_ascii=False)}；"
              f"给了但四档全不命中={audit['never_hit_any_tier']}")
        print(f"- 机会集内金标注={audit['gold_labels_in_opportunity_set']}")
        rc = audit["recall_on_opportunity_set"]
        print(f"- 机会集内 recall={rc['num']}/{rc['den']} ⇒ "
              f"{'可报' if rc['reportable'] else f'分母不足（{rc[chr(100)+chr(101)+chr(110)]} < {a.min_den}）⇒ 停用该比率'}")
    print("\n### (B) 扩展口径（四档直接施加到全部行；本脚本重算，不替换 A）")
    print("| tier | hits | TP | FP | 命中在 x 行 | precision | 分母 | recall | 分母 | 可否报 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for t in TIERS:
        e = ext[t]
        ok = "可报" if (e["precision_reportable"] and e["recall_reportable"]) else \
             ("精确率停用" if not e["precision_reportable"] else "召回率停用")
        print(f"| {t} | {e['hits']} | {e['tp']} | {e['fp']} | {e['hit_on_na']} | {e['precision']} | "
              f"{e['precision_den']} | {e['recall']} {e['recall_wilson95']} | {e['recall_den']} | {ok} |")

    payload = {
        "schema": "f3-gold-vs-tiers/1",
        "annotator": a.annotator,
        "annotator_kind": a.annotator_kind,
        "annotator_declaration": "LLM 辅助标注，不是人工金标注；未做双人独立标注，无 kappa。",
        "n_rows": n,
        "gold": {"y": gold_pos, "n": gold_neg, "x": gold_na, "E": gold_pos + gold_neg},
        "min_den": a.min_den,
        "A_inhouse_opportunity_set": audit,
        "B_extended_all_rows": ext,
    }
    if a.json_out:
        p = a.json_out if os.path.isabs(a.json_out) else os.path.join(REPO, a.json_out)
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
        print(f"\nwritten: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
