#!/usr/bin/env python3
"""F-4「误会与和解」修复闭环 · 零跑批复算锚点（R13 / 2026-10-21）。

用途
----
在花任何 LLM 钱之前，把「张力事件之后有没有发生过和解」量化成可复算的硬事实。
只读已入库的 run.jsonl，不改 code/、不起批、不写世界。

口径（**镜像 tools/d5/dialogue_metrics.py，不发明新规则**）
-----------------------------------------------------------
1. 官方读数：直接 import tools/d5/dialogue_metrics.py 调 `compute()`，
   取 `F-4_tension_repair` 与 `L-13_token_leak` 两项（与报告族同一实现）。
2. 逐事件明细：用同一 mixed 线程分组（dm 按无序对 / public 按 day / group 按 group_id+day）
   与同一极性函数（emotion_lexicon.txt 正负词计数多者胜）复算：
       张力 = 相邻两句极性相反 或 当前句极性为负
       闭环 = 其后的 **8 条**同线程消息内出现 repair_lexicon.txt 任一词
   并要求明细张力条数 == 官方 `tension_events`（不等则显式报 MISMATCH，不静默）。
3. `dialogue_rift` 字段：扫描原始记录的 payload 键，统计命中条数
   （code/life/dialogue_repair.py 的结构化信号；默认关闭时应为 0）。
4. L-13：`ctx.topic` 原字符串直接出现在 body 的消息，列出具体串 + 所属事件类型。

用法
----
  cd code 前缀不需要；脚本按仓库根解析路径：
  python3 tools/f4/f4_anchor_recompute.py \
      --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
      --run on=v2/evidence/run_f6_on_n16r60_seed42/run.jsonl \
      --run dequp=v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl \
      --out-json v2/evidence/f4_anchor_recompute.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D5 = os.path.join(REPO, "tools", "d5", "dialogue_metrics.py")


def load_d5():
    spec = importlib.util.spec_from_file_location("dialogue_metrics", D5)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def sha8(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def load_words(path: str) -> list:
    if not os.path.exists(path):
        return []
    out = []
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            out.append(ln)
    return out


def load_emotion(path: str) -> dict:
    emo = {}
    for ln in load_words(path):
        parts = ln.split()
        if len(parts) >= 2:
            try:
                emo[" ".join(parts[1:])] = int(parts[0])
            except ValueError:
                continue
    return emo


def mixed_key(m: dict) -> str:
    """与 dialogue_metrics.compute() 内 mixed_key 逐字一致（dm 无序对/public 按 day/group 按 place）。"""
    if m.get("thread_id"):
        return "m:T|%s" % m["thread_id"]
    if m["channel"] == "dm":
        k = "-".join(sorted({str(m["from"]), str(m["to"])}))
    elif m["channel"] == "public":
        k = "-"
    else:
        k = str(m.get("place") or "-")
    return "m:%s|%s|%s" % (m["day"], m["channel"], k)


def analyze(label: str, log_path: str, d5, emotion: dict, repair: list, gap: int = 8) -> dict:
    recs, parse = d5.read_run(log_path)
    msgs = d5.extract_messages(recs)
    if not msgs:
        raise SystemExit(f"[FAIL] {label}: 没有 MSG 事件")

    lexicon = load_words(os.path.join(REPO, "tools/d5/backref_lexicon.txt"))
    tmpl_raw = load_words(os.path.join(REPO, "tools/d5/template_patterns.txt"))
    import re
    templates = [re.compile(t) for t in tmpl_raw if not t.startswith("#")]
    names, pinfo = d5.load_personas(os.path.join(REPO, "code/config/personas.json"))
    extra = {
        "events": recs,
        "emotion": emotion,
        "repair": repair,
        "timeref": load_words(os.path.join(REPO, "tools/d5/timeref_lexicon.txt")),
        "task_tags": load_words(os.path.join(REPO, "tools/d5/task_tags.txt")),
    }
    official = d5.compute(msgs, lexicon, templates, names, extra)
    f4 = official["F-4_tension_repair"]
    l13 = official["L-13_token_leak"]

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
        threads[mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))

    events = []
    n_neg_msgs = n_repair_msgs = 0
    for m in msgs:
        if polarity(m["body"]) < 0:
            n_neg_msgs += 1
        if any(w in m["body"] for w in repair):
            n_repair_msgs += 1

    for key in sorted(threads):
        th = threads[key]
        for i in range(1, len(th)):
            prev, cur = th[i - 1], th[i]
            conflict = (polarity(prev["body"]) * polarity(cur["body"]) < 0) or polarity(cur["body"]) < 0
            if not conflict:
                continue
            hit = None
            for j in range(i + 1, min(i + 1 + gap, len(th))):
                words = [w for w in repair if w in th[j]["body"]]
                if words:
                    hit = {"seq": th[j]["seq"], "lag": j - i, "words": words,
                           "event_type": th[j]["event_type"], "body": th[j]["body"][:80]}
                    break
            events.append({
                "thread": key,
                "prev_seq": prev["seq"], "cur_seq": cur["seq"],
                "prev_type": prev["event_type"], "cur_type": cur["event_type"],
                "topic": cur.get("ctx_topic") or prev.get("ctx_topic"),
                "round": cur.get("round"),
                "prev_body": (prev["body"] or "")[:80],
                "cur_body": (cur["body"] or "")[:80],
                "repaired": hit is not None,
                "repair": hit,
            })

    # dialogue_rift 字段命中（原始 payload 扫描；含嵌套 payload，用 json 串兜底）
    rift_hits = 0
    rift_routes = Counter()
    for r in recs:
        p = r.get("payload") or {}
        if isinstance(p, dict) and "dialogue_rift" in p:
            rift_hits += 1
            rift_routes[(p.get("dialogue_rift") or {}).get("route")] += 1

    by_type = Counter(e["cur_type"] for e in events)
    by_type_repaired = Counter(e["cur_type"] for e in events if e["repaired"])
    by_topic = Counter(str(e["topic"]) for e in events)
    by_topic_repaired = Counter(str(e["topic"]) for e in events if e["repaired"])

    leak_rows = []
    for m in msgs:
        t = m.get("ctx_topic")
        if t and t in (m.get("body") or ""):
            leak_rows.append({
                "seq": m["seq"], "event_type": m["event_type"],
                "topic": t, "body": (m["body"] or "")[:100],
            })

    return {
        "label": label,
        "log": os.path.relpath(log_path, REPO),
        "log_sha256": d5.sha256_file(log_path),
        "log_sha8": sha8(log_path),
        "n_events": len(recs),
        "n_messages": len(msgs),
        "n_threads_mixed": len(threads),
        "n_neg_msgs": n_neg_msgs,
        "n_repair_msgs": n_repair_msgs,
        "official_F4": f4,
        "official_L13": l13,
        "recomputed": {
            "tension_events": len(events),
            "repaired": sum(1 for e in events if e["repaired"]),
            "match_official": (len(events) == f4["tension_events"]
                               and sum(1 for e in events if e["repaired"]) == f4["repaired"]),
        },
        "dialogue_rift_field_hits": rift_hits,
        "dialogue_rift_routes": dict(rift_routes),
        "by_event_type": {k: {"tension": v, "repaired": by_type_repaired.get(k, 0)}
                          for k, v in sorted(by_type.items())},
        "by_topic": {k: {"tension": v, "repaired": by_topic_repaired.get(k, 0)}
                     for k, v in sorted(by_topic.items())},
        "events": events,
        "l13_leaks": leak_rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, metavar="LABEL=PATH")
    ap.add_argument("--gap", type=int, default=8)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args(argv)

    d5 = load_d5()
    emotion = load_emotion(os.path.join(REPO, "tools/d5/emotion_lexicon.txt"))
    repair = load_words(os.path.join(REPO, "tools/d5/repair_lexicon.txt"))

    arms = []
    for spec in args.run:
        label, _, rel = spec.partition("=")
        path = rel if os.path.isabs(rel) else os.path.join(REPO, rel)
        arms.append(analyze(label, path, d5, emotion, repair, gap=args.gap))

    payload = {
        "schema": "f4-anchor/1",
        "generated_at_utc": None,
        "repo_head": os.popen("git -C %s rev-parse HEAD" % REPO).read().strip(),
        "config_dialogue_repair": json.load(open(os.path.join(REPO, "code/config/dialogue_repair.json"))),
        "repair_lexicon": repair,
        "gap_msgs": args.gap,
        "arms": arms,
    }
    txt = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True)
    if args.out_json:
        out = args.out_json if os.path.isabs(args.out_json) else os.path.join(REPO, args.out_json)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(txt + "\n")
        print("written:", out)

    print("\n## 每臂读数（官方实现 + 明细复算一致性）")
    print("| arm | sha8 | MSG | mixed线程 | 张力(官方) | 修复(官方) | 明细张力 | 明细修复 | 一致 | dialogue_rift 命中 | L-13 n |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for a in arms:
        print("| %s | %s | %d | %d | %d | %d | %d | %d | %s | %d | %d |" % (
            a["label"], a["log_sha8"], a["n_messages"], a["n_threads_mixed"],
            a["official_F4"]["tension_events"], a["official_F4"]["repaired"],
            a["recomputed"]["tension_events"], a["recomputed"]["repaired"],
            "OK" if a["recomputed"]["match_official"] else "MISMATCH",
            a["dialogue_rift_field_hits"], a["official_L13"]["n"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
