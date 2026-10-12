#!/usr/bin/env bash
# T271 decoy guard 执行体 —— 在【本单元 cgroup 内】拉起一个 detached 受害者进程，
# 精确复刻旧跑批的处境：detached（setsid）但仍在服务组 cgroup 内 → 重启必被回收。
# 每次拉起建一个独立 incarnation 目录，避免新旧受害者共用日志文件（否则证据被覆盖）。
set -u
BASE="${1:?用法: guard_start.sh <base_dir>}"
INC="$BASE/inc-$(date +%s)"
mkdir -p "$INC"
ln -sfn "$INC" "$BASE/current"
setsid python3 /root/t271/bin/mock_batch.py \
  --out "$INC/victim.jsonl" --rounds 100000 --round-seconds 0.3 \
  --flush-every 5 --heartbeat-log "$INC/victim.hb" --heartbeat-seconds 2 \
  >"$INC/victim.log" 2>&1 &
VP=$!
echo "$VP" > "$INC/victim.pid"
echo "[guard] $(date '+%F %T') inc=$INC victim pid=$VP cgroup=$(cat /proc/$VP/cgroup 2>/dev/null)"
exec sleep infinity
