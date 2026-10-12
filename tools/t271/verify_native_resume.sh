#!/usr/bin/env bash
# native 续跑链验证（T276/T288 落地后）：真 orchestration 中断 -> nightly native 续跑 ->
# 到目标回合 -> collect 报 SUCCESS；并与「一次性跑」逐字节比对（复用同一 side_root）。
#
# native 自证用法（对新 sha / 新配置跑；分钟级）：
#   T271_VR_SEED=42 T271_VR_AGENTS=4 T271_VR_ROUNDS=24 T271_VR_KILL_AFTER=1 T271_VR_GATE=1 \
#     bash tools/t271/verify_native_resume.sh
# 门禁 = 参数正确 + 判对状态；T271_VR_GATE=1 时"语义不一致"也判失败（=native 前提自证）。
#
# 【本门回答什么】(2026-10-12 Leader 裁定, 方案(b))：回答"**世界语义是否一致**"，不比本地 freeze 缓存
#   命中状态。比较用【世界语义投影 sha256】(tools/t271/semantic_log_sha.py)：排除 LLM_CALL.payload 的
#   {cached,tokens_in,tokens_out,cost_units}（本地缓存计量、与语义无关），**其余字段全比**（保留 cache_key
#   ⇒ 两路"发出的调用集合"不同则仍必须报红）。整份原 sha 仅打印作参考。
#   备选方案 (a)预热对等 / (c)维持现状 见 runbook §4。反向验证：T271_VR_REVERSE=1（扰动 1 个语义字段→须报红）。
set -uo pipefail
BIN="$(cd "$(dirname "$0")" && pwd)"
source "$BIN/safe_rmrf.sh"   # T313 rm -rf 守卫
REPO="${T271_REPO:-/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment}"
PY="/opt/openjiuwen/workswarm-venv/bin/python"
VR="${T271_NR_ROOT:-/root/t271/runs/nr}"
export T271_RUN_ROOT="$VR"
safe_rmrf "$VR"; mkdir -p "$VR/_env"
printf 'T271_NOOP=1\n' > "$VR/_env/dummy.env"
ENVF="$VR/_env/dummy.env"
SEED=${T271_VR_SEED:-9}; AGENTS=${T271_VR_AGENTS:-2}; ROUNDS=${T271_VR_ROUNDS:-150}
FLUSH=${T271_VR_FLUSH:-5}; GATE=${T271_VR_GATE:-0}
# 仪器：kill 用【跑到指定 round】而非墙钟（避免 cut 随负载漂移 -> 假"间歇"）；逐字节比对的 cut 显式参数化
KILLROUND=${T271_VR_KILLROUND:-$((ROUNDS/2))}
CUT=${T271_VR_CUT:-$((ROUNDS/2))}

PASS=1
ck(){ if [ "$1" = "$2" ]; then echo "  ok: $3"; else echo "  FAIL: $3 (got='$1' want='$2')"; PASS=0; fi; }
lastround(){ tail -1 "$1" 2>/dev/null | python3 -c 'import sys,json;print(json.loads(sys.stdin.readline()).get("round"))' 2>/dev/null || echo -1; }

{ printf 'name\trounds\tagents\tseed\tswitch\tresume_mode\ttree\tflush\tout\tcmd\n'
  printf 'N1\t%s\t%s\t%s\t-\tnative\tcopy\t%s\t\t\n' "$ROUNDS" "$AGENTS" "$SEED" "$FLUSH"; } > "$VR/batches.tsv"

echo "### 1) 起 N1（真 orchestration, mock provider），跑到 round=$KILLROUND 再 kill"
python3 "$BIN/nightly.py" start --batches "$VR/batches.tsv" --env-file "$ENVF" --heartbeat 600 >"$VR/N1.launch.log" 2>&1
# 跑到 KILLROUND 再 kill（不用墙钟——否则 cut 随负载漂移，制造假"间歇"）
for _ in $(seq 1 1200); do
  LR=$(lastround "$VR/N1/run.jsonl")
  [ "${LR:--1}" -ge "$KILLROUND" ] && break
  BPx=$(cat "$VR/N1/batch.pid" 2>/dev/null || echo '')
  kill -0 "$BPx" 2>/dev/null || break
  sleep 0.2
done
BP=$(cat "$VR/N1/batch.pid" 2>/dev/null || echo '')
if [ -n "$BP" ] && kill -0 "$BP" 2>/dev/null; then
  echo "  kill pid=$BP (到 round≈$KILLROUND)"; kill -9 "$BP" 2>/dev/null || true
  sleep 2
  LR=$(lastround "$VR/N1/run.jsonl")
  echo "  中断时日志 round=$LR (应 < $((ROUNDS-1)))"
  ck "$(python3 "$BIN/nightly.py" status --run-root "$VR" | awk '$1=="N1"{print $2}')" "INTERRUPTED" "中断被检出"
else
  echo "  [SKIP] N1 在到达 round=$KILLROUND 前已跑完（rounds 太少/太快）"
fi

echo "### 2) nightly native 续跑"
python3 "$BIN/nightly.py" resume --batches "$VR/batches.tsv" --env-file "$ENVF" --heartbeat 600 2>&1 | grep -E "resume\]" || true
for _ in $(seq 1 120); do
  R=$(lastround "$VR/N1/run.jsonl")
  ST=$(python3 "$BIN/nightly.py" status --run-root "$VR" | awk '$1=="N1"{print $2}')
  [ "$R" = "$((ROUNDS-1))" ] && [ "$ST" != "RUNNING" ] && break
  sleep 1
