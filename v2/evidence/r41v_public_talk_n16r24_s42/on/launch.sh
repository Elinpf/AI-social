#!/usr/bin/env bash
# R41V 公开面接话验证批起跑脚本（batch-operator，2026-11-01）
#
# 单变量：HITT_DIALOGUE_PUBLIC_REPLY（OFF=变量不存在 / ON=值 1）
# 纪律：外层 setsid 启动（run_batch.sh 自身不含 setsid）；每次起跑前独立跑 tools/d5/preflight.sh；
#       两臂严格串行（launch 脚本自身不并发，靠闸门1b 校验上臂 run_batch.rc=0）。
# 用法（仓库根执行）：
#   bash tools/public_talk/launch_r41v.sh off
#   bash tools/public_talk/launch_r41v.sh on            # 仅在 off 臂 run_batch.rc=0 后
#
# 产物目录：v2/evidence/r41v_public_talk_n16r24_s42/<arm>/
# 退出码：20 开关不可见 / 21 import 失败 / 22 preflight 或并发 / 23 上臂未收尾 / 25 开关断言失败 /
#         29 冻结区脏 / 31 无 .env.local / 32 .env.local 污染 / 33 参数非定稿 / 40 启动失败
set -uo pipefail

ARM="${1:?usage: launch_r41v.sh <off|on>}"
case "$ARM" in off|on) ;; *) echo "bad arm: $ARM"; exit 9 ;; esac

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$WT"
SWITCH=HITT_DIALOGUE_PUBLIC_REPLY
SEED=42; AGENTS=16; ROUNDS=24; FLUSH=2
TAG=r41v
OUT_DIR="$WT/v2/evidence/r41v_public_talk_n${AGENTS}r${ROUNDS}_s${SEED}/${ARM}"
SIDE_ROOT="/tmp/r41v_${ARM}_n${AGENTS}r${ROUNDS}_s${SEED}_side"
LE="$OUT_DIR/launch_evidence.txt"
HOSTLOG="$OUT_DIR/host.log"
UNIT="r41v-${ARM}-$(date +%H%M%S)"

mkdir -p "$OUT_DIR"

{
  echo "================ R41V 验证批起批证据（arm=$ARM，单变量 $SWITCH） ================"
  echo "采集时刻: $(date -Is)"
  echo "repo:      $WT"
  echo "branch:    $(git -C "$WT" branch --show-current 2>&1)"
  echo "HEAD:      $(git -C "$WT" rev-parse HEAD 2>&1)"
  echo "out_dir:   $OUT_DIR"
  echo "side_root: $SIDE_ROOT"
  echo "unit:      $UNIT"
  echo "params:    seed=$SEED agents=$AGENTS rounds=$ROUNDS flush_every=$FLUSH"
  echo "arm:       $ARM （off=变量不存在 / on=变量=1）"
  echo "prereg:    v2/refs/prereg-r41v-public-talk-verify.md"
} | tee "$LE"

fail() { echo "!! 闸门失败：$1" | tee -a "$LE"; exit "${2:-20}"; }

# ---- 闸门0：开关在本树可见 ----
git -C "$WT" grep -q "$SWITCH" -- code/life/ || fail "闸门0：$SWITCH 在 code/life/ 不可见" 20
echo "---- [闸门0] git grep -c $SWITCH -- code/life/ ----" | tee -a "$LE"
git -C "$WT" grep -c "$SWITCH" -- code/life/ 2>/dev/null | tee -a "$LE"

# ---- 闸门0b：模块可导入 ----
( cd "$WT/code" && python3 -c "import life.agent, life.public_talk" ) >>"$LE" 2>&1 || fail "闸门0b：import 失败" 21
echo "---- [闸门0b] import life.agent / life.public_talk = rc0 ----" | tee -a "$LE"

# ---- 闸门0e：参数定稿 ----
[ "$ROUNDS" = "24" ] && [ "$AGENTS" = "16" ] && [ "$SEED" = "42" ] && [ "$FLUSH" = "2" ] \
  || fail "闸门0e：参数非定稿" 33
echo "闸门0e PASS：seed=$SEED agents=$AGENTS rounds=$ROUNDS flush=$FLUSH" | tee -a "$LE"

# ---- 闸门1：串行铁律（三重并发，bracket 防自匹配） ----
echo "---- [闸门1] pgrep 三重并发检查 ----" | tee -a "$LE"
for pat in "orchestration[[:space:]]+run" "[r]un_[b]atch" "[n]ightly\.py"; do
  if pgrep -f "$pat" >/dev/null 2>&1; then
    pgrep -fa "$pat" | tee -a "$LE"; fail "闸门1：检出并发进程 /$pat/" 22
  fi
  echo "  pgrep -f '/$pat/' => 无命中 PASS" | tee -a "$LE"
