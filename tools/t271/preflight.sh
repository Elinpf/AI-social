#!/usr/bin/env bash
# T271 跑批预检 —— 启动长跑批前必须看的余量。
# 只读，不改任何东西。任一 WARN 都要显式决策（不做静默降级）。
set -u
echo "=== [T271 preflight] $(date '+%F %T') ==="
echo "--- self cgroup (必须在 jiuwenswarm.service 内，才需要下面的逃逸) ---"
cat /proc/self/cgroup
echo "--- systemd-run ---"
command -v systemd-run || { echo "FATAL: systemd-run 缺失"; exit 3; }
echo "--- free -h ---"
free -h
echo "--- df -h / ---"
df -h /
echo "--- df -i / ---"
df -i /
avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
echo "--- MemAvailable = ${avail} MB ---"
if [ "$avail" -lt 3072 ]; then
  echo "[WARN] MemAvailable < 3G，跑批前先降并发/清缓存"
fi
echo "[preflight] done"
