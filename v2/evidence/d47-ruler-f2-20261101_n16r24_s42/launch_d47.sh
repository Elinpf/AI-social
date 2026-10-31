#!/usr/bin/env bash
# launch_d47.sh — CYCLE-47 · D47 批起跑包装器（evidence-reporter，2026-11-01）
#
# 目的：**不改居民行为**（本轮只改尺子 tools/public_talk/），在真 LLM 批次上验证
#       修后尺子（ruler-f2/1，msg_uid 主键）可用 + 拿真 LLM 成本证据 + 出真实截图。
#       单臂：HITT_DIALOGUE_PUBLIC_REPLY=1（与 r41v ON 臂同配置，便于与历史批次做
#       「引擎事件侧应一致」的对照说明）。
#
# 纪律：
#   - 起跑前三重并发检查（bracket 防自匹配），原文写进 launch_evidence.txt；
#   - 仓库权威闸 tools/d5/preflight.sh（祖先链排除，不会把本脚本自身判成并发）；
#   - 冻结区 code/{life,orchestration,config,engine} 零改动（check_clean_tree.py）；
#   - 外层 setsid 启动（run_batch.sh 自身不含 setsid）；
#   - 启动器 argv 只含本脚本路径，run_batch 调用行藏在本脚本内部（防 preflight 误判，基线 §3.2）。
#
# 用法（仓库根执行）：
#   bash v2/evidence/d47-ruler-f2-20261101_n16r24_s42/launch_d47.sh
set -uo pipefail

WT="/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment"
cd "$WT" || exit 97
SEED=42; AGENTS=16; ROUNDS=24; FLUSH=2
TAG=d47
OUT_DIR="$WT/v2/evidence/d47-ruler-f2-20261101_n${AGENTS}r${ROUNDS}_s${SEED}"
SIDE_ROOT="/tmp/d47_ruler_f2_n${AGENTS}r${ROUNDS}_s${SEED}_side"
LE="$OUT_DIR/launch_evidence.txt"
HOSTLOG="$OUT_DIR/host.log"
mkdir -p "$OUT_DIR"

fail() { echo "!! 闸门失败：$1" | tee -a "$LE"; exit "${2:-20}"; }

{
  echo "================ D47 起批证据（单臂 HITT_DIALOGUE_PUBLIC_REPLY=1，只改尺子） ================"
  echo "采集时刻: $(date -Is)"
  echo "repo:      $WT"
  echo "branch:    $(git -C "$WT" branch --show-current 2>&1)"
  echo "HEAD:      $(git -C "$WT" rev-parse HEAD 2>&1)"
  echo "out_dir:   $OUT_DIR"
  echo "side_root: $SIDE_ROOT"
  echo "params:    seed=$SEED agents=$AGENTS rounds=$ROUNDS flush_every=$FLUSH"
  echo "臂:        ON（HITT_DIALOGUE_PUBLIC_REPLY=1），与 r41v ON 臂同配置"
} | tee "$LE"

# ---- 闸门1：串行铁律（三重并发，bracket 防自匹配） ----
echo "---- [闸门1] 三重并发检查（原文） ----" | tee -a "$LE"
{
  echo "\$ ps -eo pid,args | grep -E 'orchestration run|run_batch\.sh|nightly\.py' | grep -v grep"
  ps -eo pid,args | grep -E 'orchestration run|run_batch\.sh|nightly\.py' | grep -v grep
  echo "ps_grep_rc=$? (1=无命中)"
} | tee -a "$LE"
for pat in "orchestration[[:space:]]+run" "[r]un_[b]atch" "[n]ightly\.py"; do
  if pgrep -f "$pat" >/dev/null 2>&1; then
    pgrep -fa "$pat" | tee -a "$LE"; fail "闸门1：检出并发进程 /$pat/" 22
  fi
  echo "  pgrep -f '/$pat/' => 无命中 PASS" | tee -a "$LE"
done

