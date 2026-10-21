#!/usr/bin/env python3
"""f3_audit_echo.py — F-3 情绪呼应：**独立复算 + 四档并列**（只读日志，不改 tools/）。

口径（Leader 2026-10-22 裁决，与 `tools/f3/f3_metrics.py` 命名一致）
--------------------------------------------------------------------
官方口径 `tools/d5/dialogue_metrics.py:681-696` 的分子有两条来源，都不干净：
  (a) 极性相同：负→负 也算呼应，不区分「接住对方」与「各自表达」（R4 §2「各自过日子」就是这种）；
  (b) 共情标记词：`EMPATHY_MARKERS` 里一半是顺口附和（我懂/确实/是啊/可不是），与 R13 在 F-4 剔除 `我懂` 同类噪声。

| 字段 | 名字 | 判据 | 已知偏向 |
|---|---|---|---|
| `loose` | loose（官方 d5） | 极性相同 ∪ 任意 EMPATHY_MARKERS | 两类假阳性全留；**唯一与 R1–R13 历史读数可比** |
| `loose_no_agree` | loose_no_agree（中间列） | 极性相同 ∪ 标记剔 `我懂` | 同上，仅少一个附和词 |
| `polarity_match` | polarity_match（原"A"） | **只认极性一致**（p_cur==p_prev≠0，标记不算） | 假阳性几乎全保留（负→负）；**禁止称「严格」** |
| `marker_based` | **marker_based（主指标，原"B"）** | **只认真回应标记**（剔 `我懂/确实/是啊/可不是`），不要求极性一致 | 依赖词表 ⇒ **系统性低估** |

并集口径（A∪B）**已按裁决弃用**：它只是把两种判据叠起来，不构成第三种标准。

分母口径：`all_messages`（线程内相邻对，上一句极性≠0）+ **`reply_path`（主口径，另加当前句 `payload.reply_to` 非空）**。
F-3 只在 `_send_reply` 生效，`_initiate` 路径即使 ON 也与 OFF 逐字节相同，把发起路径算进分母会系统性稀释命中率。

每档都给：去重值（按**当前句 body 原文**）、Wilson 95% CI、band（<30 count_only / <68 probe）、
**人工可核查样本全文**（读者不必相信词表，只需读两句话）。

机制侧审计：真实落点是 **`payload["ctx"]["echo"]`**（`v=f3/1`）；顶层 `dialogue_echo` 会被
`orchestration/integration.py::_thread_fields()` 的白名单静默吞掉。OFF 臂该键**应完全不存在**（不是空值）；
ON 臂缺失/恒空 ⇒ 判「开关未生效」，不是「机制无效」。

极性判定、分词、线程键复用仓库既有实现（`dialogue_metrics.read_run/extract_messages`、
`f4_anchor_recompute.mixed_key/load_emotion/sha8`）；`polarity()` 照 `dialogue_metrics.py:635-642` 逐行复制。

用法（仓库根）：
  python3 v2/evidence/f3_audit_echo.py \
      --off v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
      --on  v2/evidence/run_f3_on_n16r60_seed42/run.jsonl \
      --out-json v2/evidence/f3_audit_echo.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from collections import Counter, defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

#: 官方共情标记（照抄 dialogue_metrics.py:45）
EMPATHY_MARKERS = ("我懂", "我也", "别难过", "恭喜", "辛苦", "真惨", "太好了", "确实", "是啊", "可不是")
#: 严格档剔除的「顺口附和」
AGREEMENT_ONLY = ("我懂", "确实", "是啊", "可不是")

TIERS = ("loose", "loose_no_agree", "polarity_match", "marker_based")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


d5 = _load("dialogue_metrics_f3audit", os.path.join(REPO, "tools/d5/dialogue_metrics.py"))
f4a = _load("f4_anchor_recompute_f3audit", os.path.join(REPO, "tools/f4/f4_anchor_recompute.py"))


def wilson(k: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - r) / d, 6), round((c + r) / d, 6)]


def band(n: int) -> str:
    if n == 0:
        return "empty"
    if n < 30:
        return "count_only"
    if n < 68:
        return "probe"
    return "ok"


def analyze(label, rel_path, max_samples=8):
    path = rel_path if os.path.isabs(rel_path) else os.path.join(REPO, rel_path)
    emo = f4a.load_emotion(os.path.join(REPO, "tools/d5/emotion_lexicon.txt"))

    def polarity(body: str) -> int:  # 逐行复制 dialogue_metrics.py:635-642
        pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
        neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
        if pos > neg:
            return 1
        if neg > pos:
            return -1
        return 0

    recs, bad = d5.read_run(path)
    msgs = d5.extract_messages(recs)

    threads = defaultdict(list)
    for m in msgs:
        threads[f4a.mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                      m["seq"] if m["seq"] is not None else -1))

    marker_hits = Counter()
    rows = []
    for key in sorted(threads):
        th = threads[key]
        for i in range(1, len(th)):
            prev, cur = th[i - 1], th[i]
            p_prev = polarity(prev["body"])
            if p_prev == 0:
                continue
            p_cur = polarity(cur["body"])
            hit = [w for w in EMPATHY_MARKERS if w in cur["body"]]
            genuine = [w for w in hit if w not in AGREEMENT_ONLY]
            no_agree = [w for w in hit if w != "我懂"]
            for w in hit:
                marker_hits[w] += 1
            same = (p_cur == p_prev and p_cur != 0)
            rows.append({
                "thread": key, "prev_seq": prev["seq"], "cur_seq": cur["seq"],
                "round": cur.get("round"), "cur_is_reply": cur.get("reply_to") is not None,
                "p_prev": p_prev, "p_cur": p_cur, "same_polarity": same,
                "markers": hit, "genuine_markers": genuine, "no_agree_markers": no_agree,
                "prev_body": prev["body"], "cur_body": cur["body"],
                "tier_loose": bool(same or hit),
                "tier_loose_no_agree": bool(same or no_agree),
                "tier_polarity_match": bool(same),
                "tier_marker_based": bool(genuine),
            })

    n_msg_all = len(msgs)
    reply_rows = [r for r in rows if r["cur_is_reply"]]

    def tally(subset, tier):
        key = f"tier_{tier}"
        hits = [r for r in subset if r[key]]
        seen = {}
        for r in hits:
            seen.setdefault(r["cur_body"], r["cur_seq"])   # 去重键 = 当前句 body 原文（**不是** cur_seq）
        k, n = len(hits), len(subset)
        return {
            "events": k,
            "dedup_by_body": len(seen),
            "dup_delta": k - len(seen),
            "denominator": n,
            "rate": round(k / n, 6) if n else None,
            "wilson95": wilson(k, n),
            "band": band(n),
            "samples": [{"prev_seq": r["prev_seq"], "cur_seq": r["cur_seq"],
                         "p_prev": r["p_prev"], "p_cur": r["p_cur"],
                         "markers": r["markers"], "genuine_markers": r["genuine_markers"],
                         "prev_body": r["prev_body"], "cur_body": r["cur_body"]}
                        for r in hits[:max_samples]],
        }

    tiers = {t: {"all_messages": tally(rows, t), "reply_path": tally(reply_rows, t)} for t in TIERS}

    # ---- 机制侧 ----
    echo_rows, top_level = [], 0
    for r in recs:
        p = r.get("payload")
        if not isinstance(p, dict):
            continue
        if p.get("dialogue_echo"):
            top_level += 1
        ctx = p.get("ctx")
        de = ctx.get("echo") if isinstance(ctx, dict) else None
        if not de:
            continue
        echo_rows.append({"seq": r.get("seq"), "round": r.get("round"), "thread": p.get("thread_id"),
                          "v": de.get("v"), "sign": de.get("sign"), "intensity": de.get("intensity"),
                          "tier": de.get("tier"), "kind": de.get("kind"), "source": de.get("source"),
                          "mood": de.get("mood"), "prompted": de.get("prompted")})
    echo_seqs = {e["seq"] for e in echo_rows}
    mech = {
        "field_path": "payload.ctx.echo",
        "echo_rows_n": len(echo_rows),
        "echo_rows_ratio_per_message": round(len(echo_rows) / n_msg_all, 6) if n_msg_all else None,
        "top_level_dialogue_echo_rows": top_level,
        "ctx_echo_key_absent_on_all_msgs": all(
            not (isinstance(r.get("payload"), dict) and isinstance(r["payload"].get("ctx"), dict)
                 and "echo" in r["payload"]["ctx"])
            for r in recs if r.get("type") in {"MSG_DM", "MSG_PUBLIC", "MSG_GROUP"}),
        "versions": sorted({str(e["v"]) for e in echo_rows}),
        "prompted_all_true": all(e["prompted"] for e in echo_rows) if echo_rows else None,
        "by_source": dict(Counter(str(e["source"]) for e in echo_rows)),
        "by_tier": dict(Counter(str(e["tier"]) for e in echo_rows)),
        "by_sign": dict(Counter(str(e["sign"]) for e in echo_rows)),
        "by_kind": dict(Counter(str(e["kind"]) for e in echo_rows)),
        "n_threads": len({e["thread"] for e in echo_rows}),
        "echo_rows_tier_hit": {t: sum(1 for r in rows if r["cur_seq"] in echo_seqs and r[f"tier_{t}"])
                               for t in TIERS},
        "echo_rows_in_opportunities": sum(1 for r in rows if r["cur_seq"] in echo_seqs),
        "echo_rows_never_hit_any_tier": sum(1 for r in rows if r["cur_seq"] in echo_seqs
                                            and not any(r[f"tier_{t}"] for t in TIERS)),
        "activation_checks": {
            "v_all_f3_1": (len(echo_rows) > 0 and all(str(e["v"]) == "f3/1" for e in echo_rows)),
            "sign_dist_nonempty": len({str(e["sign"]) for e in echo_rows}) > 0,
            "source_dist": dict(Counter(str(e["source"]) for e in echo_rows)),
            "prompted_eq_field_present": (sum(1 for e in echo_rows if e["prompted"]) == len(echo_rows)) if echo_rows else None,
            "verdict": ("on_verified" if (len(echo_rows) > 0
                                          and all(str(e["v"]) == "f3/1" for e in echo_rows)
                                          and sum(1 for e in echo_rows if e["prompted"]) == len(echo_rows))
                        else ("off_or_not_activated" if len(echo_rows) == 0 else "partial_fail")),
            "note": ("四项齐（v=f3/1 / sign 非空 / source 构成 / prompted==present）才认『ON 确实 ON』；"
                     "echo_rows=0 时**无法区分**「开关关着」与「开关没生效」，不能写『机制无效』"),
        },
        "rows": echo_rows,
    }

    return {
        "meta": {"label": label, "log": os.path.relpath(path, REPO), "log_sha8": f4a.sha8(path),
                 "n_messages": n_msg_all, "n_threads": len(threads), "bad_lines": bad["n_bad"],
                 "n_messages_reply_path": sum(1 for k in threads for m in threads[k] if m.get("reply_to")),
                 "emotion_lexicon_sha256": hashlib.sha256(
                     open(os.path.join(REPO, "tools/d5/emotion_lexicon.txt"), "rb").read()).hexdigest()},
        "tier_definitions": {
            "loose": "极性相同 ∪ 任意 EMPATHY_MARKERS（= tools/d5 原式；与 R1–R13 可比）",
            "loose_no_agree": "极性相同 ∪ 标记剔 `我懂`（中间列，保留供历史对齐）",
            "polarity_match": "只认极性一致（标记一律不算）——技术对照，**禁止称「严格」**；负→负假阳性保留",
            "marker_based": "**主指标**：只认真回应标记（剔 我懂/确实/是啊/可不是），不要求极性一致；依赖词表⇒系统性低估",
        },
        "main_metric": "marker_based",
        "dropped": {"union_of_polarity_and_marker": "已弃用（并集不构成第三种标准）"},
        "tiers": tiers,
        "marker_hits": dict(marker_hits.most_common()),
        "agreement_only_excluded": list(AGREEMENT_ONLY),
        "opportunity_density": {
            "per_message": round(len(rows) / n_msg_all, 6) if n_msg_all else None,
            "per_round": round(len(rows) / len({m["round"] for m in msgs if m["round"] is not None}), 6)
            if {m["round"] for m in msgs if m["round"] is not None} else None,
            "n_rounds_seen": len({m["round"] for m in msgs if m["round"] is not None}),
        },
        "mechanism": mech,
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", metavar="PATH")
    ap.add_argument("--on", metavar="PATH")
    ap.add_argument("--arm", action="append", default=[], metavar="LABEL=PATH")
    ap.add_argument("--out-json")
    args = ap.parse_args()

    specs = []
    if args.off:
        specs.append(("off", args.off))
    if args.on:
        specs.append(("on", args.on))
    for s in args.arm:
        label, _, rel = s.partition("=")
        specs.append((label, rel))
    if not specs:
        raise SystemExit("[FAIL] 至少给一个 --off / --on / --arm")

    arms = [analyze(label, rel) for label, rel in specs]
    payload = {"schema": "f3-audit-echo/2",
               "script_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
               "empathy_markers": list(EMPATHY_MARKERS),
               "agreement_only_excluded": list(AGREEMENT_ONLY),
               "arms": arms}
    if args.out_json:
        out = args.out_json if os.path.isabs(args.out_json) else os.path.join(REPO, args.out_json)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
        print("written:", out)

    print("\n### 四档口径（事件 / 去重 / 分母 / 率 / Wilson95 / band）")
    print("| arm | sha8 | scope | tier | 事件 | 去重 | Δ | 分母 | 率 | Wilson95 | band |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for a in arms:
        for scope in ("all_messages", "reply_path"):
            for t in TIERS:
                v = a["tiers"][t][scope]
                print(f"| {a['meta']['label']} | {a['meta']['log_sha8']} | {scope} | {t} | {v['events']} | "
                      f"{v['dedup_by_body']} | {v['dup_delta']} | {v['denominator']} | {v['rate']} | "
                      f"{v['wilson95']} | {v['band']} |")
    print("\n### 机制侧（payload.ctx.echo）")
    for a in arms:
        m = a["mechanism"]
        print(f"- {a['meta']['label']} ({a['meta']['log_sha8']}): echo_rows={m['echo_rows_n']} "
              f"ratio={m['echo_rows_ratio_per_message']} absent={m['ctx_echo_key_absent_on_all_msgs']} "
              f"top_level={m['top_level_dialogue_echo_rows']} src={json.dumps(m['by_source'], ensure_ascii=False)} "
              f"tier={json.dumps(m['by_tier'], ensure_ascii=False)} "
              f"词表接住={json.dumps(m['echo_rows_tier_hit'], ensure_ascii=False)} "
              f"给了但四档全不命中={m['echo_rows_never_hit_any_tier']}")
    for a in arms:
        print(f"\n{a['meta']['label']} 机会密度 {json.dumps(a['opportunity_density'], ensure_ascii=False)} | "
              f"回复路径 {a['meta']['n_messages_reply_path']}/{a['meta']['n_messages']} | "
              f"标记词 {json.dumps(a['marker_hits'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