done

# ---- 闸门1c：仓库权威 preflight（祖先链排除 + 留痕） ----
( cd "$WT" && bash tools/d5/preflight.sh --tag "r41v_${ARM}" --log-dir "$OUT_DIR" ) 2>&1 | tee -a "$LE"
[ "${PIPESTATUS[0]}" = "0" ] || fail "闸门1c：tools/d5/preflight.sh 失败（并发/脏树/不可判定）" 22

# ---- 闸门1b：上臂互斥（ON 臂必须看到 OFF 臂 run_batch.rc=0 + 真 provider） ----
if [ "$ARM" = "on" ]; then
  PREV_DIR="$WT/v2/evidence/r41v_public_talk_n${AGENTS}r${ROUNDS}_s${SEED}/off"
  [ "$(cat "$PREV_DIR/run_batch.rc" 2>/dev/null)" = "0" ] || fail "闸门1b：OFF 臂无 run_batch.rc=0" 23
  python3 - "$PREV_DIR/meta.json" <<'PY' || fail "闸门1b：OFF 臂 provider 非纯 openai_compat" 28
import json, sys
m = json.load(open(sys.argv[1]))
prov = m.get("llm_provider_in_events") or {}
sw = ((m.get("switch_effective") or {}).get("HITT_DIALOGUE_PUBLIC_REPLY") or {})
print("prev(off) provider =", prov, "| switch_effective =", sw)
ok = list(prov) == ["openai_compat"] and prov.get("openai_compat", 0) > 0
sys.exit(0 if ok else 1)
PY
  echo "---- [闸门1b] OFF 臂收尾凭证 PASS ----" | tee -a "$LE"
else
  echo "---- [闸门1b] 本臂为首臂 ⇒ 跳过 ----" | tee -a "$LE"
fi

# ---- 闸门2：冻结区干净 ----
( cd "$WT" && python3 tools/d5/check_clean_tree.py ) > "$OUT_DIR/clean_tree.json" 2>&1 || fail "闸门2：code/ 冻结区不干净" 29
echo "---- [闸门2] check_clean_tree.py verdict=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["verdict"])' "$OUT_DIR/clean_tree.json") ----" | tee -a "$LE"

# ---- 闸门2b：.env.local 存在且不含开关/提示词变量 ----
[ -f "$WT/code/.env.local" ] || fail "闸门2b：无 code/.env.local" 31
grep -qE "^[[:space:]]*(export[[:space:]]+)?(LIFE_PROMPT_|HITT_DIALOGUE_PUBLIC_REPLY)" "$WT/code/.env.local" \
  && fail "闸门2b：.env.local 含 LIFE_PROMPT_* 或 HITT_DIALOGUE_PUBLIC_REPLY" 32
echo "闸门2b PASS：.env.local 中无 LIFE_PROMPT_* / HITT_DIALOGUE_PUBLIC_REPLY" | tee -a "$LE"

# ---- 起跑 shell 侧 env 快照 + 开关存在性断言 ----
cd "$WT/code" || exit 1
set -a; . "$WT/code/.env.local"; set +a
export HITT_LLM_PROVIDER=openai_compat HITT_WORLD_SEED="$SEED"
if [ "$ARM" = "on" ]; then export "$SWITCH=1"; else unset "$SWITCH"; fi
if [ -z "${!SWITCH+x}" ]; then SWITCH_STATE="UNSET（变量不存在）"; SWITCH_EXISTS=NO; else SWITCH_STATE="SET（值='${!SWITCH}'）"; SWITCH_EXISTS=YES; fi
if [ "$ARM" = "off" ] && [ "$SWITCH_EXISTS" = "NO" ]; then ENV_ASSERT=PASS
elif [ "$ARM" = "on" ] && [ "$SWITCH_EXISTS" = "YES" ] && [ "${!SWITCH}" = "1" ]; then ENV_ASSERT=PASS
else ENV_ASSERT=FAIL; fi
{
  echo "---- [起跑 shell 侧 env 快照 + 单变量存在性断言]（凭据脱敏） ----"
  echo "arm: $ARM"
  echo "$SWITCH = $SWITCH_STATE"
  echo "展开检验: \${$SWITCH+x}=${!SWITCH+x}"
  echo "存在性判定: $SWITCH_EXISTS （off 要求 NO；on 要求 YES 且值=1）"
  echo "开关断言: $ENV_ASSERT"
  echo "HITT_WORLD_SEED=${SEED}  （两臂均显式注入）"
  echo "HITT_LLM_PROVIDER=${HITT_LLM_PROVIDER:-<unset>}"
  echo "LLM_API_KEY=<set:${#LLM_API_KEY} chars>"
  env | grep -E '^(LIFE_PROMPT_|HITT_)' | grep -v 'API_KEY' | sed 's/^/  ENV /'; echo "  (env grep 结束)"
  echo "code_head=$(git -C "$WT" rev-parse HEAD)"
  echo "允许差异清单（两臂唯一允许不同项）：$SWITCH / out_dir+side_root+unit"
  echo "config sha256 清单："
  ( cd "$WT/code/config" && sha256sum *.json 2>/dev/null ) | sed 's/^/  CFG /'
  echo "执行路径 sha256："
  sha256sum "$WT/tools/d2/run_batch.sh" "$WT/tools/d2/emit_run_meta.py" 2>/dev/null | sed 's/^/  LAUNCHER /'
  echo "臂实现 sha256："
  sha256sum "$WT/code/life/public_talk.py" "$WT/code/life/agent.py" "$WT/code/orchestration/integration.py" 2>/dev/null | sed 's/^/  FROZEN /'
  echo "git status --short 快照（跑批前）："
  git -C "$WT" status --short | sed 's/^/  GIT /'
} | tee -a "$LE"
cp "$LE" "$OUT_DIR/env_dump.txt"; cp "$LE" "$OUT_DIR/switch_proof.txt"
[ "$ENV_ASSERT" = "PASS" ] || fail "开关存在性断言失败（arm=$ARM state=$SWITCH_STATE）⇒ 拒绝起跑" 25

