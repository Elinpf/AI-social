"""F-6 两臂对比指标（只读 run.jsonl + 官方指标 JSON；跨臂同口径可复算）。

命名纪律（见 round1/metrics-definition-frozen.md）：
  - **F-6 = 仓库既有定义**，结论只引用 `tools/d5/dialogue_metrics.py` 的输出（本脚本不重写实现；
    本地复现值只作「交叉核对」列，不进结论）。
  - **M-1 = 本轮新指标**「跨天记忆引用率」，与 F-6 不是一回事，禁止横向比数值大小。

指标：
  M-1（主口径，机会分母）  分子=正文 6 字 n-gram 与「同线程更早一天消息」有交集；
                            分母=day>=1 且同线程存在更早一天消息的消息数
  M-1b（副列，全分母）      同一分子 / 全部 day>=1 消息数
  M-0（对照，同日基线）      分子=与「同线程同一天更早消息」有 6-gram 交集；
                            分母=day>=1 且同线程存在同日更早消息的消息数
                            期望接近 0；若与 M-1 同量级 ⇒ M-1 抓到的是模板而非跨天记忆
  token                     由 obs llm-cost 输出提供（本脚本不读 run）

用法：
  python3 f6_metrics.py --run OFF=<run.jsonl> --run ON=<run.jsonl> \
      --official OFF=<official.json> --official ON=<official.json> \
      --cost OFF=<llmcost.json> --cost ON=<llmcost.json> \
      --out result.json --markdown result.md
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import defaultdict

MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")
NGRAM = 6
TIMEREF = ["昨天", "前天", "上次", "上回", "那天", "前几天", "昨儿", "昨晚上", "以前", "早就", "那次"]


def _read(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _ngrams(text, n=NGRAM):
    t = re.sub(r"[\s，。！？、；：「」（）,.!?;:()\"'“”‘’…—-]", "", text or "")
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def _msgs(recs):
    out = []
    for r in recs:
        if r.get("type") not in MSG_TYPES:
            continue
        p = r.get("payload") or {}
        out.append({
            "seq": r.get("seq"), "round": r.get("round"),
            "day": p.get("day"), "slot": p.get("slot"), "type": r["type"],
            "from": p.get("from"), "to": p.get("to"), "group_id": p.get("group_id"),
            "body": (p.get("body") or "").strip(),
            "thread_id": p.get("thread_id"),
            "memory_refs": (p.get("ctx") or {}).get("memory_refs") or [],
        })
    return out


def _thread_key(m):
    if m["thread_id"]:
        return "T:" + str(m["thread_id"])
    if m["type"] == "MSG_DM":
        return "D:" + "|".join(sorted([str(m["from"]), str(m["to"])]))
    if m["type"] == "MSG_GROUP":
        return "G:" + str(m["group_id"])
    return "P:" + str(m["from"])


def wilson(k, n, z=1.959963984540054):
    """二项比例 Wilson 95% 区间（事前定的噪声口径，不得事后改）。"""
    if not n:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - h) / d, 4), round((c + h) / d, 4))


def compute(name, run_path):
    recs = _read(run_path)
    msgs = _msgs(recs)
    n_msg = len(msgs)
    days = sorted({m["day"] for m in msgs if m["day"] is not None})
    threads = defaultdict(list)
    for m in msgs:
        threads[_thread_key(m)].append(m)

    cross_hit = cross_den = same_hit = same_den = 0
    day1_total = 0
    for _key, th in threads.items():
        for i, m in enumerate(th):
            if m["day"] is None or m["day"] < 1:
                continue
            day1_total += 1
            g = _ngrams(m["body"])
            earlier_cross = [x for x in th[:i] if x["day"] is not None and x["day"] < m["day"]]
            earlier_same = [x for x in th[:i] if x["day"] == m["day"]]
            if earlier_cross:
                cross_den += 1
                if g and any(g & _ngrams(x["body"]) for x in earlier_cross):
                    cross_hit += 1
            if earlier_same:
                same_den += 1
                if g and any(g & _ngrams(x["body"]) for x in earlier_same):
                    same_hit += 1

    tref = sum(1 for m in msgs if any(w in m["body"] for w in TIMEREF))
    bodies = [m["body"] for m in msgs if m["body"]]
    exact_dup = len(bodies) - len(set(bodies))
    seen8, dup8 = set(), 0
    for b in bodies:
        g = _ngrams(b, 8)
        if g:
            if g & seen8:
                dup8 += 1
            seen8 |= g
    lens = sorted(len(b) for b in bodies) or [0]

    return {
        "run": name,
        "run_path": os.path.abspath(run_path),
        "records": len(recs),
        "messages": n_msg,
        "days": days,
        "threads": len(threads),
        "body_len": {"p50": lens[len(lens) // 2], "max": lens[-1],
                     "mean": round(sum(lens) / len(lens), 2)},
        "M-1_opportunity": {"hits": cross_hit, "den": cross_den,
                            "rate": round(cross_hit / cross_den, 4) if cross_den else None,
                            "wilson95": wilson(cross_hit, cross_den)},
        "M-1b_allday": {"hits": cross_hit, "den": day1_total,
                        "rate": round(cross_hit / day1_total, 4) if day1_total else None,
                        "wilson95": wilson(cross_hit, day1_total)},
        "M-0_sameday_control": {"hits": same_hit, "den": same_den,
                                "rate": round(same_hit / same_den, 4) if same_den else None,
                                "wilson95": wilson(same_hit, same_den)},
        "crosscheck_timeref": {"hits": tref, "den": n_msg,
                               "rate": round(tref / n_msg, 4) if n_msg else None,
                               "note": "本地复现，仅与官方 F-6 交叉核对，不作结论",
                               "wilson95": wilson(tref, n_msg)},
        "crosscheck_L6": {"hits": exact_dup, "den": len(bodies),
                          "rate": round(exact_dup / len(bodies), 4) if bodies else None},
        "crosscheck_L7": {"hits": dup8, "den": len(bodies),
                          "rate": round(dup8 / len(bodies), 4) if bodies else None},
        "ctx_memory_refs_msgs": sum(1 for m in msgs if m["memory_refs"]),
        "ctx_memory_refs_rate": (round(sum(1 for m in msgs if m["memory_refs"]) / n_msg, 4)
                                 if n_msg else None),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="name=path")
    ap.add_argument("--official", action="append", default=[], help="name=official_metrics.json")
    ap.add_argument("--cost", action="append", default=[], help="name=llmcost.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--markdown", default=None)
    a = ap.parse_args()

    official = dict(x.split("=", 1) for x in a.official)
    cost = dict(x.split("=", 1) for x in a.cost)

    results = []
    for spec in a.run:
        name, path = spec.split("=", 1)
        r = compute(name, path)
        o = json.load(open(official[name], encoding="utf-8")) if name in official else {}
        lw = o.get("L_wording") or {}
        r["official"] = {
            "path": os.path.abspath(official[name]) if name in official else None,
            "F-6_rate": (o.get("F-6_crossday_memory") or {}).get("timeref_rate"),
            "L-5": lw.get("L-5_template_hit_rate"),
            "L-6": lw.get("L-6_dup_exact_rate"),
            "L-7": lw.get("L-7_dup_ngram8_rate"),
            "L-8": lw.get("L-8_agent_id_leak_rate"),
        }
        if name in cost:
            c = json.load(open(cost[name], encoding="utf-8"))
            t = (c.get("engine_log") or {}).get("total") or {}
            r["cost"] = {"path": os.path.abspath(cost[name]),
                         "calls": t.get("calls"), "tokens_in": t.get("tokens_in"),
                         "tokens_out": t.get("tokens_out"),
                         "cached": t.get("cached"), "degraded": t.get("degraded"),
                         "provider_guard_ok": (c.get("provider_guard") or {}).get("ok"),
                         "by_provider": (c.get("provider_guard") or {}).get("by_provider")}
        results.append(r)

    deltas = {}
    if len(results) == 2:
        A, B = results
        for m in ("M-1_opportunity", "M-1b_allday", "M-0_sameday_control", "crosscheck_timeref"):
            ra, rb = A[m]["rate"], B[m]["rate"]
            if ra is None or rb is None:
                deltas[m] = {"delta_pp": None, "ci_overlap": None, "significant": None}
                continue
            d = round((rb - ra) * 100, 2)
            ia, ib = A[m]["wilson95"], B[m]["wilson95"]
            overlap = (ia[0] is not None and ib[0] is not None and ia[0] <= ib[1] and ib[0] <= ia[1])
            deltas[m] = {"delta_pp": d, "ci_overlap": overlap,
                         "significant": (abs(d) >= 1.0 and not overlap),
                         "rule": "|Δ|>=1pp 且 Wilson95 区间不重叠 ⇒ 判显著（事前定）"}
        for k in ("F-6_rate", "L-6", "L-7", "L-8", "L-5"):
            va, vb = A["official"].get(k), B["official"].get(k)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                deltas[k] = {"delta_pp": round((vb - va) * 100, 2),
                             "note": "官方标量（脚本不输出计数，故本表不给 CI）"}
        ca, cb = A.get("cost") or {}, B.get("cost") or {}
        if ca.get("tokens_in") and cb.get("tokens_in"):
            deltas["tokens_in"] = {
                "OFF": ca["tokens_in"], "ON": cb["tokens_in"],
                "delta": cb["tokens_in"] - ca["tokens_in"],
                "delta_pct": round((cb["tokens_in"] - ca["tokens_in"]) / ca["tokens_in"] * 100, 2),
                "rule": "计数型：报绝对差与相对差；|相对差|<5% 视为无实质差别（事前定，不与率类混用）"}

    payload = {"arms": results, "deltas": deltas}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    md = ["| 指标 | " + " | ".join(r["run"] for r in results) + " |", "|---|" + "---|" * len(results)]
    def row(label, fn):
        md.append("| " + label + " | " + " | ".join(str(fn(r)) for r in results) + " |")
    def cell(r, key):
        d = r[key]
        ci = d.get("wilson95") or (None, None)
        return f"{d['rate']} ({d['hits']}/{d['den']}) CI[{ci[0]},{ci[1]}]"
    row("消息数", lambda r: r["messages"])
    row("天数", lambda r: f"{len(r['days'])}（{r['days'][0]}–{r['days'][-1]}）" if r["days"] else "-")
    row("线程数", lambda r: r["threads"])
    row("正文长度 p50/max", lambda r: f"{r['body_len']['p50']}/{r['body_len']['max']}")
    row("**F-6 跨天记忆引用率（官方）**", lambda r: r["official"]["F-6_rate"])
    row("（交叉核对）时间回指率·本地", lambda r: cell(r, "crosscheck_timeref"))
    row("**M-1 记忆引用率（主口径·机会分母）**", lambda r: cell(r, "M-1_opportunity"))
    row("M-1b（副列·全部 day≥1 分母）", lambda r: cell(r, "M-1b_allday"))
    row("M-0 同日对照（期望≈0）", lambda r: cell(r, "M-0_sameday_control"))
    row("L-5 模板套话率（官方）", lambda r: r["official"]["L-5"])
    row("L-6 精确重复率（官方）", lambda r: r["official"]["L-6"])
    row("L-7 8-gram 重复率（官方）", lambda r: r["official"]["L-7"])
    row("L-8 裸 ID 泄漏率（官方）", lambda r: r["official"]["L-8"])
    row("带 memory_refs 的消息", lambda r: f"{r['ctx_memory_refs_msgs']} ({r['ctx_memory_refs_rate']})")
    row("tokens_in / calls", lambda r: f"{(r.get('cost') or {}).get('tokens_in')} / {(r.get('cost') or {}).get('calls')}")
    if deltas:
        md += ["", "### 两臂差值（Δ = ON − OFF；率类单位 pp，token 为计数）", "",
               "| 指标 | Δ | CI 重叠 | 判定 |", "|---|---|---|---|"]
        for k, v in deltas.items():
            md.append(f"| {k} | {v.get('delta_pp', v.get('delta'))} | {v.get('ci_overlap')} | "
                      f"{v.get('significant', '-')} |")
    table = "\n".join(md)
    print(table)
    if a.markdown:
        with open(a.markdown, "w", encoding="utf-8") as f:
            f.write(table + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