# ---- 闸门1c：仓库权威 preflight ----
( cd "$WT" && bash tools/d5/preflight.sh --tag "${TAG}" --log-dir "$OUT_DIR" ) 2>&1 | tee -a "$LE"
[ "${PIPESTATUS[0]}" = "0" ] || fail "闸门1c：tools/d5/preflight.sh 失败（并发/脏树/不可判定）" 22

# ---- 闸门2：冻结区干净 ----
( cd "$WT" && python3 tools/d5/check_clean_tree.py ) > "$OUT_DIR/clean_tree.json" 2>&1 || fail "闸门2：code/ 冻结区不干净" 29
echo "---- [闸门2] check_clean_tree verdict=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["verdict"])' "$OUT_DIR/clean_tree.json") ----" | tee -a "$LE"

# ---- 指纹留存 ----
git -C "$WT" rev-parse HEAD > "$OUT_DIR/frozen_sha.txt"
git -C "$WT" status --porcelain > "$OUT_DIR/git_status_start.txt"
{
  echo "# 冻结区代码切片 sha256（本批实际执行的树）"
  git -C "$WT" rev-parse HEAD
  sha256sum "$WT/code/life/public_talk.py" "$WT/code/life/agent.py" \
            "$WT/code/orchestration/integration.py" "$WT/tools/d2/run_batch.sh" 2>/dev/null
} > "$OUT_DIR/code_slice_check.txt"
{
  echo "# 读数器 / 渲染器指纹（本轮修复对象是 public_talk_metrics.py）"
  sha256sum "$WT/tools/public_talk/public_talk_metrics.py" "$WT/tools/metrics/render_shots.py" \
            "$WT/tools/d5/preflight.sh" "$WT/tools/d5/check_clean_tree.py" 2>/dev/null
} > "$OUT_DIR/ruler_fingerprint.txt"
cat "$OUT_DIR/ruler_fingerprint.txt" | tee -a "$LE"

# ---- .env.local 存在性（开关不得写在 .env.local 里） ----
[ -f "$WT/code/.env.local" ] || fail "无 code/.env.local" 31
grep -qE "^[[:space:]]*(export[[:space:]]+)?HITT_DIALOGUE_PUBLIC_REPLY" "$WT/code/.env.local" \
  && fail ".env.local 内混入开关" 32
echo "闸门2b PASS：.env.local 未混入开关变量" | tee -a "$LE"

# ---- setsid 启动 ----
INLINE_ENV="HITT_LLM_PROVIDER=openai_compat HITT_WORLD_SEED=$SEED HITT_DIALOGUE_PUBLIC_REPLY=1"
INNER="cd '$WT/code' && set -a && . '$WT/code/.env.local' && set +a && export $INLINE_ENV && echo \$\$ > '$OUT_DIR/pid.txt' && bash '$WT/tools/d2/run_batch.sh' --out-dir '$OUT_DIR' --seed $SEED --agents $AGENTS --rounds $ROUNDS --flush-every $FLUSH --side-root '$SIDE_ROOT' >> '$HOSTLOG' 2>&1; echo \$? > '$OUT_DIR/run_batch.rc'"
{
  echo "[d47] launcher=v2/evidence/$(basename "$OUT_DIR")/launch_d47.sh mode=setsid"
  echo "[d47] INLINE_ENV=$INLINE_ENV"
  echo "[d47] code_sha=$(git -C "$WT" rev-parse HEAD) branch=$(git -C "$WT" branch --show-current)"
  echo "[d47] started_at=$(date -Is)"
} | tee -a "$HOSTLOG" > "$OUT_DIR/launch_cmd.txt"

T0=$(date +%s)
setsid bash -c "$INNER" < /dev/null > /dev/null 2>&1 &
SETSID_PID=$!
echo "$T0" > "$OUT_DIR/start_epoch.txt"
echo "launched setsid_pid=$SETSID_PID start_epoch=$T0 out=$OUT_DIR"
{
  echo "---- [启动自证] ----"
  echo "setsid_pid=$SETSID_PID"
  echo "start_epoch=$T0 captured_at=$(date -Is)"
} | tee -a "$LE"
exit 0
