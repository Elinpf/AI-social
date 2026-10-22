#!/usr/bin/env bash
# C-1 · a1 臂（LIFE_PROMPT_WORLD_C1=1）起跑脚本 —— systemd-run 托管版
# 单变量对照：复用 ctrl 臂同一 worktree / 同一 code_sha af1dffc，只改一个环境变量。
# 用法：bash launch_a1.sh
set -u

REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
WT=$REPO/.worktrees/worldline-c1-n16r84
ARM=a1
OUT_DIR=$REPO/v2/evidence/run_worldline_c1_a1_n16r84_seed42
SIDE_ROOT=/tmp/worldline_c1_a1_side
UNIT=worldline-c1-a1-n16r84
ENVFILE=/tmp/worldline_c1_a1_env
PREV_DIR=$REPO/v2/evidence/run_worldline_c1_ctrl_n16r84_seed42
HOSTLOG=$OUT_DIR/host.log
LE=$OUT_DIR/launch_evidence.txt
ROUNDS=84; AGENTS=16; SEED=42

mkdir -p "$OUT_DIR"
: > "$LE"

log() { echo "$@" | tee -a "$LE"; }

log "================ C-1 · a1 起批证据（臂 a1） ================"
log "采集时刻: $(date -Is)"
log "repo:      $REPO"
log "worktree:  $WT"
log "branch:    $(git -C "$WT" branch --show-current 2>&1)"
log "HEAD:      $(git -C "$WT" rev-parse HEAD 2>&1)"
log "out_dir:   $OUT_DIR"
log "side_root: $SIDE_ROOT"
log "host:      systemd-run（transient unit，脱离会话 cgroup）"
log "arm:       a1（ctrl=OFF / a1=ON，单变量 LIFE_PROMPT_WORLD_C1）"
log ""

# ---------- 闸门 ----------
log "---- [闸门0] 开关可见性：git -C \$WT grep -n LIFE_PROMPT_WORLD_C1 -- code/life/ ----"
git -C "$WT" grep -n "LIFE_PROMPT_WORLD_C1" -- code/life/ 2>&1 | tee -a "$LE"
log "grep_rc=${PIPESTATUS[0]} (0=开关在树上可见=通过；1=不可见=禁止起跑)"
if ! git -C "$WT" grep -q "LIFE_PROMPT_WORLD_C1" -- code/life/; then
  log "!! 闸门0 失败 ⇒ 拒绝起跑"; exit 20
fi

log "---- [闸门0b] 模块可导入 ----"
( cd "$WT/code" && python3 -c "import life.agent" ); log "import_rc=$?"

log "---- [闸门0c] worktree 分支/HEAD 与 ctrl 臂 code_sha 一致性 ----"
WT_BR=$(git -C "$WT" branch --show-current)
WT_HEAD=$(git -C "$WT" rev-parse HEAD)
CTRL_SHA=$(sed -n 's/.*code_sha=\([0-9a-f]\{40\}\).*/\1/p' "$PREV_DIR/host.log" | head -1)
log "worktree_branch=$WT_BR"
log "worktree_HEAD=$WT_HEAD"
log "ctrl_code_sha=$CTRL_SHA"
log "same_code_sha=$([ "$WT_HEAD" = "$CTRL_SHA" ] && echo YES || echo NO)"
if [ "$WT_HEAD" != "$CTRL_SHA" ]; then log "!! 闸门0c 失败：与 ctrl 臂 code_sha 不同，单变量不成立 ⇒ 拒绝起跑"; exit 26; fi

log "---- [闸门1] 串行铁律：pgrep -af \"[o]rchestration run\" （期望无命中） ----"
pgrep -af "[o]rchestration run"; log "pgrep_rc=$? (1=无命中=通过)"
if pgrep -f "[o]rchestration run" >/dev/null; then log "!! 闸门1 失败：有并发跑批 ⇒ 拒绝起跑"; exit 22; fi

log "---- [闸门1·上臂互斥] ctrl 臂收批完整（[life] 汇总行三真 + run.jsonl 稳定） ----"
log "ctrl host.log 是否含 [life] 汇总行：$(grep -c '^\[life\] n_agents=16 rounds=84' "$PREV_DIR/host.log")"
grep -E 'chain_ok|replay_parity|conservation_ok' "$PREV_DIR/host.log" | tee -a "$LE"
n1=$(wc -l < "$PREV_DIR/run.jsonl"); sleep 3; n2=$(wc -l < "$PREV_DIR/run.jsonl")
log "prev_run_jsonl_lines: n1=$n1 n2=$n2 （相等=不再增长=flush 完整）"
if [ "$n1" != "$n2" ]; then log "!! 闸门1 失败：上臂 run.jsonl 仍增长 ⇒ 拒绝起跑"; exit 24; fi
log "prev_done_marker=$([ "$(grep -c '^\[life\] n_agents=16 rounds=84' "$PREV_DIR/host.log")" -ge 1 ] && echo OK || echo MISSING)"
log "（说明：ctrl 臂用 setsid 直跑，host.log 里没有 tools/d2 的 '[d2] OK' 行；本闸门改用更硬的 '[life] 汇总行 + run.jsonl 稳定' 判据，已在此留痕。）"
log ""

log "---- [闸门2] 当前 shell env | grep -E 'LIFE_PROMPT_|HITT_DIALOGUE_' （期望空；开关只在 env-file 里给） ----"
env | grep -E 'LIFE_PROMPT_|HITT_DIALOGUE_'; log "env_grep_rc=$?"