cp "$SELF" "$OUT_DIR/launch.sh"

# ---- 起跑快照 ----
git -C "$WT" status --porcelain > "$OUT_DIR/git_status_start.txt"
echo "git_status_start 快照已写入（$(wc -l < "$OUT_DIR/git_status_start.txt") 行）" | tee -a "$LE"

# ---- 冻结身份与代码切片指纹 ----
git -C "$WT" rev-parse HEAD > "$OUT_DIR/frozen_sha.txt"
{
  echo "# 冻结区代码切片 sha256（本臂实际执行的树）"
  git -C "$WT" rev-parse HEAD
  sha256sum "$WT/code/life/public_talk.py" "$WT/code/life/agent.py" \
            "$WT/code/orchestration/integration.py" "$WT/tools/d2/run_batch.sh"
} > "$OUT_DIR/code_slice_check.txt"
{
  echo "# 读数器 / 渲染器指纹"
  sha256sum "$WT/tools/public_talk/public_talk_metrics.py" "$WT/tools/metrics/render_shots.py" \
            "$WT/tools/d5/preflight.sh" "$WT/tools/d5/check_clean_tree.py"
} > "$OUT_DIR/ruler_fingerprint.txt"

# ---- setsid 启动（团队纪律：外层套 setsid；run_batch.sh 自身不含） ----
INLINE_ENV="HITT_LLM_PROVIDER=openai_compat HITT_WORLD_SEED=$SEED"
if [ "$ARM" = "on" ]; then INLINE_ENV="$INLINE_ENV $SWITCH=1"; fi
INNER="cd '$WT/code' && set -a && . '$WT/code/.env.local' && set +a && export $INLINE_ENV && echo \$\$ > '$OUT_DIR/pid.txt' && bash '$WT/tools/d2/run_batch.sh' --out-dir '$OUT_DIR' --seed $SEED --agents $AGENTS --rounds $ROUNDS --flush-every $FLUSH --side-root '$SIDE_ROOT' >> '$HOSTLOG' 2>&1; echo \$? > '$OUT_DIR/run_batch.rc'"

{
  echo "[r41v] arm=$ARM  launcher=tools/public_talk/launch_r41v.sh  mode=setsid"
  echo "[r41v] INLINE_ENV=$INLINE_ENV"
  echo "[r41v] INNER=$INNER"
  echo "[r41v] code_sha=$(git -C "$WT" rev-parse HEAD)  branch=$(git -C "$WT" branch --show-current)"
  echo "[r41v] started_at=$(date -Is)"
} | tee -a "$HOSTLOG" > "$OUT_DIR/launch_cmd.txt"

T0=$(date +%s)
setsid bash -c "$INNER" < /dev/null > /dev/null 2>&1 &
SETSID_PID=$!
echo "$T0" > "$OUT_DIR/start_epoch.txt"
echo "$UNIT" > "$OUT_DIR/unit.txt"
echo "launched arm=$ARM setsid_pid=$SETSID_PID start_epoch=$T0 out=$OUT_DIR"
{
  echo "---- [启动自证] ----"
  echo "setsid_pid=$SETSID_PID"
  echo "start_epoch=$T0"
  echo "captured_at=$(date -Is)"
} | tee -a "$LE"
exit 0
