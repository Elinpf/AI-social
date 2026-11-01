#!/usr/bin/env bash
# R53 单臂启动器（闸门 + 证据锚点 + setsid 后台拉起 tools/r53/arm_inner.sh）
#
# 用法（任意目录）：
#   bash tools/r53/launch_arm.sh off      # OFF 臂：HITT_SCHEDULE_OFFSET 不设（作息无相位偏移）
#   bash tools/r53/launch_arm.sh on       # ON 臂：唯一差异 HITT_SCHEDULE_OFFSET=1（相位偏移 + 活动类型个体化）
#   DRYRUN=1 bash tools/r53/launch_arm.sh on
#
# 两臂共同点（逐字相同）：LIFE_PROMPT_SCENE=1、HITT_LLM_PROVIDER=openai_compat、HITT_WORLD_SEED=42、
#                          --seed 42 --agents 16 --rounds 36 --flush-every 2
#
# 闸门（任一失败即退出，不降级）：
#   0   flock -n /tmp/hitt.batch.lock 试占（真锁由批体全程持有）
#   0b  三重 pgrep 并发探针（bracket 防自匹配）
#   1   tools/d5/preflight.sh --tag r53-schedule-offset-<arm> --log-dir <out>
#   2   tools/d5/check_clean_tree.py（code/{life,orchestration,config,engine} 零改动）
#   2b  code/.env.local 不得混入臂开关（只允许 HITT_LLM_PROVIDER / LLM_API_KEY）
set -uo pipefail

WT="/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment"
ARM="${1:?usage: launch_arm.sh off|on}"
cd "$WT" || exit 97
SEED=42; AGENTS=16; ROUNDS=36
TAG="r53-schedule-offset-${ARM}"
OUT_DIR="$WT/v2/evidence/${TAG}-20261102_n${AGENTS}r${ROUNDS}_s${SEED}"
SIDE_ROOT="/tmp/r53_schedule_offset_${ARM}_n${AGENTS}r${ROUNDS}_s${SEED}_side"
LOCK=/tmp/hitt.batch.lock
LE="$OUT_DIR/launch_evidence.txt"
HOSTLOG="$OUT_DIR/host.log"
mkdir -p "$OUT_DIR"

fail() { echo "!! 闸门失败：$1" | tee -a "$LE"; exit "${2:-20}"; }

{
  echo "================ R53 臂 ${ARM} 起批证据 ================"
  echo "采集时刻: $(date -Is)"
  echo "repo:      $WT"
  echo "branch:    $(git -C "$WT" branch --show-current 2>&1)"
  echo "HEAD:      $(git -C "$WT" rev-parse HEAD 2>&1)"
  echo "out_dir:   $OUT_DIR"
  echo "side_root: $SIDE_ROOT"
  echo "params:    seed=$SEED agents=$AGENTS rounds=$ROUNDS flush_every=2"
  if [[ "$ARM" == "on" ]]; then
    echo "臂变量:    HITT_SCHEDULE_OFFSET=1（ON 臂，唯一差异）"
  else
    echo "臂变量:    无（OFF 臂，HITT_SCHEDULE_OFFSET 不设）"
  fi
} | tee "$LE"

# ---- 闸门0 ----
echo "---- [闸门0] flock -n $LOCK ----" | tee -a "$LE"
if flock -n "$LOCK" -c 'true' 2>/dev/null; then
  echo "  flock 试占成功（探针即刻释放；真锁由批体进程全程持有）" | tee -a "$LE"
else
  { echo "  锁被占用，持有者（fuser -v $LOCK）："; fuser -v "$LOCK" 2>&1 || true; } | tee -a "$LE"
  fail "闸门0：$LOCK 已被占用（疑似并发跑批）" 22
fi

# ---- 闸门0b ----
echo "---- [闸门0b] 三重并发检查 ----" | tee -a "$LE"
for pat in "orchestration[[:space:]]+run" "[r]un_[b]atch" "[n]ightly\.py"; do
  if pgrep -f "$pat" >/dev/null 2>&1; then
    pgrep -fa "$pat" | tee -a "$LE"; fail "闸门0b：检出并发进程 /$pat/" 22
  fi
  echo "  pgrep -f '/$pat/' => 无命中 PASS" | tee -a "$LE"
