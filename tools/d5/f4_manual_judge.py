#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-4 人工判读层（并列注记，非自动指标）。

输入：
  --events-json   f4_repair_evidence.py 的输出（逐条张力事件）
  --judgements    人工判读数据（seq -> {verdict, reason, quote}），判据见 --prereg
  --prereg        先写后判的判据文件（其 sha256 会写进输出，binding 用）

约束（代码强制）：
  * 覆盖性断言：每条张力事件都必须有判读结论，缺一条即 rc=5，不许"漏判就当没发生"；
  * verdict 只能是 `real` / `noise` / `undecidable`；
  * 判读只作用于「词表口径张力事件」这一集合，不新增事件、不改分母定义；
  * 输出固定并列两套口径（词表口径 / 人工判读），且**不产出百分比**。

退出码：0 成功；2 输入不可用；5 覆盖不全或 verdict 非法。
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

VALID = ("real", "noise", "undecidable")
LABEL = {"real": "真张力", "noise": "非真张力（词表噪声）", "undecidable": "不可判"}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-json", required=True)
    ap.add_argument("--judgements", required=True)
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--arm", default="", help="臂名（如 v0-anchor / r6-after）")
    args = ap.parse_args(argv)

    for p in (args.events_json, args.judgements, args.prereg):
        if not os.path.exists(p):
            print("[FAIL] 缺输入: %s" % p, file=sys.stderr)
            return 2

    ev = json.load(open(args.events_json, encoding="utf-8"))
    events = ev.get("events") or []
    jug = json.load(open(args.judgements, encoding="utf-8"))
    rows = jug.get("judgements") or []

    by_seq = {}
    for r in rows:
        s = r.get("seq")
        if s is None:
            print("[FAIL] 判读条目缺 seq: %r" % (r,), file=sys.stderr)
            return 5
        if r.get("verdict") not in VALID:
            print("[FAIL] seq=%s verdict 非法: %r" % (s, r.get("verdict")), file=sys.stderr)
            return 5
        by_seq[s] = r

    missing = [e["seq"] for e in events if e["seq"] not in by_seq]
    if missing:
        print("[FAIL] 覆盖不全：这些张力事件没有判读结论 seq=%s（禁止漏判当无）" % missing, file=sys.stderr)
        return 5
    extra = [s for s in by_seq if s not in {e["seq"] for e in events}]
    if extra:
        print("[FAIL] 判读里有多余 seq=%s（不存在于词表口径事件集，禁止造事件）" % extra, file=sys.stderr)
        return 5

    out_rows = []
    for e in events:
        r = by_seq[e["seq"]]
        out_rows.append({
            "seq": e["seq"], "line": e["line"], "thread": e["thread"], "channel": e["channel"],
            "from": e["from"], "to": e["to"], "round": e["round"],
            "body": e["body"],
            "lexicon_trigger": e["trigger"], "lexicon_closed": e["closed"],
            "lexicon_repair_words": e["repair_words"], "lexicon_lag": e["lag"],
            "verdict": r["verdict"], "verdict_label": LABEL[r["verdict"]],
            "reason": r.get("reason", ""), "noise_type": r.get("noise_type"),
            "closed_if_real": (e["closed"] if r["verdict"] == "real" else None),
        })

    real = [x for x in out_rows if x["verdict"] == "real"]
    noise = [x for x in out_rows if x["verdict"] == "noise"]
    und = [x for x in out_rows if x["verdict"] == "undecidable"]
    real_closed = [x for x in real if x["closed_if_real"]]

    res = {
        "schema_version": "f4-manual-judge/1.0",
        "layer": "人工判读（非自动指标；标注者信息见 annotator 字段）",
        "arm": args.arm,
        "generated_at": datetime.now().astimezone().isoformat(),
        "prereg": {"path": os.path.abspath(args.prereg), "sha256": sha256_file(args.prereg)},
        "inputs": {
            "events_json": os.path.abspath(args.events_json),
            "events_json_sha256": sha256_file(args.events_json),
            "judgements": os.path.abspath(args.judgements),
            "judgements_sha256": sha256_file(args.judgements),
            "script": os.path.abspath(__file__),
            "script_sha256": sha256_file(__file__),
        },
        "two_layers_side_by_side": {
            "word_lexicon_layer": {
                "denominator_tension_events": ev["F-4_tension_repair"]["denominator_tension_events"],
                "numerator_repaired": ev["F-4_tension_repair"]["numerator_repaired"],
                "note": "跨臂同规则可比；不是真实张力计数；分母<30 只报事件数",
            },
            "manual_judgement_layer": {
                "denominator_real_tension_events": len(real),
                "numerator_real_repaired": len(real_closed),
                "undecidable": len(und),
                "note": "单一标注者判读；不作指标、不换算百分比、不与词表口径相加或互证",
            },
        },
        "counts": {"real": len(real), "noise": len(noise), "undecidable": len(und),
                   "total_judged": len(out_rows)},
        "noise_types": sorted({x["noise_type"] for x in noise if x.get("noise_type")}),
        "rows": out_rows,
    }

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
        f.write("\n")

    L = []
    L.append("# F-4 人工判读层（%s%s）" % (res["layer"], ("｜臂 " + args.arm) if args.arm else ""))
    L.append("")
    L.append("> **这不是自动指标。** 本层只能称「标注者的判读」，**不得称「人工校验通过」**。")
    L.append("> 若同一批事件另有独立第二标注，其一致性核对单独落在 `f4_interrater_*.md`（仅作标注者可靠性注记，"
             "不改变本层任何数值）。本层只用来给词表口径兜底噪声水平，**不进结论表的率、不与词表口径相加或互证**。")
    L.append("")
    L.append("- 生成时刻：`%s`" % res["generated_at"])
    L.append("- 判据（先写后判）：`%s`，sha256 `%s`" % (res["prereg"]["path"], res["prereg"]["sha256"]))
    L.append("- 事件集：`%s`，sha256 `%s`" % (res["inputs"]["events_json"], res["inputs"]["events_json_sha256"]))
    L.append("- 判读脚本 sha256：`%s`" % res["inputs"]["script_sha256"])
    L.append("")
    L.append("## 并列两套口径（两个分母都写，都不换算百分比）")
    L.append("")
    L.append("| 口径 | 张力事件（分母） | 其中已闭环（分子） | 说明 |")
    L.append("|---|---|---|---|")
    w = res["two_layers_side_by_side"]["word_lexicon_layer"]
    m = res["two_layers_side_by_side"]["manual_judgement_layer"]
    L.append("| **词表口径** | %d | %d | 跨臂同规则可比；**不是真实张力计数** |"
             % (w["denominator_tension_events"], w["numerator_repaired"]))
    L.append("| **人工判读口径** | %d | %d | 单一标注者、无双重编码、无一致性检验；不可判 %d 条 |"
             % (m["denominator_real_tension_events"], m["numerator_real_repaired"], m["undecidable"]))
    L.append("")
    L.append("## 逐条判读（含原文引用与理由）")
    L.append("")
    L.append("| # | seq | 行号 | 渠道 | 说话人→对象 | 词表触发 | 人工结论 | 噪声类型 | 判读理由（引原文） | 若为真张力：词表是否闭环 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for i, x in enumerate(out_rows, 1):
        L.append("| %d | %s | %s | %s | %s→%s | %s | **%s** | %s | %s | %s |"
                 % (i, x["seq"], x["line"], x["channel"], x["from"], x["to"] or "—",
                    x["lexicon_trigger"], x["verdict_label"], x["noise_type"] or "—",
                    x["reason"].replace("|", "\\|"),
                    ("闭环" if x["closed_if_real"] else "未闭环") if x["verdict"] == "real" else "—"))
    L.append("")
    L.append("## 原文（逐条，便于第三方复核）")
    L.append("")
    for i, x in enumerate(out_rows, 1):
        L.append("**#%d** `seq=%s` L%s｜%s｜%s→%s｜词表触发=%s｜**%s**"
                 % (i, x["seq"], x["line"], x["thread"], x["from"], x["to"] or "—",
                    x["lexicon_trigger"], x["verdict_label"]))
        L.append("")
        L.append("> %s" % x["body"])
        L.append("")
        L.append("- 判读理由：%s" % x["reason"])
        if x["verdict"] == "real":
            L.append("- 词表口径下是否闭环：%s" % ("闭环" if x["closed_if_real"] else "未闭环"))
        L.append("")
    L.append("## 不许这样用")
    L.append("")
    L.append("1. 不许写「人工判读 X% 闭环」——本轮分子恒为 0，且**分母<30，任何百分比都不成立**。")
    L.append("2. 不许把人工口径当成更准的指标替换词表口径——跨臂对比必须仍走词表口径。")
    L.append("3. 不许把本层结果用于证明机制有效；它只描述**词表口径的分母里有多少是噪声**。")
    open(args.out_md, "w", encoding="utf-8").write("\n".join(L) + "\n")

    print(json.dumps({
        "arm": args.arm,
        "word_layer": "分母 %d / 分子 %d" % (w["denominator_tension_events"], w["numerator_repaired"]),
        "manual_layer": "分母 %d / 分子 %d (不可判 %d)" % (
            m["denominator_real_tension_events"], m["numerator_real_repaired"], m["undecidable"]),
        "out_json": args.out_json, "out_md": args.out_md,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
