#!/usr/bin/env bash
# tools/d5/preflight.sh — 跑批前「串行纪律 + 代码树确定」代码闸
#
# 背景：仓库没有全局跑批锁，串行纪律长期靠人肉 pgrep；一次串跑/跑错树的代价是
# 数十分钟跑批 + 报告返工（CYCLE-05 的 F-2 事故同源）。本脚本把纪律固化成可复算的门闸。
#
# 检查项（按序全部执行，任一项失败即 exit 9）：
#   1) 三重并发检查（pgrep -f，命中任一即失败）：
#        a) -m[[:space:]]+orchestration[[:space:]]+run  —— 已有跑批在跑世界（锚定 `-m` 前缀）
#        b) run_batch\.sh([[:space:]]|$)      —— 已有 run_batch 封装在跑（**收窄**：见下）
#        c) nightly\.py([[:space:]]|$)        —— 夜间批在跑
#      说明：pgrep 会自动排除自身；此外显式排除**当前进程的全部祖先链**，
#      因此由 run_batch.sh 调用本脚本时不会把自己（run_batch）判成冲突。
#      **为什么 b 必须收窄**（R52/R53 各被误判一次、每次约 25 分钟真 LLM 损失）：
#      裸模式 `run_batch` 会命中**任何** cmdline 里含该子串的进程，包括只读监视壳
#      `ls … | grep -E 'meta.json|run_batch.rc'`（现场证据
#      v2/evidence/r53-gate0b-falsepositive-20261102/）。收窄后要求 `.sh` 后紧跟空白/行尾，
#      故 `run_batch.rc` 不命中；真跑批链路 `bash …/run_batch.sh <args>` 仍必然命中。
#      同一收窄同步用于 tools/r5x/launch_arm.sh 的闸门0b（那里 4 条探针，另含 arm_inner.sh）。
#   2) 代码树干净度：调用 tools/d5/check_clean_tree.py（冻结区 code/{life,orchestration,config,engine}
#      有任何 modified/staged/untracked 即失败；退出码 1=FAIL、2=UNDECIDABLE 均按失败处理）。
#   3) 留存锚点：记录 `git rev-parse HEAD`、分支名、ISO 时间戳与三项检查结果到可留存文件。
#
# 用法（仓库内任意目录可执行）：
#   bash tools/d5/preflight.sh [--repo <path>] [--log-dir <dir>] [--tag <name>] [--quiet]
#
# 退出码：0 = PASS（打印一行 PASS 摘要）；9 = 任一检查失败/无法判定。
# 依赖：bash、pgrep、ps、git、python3（均为仓库既有依赖）
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$ROOT"
LOG_DIR=""
TAG=""
QUIET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --log-dir) LOG_DIR="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "[preflight] unknown arg: $1" >&2; exit 9 ;;
  esac
done

REPO="$(cd "$REPO" && pwd)" || { echo "[preflight] FAIL: repo 不存在: $REPO" >&2; exit 9; }
[[ -n "$LOG_DIR" ]] || LOG_DIR="$REPO/v2/evidence/preflight"
mkdir -p "$LOG_DIR" || { echo "[preflight] FAIL: 无法创建日志目录 $LOG_DIR" >&2; exit 9; }

TS_ISO="$(date -Iseconds)"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"

# --- 祖先链排除：由 run_batch.sh 调用时，不能把自己算成并发 -------------------
ancestor_pids() {
  local pid=$$
  local depth=0
  while [[ -n "$pid" && "$pid" != "0" && "$depth" -lt 64 ]]; do
    echo "$pid"
    pid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')"
    depth=$((depth + 1))
  done
}
ANCESTORS=" $(ancestor_pids | tr '\n' ' ') "

git_meta() {
  ( cd "$REPO" && git rev-parse HEAD 2>/dev/null ) || echo "UNKNOWN"
}
BRANCH="$( cd "$REPO" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo UNKNOWN )"
HEAD_SHA="$(git_meta)"
SHA8="${HEAD_SHA:0:8}"
LOG_FILE="$LOG_DIR/preflight_${TS_UTC}_${SHA8}${TAG:+_$TAG}.log"

FAILS=()
declare -a HIT_ORCH=() HIT_BATCH=() HIT_NIGHTLY=()

log() { echo "$*" | tee -a "$LOG_FILE" >/dev/null; }

{
  echo "# preflight log"
  echo "ts_iso=$TS_ISO"
  echo "ts_utc=$TS_UTC"
  echo "repo=$REPO"
  echo "branch=$BRANCH"
  echo "head=$HEAD_SHA"
  echo "self_pid=$$"
  echo "ancestors=$ANCESTORS"
} > "$LOG_FILE"

