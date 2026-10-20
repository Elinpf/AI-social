#!/usr/bin/env bash
# dialogue_shots.sh — 出 D7 演示截图（真实渲染；命名 <batch>-<view>-<sha8>.png）。
#
# 用法：
#   bash frontend/tools/dialogue_shots.sh <base_url> <data_rel> [batch] [sha8] [out_dir]
#
#   batch / sha8 **可省略**：省略时从 threads.json 的 source.run_label / source.run_sha256 自动派生；
#   显式传入时会**自校验**——与 threads.json 对不上就报错退出（防止人工传错把截图贴错标签）。
#
# 例（全自动，最稳）：
#   bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
#        sample/dialogue_demo/threads.json
#
# 前置：静态服务在跑（cd code && python frontend/tools/serve.py），且在仓库 code/ 下执行。
# 输出：
#   <batch>-chat-<sha8>.png     1400x900  对话流（全量口径 ?still=1&multi=0&min=0）
#   <batch>-rhythm-<sha8>.png   1300x1050 节律·串门（?view=rhythm）
#   <batch>-spread-<sha8>.png   1300x900  闲话怎么传开（?view=spread）
#   <batch>-600-<sha8>.png      600x900   600px 判读（全量口径）
set -uo pipefail

BASE="${1:?需要 base_url（如 http://127.0.0.1:8848）}"
DATA="${2:?需要 threads.json 相对路径（页面 ?data= 用，相对 code/frontend）}"
WANT_BATCH="${3:-}"
WANT_SHA8="${4:-}"
OUTDIR="${5:-./shots}"

# ---- 从 threads.json 取事实（label 与日志字节 sha），不靠人填 ----
META=$(python3 - "$DATA" <<'PY'
import json, sys, pathlib
p = pathlib.Path("frontend") / sys.argv[1]
d = json.loads(p.read_text(encoding="utf-8"))
src = d.get("source") or {}
print(src.get("run_label") or "")
print(src.get("run_sha256") or "")
PY
) || { echo "读取 $DATA 失败（需先跑 gen_threads.py 生成）" >&2; exit 2; }
LABEL=$(echo "$META" | sed -n 1p)
RUN_SHA=$(echo "$META" | sed -n 2p)
SHA8="${RUN_SHA:0:8}"
# 文件名用「去掉 -sha8 后缀的批次名」，避免出现 <label>-<view>-<sha8> 里 sha8 重复
STEM="${LABEL%-$SHA8}"

[ -n "$LABEL" ] || { echo "threads.json 缺 source.run_label，请用 --label 生成" >&2; exit 2; }
[ -n "$RUN_SHA" ] || { echo "threads.json 缺 source.run_sha256" >&2; exit 2; }

# ---- 自校验：人工传入值必须与数据源一致 ----
if [ -n "$WANT_BATCH" ] && [ "$WANT_BATCH" != "$LABEL" ]; then
  echo "FAIL 传入 batch='$WANT_BATCH' 与 threads.json source.run_label='$LABEL' 不一致" >&2; exit 2
fi
if [ -n "$WANT_SHA8" ] && [ "$WANT_SHA8" != "$SHA8" ]; then
  echo "FAIL 传入 sha8='$WANT_SHA8' 与 threads.json 日志 sha 前缀 '$SHA8' 不一致（run_sha256=$RUN_SHA）" >&2; exit 2
fi

mkdir -p "$OUTDIR"
SHOT="frontend/tools/shot.py"
echo "batch=$LABEL  log_sha256=$RUN_SHA  sha8=$SHA8"

shot () { # name w h query
  local name="$1" w="$2" h="$3" q="$4"
  local out="$OUTDIR/${STEM}-${name}-${SHA8}.png"
  echo "→ $out"
  python3 "$SHOT" --url "${BASE}/dialogue.html?${q}&data=${DATA}" \
      --out "$out" --width "$w" --height "$h" --no-blank-check || return 1
}

shot chat   1400 900  "still=1&multi=0&min=0" || exit 1
shot rhythm 1300 1050 "still=1&multi=0&min=0&view=rhythm" || exit 1
shot spread 1300 900  "still=1&multi=0&min=0&view=spread" || exit 1
shot 600     600 900  "still=1&multi=0&min=0" || exit 1

echo "OK: $OUTDIR/${STEM}-{chat,rhythm,spread,600}-${SHA8}.png"
