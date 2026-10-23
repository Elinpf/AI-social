#!/usr/bin/env bash
# R21 处境锚 OFF 臂 · worktree 专用起跑脚本（sim-engineer）
#
# 为什么需要这个脚本（不直接用 ON 臂的 launch.sh）：
#   1) ON 臂 launch.sh 把 REPO 写死为主树、硬编码 `WT=${WT:-$REPO}`，且闸门0f 要求
#      `WT == */尝试/social-experiment`（主树）。若把 worktree 传给 WT，闸门0f 会 exit 35，
#      且脚本会用主树 tools/d2/run_batch.sh + 主树 code（HEAD a6d6be0，含 L-13 改动）
#      去跑 OFF 臂 ⇒ 与 3bb4430 的 ON 臂构成双变量，实验作废。
#   2) 本脚本 = ON 臂 launch.sh 的**同构改写**：只把「REPO 解析」从主树改为本 worktree，
#      并保留全部原有门禁（0/0b/0c/1/1c/1d/2b/0e/0f + 开关存在性断言），门禁语义未改。
#      门禁文件（MOCK_GATE / METRICS_GATE）仍指向主树那两份**未跟踪留痕原件**（唯一正本）。
#
# 用法（在 worktree 根执行）：
#   ORDER=off bash v2/evidence/run_scene_anchor_off_seed42_n16r24/launch_worktree.sh off
#
# 纪律：同一时刻只允许一个 orchestration run；setsid 后台；本脚本只负责起跑。
set -u

ARM="${1:?usage: launch_worktree.sh <off|on>}"
case "$ARM" in off|on) ;; *) echo "bad arm: $ARM"; exit 9;; esac

WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"    # = worktree 根
REPO="$WT"                                                      # 行为代码与工具一律取本树
MAIN="${MAIN_TREE:-/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment}"
BRANCH="${BRANCH:-feat/scene-pair-r21}"
SWITCH=LIFE_PROMPT_SCENE
SEED=${SEED:-42}; AGENTS=${AGENTS:-16}; ROUNDS=${ROUNDS:-24}; FLUSH=${FLUSH:-2}
OUT_DIR=$WT/v2/evidence/run_scene_anchor_${ARM}_seed${SEED}_n${AGENTS}r${ROUNDS}
SIDE_ROOT=${SIDE_ROOT:-/tmp/scene_anchor_${ARM}_side}
LE=$OUT_DIR/launch_evidence.txt
ORDER=${ORDER:-"on off"}
FIRST_ARM=${ORDER%% *}
PREV_ARM=""; [ "$ARM" != "$FIRST_ARM" ] && PREV_ARM=$FIRST_ARM
PREV_DIR=$WT/v2/evidence/run_scene_anchor_${PREV_ARM}_seed${SEED}_n${AGENTS}r${ROUNDS}
MOCK_GATE=${MOCK_GATE:-$MAIN/v2/evidence/round_mock_ctx_scene_check.txt}
METRICS_GATE=${METRICS_GATE:-$MAIN/v2/evidence/f8_metrics_selfcheck.txt}

mkdir -p "$OUT_DIR"

{
  echo "================ R21 处境锚起批证据（臂 $ARM · worktree 版） ================"
  echo "采集时刻: $(date -Is)"
  echo "main_tree: $MAIN"
  echo "worktree:  $WT"
  echo "branch:    $(git -C "$WT" branch --show-current 2>&1)"
  echo "HEAD:      $(git -C "$WT" rev-parse HEAD 2>&1)"
  echo "out_dir:   $OUT_DIR"
  echo "side_root: $SIDE_ROOT"
  echo "params:    seed=$SEED agents=$AGENTS rounds=$ROUNDS flush_every=$FLUSH"
  echo "arm:       $ARM （off=开关变量不存在 / on=开关=1，单变量 $SWITCH）"
  echo "ORDER=$ORDER"
  echo
} | tee "$LE"