# --- 1) 三重并发检查 ---------------------------------------------------------
scan_pattern() {
  # $1 = 模式名, $2 = pgrep ERE。输出命中行（已剔除祖先链、自身、以及 preflight 自身的子 shell）
  local label="$1" pat="$2" pids pid line
  pids="$(pgrep -f -- "$pat" 2>/dev/null || true)"
  for pid in $pids; do
    [[ "$pid" == "$$" ]] && continue
    if [[ "$ANCESTORS" == *" $pid "* ]]; then continue; fi
    line="$(ps -o pid= -o args= -p "$pid" 2>/dev/null | sed 's/^ *//' || true)"
    [[ -n "$line" ]] || continue
    # 排除 preflight 自己的调用链（含 $(...) 子 shell：子 shell 继承父 cmdline 但 pid 不同，
    # 若调用方传了 `--tag run_batch` 之类含关键词的实参，会把自己误判成并发）
    case "$line" in *"tools/d5/preflight.sh"*) continue ;; esac
    echo "$label|$pid|$line"
  done
}

mapfile -t RAW_ORCH < <(scan_pattern orchestration_run '[-]m[[:space:]]+orchestration[[:space:]]+run')
mapfile -t RAW_BATCH < <(scan_pattern run_batch 'run_batch\.sh([[:space:]]|$)')
mapfile -t RAW_NIGHTLY < <(scan_pattern nightly_py 'nightly\.py([[:space:]]|$)')

HIT_ORCH=("${RAW_ORCH[@]:-}")
HIT_BATCH=("${RAW_BATCH[@]:-}")
HIT_NIGHTLY=("${RAW_NIGHTLY[@]:-}")

log "## 1) concurrency scan"
for r in "${RAW_ORCH[@]:-}"; do [[ -n "$r" ]] && log "HIT orchestration_run: $r"; done
for r in "${RAW_BATCH[@]:-}"; do [[ -n "$r" ]] && log "HIT run_batch: $r"; done
for r in "${RAW_NIGHTLY[@]:-}"; do [[ -n "$r" ]] && log "HIT nightly_py: $r"; done
n_orch=0; n_batch=0; n_nightly=0
for r in "${RAW_ORCH[@]:-}"; do [[ -n "$r" ]] && n_orch=$((n_orch+1)); done
for r in "${RAW_BATCH[@]:-}"; do [[ -n "$r" ]] && n_batch=$((n_batch+1)); done
for r in "${RAW_NIGHTLY[@]:-}"; do [[ -n "$r" ]] && n_nightly=$((n_nightly+1)); done
log "concurrency_hits orchestration_run=$n_orch run_batch=$n_batch nightly_py=$n_nightly"
[[ "$n_orch" -eq 0 ]] || FAILS+=("concurrency:orchestration_run=$n_orch")
[[ "$n_batch" -eq 0 ]] || FAILS+=("concurrency:run_batch=$n_batch")
[[ "$n_nightly" -eq 0 ]] || FAILS+=("concurrency:nightly_py=$n_nightly")

# --- 2) 代码树干净度 --------------------------------------------------------
log "## 2) clean tree check (code/{life,orchestration,config,engine})"
CLEAN_LOG="$LOG_DIR/clean_tree_${TS_UTC}_${SHA8}${TAG:+_$TAG}.json"
CLEAN_OUT="$(cd "$REPO" && python3 tools/d5/check_clean_tree.py --repo "$REPO" --out "$CLEAN_LOG" 2>&1)"
CLEAN_RC=$?
echo "$CLEAN_OUT" >> "$LOG_FILE"
log "clean_tree_rc=$CLEAN_RC out=$CLEAN_LOG"
if [[ "$CLEAN_RC" -ne 0 ]]; then
  if [[ "$CLEAN_RC" -eq 1 ]]; then FAILS+=("dirty_frozen_tree(rc=1)"); else FAILS+=("clean_tree_undecidable(rc=$CLEAN_RC)"); fi
  # 只摘出阻断项，避免把整个 JSON 灌到终端
  BLOCKING_LINES="$(echo "$CLEAN_OUT" | python3 -c '
import json,sys
raw=sys.stdin.read()
try:
    i=raw.index("{")
    d=json.loads(raw[i:])
except Exception:
    sys.exit(0)
for b in d.get("blocking",[])[:20]:
    print("  BLOCKING %s %s" % (b.get("status"), b.get("path")))
' 2>/dev/null || true)"
  [[ -n "$BLOCKING_LINES" ]] && { echo "$BLOCKING_LINES" | tee -a "$LOG_FILE" >/dev/null; echo "$BLOCKING_LINES" >&2; }
fi

# --- 3) 锚点留存 -----------------------------------------------------------
log "## 3) anchor"
log "rev_parse_HEAD=$HEAD_SHA branch=$BRANCH ts_iso=$TS_ISO"

# --- 结论 ------------------------------------------------------------------
if [[ "${#FAILS[@]}" -gt 0 ]]; then
  {
    echo "verdict=FAIL"
    echo "reasons=${FAILS[*]}"
  } >> "$LOG_FILE"
  echo "[preflight] FAIL exit=9 reasons=${FAILS[*]}" >&2
  echo "[preflight] log: $LOG_FILE" >&2
  exit 9
fi

{
  echo "verdict=PASS"
} >> "$LOG_FILE"

SUMMARY="PASS preflight sha=$SHA8($BRANCH) ts=$TS_ISO concurrency=0 frozen_tree=clean log=$LOG_FILE"
if [[ "$QUIET" -eq 1 ]]; then
  echo "$SUMMARY"
else
  echo "$SUMMARY"
fi
exit 0
