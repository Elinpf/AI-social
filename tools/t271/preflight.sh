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
freemb=$(awk '/^MemFree:/{print int($2/1024)}' /proc/meminfo)
# 判据：看 available（含可回收 page cache），不看 free（free 列常被 cache 压到很小）
echo "--- 内存判据字段：MemAvailable = ${avail} MB （看这列；MemFree=${freemb}MB 仅参考，cache 占用的可回收） ---"
if [ "$avail" -lt 3072 ]; then
  echo "[WARN] MemAvailable(available) < 3G —— 跑批前先降并发；判据是 available 不是 free"
fi
echo "[preflight] done"
