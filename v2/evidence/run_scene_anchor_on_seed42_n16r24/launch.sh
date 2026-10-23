#!/usr/bin/env bash
# scene-anchor 双盲两臂 · 单臂起跑脚本（batch-runner）
# 用法: bash launch_scene_anchor.sh <off|on>
#   off = OFF 臂（LIFE_PROMPT_SCENE 变量**不存在**，不是空串）
#   on  = ON  臂（LIFE_PROMPT_SCENE=1）
#
# 设计：两臂跑在**同一个 worktree、同一份代码**（feat/scene-anchor）上，只差一个环境变量。
#       单变量洁净度由"同 sha + 开关存在性断言 + prompt sha 两态对比"三重保证。
# 纪律：同一时刻只允许一个 orchestration run；上一臂未完成标记即拒绝起跑。
set -u

ARM="${1:?usage: launch_scene_anchor.sh <off|on>}"
case "$ARM" in off|on) ;; *) echo "bad arm: $ARM"; exit 9;; esac

REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
WT=${WT:-$REPO}   # 实际执行目录 = 主工作树（life-dev 的代码在 59bad20 的主树；本仓无 .worktrees/scene-anchor）
[ -d "$WT" ] || { echo "!! 执行目录不存在：$WT"; exit 34; }
BRANCH=${BRANCH:-feat/scene-anchor}
SWITCH=LIFE_PROMPT_SCENE
SEED=${SEED:-42}
AGENTS=${AGENTS:-16}
ROUNDS=${ROUNDS:-24}
FLUSH=${FLUSH:-2}
OUT_DIR=$REPO/v2/evidence/run_scene_anchor_${ARM}_seed${SEED}_n${AGENTS}r${ROUNDS}
SIDE_ROOT=${SIDE_ROOT:-/tmp/scene_anchor_${ARM}_side}
LE=$OUT_DIR/launch_evidence.txt
# 臂序：leader 排期为 ON 臂先、OFF 臂后（ORDER 可覆盖，如 ORDER="off on"）
ORDER=${ORDER:-"on off"}
FIRST_ARM=${ORDER%% *}
PREV_ARM=""; [ "$ARM" != "$FIRST_ARM" ] && PREV_ARM=$FIRST_ARM
PREV_DIR=$REPO/v2/evidence/run_scene_anchor_${PREV_ARM}_seed${SEED}_n${AGENTS}r${ROUNDS}

mkdir -p "$OUT_DIR"

{
  echo "================ scene-anchor 起批证据（臂 $ARM） ================"
  echo "采集时刻: $(date -Is)"
  echo "repo:     $REPO"
  echo "worktree: $WT"
  echo "branch:   $(git -C "$WT" branch --show-current 2>&1)"
  echo "HEAD:     $(git -C "$WT" rev-parse HEAD 2>&1)"
  echo "out_dir:  $OUT_DIR"
  echo "side_root: $SIDE_ROOT"
  echo "params:   seed=$SEED agents=$AGENTS rounds=$ROUNDS flush_every=$FLUSH"
  echo "arm:      $ARM （off=开关变量不存在 / on=开关=1，单变量 $SWITCH）"
  echo

  echo "---- [闸门0a] 变量解析自证（固定段：只解析不执行，值不对就不起） ----"
  echo "  WT        = $WT"
  echo "  OUT_DIR   = $OUT_DIR"
  echo "  SIDE_ROOT = $SIDE_ROOT"
  echo "  WT_HEAD   = $(git -C "$WT" rev-parse HEAD 2>&1)"
  echo "  WT_BRANCH = $(git -C "$WT" branch --show-current 2>&1)"
  echo "  ARM=$ARM SEED=$SEED AGENTS=$AGENTS ROUNDS=$ROUNDS FLUSH=$FLUSH"
  echo "  ORDER=$ORDER  (解析于 $(date -Iseconds))"
  echo "  RELEASE_TS(leader 放行时刻) = ${RELEASE_TS:-<未填>}"
  echo

  echo "---- [闸门0] 开关可见性：git grep -c \"$SWITCH\" -- code/life/ ----"
  git -C "$WT" grep -c "$SWITCH" -- code/life/; echo "grep_rc=$?"
  echo "---- [闸门0b] 模块可导入 ----"
  ( cd "$WT/code" && python3 -c "import life.agent" ); echo "import_rc=$?"
  echo

  echo "---- [闸门1] 串行铁律：pgrep -af \"[o]rchestration run\"（期望无命中） ----"
  pgrep -af "[o]rchestration run"; echo "pgrep_rc=$? (1=无命中=通过)"
  if [ -n "$PREV_ARM" ]; then
    echo "---- [闸门1·上臂互斥] 上臂 $PREV_ARM 已收批？ ----"
    tail -2 "$PREV_DIR/host.log" 2>/dev/null | grep -q "ARM_DONE" && echo "prev_done_marker=OK" || echo "prev_done_marker=MISSING"
    n1=$(wc -l < "$PREV_DIR/run.jsonl" 2>/dev/null || echo -1); sleep 3
    n2=$(wc -l < "$PREV_DIR/run.jsonl" 2>/dev/null || echo -1)
    echo "prev_run_jsonl_lines: n1=$n1 n2=$n2"
  fi
  echo

  echo "---- [闸门2] git status 过滤 code/(life|orchestration|config|engine)（期望无输出） ----"
  git -C "$WT" status --short | grep -E 'code/(life|orchestration|config|engine)'; echo "code_dirty_rc=$? (1=干净=通过)"
  echo
} | tee "$LE"

