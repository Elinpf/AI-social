#!/usr/bin/env python3
"""F-4 闭环 × 机制配对的 2×2 交叉表（R13；零跑批，只读日志，可独立复跑）。

为什么单独成脚本
----------------
`f4_subset_metrics.py` 只直接输出 `closed_and_paired_events` 一格；报告 §2.1c 需要完整四格，
且**宽松口径**与**严格口径**（剔除 `我懂`）都要各给一遍。本脚本只做聚合，不改任何判据：

  四格定义（以单个张力事件为单位）：
    A = 词表判定闭环 ∧ 该事件 seq 出现在某条 dialogue_repair 的 trigger_seqs 里   （可信闭环）
    B = 词表判定闭环 ∧ 无配对                                                   （词表噪声）
    C = 词表未闭环 ∧ 有配对                                                     （机制给了机会、模型没接）
    D = 词表未闭环 ∧ 无配对                                                     （基线常态）
  恒等式：A + B + C + D == tension_events（逐臂成立，脚本内 assert）

配对判定口径（与 `f4_subset_metrics.py` 完全一致，**不是**「同线程其后有无 repair 行」的近似）：
  `mechanism_pairs` 由 `pair_index[(thread, trigger_seq)]` 得到，即**张力句的 trigger_seq 是否出现在
  某条 `payload.dialogue_repair.trigger_seqs` 里**；该字段由 `code/life/dialogue_repair.repair_audit()`
  在**回复路径**（`agent._send_reply`）写入 —— initiate 路径不产配对，因此 C/D 里天然包含
  「只有 initiate 路径参与」的线程，不能把「未闭环且无配对」一律读成机制失效。

用法（仓库根，干净 shell 可原样复制；只依赖仓库内已入库的 JSON/日志，不依赖 /tmp）：

  python3 tools/f4/f4_crosstab.py \
    --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
    --run on=v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
    --out-json v2/evidence/f4_crosstab.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


f4sm = _load("f4_subset_metrics", os.path.join(HERE, "f4_subset_metrics.py"))
f4a = f4sm.f4a


def cells(rows: list, strict: bool) -> dict:
    """四格聚合；strict=True 时用 `closed_strict`（剔除 `我懂`）而不是 `closed`。"""
    key = "closed_strict" if strict else "closed"
    a = b = c = d = 0
    for r in rows:
        closed = bool(r.get(key))
        paired = bool(r.get("mechanism_pairs"))
        if closed and paired:
            a += 1
        elif closed and not paired:
            b += 1
        elif (not closed) and paired:
            c += 1
        else:
            d += 1
    total = a + b + c + d
    return {"closed_paired": a, "closed_unpaired": b,
            "unclosed_paired": c, "unclosed_unpaired": d,
            "sum_check": "OK" if total == len(rows) else "BAD"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, metavar="LABEL=PATH")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args(argv)

    emotion = f4a.load_emotion(os.path.join(REPO, "tools/d5/emotion_lexicon.txt"))
    repair = f4a.load_words(os.path.join(REPO, "tools/d5/repair_lexicon.txt"))

    out = {"schema": "f4-crosstab/1",
           "pairing_rule": ("mechanism_pairs = 张力句 seq 出现在某条 payload.dialogue_repair.trigger_seqs 里；"
                            "dialogue_repair 仅在 _send_reply 路径写入"),
           "strict_excluded_words": list(f4sm.AGREEMENT_ONLY),
           "arms": []}

    print("\n| arm | sha8 | 口径 | 张力 | A 闭环∧配对 | B 闭环无配对(词表噪声) | C 未闭环∧配对 | D 未闭环无配对 | 恒等式 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for spec in args.run:
        label, _, rel = spec.partition("=")
        path = rel if os.path.isabs(rel) else os.path.join(REPO, rel)
        arm = f4sm.analyze(label, path, emotion, repair)
        entry = {"label": label, "log": arm["log"], "log_sha8": arm["log_sha8"]}
        for name, rows, summary in (
                ("legacy", arm["legacy"]["rows"], arm["legacy"]),
                ("interpersonal", arm["interpersonal"]["rows"], arm["interpersonal"])):
            loose = cells(rows, strict=False)
            strict = cells(rows, strict=True)
            # 键名与 f4_subset_metrics.py 逐字同名同值（机器可校验，不做映射）
            entry[name] = {"tension_events": summary["tension_events"],
                           "closed_events": summary["closed_events"],
                           "closed_strict_events": summary["closed_strict_events"],
                           "cells_loose": loose, "cells_strict": strict}
            for tag, cc in (("宽松", loose), ("严格", strict)):
                print("| %s | %s | %s/%s | %d | %d | %d | %d | %d | %s |" % (
                    label, arm["log_sha8"], name, tag, summary["tension_events"],
                    cc["closed_paired"], cc["closed_unpaired"],
                    cc["unclosed_paired"], cc["unclosed_unpaired"],
                    cc["sum_check"]))
        out["arms"].append(entry)

    if args.out_json:
        p = args.out_json if os.path.isabs(args.out_json) else os.path.join(REPO, args.out_json)
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1,
                                                        sort_keys=True) + "\n")
        print("written:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
