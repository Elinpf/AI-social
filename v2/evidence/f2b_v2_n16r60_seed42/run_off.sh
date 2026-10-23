#!/usr/bin/env bash
# F-2b B.4-v2 放量复验 · off 臂（LIFE_PROMPT_TOPIC_BREADTH 不设 = 默认 OFF）
# 与本目录 run_on.sh 唯一差异 = 这个变量；同 commit / 同 seed / 同 n16r60。
# 注意：setsid 在**外层**（tools/d2/run_batch.sh 自身不含 setsid）。
set -eu
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
WT=$REPO/.worktrees/f2b-v2-n16r60
E=$REPO/v2/evidence/f2b_v2_n16r60_seed42
cd "$WT"
unset LIFE_PROMPT_TOPIC_BREADTH        # ← off 臂：不设（代码内默认 OFF）
rm -rf /tmp/f2b_v2_off_side
setsid nohup bash tools/d2/run_batch.sh \
  --out-dir "$E/run_off" --seed 42 --agents 16 --rounds 60 \
  --side-root /tmp/f2b_v2_off_side \
  > "$E/run_off_host.log" 2>&1 < /dev/null &
echo "launched off pid=$!"
