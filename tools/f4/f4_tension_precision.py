#!/usr/bin/env python3
"""F-4 锚点补充：张力检测的**精度**初查（零跑批，只读日志）。

词表张力判据是子串匹配（`emotion_lexicon.txt`），`怕 / 累 / 烦 / 苦` 这类**自述状态词**
在口头语里极常见，会把「我怕是要把您当包子啃啦」这种玩笑也判成张力。
本脚本不改变 F-4 口径（分母仍是词表层定义），只把每个张力事件命中的负向词列出来，
并按「人际冲突词 / 自述状态词」二分，供报告如实披露**分子噪声**，避免把 0 闭环直接读成机制失败。

用法：
  python3 tools/f4/f4_tension_precision.py --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl ...
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

#: 指向**人与人之间**的负向词（真冲突信号）
INTERPERSONAL = {"生气", "烦", "委屈", "失望", "后悔", "吵", "凭什么", "你什么意思", "别这样"}
#: 指向**自己状态**的负向词（口头语高频，容易假阳性）
SELF_STATE = {"难过", "难受", "累", "怕", "担心", "算了", "倒霉", "疼", "苦"}


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


f4a = _load("f4_anchor_recompute", os.path.join(HERE, "f4_anchor_recompute.py"))
d5 = f4a.load_d5()


def analyze(label: str, log_path: str, emotion: dict) -> dict:
    recs, _ = d5.read_run(log_path)
    msgs = d5.extract_messages(recs)

    def words_in(body: str, bucket: set) -> list:
        return [w for w in sorted(bucket) if w in (body or "")]

    def polarity(body: str) -> int:
        pos = sum(1 for w, p in emotion.items() if p > 0 and w in body)
        neg = sum(1 for w, p in emotion.items() if p < 0 and w in body)
        return 1 if pos > neg else (-1 if neg > pos else 0)

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
            ip = words_in(cur["body"], INTERPERSONAL) + words_in(prev["body"], INTERPERSONAL)
            ss = words_in(cur["body"], SELF_STATE) + words_in(prev["body"], SELF_STATE)
            rows.append({"thread": key, "cur_seq": cur["seq"],
                         "topic": cur.get("ctx_topic"),
                         "interpersonal_words": ip, "self_state_words": ss,
                         "cur_body": cur["body"][:60]})
    n_ip = sum(1 for r in rows if r["interpersonal_words"])
    return {
        "label": label, "log_sha8": f4a.sha8(log_path),
        "tension_events": len(rows),
        "with_interpersonal_word": n_ip,
        "only_self_state_word": sum(1 for r in rows if not r["interpersonal_words"]),
        "self_state_word_counter": dict(Counter(w for r in rows for w in set(r["self_state_words"]))),
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, metavar="LABEL=PATH")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args(argv)
    emotion = f4a.load_emotion(os.path.join(REPO, "tools/d5/emotion_lexicon.txt"))
    arms = []
    for spec in args.run:
        label, _, rel = spec.partition("=")
        path = rel if os.path.isabs(rel) else os.path.join(REPO, rel)
        arms.append(analyze(label, path, emotion))
    payload = {"schema": "f4-tension-precision/1", "interpersonal": sorted(INTERPERSONAL),
               "self_state": sorted(SELF_STATE), "arms": arms}
    if args.out_json:
        out = args.out_json if os.path.isabs(args.out_json) else os.path.join(REPO, args.out_json)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1,
                                                          sort_keys=True) + "\n")
        print("written:", out)
    print("\n| arm | sha8 | 张力事件 | 含人际冲突词 | 仅自述状态词 | 自述词分布 |")
    print("|---|---|---|---|---|---|")
    for a in arms:
        print("| %s | %s | %d | %d | %d | %s |" % (
            a["label"], a["log_sha8"], a["tension_events"], a["with_interpersonal_word"],
            a["only_self_state_word"], json.dumps(a["self_state_word_counter"], ensure_ascii=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
