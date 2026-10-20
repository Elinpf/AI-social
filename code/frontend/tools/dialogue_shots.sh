#!/usr/bin/env bash
# dialogue_shots.sh — 出 D7 演示截图（真实日志渲染；命名规范 <batch>-<view>-<sha8>.png）。
#
# 用法：
#   bash frontend/tools/dialogue_shots.sh <base_url> <data_rel> <batch_label> <log_sha8> [out_dir]
# 例：
#   bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
#        sample/dialogue_demo/threads.json p1_final_n20_llm fb832372 ./shots
#
# 前置：静态服务在跑（cd code && python frontend/tools/serve.py）且在仓库 code/ 下执行。
# 输出（全部真实渲染，非拼图、不跨批混拼）：
#   <batch>-chat-<sha8>.png     1400x900  对话流（全量口径 ?still=1&multi=0&min=0）
#   <batch>-rhythm-<sha8>.png   1300x1050 节律·串门（?view=rhythm）
#   <batch>-spread-<sha8>.png   1300x900  闲话怎么传开（?view=spread）
#   <batch>-600-<sha8>.png      600x900   600px 判读（全量口径）
set -uo pipefail

BASE="${1:?需要 base_url（如 http://127.0.0.1:8848）}"
DATA="${2:?需要 threads.json 相对路径（页面 ?data= 用）}"
BATCH="${3:?需要 batch_label}"
SHA8="${4:?需要日志 sha 前 8 位}"
OUTDIR="${5:-./shots}"
mkdir -p "$OUTDIR"

SHOT="frontend/tools/shot.py"
COMMON="--no-blank-check"

shot () { # name w h query
  local name="$1" w="$2" h="$3" q="$4"
  local out="$OUTDIR/${BATCH}-${name}-${SHA8}.png"
  echo "→ $out"
  python3 "$SHOT" --url "${BASE}/dialogue.html?${q}&data=${DATA}" \
      --out "$out" --width "$w" --height "$h" $COMMON || return 1
}

shot chat   1400 900  "still=1&multi=0&min=0" || exit 1
shot rhythm 1300 1050 "still=1&multi=0&min=0&view=rhythm" || exit 1
shot spread 1300 900  "still=1&multi=0&min=0&view=spread" || exit 1
shot 600     600 900  "still=1&multi=0&min=0" || exit 1

echo "OK: $OUTDIR/${BATCH}-{chat,rhythm,spread,600}-${SHA8}.png"
