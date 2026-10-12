"""校准度量（M2b 准入）—— **纯函数、只读、确定性**（无随机 / 无时钟）。

唯一目的：给「判别式判定的置信度是否可信」一个**单一实现**，供 T203/T212 共用。
**ECE 是最容易"同名不同义"的指标**（分档数、边界、缺失参考标签）—— 本模块是**唯一口径**。

交付（共用一个模块 + `__main__` 复算脚本）：
  - `reliability_diagram`        可靠性图（每档 conf vs acc）
  - `expected_calibration_error` ECE = Σ_b (n_b/N)·|acc_b − conf_b|
  - `tiered_hit_rate`            分层命中率 + 单调性 + top/bottom
  - `score_gap_analysis`         top-2 候选分差 vs 正确性：AUC / 点二列相关 / 阈值扫描
  - `calibration_report`         汇总 + **门禁裁决**（是否允许"置信度回退"）

门禁规则（T203 §4.10）：
  允许置信度回退 ⇔ `ECE ≤ ece_threshold` **或**（分层命中率单调 **且** top−bottom ≥ monotone_min_gap）；
  否则 **禁用置信度回退** → 改用**规则判定**（候选分差阈值）。
口径固定：分档等宽、闭左开右、最后一档含 1.0；缺失参考标签的样本必须先剔除（调用方负责），本模块不猜。

**⚠️ 两份对照，别混（T203 方法论）**：
  - **一致率 `agreement_rate(predicted, reference_A)`** —— reference 取**生成式 A（T2）标签**，衡量「判别式是否**等价**于生成式」（质量是否被偷走）。
  - **准确率 + ECE** —— `correct` 必须来自**真值**（= 与**确定性后果**的吻合；**不得把 A 的标签当正确答案**），否则测出的只是"与 A 一致率"、**测不出校准**。
  - 本模块只做**纯度量**；"确定性后果"真值口径由调用方（T212/obs）定义并落盘。
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

__all__ = [
    "reliability_diagram", "expected_calibration_error", "tiered_hit_rate",
    "score_gap_analysis", "calibration_report", "agreement_rate",
    "multiclass_brier", "multiclass_logloss", "multiclass_report",
]


def _probs_of(rec):
    return rec.get("probs") or rec.get("label_probs") or {}


def multiclass_brier(records) -> float | None:
    """多类 Brier = mean_rec Σ_k (p_k − 1[k==true])²（对 `label_probs` 的**排序键**累加，确定性）。

    `records`：每项 `{"true_label": str|None, "probs"|"label_probs": {option: prob}}`。
    仅取 `true_label` 与 `probs` 都存在的样本；无样本 → None。
    """
    vals = []
    for rec in records:
        tl, probs = rec.get("true_label"), _probs_of(rec)
        if tl is None or not probs:
            continue
        vals.append(sum((float(probs[k]) - (1.0 if k == tl else 0.0)) ** 2
                        for k in sorted(probs)))
    return round(sum(vals) / len(vals), 6) if vals else None


def multiclass_logloss(records, eps: float = 1e-12) -> float | None:
    """多类 log-loss = mean(−ln p_true)，`p_true` 截断到 [eps,1]。确定性。"""
    vals = []
    for rec in records:
        tl, probs = rec.get("true_label"), _probs_of(rec)
        if tl is None or not probs:
            continue
        p = probs.get(tl, eps)
        p = min(1.0, max(eps, float(p)))
        vals.append(-math.log(p))
    return round(sum(vals) / len(vals), 6) if vals else None


def multiclass_report(records) -> dict:
    recs = [r for r in records if r.get("true_label") is not None and _probs_of(r)]
    return {"n": len(recs), "brier": multiclass_brier(records),
            "logloss": multiclass_logloss(records)}


def agreement_rate(predicted, reference) -> float:
    """`predicted` 与 `reference` 的逐条一致率。

    ⚠️ **这不是校准**：它衡量「判别式是否等价于生成式 A」（质量是否被偷走），
    **不得**用它替代准确率去算 ECE（ECE 的 `correct` 必须来自**真值**，见 `calibration_report` 文档）。
    """
    predicted = list(predicted)
    reference = list(reference)
    if len(predicted) != len(reference):
        raise ValueError("predicted 与 reference 长度不一致")
    n = len(predicted)
    if n == 0:
        return 0.0
    return round(sum(1 for a, b in zip(predicted, reference) if a == b) / n, 6)


def _bin_index(c: float, n_bins: int) -> int:
    """等宽分档：[i/n, (i+1)/n)；最后一档含 1.0。c 越界则夹到 [0,1]。"""
    c = min(1.0, max(0.0, float(c)))
    i = int(c * n_bins)
    return n_bins - 1 if i >= n_bins else i


def reliability_diagram(confidences, correct, n_bins: int = 10) -> list:
    """每档 {lo,hi,count,avg_conf,acc}；空档 avg_conf/acc=None。确定性输出。"""
    bins = [{"count": 0, "sum_conf": 0.0, "sum_correct": 0} for _ in range(n_bins)]
    for c, k in zip(confidences, correct):
        b = bins[_bin_index(c, n_bins)]
        b["count"] += 1
        b["sum_conf"] += float(c)
        b["sum_correct"] += 1 if k else 0
    out = []
    for i, b in enumerate(bins):
        cnt = b["count"]
        out.append({
            "lo": round(i / n_bins, 6),
            "hi": round((i + 1) / n_bins, 6),
            "count": cnt,
            "avg_conf": round(b["sum_conf"] / cnt, 6) if cnt else None,
            "acc": round(b["sum_correct"] / cnt, 6) if cnt else None,
        })
    return out


def expected_calibration_error(confidences, correct, n_bins: int = 10) -> float:
    """ECE（期望校准误差）。N=0 → 0.0（分母 0 不默认 1）。"""
    n = len(confidences)
    if n == 0:
        return 0.0
    ece = 0.0
    for b in reliability_diagram(confidences, correct, n_bins):
        if b["count"]:
            ece += (b["count"] / n) * abs(b["acc"] - b["avg_conf"])
    return round(ece, 6)


def tiered_hit_rate(confidences, correct, n_bins: int = 10) -> dict:
    """分层命中率 + 单调性 + top/bottom 档准确率。"""
    tiers = [b for b in reliability_diagram(confidences, correct, n_bins) if b["count"]]
    accs = [b["acc"] for b in tiers]
    monotonic = all(accs[i] <= accs[i + 1] + 1e-9 for i in range(len(accs) - 1))
    return {
        "n_nonempty_tiers": len(tiers),
        "monotonic": bool(monotonic),
        "bottom_acc": accs[0] if accs else None,
        "top_acc": accs[-1] if accs else None,
        "top_minus_bottom": round(accs[-1] - accs[0], 6) if accs else None,
        "tiers": tiers,
    }


def _auc(pos, neg):
    """P(分差_正 > 分差_负) + 0.5·P(相等)；无正或无负 → None。确定性（成对比较）。"""
    if not pos or not neg:
        return None
    wins = ties = 0
    for a in pos:
        for b in neg:
            if a > b:
                wins += 1
            elif a == b:
                ties += 1
    return round((wins + 0.5 * ties) / (len(pos) * len(neg)), 6)


def _point_biserial(gaps, correct) -> float | None:
    """分差(连续) 与 正确(二值) 的点二列相关。全同或退化 → None。"""
    n = len(gaps)
    if n == 0:
        return None
    pos = [g for g, k in zip(gaps, correct) if k]
    neg = [g for g, k in zip(gaps, correct) if not k]
    if not pos or not neg:
        return None
    p = len(pos) / n
    q = 1.0 - p
    mean_all = sum(gaps) / n
    var = sum((g - mean_all) ** 2 for g in gaps) / n
    sd = var ** 0.5
    if sd == 0.0:
        return None
    r = ((sum(pos) / len(pos)) - (sum(neg) / len(neg))) / sd * (p * q) ** 0.5
    return round(r, 6)


def score_gap_analysis(gaps, correct, n_grid: int = 21) -> dict:
    """top-2 候选分差 vs 正确性 —— 回答"分差阈值能否当回退判据"。

    返回：AUC、点二列相关、以及**阈值扫描的最优阈值**（准确率最大；同分取更小阈值）。
    判别式若无真置信度，用它作为"是否存在可回退信号"的**有依据替代**。
    """
    n = len(gaps)
    if n == 0:
        return {"n": 0, "auc": None, "point_biserial": None,
                "best_threshold": None, "best_accuracy": None}
    total = len(correct)
    uniq = sorted({round(float(g), 9) for g in gaps})
    best = None
    for t in uniq:
        tp = fp = fn = 0
        for g, k in zip(gaps, correct):
            pred = float(g) >= t
            if pred and k:
                tp += 1
            elif pred and not k:
                fp += 1
            elif not pred and k:
                fn += 1
        acc = (tp + (total - tp - fp - fn)) / total
        cand = {"threshold": t, "accuracy": round(acc, 6),
                "precision": round(tp / (tp + fp), 6) if (tp + fp) else 0.0,
                "recall": round(tp / (tp + fn), 6) if (tp + fn) else 0.0}
        if best is None or cand["accuracy"] > best["accuracy"] or (
                cand["accuracy"] == best["accuracy"] and t < best["threshold"]):
            best = cand
    return {
        "n": n,
        "auc": _auc([float(g) for g, k in zip(gaps, correct) if k],
                    [float(g) for g, k in zip(gaps, correct) if not k]),
        "point_biserial": _point_biserial([float(g) for g in gaps], list(correct)),
        "best_threshold": best["threshold"] if best else None,
        "best_accuracy": best["accuracy"] if best else None,
        "best_precision": best["precision"] if best else None,
        "best_recall": best["recall"] if best else None,
    }


def calibration_report(confidences, correct, score_gaps=None, n_bins: int = 10,
                       ece_threshold: float = 0.05, monotone_min_gap: float = 0.1) -> dict:
    """汇总 + 门禁裁决。长度不一致 → 报错（口径不猜）。"""
    confidences = list(confidences)
    correct = [bool(k) for k in correct]
    if len(confidences) != len(correct):
        raise ValueError("confidences 与 correct 长度不一致")
    n = len(confidences)
    ece = expected_calibration_error(confidences, correct, n_bins)
    tier = tiered_hit_rate(confidences, correct, n_bins)
    n_pos = sum(1 for k in correct if k)
    n_neg = n - n_pos
    # 证据充分性：**≥2 个非空档 且 正负例都在** —— 否则 ECE/单调都无意义
    #   （单档、全对 ⇒ ECE 天然≈0，是"证据不足"而非"校准好"；这正是 T212 的坑）
    evidence_ok = bool(tier["n_nonempty_tiers"] >= 2 and n_pos > 0 and n_neg > 0)
    ece_branch = bool(ece <= ece_threshold)
    tier_branch = bool(tier["monotonic"] and tier["n_nonempty_tiers"] >= 2
                       and tier["top_minus_bottom"] is not None
                       and tier["top_minus_bottom"] >= monotone_min_gap)
    allowed = evidence_ok and (ece_branch or tier_branch)
    if allowed:
        rule = "confidence"
    elif not evidence_ok:
        rule = "rule:insufficient_evidence（单档/缺正负例 → 置信度回退禁用）"
    else:
        rule = "rule:score_gap_threshold（置信度不可信 → 退回规则判定）"
    rep = {
        "n": n,
        "n_bins": n_bins,
        "n_pos": n_pos,
        "n_neg": n_neg,
        "accuracy": round(n_pos / n, 6) if n else 0.0,
        "ece": ece,
        "ece_threshold": ece_threshold,
        "reliability": reliability_diagram(confidences, correct, n_bins),
        "tiered": tier,
        "evidence_sufficient": evidence_ok,
        "confidence_fallback_allowed": allowed,
        "fallback_rule": rule,
    }
    if score_gaps is not None:
        sg = list(score_gaps)
        if len(sg) != n:
            raise ValueError("score_gaps 与 confidences 长度不一致")
        rep["score_gap"] = score_gap_analysis(sg, correct)
    return rep


def _load_pairs(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="obs.calibration",
                                 description="校准度量（唯一口径，纯函数）")
    ap.add_argument("--input", required=True,
                    help="JSON：{confidences:[..], correct:[true/false..], gaps:[..]（可选）}")
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--ece-threshold", type=float, default=0.05)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    d = _load_pairs(a.input)
    rep = calibration_report(d.get("confidences", []), d.get("correct", []),
                             score_gaps=d.get("gaps"), n_bins=a.bins,
                             ece_threshold=a.ece_threshold)
    txt = json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out:
        Path(a.out).write_text(txt + "\n", encoding="utf-8")
        print(f"written: {a.out}")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
