#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A0 结构生效体检（S1–S12）—— 只读、零 LLM、可复算

作者：sim-engineer ｜ 口径来源：`v2/evidence/D4-A0-expected-structure-checklist.md`（逐项 S1–S12）
用途：A0（或任意 run）日志到手后，**先**判「结构改造是否真生效」，再决定是否值得算全套指标。
纪律（照抄清单第 5 行）：**"没有变化"优先解释为"结构没生效"，而不是"效果弱"**。

用法：
  python3 experiments/gossip-third-party/a0_structure_check.py \
      --run A0=v2/evidence/run_d2_after_n16_seed42/run.jsonl \
      --baseline v0anchor=v2/evidence/run_d2_before_n16_seed42/run.jsonl \
      --out-json experiments/gossip-third-party/a0_structure_check.json

线程口径：有 `payload.thread_id` ⇒ explicit（按 thread_id 分组）；否则 legacy
          （DM={day,发送者,收件人对}，GROUP={day,group_id}，PUBLIC={day,public}）。

每项输出：值 + 分母 + 与基线的方向 + 清单里的期望量级 + 自动结论（pass/warn/fail）。
**本脚本不判"自然度"，只判"结构是否生效"。**
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
CHANNEL = {"MSG_DM": "dm", "MSG_PUBLIC": "public", "MSG_GROUP": "group"}
AGENT_ID_RE = re.compile(r"P\d{3}(?!\d)")
PAREN_OPEN = ("（", "(")
BACKREF_LEXICON = ["你刚", "刚才", "你说", "你说过", "那", "这事儿", "这事", "这个",
                   "上回", "昨天", "也是", "对啊", "可不是", "嗯", "对", "是嘛"]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NAMES = REPO_ROOT / "code" / "config" / "personas.json"


