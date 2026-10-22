#!/usr/bin/env python3
"""R18 修前基线复算（**修正版**：解析 JSON 取顶层 `type`，不用子串计数）。

背景（必须写进报告的坑）：`v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline.sh:69`
用 `grep -c '"type":"MEMORY_CONSOLIDATE"'` 计数，但 `DROPPED` 事件的 payload 里也含
`"type":"MEMORY_CONSOLIDATE"` ⇒ 每条被丢弃的固化被数**两次**（a5: 1510=755×2；worldline: 3558=1779×2），
由此得出的 `discard_rate=50.00%` 是**伪值**，真实值是 100.00%。本脚本只解析 JSON 顶层 `type`。

用法（仓库根）：
    python3 v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline_fixed.py [run_dir...]
"""

import json
import os
import sys

DEFAULT = ["v2/evidence/run_worldline_c1_ctrl_n16r84_seed42",
           "v2/evidence/run_worldline_c1_a1_n16r84_seed42",
           "v2/evidence/run_a5_real_n16r42_seed42"]


def main() -> None:
    dirs = sys.argv[1:] or DEFAULT
    for d in dirs:
        path = os.path.join(d, "run.jsonl")
        if not os.path.exists(path):
            print(f"{d}\tMISSING run.jsonl")
            continue
        n_cons = n_drop = n_sm_write = n_writes = n_sm_should = 0
        n_sleep = n_null = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                t = r.get("type")
                p = r.get("payload") or {}
                if t == "MEMORY_CONSOLIDATE":
                    n_cons += 1
                    if "-SM-" in str(p.get("produced_mem_id") or ""):
                        n_sm_should += 1
                elif t == "DROPPED":
                    if p.get("reason") == "unknown_intent_field" \
                            and p.get("type") == "MEMORY_CONSOLIDATE" \
                            and "text" in (p.get("keys") or []):
                        n_drop += 1
                elif t == "MEMORY_WRITE":
                    n_writes += 1
                    if "-SM-" in str(p.get("mem_id") or ""):
                        n_sm_write += 1
                elif t == "SLEEP_COMPLETED":
                    n_sleep += 1
                    if p.get("drift_permille") is None:
                        n_null += 1
        rate = (100.0 * n_drop / n_cons) if n_cons else 0.0
        print(f"{d}\tMEMORY_CONSOLIDATE={n_cons}\ttext_discard={n_drop}"
              f"\tdiscard_rate={rate:.2f}%\tsm_should={n_sm_should}"
              f"\tMEMORY_WRITE_total={n_writes}\tSM_write={n_sm_write}"
              f"\tdrift_null={n_null}/{n_sleep}")


if __name__ == "__main__":
    main()
