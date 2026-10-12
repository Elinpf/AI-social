#!/usr/bin/env bash
# T274 验收演示（全 mock，不碰真批）：起 2 批 → kill 一批 → 收报中断 → 续 → 收成功 → 清理
set -euo pipefail
BIN="$(cd "$(dirname "$0")" && pwd)"
D="${T271_DEMO_DIR:-/root/t271/demo}"; mkdir -p "$D"
RUN_ROOT="${T271_RUN_ROOT:-/root/t271/runs/nightly}"; rm -rf "$RUN_ROOT"; mkdir -p "$RUN_ROOT"
printf 'T271_NOOP=1\n' > "$D/dummy.env"
PY=/opt/openjiuwen/workswarm-venv/bin/python
MOCKCMD="$PY $BIN/mock_batch.py --out {out} --rounds 40 --agents 2 --seed 42 --flush-every 5 --round-seconds 1.5 --heartbeat-seconds 3"
{ printf 'name\trounds\tagents\tseed\tswitch\tresume_mode\ttree\tflush\tcmd\n'
  printf 'm1\t40\t2\t42\t-\tnative\tcopy\t5\t%s\n' "$MOCKCMD"
  printf 'm2\t40\t2\t42\t-\tnative\tcopy\t5\t%s\n' "$MOCKCMD"; } > "$D/batches.mock.tsv"

echo "### 1) 一键起"
python3 "$BIN/nightly.py" start --batches "$D/batches.mock.tsv" --env-file "$D/dummy.env" --heartbeat 3
sleep 8
echo "### 2) 模拟中断（kill m2）"
BP=$(cat /root/t271/runs/nightly/m2/batch.pid 2>/dev/null || echo '')
echo "kill m2 pid=$BP"; kill -9 "$BP" 2>/dev/null || true
sleep 3
echo "### 3) 一键收（应报中断）"
python3 "$BIN/nightly.py" collect
echo "### 4) 失败可续"
python3 "$BIN/nightly.py" resume --batches "$D/batches.mock.tsv" --env-file "$D/dummy.env" --heartbeat 3
while python3 "$BIN/nightly.py" status | grep -q RUNNING; do sleep 3; done
echo "### 5) 终收（应全 SUCCESS）"
python3 "$BIN/nightly.py" collect
echo "### 6) 清理（删副本 + side 打包）"
python3 "$BIN/nightly.py" cleanup
