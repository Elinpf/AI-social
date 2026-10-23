#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R19 · off-arm 内容门控假阳性率（同一份词表口径，改造关闭时也跑一遍）。

## 为什么要这个数

`code/life/topic_breadth.py::confirm()` 是**内容门控**：只有生成出来的正文真的命中
「岔入话题」关键词，才在 `tag_hints` 里追加第二个 tag。若关键词太松，**没开改造**的
基线日志里也会有一批消息「本来就命中」⇒ 这部分 tag 是白送的，会污染 on-arm 归因。
board-scout 在旧词表上实测 off 基线 **66/686 = 9.6%**（其中 `gift` 41/66）。

本脚本在同一批**未开改造**的真实日志上，用两种口径各算一次：
  * `old`：旧词表 + 单条件（board-scout 复核时的那版）
  * `new`：收紧词表 + 双条件「命中 shift 且不命中 base」（`code/life/topic_breadth.py` 现值）

## 口径（可复算，不用 LLM）

对日志里每条 MSG：
  1. 取 `agent = payload.from (DM/GROUP) 或 author (PUBLIC)`、`thread = payload.thread_id`、
     `round`、`turn = payload.turn_index`、`base = payload.ctx.topic 或 tag_hints[0]`；
  2. 用**与运行时同一个纯函数** `TB.plan(agent, thread, round, turn, base)` 指派岔题
     （`turn<1` 与 `sha256%3==0` 的 1/3 条按设计不岔 ⇒ 不计入分母）；
  3. 用 `confirm(body, shift, base)` 判定该条正文是否「已经命中」该岔题话题。
     ——改造关闭时不会有 tag 追加，所以**命中即假阳性**。

用法：
    python3 v2/evidence/r19_topicbreadth_pilot_n8r24_seed42/off_gate_fp.py \\
        --log v2/evidence/run_worldline_c1_ctrl_n16r84_seed42/run.jsonl \\
        --out v2/evidence/r19_topicbreadth_pilot_n8r24_seed42/off_gate_fp_n16r84.txt
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "code"))

from life import topic_breadth as TB  # noqa: E402

#: board-scout 复核时使用的**旧**词表（原样保留，仅用于对比"收紧前后"两个数）
OLD_KEYWORDS = {
    "skill_practice": ("手艺", "琢磨", "练手", "做工", "活计", "斧", "刀口", "针脚"),
    "mentorship": ("指点", "教", "请教", "跟着学", "学会了", "带我", "领我"),
    "job_choice": ("找活", "差事", "营生", "活儿", "做短工"),
    "combat_training": ("练功", "出拳", "拳", "胳膊", "力气", "招式", "对练"),
    "academic_collab": ("读书", "认字", "书本", "学问", "念书", "算盘", "字帖"),
    "creative_collab": ("搭伙", "花样", "点子", "新鲜", "捣鼓", "琢磨个"),
    "scarce_buy": ("抢", "紧俏", "存货", "剩", "买"),
    "savings": ("攒", "存", "钱罐", "积蓄", "省下"),
    "polite_reject": ("改天", "不巧", "推不了", "难为", "实在不行", "下回吧"),
    "counter_propose": ("价钱", "还价", "便宜", "折算", "换个价"),
    "gift": ("给你", "拿着", "捎", "送去", "尝", "留了"),
    "rel_maintain": ("走动", "串门", "惦记", "来看看", "问一声", "常来", "坐坐"),
    "whisper": ("悄悄", "别声张", "听说", "私下", "小声", "传话", "风声"),
    "ice_break": ("头回", "生面孔", "搭话", "认得", "认识"),
    "rel_accept": ("应下", "说定了", "记着", "就这么办", "一定"),
    "power_conflict": ("镇长", "规矩", "争", "拗", "说不通", "公道", "上头"),
    "contest": ("比一比", "谁赢", "较量", "试试身手", "赛"),
    "group_proposal": ("凑人", "张罗", "提议", "约齐", "大家一块"),
    "select_location": ("去哪儿", "地点", "改到", "挪到", "约在"),
}

MSG_TYPES = {"MSG_DM", "MSG_PUBLIC", "MSG_GROUP"}


def sender(rec: dict) -> str | None:
    p = rec.get("payload") or {}
    return p.get("from") or p.get("author")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = []
    with open(args.log, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("type") not in MSG_TYPES:
                continue
            p = r.get("payload") or {}
            ctx = p.get("ctx") or {}
            base = ctx.get("topic") or (p.get("tag_hints") or [None])[0]
            rows.append({
                "agent": sender(r),
                "thread": p.get("thread_id"),
                "round": r.get("round"),
                "turn": p.get("turn_index"),
                "base": base,
                "body": p.get("body") or "",
                "tags": list(p.get("tag_hints") or []),
            })

    n_msg = len(rows)
    n_with_shift = 0
    hit_old = hit_new = 0
    by_old = collections.Counter()
    by_new = collections.Counter()
    for m in rows:
        if not m["agent"] or not m["thread"] or m["turn"] is None or not m["base"]:
            continue
        plan = TB.plan(m["agent"], m["thread"], int(m["round"] or 0), int(m["turn"]), m["base"])
        if not plan:
            continue
        n_with_shift += 1
        shift = plan["shift"]
        if any(k in m["body"] for k in OLD_KEYWORDS.get(shift, ())):
            hit_old += 1
            by_old[shift] += 1
        if TB.confirm(m["body"], shift, m["base"]):
            hit_new += 1
            by_new[shift] += 1

    def r6(x: float) -> float:
        return round(x, 6)

    lines = [
        "# R19 off-arm 内容门控假阳性率（改造关闭时同口径重算）",
        "",
        "> 生成脚本：`v2/evidence/r19_topicbreadth_pilot_n8r24_seed42/off_gate_fp.py`",
        "> 口径：对每条 MSG 用运行时同一个纯函数 `TB.plan` 指派岔题，"
        "再用 `confirm(body, shift, base)` 判定正文是否已命中；改造关闭时命中即假阳性。",
        "",
        f"log = `{os.path.relpath(os.path.abspath(args.log), REPO)}`",
        f"MSG 总数 = {n_msg}",
        f"有岔题指派的分母（turn≥1 且未被 1/3 抽签跳过）= {n_with_shift}"
        f"（{r6(n_with_shift / n_msg) if n_msg else 0}）",
        "",
        "| 口径 | 命中条数 | 占全部 MSG | 占有指派的分母 | 主要误命中话题 |",
        "|---|---|---|---|---|",
        f"| old（旧词表 + 单条件） | {hit_old} | "
        f"{r6(hit_old / n_msg) if n_msg else 0} | "
        f"{r6(hit_old / n_with_shift) if n_with_shift else 0} | "
        f"{dict(by_old.most_common(5))} |",
        f"| new（收紧词表 + 双条件） | {hit_new} | "
        f"{r6(hit_new / n_msg) if n_msg else 0} | "
        f"{r6(hit_new / n_with_shift) if n_with_shift else 0} | "
        f"{dict(by_new.most_common(5))} |",
        "",
        "判读：`new` 这一行的「占全部 MSG」就是 on-arm 归因时必须扣掉的**基线白送率**；"
        "on-arm 的 tag 追加条数必须显著高于该基线，否则只能判「无结论」。",
    ]
    out = "\n".join(lines) + "\n"
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
