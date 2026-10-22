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
           --finished-at "$FINISHED" --duration-sec "$((T1 - T0))")
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
