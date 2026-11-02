#!/usr/bin/env bash
# D2 跑批封装：跑一批世界（真/mock LLM），落 run.jsonl，并调用**单一真源**的
# `tools/d2/emit_run_meta.py` 生成 meta.json（provider/model 由运行期 LLM_CALL 推导，
# 不采用命令行声明；Leader 裁决：meta.provider 不是事实）。
#
# 用法（在仓库根执行）：
#   bash tools/d2/run_batch.sh --out-dir v2/evidence/run_d2_before_n16_seed42 \
#       --seed 42 --agents 16 --rounds 84 [--mock] [--side-root /tmp/d2_before16_side]
#
# 退出码：3 = wc -l != meta.events；4 = 非真跑；5 = 日志内 spec 与声明不一致；6 = obs llm-cost 门禁失败
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CODE="$ROOT/code"
OUT_DIR=""
SEED=42
AGENTS=16
ROUNDS=84
MOCK=0
SIDE_ROOT=""
FLUSH_EVERY=2
MOCK_PRECALIB_MSG="${MOCK_PRECALIB_MSG:-0}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --agents) AGENTS="$2"; shift 2 ;;
    --rounds) ROUNDS="$2"; shift 2 ;;
    --side-root) SIDE_ROOT="$2"; shift 2 ;;
    --flush-every) FLUSH_EVERY="$2"; shift 2 ;;
    --mock-precalib-msg) MOCK_PRECALIB_MSG="$2"; shift 2 ;;
    --mock) MOCK=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$OUT_DIR" ]] || { echo "--out-dir required" >&2; exit 2; }

# --- 串行纪律代码闸（tools/d5/preflight.sh）：并发跑批 / 冻结区脏树 → exit 9 ---
# 说明：preflight.sh 会排除自身祖先链，因此这里不会把本 run_batch 判成并发。
bash "$ROOT/tools/d5/preflight.sh" --tag run_batch || exit 9

mkdir -p "$OUT_DIR"
OUT_ABS="$(cd "$OUT_DIR" && pwd)"
RUN="$OUT_ABS/run.jsonl"

# --- 冻结区零改动：EXIT trap 落盘（看板 A-3）---------------------------------------
# 为什么用 trap：跑批中途 `exit` / `set -e` 触发的任何一条退出路径都要留下证据，
# 否则「批结束时冻结区动没动」就只存在于人的记忆里。落盘文件名与口径由
# `tools/d2/frozen_zone_diff.py`（冻结区单一真源）定义，`emit_run_meta.py` 会优先读它。
TRAP_OUT="$OUT_ABS/code_frozen_diff_at_exit.txt"
_frozen_zone_exit_trap() {
  local rc=$?
  set +e
  {
    echo "# run_batch EXIT trap at $(date -Iseconds) rc=$rc"
    echo "code_sha=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null)"
    echo "rc=$rc"
    python3 "$ROOT/tools/d2/frozen_zone_diff.py" --repo "$ROOT" --rev "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null)" 2>/dev/null \
      | sed -n 's/^DIFF //p'
  } > "$TRAP_OUT" 2>/dev/null
  return $rc
}
trap _frozen_zone_exit_trap EXIT

# 起跑快照：launcher（launch_arm.sh 一类）通常已写；没有就由这里补，供
# `emit_run_meta.py` 自动探测（看板 A-3 的「起跑 vs 结束」对照）。
if [[ ! -s "$OUT_ABS/git_status_start.txt" ]]; then
  git -C "$ROOT" status --porcelain > "$OUT_ABS/git_status_start.txt" 2>/dev/null || true
fi

cd "$CODE"
# shellcheck disable=SC1091
set -a; . ./.env.local; set +a
if [[ "$MOCK" -eq 0 ]]; then export HITT_LLM_PROVIDER=openai_compat; else unset HITT_LLM_PROVIDER || true; fi
STARTED="$(date -Iseconds)"

ARGS=(--life --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" --out "$RUN" --flush-every "$FLUSH_EVERY")
if [[ -n "$SIDE_ROOT" ]]; then ARGS+=(--side-root "$SIDE_ROOT"); fi

echo "[d2] run: python3 -m orchestration run ${ARGS[*]}"
T0=$(date +%s)
python3 -m orchestration run "${ARGS[@]}"
T1=$(date +%s)
FINISHED="$(date -Iseconds)"

META_ARGS=(--run-dir "$OUT_ABS" --seed "$SEED" --n "$AGENTS" --rounds "$ROUNDS"
           --mock-precalib-msg "$MOCK_PRECALIB_MSG" --started-at "$STARTED"
           --finished-at "$FINISHED" --duration-sec "$((T1 - T0))"
           # live 模式：本进程 environ 就是跑批 environ，比 launcher 只登记几个键的
           # env_manifest.txt 更权威 ⇒ 显式关掉自动探测（回放时才用 --env-manifest）。
           --no-env-manifest)
if [[ "$MOCK" -eq 1 ]]; then META_ARGS+=(--mock); fi
set +e
python3 "$ROOT/tools/d2/emit_run_meta.py" "${META_ARGS[@]}"
RC=$?
set -e
[[ "$RC" -eq 0 ]] || { echo "[d2] FAIL: emit_run_meta exit=$RC" >&2; exit "$RC"; }
# 护栏：批结束后 meta 必须存在（防止「末尾写 meta」静默失败 ⇒ 证据无锚点）
[[ -s "$OUT_ABS/meta.json" ]] || { echo "[d2] FAIL: meta.json 未生成（$OUT_ABS/meta.json）" >&2; exit 7; }

LINES=$(wc -l < "$RUN")
MEV=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['events'])" "$OUT_ABS/meta.json")
echo "[d2] self-check wc -l=$LINES meta.events=$MEV"
[[ "$LINES" -eq "$MEV" ]] || { echo "[d2] FAIL: line count != meta.events" >&2; exit 3; }

# --- 真跑门禁（硬证据：运行期 provider + obs llm-cost）---
if [[ "$MOCK" -eq 0 ]]; then
  OUT="/tmp/d2_llmcost_$$.out"
  if ! python3 -m obs llm-cost --log "$RUN" --require-provider openai_compat > "$OUT" 2>&1; then
    echo "[d2] FAIL(obs llm-cost 门禁)" >&2; cat "$OUT" >&2; exit 6
  fi
  tail -3 "$OUT"
fi
echo "[d2] OK"
