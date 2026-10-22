#!/usr/bin/env bash
# R1 · C-1（世界/场景行进对话）双臂跑批 —— 单臂起跑脚本
# 用法: launch_arm.sh <ctrl|a1>
#   ctrl = OFF 臂（LIFE_PROMPT_WORLD_C1 **不存在**，不是空字符串）
#   a1   = ON  臂（LIFE_PROMPT_WORLD_C1=1）
# 依赖: feat/world-line-c1 已推 origin；worktree = $REPO/.worktrees/worldline-c1-n16r84
#       （.gitignore:38 `.worktrees/` 已忽略 ⇒ 不污染主树 git status）
set -u

ARM="${1:?usage: launch_arm.sh <ctrl|a1>}"
case "$ARM" in ctrl|a1) ;; *) echo "bad arm: $ARM"; exit 9;; esac

REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
WT=${WT:-$REPO/.worktrees/worldline-c1-n16r84}
OUT_DIR=$REPO/v2/evidence/run_worldline_c1_${ARM}_n16r84_seed42
TAG=worldline_c1_${ARM}
SIDE_ROOT=/tmp/${TAG}_side
LE=$OUT_DIR/launch_evidence.txt
ROUNDS=84; AGENTS=16; SEED=42
PREV_ARM=""; [ "$ARM" = "a1" ] && PREV_ARM=ctrl
PREV_DIR=$REPO/v2/evidence/run_worldline_c1_ctrl_n16r84_seed42

mkdir -p "$OUT_DIR"

{
  echo "================ R1 · C-1 起批证据（臂 $ARM） ================"
  echo "采集时刻: $(date -Is)"
  echo "repo:     $REPO"
  echo "worktree: $WT"
  echo "branch:   $(git -C "$WT" branch --show-current 2>&1)"
  echo "HEAD:     $(git -C "$WT" rev-parse HEAD 2>&1)"
  echo "out_dir:  $OUT_DIR"
  echo "side_root: $SIDE_ROOT"
  echo "arm:      $ARM （ctrl=OFF / a1=ON，单变量 LIFE_PROMPT_WORLD_C1）"
  echo

  echo "---- [闸门0] 开关可见性：git grep -c \"LIFE_PROMPT_WORLD_C1\" -- code/life/ ----"
  git -C "$WT" grep -c "LIFE_PROMPT_WORLD_C1" -- code/life/; echo "grep_rc=$? (0=开关在树上可见=通过；1=不可见=禁止起跑)"
  echo "---- [闸门0b] 模块可导入：python3 -c 'import life.agent' ----"
  ( cd "$WT/code" && python3 -c "import life.agent" ); echo "import_rc=$? (0=通过)"
  echo

  echo "---- [闸门1] 串行铁律：pgrep -af \"[o]rchestration run\" （期望：无命中） ----"
  pgrep -af "[o]rchestration run"; echo "pgrep_rc=$? (1=无命中=通过)"
  if [ -n "$PREV_ARM" ]; then
    echo "---- [闸门1·上臂互斥] 上臂 $PREV_ARM 的进程确已退出 + run.jsonl 已 flush 完整 ----"
    n1=$(wc -l < "$PREV_DIR/run.jsonl" 2>/dev/null || echo -1)
    sleep 3
    n2=$(wc -l < "$PREV_DIR/run.jsonl" 2>/dev/null || echo -1)
    echo "prev_run_jsonl_lines: n1=$n1 n2=$n2 （两次相等=不再增长=flush 完整）"
    if [ "$n1" = "$n2" ] && [ "$n1" != "-1" ]; then echo "prev_flush_stable=OK"; else echo "prev_flush_stable=FAIL"; fi
    echo "prev_host_log_tail:"; tail -3 "$PREV_DIR/host.log" 2>/dev/null
    if tail -3 "$PREV_DIR/host.log" 2>/dev/null | grep -q '\[d2\] OK'; then echo "prev_done_marker=OK"; else echo "prev_done_marker=MISSING"; fi
    echo "prev_meta_gate:"; grep -E '^verdict:' "$PREV_DIR/meta_gate.txt" 2>/dev/null || echo "(meta_gate.txt 尚无 verdict)"
  else
    echo "---- [闸门1·上臂互斥] 本臂为首臂（$ARM），无上臂需等待 ----"
  fi
  echo

  echo "---- [闸门2] env | grep -E 'LIFE_PROMPT_|HITT_DIALOGUE_' （ctrl 期望空；a1 期望只含 LIFE_PROMPT_WORLD_C1） ----"
  env | grep -E 'LIFE_PROMPT_|HITT_DIALOGUE_'; echo "env_grep_rc=$?"
  echo

  echo "---- [闸门3] git status --short 过滤 code/(life|orchestration|config|engine) （期望：无输出） ----"
  git -C "$WT" status --short | grep -E 'code/(life|orchestration|config|engine)'; echo "code_dirty_rc=$? (1=干净=通过)"
  echo "worktree 全量 git status --short："
  git -C "$WT" status --short; echo "(end)"
  echo

  echo "---- [分支可见性 · 远端（诚实留痕，Leader 裁决 A：出网不可达 ⇒ 降级本地双证）] ----"
  echo "命令: timeout 60 git ls-remote --heads origin feat/world-line-c1 （GitHub 出网 443，实测不可达）"
  LSR_START=$(date +%s)
  LSR_OUT=$(timeout 60 git -C "$REPO" ls-remote --heads origin feat/world-line-c1 2>&1); LSR_RC=$?
  LSR_ELAPSED=$(( $(date +%s) - LSR_START ))
  echo "stdout+stderr: [${LSR_OUT}]"
  echo "lsremote_rc=$LSR_RC   elapsed=${LSR_ELAPSED}s （124=timeout；128=连接失败）"
  echo -n "DNS 解析: "; timeout 10 getent hosts github.com || echo "(getent 失败/超时)"
  echo -n "TCP 443 探测: "; timeout 10 bash -c 'cat < /dev/null > /dev/tcp/github.com/443' 2>&1 && echo "可达" || echo "不可达（超时/拒绝）"
  if [ "$LSR_RC" = "0" ] && [ -n "$LSR_OUT" ]; then
    echo "远端可见性：已验证（git ls-remote 返回分支引用）"
  else
    echo "远端可见性：未验证（出网 443 不可达），本轮降级为本地双证"
  fi
  echo
  echo "---- [分支可见性 · 本地双证（至少三件）] ----"
  echo "① git rev-parse feat/world-line-c1:"; git -C "$REPO" rev-parse feat/world-line-c1 2>&1; echo "rc=$?"
  echo "② git log -1 --format='%H %s' feat/world-line-c1:"; git -C "$REPO" log -1 --format='%H %s' feat/world-line-c1 2>&1; echo "rc=$?"
  BRSHA=$(git -C "$REPO" rev-parse feat/world-line-c1 2>/dev/null || echo "")
  echo "③ git branch --contains ${BRSHA:-<无法解析>}:"; [ -n "$BRSHA" ] && git -C "$REPO" branch --contains "$BRSHA" 2>&1; echo "rc=$?"
  echo "④ 与主树 HEAD 的关系: 主树 HEAD=$(git -C "$REPO" rev-parse --short HEAD) on $(git -C "$REPO" branch --show-current)"
  echo "   git merge-base --is-ancestor <branch> HEAD ?"; [ -n "$BRSHA" ] && { git -C "$REPO" merge-base --is-ancestor "$BRSHA" HEAD && echo "   branch 是 HEAD 的祖先=是" || echo "   branch 是 HEAD 的祖先=否（HEAD 不含该分支）"; }
  echo "   git rev-list --count <branch>..HEAD = $(git -C "$REPO" rev-list --count $(echo "${BRSHA:-HEAD}")..HEAD 2>/dev/null)"
  echo

  echo "---- [起跑 argv] ----"
  echo "cd $WT/code && setsid python3 -m orchestration run --life --seed $SEED --agents $AGENTS --rounds $ROUNDS \\"
  echo "  --out $OUT_DIR/run.jsonl --flush-every 2 --side-root $SIDE_ROOT"
  echo
} | tee "$LE"

