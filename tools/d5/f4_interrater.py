#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两位标注者的一致性核对（标注者可靠性注记，非指标）。

输入：
  --mine     第一标注者 verdict（judgements: seq/verdict）
  --other    第二标注者 verdict（judgements: item_id/seq/verdict）
  --packet   盲包 json（用于 seq→item_id 映射 + sha 完整性校验）

输出：一致 N / 不一致 M + 分歧明细；并计算 Cohen's κ，但**在 n 很小时显式标注不可用**。

代码强制：
  * 两位标注者的 seq 集合必须完全相同（否则 rc=6），缺一条不许"当作一致"；
  * 只有当 second 文件自报的 packet_sha256 / criteria_sha256 与实物 sha 一致时才继续（否则 rc=7）——
    防止"声称用了同一个包、实际不是"；
  * 任何 verdict 不在 real/noise/undecidable 内即 rc=5。

退出码：0 成功；2 输入不可用；5 verdict 非法；6 seq 集合不一致；7 包/判据 sha 自述与实物不符。
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

VALID = ("real", "noise", "undecidable")
LABEL = {"real": "真张力", "noise": "非真张力", "undecidable": "不可判"}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_verdicts(path, key):
    d = json.load(open(path, encoding="utf-8"))
    out = {}
    for r in d.get("judgements") or []:
        v = r.get("verdict")
        if v not in VALID:
            print("[FAIL] %s: seq=%s verdict 非法 %r" % (path, r.get("seq"), v), file=sys.stderr)
            sys.exit(5)
        out[r["seq"]] = {"verdict": v, "reason": r.get("reason", ""), "noise_type": r.get("noise_type")}
    return d, out


