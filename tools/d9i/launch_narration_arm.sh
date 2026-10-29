#!/usr/bin/env bash
# tools/d9i/launch_narration_arm.sh —— D9i「旁白通道」单臂起跑封装（OFF/ON 两臂只有 LIFE_PROMPT_NARRATION 不同）
#
# 与 tools/emo/launch_emo_arm.sh 同形态，只把开关换成 LIFE_PROMPT_NARRATION ∈ {0(默认=现状), 1(允许成对括号旁白)}。
#
# 用法：
#   bash tools/d9i/launch_narration_arm.sh <off|on> <out_dir> [--seed 42] [--agents 16] [--rounds 24] [--flush-every 2]
#
# 语义：
#   ON  臂：export LIFE_PROMPT_NARRATION=1
#   OFF 臂：显式 unset LIFE_PROMPT_NARRATION ⇒ 代码默认分支 = 改动前字面量（逐字节等价）
#
# 落盘证据（每臂）：
#   env_pre_shell_<arm>.txt   起跑前 shell 层声明（仅自查，真值看 switch_proof.txt 的 /proc environ）
#   launch_cmd.txt            实际命令行
#   switch_proof.txt          被执行层 /proc/<pid>/environ 的开关真值 + cmdline + cgroup（runbook §3.98b）
#   start_end.txt             起止时间与耗时
#   run.jsonl / meta.json     run_batch.sh 产出
#   run.rc / run_batch.rc     退出码
#   llm_cost.json / llm_cost.txt / llm_cost.rc   obs llm-cost 真跑验真（--require-provider openai_compat）
#   heartbeat.tsv             心跳（时间 / run.jsonl 字节数 / 最近 round）
set -uo pipefail

ARM="${1:?用法: launch_narration_arm.sh <off|on> <out_dir> [run_batch params]}"
OUT_DIR="${2:?缺少 out_dir}"
shift 2 || true

SEED=42; AGENTS=16; ROUNDS=24; FLUSH=2
while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed) SEED="$2"; shift 2 ;;
    --agents) AGENTS="$2"; shift 2 ;;
    --rounds) ROUNDS="$2"; shift 2 ;;
    --flush-every) FLUSH="$2"; shift 2 ;;
    *) echo "[narr-arm] unknown arg: $1" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 2
mkdir -p "$OUT_DIR"
OUT_ABS="$(cd "$OUT_DIR" && pwd)"

case "$ARM" in
  on)
    export LIFE_PROMPT_NARRATION=1
    DECL="1" ;;
  off)
    unset LIFE_PROMPT_NARRATION 2>/dev/null || true
    DECL="<unset>" ;;
  *)
    echo "[narr-arm] arm 必须是 on|off，收到: $ARM" >&2; exit 2 ;;
esac
export PYTHONUNBUFFERED=1

# 起跑前 shell 层声明（仅自查）
{
  echo "ts=$(date -Is)"
  echo "arm=$ARM"
  echo "declared_LIFE_PROMPT_NARRATION=$DECL"
  echo "note=本文件是起跑前 shell 层声明值；真值取 /proc/<pid>/environ（switch_proof.txt）"
} > "$OUT_ABS/env_pre_shell_$ARM.txt"

CMD=(bash tools/d2/run_batch.sh --out-dir "$OUT_ABS" --seed "$SEED" --agents "$AGENTS"
     --rounds "$ROUNDS" --flush-every "$FLUSH" --side-root "/tmp/narr_${ARM}_n${AGENTS}r${ROUNDS}_s${SEED}")
{
  echo "[narr-arm] arm=$ARM out_dir=$OUT_ABS"
  echo "[narr-arm] declared LIFE_PROMPT_NARRATION=$DECL"
  echo "[narr-arm] cmd: ${CMD[*]}"
  echo "[narr-arm] script_sha256=$(sha256sum "${BASH_SOURCE[0]}" | awk '{print $1}')"
} | tee "$OUT_ABS/launch_cmd.txt"

STARTED="$(date -Iseconds)"; T0=$(date +%s)

