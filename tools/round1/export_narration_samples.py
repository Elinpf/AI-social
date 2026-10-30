#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROUND1 抽样件导出：从 run.jsonl 抽「旁白/动作神态」与「纯台词」两类 MSG 样本，落可入库的 md。

为什么需要：`run.jsonl` 被 `.gitignore` 的 `**/*.jsonl` 排除（17 MB 日志不入库），
评审不该被要求先 clone 再找原始日志。本工具把**评审真正要看的那 40 条**抽成小 md 入库，
并给出每条的定位字段（actor / round / seq / thread_id / turn_index / msg_uid），可回原始日志定位。

口径（与 `tools/d9i/narration_stats.py` 一致，不另立尺子）：
  * 旁白/动作神态样本 = body 里含**成对括号块**（`PAIRED_RE`）的 MSG；
  * 纯台词样本       = body 里**不含**任何左括号字符的 MSG。

选样规则（确定性、可复算）：
  * 按 `msg_uid` 的数值序（seed:mono_ts）排序后顺序扫描；
  * 同一 `body` 只保留第一次出现（去重，避免同一句重复刷屏）；
  * 一类取满 `--n-narration` / `--n-plain` 条即停；
  * 不做随机，不读墙钟 ⇒ 同输入必然同输出。

⚠️ **抽样局限（必须随件一起读）**：上面的"顺序取前 N"**不是分层抽样**，
⇒ 样本**偏向靠前轮次与靠前出场角色**；本件只作定性阅读材料，**不作分布推断**。

`msg_uid` 唯一性（去重会不会误删的依据）：`muid = seed:mono_ts`，本函数在导出时实测
`len(set(msg_uid)) == len(msg_uid)` 并写进 md 与 stdout（不等即 fail-loud：
同毫秒同角色两次发言会撞 uid，那时"按 uid 排序 + body 去重"就不再等价于"按发言顺序"）。

用法：
    PYTHONPATH=code python3 tools/round1/export_narration_samples.py \
        --log v2/evidence/round1_narration_default_n16r24_s42/run.jsonl \
        --out v2/evidence/round1_narration_default_n16r24_s42/narration_samples.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "d9i"))
from narration_stats import PAIRED_RE  # noqa: E402  同一把尺子

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC")
ANY_OPEN = re.compile(r"[（(]")


def _uid_key(uid: str):
    seed, _, ts = (uid or "0:0").partition(":")
    try:
        return (int(seed), int(ts))
    except ValueError:
        return (1 << 30, 1 << 30)


