#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R19 · on/off 双臂读数汇总（工具只出数，不下结论；指标口径单一真源 = tools/d5/dialogue_metrics.py）。

产出（供报告/汇报直接引用）：
  1. D（下发数）、through（门控通过数）、through/D、landed/D（实现里 landed == through）
  2. F-2_content_drift 的 jaccard 分布（全对 + 发生 tag 变化的对）——**只作不恶化守卫**
  3. F-2_tag_change_split：tag_added（话题展开，副指标）/ tag_replaced（结构上恒 0，作反证）
  4. F-2b 多话题线程数 + 分母
  5. L-13 token 泄漏条数 + 分母
  6. 守卫：L-5 / L-6 / L-7 / F-1
  7. 人工 precision 抽样：把 tag 追加事件（含原文、base、shift、两侧 tag）导出，供人工判定

用法：
    python3 v2/evidence/r19_topicbreadth_n8r24_seed42/summarize_arms.py \
        --off v2/evidence/.../run_off --on v2/evidence/.../run_on \
        --out v2/evidence/.../summary.json --sample v2/evidence/.../precision_sample.md
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DM = os.path.join(REPO, "tools", "d5", "dialogue_metrics.py")
MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def run_metrics(log: str) -> dict:
    """调官方复算器（子进程），拿全量指标 JSON；不重复实现口径。"""
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    subprocess.run([sys.executable, DM, "--log", log, "--out-json", tmp],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(tmp, encoding="utf-8") as fh:
        res = json.load(fh)
    os.unlink(tmp)
    return res


def arm_stats(arm_dir: str) -> tuple[dict, list[dict]]:
    log = os.path.join(arm_dir, "run.jsonl")
    res = run_metrics(log)
    out = {"dir": os.path.relpath(arm_dir, REPO)}
    out["F1_chatter"] = res["F-1_chatter"]["nonfunctional_chatter_rate"]
    out["F2_content_drift"] = res["F-2_content_drift"]
    out["F2_tag_switch"] = res["F-2_tag_switch"]
    out["F2_tag_change_split"] = res["F-2_tag_change_split"]
    out["F2_legacy_dead_ruler"] = res["F-2_topic_drift"]["drift_rate"]
    out["F2b_multi_topic"] = res["F-2b_multi_topic_threads"]
    out["L13"] = {"n": res["L-13_token_leak"]["n"],
                  "rate": res["L-13_token_leak"]["token_leak_rate"],
                  "by_topic": res["L-13_token_leak"]["by_topic"]}
    out["L5_template_hit"] = res["L_wording"]["L-5_template_hit_rate"]
    out["L6_dup_exact"] = res["L_wording"]["L-6_dup_exact_rate"]
    out["L7_dup_ngram8"] = res["L_wording"]["L-7_dup_ngram8_rate"]

    D = through = msgs = 0
    tag_rows: list[dict] = []
    with open(log, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("type") not in MSG_TYPES:
                continue
            msgs += 1
            p = r.get("payload") or {}
            tb = (p.get("ctx") or {}).get("topic_breadth")
            if not tb:
                continue
            D += 1
            landed = bool(tb.get("landed"))
            if landed:
                through += 1
            tags = list(p.get("tag_hints") or [])
            if len(tags) >= 2:
                tag_rows.append({
                    "seq": r.get("seq"), "round": r.get("round"),
                    "agent": p.get("from") or p.get("author"),
                    "base": tb.get("base"), "shift": tb.get("shift"), "tags": tags,
                    "body": p.get("body"), "thread": p.get("thread_id"),
                    "turn": p.get("turn_index"), "landed": landed,
                })
    out.update({
        "msgs": msgs, "D_dispatched": D, "through": through,
        "through_over_D": round(through / D, 6) if D else None,
        "through_over_msgs": round(through / msgs, 6) if msgs else None,
        "tag_appended_events": len(tag_rows),
    })
    return out, tag_rows


def precision_sample(rows: list[dict], n: int = 15) -> str:
    """人工 precision 抽样：按 seq 升序**等间隔**取（不按质量挑选）。"""
    if not rows:
        return ("# R19 人工 precision 抽样\n\n"
                "（on 臂没有任何 tag 追加事件 ⇒ 无法抽样；按 Leader 规则判「不可判（召回不足）」，"
                "**不得**写成「改造无效」。）\n")
    step = max(1, len(rows) // n)
    picked = rows[::step][:n]
    lines = [
        "# R19 人工 precision 抽样（tag 追加 = 「话题展开」事件）", "",
        f"> 抽样规则：按 seq 升序**等间隔**取（不按质量挑选），共 {len(picked)} 条 / 总 {len(rows)} 条。",
        "> 判定标准：这句台词是否**接着上一句对话**自然带出第二个话题线索（不是硬拐、不是答非所问、"
        "不是把内部 token 念出来）。逐条填 `judgement`（真展开 / 假展开 / 存疑）。",
        "> 判定者须是**未参与实现代码编写**的人；本目录只提供抽样与原文。", "",
    ]
    for i, r in enumerate(picked, 1):
        lines += [
            f"## {i}. seq={r['seq']} round={r['round']} agent={r['agent']} "
            f"thread={r['thread']} turn={r['turn']}",
            f"- base 话题（本线程原有）：`{r['base']}`",
            f"- shift 话题（下发给模型的相邻话题）：`{r['shift']}`",
            f"- 记入日志的 tag_hints：`{r['tags']}`",
            f"- 正文：{r['body']}",
            "- judgement：【待人工填】",
            "",
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True, help="off 臂目录（含 run.jsonl）")
    ap.add_argument("--on", required=True, help="on 臂目录（含 run.jsonl）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--sample", default=None)
    args = ap.parse_args()

    off, _ = arm_stats(args.off)
    on, on_rows = arm_stats(args.on)
    summary = {"off_arm": off, "on_arm": on}
    txt = json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(txt + "\n")
    print(txt)
    if args.sample:
        with open(args.sample, "w", encoding="utf-8") as fh:
            fh.write(precision_sample(on_rows))
        print(f"[sample] {args.sample}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
