#!/usr/bin/env bash
# F-2b B.4-v2 放量复验 · on 臂（LIFE_PROMPT_TOPIC_BREADTH=1）
# 与 run_off.sh 唯一差异 = 这个变量；同 commit / 同 seed / 同 n16r60。
# setsid 在**外层**（tools/d2/run_batch.sh 自身不含 setsid）。**串行**：必须在 off 臂收批后再起。
set -eu
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
WT=$REPO/.worktrees/f2b-v2-n16r60
E=$REPO/v2/evidence/f2b_v2_n16r60_seed42
cd "$WT"
export LIFE_PROMPT_TOPIC_BREADTH=1     # ← on 臂：唯一变量
rm -rf /tmp/f2b_v2_on_side
setsid nohup bash tools/d2/run_batch.sh \
  --out-dir "$E/run_on" --seed 42 --agents 16 --rounds 60 \
  --side-root /tmp/f2b_v2_on_side \
  > "$E/run_on_host.log" 2>&1 < /dev/null &
echo "launched on pid=$!"
