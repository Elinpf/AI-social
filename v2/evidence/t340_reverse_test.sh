#!/usr/bin/env bash
# T340 反向验证：跑 make verify 期间「改树」⇒ 必须判 exit 2（结果不可信）。
#   做法：后台起 `make verify`（受守卫），待「起跑指纹」出现后，在 code/config 下新增一个未跟踪文件
#   （内容极小、非 .json，不被 config loader 误读）⇒ 收尾指纹应不同 ⇒ exit 2。
set -uo pipefail
REPO="$(git rev-parse --show-toplevel)"; cd "$REPO" || exit 2
PROBE="code/config/_t340probe.probe"
LOG=/tmp/t340_rev.log
rm -f "$PROBE" "$LOG"

make verify > "$LOG" 2>&1 &
MP=$!
# 等内部门起跑
for _ in $(seq 1 90); do grep -q "起跑指纹" "$LOG" 2>/dev/null && break; sleep 1; done
F0="$(grep -o '起跑指纹.* = [0-9a-f]*' "$LOG" | awk '{print $NF}')"
echo "[rev] 起跑指纹=$F0；现于跑中改树：新增 $PROBE"
sleep 6
printf 't340 probe\n' > "$PROBE"
wait $MP; rc=$?
rm -f "$PROBE"
echo "[rev] REVERSE rc=$rc （期望 2）"
grep -E "起跑指纹|收尾指纹|跑中树被改|跑中树未变" "$LOG" | head
