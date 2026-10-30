#!/usr/bin/env bash
# tools/emo/launch_emo_arm.sh —— 缺口①（情绪回声 + 对话修复）ON/OFF 两臂的**单臂**起跑封装
#
# 为什么需要它：
#   1) tools/d2/run_batch.sh 已内含 d5 串行闸 + meta.json 单一真源 + 真跑门禁，但不写 run_batch.rc；
#   2) 本封装补齐**退出码留痕**（run_batch.rc）与**起跑前 shell 层开关自查**（env_pre_shell_*.txt），
#      并把「两臂只有开关不同」固化成参数（on|off），避免手抄命令行漏带/多带开关。
#   ⚠️ 真正的开关自证在 tools/emo/switch_proof.sh（读 /proc/<pid>/environ），**不用 printenv**（runbook §3.98b）。
#
# 用法（由 tools/emo/emo_runner.sh 在 transient unit 内调用）：
#   bash tools/emo/launch_emo_arm.sh <on|off> <out_dir> [--seed 42] [--agents 16] [--rounds 24] [--flush-every 2]
#
# 开关语义（2026-10-29 复核 code/life/emotion_echo.py 与 code/life/dialogue_repair.py 实现）：
#   HITT_DIALOGUE_EMOTION_ECHO ∈ {1,true,on,yes} → 开；其它任意取值（含 0/off/空串）→ 关；**未设 ⇒ 跟随 config 默认值**
#   HITT_DIALOGUE_REPAIR       ∈ {1,true,on,yes} → 开；{0,false,off,...}      → 关；**未设 ⇒ 跟随 config 默认值**
#   config 两文件默认 enabled=false（impl-101 未改默认值）。
#   ⇒ ON 臂：两个都显式 =1（不依赖默认值，防止将来 config 默认值改成 true 后「ON/OFF 其实是同一臂」）；
#   ⇒ OFF 臂：两个都**显式 unset** —— 历史默认语义（life-engineer 交接口径优先「不设」），与 `=0` 等价；
#     关法在 switch_proof.txt 里按「无输出」硬判定，不靠含糊说法。
#
# 退出码：0=正常收尾；其余为 run_batch.sh 原样透传（3/4/5/6/7/9 见其注释）
set -uo pipefail

ARM="${1:?用法: launch_emo_arm.sh <on|off> <out_dir> [run_batch params]}"
OUT_DIR="${2:?缺少 out_dir}"
shift 2 || true

SEED=42; AGENTS=16; ROUNDS=24; FLUSH=2
while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed) SEED="$2"; shift 2 ;;
    --agents) AGENTS="$2"; shift 2 ;;
    --rounds) ROUNDS="$2"; shift 2 ;;
    --flush-every) FLUSH="$2"; shift 2 ;;
    *) echo "[emo-arm] unknown arg: $1" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 2
mkdir -p "$OUT_DIR"

case "$ARM" in
  on)
    export HITT_DIALOGUE_EMOTION_ECHO=1
    export HITT_DIALOGUE_REPAIR=1
    DECL_ECHO="1"; DECL_REPAIR="1" ;;
  off)
    unset HITT_DIALOGUE_EMOTION_ECHO HITT_DIALOGUE_REPAIR 2>/dev/null || true
    DECL_ECHO="<unset>"; DECL_REPAIR="<unset>" ;;
  *)
    echo "[emo-arm] arm 必须是 on|off，收到: $ARM" >&2; exit 2 ;;
esac
export PYTHONUNBUFFERED=1

# 起跑前「本 shell 层」的开关声明（**仅自查**；不得作为 switch_proof，见 runbook §3.98b）
{
  echo "ts=$(date -Is)"
  echo "arm=$ARM"
  echo "declared_HITT_DIALOGUE_EMOTION_ECHO=$DECL_ECHO"
  echo "declared_HITT_DIALOGUE_REPAIR=$DECL_REPAIR"
  echo "note=本文件是起跑前 shell 层声明值；真值取 /proc/<batch_pid>/environ（switch_proof.sh）"
} > "$OUT_DIR/env_pre_shell_$ARM.txt"

CMD=(bash tools/d2/run_batch.sh --out-dir "$OUT_DIR" --seed "$SEED" --agents "$AGENTS"
     --rounds "$ROUNDS" --flush-every "$FLUSH" --side-root "/tmp/emo_${ARM}_n${AGENTS}r${ROUNDS}_s${SEED}")
{
  echo "[emo-arm] arm=$ARM out_dir=$OUT_DIR"
  echo "[emo-arm] switches: HITT_DIALOGUE_EMOTION_ECHO=$DECL_ECHO HITT_DIALOGUE_REPAIR=$DECL_REPAIR"
  echo "[emo-arm] cmd: ${CMD[*]}"
} | tee "$OUT_DIR/launch_cmd.txt"

# 真实执行（run_batch.sh 内部会再跑一次 tools/d5/preflight.sh；其祖先链排除机制保证不自判并发）
"${CMD[@]}"
RC=$?
echo "$RC" > "$OUT_DIR/run_batch.rc"
echo "[emo-arm] run_batch rc=$RC → $OUT_DIR/run_batch.rc"
exit "$RC"
