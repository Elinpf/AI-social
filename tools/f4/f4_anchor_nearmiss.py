#!/usr/bin/env python3
"""F-4 锚点补充：张力事件与修复词的「近失（near-miss）」距离分析（零跑批，只读日志）。

回答一个问题：闭环为 0，是因为**修复词根本不出现**，还是因为**出现了但落在 8 条窗口之外/别的线程**？

规则（与 f4_anchor_recompute.py 完全同口径）：
  * 张力事件、线程分组、极性函数均复用 f4_anchor_recompute 的实现；
  * 对每个张力事件，找**同线程内其后最近**的一条含 repair 词的消息（不设 8 条上限），记录 lag；
  * 同时给出该线程内全部 repair 消息、以及全日志 repair 消息的分布。

用法：
  python3 tools/f4/f4_anchor_nearmiss.py --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl ...
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


f4a = _load("f4_anchor_recompute", os.path.join(HERE, "f4_anchor_recompute.py"))
d5 = f4a.load_d5()


def analyze(label: str, log_path: str, emotion: dict, repair: list) -> dict:
    recs, _ = d5.read_run(log_path)
    msgs = d5.extract_messages(recs)

    def polarity(body: str) -> int:
        pos = sum(1 for w, p in emotion.items() if p > 0 and w in body)
        neg = sum(1 for w, p in emotion.items() if p < 0 and w in body)
        if pos > neg:
            return 1
        if neg > pos:
            return -1
        return 0

    threads = defaultdict(list)
    for m in msgs:
        threads[f4a.mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))

    rows = []
    for key in sorted(threads):
        th = threads[key]
        for i in range(1, len(th)):
            prev, cur = th[i - 1], th[i]
            conflict = (polarity(prev["body"]) * polarity(cur["body"]) < 0) or polarity(cur["body"]) < 0
            if not conflict:
                continue
            near = None
            for j in range(i + 1, len(th)):
                words = [w for w in repair if w in th[j]["body"]]
                if words:
                    near = {"seq": th[j]["seq"], "lag": j - i, "words": words,
                            "body": th[j]["body"][:80], "event_type": th[j]["event_type"]}
                    break
            rows.append({"thread": key, "cur_seq": cur["seq"], "topic": cur.get("ctx_topic"),
                         "cur_type": cur["event_type"], "in8": bool(near and near["lag"] <= 8),
                         "nearest_after": near})

    lag_dist = Counter(
        ("<=8" if r["in8"] else ("9-16" if r["nearest_after"] and r["nearest_after"]["lag"] <= 16
                                 else ("17+" if r["nearest_after"] else "none")))
        for r in rows
    )
    # 全日志 repair 消息
    repair_msgs = []
    for m in msgs:
        words = [w for w in repair if w in m["body"]]
        if words:
            repair_msgs.append({"seq": m["seq"], "thread": f4a.mixed_key(m), "words": words,
                                "event_type": m["event_type"], "body": (m["body"] or "")[:80]})
    return {
        "label": label, "log": os.path.relpath(log_path, REPO), "log_sha8": f4a.sha8(log_path),
        "n_messages": len(msgs),
        "tension_events": len(rows),
        "repaired_in_8": sum(1 for r in rows if r["in8"]),
        "nearest_lag_dist": dict(lag_dist),
        "n_repair_msgs_total": len(repair_msgs),
        "repair_words_counter": dict(Counter(w for r in repair_msgs for w in r["words"])),
        "repair_msg_event_types": dict(Counter(r["event_type"] for r in repair_msgs)),
        "repair_threads": len({r["thread"] for r in repair_msgs}),
        "rows": rows,
        "repair_msgs": repair_msgs,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, metavar="LABEL=PATH")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args(argv)

    emotion = f4a.load_emotion(os.path.join(REPO, "tools/d5/emotion_lexicon.txt"))
    repair = f4a.load_words(os.path.join(REPO, "tools/d5/repair_lexicon.txt"))
    arms = []
    for spec in args.run:
        label, _, rel = spec.partition("=")
        path = rel if os.path.isabs(rel) else os.path.join(REPO, rel)
        arms.append(analyze(label, path, emotion, repair))

    payload = {"schema": "f4-anchor-nearmiss/1",
               "repair_lexicon": repair,
               "repo_head": os.popen("git -C %s rev-parse HEAD" % REPO).read().strip(),
               "arms": arms}
    txt = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True)
    if args.out_json:
        out = args.out_json if os.path.isabs(args.out_json) else os.path.join(REPO, args.out_json)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        open(out, "w", encoding="utf-8").write(txt + "\n")
        print("written:", out)

    print("\n| arm | sha8 | MSG | 张力 | 8条内修复 | 最近修复 lag 分布 | 全日志修复词消息数 | 修复词计数 |")
    print("|---|---|---|---|---|---|---|---|")
    for a in arms:
        print("| %s | %s | %d | %d | %d | %s | %d | %s |" % (
            a["label"], a["log_sha8"], a["n_messages"], a["tension_events"],
            a["repaired_in_8"], json.dumps(a["nearest_lag_dist"], ensure_ascii=False),
            a["n_repair_msgs_total"], json.dumps(a["repair_words_counter"], ensure_ascii=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
