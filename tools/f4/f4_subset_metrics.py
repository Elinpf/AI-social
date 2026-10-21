#!/usr/bin/env python3
"""F-4 双口径度量 + 可审计配对表（R13；零跑批，只读日志；**不改 tools/d5**）。

为什么要双口径
--------------
R4 起沿用的 F-4 口径（`tools/d5/dialogue_metrics.py`）是**词表张力 + 8 条内修复词**：
  * 张力分子噪声大：off 基线 22 条里 19 条只命中 `怕/累/疼` 这类自述状态词（anchor §5.3）；
  * 修复分子精度低：`我懂` 这类附和词也被算成「和解」（anchor §4.3）。
改历史口径会让 R1–R12 不可比，所以本模块**不动 d5**，只并排输出两列：

  旧口径（legacy）      = 与 d5 完全一致（分母 = 全部词表张力事件）
  新口径（interpersonal）= 张力事件**必须**至少一方含「人际冲突词」（生气/烦/委屈/失望/后悔/吵/凭什么/
                          你什么意思/别这样），其余规则（8 条同线程窗口、修复词判定）逐字沿用旧口径

同时输出**可审计配对表**（R13 新信号）：把日志里 `dialogue_repair` 字段逐条列出，
并和 `rift_id` / `trigger_seq` / 收口句 `closed_seq` 对齐，做到「一条一条点开能复核」。

用法
----
  python3 tools/f4/f4_subset_metrics.py \
      --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
      --out-json v2/evidence/f4_subset_off.json
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

#: 人际冲突词（只在这里定义一次，写进预注册文件后不再改动）
INTERPERSONAL_NEG = ("生气", "烦", "委屈", "失望", "后悔", "吵", "凭什么", "你什么意思", "别这样")
#: **严格口径**排除表：anchor（`v2/evidence/f4_anchor.md` §4.3）已确认是「顺口附和、不是和解」的词。
#: 宽松口径（legacy，与 d5 一致）不做排除；严格口径在宽松基础上剔除本表 —— 两列并列输出。
AGREEMENT_ONLY = ("我懂",)
WINDOW_MSGS = 8


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
        return 1 if pos > neg else (-1 if neg > pos else 0)

    threads = defaultdict(list)
    for m in msgs:
        threads[f4a.mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))

    strict_words = [w for w in repair if w not in AGREEMENT_ONLY]

    def run_metric(subset: bool) -> list:
        rows = []
        for key in sorted(threads):
            th = threads[key]
            for i in range(1, len(th)):
                prev, cur = th[i - 1], th[i]
                if not ((polarity(prev["body"]) * polarity(cur["body"]) < 0)
                        or polarity(cur["body"]) < 0):
                    continue
                if subset and not any(w in (prev["body"] or "") + (cur["body"] or "")
                                      for w in INTERPERSONAL_NEG):
                    continue
                close = strict = None
                for j in range(i + 1, min(i + 1 + WINDOW_MSGS, len(th))):
                    body = th[j]["body"]
                    if close is None:
                        words = [w for w in repair if w in body]
                        if words:
                            close = {"seq": th[j]["seq"], "lag": j - i, "words": words}
                    if strict is None:
                        swords = [w for w in strict_words if w in body]
                        if swords:
                            strict = {"seq": th[j]["seq"], "lag": j - i, "words": swords}
                    if close is not None and strict is not None:
                        break
                rows.append({"thread": key, "trigger_seq": cur["seq"], "prev_seq": prev["seq"],
                             "topic": cur.get("ctx_topic"), "event_type": cur["event_type"],
                             "round": cur.get("round"), "closed": close is not None,
                             "closed_by": close,
                             "closed_strict": strict is not None, "closed_strict_by": strict})
        return rows

    legacy = run_metric(False)
    subset = run_metric(True)

    # ---- 可审计配对：日志里带 dialogue_repair 的事件（R13 新信号）
    audit = []
    for r in recs:
        p = r.get("payload") or {}
        ra = p.get("dialogue_repair") if isinstance(p, dict) else None
        if not ra:
            continue
        audit.append({"seq": r.get("seq"), "round": r.get("round"),
                      "thread": p.get("thread_id"), "topic": p.get("topic"),
                      "rift_ids": ra.get("rift_ids") or [],
                      "trigger_seqs": ra.get("trigger_seqs") or [],
                      "prompted": ra.get("prompted")})

    # 每条 rift 的收口句（同线程、其后 8 条内出现修复词；与旧口径同规则，仅用于对照）
    def closing_seq(thread: str, trigger_seq: int):
        th = threads.get(thread) or []
        idx = next((i for i, m in enumerate(th) if m["seq"] == trigger_seq), None)
        if idx is None:
            return None
        for j in range(idx + 1, min(idx + 1 + WINDOW_MSGS, len(th))):
            if any(w in th[j]["body"] for w in repair):
                return th[j]["seq"]
        return None

    # 机制配对索引：(thread, trigger_seq) -> 携带该配对的 dialogue_repair 行 seq
    pair_index = {}
    for row in audit:
        for tseq in row["trigger_seqs"]:
            pair_index.setdefault((row["thread"], tseq), []).append(row["seq"])

    # 2.1c 交叉核对：词表判定的闭环里，同线程其后是否确实存在机制配对
    def annotate(rows: list) -> list:
        for r in rows:
            r["mechanism_pairs"] = pair_index.get((r["thread"], r["trigger_seq"]), [])
            r["closed_and_paired"] = bool(r["closed"] and r["mechanism_pairs"])
            r["strict_and_paired"] = bool(r["closed_strict"] and r["mechanism_pairs"])
        return rows

    annotate(legacy)
    annotate(subset)

    for row in audit:
        row["closed_by_seq"] = [closing_seq(row["thread"], s) for s in row["trigger_seqs"]]

    return {
        "label": label, "log": os.path.relpath(log_path, REPO), "log_sha8": f4a.sha8(log_path),
        "n_messages": len(msgs), "n_threads": len(threads),
        "legacy": {
            "tension_events": len(legacy),
            "closed_events": sum(1 for r in legacy if r["closed"]),
            "closed_strict_events": sum(1 for r in legacy if r["closed_strict"]),
            "closed_and_paired_events": sum(1 for r in legacy if r["closed_and_paired"]),
            "by_topic": dict(Counter(str(r["topic"]) for r in legacy)),
            "rows": legacy,
        },
        "interpersonal": {
            "tension_events": len(subset),
            "closed_events": sum(1 for r in subset if r["closed"]),
            "closed_strict_events": sum(1 for r in subset if r["closed_strict"]),
            "closed_and_paired_events": sum(1 for r in subset if r["closed_and_paired"]),
            "by_topic": dict(Counter(str(r["topic"]) for r in subset)),
            "rows": subset,
        },
        "audit_rows": audit,
        "audit_rows_n": len(audit),
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

    payload = {"schema": "f4-subset-metrics/2",
               "interpersonal_neg": list(INTERPERSONAL_NEG),
               "agreement_only_excluded_in_strict": list(AGREEMENT_ONLY),
               "window_msgs": WINDOW_MSGS,
               "repo_head": os.popen("git -C %s rev-parse HEAD" % REPO).read().strip(),
               "arms": arms}
    if args.out_json:
        out = args.out_json if os.path.isabs(args.out_json) else os.path.join(REPO, args.out_json)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False,
                                                          indent=1, sort_keys=True) + "\n")
        print("written:", out)

    print("\n| arm | sha8 | MSG | 旧口径张力 | 旧口径闭环(宽松/严格) | 人际张力 | 人际闭环(宽松/严格) | 闭环且机制配对 | 可审计配对行 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for a in arms:
        print("| %s | %s | %d | %d | %d / %d | %d | %d / %d | 旧 %d / 人际 %d | %d |" % (
            a["label"], a["log_sha8"], a["n_messages"],
            a["legacy"]["tension_events"],
            a["legacy"]["closed_events"], a["legacy"]["closed_strict_events"],
            a["interpersonal"]["tension_events"],
            a["interpersonal"]["closed_events"], a["interpersonal"]["closed_strict_events"],
            a["legacy"]["closed_and_paired_events"],
            a["interpersonal"]["closed_and_paired_events"],
            a["audit_rows_n"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
