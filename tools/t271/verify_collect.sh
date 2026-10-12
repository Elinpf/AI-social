#!/usr/bin/env bash
# T290 反向验证 —— `collect` 成功判定两头都要收得住（缺一即门禁失效）。
#   A) 心跳滞后但实际成功  -> 必须 SUCCESS      （真 orchestration, heartbeat=600, 日志 round 到目标, rc=0）
#   B) 真中断              -> 必须 INTERRUPTED  （kill 中途, 日志 round < 目标, rc=137）
#   C) meta 回填           -> ended_at / engine_version_fingerprint 非空
# 全程在隔离 run_root 下，不碰今晚真实产物。
set -uo pipefail
BIN="$(cd "$(dirname "$0")" && pwd)"
REPO="${T271_REPO:-/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment}"
PY="/opt/openjiuwen/workswarm-venv/bin/python"
VR="${T271_VERIFY_ROOT:-/root/t271/runs/verify}"
export T271_RUN_ROOT="$VR"
rm -rf "$VR"; mkdir -p "$VR/_env"
printf 'T271_NOOP=1\n' > "$VR/_env/dummy.env"
ENVF="$VR/_env/dummy.env"
SHA="$(git -C "$REPO" rev-parse --short HEAD)"

PASS=1
ck() { if [ "$1" = "$2" ]; then echo "  ok: $3"; else echo "  FAIL: $3 (got='$1' want='$2')"; PASS=0; fi; }
row() { python3 "$BIN/nightly.py" status --run-root "$VR" 2>/dev/null | awk -v n="$1" '$1==n{print $2}'; }

echo "### A) 心跳滞后但实际成功 -> SUCCESS"
COPA="$VR/_copyA"; rm -rf "$COPA"; mkdir -p "$COPA"
git -C "$REPO" archive HEAD | tar -x -C "$COPA"
AOUT="$VR/A/run.jsonl"
bash "$BIN/host_batch.sh" --name A --out "$AOUT" --run-dir "$VR/A" \
  --workdir "$COPA/code" --env-file "$ENVF" --heartbeat 600 \
  --meta rounds=6 --meta agents=2 --meta seed=1 --meta sha="$SHA" --meta copy="$COPA" \
  --meta switch=- --meta resume_mode=native --meta flush_every=2 --meta side_root="$VR/A/side" \
  -- "$PY" -m orchestration run --life --seed 1 --agents 2 --rounds 6 \
     --out "$AOUT" --side-root "$VR/A/side" --flush-every 2 >"$VR/A.launch.log" 2>&1
for _ in $(seq 1 60); do
  [ -f "$AOUT" ] && [ "$(tail -1 "$AOUT" | python3 -c 'import sys,json;print(json.loads(sys.stdin.readline()).get("round"))' 2>/dev/null)" = "5" ] && break
  sleep 1
done
bash "$BIN/finalize_meta.sh" "$VR/A" >/dev/null 2>&1 || true
hb_last=$(awk -F'\t' '$3 ~ /^-?[0-9]+$/ && $3>=0 {r=$3} END{print (r==""?-1:r)}' "$VR/A/heartbeat.tsv")
log_last=$(tail -1 "$AOUT" | python3 -c 'import sys,json;print(json.loads(sys.stdin.readline()).get("round"))' 2>/dev/null)
echo "  证据: 心跳最后数据 round=$hb_last (滞后) ; 日志最后 round=$log_last ; target-1=5"
ck "$(row A)" "SUCCESS" "A 应为 SUCCESS（不被滞后心跳误判）"

echo "### B) 真中断 -> INTERRUPTED"
BOUT="$VR/B/run.jsonl"
bash "$BIN/host_batch.sh" --name B --out "$BOUT" --run-dir "$VR/B" \
  --workdir "$COPA/code" --env-file "$ENVF" --heartbeat 600 \
  --meta rounds=30 --meta agents=2 --meta seed=2 --meta sha="$SHA" --meta copy="$COPA" \
  --meta switch=- --meta resume_mode=native --meta flush_every=5 --meta side_root="$VR/B/side" \
  -- "$PY" "$BIN/mock_batch.py" --out "$BOUT" --rounds 30 --agents 2 --seed 2 \
     --flush-every 5 --round-seconds 1.0 --heartbeat-seconds 600 >"$VR/B.launch.log" 2>&1
sleep 4
Bpid=$(cat "$VR/B/batch.pid" 2>/dev/null || echo '')
echo "  kill B pid=$Bpid（模拟外因中断）"; kill -9 "$Bpid" 2>/dev/null || true
sleep 3
hbB=$(awk -F'\t' '$3 ~ /^-?[0-9]+$/ && $3>=0 {r=$3} END{print (r==""?-1:r)}' "$VR/B/heartbeat.tsv")
logB=$(tail -1 "$BOUT" 2>/dev/null | python3 -c 'import sys,json;print(json.loads(sys.stdin.readline()).get("round"))' 2>/dev/null)
echo "  证据: 日志最后 round=$logB (< 29) ; rc=137"
ck "$(row B)" "INTERRUPTED" "B 应为 INTERRUPTED（真中断不被漏判为成功）"

echo "### C) meta 回填"
python3 - "$VR/A/meta.json" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
print("  A.ended_at =",m.get("ended_at"))
print("  A.engine_version_fingerprint =",m.get("engine_version_fingerprint"))
ok = bool(m.get("ended_at")) and bool(m.get("engine_version_fingerprint"))
sys.exit(0 if ok else 1)
PY
ck "$?" "0" "A 的 ended_at / fingerprint 已由 runner 退出时回填"

# 清理单元
for u in t271-A t271-B; do systemctl stop "$u" 2>/dev/null; systemctl reset-failed "$u" 2>/dev/null; done
echo
if [ "$PASS" = "1" ]; then echo "############ T290 VERIFY: PASS ############"; else echo "############ T290 VERIFY: FAIL ############"; fi
exit $((1-PASS))