# ---- 闸门0：开关在本树可见 ----
git -C "$WT" grep -q "$SWITCH" -- code/life/ || { echo "!! 闸门0 失败：$SWITCH 在 $WT/code/life/ 不可见" | tee -a "$LE"; exit 20; }
# ---- 闸门0b：模块可导入 ----
( cd "$WT/code" && python3 -c "import life.agent" ) >>"$LE" 2>&1 || { echo "!! 闸门0b 失败：life.agent 导入失败" | tee -a "$LE"; exit 21; }
# ---- 闸门0c：worktree 分支/HEAD 一致 ----
WT_BR=$(git -C "$WT" branch --show-current 2>/dev/null); WT_HEAD=$(git -C "$WT" rev-parse HEAD 2>/dev/null)
{ echo "---- [闸门0c] worktree 分支/HEAD ----"; echo "worktree_branch=$WT_BR (期望 $BRANCH)"; echo "worktree_HEAD=$WT_HEAD"; } | tee -a "$LE"
[ "$WT_BR" = "$BRANCH" ] || { echo "!! 闸门0c 失败：worktree 不在 $BRANCH（实际 $WT_BR）" | tee -a "$LE"; exit 26; }
# ---- 闸门0d（本脚本新增，只读断言）：固定 sha 3bb4430 ----
WT_HEAD_BASE=$(git -C "$WT" rev-parse "$BRANCH^" 2>/dev/null)
{ echo "---- [闸门0d] 基线 sha 断言 ----"; echo "branch=$BRANCH  HEAD=$WT_HEAD  父提交(基线)=$WT_HEAD_BASE"; } | tee -a "$LE"
[ "$WT_HEAD_BASE" = "3bb44308291c8ea61d71ae0c595ff2e8b09b5502" ] || { echo "!! 闸门0d 失败：分支基线不是 3bb4430（实际 $WT_HEAD_BASE）" | tee -a "$LE"; exit 38; }
# ---- 闸门1：串行铁律 ----
pgrep -f "[o]rchestration run" >/dev/null && { echo "!! 闸门1 失败：仍有 orchestration run 在跑" | tee -a "$LE"; exit 22; }
echo "---- [闸门1] pgrep -f '[o]rchestration run' 无命中（通过）" | tee -a "$LE"
# ---- 闸门1b（上臂互斥 + 上臂成本凭证）：仅当 PREV_ARM 非空 ----
if [ -n "$PREV_ARM" ]; then
  tail -2 "$PREV_DIR/host.log" 2>/dev/null | grep -q "ARM_DONE" || { echo "!! 闸门1b 失败：上臂 $PREV_ARM 无 ARM_DONE" | tee -a "$LE"; exit 23; }
  [ -s "$PREV_DIR/llm_cost.txt" ] || { echo "!! 闸门1b 失败：上臂 llm_cost.txt 缺失/为空" | tee -a "$LE"; exit 27; }
  python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));g=d.get("provider_guard") or {};tot=(d.get("engine_log") or {}).get("total") or {};sys.exit(0 if g.get("ok") and tot.get("calls",0)>0 else 1)' "$PREV_DIR/llm_cost.txt" \
    || { echo "!! 闸门1b 失败：上臂 provider_guard.ok!=true 或 calls=0" | tee -a "$LE"; exit 28; }
else
  echo "---- [闸门1b] 本次为首臂（ORDER=$ORDER）⇒ 跳过上臂互斥检查（与 ON 臂起跑时同语义）" | tee -a "$LE"
fi
# ---- 闸门1c / 1d：沿用主树未跟踪留痕原件（唯一正本） ----
if [ "${REQUIRE_MOCK_GATE:-1}" != "0" ]; then
  grep -qi "MOCK_GATE=PASS" "$MOCK_GATE" 2>/dev/null || { echo "!! 闸门1c 失败：mock 门槛未通过或未留痕（$MOCK_GATE）" | tee -a "$LE"; exit 29; }
  echo "mock_gate: $(head -3 "$MOCK_GATE" 2>/dev/null)" | tee -a "$LE"
fi
grep -qi "METRICS_GATE=PASS" "$METRICS_GATE" 2>/dev/null || { echo "!! 闸门1d 失败：F-8 指标工具自测未通过或未留痕（$METRICS_GATE）" | tee -a "$LE"; exit 30; }
echo "metrics_gate: $(head -3 "$METRICS_GATE" 2>/dev/null)" | tee -a "$LE"
# ---- 闸门2b：.env.local 不得含 LIFE_PROMPT_* ----
[ -f "$WT/code/.env.local" ] || { echo "!! 闸门2b 失败：worktree 无 code/.env.local" | tee -a "$LE"; exit 31; }
grep -qE "^[[:space:]]*(export[[:space:]]+)?LIFE_PROMPT_" "$WT/code/.env.local" && { echo "!! 闸门2b 失败：.env.local 含 LIFE_PROMPT_*" | tee -a "$LE"; exit 32; }
echo "闸门2b PASS：.env.local 中无 LIFE_PROMPT_*" | tee -a "$LE"
# ---- 闸门0e：参数定稿 ----
if [ "$ROUNDS" != "24" ] || [ "$AGENTS" != "16" ] || [ "$SEED" != "42" ] || [ "$FLUSH" != "2" ]; then
  echo "!! 闸门0e 失败：参数非定稿值（要求 seed=42 agents=16 rounds=24 flush=2）" | tee -a "$LE"; exit 33
fi
echo "闸门0e PASS：seed=$SEED agents=$AGENTS rounds=$ROUNDS flush=$FLUSH out=$OUT_DIR side=$SIDE_ROOT" | tee -a "$LE"
# ---- 闸门0f：路径解析断言（本 worktree） ----
case "$WT" in */尝试/social-experiment/.worktrees/scene-pair-r21) ;; *) echo "!! 闸门0f 失败：WT 不是 scene-pair-r21 worktree（实际 $WT）" | tee -a "$LE"; exit 35;; esac
case "$OUT_DIR" in */v2/evidence/run_scene_anchor_${ARM}_seed42_n16r24) ;; *) echo "!! 闸门0f 失败：OUT_DIR 解析异常（实际 $OUT_DIR）" | tee -a "$LE"; exit 36;; esac
case "$SIDE_ROOT" in /tmp/scene_anchor_${ARM}_side) ;; *) echo "!! 闸门0f 失败：SIDE_ROOT 解析异常" | tee -a "$LE"; exit 37;; esac
echo "闸门0f PASS：WT/OUT_DIR/SIDE_ROOT 三项解析值均与定稿一致" | tee -a "$LE"

