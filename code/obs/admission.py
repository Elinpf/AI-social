"""M2b 准入报告：从 T212 配对 JSONL 直算 **合法率 / token 比 / 延迟比**（口径唯一、只读、确定性）。

供 freeze-layer-dev 直接调用，避免各写一份口径。**本模块不做校准**（那在 `obs.calibration`）。
输入 = `m2b_pairs.jsonl` 每行的 dict（schema 由 freeze-layer-dev 定义）：
每个样本含 `A` / `B` 两侧，各带 `{"legal","tokens_in","tokens_out","reasoning_tokens","latency_s"}`。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

__all__ = ["load_pairs_jsonl", "legal_rate", "token_totals", "latency_p50",
           "admission_report", "flag_rate"]


def flag_rate(records, field):
    """布尔旗标占比（如 `escaped` / `fallback_used`）；该字段缺失不计入；无样本 → None。

    用于 `escape_rate` / `fallback_rate` 的**唯一口径**（M2b 验收，见 `v2/refs/m2b-acceptance.md`）。
    """
    xs = [r.get(field) for r in records if r.get(field) is not None]
    return round(sum(1 for x in xs if x) / len(xs), 6) if xs else None


def load_pairs_jsonl(path) -> list:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _side(rec, side) -> dict:
    return rec.get(side) or {}


def legal_rate(records, side: str):
    """该侧 `legal==True` 占比；无样本 → None。"""
    flags = [bool(_side(r, side).get("legal")) for r in records
             if _side(r, side).get("legal") is not None]
    return round(sum(1 for f in flags if f) / len(flags), 6) if flags else None


def token_totals(records, side: str) -> dict:
    """该侧 token 合计（in/out/total/reasoning）；缺失按 0，另报样本数。"""
    tin = tout = treason = 0
    n = 0
    for r in records:
        s = _side(r, side)
        if not s:
            continue
        n += 1
        tin += int(s.get("tokens_in", 0) or 0)
        tout += int(s.get("tokens_out", 0) or 0)
        treason += int(s.get("reasoning_tokens", 0) or 0)
    return {"n": n, "tokens_in": tin, "tokens_out": tout, "tokens_total": tin + tout,
            "reasoning_tokens": treason}


def latency_p50(records, side: str):
    """延迟中位数（排序后取中；偶数取中间两值均值）。确定性。无样本 → None。"""
    xs = sorted(float(_side(r, side).get("latency_s")) for r in records
                if _side(r, side).get("latency_s") is not None)
    if not xs:
        return None
    mid = len(xs) // 2
    med = xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2.0
    return round(med, 6)


def _ratio(b, a):
    return round(b / a, 6) if a else None


def admission_report(records) -> dict:
    """A vs B 汇总：合法率、token 比、延迟比（口径唯一）。"""
    ta, tb = token_totals(records, "A"), token_totals(records, "B")
    la, lb = latency_p50(records, "A"), latency_p50(records, "B")
    return {
        "n": len(records),
        "legal_rate": {"A": legal_rate(records, "A"), "B": legal_rate(records, "B")},
        "tokens": {"A": ta, "B": tb,
                   "ratio_B_over_A": _ratio(tb["tokens_total"], ta["tokens_total"])},
        "latency_p50_s": {"A": la, "B": lb, "ratio_B_over_A": _ratio(lb, la)},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="obs.admission",
                                 description="M2b 准入：合法率/token比/延迟比（只读）")
    ap.add_argument("--pairs", required=True, help="m2b_pairs.jsonl")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    rep = admission_report(load_pairs_jsonl(a.pairs))
    txt = json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out:
        Path(a.out).write_text(txt + "\n", encoding="utf-8")
        print(f"written: {a.out}")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
