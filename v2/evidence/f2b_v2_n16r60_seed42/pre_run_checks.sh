#!/usr/bin/env bash
# 起跑前串行纪律复核（可复算；把检测逻辑放进脚本文件，避免 pgrep 命中「检查命令自身的 cmdline」）
set -u
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
WT=$REPO/.worktrees/f2b-v2-n16r60
SELF=$$
echo "# 起跑前串行纪律复核（T=$(date -Iseconds)）"
echo "## A. pgrep -af（跑批三种形态；结果中的候选是否为本脚本/其祖先需逐个核对）"
echo '$ pgrep -af "orchestration run|run_batch|nightly.py"'
pgrep -af "orchestration run|run_batch|nightly.py"
echo "pgrep_rc=$?"
echo
echo "## A1. 祖先链（用于排除自身）"
pid=$SELF; depth=0
while [[ -n "$pid" && "$pid" != "0" && $depth -lt 64 ]]; do echo -n "$pid "; pid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' '); depth=$((depth+1)); done
echo
echo
echo "## B. 遍历 /proc/*/cwd：cwd 落在 social-experiment 下且 cmdline 含 orchestration/run_batch/nightly.py"
for p in /proc/[0-9]*; do
  c=$(readlink "$p/cwd" 2>/dev/null) || continue
  case "$c" in *social-experiment*)
    cmd=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
    case "$cmd" in *orchestration*|*run_batch*|*nightly.py*) echo "PID=${p#/proc/} cwd=$c cmd=${cmd:0:160}";; esac;;
  esac
done
echo "(B 段为空 ⇒ 无双重复核发现的跑批进程)"
echo
echo "## C. 主树 / worktree 分支与状态"
echo "main: $(git -C "$REPO" branch --show-current) @ $(git -C "$REPO" rev-parse --short HEAD)"
echo "wt  : $(git -C "$WT" branch --show-current) @ $(git -C "$WT" rev-parse --short HEAD)"
echo "wt git status --porcelain 行数: $(git -C "$WT" status --porcelain | wc -l)"
echo
echo "## D. 开关与默认值（代码内唯一出处 code/life/topic_breadth.py）"
grep -n 'BREADTH_ENV\|_ON =' "$WT/code/life/topic_breadth.py" | head -8
echo
echo "## E. run_batch.sh 自身不含 setsid（外层必须套）"
echo -n 'grep -c setsid tools/d2/run_batch.sh => '
grep -c 'setsid' "$WT/tools/d2/run_batch.sh" || true