def load_names(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for p in d.get("personas", []):
        pid = str(p.get("persona_id") or "")
        nm = str(p.get("display_name") or "").split("·")[-1].strip()
        if pid and nm:
            out[pid] = nm
    return out


def load(path: str) -> dict:
    msgs = []
    llm = Counter()
    llm_cached = 0
    providers = Counter()
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        t = e.get("type")
        p = e.get("payload") or {}
        if t == "LLM_CALL":
            llm[str(p.get("purpose"))] += 1
            if p.get("cached"):
                llm_cached += 1
            if p.get("provider"):
                providers[str(p["provider"])] += 1
            continue
        if t not in MSG_TYPES:
            continue
        msgs.append({
            "seq": e.get("seq"), "round": e.get("round"), "type": t, "channel": CHANNEL[t],
            "from": p.get("author") or p.get("from"), "to": p.get("to"),
            "group_id": p.get("group_id"), "day": p.get("day"), "slot": p.get("slot"),
            "thread_id": p.get("thread_id"), "turn_index": p.get("turn_index"),
            "reply_to": p.get("reply_to"), "participants": p.get("participants"),
            "ctx": p.get("ctx"), "topic": p.get("topic"),
            "body": p.get("body") or "",
        })
    return {"path": path, "msgs": msgs, "llm_calls": sum(llm.values()),
            "llm_cached": llm_cached, "llm_purposes": dict(llm), "providers": dict(providers)}


def thread_key(m: dict) -> str:
    if m.get("thread_id"):
        return f"T|{m['thread_id']}"
    if m["channel"] == "dm":
        pair = "-".join(sorted([str(m["from"]), str(m["to"])]))
        return f"L|{m['day']}|dm|{pair}"
    if m["channel"] == "group":
        return f"L|{m['day']}|group|{m['group_id']}"
    return f"L|{m['day']}|public|-"


def pct(k, n):
    return round(100.0 * k / n, 2) if n else None


def check(run: dict, pid2name: dict) -> dict:
    ms = run["msgs"]
    n = len(ms)
    schema = "explicit" if any(m["thread_id"] for m in ms) else "legacy"
    th = defaultdict(list)
    for m in ms:
        th[thread_key(m)].append(m)
    for k in th:
        th[k].sort(key=lambda m: (m["round"] or 0, m["seq"] or 0))

    def turns_of(arr):
        t = 1
        for a, b in zip(arr, arr[1:]):
            if a["from"] != b["from"]:
                t += 1
        return t

    sizes = sorted(len(v) for v in th.values())
    turns = [turns_of(v) for v in th.values()]
    turns_sorted = sorted(turns)
    n_threads = len(th)

    # S1 / S3 / S4 / S5
    s1 = pct(sum(1 for t in turns if t >= 3), n_threads)
    s3 = pct(sum(1 for s in sizes if s == 1), n_threads)
    s4_p50 = statistics.median(sizes) if sizes else None
    s4_p90 = sizes[int(0.9 * (n_threads - 1))] if n_threads else None
    s5 = max(turns) if turns else None

    # S2 回复指针完整率（分母 = 线程内非首条消息）
    non_first = []
    for arr in th.values():
        non_first.extend(arr[1:])
    s2 = pct(sum(1 for m in non_first if m.get("reply_to")), len(non_first))

    # S6 L-12 对端称呼率（DM+GROUP）；S7 裸 ID
    directed = [m for m in ms if m["channel"] in ("dm", "group")]
    peer_hit = 0
    for m in directed:
        own = pid2name.get(str(m["from"]))
        if any(nm in m["body"] for nm in pid2name.values() if nm and nm != own):
            peer_hit += 1
    s6 = pct(peer_hit, len(directed))
    l8 = pct(sum(1 for m in ms if AGENT_ID_RE.search(m["body"])), n)

    # S8 承接率（线程内相邻对，分母 = 相邻对数）
    pairs = 0
    backref = 0
    for arr in th.values():
        for a, b in zip(arr, arr[1:]):
            pairs += 1
            if any(w in b["body"] for w in BACKREF_LEXICON):
                backref += 1
    s8 = pct(backref, pairs)

    # S9 ctx.topic 非空率（定向线程）
    ctx_topic = sum(1 for m in directed
                    if (m.get("ctx") or {}).get("topic") or m.get("topic"))
    s9 = pct(ctx_topic, len(directed))

    # S10 K-1 分母
    s10 = len(non_first)

    # S11 消息条数
    by_ch = Counter(m["channel"] for m in ms)

    # S12 LLM
    cached_ratio = round(run["llm_cached"] / run["llm_calls"], 4) if run["llm_calls"] else None

    return {
        "path": run["path"], "n_msgs": n, "channels": dict(by_ch), "thread_schema": schema,
        "S": {
            "S1_multi_turn_thread_ratio_pct": {"value": s1, "denom_threads": n_threads,
                                               "expect": ">=10%", "verdict": _v(s1, 10, ">=")},
            "S2_reply_pointer_coverage_pct": {"value": s2, "denom_non_first_msgs": len(non_first),
                                              "expect": ">=95%（<80% 判实现缺陷）",
                                              "verdict": "fail" if (s2 is not None and s2 < 80) else
                                                         ("warn" if (s2 is not None and s2 < 95) else "pass")},
            "S3_single_msg_thread_ratio_pct": {"value": s3, "denom_threads": n_threads,
                                               "expect": "<=80%", "verdict": _v(s3, 80, "<=")},
            "S4_msgs_per_thread": {"p50": s4_p50, "p90": s4_p90, "expect": "p50>=2 且 p90>=3",
                                   "verdict": "pass" if (s4_p50 and s4_p50 >= 2 and s4_p90 and s4_p90 >= 3) else "warn"},
            "S5_longest_chain": {"value": s5, "expect": ">=4",
                                 "verdict": "pass" if (s5 or 0) >= 4 else "warn"},
            "S6_peer_name_address_rate_pct": {"value": s6, "denom_dm_group": len(directed),
                                              "expect": ">0（显著）",
                                              "verdict": "pass" if (s6 or 0) > 0 else "fail"},
            "S7_naked_id_rate_pct": {"value": l8, "denom_msgs": n, "expect": "<=5%",
                                     "verdict": "pass" if (l8 or 0) <= 5 else ("warn" if (l8 or 0) <= 30 else "fail")},
            "S8_cont_backref_rate_pct": {"value": s8, "denom_adjacent_pairs": pairs, "expect": ">40%",
                                         "verdict": _v(s8, 40, ">=")},
            "S9_ctx_topic_nonnull_pct": {"value": s9, "denom_dm_group": len(directed), "expect": "≈100%",
                                         "verdict": "pass" if (s9 or 0) >= 90 else ("warn" if (s9 or 0) > 0 else "fail")},
            "S10_k1_denominator": {"value": s10, "expect": ">=68",
                                   "verdict": "pass" if s10 >= 68 else "warn",
                                   "note": "<30 ⇒ 承接类只能 INCONCLUSIVE"},
            "S11_msg_count": {"value": n, "channels": dict(by_ch), "expect": "150–210",
                              "verdict": "pass" if 150 <= n <= 210 else "warn"},
            "S12_llm": {"calls": run["llm_calls"], "cached": run["llm_cached"],
                        "cached_ratio": cached_ratio, "providers": run["providers"],
                        "purposes": run["llm_purposes"],
                        "expect": "calls 不降、cached_ratio 与基线同量级",
                        "verdict": "info"},
        },
    }


def _v(val, thr, op):
    if val is None:
        return "n/a"
    if op == ">=":
        return "pass" if val >= thr else "fail"
    return "pass" if val <= thr else "fail"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="name=path（被测臂，如 A0=...）")
    ap.add_argument("--baseline", default=None, help="name=path（可选基线，如 v0anchor=...）")
    ap.add_argument("--names", default=str(DEFAULT_NAMES))
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    pid2name = load_names(Path(a.names))

    res = {"generated_by": "experiments/gossip-third-party/a0_structure_check.py",
           "criterion_source": "v2/evidence/D4-A0-expected-structure-checklist.md (S1–S12)",
           "runs": {}}
    name, _, path = a.run.partition("=")
    res["runs"][name] = check(load(path), pid2name)
    if a.baseline:
        bname, _, bpath = a.baseline.partition("=")
        res["runs"][bname] = check(load(bpath), pid2name)
        res["baseline_key"] = bname
        res["run_key"] = name

    for rn, r in res["runs"].items():
        print(f"===== {rn}  n_msgs={r['n_msgs']}  schema={r['thread_schema']}  channels={r['channels']}")
        for k, v in r["S"].items():
            if k == "S12_llm":
                print(f"  {k:32s} calls={v['calls']} cached={v['cached']} "
                      f"ratio={v['cached_ratio']} providers={v['providers']}")
            elif k == "S4_msgs_per_thread":
                print(f"  {k:32s} p50={v['p50']} p90={v['p90']}  expect={v['expect']}  [{v['verdict']}]")
            elif k == "S11_msg_count":
                print(f"  {k:32s} {v['value']} expect={v['expect']}  [{v['verdict']}]")
            else:
                print(f"  {k:32s} {v['value']}  denom={ {kk: vv for kk, vv in v.items() if kk.startswith('denom')} }  "
                      f"expect={v['expect']}  [{v['verdict']}]")

    # 30 秒版判读
    if "run_key" in res:
        r = res["runs"][res["run_key"]]
        gate = [r["S"]["S2_reply_pointer_coverage_pct"]["verdict"],
                r["S"]["S6_peer_name_address_rate_pct"]["verdict"],
                r["S"]["S1_multi_turn_thread_ratio_pct"]["verdict"]]
        verdict = ("STOP：结构未生效，G-1 前后差不可解释（查实现，不要出对比结论）"
                   if "fail" in gate else "GO：结构生效，可继续算 G-1 两臂对比")
        res["gate_verdict"] = verdict
        print(f"\n[gate] S2/S6/S1 = {gate}  =>  {verdict}")

    Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out_json).write_text(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[ok] json -> {a.out_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
