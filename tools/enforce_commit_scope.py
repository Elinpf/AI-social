#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enforce_commit_scope.py — 拦住「提交里裹带他人未提交 WIP」的机制（T273）。

背景
----
`git add -A` 会不留痕地把共享工作树里**别人尚未提交的 WIP**一起暂存，
提交时无法事后归因作者（git 本身不记录「谁写的」）。今天已发生 5 次，
其中一次把 T268 的 WIP 扫进了 HEAD。**反复失败的规则需要机制，不是再提醒。**

诚实边界（不假装能解决）
------------------------
- `git add -A` 不留痕、无法归因作者 ⇒ 本机制**不判定「作者是谁」**。
- 本机制只判定一个**可观测的裹带信号**：同一次提交里**混有「刚改动的新鲜文件」与
  「长时间未提交的陈旧文件」**——这正是 `add -A` 裹带他人 WIP 的典型形态。
- 单文件提交无法用此信号判断（不声称能拦），返回放行。

判据（确定性、可复算）
----------------------
对 `git diff --cached --diff-filter=ACM` 的暂存文件，取 worktree mtime：
  age(p) = now - mtime(p)
  flagged  = { p : age(p) > AGE_MIN }        # 陈旧：疑似他人 WIP
  fresh    = { p : age(p) <= FRESH_MAX }     # 新鲜：本次自己的改动
若 (fresh 非空 且 flagged 非空) 或 (|flagged| >= 2 且 max_age-min_age > SPREAD_MIN)
  ⇒ 判为「疑似裹带」，**默认拦截（红）**；列出 flagged 路径 + 精确确认令牌。
确认放行：设 `COMMIT_SCOPE_ACK=<令牌>`（令牌随本次 flagged 集合而定，避免"一键永久放行"）。
急救放行：设 `COMMIT_SCOPE_DISABLE=1`（会打印显式告警，便于审计）。

环境变量
--------
COMMIT_SCOPE_AGE_MIN_SEC   陈旧阈值，默认 900（15 分钟）
COMMIT_SCOPE_FRESH_SEC     新鲜阈值，默认 300（5 分钟）
COMMIT_SCOPE_SPREAD_SEC    多陈旧文件的时差阈值，默认 900（15 分钟）
COMMIT_SCOPE_ACK           确认令牌（脚本打印的期望值）
COMMIT_SCOPE_DISABLE       =1 时放行（急救；会告警）

退出码：0 放行；1 拦截。
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time

AGE_MIN = int(os.environ.get("COMMIT_SCOPE_AGE_MIN_SEC", "900"))
FRESH_MAX = int(os.environ.get("COMMIT_SCOPE_FRESH_SEC", "300"))
SPREAD_MIN = int(os.environ.get("COMMIT_SCOPE_SPREAD_SEC", "900"))

RED = "\033[31m"
YEL = "\033[33m"
GRN = "\033[32m"
RST = "\033[0m"


def _staged_paths() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "-z"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        return []
    return [p for p in out.stdout.split("\0") if p]


def _token(flagged: list[str]) -> str:
    h = hashlib.sha256("\n".join(sorted(flagged)).encode("utf-8")).hexdigest()
    return h[:12]


def main() -> int:
    # 非 git 环境或空仓库：放行（本机制只在有暂存内容时有意义）
    if subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True).returncode != 0:
        return 0
    staged = _staged_paths()
    if not staged:
        return 0

    now = time.time()
    ages: dict[str, float] = {}
    for p in staged:
        try:
            ages[p] = now - os.stat(p).st_mtime
        except OSError:
            # 文件不存在（已删/子模块/case 变化）：跳过，不参与判据
            continue
    if len(ages) < 2:
        # 单文件（或仅 1 个可 stat）无法用 mtime 异质性判断 —— 诚实放行
        return 0

    flagged = sorted(p for p, a in ages.items() if a > AGE_MIN)
    fresh = [p for p, a in ages.items() if a <= FRESH_MAX]
    spread_hit = False
    if len(flagged) >= 2:
        fa = [ages[p] for p in flagged]
        spread_hit = (max(fa) - min(fa)) > SPREAD_MIN

    suspicious = (bool(fresh) and bool(flagged)) or spread_hit

    if not suspicious:
        return 0

    token = _token(flagged)

    if os.environ.get("COMMIT_SCOPE_ACK", "").strip() == token:
        print(f"{GRN}[scope-guard] OK{RST} 已显式确认本次范围（含 {len(flagged)} 个陈旧路径）")
        return 0

    if os.environ.get("COMMIT_SCOPE_DISABLE", "").strip() == "1":
        print(f"{YEL}[scope-guard] 告警：COMMIT_SCOPE_DISABLE=1 已绕过范围守卫"
              f"（本次含 {len(flagged)} 个陈旧路径，未确认）{RST}")
        return 0

    # 拦截（红）
    fresh_n = len(fresh)
    print(f"{RED}[scope-guard] 拦截：本次提交疑似裹带「长时间未提交」的路径{RST}")
    print(f"{RED}  暂存文件共 {len(ages)} 个；其中「新鲜(≤{FRESH_MAX}s)」{fresh_n} 个、"
          f"「陈旧(>{AGE_MIN}s)」{len(flagged)} 个{RST}")
    print("  ---- 疑似他人 WIP（陈旧、且与本次新鲜改动同批）----")
    for p in flagged[:30]:
        print(f"    {int(ages[p])}s  {p}")
    if len(flagged) > 30:
        print(f"    ... 其余 {len(flagged)-30} 个略")
    print("  ----------------------------------------------------")
    print("  这是 `git add -A` 裹带他人未提交改动的典型形态。请二选一：")
    print("   (1) 只暂存你自己的文件：git restore --staged <他人路径> 后重试；")
    print(f"   (2) 确认这些路径确实属于本次提交：COMMIT_SCOPE_ACK={token} git commit ...")
    print("  急救（不建议，会告警）：COMMIT_SCOPE_DISABLE=1 git commit ...")
    print("  注：本机制不判定作者（git 不记录作者），只识别「新旧混批」这一可观测信号。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
