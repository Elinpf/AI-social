#!/usr/bin/env bash
# tools/d9i/run_two_arms.sh —— D9i 旁白通道 OFF/ON 两臂**严格串行**驱动器
#
#   bash tools/d9i/run_two_arms.sh [--seed 42] [--agents 16] [--rounds 24]
#
# 纪律：
#   - 起跑前 pgrep 三重确认无并发（orchestration run / run_batch / nightly.py；排除自身祖先链）
#   - 两臂严格串行：OFF 收批 → 检查 run_batch.rc==0 且 llm_cost.rc==0 → 才起 ON
#   - 任一臂失败即停，不自行放宽（rc 落盘、日志留下）
#   - 由外部 setsid 启动；本脚本不做长 sleep（心跳由各臂脚本自己写）
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 2

SEED=42; AGENTS=16; ROUNDS=24
while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed) SEED="$2"; shift 2 ;;
    --agents) AGENTS="$2"; shift 2 ;;
    --rounds) ROUNDS="$2"; shift 2 ;;
    *) echo "[two-arms] unknown arg: $1" >&2; exit 2 ;;
  esac
done

LOG_DIR="$ROOT/v2/evidence"
DRIVER_LOG="$LOG_DIR/narr_two_arms_driver.log"
: > "$DRIVER_LOG"
say() { echo "[$(date -Is)] $*" | tee -a "$DRIVER_LOG"; }

# --- 串行纪律：三重并发确认（排除本进程祖先链）
ancestors() { local p=$$; while [[ -n "$p" && "$p" != 0 ]]; do echo "$p"; p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' '); done; }
ANC=" $(ancestors | tr '\n' ' ') "
hits=0
for pat in 'orchestration[[:space:]]+run' 'run_batch' 'nightly\.py'; do
  for pid in $(pgrep -f -- "$pat" 2>/dev/null || true); do
    [[ "$ANC" == *" $pid "* ]] && continue
    line=$(ps -o args= -p "$pid" 2>/dev/null || true)
    case "$line" in *"tools/d9i/run_two_arms.sh"*) continue ;; esac
    [[ -n "$line" ]] && { say "CONCURRENCY HIT [$pat] pid=$pid: $line"; hits=$((hits+1)); }
  done
done
[[ "$hits" -eq 0 ]] || { say "ABORT: 检测到并发跑批 hits=$hits"; exit 9; }
say "concurrency check: 0 hits"

bash tools/d5/preflight.sh --tag narr_two_arms 2>&1 | tail -2 | tee -a "$DRIVER_LOG" || { say "ABORT: preflight FAIL"; exit 9; }
say "code_sha=$(git rev-parse HEAD)"

run_arm() {
  local arm="$1" out="$2"
  say "=== ARM $arm START (out=$out) ==="
  bash tools/d9i/launch_narration_arm.sh "$arm" "$out" --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" >> "$DRIVER_LOG" 2>&1
  local rc=$?
  local lc=$(cat "$out/llm_cost.rc" 2>/dev/null || echo missing)
  say "=== ARM $arm END rc=$rc llm_cost_rc=$lc ==="
  [[ "$rc" -eq 0 ]] || { say "ABORT: arm $arm run_batch rc=$rc"; return 1; }
  [[ "$lc" == "0" ]] || { say "ABORT: arm $arm llm-cost rc=$lc（该臂无效，不得用别的证据替代）"; return 1; }
  return 0
}

run_arm off "$LOG_DIR/narr-off-20261030" || { say "STOP after OFF arm"; exit 10; }
run_arm on  "$LOG_DIR/narr-on-20261030"  || { say "STOP after ON arm"; exit 11; }

say "BOTH ARMS DONE"
{
  echo "=== both arms summary $(date -Is)"
  for a in off on; do
    d="$LOG_DIR/narr-$a-20261030"
    echo "--- arm=$a"
    echo "code_sha=$(python3 -c "import json;print(json.load(open('$d/meta.json'))['code_sha'])" 2>/dev/null || echo NA)"
    cat "$d/start_end.txt" 2>/dev/null
  done
} | tee -a "$DRIVER_LOG"
