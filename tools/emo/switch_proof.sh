#!/usr/bin/env bash
# tools/emo/switch_proof.sh —— 取「被执行的那一层」的开关真值（runbook §3.98b 标准三件套）
#
# 用法: bash tools/emo/switch_proof.sh <out_dir> <arm:on|off>
# 依赖: <out_dir>/batch.pid（emo_runner.sh 写入）+ 该 out_dir 对应的 unit cgroup
#
# 为什么不能用 printenv：printenv 读的是**执行 printenv 的 shell** 的环境，而开关真正生效在跑批进程里；
# D12-B 事故就是把 =1 记成 <unset>。⇒ 唯一可信来源是 /proc/<pid>/environ，再加 cmdline 与 cgroup 交叉印证。
#
# pid 定位：先取 batch.pid 的**其后代**里 cmdline 含 `orchestration run` 的进程（run_batch → python3 -m orchestration），
#          因为 batch.pid 指向的是 bash 封装，真正的跑批进程是它的子进程。
# OFF 臂的期望是**该键组无输出**（显式期望，不写「未设置」这种含糊话）。
set -uo pipefail

OUT_DIR="${1:?缺少 out_dir}"
ARM="${2:?缺少 arm(on|off)}"
PIDFILE="$OUT_DIR/batch.pid"
PROOF="$OUT_DIR/switch_proof.txt"
[[ -r "$PIDFILE" ]] || { echo "[proof] FATAL: 缺 $PIDFILE（批次还没起来？）" >&2; exit 3; }

# 收集进程树（含 batch.pid 自身）
descendants() {
  local root="$1"
  echo "$root"
  local kids; kids="$(pgrep -P "$root" 2>/dev/null || true)"
  for k in $kids; do descendants "$k"; done
}
TREE="$(descendants "$(cat "$PIDFILE")" | tr '\n' ' ')"
PID=""
for p in $TREE; do
  if tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -q "orchestration run"; then PID="$p"; break; fi
done
if [[ -z "$PID" ]]; then
  echo "[proof] WARN: 进程树里没有 'orchestration run'（可能还在 preflight/import 阶段），退回 batch.pid 并只取其进程树环境" >&2
  PID="$(cat "$PIDFILE")"
fi
[[ -d "/proc/$PID" ]] || { echo "[proof] FATAL: pid=$PID 已不存在" >&2; exit 4; }

ENV_ALL="$(tr '\0' '\n' < "/proc/$PID/environ" 2>/dev/null || true)"
ENV_LINES="$(echo "$ENV_ALL" | grep -E '^(HITT_DIALOGUE_EMOTION_ECHO|HITT_DIALOGUE_REPAIR|HITT_LLM_PROVIDER|FREEZE_MODE)=' || true)"
CMDLINE="$(tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null)"
CGROUP="$(cat "/proc/$PID/cgroup" 2>/dev/null)"
DIALOGUE_LINES="$(echo "$ENV_LINES" | grep -E '^HITT_DIALOGUE_' || true)"

if [[ "$ARM" == "off" ]]; then
  EXPECT="OFF 臂期望：HITT_DIALOGUE_* 在 /proc/$PID/environ 中【无输出】（显式 unset；config 默认 enabled=false）"
else
  EXPECT="ON 臂期望：env 里同时出现 HITT_DIALOGUE_EMOTION_ECHO=1 与 HITT_DIALOGUE_REPAIR=1"
fi

{
  echo "# switch_proof（被执行层自证，runbook §3.98b）"
  echo "captured_at=$(date -Is)"
  echo "arm=$ARM"
  echo "batch_pid_file=$(cat "$PIDFILE")"
  echo "resolved_pid=$PID"
  echo "pid_cgroup=$CGROUP"
  echo "--- ① /proc/$PID/environ（唯一可信的开关真值来源；仅摘相关键）"
  if [[ -n "$ENV_LINES" ]]; then echo "$ENV_LINES"; else echo "(无相关键输出)"; fi
  echo "--- ② /proc/$PID/cmdline"
  echo "$CMDLINE"
  echo "--- ③ 期望"
  echo "$EXPECT"
} | tee "$PROOF"

ok=1
if [[ "$ARM" == "on" ]]; then
  grep -qx "HITT_DIALOGUE_EMOTION_ECHO=1" <<<"$ENV_LINES" || { echo "[proof] FAIL: 缺 HITT_DIALOGUE_EMOTION_ECHO=1" >&2; ok=0; }
  grep -qx "HITT_DIALOGUE_REPAIR=1" <<<"$ENV_LINES" || { echo "[proof] FAIL: 缺 HITT_DIALOGUE_REPAIR=1" >&2; ok=0; }
else
  [[ -z "$DIALOGUE_LINES" ]] || { echo "[proof] FAIL: OFF 臂却出现 HITT_DIALOGUE_* 键: $DIALOGUE_LINES" >&2; ok=0; }
fi
[[ "$ok" -eq 1 ]] && echo "[proof] OK arm=$ARM（三件套已落 $PROOF）"
exit $(( ok == 1 ? 0 : 5 ))