# --- 心跳：独立后台，每 60s 落一行（不靠会话内轮询）
HB_SEC="${NARR_HEARTBEAT_SEC:-60}"
(
  while [[ ! -f "$OUT_ABS/.arm_done" ]]; do
    sz=$(stat -c %s "$OUT_ABS/run.jsonl" 2>/dev/null || echo -1)
    rd=$(tail -c 262144 "$OUT_ABS/run.jsonl" 2>/dev/null | python3 -c '
import sys, json
last=None
for line in sys.stdin.buffer.read().split(b"\n"):
    line=line.strip()
    if not line: continue
    try: r=json.loads(line)
    except Exception: continue
    if isinstance(r,dict) and "round" in r: last=r["round"]
print(-1 if last is None else last)
' 2>/dev/null || echo -1)
    printf '%s\t%s\t%s\n' "$(date '+%F %T')" "$sz" "$rd" >> "$OUT_ABS/heartbeat.tsv"
    sleep "$HB_SEC"
  done
) &
HB_PID=$!

# --- switch_proof：在跑批进程活着时读 /proc/<pid>/environ（唯一可信来源）
#     注意：这段内联 python 不把 pgrep 模式写进任何 *外部* cmdline，避免被 preflight 误判为并发。
(
  for _ in $(seq 1 600); do
    NARR_PROOF_DIR="$OUT_ABS" NARR_PROOF_ARM="$ARM" python3 - <<'PY'
import os, re, subprocess, time
out = os.environ["NARR_PROOF_DIR"]; arm = os.environ["NARR_PROOF_ARM"]
pat = re.compile(rb"orchestration\x00run")   # python -m orchestration run 的 cmdline 形式
pids = subprocess.run(["pgrep", "-f", "orchestration"], capture_output=True, text=True).stdout.split()
for p in pids:
    try:
        cl = open(f"/proc/{p}/cmdline", "rb").read()
    except Exception:
        continue
    if not pat.search(cl):
        continue
    env = open(f"/proc/{p}/environ", "rb").read().split(b"\x00")
    keys = (b"LIFE_PROMPT_NARRATION=", b"HITT_LLM_PROVIDER=", b"FREEZE_MODE=")
    lines = [e.decode(errors="replace") for e in env if e.startswith(keys)]
    cg = open(f"/proc/{p}/cgroup").read().strip()
    txt = []
    txt.append("# switch_proof（被执行层自证，runbook §3.98b）")
    txt.append(f"captured_at={time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    txt.append(f"arm={arm}")
    txt.append(f"resolved_pid={p}")
    txt.append(f"pid_cgroup={cg}")
    txt.append("--- @ 1 /proc/<pid>/environ（开关真值；仅摘相关键）")
    txt.append("\n".join(lines) if lines else "(无相关键输出：该进程 environ 中不存在 LIFE_PROMPT_NARRATION / HITT_LLM_PROVIDER / FREEZE_MODE)")
    txt.append("--- @ 2 /proc/<pid>/cmdline")
    txt.append(cl.replace(b"\x00", b" ").decode(errors="replace").strip())
    txt.append("--- @ 3 期望")
    txt.append("OFF 臂期望：LIFE_PROMPT_NARRATION 无输出（显式 unset ⇒ 代码走默认分支 = 改动前逐字节）"
               if arm == "off" else
               "ON 臂期望：LIFE_PROMPT_NARRATION=1")
    open(os.path.join(out, "switch_proof.txt"), "w", encoding="utf-8").write("\n".join(txt) + "\n")
    raise SystemExit(0)
PY
    [[ -s "$OUT_ABS/switch_proof.txt" ]] && break
    sleep 1
  done
) &
PROOF_PID=$!

# --- 真实执行（run_batch.sh 内部含 d5 preflight + obs llm-cost 门禁）
"${CMD[@]}"
RC=$?
echo "$RC" > "$OUT_ABS/run.rc"
echo "$RC" > "$OUT_ABS/run_batch.rc"
FINISHED="$(date -Iseconds)"; T1=$(date +%s)
: > "$OUT_ABS/.arm_done"
wait "$PROOF_PID" 2>/dev/null || true

# --- 真 LLM 验真（独立落盘，rc≠0 该臂无效）
LC_JSON="$OUT_ABS/llm_cost.json"; LC_TXT="$OUT_ABS/llm_cost.txt"
set +e
PYTHONPATH="$ROOT/code${PYTHONPATH:+:$PYTHONPATH}" python3 -m obs llm-cost --log "$OUT_ABS/run.jsonl" --require-provider openai_compat --out "$LC_JSON" > "$LC_TXT" 2>&1
LC_RC=$?
set -e
echo "$LC_RC" > "$OUT_ABS/llm_cost.rc"

{
  echo "arm=$ARM"
  echo "started_at=$STARTED"
  echo "finished_at=$FINISHED"
  echo "duration_sec=$((T1 - T0))"
  echo "run_batch_rc=$RC"
  echo "llm_cost_rc=$LC_RC"
} > "$OUT_ABS/start_end.txt"

# --- 收尾（幂等）
if [[ ! -f "$OUT_ABS/END.json" ]]; then
  python3 - "$OUT_ABS" "$ARM" "$RC" "$LC_RC" "$STARTED" "$FINISHED" <<'PY'
import json, os, sys
d = sys.argv[1]; arm = sys.argv[2]; rc = int(sys.argv[3]); lc = int(sys.argv[4])
out = {"arm": arm, "run_batch_rc": rc, "llm_cost_rc": lc,
       "started_at": sys.argv[5], "finished_at": sys.argv[6],
       "meta_json_present": os.path.exists(os.path.join(d, "meta.json")),
       "switch_proof_present": os.path.exists(os.path.join(d, "switch_proof.txt"))}
try:
    m = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    out.update({"code_sha": m.get("code_sha"), "provider": m.get("provider"),
                "model": m.get("model"), "events": m.get("events"),
                "duration_sec_meta": m.get("duration_sec")})
except Exception as e:
    out["meta_read_error"] = str(e)
json.dump(out, open(os.path.join(d, "END.json"), "w"), ensure_ascii=False, indent=2)
print("[narr-arm] END.json:", json.dumps(out, ensure_ascii=False))
PY
fi

kill "$HB_PID" 2>/dev/null || true
echo "[narr-arm] arm=$ARM run_batch rc=$RC llm_cost rc=$LC_RC"
exit "$RC"