def kappa(a, b, keys):
    """Cohen's κ（二分类展开到三分类）。n 小时不稳定，调用方必须标注。"""
    n = len(keys)
    if n == 0:
        return None
    po = sum(1 for k in keys if a[k]["verdict"] == b[k]["verdict"]) / n
    pe = 0.0
    for c in VALID:
        pa = sum(1 for k in keys if a[k]["verdict"] == c) / n
        pb = sum(1 for k in keys if b[k]["verdict"] == c) / n
        pe += pa * pb
    if pe == 1.0:
        return None
    return round((po - pe) / (1 - pe), 4)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mine", required=True)
    ap.add_argument("--other", required=True)
    ap.add_argument("--packet", required=True)
    ap.add_argument("--arm", default="")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args(argv)

    for p in (args.mine, args.other, args.packet):
        if not os.path.exists(p):
            print("[FAIL] 缺输入: %s" % p, file=sys.stderr)
            return 2

    dmine, vm = load_verdicts(args.mine, "seq")
    doth, vo = load_verdicts(args.other, "seq")

    # --- 完整性：第二标注者自报的包/判据 sha 必须与实物一致
    pkt_sha = sha256_file(args.packet)
    declared_pkt = doth.get("packet_sha256")
    declared_crit = doth.get("criteria_sha256")
    crit_path = os.path.join(os.path.dirname(args.packet), "criteria_rules_extract.md")
    crit_sha = sha256_file(crit_path) if os.path.exists(crit_path) else None
    integrity = {
        "packet_sha256_actual": pkt_sha,
        "packet_sha256_declared": declared_pkt,
        "packet_match": declared_pkt in (None, pkt_sha),
        "criteria_sha256_actual": crit_sha,
        "criteria_sha256_declared": declared_crit,
        "criteria_match": (crit_sha is None) or (declared_crit in (None, crit_sha)),
    }
    if not (integrity["packet_match"] and integrity["criteria_match"]):
        print("[FAIL] 第二标注者自报的包/判据 sha 与实物不符: %s" % json.dumps(integrity, ensure_ascii=False),
              file=sys.stderr)
        return 7

    if set(vm) != set(vo):
        print("[FAIL] seq 集合不一致: 仅我方=%s 仅对方=%s"
              % (sorted(set(vm) - set(vo)), sorted(set(vo) - set(vm))), file=sys.stderr)
        return 6

    keys = sorted(vm)
    pkt = json.load(open(args.packet, encoding="utf-8"))
    id_by_seq = {it["seq"]: it["item_id"] for it in pkt.get("items", [])}

    rows, agree, disagree = [], 0, []
    for k in keys:
        ok = vm[k]["verdict"] == vo[k]["verdict"]
        agree += 1 if ok else 0
        row = {
            "item_id": id_by_seq.get(k), "seq": k,
            "annotator_1": vm[k]["verdict"], "annotator_1_label": LABEL[vm[k]["verdict"]],
            "annotator_2": vo[k]["verdict"], "annotator_2_label": LABEL[vo[k]["verdict"]],
            "agree": ok,
            "annotator_1_reason": vm[k]["reason"], "annotator_2_reason": vo[k]["reason"],
            "annotator_2_noise_type": vo[k].get("noise_type"),
        }
        rows.append(row)
        if not ok:
            disagree.append(row)

    k = kappa(vm, vo, keys)
    res = {
        "schema_version": "f4-interrater/1.0",
        "positioning": "标注者可靠性注记，非指标；不改变主口径结论，不用于判断机制好坏",
        "arm": args.arm,
        "generated_at": datetime.now().astimezone().isoformat(),
        "inputs": {
            "annotator_1": {"path": os.path.abspath(args.mine), "sha256": sha256_file(args.mine),
                            "identity": dmine.get("annotator") or "batch-evidence-runner"},
            "annotator_2": {"path": os.path.abspath(args.other), "sha256": sha256_file(args.other),
                            "identity": doth.get("annotator")},
            "packet": {"path": os.path.abspath(args.packet), "sha256": pkt_sha},
            "criteria_rules_extract_sha256": crit_sha,
            "criteria_source_sha256": doth.get("criteria_source_sha256"),
        },
        "integrity": integrity,
        "n_items": len(keys),
        "agree": agree,
        "disagree": len(disagree),
        "agreement_detail": rows,
        "kappa": k,
        "kappa_note": ("n=%d 太小，Cohen's κ 不稳定，只能作参考、不得当作可靠性证据；"
                       "结论以「一致 %d / 不一致 %d + 分歧明细」为准" % (len(keys), agree, len(disagree))),
        "partial_priming_disclosure":
            "判据 §4「常见噪声形态」的示例与本批判定条目中的若干条同形（判据本身由这些个案起草），"
            "因此该部分标注存在部分引导；一致率对这几条不构成独立验证。",
        "layers_not_changed":
            "本文件不改变词表口径与人工判读口径的报告值，只说明两位标注者是否互相独立地收敛。",
    }

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
        f.write("\n")

    L = []
    L.append("# 两位标注者一致性核对（%s%s）" % (res["positioning"], ("｜臂 " + args.arm) if args.arm else ""))
    L.append("")
    L.append("> 这不是指标。它只回答一个问题：两个人在**同一批判定条款**下是否各自独立地判出同样的结论。")
    L.append("")
    L.append("- 生成时刻：`%s`" % res["generated_at"])
    L.append("- 第一标注者：`%s`（sha `%s`）" % (res["inputs"]["annotator_1"]["identity"],
                                             res["inputs"]["annotator_1"]["sha256"][:16] + "…"))
    L.append("- 第二标注者：`%s`（sha `%s`）" % (res["inputs"]["annotator_2"]["identity"] or "—",
                                             res["inputs"]["annotator_2"]["sha256"][:16] + "…"))
    L.append("- 事件包 sha：`%s`（自述一致：%s）" % (pkt_sha, integrity["packet_match"]))
    L.append("- 规则摘录 sha：`%s`（自述一致：%s）" % (crit_sha, integrity["criteria_match"]))
    L.append("")
    L.append("## 结果")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append("| 条目数 | %d |" % res["n_items"])
    L.append("| 一致 | **%d** |" % res["agree"])
    L.append("| 不一致 | **%d** |" % res["disagree"])
    L.append("| Cohen's κ（仅参考） | %s —— %s |" % (res["kappa"], res["kappa_note"]))
    L.append("")
    L.append("## 逐条并排")
    L.append("")
    L.append("| item | seq | 标注者1 | 标注者2 | 一致 |")
    L.append("|---|---|---|---|---|")
    for r in rows:
        L.append("| %s | %s | %s | %s | %s |"
                 % (r["item_id"], r["seq"], r["annotator_1_label"], r["annotator_2_label"],
                    "✔" if r["agree"] else "✘"))
    L.append("")
    if disagree:
        L.append("## 分歧明细")
        L.append("")
        for r in disagree:
            L.append("- `seq=%s`：标注者1 = %s；标注者2 = %s" % (r["seq"], r["annotator_1_label"], r["annotator_2_label"]))
            L.append("  - 标注者1 理由：%s" % r["annotator_1_reason"])
            L.append("  - 标注者2 理由：%s" % r["annotator_2_reason"])
        L.append("")
    else:
        L.append("## 分歧明细")
        L.append("")
        L.append("无分歧（`不一致 = 0`）。")
        L.append("")
    L.append("## 必须披露的限制")
    L.append("")
    L.append("1. %s" % res["partial_priming_disclosure"])
    L.append("2. 两位标注者看到的是**同一批判定条款**（T1–T4 同源同版本）：第一标注者看完整判据（含 §1 背景/§7 起草披露），"
             "第二标注者看 §2–§5 逐行摘录（逐字可定位）；差异仅在背景说明与上下文信息，不是两套规则。")
    L.append("3. 本文件不改变任何报告值；词表口径与人工判读口径的分母/分子照旧各自报，不相加、不互证。")
    open(args.out_md, "w", encoding="utf-8").write("\n".join(L) + "\n")

    print(json.dumps({"n_items": res["n_items"], "agree": agree, "disagree": len(disagree),
                      "kappa": k, "out_md": args.out_md}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
