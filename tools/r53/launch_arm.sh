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
#   0b  并发探针（四条：锚定真实跑批调用形态；bracket 防自匹配）
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
# 探针收窄（事故根因：`pgrep -f` 匹配**整条 cmdline 子串**，人为只读监视壳的命令行里
# 只要出现字面量 `run_batch.rc`（例如 `ls … | grep -E 'meta.json|run_batch.rc'`）就会被
# 裸模式 `[r]un_[b]atch` 命中 ⇒ 整臂中止。R52、R53 各中一次，每次约 25 分钟真 LLM 损失）。
# 修法：只认「真实跑批进程」的调用形态（四条都锚定到可执行/脚本名本身，且要求名字后
# 紧跟空白或行尾），不做「删检查 / 永远 pass」的降级：
#   a) `python3 -m orchestration run …`  —— 跑批的 Python 主体（tools/d2/run_batch.sh:58；
#      要求 `-m` 前缀：仓库里所有真实调用都是 `-m orchestration run`，裸 `orchestration run`
#      子串同样可能出现在只读壳/RG 命令行里 ⇒ 一并收窄）
#   b) `bash …/run_batch.sh <args>`       —— 跑批封装；`.sh` 后必须是空白/行尾 ⇒ `run_batch.rc` 不命中
#   c) `bash …/arm_inner.sh <arm>`        —— 臂批体（launch_arm.sh 用 setsid 拉起）；覆盖
#                                            「run_batch.sh 还没起来 / 已退出但 flock 仍持有」的窗口
#   d) `…/nightly.py <args>`              —— 历史夜间批
# 为什么不漏报：真正的并发只有这四种形态能起跑（launch_arm.sh → arm_inner.sh → run_batch.sh
# → orchestration run），每条真跑批链路至少命中 (b)+(c) 中的一条；闸门0 的 flock 仍是第一道硬锁。
GATE0B_PATTERNS=(
  "[-]m[[:space:]]+orchestration[[:space:]]+run"
  "[r]un_batch\.sh([[:space:]]|$)"
  "[a]rm_inner\.sh([[:space:]]|$)"
  "[n]ightly\.py([[:space:]]|$)"
)
echo "---- [闸门0b] 并发检查（${#GATE0B_PATTERNS[@]} 条，锚定真实跑批调用形态）----" | tee -a "$LE"
for pat in "${GATE0B_PATTERNS[@]}"; do
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
