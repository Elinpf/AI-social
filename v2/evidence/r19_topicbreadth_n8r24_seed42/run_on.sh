#!/usr/bin/env bash
# R19 · on 臂（LIFE_PROMPT_TOPIC_BREADTH=1，其余完全相同：同 commit / 同 seed / 同 n8r24）
set -eu
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
E=$REPO/v2/evidence/r19_topicbreadth_n8r24_seed42
cd "$REPO"
export LIFE_PROMPT_TOPIC_BREADTH=1       # ← 唯一变量：on 臂打开
rm -rf /tmp/r19_tb_on_side
setsid nohup bash tools/d2/run_batch.sh \
  --out-dir "$E/run_on" --seed 42 --agents 8 --rounds 24 \
  --side-root /tmp/r19_tb_on_side \
  > "$E/run_on_host.log" 2>&1 < /dev/null &
echo "launched on pid=$!"
