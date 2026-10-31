#!/usr/bin/env bash
# R41 公开面接话臂 · 双小批严格串行（先 OFF 后 ON，同 seed / 同 agents / 同 rounds）
#
# 纪律（逐条对齐团队与本仓既有规矩）：
#   * 串行：前臂拿到 rc 才起后臂；两臂之间**再**跑一次 pgrep 三重确认（见 run_batch.sh 自带 preflight）；
#   * 后台：本脚本自身用 `setsid` 托管启动（见 round-impl-notes.md 的启动命令），内部不再 setsid；
#   * 变量唯一：两臂同 commit、同树，唯一自变量是 `HITT_DIALOGUE_PUBLIC_REPLY`；
#   * side-root 各自独立：不复用 `/tmp/d9t_*`（外部批的 side-root），避免 freeze 缓存串味；
#   * 日志：每臂 stdout 落 `<arm>/host.txt`（`*.log` 被 .gitignore 忽略，故用 .txt）。
set -uo pipefail
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
OUT=v2/evidence/r41_public_talk
TL="$REPO/$OUT/timeline.txt"
cd "$REPO" || exit 2

SEED=42
AGENTS=8
ROUNDS=8

echo "off_start=$(date -Is) seed=$SEED agents=$AGENTS rounds=$ROUNDS" >> "$TL"
env -u HITT_DIALOGUE_PUBLIC_REPLY bash tools/d2/run_batch.sh \
  --out-dir "$OUT/off" --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" \
  --side-root /tmp/r41_pt_off_side > "$REPO/$OUT/off/host.txt" 2>&1 < /dev/null
rc_off=$?
echo "off_rc=$rc_off off_end=$(date -Is)" >> "$TL"
echo "$rc_off" > "$REPO/$OUT/off.rc"

if [[ "$rc_off" -ne 0 ]]; then
  echo "OFF ARM FAILED rc=$rc_off -> 不起 ON 臂" >> "$TL"
  exit "$rc_off"
fi

echo "on_start=$(date -Is)" >> "$TL"
env HITT_DIALOGUE_PUBLIC_REPLY=1 bash tools/d2/run_batch.sh \
  --out-dir "$OUT/on" --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" \
  --side-root /tmp/r41_pt_on_side > "$REPO/$OUT/on/host.txt" 2>&1 < /dev/null
rc_on=$?
echo "on_rc=$rc_on on_end=$(date -Is)" >> "$TL"
echo "$rc_on" > "$REPO/$OUT/on.rc"
exit "$rc_on"
