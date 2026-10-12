#!/usr/bin/env bash
# T271 状态查看 —— 平台重启后回来看这个文件即可判「死在哪一刻」。
# 用法: status.sh <run_dir>
set -u
RUN_DIR="${1:?用法: status.sh <run_dir>}"
[ -d "$RUN_DIR" ] || { echo "无此 run 目录: $RUN_DIR"; exit 1; }
echo "=== run: $RUN_DIR ==="
BPID="$(cat "$RUN_DIR/batch.pid" 2>/dev/null || echo '')"
echo "batch pid = ${BPID:-<无>}"
if [ -n "$BPID" ] && [ -d "/proc/$BPID" ]; then
  echo "状态 = ALIVE"
  echo "cgroup = $(cat /proc/$BPID/cgroup 2>/dev/null)"
  echo "RSS = $(awk '/VmRSS/{print int($2/1024)" MB"}' /proc/$BPID/status 2>/dev/null)"
else
  echo "状态 = DEAD"
fi
echo "=== unit cgroup 快照 ==="; cat "$RUN_DIR/cgroup.txt" 2>/dev/null
echo "=== 心跳（时间 / size / round / RSS_MB）最后 8 行 ==="
tail -8 "$RUN_DIR/heartbeat.tsv" 2>/dev/null || echo "(无心跳)"
echo "=== 日志大小 ==="; ls -l "$RUN_DIR"/*.jsonl 2>/dev/null
echo "=== host.log 尾 ==="; tail -5 "$RUN_DIR/host.log" 2>/dev/null
