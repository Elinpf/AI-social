#!/usr/bin/env bash
# R52 双臂批体（由 tools/r52/launch_arm.sh 用 setsid 拉起；本文件不前台阻塞、不长 sleep）
#
# 纪律：
#   * `flock -n /tmp/hitt.batch.lock` 全程持锁（fd 9）——拿不到立刻 exit 22，不静默降级；
#   * 心跳 30s（只写一个时间戳文件，供人肉观测，不参与判定）；
#   * 除一个变量 `HITT_SCENE_FRESH` 外，两臂 INLINE_ENV **逐字相同**（见 R52 预登记 §3）。
#
# 用法：bash arm_inner.sh off|on
set -uo pipefail

WT="/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment"
ARM="${1:?usage: arm_inner.sh off|on}"
SEED=42; AGENTS=16; ROUNDS=36; FLUSH=2
TAG="r52-scene-fresh-${ARM}"
OUT_DIR="$WT/v2/evidence/${TAG}-20261102_n${AGENTS}r${ROUNDS}_s${SEED}"
SIDE_ROOT="/tmp/r52_scene_fresh_${ARM}_n${AGENTS}r${ROUNDS}_s${SEED}_side"
LOCK=/tmp/hitt.batch.lock
HOSTLOG="$OUT_DIR/host.log"

# 两臂共同点：处境锚臂打开（SCENE=1），保证两臂都读场景行，差异只在"取值时点"
COMMON_ENV="HITT_LLM_PROVIDER=openai_compat HITT_WORLD_SEED=${SEED} LIFE_PROMPT_SCENE=1"
if [[ "$ARM" == "on" ]]; then
  INLINE_ENV="$COMMON_ENV HITT_SCENE_FRESH=1"
else
  INLINE_ENV="$COMMON_ENV"
fi

mkdir -p "$OUT_DIR"

# ---- 闸门0：全局跑批锁，整个批次期间持有 ----
exec 9>"$LOCK"
if ! flock -n 9; then
  {
    echo "[$TAG] flock busy：$LOCK 已被占用，持有者（fuser -v）："
    fuser -v "$LOCK" 2>&1 || true
  } >> "$HOSTLOG"
  echo 22 > "$OUT_DIR/run_batch.rc"
  exit 22
fi

# ---- 心跳（存活可见） ----
( while : ; do date -Is > "$OUT_DIR/heartbeat.txt"; sleep 30; done ) &
HB=$!

echo "[$TAG] inner start_at=$(date -Is) pid=$$ lock=held host=$(hostname)" >> "$HOSTLOG"
cd "$WT/code" || { echo 97 > "$OUT_DIR/run_batch.rc"; kill "$HB" 2>/dev/null; exit 97; }
set -a; . "$WT/code/.env.local"; set +a
# shellcheck disable=SC2086
export $INLINE_ENV
echo $$ > "$OUT_DIR/pid.txt"

{
  echo "# R52 臂 $ARM 实际 env（INLINE_ENV + .env.local 键名）"
  echo "INLINE_ENV=$INLINE_ENV"
  echo "HITT_SCENE_FRESH=${HITT_SCENE_FRESH:-<unset>}"
  echo "LIFE_PROMPT_SCENE=${LIFE_PROMPT_SCENE:-<unset>}"
  echo "HITT_LLM_PROVIDER=${HITT_LLM_PROVIDER:-<unset>}"
  echo "HITT_WORLD_SEED=${HITT_WORLD_SEED:-<unset>}"
  echo "code_sha=$(git -C "$WT" rev-parse HEAD)"
  echo "branch=$(git -C "$WT" branch --show-current)"
} > "$OUT_DIR/env_manifest.txt"

bash "$WT/tools/d2/run_batch.sh" \
  --out-dir "$OUT_DIR" --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" \
  --flush-every "$FLUSH" --side-root "$SIDE_ROOT" >> "$HOSTLOG" 2>&1
RC=$?

kill "$HB" 2>/dev/null
echo "$RC" > "$OUT_DIR/run_batch.rc"
echo "[$TAG] finished_at=$(date -Is) rc=$RC" >> "$HOSTLOG"
exit 0