done
ck "$(lastround "$VR/N1/run.jsonl")" "$((ROUNDS-1))" "续跑到目标回合 $((ROUNDS-1))"
ck "$(python3 "$BIN/nightly.py" status --run-root "$VR" | awk '$1=="N1"{print $2}')" "SUCCESS" "collect 判 native 续跑批为 SUCCESS"

echo "### 3) 逐字节比对（用【持久共享 side_root】+ 预热，冷/热缓存一致；复刻本流水线生成的续跑参数）"
S="$VR/side_shared"; safe_rmrf "$S"; mkdir -p "$S"
oneshot(){ ( cd /tmp/t271-N1/code && "$PY" -m orchestration run --life --seed "$SEED" --agents "$AGENTS" \
    --rounds "$ROUNDS" --out "$1" --side-root "$S" --flush-every "$FLUSH" ); }
oneshot "$VR/warm.jsonl"    >>"$VR/oneshot.log" 2>&1   # 预热 freeze 缓存
oneshot "$VR/ref.jsonl"      >>"$VR/oneshot.log" 2>&1   # 热跑基准
# 【用固定前缀，消除 kill 时序变量】：从 ref.jsonl 截到最后一个 TURN_SEAL@CUT -> n1b.jsonl，再 resume。
# （kill 路径由上面步骤 1–2 覆盖：跑到 KILLROUND 中断检出 + nightly native 续跑到 target。）
# CUT 由 T271_VR_CUT 参数化（默认 ROUNDS/2）；cut=75 暴露真分歧(红)，cut=89 无分歧(绿)。
python3 - "$VR/ref.jsonl" "$VR/n1b.jsonl" "$CUT" <<'PYEOF'
import sys, json
src, out, cut = sys.argv[1], sys.argv[2], int(sys.argv[3])
keep = []
for l in open(src, encoding="utf-8"):
    keep.append(l)
    r = json.loads(l)
    if r.get("type") == "TURN_SEAL" and r.get("round") == cut:
        break
open(out, "w", encoding="utf-8").writelines(keep)
print(f"[prefix] 截到 TURN_SEAL@{cut}, lines={len(keep)}")
PYEOF
( cd /tmp/t271-N1/code && "$PY" -m orchestration run --life --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" \
    --resume-from "$VR/n1b.jsonl" --target-round "$ROUNDS" --out "$VR/n1b.jsonl" \
    --side-root "$S" --flush-every "$FLUSH" ) >>"$VR/oneshot.log" 2>&1 || true
S1=$(python3 "$BIN/semantic_log_sha.py" "$VR/n1b.jsonl" 2>/dev/null | awk '{print $1}')   # 世界语义投影 sha
S2=$(python3 "$BIN/semantic_log_sha.py" "$VR/ref.jsonl" 2>/dev/null | awk '{print $1}')
R1=$(sha256sum "$VR/n1b.jsonl" 2>/dev/null | cut -d' ' -f1); R2=$(sha256sum "$VR/ref.jsonl" 2>/dev/null | cut -d' ' -f1)
echo "  语义投影 sha: resumed=$S1 oneshot=$S2  [seed=$SEED n=$AGENTS rounds=$ROUNDS]"
echo "  整份原 sha : resumed=$R1 oneshot=$R2 （仅参考，含本地缓存计量）"
# 本门回答"世界语义是否一致"（排除本地缓存计量字段）；GATE=1 时不一致即失败。
if [ "$S1" = "$S2" ]; then
  echo "  PROBE ok: 世界语义一致（排除 {cached,tokens_in,tokens_out,cost_units} 后逐字节相等）"
else
  echo "  ✗ PROBE 不一致（世界语义）：resumed=$S1 oneshot=$S2"
  if [ "$GATE" = "1" ]; then
    echo "  (T271_VR_GATE=1 ⇒ 该 sha/配置【未通过】native 前提自证 → 建议用 overlap)"
    PASS=0
  else
    echo "  (仅探针；要把它当门禁请设 T271_VR_GATE=1)"
  fi
fi

# 显式核 TURN_SEAL.state_hash 相等（T299 验收要求）
if python3 - "$VR/n1b.jsonl" "$VR/ref.jsonl" >"$VR/statehash.log" 2>&1 <<'PYEOF'
import sys, json
def seals(p):
    d = {}
    for l in open(p, encoding="utf-8"):
        try: r = json.loads(l)
        except Exception: continue
        if r.get("type") == "TURN_SEAL":
            d[r.get("round")] = (r.get("payload") or {}).get("state_hash")
    return d
a, b = seals(sys.argv[1]), seals(sys.argv[2])
bad = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
print(f"TURN_SEAL.state_hash 不等数={len(bad)}（应为 0）")
sys.exit(0 if not bad else 1)
PYEOF
then echo "  ok: $(cat "$VR/statehash.log")"; else echo "  ✗ $(cat "$VR/statehash.log")"; PASS=0; fi

# 反向验证（必要性）：最小【agent 决策】扰动 -> 门必须仍报红
if [ "${T271_VR_REVERSE:-0}" = "1" ]; then
  if python3 "$BIN/semantic_log_sha.py" --selftest "$VR/ref.jsonl" >"$VR/reverse.log" 2>&1; then
    echo "  REVERSE ok: 最小语义扰动仍报红 -> $(cat "$VR/reverse.log")"
  else
    echo "  ✗ REVERSE FAIL: 语义差异未被捕获 -> $(cat "$VR/reverse.log")"; PASS=0
  fi
fi

for u in t271-N1; do systemctl stop "$u" 2>/dev/null; systemctl reset-failed "$u" 2>/dev/null; done
echo
[ "$PASS" = "1" ] && echo "############ NATIVE-RESUME VERIFY: PASS ############" || echo "############ NATIVE-RESUME VERIFY: FAIL ############"
exit $((1-PASS))