cd "$WT/code" || exit 1
set -a; . "$WT/code/.env.local"; set +a
export HITT_LLM_PROVIDER=openai_compat
if [ "$ARM" = "on" ]; then export "$SWITCH=1"; else unset "$SWITCH"; fi

if [ -z "${!SWITCH+x}" ]; then SWITCH_STATE="UNSET（变量不存在）"; SWITCH_EXISTS=NO; else SWITCH_STATE="SET（值='${!SWITCH}'）"; SWITCH_EXISTS=YES; fi
if [ "$ARM" = "off" ] && [ "$SWITCH_EXISTS" = "NO" ]; then ENV_ASSERT=PASS
elif [ "$ARM" = "on" ] && [ "$SWITCH_EXISTS" = "YES" ] && [ "${!SWITCH}" = "1" ]; then ENV_ASSERT=PASS
else ENV_ASSERT=FAIL; fi

{
  echo "---- [生效 env 快照 + 单变量存在性断言]（凭据脱敏） ----"
  echo "arm: $ARM"
  echo "$SWITCH = $SWITCH_STATE"
  echo "展开检验: \${$SWITCH+x}=${!SWITCH+x}"
  echo "存在性判定: $SWITCH_EXISTS （off 要求 NO；on 要求 YES 且值=1）"
  echo "开关断言: $ENV_ASSERT"
  echo "HITT_LLM_PROVIDER=${HITT_LLM_PROVIDER:-<unset>}"
  echo "LLM_API_KEY=<set:${#LLM_API_KEY} chars>"
  env | grep -E '^(LIFE_PROMPT_|HITT_DIALOGUE_)' | sed 's/^/  ENV /'; echo "  (env grep 结束)"
  echo "cwd=$(pwd)  code_head=$(git -C "$WT" rev-parse HEAD)"
  echo "允许差异清单（两臂只允许这三项不同）：$SWITCH / ORDER / out_dir+side_root"
  echo "config sha256 清单："
  ( cd "$WT/code/config" && sha256sum *.json 2>/dev/null ) | sed 's/^/  CFG /'
  echo "执行路径 sha256："
  sha256sum "$WT/tools/d2/run_batch.sh" "$WT/tools/d2/emit_run_meta.py" 2>/dev/null | sed 's/^/  LAUNCHER /'
  echo "指标工具 sha256（冻结口径）："
  for f in "$WT/tools/d5/dialogue_metrics.py" "$WT/tools/d5/f8_lexicon.json" "$WT/code/life/scene_anchor.py" "$WT/code/life/agent.py"; do
    [ -f "$f" ] && { sha256sum "$f" | sed 's/^/  FROZEN /'; echo "  FROZEN_MTIME $(stat -c '%y' "$f")  $f"; } || echo "  FROZEN MISSING $f"
  done
  echo "git status --short 快照（跑批前）："
  git -C "$WT" status --short | sed 's/^/  GIT /'
} | tee -a "$LE"
cp "$LE" "$OUT_DIR/env_dump.txt"
cp "$LE" "$OUT_DIR/switch_proof.txt"
[ "$ENV_ASSERT" = "PASS" ] || { echo "!! 开关存在性断言失败（arm=$ARM state=$SWITCH_STATE）⇒ 拒绝起跑" | tee -a "$LE"; exit 25; }

cp "$0" "$OUT_DIR/launch_worktree.sh"
HOSTLOG="$OUT_DIR/host.log"
{
  echo "[scene-anchor] arm=$ARM（worktree 版 launcher）"
  echo "[scene-anchor] run: bash tools/d2/run_batch.sh --out-dir $OUT_DIR --seed $SEED --agents $AGENTS --rounds $ROUNDS --flush-every $FLUSH --side-root $SIDE_ROOT"
  echo "[scene-anchor] env: $SWITCH=$SWITCH_STATE"
  echo "[scene-anchor] code_sha=$(git -C "$WT" rev-parse HEAD) code_dir=$WT/code"
  echo "[scene-anchor] started_at=$(date -Is)"
} > "$HOSTLOG"

T0=$(date +%s)
setsid bash "$WT/tools/d2/run_batch.sh" --out-dir "$OUT_DIR" \
  --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" --flush-every "$FLUSH" \
  --side-root "$SIDE_ROOT" >> "$HOSTLOG" 2>&1 &
PID=$!
echo "launched arm=$ARM pid=$PID launcher=run_batch.sh out=$OUT_DIR host.log=$HOSTLOG"
echo "$PID" > "$OUT_DIR/pid.txt"
echo "$T0" > "$OUT_DIR/start_epoch.txt"
