#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R10-E2E 四轴读数器（**冻结件**，只读 run.jsonl，不写世界、不调 LLM）。

用途
----
把「睡眠 → 固化 → 次日记忆延续」的四条轴一次性算成机器可核的 JSON，
供批次 README / 报告引用。**同一份脚本**既跑基线批（f2b_v2 off 臂）也跑修后批
（r10e2e），因此「同一段代码」是可验证的（引用本文件 sha256），不是「同一套人工口径」。

四条轴（**必须分开读，不得合成一个「改善」**）
------------------------------------------------
1) 机制轴（arm 无关）：`MEMORY_CONSOLIDATE` 总数、`text` 透传/丢弃条数。
   - `text` 在 c01f6dd 之前被整段丢弃 ⇒ payload 里 `text` 缺失或空串；
   - 本脚本判据：`text` 为「非空字符串」= 透传（KEPT），否则 = 丢弃（DROPPED）。
2) 落账轴：`MEMORY_WRITE{kind=semantic}` 条数、`MEMORY_CONSOLIDATE.distinct produced_mem_id`、
   差额（事件数 − distinct）、`INTENT_REJECTED{intent_class=INTENT.MEMORY, reason=invalid_payload}` 条数，
   以及机械断言 `差额 == 拒收计数`。**这是「修没修好」最硬的一条。**
3) 漂移轴：`SLEEP_COMPLETED` 总数 + 三字段（`drift_permille` / `pf0` / `pf_t`）各自 null 条数 / 分母。
4) 行为轴：`MSG_*` 中 `ctx.memory_refs` 非空条数（**只登记，不下效果结论**）。

附带口径分母（R10 既有读数的分母，必须一起给，防口径漂移）
----------------------------------------------------------
`MEMORY_WRITE` 总数与 kind 分布、`MEMORY_FORGET` 总数与 forget/write 比值、
`SLEEP_STARTED`/`SLEEP_COMPLETED`（80/80 口径）、`PERSONA_DRIFT` 条数。

用法
----
    PYTHONPATH=code python3 tools/f2/r10e2e_axes.py \
        --run v2/evidence/<run>/run.jsonl --out v2/evidence/<run>/axes_r10e2e.json