# ---------- 硬门禁（任一不通过即拒绝起跑） ----------
if ! git -C "$WT" grep -q "LIFE_PROMPT_WORLD_C1" -- code/life/; then
  echo "!! 闸门0 失败：LIFE_PROMPT_WORLD_C1 在 $WT/code/life/ 不可见 ⇒ 拒绝起跑（两臂会跑成同一份代码）" | tee -a "$LE"; exit 20
fi
if ! ( cd "$WT/code" && python3 -c "import life.agent" ) >>"$LE" 2>&1; then
  echo "!! 闸门0b 失败：life.agent 导入失败 ⇒ 拒绝起跑" | tee -a "$LE"; exit 21
fi
# 闸门0c：worktree 必须真在 feat/world-line-c1 上，且其 HEAD == 该分支 sha
WT_BR=$(git -C "$WT" branch --show-current 2>/dev/null)
WT_HEAD=$(git -C "$WT" rev-parse HEAD 2>/dev/null)
BR_SHA=$(git -C "$REPO" rev-parse feat/world-line-c1 2>/dev/null)
{
  echo "---- [闸门0c] worktree 分支/HEAD 一致性 ----"
  echo "worktree_branch=$WT_BR （期望 feat/world-line-c1）"
  echo "worktree_HEAD=$WT_HEAD"
  echo "feat/world-line-c1=$BR_SHA"
} | tee -a "$LE"
if [ "$WT_BR" != "feat/world-line-c1" ] || [ -z "$BR_SHA" ] || [ "$WT_HEAD" != "$BR_SHA" ]; then
  echo "!! 闸门0c 失败：worktree 不在 feat/world-line-c1 或 HEAD≠分支 sha ⇒ 拒绝起跑" | tee -a "$LE"; exit 26
