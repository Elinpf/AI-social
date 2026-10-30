#!/usr/bin/env python3
"""D10 C-A 汇总器：把 `address_drift` 的称呼口径与**官方口径**（`dialogue_metrics.py` 的
`F-1` / `L-7` / `L-12b`）并到一张表里，输出 `summary.json` + `summary.md`。

为什么必须有这一层：
  * 陷阱2（`R4:89`）要求"称呼变化"必须并列 `L-7` 8-gram 重复率，防"其实只是模板轮换"；
  * 陷阱1/F-1 假性相关要求并列 `F-1` 非功能性闲聊占比；
  * 官方已有 `L-12b_peer_address_rate`（名字以称呼语形式出现）⇒ 本尺子的 `addr_coverage`
    必须与它并列，差异要写出来（口径不同不得假装一致）。

只用官方入口：`dialogue_metrics.py` 以 **subprocess 调 CLI**（不复制它的公式，避免自造口径）。

用法（仓库根）：
  python3 tools/metrics/d10_address_summary.py \
      --run d9m-off=OFF=v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl \
      --run d9m-on=ON=v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl \
      --out-dir v2/evidence/d10_address_drift
退出码：0 正常；2 输入不可用；3 汇总自检失败。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "metrics"))
import address_drift as AD  # noqa: E402


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2 精确检验（双侧，取所有概率 ≤ 观测概率的表之和）。纯 stdlib，可复算。"""
    n1, n2 = a + b, c + d
    total = n1 + n2
    denom = math.comb(total, a + c)

    def pmf(x):
        return (math.comb(n1, x) * math.comb(n2, a + c - x)) / denom

    p_obs = pmf(a)
    lo = max(0, a + c - n2)
    hi = min(n1, a + c)
    tol = 1e-12
    return sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs + tol)


def official(log: str) -> dict:
    """调官方 dialogue_metrics.py CLI，取 F-1 / L-7 / L-12a / L-12b。"""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "dm.json")
        cmd = [sys.executable, os.path.join(ROOT, "tools", "d5", "dialogue_metrics.py"),
               "--log", log, "--out-json", out]
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"dialogue_metrics rc={r.returncode}: {r.stderr[-800:]}")
        d = json.load(open(out, encoding="utf-8"))
    lw = d.get("L_wording") or {}
    return {
        "F-1_nonfunctional_chatter_rate": (d.get("F-1_chatter") or {}).get("nonfunctional_chatter_rate"),
        "F-1_n_messages_denom": (d.get("F-1_chatter") or {}).get("n_messages_denom"),
        "L-7_dup_ngram8_rate": lw.get("L-7_dup_ngram8_rate"),
        "L-12a_peer_mention_rate": lw.get("L-12_peer_mention_rate"),
        "L-12b_peer_address_rate": lw.get("L-12b_peer_address_rate"),
        "official_cmd": " ".join(cmd),
        "official_rc": 0,
    }