log "---- [闸门3] git status 过滤 code/(life|orchestration|config|engine) （期望无输出） ----"
git -C "$WT" status --short | grep -E 'code/(life|orchestration|config|engine)'; log "code_dirty_rc=$? (1=干净=通过)"
log "worktree 全量 git status --short："; git -C "$WT" status --short; log "(end)"
log ""

# ---------- 起跑快照（runbook §3.9 要求） ----------
git -C "$REPO" status --porcelain > "$OUT_DIR/git_status_start.txt"
log "---- [快照] git status --porcelain > $OUT_DIR/git_status_start.txt ----"
cat "$OUT_DIR/git_status_start.txt" | tee -a "$LE"; log "(end)"

# ---------- 凭据走 --env-file（禁 --setenv）；开关也写进同一份 env 文件，保证「单文件可见差异」 ----------
cp "$REPO/code/.env.local" "$ENVFILE"
grep -q '^LIFE_PROMPT_WORLD_C1=' "$ENVFILE" && sed -i '/^LIFE_PROMPT_WORLD_C1=/d' "$ENVFILE"
echo 'LIFE_PROMPT_WORLD_C1=1' >> "$ENVFILE"
chmod 600 "$ENVFILE"
log ""
log "---- [env-file] 只落到 /tmp（600），凭据值不上屏 ----"
log "env_file=$ENVFILE"
sed 's/=.*/=<redacted>/' "$ENVFILE" | tee -a "$LE"
log "sha256(env_file)=$(sha256sum "$ENVFILE" | cut -d' ' -f1)  （ctrl 臂 env 里该变量不存在 ⇒ 差异就是这最后一行）"

# ---------- host.log 头 ----------
{
  echo "[a1] arm=a1"
  echo "[a1] run: python3 -m orchestration run --life --seed $SEED --agents $AGENTS --rounds $ROUNDS --out $OUT_DIR/run.jsonl --flush-every 2 --side-root $SIDE_ROOT"
  echo "[a1] env: LIFE_PROMPT_WORLD_C1=SET（值=1）"
  echo "[a1] code_sha=$WT_HEAD code_dir=$WT/code"
  echo "[a1] host=systemd-run unit=$UNIT env_file=$ENVFILE"
  echo "[a1] started_at=$(date -Is)"
} > "$HOSTLOG"

# ---------- systemd-run 托管起跑 ----------
log ""
log "---- [起跑 argv] ----"
log "systemd-run --unit=$UNIT --collect -p WorkingDirectory=$WT/code -p EnvironmentFile=$ENVFILE \\"
log "  -p MemoryHigh=12G -p MemoryMax=16G -p StandardOutput=append:$HOSTLOG -p StandardError=append:$HOSTLOG \\"
log "  -- python3 -m orchestration run --life --seed $SEED --agents $AGENTS --rounds $ROUNDS \\"
log "       --out $OUT_DIR/run.jsonl --flush-every 2 --side-root $SIDE_ROOT"

systemd-run --unit="$UNIT" --collect \
  -p WorkingDirectory="$WT/code" \
  -p EnvironmentFile="$ENVFILE" \
  -p MemoryHigh=12G -p MemoryMax=16G \
  -p StandardOutput="append:$HOSTLOG" \
  -p StandardError="append:$HOSTLOG" \
  -- python3 -m orchestration run --life --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" \
       --out "$OUT_DIR/run.jsonl" --flush-every 2 --side-root "$SIDE_ROOT" 2>&1 | tee -a "$LE"
SRC=${PIPESTATUS[0]}
log "systemd_run_rc=$SRC"
[ "$SRC" = "0" ] || { log "!! systemd-run 起跑失败 ⇒ BLOCKED"; exit 27; }

# ---------- 进程级开关自证：/proc/<pid>/environ ----------
sleep 4
MAINPID=$(systemctl show -p MainPID --value "$UNIT")
log ""
log "---- [进程级开关自证] unit=$UNIT MainPID=$MAINPID ----"
log "systemctl show ActiveState=$(systemctl show -p ActiveState --value "$UNIT") SubState=$(systemctl show -p SubState --value "$UNIT")"
log "cgroup=$(systemctl show -p ControlGroup --value "$UNIT")  （须为 /system.slice/$UNIT.service ⇒ 已脱离会话 cgroup）"
log "MainPID 进程命令行：$(tr '\0' ' ' < /proc/$MAINPID/cmdline 2>/dev/null)"
SW=$(tr '\0' '\n' < /proc/$MAINPID/environ 2>/dev/null | grep -E '^(LIFE_PROMPT_WORLD_C1|HITT_LLM_PROVIDER)=' | sed 's/^LLM_API_KEY=.*/LLM_API_KEY=<redacted>/')
log "子进程实际生效的关键 env："
echo "$SW" | sed 's/^/  PROC-ENV /' | tee -a "$LE"
if echo "$SW" | grep -qx 'LIFE_PROMPT_WORLD_C1=1'; then
  log "switch_in_process=PASS（跑批进程内确认 LIFE_PROMPT_WORLD_C1=1）"
else
  log "switch_in_process=FAIL（进程内未见 LIFE_PROMPT_WORLD_C1=1 ⇒ 该臂无效，须停批并标 INVALID）"
fi

# 起跑后立刻收紧凭据文件权限（环境已读入内存，文件可删）
rm -f "$ENVFILE"
log "env_file_removed_after_start=YES（环境已在 unit 进程内，减少凭据落盘暴露面）"
log ""
log "launched arm=a1 unit=$UNIT MainPID=$MAINPID out=$OUT_DIR hostlog=$HOSTLOG"
