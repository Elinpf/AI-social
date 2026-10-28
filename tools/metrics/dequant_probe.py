#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEQUANT 维度的离线度量器（**纯只读、零跑批、零 LLM、零 import `code/life`**）。

口径**直接来自侦察报告** `reports/recon-20261028.md` §7.1，不自造：

    「半指」121/510=23.7%、「第三格」152/510=29.8%、「上回」407/510=79.8%、
      「上次」35/510=6.9%、「想起」52/510=10.2%、首 6 字模板 Top5。

判定口径（与 report 的 `python3 -c` 一行版逐字等价）：
  * 分母 = `run.jsonl` 里 `type` 以 `MSG_` 开头的所有事件（`MSG_PUBLIC`/`MSG_DM`/
    `MSG_GROUP` …），正文取 `payload.body`；
  * 关键词命中 = **子串包含**（`kw in body`），一条消息只计一次；
  * 首 6 字模板 = `body[:6]` 的最频繁取值（并列时按 (词, 计数) 稳定排序后取前 N）。

本脚本的**自证**要求：在基线日志上必须复算出 79.8% / 29.8% / 23.7%（±0.4pp），
否则 `--expect-baseline` 直接 rc=4 退出（防口径漂移）。

用法：
    python3 tools/metrics/dequant_probe.py --log <run.jsonl> [--out out.json] \
        [--expect-baseline] [--no-timestamp] [--top-n 5]

退出码：0 正常 / 2 输入不可用（日志缺失或无 MSG）/ 3 自检失败（--expect-baseline 未达标）
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True          # 不在 code/ 下留 __pycache__（跑批期禁止动 code/）

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

SCHEMA_VERSION = "dequant-probe/1.0"

#: 侦察报告 §7.1 打印的关键词表（顺序即输出顺序）
KEYWORDS: tuple[str, ...] = ("上回", "上次", "想起", "半指", "第三格")

#: 与 `code/life/agent.py::DEQUANT_LEXICON` 同口径的**字面黑名单**（用于分维度细看）
LEXICON: tuple[str, ...] = (
    "半指", "一指", "两指", "三指", "第三格", "第二格", "第一格",
    "半勺", "三钱", "半袋", "半日", "上回", "上次", "上月",
)

#: 数字+度量词遮蔽（与 `code/life/agent.py::_DEQ_NUM_RE` 同口径）
_NUM_RE = re.compile(
    r"(?:第[一二三四五六七八九十0-9]+[格层遍回步天年]"
    r"|[一二两三四五六七八九十半几0-9]+(?:指|勺|寸|钱|文|升|斗|斤|尺|袋|日|天|年))"
)
#: 标点/空白（与 `life/anti_repeat.py::normalize` 同一套标点集合）
_PUNCT_RE = re.compile(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)（）\[\]【】]")

#: 自证阈值（报告 §7.1 的落盘数字；单位：百分点）
BASELINE_PCT = {"上回": 79.8, "第三格": 29.8, "半指": 23.7}
BASELINE_TOL_PP = 0.4


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_bodies(log: Path) -> tuple[list[str], Counter]:
    """抽取全部 `MSG_*` 正文（按文件顺序，可复现）。"""
    bodies: list[str] = []
    by_type: Counter = Counter()
    with open(log, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = str(d.get("type") or "")
            if not t.startswith("MSG_"):
                continue
            body = ((d.get("payload") or {}).get("body") or "").strip()
            bodies.append(body)
            by_type[t] += 1
    return bodies, by_type


def pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def skeleton(body: str) -> str:
    """骨架：字面黑名单词与数字量词 → `#`、标点空白删光，取前 16 字。

    与 `code/life/agent.py::dequant_skeleton` **同口径**（差别只有一处：
    离线器拿不到本 run 的人名表，故不遮人名 ⇒ 这里的重复度是**上界**，比线上 guard 更宽）。
    """
    s = body or ""
    for w in LEXICON:
        s = s.replace(w, "#")
    return _PUNCT_RE.sub("", _NUM_RE.sub("#", s))[:16]


def probe(bodies: list[str], by_type: Counter, top_n: int = 5) -> dict:
    n = len(bodies)
    kw = {}
    for k in KEYWORDS:
        c = sum(1 for b in bodies if k in b)
        kw[k] = {"count": c, "pct": pct(c, n)}
    lex = {}
    for k in LEXICON:
        c = sum(1 for b in bodies if k in b)
        lex[k] = {"count": c, "pct": pct(c, n)}
    head6 = Counter(b[:6] for b in bodies)
    top_heads = [{"head6": h, "count": c}
                 for h, c in sorted(head6.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]]
    # 首 6 字「（把…往…」骨架占比：报告 §7.1 病灶③的量化口径
    paren_toput = sum(1 for b in bodies if b.startswith("（") and "往" in b[:12])
    # 句式骨架重复度（同一骨架出现次数 ≥2 的消息占比；只在单批内可比）
    skel = Counter(skeleton(b) for b in bodies)
    skel_dup = sum(c for s, c in skel.items() if c >= 2 and s)
    return {
        "schema": SCHEMA_VERSION,
        "n_msg": n,
        "msg_by_type": dict(sorted(by_type.items())),
        "keywords": kw,
        "lexicon": lex,
        "head6_top": top_heads,
        "paren_ba_wang_msgs": {"count": paren_toput, "pct": pct(paren_toput, n)},
        "skeleton_dup": {"count": skel_dup, "pct": pct(skel_dup, n),
                         "distinct_skeletons": len(skel)},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DEQUANT 维度离线度量（只读）")
    ap.add_argument("--log", required=True, help="run.jsonl 路径")
    ap.add_argument("--out", default="", help="输出 JSON 路径（缺省打到 stdout）")
    ap.add_argument("--top-n", type=int, default=5, help="首 6 字模板 TopN（默认 5）")
    ap.add_argument("--expect-baseline", action="store_true",
                    help="自检：必须复算出报告 §7.1 的 79.8/29.8/23.7（±0.4pp）")
    ap.add_argument("--no-timestamp", action="store_true", help="不写 generated_at")
    args = ap.parse_args(argv)

    log = Path(args.log)
    if not log.exists():
        print(f"[dequant-probe] 日志不存在: {log}", file=sys.stderr)
        return 2
    bodies, by_type = load_bodies(log)
    if not bodies:
        print(f"[dequant-probe] 无 MSG_* 事件: {log}", file=sys.stderr)
        return 2

    res = probe(bodies, by_type, top_n=args.top_n)
    res["source"] = {"log": str(log), "log_sha256": sha256_file(log)}
    res["cmd"] = f"python3 tools/metrics/dequant_probe.py --log {log}"
    if not args.no_timestamp:
        import datetime
        res["generated_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    ok = True
    if args.expect_baseline:
        checks = {}
        for k, want in BASELINE_PCT.items():
            got = res["keywords"][k]["pct"]
            delta = round(got - want, 1)
            checks[k] = {"expect_pct": want, "got_pct": got, "delta_pp": delta,
                         "ok": abs(delta) <= BASELINE_TOL_PP}
            ok = ok and checks[k]["ok"]
        res["self_check"] = {"tolerance_pp": BASELINE_TOL_PP, "checks": checks, "ok": ok}

    text = json.dumps(res, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"[dequant-probe] wrote {out}")
    else:
        print(text)

    if args.expect_baseline and not ok:
        print("[dequant-probe] 自检失败：与报告 §7.1 基线不符（口径漂移）", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
