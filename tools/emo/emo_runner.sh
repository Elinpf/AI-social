#!/usr/bin/env bash
# tools/emo/emo_runner.sh —— 单臂批次的 unit 内执行体（由 tools/emo/host_emo_arm.sh 经 systemd-run 拉起）
#
# 职责（只做四件可审计的事，**不写/不改 meta.json** —— meta 的单一真源是 tools/d2/emit_run_meta.py）：
#   1) 落 unit cgroup 证据（证明不在 jiuwenswarm.service 内）
#   2) 写 batch.pid（供 switch_proof.sh 读 /proc/<pid>/environ）
#   3) 心跳落文件 heartbeat.tsv（时间 / run.jsonl 字节数 / 最近 round / RSS_MB）——不靠会话内轮询
#   4) 收尾写 END.json 与 run_batch.rc 的副本，退出码透传
#
# 用法: emo_runner.sh <out_dir> <arm:on|off> [launch_emo_arm.sh 的参数...]
set -uo pipefail

OUT_DIR="${1:?缺少 out_dir}"; ARM="${2:?缺少 arm}"; shift 2
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 2
mkdir -p "$OUT_DIR"
HB="${EMO_HEARTBEAT_SEC:-60}"

# 1) unit cgroup 一次性落盘
{ echo "ts=$(date '+%F %T')"; echo "unit_cgroup=$(cat /proc/self/cgroup)"; } > "$OUT_DIR/cgroup.txt"

# 3) 心跳工具
last_round() {
  local f="$OUT_DIR/run.jsonl"
  [ -f "$f" ] || { echo -1; return; }
  tail -c 262144 "$f" 2>/dev/null | python3 -c '
import sys, json
last=None
for line in sys.stdin.buffer.read().split(b"\n"):
    line=line.strip()
    if not line: continue
    try: r=json.loads(line)
    except Exception: continue
    if isinstance(r,dict) and "round" in r: last=r["round"]
print(-1 if last is None else last)
' 2>/dev/null || echo -1
}
rss_of() { awk '/VmRSS/{print int($2/1024)}' "/proc/$1/status" 2>/dev/null || echo -1; }

echo "[emo-runner] starting arm=$ARM out=$OUT_DIR unit=$(sed 's#.*/##' /proc/self/cgroup)"
bash "$ROOT/tools/emo/launch_emo_arm.sh" "$ARM" "$OUT_DIR" "$@" &
CHILD=$!
echo "$CHILD" > "$OUT_DIR/batch.pid"
echo "[emo-runner] child pid=$CHILD cgroup=$(cat /proc/$CHILD/cgroup 2>/dev/null)"

while kill -0 "$CHILD" 2>/dev/null; do
  sz=$(stat -c %s "$OUT_DIR/run.jsonl" 2>/dev/null || echo -1)
  printf '%s\t%s\t%s\t%s\n' "$(date '+%F %T')" "$sz" "$(last_round)" "$(rss_of $CHILD)" >> "$OUT_DIR/heartbeat.tsv"
  sleep "$HB"
done
wait "$CHILD"; RC=$?
printf '%s\t%s\t%s\t%s\n' "$(date '+%F %T')" "$(stat -c %s "$OUT_DIR/run.jsonl" 2>/dev/null || echo -1)" "EXIT" "$(rss_of $CHILD)" >> "$OUT_DIR/heartbeat.tsv"
echo "[emo-runner] arm=$ARM exited rc=$RC"

# 4) 收尾（幂等，不覆盖已有 END）
if [ ! -f "$OUT_DIR/END.json" ]; then
  python3 - "$OUT_DIR" "$ARM" "$RC" <<'PY'
import json, os, sys, time
rd, arm, rc = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = {"arm": arm, "rc": rc, "ended_at": time.strftime("%F %T"),
     "out_dir": rd, "run_batch_rc_file": os.path.join(rd, "run_batch.rc")}
mb = os.path.join(rd, "meta.json")
d["meta_json_present"] = os.path.exists(mb)
if d["meta_json_present"]:
    try:
        m = json.load(open(mb, encoding="utf-8"))
        d["meta_events"] = m.get("events")
        d["meta_provider"] = m.get("provider")
    except Exception as e:
        d["meta_read_error"] = str(e)
json.dump(d, open(os.path.join(rd, "END.json"), "w"), ensure_ascii=False, indent=2)
print("[emo-runner] END.json:", d)
PY
fi
exit "$RC"
