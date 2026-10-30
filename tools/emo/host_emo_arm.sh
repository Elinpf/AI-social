#!/usr/bin/env bash
# tools/emo/host_emo_arm.sh —— 单臂「托管起跑」（systemd-run transient unit，脱离 jiuwenswarm.service cgroup）
#
# 为什么自己起 unit 而不用 tools/t271/host_batch.sh：
#   host_batch.sh 的 systemd-run 参数是写死的，无法追加 `-p Environment=...`；
#   而 life-engineer 交接口径明确要求 ON 臂把开关**既内联、又进 unit 属性**（双保险，都可审计）。
#   本脚本不修改 t271 装置，只补齐这一个缺口。
#
# 用法:
#   bash tools/emo/host_emo_arm.sh <on|off> <out_dir> <tag>
# 说明:
#   - 凭据只走 EnvironmentFile（= code/.env.local），**绝不 --setenv**（否则密钥进 systemctl show / ps / journal）
#   - OFF 臂不注入 HITT_DIALOGUE_*：unit 环境默认不继承本 shell，天然 unset
set -uo pipefail

ARM="${1:?用法: host_emo_arm.sh <on|off> <out_dir> <tag>}"
OUT_DIR="${2:?缺少 out_dir}"
TAG="${3:-$ARM}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 2
mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"   # systemd 的 append: 路径必须是绝对路径

case "$ARM" in
  on)  ENVPROPS=(-p Environment=HITT_DIALOGUE_EMOTION_ECHO=1 -p Environment=HITT_DIALOGUE_REPAIR=1) ;;
  off) ENVPROPS=() ;;
  *)   echo "[host-emo] arm 必须是 on|off" >&2; exit 2 ;;
esac

UNIT="emo-${TAG}-$(date +%H%M%S)"
systemctl stop "$UNIT" 2>/dev/null || true
systemctl reset-failed "$UNIT" 2>/dev/null || true

{
  echo "[host-emo] ts=$(date -Is)"
  echo "[host-emo] unit=$UNIT arm=$ARM out_dir=$OUT_DIR"
  echo "[host-emo] env_props=${ENVPROPS[*]:-<none>}"
} >> "$OUT_DIR/host_launch.txt"

systemd-run --unit="$UNIT" --collect \
  --working-directory="$ROOT" \
  -p Type=simple \
  -p MemoryHigh=6G -p MemoryMax=8G \
  -p Restart=no -p KillMode=control-group \
  -p "EnvironmentFile=$ROOT/code/.env.local" \
  "${ENVPROPS[@]}" \
  -p StandardOutput=append:"$OUT_DIR/host.log" \
  -p StandardError=append:"$OUT_DIR/host.log" \
  bash "$ROOT/tools/emo/emo_runner.sh" "$OUT_DIR" "$ARM" \
       --seed 42 --agents 16 --rounds 24 --flush-every 2

{
  echo "[host-emo] launched at $(date -Is)"
  systemctl show "$UNIT" -p Id -p ControlGroup -p MainPID --no-pager
} | tee -a "$OUT_DIR/host_launch.txt"
echo "[host-emo] unit=$UNIT out_dir=$OUT_DIR host.log=$OUT_DIR/host.log heartbeat=$OUT_DIR/heartbeat.tsv"
