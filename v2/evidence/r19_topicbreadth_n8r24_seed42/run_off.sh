#!/usr/bin/env bash
# R19 · off 臂（LIFE_PROMPT_TOPIC_BREADTH 不设 = 默认关）
# 复算方式：在仓库根直接 bash 本文件（会重新跑一批真 LLM，约 8–12 分钟，n8r24）
set -eu
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
E=$REPO/v2/evidence/r19_topicbreadth_n8r24_seed42
cd "$REPO"
unset LIFE_PROMPT_TOPIC_BREADTH          # ← 唯一变量：off 臂不设
rm -rf /tmp/r19_tb_off_side
setsid nohup bash tools/d2/run_batch.sh \
  --out-dir "$E/run_off" --seed 42 --agents 8 --rounds 24 \
  --side-root /tmp/r19_tb_off_side \
  > "$E/run_off_host.log" 2>&1 < /dev/null &
echo "launched off pid=$!"
