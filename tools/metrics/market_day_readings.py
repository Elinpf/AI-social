#!/usr/bin/env python3
"""market_day_readings.py —— market-day 臂（CYCLE-44）**只读**读数器（零 LLM）。

设计纪律（对齐仓库既有读数器：tools/metrics/weather_readings.py、v2/evidence/r37_readings.py）：
  - **只读** `run.jsonl`（+ 冻结词表），不 import `code/`、不写 run 目录、不改任何运行时源码；
  - 判据口径**写死在代码里**并有 `LEXICON_VERSION`，任何改动必须先走预登记 Amendment；
  - 输出**成组**读数（主判据 + 探针 + 极性 + 去重），不做任何"提升/改善"式措辞。

三档口径（T1b 审计裁决：原式 69.2% 假阳性，已否决）：
  - R_A 显式日历档  `集日|逢三|赶集日|逢集日`            → 只作「注入被采纳」探针
  - R_B 时间邻接档  `(今儿|今天|今早|…|逢三) ⇄ 集市词 ≤6 字` → **主判据**
  - R_C 宽档（= 已被否决的原式）                          → 仅作召回探索，不作判据

用法（在仓库根，或任意目录，脚本只读文件）：
  # 单臂
  python3 tools/metrics/market_day_readings.py --arm off=<off>/run.jsonl --json out_off.json
  # 两臂对照（主判据 Δ + 两臂 Wilson CI + 判据表）
  python3 tools/metrics/market_day_readings.py \
      --arm off=<off>/run.jsonl --arm on=<on>/run.jsonl --json out_pair.json
  # 只看集日子集（默认 --market-every 3 --market-offset 0，即 day%3==0）
  ... --subset market      # 亦支持 --subset all

退出码：0 正常；2 参数/文件错；3 词表自检失败。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

LEXICON_VERSION = "market-day-lexicon/R-B-v1 (T1b audit 2026-10-31)"

# ---------------------------------------------------------------- 集市词 / 时间词
MK = r"(?:赶集|逢集|集日|集上|集市|市集|赶场)"
TW = (r"(?:今儿|今天|今日|今早|今晨|今午|今晚|当日|当天|当天里|明天|明日|明儿|"
      r"后日|后天|逢三|初三|初六|初九|这个日子|这日子)")
# 窗口 ≤6 字、不跨句读（。！？；换行）
R_A = re.compile(r"集日|逢三|赶集日|逢集日")
R_B = re.compile(rf"{TW}[^。！？；\n]{{0,6}}{MK}|{MK}[^。！？；\n]{{0,6}}{TW}")
R_C = re.compile(r"赶集|逢集|集市|集上|摆摊|卖货|买(点|些|个)")

# ---------------------------------------------------------------- 负例表（T1b §3.1）
NEG_IDIOM = re.compile(r"(跟|像|似|如同)[^，。！？\n]{0,6}赶集")                    # 挤得跟赶集似的
NEG_PRICE = re.compile(r"(集上|市集|集市)(价|的价|行情|价儿)")                      # 集上价 = 市价
NEG_PAST = re.compile(r"(上回|上次|昨天|昨儿|前儿|前阵子|以前|小时候|那年|当年)")   # 回忆/传闻
NEG_ECHO = re.compile(r"(你刚说|你说的|你方才说|刚说|听你说|照你说)[^。！？\n]{0,8}" + MK)  # 回声复读
NEG_NEG = re.compile(
    rf"(不|没|别)[^。！？；\n]{{0,6}}{MK}|{MK}[^。！？；\n]{{0,6}}(不|没)(来|去|赶|摆|开)"
)
# 显式不采（T1b 裁决：任何日子都成立，纯噪声）
DROPPED_TOKENS = ["买点", "买些", "买个", "卖货"]

HARD_NEG = [("idiom", NEG_IDIOM), ("price", NEG_PRICE), ("echo", NEG_ECHO), ("past-recall", NEG_PAST)]

MSG_TYPES = {"MSG_PUBLIC", "MSG_DM", "MSG_PRIVATE", "MSG"}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson 95% 区间（与仓库其余读数器同式）。"""
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def classify(body: str) -> dict:
    """单条正文 → 口径判定。返回 hit / 口径档案 / 极性 / 剔除理由。"""
    flags = [name for name, rx in HARD_NEG if rx.search(body)]
    negated = bool(NEG_NEG.search(body))
    r_a = bool(R_A.search(body))
    r_b_raw = bool(R_B.search(body))
    r_c = bool(R_C.search(body))
    r_b = bool(r_b_raw and not flags)          # 主判据：邻接 + 非硬负例
    return {
        "hit_R_A": r_a,
        "hit_R_B_raw": r_b_raw,
        "hit_R_B": r_b,
        "hit_R_C": r_c,
        "flags": flags,
        "polarity": (-1 if negated else +1) if r_b else 0,
    }