def _row(e: dict) -> dict:
    p = e.get("payload") or {}
    return {
        "actor": e.get("actor") or p.get("from"),
        "round": e.get("round"),
        "seq": e.get("seq"),
        "msg_id": p.get("msg_id"),
        "msg_uid": p.get("msg_uid"),
        "thread_id": p.get("thread_id"),
        "turn_index": p.get("turn_index"),
        "reply_to": p.get("reply_to"),
        "place": p.get("place"),
        "slot": p.get("slot"),
        "day": p.get("day"),
        "body": p.get("body") or "",
        "type": e.get("type"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-narration", type=int, default=25)
    ap.add_argument("--n-plain", type=int, default=15)
    ap.add_argument("--head", default="ROUND1 旁白通道默认化 · 抽样件（n16 r24 seed42）")
    args = ap.parse_args(argv)

    msgs, total = [], 0
    for ln in open(args.log, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if e.get("type") not in MSG_TYPES:
            continue
        total += 1
        msgs.append(_row(e))

    msgs.sort(key=lambda r: _uid_key(r["msg_uid"]))
    seen, nar, plain = set(), [], []
    for r in msgs:
        body = r["body"]
        if not body.strip() or body in seen:
            continue
        if PAIRED_RE.search(body):
            if len(nar) < args.n_narration:
                nar.append(r)
                seen.add(body)
        elif not ANY_OPEN.search(body):
            if len(plain) < args.n_plain:
                plain.append(r)
                seen.add(body)

    n_paired = sum(1 for r in msgs if PAIRED_RE.search(r["body"]))

    # msg_uid 唯一性（去重与排序都依赖它）：实测并写进产物；不唯一即 fail-loud，不静默继续
    uids = [r["msg_uid"] for r in msgs]
    n_uid, n_uid_distinct = len(uids), len(set(uids))
    if n_uid != n_uid_distinct:
        dup = sorted({u for u in uids if uids.count(u) > 1})
        raise SystemExit(f"[export] FAIL: msg_uid 不唯一（{n_uid_distinct}/{n_uid}），"
                         f"重复值示例={dup[:5]}；本工具的去重/排序口径不再成立，停止导出。")
    bodies = [r["body"] for r in msgs]

    def esc(s) -> str:
        return str(s).replace("|", "\\|").replace("\n", " ")

    lines = [
        f"# {args.head}",
        "",
        "来源：`run.jsonl`（17 MB，被 `.gitignore` 的 `**/*.jsonl` 排除，**未入库**）；"
        f"本文件由 `tools/round1/export_narration_samples.py` 确定性导出，可复算。",
        "",
        f"- MSG 总数（MSG_DM+MSG_PUBLIC）：**{total}**",
        f"- 含成对括号（旁白/动作神态）MSG 数：**{n_paired}**（{n_paired / total:.1%}）"
        if total else "",
        f"- 本文件抽：旁白类 **{len(nar)}** 条 + 纯台词类 **{len(plain)}** 条",
        f"- `msg_uid` 唯一性实测：**`len(set)= {n_uid_distinct}` == `len = {n_uid}`**（全批无碰撞）"
        f"；`body` 去重：`len(set)= {len(set(bodies))}` / `len = {len(bodies)}`（本批去重未删掉任何一条）",
        "",
        "> **抽样局限**：抽样为确定性顺序取前 N（按 `msg_uid` 序、`body` 首次出现去重），"
        "**非分层抽样**，故样本偏向靠前轮次与靠前出场角色；结论只作定性阅读材料，**不作分布推断**。",
        "",
        "定位字段说明：`actor`（= `P{id}`） = 说话角色；`R{round}` = 世界回合；`seq` = 事件序号（run.jsonl 内唯一）；"
        "`thread_id` = 对话线程；`turn_index` = 线程内第几轮；`msg_uid` = `seed:mono_ts`（回原始日志用 grep 定位）。",
        "",
        "口径与 `tools/d9i/narration_stats.py` 一致：旁白类 = body 含**成对括号块**；纯台词类 = body 不含任何左括号字符。",
        "",
        "## A. 旁白 / 动作神态样本（含成对括号）",
        "",
        "| # | 定位 | 正文 |",
        "|---|---|---|",
    ]
    for i, r in enumerate(nar, 1):
        loc = (f"{r['actor']} / R{r['round']} / seq={r['seq']} / {r['thread_id']} / "
               f"turn={r['turn_index']} / uid={r['msg_uid']} / {r['type']}")
        lines.append(f"| {i} | {esc(loc)} | {esc(r['body'])} |")

    lines += ["", "## B. 纯台词样本（无括号旁白）", "", "| # | 定位 | 正文 |", "|---|---|---|"]
    for i, r in enumerate(plain, 1):
        loc = (f"{r['actor']} / R{r['round']} / seq={r['seq']} / {r['thread_id']} / "
               f"turn={r['turn_index']} / uid={r['msg_uid']} / {r['type']}")
        lines.append(f"| {i} | {esc(loc)} | {esc(r['body'])} |")

    lines += [
        "",
        "## 复算",
        "",
        "```bash",
        "PYTHONPATH=code python3 tools/round1/export_narration_samples.py \\",
        f"  --log {args.log} \\",
        f"  --out {args.out}",
        "```",
        "",
        "注：本抽样件只用于**人工读样本**（Q2 的 N≥30），不做质量判定；"
        "「像不像人 / 有没有生活气息」必须由人读后给结论，机器读数只报通道是否生效。",
        "",
    ]
    Path(args.out).write_text("\n".join(l for l in lines if l is not None), encoding="utf-8")
    print(json.dumps({"log": args.log, "out": args.out, "msg_total": total,
                      "paired_total": n_paired, "narration_picked": len(nar),
                      "plain_picked": len(plain), "uid_total": n_uid,
                      "uid_distinct": n_uid_distinct,
                      "body_total": len(bodies), "body_distinct": len(set(bodies)),
                      "sampling": "deterministic_prefix_not_stratified"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