fi
if pgrep -f "[o]rchestration run" >/dev/null; then
  echo "!! 闸门1 失败：仍有 orchestration run 进程在跑 ⇒ 串行铁律，拒绝起跑" | tee -a "$LE"; exit 22
fi
if [ -n "$PREV_ARM" ]; then
  if ! tail -3 "$PREV_DIR/host.log" 2>/dev/null | grep -q '\[d2\] OK'; then
    echo "!! 闸门1 失败：上臂 $PREV_ARM 的 host.log 无 '[d2] OK' 收尾标记 ⇒ 拒绝起跑 A1" | tee -a "$LE"; exit 23
  fi
  n1=$(wc -l < "$PREV_DIR/run.jsonl"); sleep 3; n2=$(wc -l < "$PREV_DIR/run.jsonl")
  if [ "$n1" != "$n2" ]; then
    echo "!! 闸门1 失败：上臂 run.jsonl 仍在增长（$n1 → $n2）⇒ 未 flush 完整，拒绝起跑 A1" | tee -a "$LE"; exit 24
  fi
fi

cd "$WT/code" || exit 1
# 真实 LLM 凭据（gitignore，不入库）；从主仓 code/.env.local 读取
set -a; . "$REPO/code/.env.local"; set +a

if [ "$ARM" = "a1" ]; then
  export LIFE_PROMPT_WORLD_C1=1
else
  unset LIFE_PROMPT_WORLD_C1
fi

# 存在性断言：区分「变量不存在」与「存在但为空字符串」（${VAR+x} 展开）
if [ -z "${LIFE_PROMPT_WORLD_C1+x}" ]; then
  SWITCH_STATE="UNSET（变量不存在）"
  SWITCH_EXISTS=NO
else
  SWITCH_STATE="SET（值='${LIFE_PROMPT_WORLD_C1}'）"
  SWITCH_EXISTS=YES
fi
if [ "$ARM" = "ctrl" ] && [ "$SWITCH_EXISTS" = "NO" ]; then ENV_ASSERT=PASS
elif [ "$ARM" = "a1" ] && [ "$SWITCH_EXISTS" = "YES" ] && [ "${LIFE_PROMPT_WORLD_C1}" = "1" ]; then ENV_ASSERT=PASS
else ENV_ASSERT=FAIL; fi

{
  echo "---- [生效 env 快照 + 单变量存在性断言]（凭据值脱敏） ----"
  echo "arm: $ARM"
  echo "LIFE_PROMPT_WORLD_C1 = $SWITCH_STATE"
  echo "检验命令: [ -z \"\${LIFE_PROMPT_WORLD_C1+x}\" ] ; 展开=${LIFE_PROMPT_WORLD_C1+x}"
  echo "存在性判定: $SWITCH_EXISTS （ctrl 要求 NO=变量根本不存在；a1 要求 YES 且值=1）"
  echo "开关断言: $ENV_ASSERT"
  echo "HITT_LLM_PROVIDER=${HITT_LLM_PROVIDER:-<unset>}"
  echo "LLM_API_KEY=<set:${#LLM_API_KEY} chars>"
  env | grep -E '^(LIFE_PROMPT_|HITT_DIALOGUE_)' | sed 's/^/  ENV /'; echo "  (env grep 结束)"
  echo "cwd=$(pwd)  code_head=$(git -C "$WT" rev-parse HEAD)"
} | tee -a "$LE"
cp "$LE" "$OUT_DIR/env_dump.txt"

if [ "$ENV_ASSERT" != "PASS" ]; then
  echo "!! 开关存在性断言失败（arm=$ARM, state=$SWITCH_STATE）⇒ 拒绝起跑" | tee -a "$LE"; exit 25
fi

cp "$0" "$OUT_DIR/launch.sh"

HOSTLOG="$OUT_DIR/host.log"
{
  echo "[r1] arm=$ARM"
  echo "[r1] run: python3 -m orchestration run --life --seed $SEED --agents $AGENTS --rounds $ROUNDS --out $OUT_DIR/run.jsonl --flush-every 2 --side-root $SIDE_ROOT"
  echo "[r1] env: LIFE_PROMPT_WORLD_C1=$SWITCH_STATE"
  echo "[r1] code_sha=$(git -C "$WT" rev-parse HEAD) code_dir=$WT/code"
  echo "[r1] started_at=$(date -Is)"
} > "$HOSTLOG"

setsid python3 -m orchestration run --life --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" \
  --out "$OUT_DIR/run.jsonl" --flush-every 2 --side-root "$SIDE_ROOT" \
  >> "$HOSTLOG" 2>&1 &

echo "launched arm=$ARM pid=$! out=$OUT_DIR host.log=$HOSTLOG"
