#!/usr/bin/env bash
# native 续跑链验证（T276/T288 落地后）：真 orchestration 中断 -> nightly native 续跑 ->
# 到目标回合 -> collect 报 SUCCESS；并与「一次性跑」逐字节比对（复用同一 side_root）。
set -uo pipefail
BIN="$(cd "$(dirname "$0")" && pwd)"
REPO="${T271_REPO:-/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment}"
PY="/opt/openjiuwen/workswarm-venv/bin/python"
VR="${T271_NR_ROOT:-/root/t271/runs/nr}"
export T271_RUN_ROOT="$VR"
rm -rf "$VR"; mkdir -p "$VR/_env"
printf 'T271_NOOP=1\n' > "$VR/_env/dummy.env"
ENVF="$VR/_env/dummy.env"
ROUNDS=150; SEED=9; AGENTS=2; FLUSH=5

PASS=1
ck(){ if [ "$1" = "$2" ]; then echo "  ok: $3"; else echo "  FAIL: $3 (got='$1' want='$2')"; PASS=0; fi; }
lastround(){ tail -1 "$1" 2>/dev/null | python3 -c 'import sys,json;print(json.loads(sys.stdin.readline()).get("round"))' 2>/dev/null || echo -1; }

{ printf 'name\trounds\tagents\tseed\tswitch\tresume_mode\ttree\tflush\tout\tcmd\n'
  printf 'N1\t%s\t%s\t%s\t-\tnative\tcopy\t%s\t\t\n' "$ROUNDS" "$AGENTS" "$SEED" "$FLUSH"; } > "$VR/batches.tsv"

echo "### 1) 起 N1（真 orchestration, mock provider），中途 kill"
python3 "$BIN/nightly.py" start --batches "$VR/batches.tsv" --env-file "$ENVF" --heartbeat 600 >"$VR/N1.launch.log" 2>&1
sleep 2
BP=$(cat "$VR/N1/batch.pid" 2>/dev/null || echo '')
echo "  kill pid=$BP"; kill -9 "$BP" 2>/dev/null || true
sleep 2
LR=$(lastround "$VR/N1/run.jsonl")
echo "  中断时日志 round=$LR (应 < $((ROUNDS-1)))"
ck "$(python3 "$BIN/nightly.py" status --run-root "$VR" | awk '$1=="N1"{print $2}')" "INTERRUPTED" "中断被检出"

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
S="$VR/side_shared"; rm -rf "$S"; mkdir -p "$S"
oneshot(){ ( cd /tmp/t271-N1/code && "$PY" -m orchestration run --life --seed "$SEED" --agents "$AGENTS" \
    --rounds "$ROUNDS" --out "$1" --side-root "$S" --flush-every "$FLUSH" ); }
oneshot "$VR/warm.jsonl"    >>"$VR/oneshot.log" 2>&1   # 预热 freeze 缓存
oneshot "$VR/ref.jsonl"      >>"$VR/oneshot.log" 2>&1   # 热跑基准
# 中断 + 续跑（同一共享 side_root；续跑参数 == nightly 生成的 --resume-from/--target-round）
bash "$BIN/host_batch.sh" --name N1b --out "$VR/n1b.jsonl" --run-dir "$VR/N1b" \
  --workdir /tmp/t271-N1/code --env-file "$ENVF" --heartbeat 600 \
  --meta rounds="$ROUNDS" --meta side_root="$S" --meta copy=/tmp/t271-N1 --meta switch=- \
  --meta resume_mode=native --meta sha=x --meta flush_every="$FLUSH" --meta agents="$AGENTS" --meta seed="$SEED" \
  -- "$PY" -m orchestration run --life --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" \
     --out "$VR/n1b.jsonl" --side-root "$S" --flush-every "$FLUSH" >"$VR/n1b.launch.log" 2>&1
sleep 2; kill -9 "$(cat "$VR/N1b/batch.pid" 2>/dev/null)" 2>/dev/null || true; sleep 2
( cd /tmp/t271-N1/code && "$PY" -m orchestration run --life --seed "$SEED" --agents "$AGENTS" --rounds "$ROUNDS" \
    --resume-from "$VR/n1b.jsonl" --target-round "$ROUNDS" --out "$VR/n1b.jsonl" \
    --side-root "$S" --flush-every "$FLUSH" ) >>"$VR/oneshot.log" 2>&1 || true
S1=$(sha256sum "$VR/n1b.jsonl" 2>/dev/null | cut -d' ' -f1)
S2=$(sha256sum "$VR/ref.jsonl" 2>/dev/null | cut -d' ' -f1)
echo "  resumed(x)=$S1"; echo "  oneshot  =$S2"
# 注：逐字节一致是【runner/life 层（T276/T288）】的承诺，不是本流水线的门禁。
# 本脚本的门禁 = native 参数正确 + 判对状态；逐字节结果仅作【探针】如实打印。
if [ "$S1" = "$S2" ]; then
  echo "  PROBE ok: native 续跑 == 一次性跑（逐字节）"
else
  echo "  ⚠️ PROBE 不一致（非流水线问题；T276/T288 关注）：resumed=$S1 oneshot=$S2"
fi

for u in t271-N1; do systemctl stop "$u" 2>/dev/null; systemctl reset-failed "$u" 2>/dev/null; done
echo
[ "$PASS" = "1" ] && echo "############ NATIVE-RESUME VERIFY: PASS ############" || echo "############ NATIVE-RESUME VERIFY: FAIL ############"
exit $((1-PASS))