def scan_run(path: Path, market_every: int, market_offset: int, subset: str) -> dict:
    """扫一份 run.jsonl，按口径累计。"""
    acc = {
        "msgs": 0,                    # 参与分母的正文条数（已按 subset 过滤）
        "msgs_all": 0,
        "hit_R_A": 0, "hit_R_B": 0, "hit_R_B_raw": 0, "hit_R_C": 0,
        "hit_R_B_pos": 0, "hit_R_B_neg": 0,
        "flag_counts": Counter(),
        "by_day_msgs": Counter(), "by_day_hit": Counter(),
        "cells": set(), "cells_hit": set(),      # (author, day) 去重用
        "samples": [], "negatives": [],
    }
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") not in MSG_TYPES:
                continue
            p = e.get("payload") or {}
            body = p.get("body") or ""
            if not body:
                continue
            acc["msgs_all"] += 1
            day = p.get("day")
            is_market_day = (isinstance(day, int) and day % market_every == market_offset)
            if subset == "market" and not is_market_day:
                continue
            acc["msgs"] += 1
            acc["by_day_msgs"][day] += 1
            acc["cells"].add((e.get("actor"), day))
            c = classify(body)
            for key in ("hit_R_A", "hit_R_B", "hit_R_B_raw", "hit_R_C"):
                if c[key]:
                    acc[key] += 1
            if c["hit_R_B"]:
                acc["by_day_hit"][day] += 1
                acc["cells_hit"].add((e.get("actor"), day))
                acc["hit_R_B_pos" if c["polarity"] > 0 else "hit_R_B_neg"] += 1
                if len(acc["samples"]) < 40:
                    acc["samples"].append({
                        "seq": e.get("seq"), "day": day, "actor": e.get("actor"),
                        "topic": (p.get("ctx") or {}).get("topic"),
                        "msg_id": p.get("msg_id"), "msg_uid": p.get("msg_uid"),
                        "polarity": c["polarity"], "text": body,
                    })
            for fl in c["flags"]:
                acc["flag_counts"][fl] += 1
                if len(acc["negatives"]) < 40:
                    acc["negatives"].append({"flag": fl, "seq": e.get("seq"),
                                             "actor": e.get("actor"), "msg_id": p.get("msg_id"),
                                             "text": body})
    return acc


def summarize(name: str, acc: dict) -> dict:
    n = acc["msgs"]
    out = {
        "arm": name,
        "lexicon_version": LEXICON_VERSION,
        "denominator_msgs": n,
        "msgs_all": acc["msgs_all"],
        "main_R_B": {"num": acc["hit_R_B"], "den": n,
                     "rate": acc["hit_R_B"] / n if n else None,
                     "wilson95": wilson(acc["hit_R_B"], n)},
        "probe_R_A": {"num": acc["hit_R_A"], "den": n,
                      "rate": acc["hit_R_A"] / n if n else None,
                      "wilson95": wilson(acc["hit_R_A"], n)},
        "explore_R_C": {"num": acc["hit_R_C"], "den": n,
                        "rate": acc["hit_R_C"] / n if n else None},
        "narrative_R_B_raw": {"num": acc["hit_R_B_raw"], "den": n},
        "polarity": {"positive": acc["hit_R_B_pos"], "negated": acc["hit_R_B_neg"]},
        "hard_negative_flags": dict(acc["flag_counts"]),
        "dedup_cells": {"cells": len(acc["cells"]), "cells_with_hit": len(acc["cells_hit"]),
                        "rate_cell_level": (len(acc["cells_hit"]) / len(acc["cells"])
                                            if acc["cells"] else None)},
        "by_day": {str(d): {"msgs": acc["by_day_msgs"][d], "hit": acc["by_day_hit"][d]}
                   for d in sorted(acc["by_day_msgs"], key=lambda x: (x is None, x))},
        "samples_hit": acc["samples"],
        "samples_negative": acc["negatives"],
        "dropped_tokens": DROPPED_TOKENS,
    }
    return out