def pct(x):
    return None if x is None else round(x * 100, 4)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True,
                    help="key=ARM=logpath（可多次）")
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "v2", "evidence", "d10_address_drift"))
    a = ap.parse_args(argv)

    runs = []
    for spec in a.run:
        key, arm, log = spec.split("=", 2)
        logp = log if os.path.isabs(log) else os.path.join(ROOT, log)
        if not os.path.isfile(logp):
            print(f"[FAIL] 日志不可用: {logp}", file=sys.stderr)
            return 2
        runs.append((key, arm, logp))

    rows = []
    for key, arm, logp in runs:
        res = AD.compute(logp, arm=arm)
        off = official(logp)
        m = res["metrics"]
        rows.append({
            "key": key, "arm": arm, "log": logp, "log_sha256": res["input_log_sha256"],
            "addr_drift": res, "official": off,
            "flat": {
                "n_messages": res["n_messages"],
                "addr_coverage_pct": pct(res["addr_coverage"]),
                "addr_any_mention_pct": pct(res["addr_any_mention_rate"]),
                "addr_vocab_pairs": m["addr_vocab_per_pair"]["denom_pairs"],
                "addr_vocab_mean": m["addr_vocab_per_pair"]["mean"],
                "addr_switch_n": m["addr_switch_rate"]["n_switch"],
                "addr_switch_denom_scored": m["addr_switch_rate"]["denom_scored_pairs"],
                "addr_switch_rate_scored_pct": pct(m["addr_switch_rate"]["rate_scored"]),
                "addr_switch_rate_all_pct": pct(m["addr_switch_rate"]["rate_all"]),
                "addr_switch_denom_all": m["addr_switch_rate"]["denom_all_pairs"],
                "addr_stage_pairs": m["addr_stage_ordinal"]["denom_directed_pairs"],
                "addr_stage_up": m["addr_stage_ordinal"]["n_up"],
                "addr_stage_flat": m["addr_stage_ordinal"]["n_flat"],
                "addr_stage_down": m["addr_stage_ordinal"]["n_down"],
                "addr_stage_mean_delta": m["addr_stage_ordinal"]["mean_delta"],
                "addr_named_judgeable": res["addr_misaddress"]["n_named_addr_judgeable"],
                "addr_target_ok": res["addr_misaddress"]["n_target_ok"],
                "addr_selfname_n": res["addr_misaddress"]["n_self_name"],
                "addr_other_named_n": res["addr_misaddress"]["n_other_named"],
                "addr_error_n": res["addr_misaddress"]["n_addr_err"],
                "addr_error_rate_pct": pct(res["addr_misaddress"]["addr_error_rate"]),
                "addr_misaddress_rate_pct": pct(res["addr_misaddress"]["misaddress_rate"]),
                "addr_selfname_rate_pct": pct(res["addr_misaddress"]["selfname_rate"]),
                "F1_pct": pct(off["F-1_nonfunctional_chatter_rate"]),
                "L7_pct": pct(off["L-7_dup_ngram8_rate"]),
                "L12b_pct": pct(off["L-12b_peer_address_rate"]),
                "L12a_pct": pct(off["L-12a_peer_mention_rate"]),
            },
        })

    # 与基线对比（同 code_sha 的两臂；仅描述，无因果）
    pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            A, B = rows[i], rows[j]
            if A["arm"] == B["arm"]:
                continue
            a1, n1 = A["flat"]["addr_switch_n"], A["flat"]["addr_switch_denom_scored"]
            a2, n2 = B["flat"]["addr_switch_n"], B["flat"]["addr_switch_denom_scored"]
            # 2x2: [switch_A, no_switch_A] / [switch_B, no_switch_B]
            p = fisher_exact_two_sided(a1, n1 - a1, a2, n2 - a2) if n1 and n2 else None
            pairs.append({
                "baseline": A["key"], "treatment": B["key"],
                "switch_baseline": f"{a1}/{n1}", "switch_treatment": f"{a2}/{n2}",
                "delta_pp": (round((a2 / n2 - a1 / n1) * 100, 4) if n1 and n2 else None),
                "fisher_exact_two_sided_p": (round(p, 6) if p is not None else None),
                "caveat": "两臂差异**不是**称呼干预（各自只差旁白轮换 / 句式起首臂）⇒ 只作描述，不可归因",
            })

    summary = {
        "tool": "tools/metrics/d10_address_summary.py",
        "tool_sha256": AD.sha256_file(os.path.abspath(__file__)),
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "lexicon_sha256": AD.sha256_file(os.path.join(ROOT, "v2", "refs", "address-ordinal.yaml")),
        "runs": rows,
        "comparisons": pairs,
    }
    os.makedirs(a.out_dir, exist_ok=True)
    if not os.path.isabs(a.out_dir):
        a.out_dir = os.path.join(ROOT, a.out_dir)
    jp = os.path.join(a.out_dir, "summary.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)

    hdr = ["key", "arm", "n_msg", "cov%", "mention%", "vocabN", "vocabMean",
           "sw_n", "sw/den_scored", "sw%scored", "sw%all", "stageN", "up", "flat", "down",
           "err_n/den", "err%", "F1%", "L7%", "L12b%"]
    lines = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for r in rows:
        f = r["flat"]
        lines.append("| " + " | ".join(str(x) for x in [
            r["key"], r["arm"], f["n_messages"], f["addr_coverage_pct"], f["addr_any_mention_pct"],
            f["addr_vocab_pairs"], f["addr_vocab_mean"],
            f["addr_switch_n"], f"{f['addr_switch_n']}/{f['addr_switch_denom_scored']}",
            f["addr_switch_rate_scored_pct"], f["addr_switch_rate_all_pct"],
            f["addr_stage_pairs"], f["addr_stage_up"], f["addr_stage_flat"], f["addr_stage_down"],
            f"{f['addr_selfname_n']}+{f['addr_other_named_n']}/{f['addr_named_judgeable']}", f["addr_error_rate_pct"],
            f["F1_pct"], f["L7_pct"], f["L12b_pct"],
        ]) + " |")
    md = "\n".join(lines) + "\n"
    mp = os.path.join(a.out_dir, "summary.md")
    with open(mp, "w", encoding="utf-8") as f:
        f.write("# D10 C-A 汇总表（address_drift × 官方 F-1/L-7/L-12b）\n\n")
        f.write(f"- computed_at: {summary['computed_at']}\n")
        f.write(f"- lexicon_sha256: `{summary['lexicon_sha256']}`\n")
        f.write(f"- summary_tool_sha256: `{summary['tool_sha256']}`\n\n")
        f.write(md)
        i = 0
        for r in rows:
            i += 1
            f.write(f"\n## {r['key']} (arm={r['arm']})\n")
            f.write(f"- log: `{r['log']}`\n- log_sha256: `{r['log_sha256']}`\n")
            f.write(f"- official_cmd: `{r['official']['official_cmd']}`\n")
        if pairs:
            f.write("\n## 与基线/另一臂的对比（仅描述，不可归因）\n\n")
            f.write("| baseline | treatment | switch(base) | switch(treat) | Δpp | Fisher 双侧 p | 说明 |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for p in pairs:
                f.write(f"| {p['baseline']} | {p['treatment']} | {p['switch_baseline']} | {p['switch_treatment']} | "
                        f"{p['delta_pp']} | {p['fisher_exact_two_sided_p']} | {p['caveat']} |\n")
    print(md)
    print(f"[summary] wrote {jp} and {mp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
