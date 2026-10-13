#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enforce_commit_scope.py — 拦住「提交里裹带他人未提交 WIP」的机制（T273；T342 改判据）。

背景
----
`git add -A` 会不留痕地把共享工作树里**别人尚未提交的 WIP**一起暂存；git 不记录作者 ⇒ 无法归因。
故本机制**不判定作者**，只判定一个**可观测的裹带信号**。

⚠️ T342 修订（为何改判据而非放宽断言）
------------------------------------
旧判据用「**绝对年龄** > AGE_MIN 即陈旧」⇒ 把作者**自己的慢工**（同一长会话里 20 分钟前写的文件 +
刚写的报告）也判成"混批" ⇒ **误报**。常误报的守卫会被人养成"无脑 ACK"习惯 ⇒ **控制失效**。
新判据改为「**相对年龄离群**」：只有当**同一批暂存里既有"本次新鲜改动"、又有"比它老得多(GAP)的文件"**时
才判疑似裹带 —— 这正是 `add -A` 裹带他人 WIP 的形态；而"全是自己的慢工"不触发。

判据（确定性、可复算）
----------------------
对 `git diff --cached --diff-filter=ACM` 的暂存文件取 worktree mtime：
  age(p) = now - mtime(p)
  newest = min(age)                       # 本次最新改动
  flagged = { p : age(p) - newest > OUTLIER_GAP }   # 比本次最新改动老得多 ⇒ 疑似他人/遗留 WIP
  recent  = { p : age(p) <= FRESH_MAX }             # 本次新鲜改动
**suspicious = (recent 非空) ∧ (flagged 非空)** —— 需"有新鲜改动可对比"才判；纯慢工/单文件不判。
- 输出**依据**：逐条打印 `age / newest / Δ(=age-newest)` 与"比本次最新改动老 Δs"。
- 确认放行：`COMMIT_SCOPE_ACK=<令牌>`（令牌随本次 flagged 集合而定，非永久白名单）。
- 急救放行：`COMMIT_SCOPE_DISABLE=1`（打印告警，便于审计）。

环境变量
--------
COMMIT_SCOPE_FRESH_SEC     新鲜阈值，默认 300（5 分钟）
COMMIT_SCOPE_GAP_SEC       离群间隔，默认 1800（30 分钟；比最新改动老 >30min 才可疑）
COMMIT_SCOPE_ACK           确认令牌
COMMIT_SCOPE_DISABLE       =1 放行（急救；告警）
兼容旧名：COMMIT_SCOPE_OUTLIER_GAP_SEC 亦可。

退出码：0 放行；1 拦截。
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time

FRESH_MAX = int(os.environ.get("COMMIT_SCOPE_FRESH_SEC", "300"))
OUTLIER_GAP = int(os.environ.get("COMMIT_SCOPE_GAP_SEC",
                                 os.environ.get("COMMIT_SCOPE_OUTLIER_GAP_SEC", "1800")))

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
    return hashlib.sha256("\n".join(sorted(flagged)).encode("utf-8")).hexdigest()[:12]


def main() -> int:
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
            continue
    if len(ages) < 2:
        return 0  # 单文件：无"新鲜 vs 陈旧"对比，诚实放行

    newest = min(ages.values())
    newest_path = min(ages, key=lambda p: ages[p])
    flagged = sorted(p for p, a in ages.items() if a - newest > OUTLIER_GAP)
    recent = [p for p, a in ages.items() if a <= FRESH_MAX]

    suspicious = bool(recent) and bool(flagged)
    if not suspicious:
        return 0

    token = _token(flagged)

    if os.environ.get("COMMIT_SCOPE_ACK", "").strip() == token:
        print(f"{GRN}[scope-guard] OK{RST} 已显式确认本次范围（含 {len(flagged)} 个离群旧路径）")
        return 0
    if os.environ.get("COMMIT_SCOPE_DISABLE", "").strip() == "1":
        print(f"{YEL}[scope-guard] 告警：COMMIT_SCOPE_DISABLE=1 已绕过范围守卫"
              f"（本次含 {len(flagged)} 个离群旧路径，未确认）{RST}")
        return 0

    print(f"{RED}[scope-guard] 拦截：本次提交疑似裹带「比本次最新改动老得多」的路径{RST}")
    print(f"{RED}  暂存 {len(ages)} 个；本次最新改动 = {newest_path}（age={int(newest)}s）{RST}")
    print(f"  ---- 离群旧路径（比最新改动老 >{OUTLIER_GAP}s）----")
    for p in flagged[:30]:
        d = int(ages[p] - newest)
        print(f"    age={int(ages[p])}s  (+{d}s)  {p}   ← 依据：比本次最新改动老 {d}s")
    if len(flagged) > 30:
        print(f"    ... 其余 {len(flagged)-30} 个略")
    print("  ----------------------------------------------------")
    print("  这是 `git add -A` 裹带他人未提交改动的典型形态（你的新鲜改动 + 别人的旧文件同批）。请二选一：")
    print("   (1) 只暂存你自己的文件：git restore --staged <他人路径> 后重试；")
    print(f"   (2) 确认这些路径确实属于本次提交：COMMIT_SCOPE_ACK={token} git commit ...")
    print("  急救（不建议，会告警）：COMMIT_SCOPE_DISABLE=1 git commit ...")
    print("  注：本机制不判定作者（git 不记录作者），只识别「新鲜+离群旧」混批这一可观测信号。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