退出码：0 = 正常产出；2 = 参数/文件错误。
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC")
DRIFT_FIELDS = ("drift_permille", "pf0", "pf_t")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R10-E2E 四轴读数器（冻结件）")
    ap.add_argument("--run", required=True, help="run.jsonl 路径")
    ap.add_argument("--out", default=None, help="输出 JSON 路径（不给则打印 stdout）")
    ap.add_argument("--label", default=None, help="批次标签（写进 JSON，便于对照）")
    args = ap.parse_args(argv)

    if not os.path.exists(args.run):
        print(f"[axes] FAIL: run 不存在: {args.run}", file=sys.stderr)
        return 2

    types = collections.Counter()
    write_by_kind = collections.Counter()
    reject = collections.Counter()

    consolidate_total = 0
    consolidate_text_kept = 0
    consolidate_text_dropped = 0
    produced_ids: set[str] = set()
    produced_null = 0

    sleep_total = 0
    drift_null = {k: 0 for k in DRIFT_FIELDS}
    drift_null_all3 = 0

    msg_total = 0
    msg_memrefs_nonzero = 0
    retrieve_total = 0
    retrieve_with_selected = 0

    with open(args.run, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            t = r.get("type")
            pl = r.get("payload") or {}
            types[t] += 1

            if t == "MEMORY_CONSOLIDATE":
                consolidate_total += 1
                txt = pl.get("text")
                if isinstance(txt, str) and txt.strip():
                    consolidate_text_kept += 1
                else:
                    consolidate_text_dropped += 1
                mid = pl.get("produced_mem_id")
                if mid:
                    produced_ids.add(str(mid))
                else:
                    produced_null += 1

            elif t == "MEMORY_WRITE":
                write_by_kind[str(pl.get("kind"))] += 1

            elif t == "INTENT_REJECTED":
                reject[(str(pl.get("intent_class")), str(pl.get("reason")))] += 1

            elif t == "SLEEP_COMPLETED":
                sleep_total += 1
                nulls = 0
                for k in DRIFT_FIELDS:
                    if pl.get(k) is None:
                        drift_null[k] += 1
                        nulls += 1
                if nulls == len(DRIFT_FIELDS):
                    drift_null_all3 += 1

            elif t in MSG_TYPES:
                msg_total += 1
                ctx = pl.get("ctx") or {}
                refs = ctx.get("memory_refs")
                if refs:
                    msg_memrefs_nonzero += 1

            elif t == "MEMORY_RETRIEVE":
                retrieve_total += 1
                if pl.get("selected_mem_ids"):
                    retrieve_with_selected += 1

    mem_write_total = types.get("MEMORY_WRITE", 0)
    forget_total = types.get("MEMORY_FORGET", 0)
    distinct_ids = len(produced_ids)
    ledger_gap = consolidate_total - distinct_ids
    reject_mem = reject[("INTENT.MEMORY", "invalid_payload")]

    out = {
        "reader": {
            "script": os.path.abspath(__file__),
            "script_sha256": sha256_file(os.path.abspath(__file__)),
        },
        "source": {
            "run": os.path.abspath(args.run),
            "run_sha256": sha256_file(args.run),
            "run_bytes": os.path.getsize(args.run),
            "label": args.label,
        },
        "axes": {
            "mechanism": {
                "MEMORY_CONSOLIDATE_total": consolidate_total,
                "text_KEPT": consolidate_text_kept,
                "text_DROPPED": consolidate_text_dropped,
                "note": "text 非空字符串=KEPT；c01f6dd 之前为整段丢弃",
            },
            "ledger": {
                "semantic_writes": write_by_kind.get("semantic", 0),
                "distinct_produced_mem_id": distinct_ids,
                "produced_mem_id_null": produced_null,
                "gap_events_minus_distinct": ledger_gap,
                "INTENT_REJECTED_MEMORY_invalid_payload": reject_mem,
                "assert_gap_eq_rejected": ledger_gap == reject_mem,
                "assert_semantic_eq_distinct": write_by_kind.get("semantic", 0) == distinct_ids,
            },
            "drift": {
                "SLEEP_COMPLETED_total": sleep_total,
                "null_drift_permille": drift_null["drift_permille"],
                "null_pf0": drift_null["pf0"],
                "null_pf_t": drift_null["pf_t"],
                "null_all_three": drift_null_all3,
                "denominator": sleep_total,
            },
            "behavior": {
                "MSG_total": msg_total,
                "MSG_ctx_memory_refs_nonzero": msg_memrefs_nonzero,
                "MEMORY_RETRIEVE_total": retrieve_total,
                "MEMORY_RETRIEVE_with_selected": retrieve_with_selected,
                "note": "只登记，不下效果结论",
            },
        },
        "denominators": {
            "MEMORY_WRITE_total": mem_write_total,
            "MEMORY_WRITE_by_kind": dict(sorted(write_by_kind.items())),
            "MEMORY_FORGET_total": forget_total,
            "forget_per_write": round(forget_total / mem_write_total, 4) if mem_write_total else None,
            "SLEEP_STARTED": types.get("SLEEP_STARTED", 0),
            "SLEEP_COMPLETED": types.get("SLEEP_COMPLETED", 0),
            "PERSONA_DRIFT": types.get("PERSONA_DRIFT", 0),
        },
        "reject_breakdown": {f"{k[0]}|{k[1]}": v for k, v in sorted(reject.items())},
        "event_type_counts": dict(sorted(types.items())),
    }

    text = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=False)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"[axes] written: {args.out}")
        print(json.dumps(out["axes"], ensure_ascii=False))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
