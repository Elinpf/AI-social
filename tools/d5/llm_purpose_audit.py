#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM_CALL 目的层审计：找出「静默空输出」与「实际没在跑」的 purpose。

背景（2026-10-20 实测）：
- `code/config/llm.json` 的 `true_purposes = ["judge","narrate","describe"]` 会让这些 purpose 走 thinking=true；
  若 max_tokens 偏低，服务端可能把预算全用在 reasoning 上、`content` 为空而**日志看起来一切正常**。
- 另有一个更隐蔽的假绿：某 purpose 只有 `cached=true` 的记录在跑，真调用全 0 —— 说明它其实没在跑。

判据（写死）：
1. **可疑空输出**：`tokens_out == 0` **且** `cached == false`。
2. **未真跑**：该 purpose 的非缓存调用数（`cached==false`）== 0，但存在缓存记录。
3. **截断疑似**：`tokens_out` 恰好等于该 purpose 内最大值的记录占比 ≥ 80% 且最大值 ≥ 300（粗代理，需人工抽样确认）。
4. **未出现**：purpose 在日志中 0 条（结论写「未出现，无实例」，同样是证据）。

输出：规范 JSON + Markdown；按 purpose 分别给 `cached=true/false` 两个子集的 tokens_in/out 分布。

用法：
    python3 tools/d5/llm_purpose_audit.py --log <RUN>/run.jsonl \
        --out-json v2/evidence/d5_llm_purpose_audit.json --out-md v2/evidence/d5_llm_purpose_audit.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

SCHEMA = "d5-llm-purpose-audit/1.0"
EXPECTED_PURPOSES = ["dialogue", "judge", "narrate", "describe", "importance",
                     "reflect", "plan", "negotiation"]


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return "sha256:" + h.hexdigest()