# ---------- 硬门禁 ----------
git -C "$WT" grep -q "$SWITCH" -- code/life/ || { echo "!! 闸门0 失败：$SWITCH 在 $WT/code/life/ 不可见 ⇒ 两臂会跑成同一份代码，拒绝起跑" | tee -a "$LE"; exit 20; }
( cd "$WT/code" && python3 -c "import life.agent" ) >>"$LE" 2>&1 || { echo "!! 闸门0b 失败：life.agent 导入失败" | tee -a "$LE"; exit 21; }
WT_BR=$(git -C "$WT" branch --show-current 2>/dev/null); WT_HEAD=$(git -C "$WT" rev-parse HEAD 2>/dev/null); BR_SHA=$(git -C "$REPO" rev-parse "$BRANCH" 2>/dev/null)
{ echo "---- [闸门0c] worktree 分支/HEAD 一致性 ----"; echo "worktree_branch=$WT_BR (期望 $BRANCH)"; echo "worktree_HEAD=$WT_HEAD"; echo "$BRANCH=$BR_SHA"; } | tee -a "$LE"
[ "$WT_BR" = "$BRANCH" ] && [ -n "$BR_SHA" ] && [ "$WT_HEAD" = "$BR_SHA" ] || { echo "!! 闸门0c 失败：worktree 不在 $BRANCH 或 HEAD≠分支 sha" | tee -a "$LE"; exit 26; }
pgrep -f "[o]rchestration run" >/dev/null && { echo "!! 闸门1 失败：仍有 orchestration run 在跑 ⇒ 串行铁律，拒绝起跑" | tee -a "$LE"; exit 22; }
if [ -n "$PREV_ARM" ]; then
  tail -2 "$PREV_DIR/host.log" 2>/dev/null | grep -q "ARM_DONE" || { echo "!! 闸门1 失败：上臂 $PREV_ARM 无 ARM_DONE 收尾标记" | tee -a "$LE"; exit 23; }
  # 备份门禁（leader 02:10 追认 3）：标记存在还不够，验真原文必须已落盘且 guard 通过，防"标记有、证据全无"误起
  [ -s "$PREV_DIR/llm_cost.txt" ] || { echo "!! 闸门1b 失败：上臂 $PREV_ARM 的 llm_cost.txt 缺失或为空 ⇒ 证据不全，拒绝起跑" | tee -a "$LE"; exit 27; }
  python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));g=d.get("provider_guard") or {};tot=(d.get("engine_log") or {}).get("total") or {};sys.exit(0 if g.get("ok") and tot.get("calls",0)>0 else 1)' "$PREV_DIR/llm_cost.txt" \
    || { echo "!! 闸门1b 失败：上臂 $PREV_ARM 的 provider_guard.ok!=true 或 calls=0 ⇒ 拒绝起跑" | tee -a "$LE"; exit 28; }
  tail -3 "$PREV_DIR/llm_cost.txt" | tee -a "$LE"
