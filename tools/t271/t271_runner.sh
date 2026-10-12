#!/usr/bin/env bash
# T271 跑批执行体 —— 运行在【独立 transient unit】内（不在 jiuwenswarm.service cgroup）。
# 职责：拉起真实批次作为子进程、写 pid、跑心跳（每 N 秒落一行到文件）、等它结束。
# 用法: t271_runner.sh <run_dir> <out_file> <heartbeat_sec> -- <batch cmd...>
set -u
RUN_DIR="${1:?}"; OUT="${2:?}"; HB="${3:?}"; shift 3
[ "${1:-}" = "--" ] && shift

PIDFILE="$RUN_DIR/batch.pid"
HBLOG="$RUN_DIR/heartbeat.tsv"
CGROUPLOG="$RUN_DIR/cgroup.txt"
mkdir -p "$RUN_DIR"

# 一次落盘：本单元 cgroup（事后证明「不在 jiuwenswarm.service 内」的关键证据）
{ echo "ts=$(date '+%F %T')"; echo "unit_cgroup=$(cat /proc/self/cgroup)"; \
  echo "unit_id=$(cat /proc/self/cgroup | sed 's#.*/##')"; } > "$CGROUPLOG"

# 心跳工具：从日志尾部推最近 round；从 /proc 读批次子进程 RSS
rss_of() { awk '/VmRSS/{print int($2/1024)}' "/proc/$1/status" 2>/dev/null || echo -1; }
# 通用 round 探测：读日志尾部最后一条能解析的 JSON 记录的 "round" 字段。
# 对 mock（ROUND_END）与真批（每条记录都带 round）都成立。
last_round() {
  [ -f "$OUT" ] || { echo -1; return; }
  tail -c 262144 "$OUT" 2>/dev/null | python3 -c '
import sys, json
last = None
for line in sys.stdin.buffer.read().split(b"\n"):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except Exception:
        continue
    if isinstance(r, dict) and "round" in r:
        last = r["round"]
print(-1 if last is None else last)
' 2>/dev/null || echo -1
}

echo "[runner] starting: $* (unit=$(sed 's#.*/##' /proc/self/cgroup))"
"$@" &
CHILD=$!
echo "$CHILD" > "$PIDFILE"
echo "[runner] batch child pid=$CHILD cgroup=$(cat /proc/$CHILD/cgroup 2>/dev/null)"

while kill -0 "$CHILD" 2>/dev/null; do
  sz=$(stat -c %s "$OUT" 2>/dev/null || echo -1)
  rnd=$(last_round); [ -z "$rnd" ] && rnd=-1
  printf '%s\t%s\t%s\t%s\n' "$(date '+%F %T')" "$sz" "$rnd" "$(rss_of $CHILD)" >> "$HBLOG"
  sleep "$HB"
done
wait "$CHILD"; rc=$?
printf '%s\t%s\t%s\t%s\n' "$(date '+%F %T')" "$(stat -c %s "$OUT" 2>/dev/null || echo -1)" "EXIT" "$(rss_of $CHILD)" >> "$HBLOG"
echo "[runner] batch exited rc=$rc"
exit $rc
