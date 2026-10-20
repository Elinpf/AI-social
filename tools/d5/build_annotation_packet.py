#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「独立第二标注」用的中性盲包（annotation packet）。

设计约束（来自 leader 补丁，逐条落实）：
  1. 中性命名与中性措辞：文件名/字段/README 不出现 v0 / baseline / before / 预期结论等身份与结论线索；
  2. 触发线索只给「命中的词 + 该词在正文中的字符位置」，**不给**任何倾向性解释
     （不写"反诘""疑似成语误命中"之类，避免把答案递给标注者）；
  3. 上下文给足：焦点消息前后各 N 条同线程消息（默认 2），带 from/to/渠道/轮次；
     但**不**给出任何"之后多少条内是否出现某词"的窗口结论信息；
  4. 不输出任何判读结论、闭环状态、命中修复词。

用法：
  python3 tools/d5/build_annotation_packet.py \
    --events-json <f4_repair_evidence 输出> --log <run.jsonl> \
    --out-dir <目录> --packet-id P-A1 --context 2
"""
import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dialogue_metrics as dm  # noqa: E402
from f4_repair_evidence import mixed_key, load_emotion, load_words  # noqa: E402

NEG_MARK = "负向词"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hits(body, emotion, sign):
    out = []
    for w, p in emotion.items():
        if (p > 0 and sign > 0) or (p < 0 and sign < 0):
            i = body.find(w)
            if i >= 0:
                out.append({"word": w, "char_pos_1based": i + 1})
    out.sort(key=lambda x: x["char_pos_1based"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-json", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--emotion", default=os.path.join(HERE, "emotion_lexicon.txt"))
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--packet-id", default="P-A1")
    ap.add_argument("--context", type=int, default=2, help="焦点消息前后各取几条同线程消息")
    ap.add_argument("--sample-n", type=int, default=0,
                    help="分层抽样条数（0=全量）。规则见 --sample-prereg，必须与预注册规则一致")
    ap.add_argument("--sample-prereg", default=None, help="抽样预注册文件（其 sha256 会写入包内）")
    ap.add_argument("--criteria", default=os.path.join(HERE, "..", "..", "v2", "evidence",
                                                       "r6_f4_baseline_repro", "prereg_f4_manual_judgement.md"),
                    help="冻结判据源文件（会复制成中性文件名放入包内，sha 不变）")
    args = ap.parse_args(argv)

    ev = json.load(open(args.events_json, encoding="utf-8"))
    emo = load_emotion(args.emotion)
    recs, _ = dm.read_run(args.log)
    msgs = dm.extract_messages(recs)
    threads = defaultdict(list)
    for m in msgs:
        threads[mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))

    os.makedirs(args.out_dir, exist_ok=True)

    # ---- 分层抽样（规则与 prereg_armC_sampling.md 一致；确定性、无随机数）
    events_all = ev["events"]
    sampling = None
    if args.sample_n and args.sample_n > 0:
        layers = ("dm", "public", "group")
        by_layer = {c: sorted([e for e in events_all if e["channel"] == c], key=lambda x: x["seq"])
                    for c in layers}
        n_total = sum(len(v) for v in by_layer.values())
        N = args.sample_n
        if n_total <= N:
            chosen = [e for c in layers for e in by_layer[c]]
            sampling = {"mode": "all", "n_total": n_total, "target": N,
                        "note": "事件总数 <= 目标抽检数 ⇒ 全取，不凑数、不重复",
                        "layers": {c: {"n_events": len(by_layer[c]), "k_taken": len(by_layer[c])} for c in layers}}
        else:
            base = {c: N * len(by_layer[c]) / n_total for c in layers}
            quota = {c: int(base[c]) for c in layers}
            rem = N - sum(quota.values())
            order = sorted(layers, key=lambda c: (-(base[c] - int(base[c])), layers.index(c)))
            for c in order:
                if rem <= 0:
                    break
                quota[c] += 1
                rem -= 1
            chosen, layers_info = [], {}
            # 层内等距取中点：idx = round((i+0.5)*n_c/k_c)，冲突则顺延
            for c in layers:
                arr = by_layer[c]
                n_c = len(arr)
                k_c = quota[c]
                if k_c <= 0 or n_c == 0:
                    layers_info[c] = {"n_events": n_c, "k_taken": 0}
                    continue
                k_eff = min(k_c, n_c)
                idxs = []
                for i in range(k_eff):
                    j = int(round((i + 0.5) * n_c / k_eff))
                    j = min(j, n_c - 1)
                    while j in idxs:
                        j = (j + 1) % n_c
                    idxs.append(j)
                layers_info[c] = {"n_events": n_c, "k_taken": len(idxs),
                                  "selected_seq": [arr[j]["seq"] for j in sorted(idxs)]}
                chosen.extend(arr[j] for j in sorted(idxs))
            chosen.sort(key=lambda x: x["seq"])
            sampling = {"mode": "stratified", "n_total": n_total, "target": N,
                        "rule": "按 channel 分层；最大余数法分配层额（小数相同按 dm→public→group）；"
                                "层内按 seq 升序等距取中点 round((i+0.5)*n_c/k_c)，冲突顺延；不使用随机数",
                        "layers": layers_info}
        if args.sample_prereg:
            sampling["prereg_path"] = os.path.abspath(args.sample_prereg)
            sampling["prereg_sha256"] = sha256_file(args.sample_prereg)
        events_used = chosen
    else:
        events_used = events_all

    items = []
    for e in events_used:
        th = threads[e["thread"]]
        idx = next(i for i, m in enumerate(th) if m["seq"] == e["seq"])
        lo = max(0, idx - args.context)
        hi = min(len(th), idx + args.context + 1)
        ctx = []
        for j in range(lo, hi):
            m = th[j]
            ctx.append({
                "position": ("focus" if j == idx else ("前 %d" % (idx - j) if j < idx else "后 %d" % (j - idx))),
                "seq": m["seq"],
                "from": m["from"], "to": m["to"],
                "channel": m["channel"],
                "round": m["round"],
                "day": m["day"], "slot": m["slot"], "place": m["place"],
                "body": m["body"],
            })
        focus = th[idx]
        cue = {"hit_words": hits(focus["body"], emo, -1)}
        if idx > 0:
            prev_pos = hits(th[idx - 1]["body"], emo, +1)
            if prev_pos:
                cue["previous_message_hit_words"] = prev_pos
        items.append({
            "item_id": "E%02d" % (len(items) + 1),
            "seq": focus["seq"],
            "channel": focus["channel"],
            "round": focus["round"],
            "from": focus["from"], "to": focus["to"],
            "focus_body": focus["body"],
            "mechanical_cue": cue,
            "context": ctx,
        })

    packet = {
        "packet_id": args.packet_id,
        "purpose": "对一组候选「人际张力」消息做独立文本判读",
        "note": "本包只含原文、定位与机械命中线索；不含任何判读结论、倾向性提示，也不含后续消息的判定信息。",
        "judgement_file": "criteria_judgement_frozen.md（同目录，冻结）",
        "context_window": "焦点消息前后各 %d 条同线程消息" % args.context,
        "sampling": sampling,
        "items": items,
    }
    pk = os.path.join(args.out_dir, "annotation_packet_events.json")
    json.dump(packet, open(pk, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 判据：只给**规则部分**的逐行摘录（§2–§5），不整份拷贝。
    # 原因：冻结判据的 §1/§7 记录了另一次判读的具体发现（哪几条是假阳性、起草背景），
    # 整份给出去会直接破坏盲判（身份+答案双泄露）。规则文本本身一字不改。
    raw_lines = open(args.criteria, encoding="utf-8").read().splitlines()
    src_sha = sha256_file(args.criteria)
    sec_idx = [i for i, ln in enumerate(raw_lines) if ln.startswith("## ")]
    keep_ranges = []
    for k, i in enumerate(sec_idx):
        head = raw_lines[i]
        num = head.replace("## ", "").strip()[:1]
        if num in "2345":
            end = sec_idx[k + 1] if k + 1 < len(sec_idx) else len(raw_lines)
            keep_ranges.append((i, end))
    extract_lines = []
    for a, b in keep_ranges:
        extract_lines.extend(raw_lines[a:b])
    src_set = set(raw_lines)
    for ln in extract_lines:                       # 逐行 verbatim 校验
        assert ln in src_set, "摘录行必须在源判据中逐字出现: %r" % ln
    crit_dst = os.path.join(args.out_dir, "criteria_rules_extract.md")
    hdr = [
        "# 判读规则（冻结判据的逐行摘录 §2–§5）",
        "",
        "> 本文件是冻结判据 `criteria_judgement_frozen` 源文件的**逐行摘录**（只摘 §2 判定单元、§3 判定条件 T1–T4、"
        "§4 常见噪声形态、§5 允许的第三种结论），**规则文本一字未改**；",
        "> 源文件 sha256 = `%s`。" % src_sha,
        "> 未纳入摘录的：§1 背景说明、§6 判读流程、§7 起草披露——§1/§7 含另一路判读的具体发现，§6 含本团队内部文件名与预期产出，"
        "给出都会破坏独立判读或泄露身份，故按隔离要求剔除。",
        "> 校验：上列每一行均可在源文件中逐字定位（生成时以 assert 强制）。",
        "",
    ]
    open(crit_dst, "w", encoding="utf-8").write("\n".join(hdr + extract_lines) + "\n")
    crit_sha = sha256_file(crit_dst)

    tpl = {
        "annotator": "",
        "annotator_role": "独立第二标注者",
        "packet_id": args.packet_id,
        "judged_at": "",
        "criteria_path": "criteria_rules_extract.md（与本包同目录；冻结判据的逐行摘录 §2–§5）",
        "criteria_source_sha256": src_sha,
        "criteria_sha256": crit_sha,
        "judgements": [{"item_id": it["item_id"], "seq": it["seq"], "verdict": "",
                        "noise_type": "", "reason": ""} for it in items],
    }
    tp = os.path.join(args.out_dir, "annotation_template.json")
    json.dump(tpl, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    L = []
    L.append("# 独立第二标注 · 说明（packet `%s`）" % args.packet_id)
    L.append("")
    L.append("你的任务：按一份**冻结的**判据文本，对下面 %d 条消息逐条判「是不是真实的人际张力」。" % len(items))
    L.append("这是纯文本判读，不需要跑任何脚本、不需要跑批、不需要改仓库文件。")
    L.append("")
    L.append("## 你要读的两个文件")
    L.append("")
    L.append("1. **判读规则（冻结，一个字都不许改）**：`criteria_rules_extract.md`（与本包同目录，是冻结判据 §2–§5 的逐行摘录）")
    L.append("   源判据 sha256 = `%s`；摘录已剔除 §1 背景与 §7 披露（含另一路判读的具体发现，给出会破坏独立判读）。" % tpl["criteria_source_sha256"])
    L.append("   sha256 = `%s`" % tpl["criteria_sha256"])
    L.append("2. **事件包**：`annotation_packet_events.json`（sha256 = `%s`）" % sha256_file(pk))
    L.append("")
    L.append("## 隔离规则（硬约束）")
    L.append("")
    L.append("- 只看上面两个文件；**不要**去仓库里翻与这批消息相关的其它证据文件（别处已有另一个人完成的判读结果与相关读数），也不要看 `tools/d5/` 下统计脚本的输出。")
    L.append("- 判读期间不要与其他成员讨论这批消息。")
    L.append("- 判据没覆盖的情形：判 `undecidable`，reason 写「判据未覆盖：…」，**不要**自行扩写判据，也**不要**要求修改判据（判据已冻结，改判据等于事后拟合）。")
    L.append("")
    L.append("## 每条 item 的结构")
    L.append("")
    L.append("| 字段 | 含义 |")
    L.append("|---|---|")
    L.append("| `item_id` / `seq` | 条目编号与日志事件序号（定位用） |")
    L.append("| `focus_body` | **需要你判读的那一条**消息正文 |")
    L.append("| `mechanical_cue` | 纯机械命中信息：哪个词、在该正文第几个字符。**不含任何倾向性解释** |")
    L.append("| `context` | 同线程上下文：焦点消息前后各 %d 条（`position` 标明 focus / 前 N / 后 N） |" % args.context)
    L.append("")
    L.append("## 产出")
    L.append("")
    L.append("- 填 `annotation_template.json` → 另存为 `verdict_%s_second.json`（**不要增删 item，不要改 seq**）" % args.packet_id)
    L.append("- `verdict` 只允许：`real` / `noise` / `undecidable`；`noise_type` 自己用短语概括；`reason` 必须**引用原文片段**。")
    L.append("- 填完把该文件的**绝对路径**发消息给 batch-evidence-runner，只发路径即可。")
    L.append("")
    L.append("## 后续怎么用你的结果")
    L.append("")
    L.append("- 只与另一位标注者的结论做**并排核对**：报「一致 N 条 / 不一致 M 条 + 分歧明细」；条目数很少，**不计算 Cohen's κ**。")
    L.append("- 该核对只作为**标注者可靠性注记**，不改变主结论，也不用于判定机制好坏。")
    L.append("")
    rp = os.path.join(args.out_dir, "README_annotation.md")
    open(rp, "w", encoding="utf-8").write("\n".join(L) + "\n")

    print(json.dumps({"packet": pk, "packet_sha256": sha256_file(pk),
                      "template": tp, "readme": rp, "n_items": len(items)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