fi
# 闸门1c（leader 02:10 追认 2）：scout 的 mock 批硬前置——payload.ctx.scene 必须在 run.jsonl 里出现
MOCK_GATE=${MOCK_GATE:-$REPO/v2/evidence/round_mock_ctx_scene_check.txt}
if [ "${REQUIRE_MOCK_GATE:-1}" != "0" ]; then
  grep -qi "MOCK_GATE=PASS" "$MOCK_GATE" 2>/dev/null || { echo "!! 闸门1c 失败：scout mock 门槛未通过或未留痕（$MOCK_GATE）⇒ ON 臂不起" | tee -a "$LE"; exit 29; }
  say_mock=$(head -3 "$MOCK_GATE" 2>/dev/null); echo "mock_gate: $say_mock" | tee -a "$LE"
fi
# 闸门1d（leader 02:15）：F-8 工具实现自测复现必须 PASS，否则跑完也出不了数 = 白烧
METRICS_GATE=${METRICS_GATE:-$REPO/v2/evidence/f8_metrics_selfcheck.txt}
grep -qi "METRICS_GATE=PASS" "$METRICS_GATE" 2>/dev/null || { echo "!! 闸门1d 失败：F-8 指标工具自测未通过或未留痕（$METRICS_GATE）⇒ 拒绝起跑（跑完也算不出 F-8）" | tee -a "$LE"; exit 30; }
echo "metrics_gate: $(head -3 "$METRICS_GATE" 2>/dev/null)" | tee -a "$LE"

# 闸门2b（leader 02:20）：run_batch.sh 内部会 source code/.env.local —— 若其中定义了
# LIFE_PROMPT_*，OFF 臂"变量不存在"的前提会被脚本自己破坏（外面 env -u 无效）。
[ -f "$REPO/code/.env.local" ] || { echo "!! 闸门2b 失败：code/.env.local 不存在（run_batch.sh 依赖它）" | tee -a "$LE"; exit 31; }
if grep -qE "^[[:space:]]*(export[[:space:]]+)?LIFE_PROMPT_" "$REPO/code/.env.local"; then
  echo "!! 闸门2b 失败：.env.local 里定义了 LIFE_PROMPT_* ⇒ 会污染 OFF 臂，拒绝起跑" | tee -a "$LE"; exit 32
fi
echo "闸门2b PASS：.env.local 中无 LIFE_PROMPT_*（变量名清单见下）" | tee -a "$LE"
grep -oE "^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=" "$REPO/code/.env.local" | sed -E 's/^[[:space:]]*(export[[:space:]]+)?//; s/=$//' | sed 's/^/  ENVFILE /' | tee -a "$LE"

# 闸门0e（leader 02:23）：显式六参数，绝不吃默认值（run_batch.sh 默认 ROUNDS=84 是最大误跑风险）
if [ "$ROUNDS" != "24" ] || [ "$AGENTS" != "16" ] || [ "$SEED" != "42" ] || [ "$FLUSH" != "2" ]; then
  echo "!! 闸门0e 失败：参数非定稿值（要求 seed=42 agents=16 rounds=24 flush=2，实际 seed=$SEED agents=$AGENTS rounds=$ROUNDS flush=$FLUSH）" | tee -a "$LE"; exit 33
fi
echo "闸门0e PASS：显式六参数 seed=$SEED agents=$AGENTS rounds=$ROUNDS flush=$FLUSH out=$OUT_DIR side=$SIDE_ROOT" | tee -a "$LE"

# 闸门0f（leader 02:24）：解析值必须与定稿一致，否则拒绝起跑
case "$WT" in */尝试/social-experiment) ;; *) echo "!! 闸门0f 失败：WT 不是主树（实际 $WT）" | tee -a "$LE"; exit 35;; esac
case "$OUT_DIR" in */v2/evidence/run_scene_anchor_${ARM}_seed42_n16r24) ;; *) echo "!! 闸门0f 失败：OUT_DIR 解析异常（实际 $OUT_DIR）" | tee -a "$LE"; exit 36;; esac
case "$SIDE_ROOT" in /tmp/scene_anchor_${ARM}_side) ;; *) echo "!! 闸门0f 失败：SIDE_ROOT 解析异常（实际 $SIDE_ROOT）" | tee -a "$LE"; exit 37;; esac
echo "闸门0f PASS：WT/OUT_DIR/SIDE_ROOT 三项解析值均与定稿一致" | tee -a "$LE"