def pct(vals: List[float], q: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return float(s[0])
    pos = (len(s) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (pos - lo), 3)


def dist(vals: List[int]) -> Dict[str, Any]:
    if not vals:
        return {"n": 0}
    return {"n": len(vals), "min": min(vals), "p10": pct(vals, .1), "p50": pct(vals, .5),
            "p90": pct(vals, .9), "max": max(vals), "mean": round(sum(vals) / len(vals), 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="LLM_CALL 目的层审计")
    ap.add_argument("--log", required=True)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args(argv)

    rows: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "calls": 0, "cached_true": 0, "cached_false": 0,
        "out_cached": [], "out_live": [], "in_cached": [], "in_live": [],
        "thinking": Counter(), "models": Counter(), "providers": Counter(),
        "empty_live": 0, "empty_cached": 0,
    })
    bad_lines = 0
    n_llm = 0
    with open(args.log, encoding="utf-8") as f:
        for ln in f:
            if '"LLM_CALL"' not in ln:
                continue
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except Exception:
                bad_lines += 1
                continue
            if d.get("type") != "LLM_CALL":
                continue
            n_llm += 1
            p = d.get("payload") or {}
            pu = str(p.get("purpose") or "<none>")
            r = rows[pu]
            r["calls"] += 1
            out = int(p.get("tokens_out") or 0)
            tin = int(p.get("tokens_in") or 0)
            cached = bool(p.get("cached"))
            r["cached_true" if cached else "cached_false"] += 1
            if cached:
                r["out_cached"].append(out)
                r["in_cached"].append(tin)
                if out == 0:
                    r["empty_cached"] += 1
            else:
                r["out_live"].append(out)
                r["in_live"].append(tin)
                if out == 0:
                    r["empty_live"] += 1
            r["thinking"][str(p.get("thinking"))] += 1
            r["models"][str(p.get("model"))] += 1
            r["providers"][str(p.get("provider"))] += 1

    log_sha = sha256_file(args.log)
    res: Dict[str, Any] = {
        "schema_version": SCHEMA,
        "inputs": {"log": os.path.abspath(args.log), "log_sha256": log_sha, "log_sha8": log_sha[7:15]},
        "rules": {
            "suspicious_empty": "tokens_out==0 且 cached==false",
            "not_really_running": "cached==false 的调用数 == 0 但存在 cached==true",
            "truncation_proxy": "tokens_out 等于组内最大值(>=300)的记录占比 >= 80% ⇒ 疑似截断，需人工抽样",
            "absent_purpose": "0 条记录 ⇒ 结论写「未出现，无实例」（同样是证据）",
        },
        "n_llm_calls": n_llm,
        "bad_lines": bad_lines,
        "purposes": {},
        "findings": [],
    }
    for pu in sorted(set(list(rows) + EXPECTED_PURPOSES)):
        r = rows.get(pu)
        if r is None:
            res["purposes"][pu] = {"calls": 0,
                                   "status": f"未出现，无实例（完整日志 {log_sha[7:15]} 中 0 条记录）"}
            res["findings"].append({"purpose": pu, "issue": "absent",
                                    "detail": {"log_sha8": log_sha[7:15], "records": 0,
                                               "statement": f"在该日志（sha8={log_sha[7:15]}）中 0 条记录"}})
            continue
        live = r["out_live"]
        entry: Dict[str, Any] = {
            "calls": r["calls"], "cached_true": r["cached_true"], "cached_false": r["cached_false"],
            "tokens_out_cached": dist(r["out_cached"]),
            "tokens_out_live": dist(live),
            "tokens_in_cached": dist(r["in_cached"]),
            "tokens_in_live": dist(r["in_live"]),
            "thinking": dict(r["thinking"]), "models": dict(r["models"]),
            "providers": dict(r["providers"]),
            "suspicious_empty_live": r["empty_live"],
            "suspicious_empty_rate_live": (round(r["empty_live"] / len(live), 6) if live else None),
            "empty_cached": r["empty_cached"],
        }
        status = []
        if r["cached_false"] == 0:
            status.append("未真跑（只有缓存记录）")
            res["findings"].append({"purpose": pu, "issue": "not_really_running",
                                    "detail": f"cached_false=0, cached_true={r['cached_true']}"})
        if live and r["empty_live"] > 0:
            rate = r["empty_live"] / len(live)
            status.append(f"可疑空输出 {r['empty_live']}/{len(live)} = {rate:.1%}")
            res["findings"].append({"purpose": pu, "issue": "suspicious_empty",
                                    "detail": {"empty": r["empty_live"], "live": len(live), "rate": round(rate, 6)}})
        if live:
            mx = max(live)
            if mx >= 300 and sum(1 for v in live if v == mx) / len(live) >= 0.8:
                status.append(f"疑似截断（{sum(1 for v in live if v == mx)}/{len(live)} 等于 max={mx}）")
                res["findings"].append({"purpose": pu, "issue": "truncation_proxy",
                                        "detail": {"max": mx, "count_at_max": sum(1 for v in live if v == mx)}})
        entry["status"] = "；".join(status) if status else "正常"
        res["purposes"][pu] = entry

    # ---- 成本汇总：每个 purpose 的 tokens_out 总量与占比（judge 是大头）
    tot_out = sum(sum(r["out_cached"]) + sum(r["out_live"]) for r in rows.values())
    tot_in = sum(sum(r["in_cached"]) + sum(r["in_live"]) for r in rows.values())
    cost = {}
    for pu, r in sorted(rows.items(), key=lambda kv: -(sum(kv[1]["out_live"]) + sum(kv[1]["out_cached"]))):
        o = sum(r["out_live"]) + sum(r["out_cached"])
        i = sum(r["in_live"]) + sum(r["in_cached"])
        cost[pu] = {"tokens_in_total": i, "tokens_out_total": o,
                    "out_share": (round(o / tot_out, 6) if tot_out else None),
                    "in_share": (round(i / tot_in, 6) if tot_in else None),
                    "max_tokens_out_single": (max(r["out_live"] + r["out_cached"]) if (r["out_live"] or r["out_cached"]) else None)}
    res["cost_summary"] = {"tokens_in_total": tot_in, "tokens_out_total": tot_out, "by_purpose": cost}

    txt = json.dumps(res, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if args.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
        open(args.out_json, "w", encoding="utf-8").write(txt + "\n")

    lines = ["# LLM_CALL 目的层审计（静默空输出 / 未真跑 / 疑似截断）\n",
             f"- 日志：`{res['inputs']['log']}`",
             f"- run.jsonl sha256：`{res['inputs']['log_sha256']}`",
             f"- LLM_CALL 总数：{n_llm}（无法解析行 {bad_lines}）",
             "- 判据：可疑空输出 = `tokens_out==0 且 cached==false`；未真跑 = `cached==false` 调用数为 0 但有缓存；未出现 = 0 条记录（同样是证据）\n",
             "| purpose | 调用 | cached=T | cached=F | out(p50) 缓存 / 真调用 | out(max) 缓存 / 真调用 | 可疑空输出(真调用) | thinking | 状态 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for pu, e in res["purposes"].items():
        if e.get("calls", 0) == 0:
            lines.append(f"| `{pu}` | 0 | - | - | - | - | - | - | 未出现，无实例 |")
            continue
        oc, ol = e["tokens_out_cached"], e["tokens_out_live"]
        lines.append(f"| `{pu}` | {e['calls']} | {e['cached_true']} | {e['cached_false']} | "
                     f"{oc.get('p50')} / {ol.get('p50')} | {oc.get('max')} / {ol.get('max')} | "
                     f"{e['suspicious_empty_live']} | {e['thinking']} | {e['status']} |")
    if res.get("cost_summary"):
        cs = res["cost_summary"]
        lines += ["\n## 成本汇总（tokens_out 占比，降序）\n",
                  "| purpose | tokens_in | tokens_out | out 占比 | 单次最大 out |", "|---|---|---|---|---|"]
        for pu, c in cs["by_purpose"].items():
            lines.append(f"| `{pu}` | {c['tokens_in_total']} | {c['tokens_out_total']} | "
                         f"{c['out_share']} | {c['max_tokens_out_single']} |")
        lines.append(f"\n合计：in {cs['tokens_in_total']} / out {cs['tokens_out_total']} tokens。")
    if res["findings"]:
        lines += ["\n## 发现\n"]
        for f in res["findings"]:
            lines.append(f"- **{f['purpose']}** / `{f['issue']}`：{json.dumps(f['detail'], ensure_ascii=False)}")
    md = "\n".join(lines) + "\n"
    if args.out_md:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
        open(args.out_md, "w", encoding="utf-8").write(md)
    print(json.dumps({"n_llm_calls": n_llm, "findings": res["findings"],
                      "out_json": args.out_json, "out_md": args.out_md},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
