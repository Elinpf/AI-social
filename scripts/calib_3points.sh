#!/usr/bin/env bash
# calib_3points.sh —— 三点标定（16×8 / 32×8 / 16×15）串行起跑，带全部守门
#
# 由来：2026-10-31 一晚踩过 4 个执行层坑——
#   ① 同命令被启动两次、写同一 out 与 side-root（污染批）；
#   ② launch_cmd/switch_proof 被下一次启动覆盖；
#   ③ 用 run.jsonl 行数判活跃 ⇒ 误杀 5 次正常跑批；
#   ④ 0 字节 run.log 分不清"没跑"与"缓冲"。
# 本脚本逐条对治：串行门 / run-id 目录永不覆盖 / 只报不杀 / -u + tee。
#
# 用法：bash scripts/calib_3points.sh            # 真跑
#       bash scripts/calib_3points.sh --dry-run  # 只打印将执行的命令
set -uo pipefail

ROOT=$(git rev-parse --show-toplevel) || { echo "FATAL: 不在 git 仓库内" >&2; exit 4; }
WT="$ROOT/.worktrees/d9t-openings-2"
[ -d "$WT/code" ] || { echo "FATAL: 缺 worktree $WT" >&2; exit 4; }
HEAD_WANT="cef1c58c448d400c0fe98736634cc0891b0a78e6"
ACTUAL=$(git -C "$WT" rev-parse HEAD)
[ "$ACTUAL" = "$HEAD_WANT" ] || { echo "FATAL: worktree HEAD=$ACTUAL ≠ $HEAD_WANT" >&2; exit 23; }

RUN_ID=$(date +%H%M%S)
BASE=/tmp/d9x_calib_$RUN_ID
FIVE="LIFE_PROMPT_NARRATION=1 LIFE_PROMPT_NARRATION_ROTATION=1 LIFE_PROMPT_NARRATION_ACTION=1 LIFE_PROMPT_NARRATION_SYNTAX=1 LIFE_PROMPT_NARRATION_OPENINGS=1"
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1

run_point () {  # $1=agents  $2=rounds  $3=tag
  local agents=$1 rounds=$2 tag=$3
  local out="$BASE/$tag" side="/tmp/d9x_side_${RUN_ID}_${tag}"

  # ① 串行门：任何 orchestration run 在跑就不起（用 ps，避免 pgrep 自匹配）
  local n
  n=$(ps -eo cmd | grep -F "orchestration run" | grep -v grep | grep -v calib_3points | wc -l)
  [ "$n" -eq 0 ] || { echo "ABORT($tag): 已有 $n 个 orchestration run 在跑（串行纪律）" >&2; return 21; }

  mkdir -p "$out"
  [ "$DRY" -eq 1 ] && { echo "[dry] env $FIVE HITT_LLM_PROVIDER=openai_compat python3 -m orchestration run --life --seed 42 --agents $agents --rounds $rounds --out $out/run.jsonl --side-root $side"; return 0; }

  echo "== 起跑 $tag：agents=$agents rounds=$rounds =="
  # ② 取证：先写 launch_cmd（带 run-id，永不覆盖），再取 switch_proof
  { echo "arm=CALIB-$tag run_id=$RUN_ID"; echo "out=$out"; echo "side=$side"; echo "HEAD=$ACTUAL";
    echo "started_at=$(date -Iseconds)"; } > "$out/launch_cmd.txt"
  ( cd "$WT/code" && set -a && . ./.env.local && set +a && \
    env $FIVE HITT_LLM_PROVIDER=openai_compat python3 -u -m orchestration run --life --seed 42 \
      --agents "$agents" --rounds "$rounds" --out "$out/run.jsonl" --side-root "$side" \
      2>&1 | tee "$out/run.log" )
  local rc=${PIPESTATUS[0]}
  echo "finished_at=$(date -Iseconds) rc=$rc" >> "$out/launch_cmd.txt"

  # ③ 只报不杀：三项产出交给 calib_report，异常也不 kill
  python3 "$ROOT/scripts/calib_report.py" "$out" || true
  echo "-- $tag rc=$rc --"
  return 0
}

echo "BASE=$BASE  HEAD=$ACTUAL"
run_point 16  8  A_16x8  || exit $?
run_point 32  8  B_32x8  || exit $?
run_point 16 15  C_16x15 || exit $?
echo "== 三点完成：目录 $BASE =="