def compare(a: dict, b: dict) -> dict:
    """两臂对照：Δ（绝对）、两臂 Wilson、判据表（照预登记 §10 映射，不写"提升"）。"""
    ma, mb = a["main_R_B"], b["main_R_B"]
    if not (ma["den"] and mb["den"]):
        return {"verdict": "CANNOT-JUDGE（分母为 0）"}
    delta = mb["rate"] - ma["rate"]
    lo_a, hi_a = ma["wilson95"]
    lo_b, hi_b = mb["wilson95"]
    overlap = not (lo_b > hi_a or lo_a > hi_b)
    if mb["num"] == 0 and ma["num"] == 0:
        note = "两臂 R_B 命中均为 0：本轮只能报『注入未被台词采纳』，不得判机制无效。"
    elif delta >= 0.05 and not overlap:
        note = "达 +5pp 且 CI 不重叠 ⇒ 判『成立（仅限本构念/本规模）』。"
    elif delta >= 0.05 and overlap:
        note = "方向达标但 CI 重叠 ⇒ 判『不可分（统计不足）』，不得写成立。"
    elif delta > 0:
        note = "Δ<+5pp ⇒ 判『未达阈值』。"
    else:
        note = "Δ≤0 ⇒ 判『未达阈值（方向为负）』。"
    return {
        "delta_pp": round(delta * 100, 2),
        "arm_off_rate_pct": round(ma["rate"] * 100, 2),
        "arm_on_rate_pct": round(mb["rate"] * 100, 2),
        "off_wilson95_pct": [round(lo_a * 100, 2), round(hi_a * 100, 2)],
        "on_wilson95_pct": [round(lo_b * 100, 2), round(hi_b * 100, 2)],
        "ci_overlap": overlap,
        "verdict": note,
        "reading_rule": "Δ 与 CI 只描述『集日提及率』之差，不描述生活气息、不描述行为。",
    }


def selftest() -> int:
    """词表自检：用 T1b 审计的 13 条真语料命中断言 R_B 只放 4 条。"""
    cases = [
        ("（拿围裙角蹭了蹭手）我这会儿得去集上把最后两筐青椒清了", False),          # 纯地点
        ("这两天铺子前头挤得跟赶集似的", False),                                   # 比喻
        ("她上回为半垄菜地能追到集上骂三条街", False),                             # 回忆
        ('你刚说"赶集"，我倒想起桂香家那口子', False),                             # 回声
        ("布角还沾着今早集上的泥点子", True),                                       # 邻接
        ("今早那趟集上碰见你三叔", True),                                           # 邻接
        ("那两把葱我按集上价给你", False),                                          # 市价
        ("他娘今儿又没来集上", True),                                               # 邻接（极性 -1）
        ("我刚从集上拎了半袋新茶回来", False),                                      # 纯地点
        ("买点盐，回头再买些菜", False),                                            # 已剔除 token
        ("明天逢集，得早点去占位", True),                                           # 日历词
    ]
    bad = 0
    for text, expect in cases:
        got = classify(text)["hit_R_B"]
        if got != expect:
            print(f"  SELFTEST FAIL: expect={expect} got={got} :: {text}", file=sys.stderr)
            bad += 1
    print(f"selftest: {len(cases) - bad}/{len(cases)} passed ({LEXICON_VERSION})")
    return 0 if bad == 0 else 3


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="market-day 臂只读读数器（零 LLM）")
    ap.add_argument("--arm", action="append", default=[],
                    help="name=path/to/run.jsonl，可给两次（如 off=… on=…）")
    ap.add_argument("--json", dest="json_out", default=None, help="结果落盘路径")
    ap.add_argument("--subset", choices=["market", "all"], default="market",
                    help="market=只取集日回合（day%%market_every==market_offset，默认 day%%3==0）")
    ap.add_argument("--market-every", type=int, default=3)
    ap.add_argument("--market-offset", type=int, default=0)
    ap.add_argument("--max-samples", type=int, default=40)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.arm:
        ap.error("至少给一个 --arm name=path")

    arms, order = {}, []
    for spec in args.arm:
        if "=" not in spec:
            ap.error(f"--arm 需 name=path 形式：{spec}")
        name, path = spec.split("=", 1)
        p = Path(path)
        if not p.exists():
            print(f"FATAL: 找不到 {p}", file=sys.stderr)
            return 2
        acc = scan_run(p, args.market_every, args.market_offset, args.subset)
        acc["samples"] = acc["samples"][: args.max_samples]
        acc["negatives"] = acc["negatives"][: args.max_samples]
        arms[name] = summarize(name, acc)
        order.append(name)

    result = {
        "lexicon_version": LEXICON_VERSION,
        "subset": {"mode": args.subset, "market_every": args.market_every,
                   "market_offset": args.market_offset,
                   "rule": "集日 = day % market_every == market_offset"},
        "arms": arms,
    }
    if len(order) == 2:
        result["pair"] = compare(arms[order[0]], arms[order[1]])
        result["pair"]["pair_note"] = f"{order[0]} → {order[1]}"

    text = json.dumps(result, ensure_ascii=False, indent=1, default=str)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
