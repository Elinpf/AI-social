#!/usr/bin/env python3
"""R11 · M-1 去自我复读判定器（只读 run.jsonl；判据与 R11 §3.6 逐字一致）

用途
----
把 `tools/f6/f6_metrics.py` 的 M-1（跨天 6-gram 重合，未去重）按 R11 §3.6 的
**主口径**（同一说话人 且 共享 6-gram >= 3 ⇒ 剔除）与**严判据**
（同一说话人 且 覆盖率 |A∩B|/|A| >= 0.5 ⇒ 剔除）拆成三档：

    M-1          未去重（上界 / 被污染读数）
    M-1'         主口径（本轮唯一可用读数）
    M-1'_strict  去重下界（只剔近乎逐字复读）

判据先写死、不可通过命令行调阈值（改阈值必须先进预注册，R11 §3.6）。

用法
----
    python3 tools/f6/f6_m1_dedup.py --run v2/evidence/run_f6_off_n16r60_seed42/run.jsonl
    python3 tools/f6/f6_m1_dedup.py --run v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --json out.json

输入：`<out-dir>/run.jsonl`（被 .gitignore 忽略，不入库）；零 LLM 调用、零网络。
输出：stdout 命中明细 + 三档计数；`--json` 另存机器可读结果。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict

MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")
_PUNCT = r"[\s，。！？、；：「」（）,.!?;:()\"'“”‘’…—-]"
NGRAM = 6
SHARED_MIN = 3      # 主口径阈值（R11 §3.6 冻结）
COVER_MIN = 0.5     # 严判据阈值（R11 §3.6 冻结）


def ngrams(text: str, n: int = NGRAM) -> set[str]:
    t = re.sub(_PUNCT, "", text or "")
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def thread_key(m: dict) -> str:
    if m["tid"]:
        return "T:" + str(m["tid"])
    if m["type"] == "MSG_DM":
        return "D:" + "|".join(sorted([str(m["frm"]), str(m["to"])]))
    if m["type"] == "MSG_GROUP":
        return "G:" + str(m["gid"])
    return "P:" + str(m["frm"])


def load(path: str) -> list[dict]:
    msgs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("type") not in MSG_TYPES:
                continue
            p = r.get("payload") or {}
            msgs.append(dict(
                seq=r.get("seq"), round=r.get("round"), day=p.get("day"),
                type=r["type"], frm=p.get("from"), to=p.get("to"),
                gid=p.get("group_id"), body=(p.get("body") or "").strip(),
                tid=p.get("thread_id"),
            ))
    return msgs


def main() -> int:
    ap = argparse.ArgumentParser(description="R11 M-1 去自我复读判定器（判据冻结，不可调阈值）")
    ap.add_argument("--run", required=True, help="run.jsonl 路径")
    ap.add_argument("--json", default=None, help="可选：机器可读结果输出路径")
    ap.add_argument("--quiet", action="store_true", help="只输出三档计数，不打印命中明细")
    a = ap.parse_args()

    msgs = load(a.run)
    threads = defaultdict(list)
    for m in msgs:
        threads[thread_key(m)].append(m)

    hit = den = 0
    drop_main = drop_strict = 0
    rows = []
    for key, grp in threads.items():
        for i, m in enumerate(grp):
            if m["day"] is None or m["day"] < 1:
                continue
            A = ngrams(m["body"])
            earlier = [x for x in grp[:i] if x["day"] is not None and x["day"] < m["day"]]
            if not earlier:
                continue
            den += 1
            hits = [x for x in earlier if A & ngrams(x["body"])]
            if not hits:
                continue
            hit += 1
            x = hits[0]
            B = ngrams(x["body"])
            shared = len(A & B)
            cov = (shared / len(A)) if A else 0.0
            same = m["frm"] == x["frm"]
            main_drop = bool(same and shared >= SHARED_MIN)
            strict_drop = bool(same and cov >= COVER_MIN)
            drop_main += main_drop
            drop_strict += strict_drop
            rows.append(dict(
                seq=m["seq"], round=m["round"], day=m["day"], speaker=m["frm"],
                earlier_seq=x["seq"], earlier_day=x["day"], earlier_speaker=x["frm"],
                thread=key, shared_6gram=shared, covA=round(cov, 3),
                same_speaker=same, drop_main=main_drop, drop_strict=strict_drop,
                body=m["body"], earlier_body=x["body"],
            ))

    if not a.quiet:
        for r in rows:
            print("hit=%s(%s) day=%s round=%s thread=%s" %
                  (r["seq"], r["speaker"], r["day"], r["round"], r["thread"]))
            print("  body:", r["body"])
            print("  earlier=%s(%s) day=%s body=%s" %
                  (r["earlier_seq"], r["earlier_speaker"], r["earlier_day"], r["earlier_body"]))
            print("  same_speaker=%s shared6=%d covA=%.3f drop_main=%s drop_strict=%s" %
                  (r["same_speaker"], r["shared_6gram"], r["covA"], r["drop_main"], r["drop_strict"]))

    result = {
        "run": a.run,
        "denominator": den,
        "M-1": f"{hit}/{den}",
        "M-1'": f"{hit - drop_main}/{den}",
        "M-1'_strict": f"{hit - drop_strict}/{den}",
        "hits": hit, "drop_main": drop_main, "drop_strict": drop_strict,
        "thresholds": {"ngram": NGRAM, "shared_min": SHARED_MIN, "cover_min": COVER_MIN},
        "rows": rows,
    }
    print("M-1  = %d/%d" % (hit, den))
    print("M-1' (main, same_speaker & shared6>=%d)   = %d/%d" % (SHARED_MIN, hit - drop_main, den))
    print("M-1'_strict (same_speaker & covA>=%.1f)   = %d/%d" % (COVER_MIN, hit - drop_strict, den))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print("written:", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
