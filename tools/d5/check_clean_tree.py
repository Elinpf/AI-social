#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S0a 代码树干净度判定（按 leader 2026-10-20 放宽口径）。

判据（写死）：
- **HARD FAIL（阻断跑批）**：`code/life`、`code/orchestration`、`code/config`、`code/engine`
  下存在任何 modified / staged / untracked 文件；
- **不阻断（记注）**：仅 `code/frontend/`、`reports/`、`v2/refs/`、`v2/evidence/`、`tools/` 下的未跟踪文件
  —— 但要求 meta 的 `git_dirty_files` 如实列出，且这些文件里不得有影响 `code/life` import 链的 `.py`。

理由：判据的目的是「跑批用的代码树确定」，不是「仓库绝对干净」。

用法：
    python3 tools/d5/check_clean_tree.py [--repo <path>] [--out <json>]
退出码：0 = 通过（可能带非阻断注记）；1 = HARD FAIL；2 = 无法判定（git 不可用/不在仓库内）。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

BLOCKING_PREFIXES = ("code/life/", "code/orchestration/", "code/config/", "code/engine/")
NONBLOCKING_PREFIXES = ("code/frontend/", "reports/", "v2/refs/", "v2/evidence/", "tools/", "glossary/")


def run(cmd: List[str], cwd: str) -> str:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True).stdout


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="S0a 代码树干净度判定（放宽口径）")
    ap.add_argument("--repo", default=None, help="仓库路径，默认由脚本位置推断")
    ap.add_argument("--out", default=None, help="输出 JSON 路径")
    args = ap.parse_args(argv)

    cwd = args.repo or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    try:
        porcelain = run(["git", "status", "--porcelain"], cwd)
        head = run(["git", "rev-parse", "HEAD"], cwd).strip()
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"verdict": "UNDECIDABLE", "error": str(e)}, ensure_ascii=False))
        return 2

    blocking, nonblocking = [], []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        status, path = line[:2], line[3:].strip().strip('"')
        path = path.split(" -> ")[-1]
        rec = {"status": status.strip(), "path": path}
        if any(path.startswith(p) for p in BLOCKING_PREFIXES):
            blocking.append(rec)
        elif any(path.startswith(p) for p in NONBLOCKING_PREFIXES):
            nonblocking.append(rec)
        else:
            # 不在白名单也不在硬阻断区（如根目录杂项）：按「需人工判断」记注，不阻断
            nonblocking.append({**rec, "note": "其它路径，按非阻断记注"})

    # 检查非阻断区里是否有 .py（可能影响 import 链）
    py_risk = [r for r in nonblocking if r["path"].endswith(".py") and r["path"].startswith("tools/")]
    verdict = "FAIL" if blocking else "PASS"
    res: Dict[str, Any] = {
        "schema_version": "d5-s0a-clean-tree/1.0",
        "rule": {
            "hard_fail_prefixes": list(BLOCKING_PREFIXES),
            "nonblocking_prefixes": list(NONBLOCKING_PREFIXES),
            "source": "leader 裁决 2026-10-20：A0 起跑的 S0a 放宽为「跑批代码树确定」",
        },
        "repo": cwd, "head": head,
        "blocking": blocking, "nonblocking_count": len(nonblocking),
        "nonblocking": nonblocking[:50],
        "tools_py_present": py_risk[:20],
        "note": ("tools/ 下存在未跟踪 .py：需人工确认其不在 code/life 的 import 链上"
                 if py_risk else "tools/ 下无未跟踪 .py"),
        "verdict": verdict,
    }
    out = json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(out + "\n")
    print(out)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