cd "$WT/code" || exit 1
set -a; . "$REPO/code/.env.local"; set +a
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
  echo "ORDER=$ORDER （调度参数，非行为参数；列入两臂「允许差异清单」）"
  echo "允许差异清单（两臂只允许这两项不同）："
  echo "  1) $SWITCH        （off=不存在 / on=1）—— 被测单变量"
  echo "  2) ORDER          （臂序调度参数，不影响代码行为）"
  echo "  3) out_dir/side_root（两臂各自独立，路径不同）"
  echo "其余必须全等：code_head / config 文件 sha256 / HITT_* / LIFE_PROMPT_ 其它变量 / seed / agents / rounds / flush_every"
  echo "config sha256 清单："
  ( cd "$WT/code/config" && sha256sum *.json 2>/dev/null ) | sed 's/^/  CFG /'
  echo "执行路径 sha256（脚本变了 = 实验条件变了）："
  sha256sum "$REPO/tools/d2/run_batch.sh" "$REPO/tools/d2/emit_run_meta.py" 2>/dev/null | sed 's/^/  LAUNCHER /'
  echo "指标工具 sha256（冻结口径，收批前不得再变）："
  for f in "$REPO/tools/d5/dialogue_metrics.py" "$REPO/tools/d5/f8_lexicon.json" "$REPO/code/life/scene_anchor.py" "$REPO/code/life/agent.py"; do
    if [ -f "$f" ]; then
      sha256sum "$f" | sed 's/^/  FROZEN /'
      echo "  FROZEN_MTIME $(stat -c '%y' "$f")  $f"
    else
      echo "  FROZEN MISSING $f"
    fi
  done
  echo "git status --short 快照（跑批前）："
  git -C "$WT" status --short | sed 's/^/  GIT /'
} | tee -a "$LE"
cp "$LE" "$OUT_DIR/env_dump.txt"
cp "$LE" "$OUT_DIR/switch_proof.txt"

[ "$ENV_ASSERT" = "PASS" ] || { echo "!! 开关存在性断言失败（arm=$ARM state=$SWITCH_STATE）⇒ 拒绝起跑" | tee -a "$LE"; exit 25; }

cp "$0" "$OUT_DIR/launch.sh"
HOSTLOG="$OUT_DIR/host.log"
{
  echo "[scene-anchor] arm=$ARM"
  echo "[scene-anchor] launcher=tools/d2/run_batch.sh（走封装脚本 ⇒ 产出 meta.json + '[d2] OK' 收尾标记 + 内建 obs llm-cost 门禁）"
  echo "[scene-anchor] run: env ${ARM:+}bash tools/d2/run_batch.sh --out-dir $OUT_DIR --seed $SEED --agents $AGENTS --rounds $ROUNDS --flush-every $FLUSH --side-root $SIDE_ROOT"
  echo "[scene-anchor] env: $SWITCH=$SWITCH_STATE"
  echo "[scene-anchor] code_sha=$(git -C "$WT" rev-parse HEAD) code_dir=$WT/code"
  echo "[scene-anchor] started_at=$(date -Is)"
} > "$HOSTLOG"

# 起跑：一律走 tools/d2/run_batch.sh（leader 02:19 要求），以便产出 meta.json 与 [d2] OK 收尾标记；
# 真 LLM 凭据由 run_batch.sh 自己 source code/.env.local，开关变量由本脚本 export/unset 后继承。
T0=$(date +%s)
setsid bash "$REPO/tools/d2/run_batch.sh" --out-dir "$OUT_DIR" \
  --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" --flush-every "$FLUSH" \
  --side-root "$SIDE_ROOT" >> "$HOSTLOG" 2>&1 &
PID=$!
echo "launched arm=$ARM pid=$PID launcher=run_batch.sh out=$OUT_DIR host.log=$HOSTLOG"
echo "$PID" > "$OUT_DIR/pid.txt"
echo "$T0" > "$OUT_DIR/start_epoch.txt"

# 收批证据由 finalize_arm.sh 落（含 rc/耗时/llm_cost/指标），本脚本只负责起跑。