done

# ---- 闸门1 ----
( cd "$WT" && bash tools/d5/preflight.sh --tag "$TAG" --log-dir "$OUT_DIR" ) 2>&1 | tee -a "$LE"
[ "${PIPESTATUS[0]}" = "0" ] || fail "闸门1：tools/d5/preflight.sh 失败" 22

# ---- 闸门2 ----
( cd "$WT" && python3 tools/d5/check_clean_tree.py ) > "$OUT_DIR/clean_tree.json" 2>&1 || fail "闸门2：code/ 冻结区不干净" 29
echo "---- [闸门2] check_clean_tree verdict=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["verdict"])' "$OUT_DIR/clean_tree.json") ----" | tee -a "$LE"

# ---- 指纹 ----
git -C "$WT" rev-parse HEAD > "$OUT_DIR/frozen_sha.txt"
git -C "$WT" status --porcelain > "$OUT_DIR/git_status_start.txt"
{
  echo "# R53 冻结区代码切片 sha256（本批实际执行的树，r53 起另含 tools/r53 脚手架）"
  git -C "$WT" rev-parse HEAD
  sha256sum "$WT/code/life/agent.py" "$WT/code/life/scene_anchor.py" \
            "$WT/code/orchestration/integration.py" "$WT/tools/d2/run_batch.sh" 2>/dev/null
} > "$OUT_DIR/code_slice_check.txt"
{
  echo "# 读数器 / 渲染器 / 探针指纹"
  sha256sum "$WT/tools/metrics/scene_fresh_rate.py" "$WT/tools/metrics/place_content_consistency.py" \
            "$WT/tools/metrics/render_shots.py" "$WT/tools/r53/prompt_hash_probe.py" \
            "$WT/tools/r53/launch_arm.sh" "$WT/tools/r53/arm_inner.sh" \
            "$WT/tools/d5/preflight.sh" "$WT/tools/d5/check_clean_tree.py" 2>/dev/null
} > "$OUT_DIR/ruler_fingerprint.txt"
tee -a "$LE" < "$OUT_DIR/ruler_fingerprint.txt"

# ---- 闸门2b ----
[ -f "$WT/code/.env.local" ] || fail "无 code/.env.local" 31
if grep -qE "^[[:space:]]*(export[[:space:]]+)?(HITT_SCHEDULE_OFFSET|LIFE_PROMPT_SCENE|HITT_NEED_SPEECH|HITT_D12_DETAIL|HITT_DIALOGUE_PUBLIC_REPLY|HITT_WEATHER)" "$WT/code/.env.local"; then
  fail ".env.local 内混入臂开关变量" 32
fi
echo "闸门2b PASS：.env.local 未混入臂开关" | tee -a "$LE"

# ---- 干跑 ----
if [[ "${DRYRUN:-0}" == "1" ]]; then
  echo "---- [干跑] DRYRUN=1：闸门全过，未启动任何进程 ----" | tee -a "$LE"
  echo "dryrun_ok arm=$ARM"
  exit 0
fi

# ---- setsid 后台拉起（不前台阻塞） ----
T0=$(date +%s)
echo "$T0" > "$OUT_DIR/start_epoch.txt"
{
  echo "[$TAG] launcher=tools/r53/launch_arm.sh mode=setsid unitless"
  echo "[$TAG] started_at=$(date -Is) code_sha=$(git -C "$WT" rev-parse HEAD) branch=$(git -C "$WT" branch --show-current)"
} >> "$HOSTLOG"
setsid bash "$WT/tools/r53/arm_inner.sh" "$ARM" >> /dev/null 2>&1 &
LAUNCH_PID=$!
echo "launched arm=$ARM setsid_pid=$LAUNCH_PID start_epoch=$T0 out=$OUT_DIR"
{
  echo "---- [启动自证] ----"
  echo "hosting_mode=setsid"
  echo "setsid_pid=$LAUNCH_PID"
  echo "start_epoch=$T0 captured_at=$(date -Is)"
} | tee -a "$LE"
exit 0
