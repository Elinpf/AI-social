#!/usr/bin/env bash
# R52 两臂串行驱动器（**监视壳**，不是批体；批体是 tools/r52/arm_inner.sh，由 launch_arm.sh setsid 起）
#
# 职责只有一个：保证两臂**串行**——OFF 收批（run_batch.rc 落盘）后再起 ON。
# 本脚本不持有跑批锁（锁由 arm_inner.sh 的 fd 9 全程持有，并发由 flock 兜底）：
# 即使本壳意外重入，第二臂也会因 `flock -n` 拿不到锁而直接 exit 22。
#
# 用法：setsid bash tools/r52/run_two_arms.sh >> /tmp/r52_two_arms.log 2>&1 &
set -uo pipefail

WT="/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment"
SEED=42; AGENTS=16; ROUNDS=36
cd "$WT" || exit 97

wait_rc() {   # $1=arm  $2=超时秒数（默认 7200）
  local arm="$1" limit="${2:-7200}" t0 now out
  out="$WT/v2/evidence/r52-scene-fresh-${arm}-20261102_n${AGENTS}r${ROUNDS}_s${SEED}"
  t0=$(date +%s)
  while :; do
    if [[ -f "$out/run_batch.rc" ]]; then
      echo "[monitor] arm=$arm rc=$(cat "$out/run_batch.rc") at=$(date -Is)"
      return 0
    fi
    now=$(date +%s)
    if (( now - t0 > limit )); then
      echo "[monitor] arm=$arm TIMEOUT after ${limit}s（未写 rc，交由人工判断）"
      return 9
    fi
    sleep 30      # 监视壳轮询间隔（非批体；批体只有 30s 心跳）
  done
}

echo "[monitor] start at=$(date -Is) pid=$$"
bash "$WT/tools/r52/launch_arm.sh" off || { echo "[monitor] off 启动失败"; exit 20; }
wait_rc off || exit 21
bash "$WT/tools/r52/launch_arm.sh" on || { echo "[monitor] on 启动失败"; exit 22; }
wait_rc on || exit 23
echo "[monitor] all done at=$(date -Is)"
