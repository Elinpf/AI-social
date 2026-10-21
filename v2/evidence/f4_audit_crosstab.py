#!/usr/bin/env python3
"""f4_audit_crosstab.py — R13 复核：**独立重算** 2×2 交叉表（只读日志，不改 tools/）。

为什么单独写一份
----------------
`tools/f4/f4_subset_metrics.py` 里的配对索引是：

    pair_index.setdefault((row["thread"], tseq), []).append(row["seq"])

其中 `row["thread"]` 取自日志 payload 的 **原始 `thread_id`**（如 `TH-P007-P005-19`），
而张力事件行用的是 `f4a.mixed_key(m)` 的**混合键**（如 `m:T|TH-P007-P005-19`）。
两种键**永远不相等** ⇒ `mechanism_pairs` 恒为 `[]`，
`closed_and_paired` 恒为 0，`audit_rows[].closed_by_seq` 恒为 `[null]`。

=> `tools/f4/f4_crosstab.py` 输出的 A/C 两格（以及「机制给了机会、模型没接」的结论）
   是**键口径不一致造成的结构性 0**，不是日志事实。

本脚本只做一件事：按 `mixed_key` 归一后重算同一张 2×2 表，逐格给出行 seq 供人工点开核对。
判定规则与 `tools/f4/f4_subset_metrics.py` 逐字一致（阈值/词表/窗口均从该模块 import，
不重定义），只修键映射。

用法（仓库根）：
  python3 v2/evidence/f4_audit_crosstab.py \
      --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
      --run on=v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
      --out-json v2/evidence/f4_audit_crosstab.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


f4sm = _load("f4_subset_metrics", os.path.join(REPO, "tools/f4/f4_subset_metrics.py"))
d5 = f4sm.d5
f4a = f4sm.f4a


def normalize(tid):
    """把原始 thread_id 归一成 mixed_key 用的键：m:T|<tid>。"""
    if tid is None:
        return None
    if tid.startswith("m:"):
        return tid
    return "m:T|" + tid


def audit_arm(label, rel_path):
    path = rel_path if os.path.isabs(rel_path) else os.path.join(REPO, rel_path)
    # 复用官方模块的度量结果（词表/窗口/极性判定完全同源）
    arm = f4sm.analyze(label, path, f4a.load_emotion(os.path.join(REPO, "tools/d5/emotion_lexicon.txt")),
                       f4a.load_words(os.path.join(REPO, "tools/d5/repair_lexicon.txt")))

    # 重算配对索引：键归一成 mixed_key
    pair_index = {}
    for row in arm["audit_rows"]:
        k = normalize(row["thread"])
        for tseq in row["trigger_seqs"]:
            pair_index.setdefault((k, tseq), []).append(row["seq"])

    out = {}
    for band in ("legacy", "interpersonal"):
        for strict in (False, True):
            key = "closed_strict" if strict else "closed"
            cells = {"A_closed_and_paired": [], "B_closed_no_pair": [],
                     "C_open_but_paired": [], "D_open_no_pair": []}
            for r in arm[band]["rows"]:
                closed = bool(r.get(key))
                pairs = pair_index.get((r["thread"], r["trigger_seq"]), [])
                if closed and pairs:
                    cells["A_closed_and_paired"].append({"trigger_seq": r["trigger_seq"],
                                                         "closed_by_seq": (r.get("closed_strict_by") or r.get("closed_by") or {}).get("seq"),
                                                         "pairs": pairs})
                elif closed:
                    cells["B_closed_no_pair"].append({"trigger_seq": r["trigger_seq"],
                                                      "closed_by_seq": (r.get("closed_strict_by") or r.get("closed_by") or {}).get("seq")})
                elif pairs:
                    cells["C_open_but_paired"].append({"trigger_seq": r["trigger_seq"], "pairs": pairs})
                else:
                    cells["D_open_no_pair"].append({"trigger_seq": r["trigger_seq"]})
            n = sum(len(v) for v in cells.values())
            out[f"{band}|{'strict' if strict else 'loose'}"] = {
                "tension_events": n,
                "A": len(cells["A_closed_and_paired"]), "B": len(cells["B_closed_no_pair"]),
                "C": len(cells["C_open_but_paired"]), "D": len(cells["D_open_no_pair"]),
                "identity_ok": n == arm[band]["tension_events"],
                "detail": cells,
            }
    # 每条 rift 的收口句（同样按 mixed_key 找回同线程）
    recs, _ = d5.read_run(path)
    msgs = d5.extract_messages(recs)
    from collections import defaultdict
    threads = defaultdict(list)
    for m in msgs:
        threads[f4a.mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                      m["seq"] if m["seq"] is not None else -1))
    repair = f4a.load_words(os.path.join(REPO, "tools/d5/repair_lexicon.txt"))
    closed_by = []
    for row in arm["audit_rows"]:
        k = normalize(row["thread"])
        th = threads.get(k) or []
        seqs = []
        for tseq in row["trigger_seqs"]:
            idx = next((i for i, m in enumerate(th) if m["seq"] == tseq), None)
            hit = None
            if idx is not None:
                for j in range(idx + 1, min(idx + 1 + f4sm.WINDOW_MSGS, len(th))):
                    if any(w in th[j]["body"] for w in repair):
                        hit = th[j]["seq"]
                        break
            seqs.append(hit)
        closed_by.append({"seq": row["seq"], "thread": row["thread"],
                          "trigger_seqs": row["trigger_seqs"], "closed_by_seq": seqs})
    out["audit_rows_closed_by_seq"] = closed_by
    out["audit_rows_with_a_closure"] = sum(1 for r in closed_by if any(s is not None for s in r["closed_by_seq"]))
    out["meta"] = {"label": label, "log": os.path.relpath(path, REPO), "log_sha8": arm["log_sha8"],
                   "n_messages": arm["n_messages"], "audit_rows_n": arm["audit_rows_n"]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, metavar="LABEL=PATH")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()
    arms = []
    for spec in args.run:
        label, _, rel = spec.partition("=")
        arms.append(audit_arm(label, rel))
    payload = {"schema": "f4-audit-crosstab/1",
               "why": "tools/f4/f4_subset_metrics.py 的 pair_index 用原始 thread_id、张力行用 mixed_key，两键不等 ⇒ mechanism_pairs 恒空；本脚本只修键映射，规则同源",
               "arms": arms}
    if args.out_json:
        out = args.out_json if os.path.isabs(args.out_json) else os.path.join(REPO, args.out_json)
        open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
        print("written:", out)
    for a in arms:
        m = a["meta"]
        print(f"\n## {m['label']} ({m['log_sha8']}, MSG={m['n_messages']}, 配对行={m['audit_rows_n']}, 有收口的配对行={a['audit_rows_with_a_closure']})")
        print("| 口径 | 张力 | A 闭环∧配对 | B 闭环无配对 | C 未闭环∧配对 | D 未闭环无配对 | 恒等式 |")
        print("|---|---|---|---|---|---|---|")
        for k in ("legacy|loose", "legacy|strict", "interpersonal|loose", "interpersonal|strict"):
            v = a[k]
            print(f"| {k} | {v['tension_events']} | {v['A']} | {v['B']} | {v['C']} | {v['D']} | {'OK' if v['identity_ok'] else 'FAIL'} |")


if __name__ == "__main__":
    main()
