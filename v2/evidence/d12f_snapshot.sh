#!/usr/bin/env bash
# D12-F 单次采集 wrapper：**一条命令出全部读数**，杜绝"手写时点/多项错配"。
#
# 纪律（auditor §时点协议）：
#   1. TS 只取本脚本执行瞬间的 `date -Iseconds`，同一个 TS 传给所有产物；
#   2. 先 `stat` + `wc -l` + `grep -c TURN_SEAL` 记录源文件真实状态；
#   3. 三份产物（gate JSON / m0 curve JSON+MD / adjacent 两份 MD）同一次采集完成；
#   4. 终态另需 `run.jsonl.tmp` 不存在（或已合入）且 `wc -l run.jsonl == meta.events`。
#
# 用法：
#   bash v2/evidence/d12f_snapshot.sh partial   # 期中快照
#   bash v2/evidence/d12f_snapshot.sh final     # 终态（跑完后）
set -euo pipefail

MODE="${1:-partial}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="$ROOT/.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42"
RUN="$RUN_DIR/run.jsonl"
OUT="$ROOT/v2/evidence"
TAG="$(date +%H%M)"

TS="$(date -Iseconds)"
echo "[snapshot] TS=$TS MODE=$MODE"
echo "[snapshot] stat: $(stat -c 'mtime=%y size=%s' "$RUN")"
LINES="$(wc -l < "$RUN")"
SEALS="$(grep -c TURN_SEAL "$RUN" || true)"
echo "[snapshot] lines=$LINES seals=$SEALS"
if [[ -e "$RUN_DIR/run.jsonl.tmp" ]]; then
  echo "[snapshot] WARN: run.jsonl.tmp 仍存在 → $(stat -c 'size=%s mtime=%y' "$RUN_DIR/run.jsonl.tmp")"
fi

EXTRA=()
if [[ "$MODE" == "final" ]]; then EXTRA+=(--final); else EXTRA+=(--partial); fi

python3 "$OUT/d12f_gate_metrics.py" --run-jsonl "$RUN" --ctx-key d12f \
  --snapshot-at "$TS" "${EXTRA[@]}" \
  --out-json "$OUT/d12f_gates_${MODE}.json" > /dev/null

python3 "$OUT/d12f_m0_curve.py" --run-jsonl "$RUN" --snapshot-at "$TS" "${EXTRA[@]}" \
  --out-json "$OUT/d12f_m0_curve_${MODE}.json" > /dev/null

python3 "$OUT/d12f_adjacent_pairs.py" --run-jsonl "$RUN" --snapshot-at "$TS" --seals "$SEALS" \
  ${EXTRA[@]+"${EXTRA[@]}"} --out-md "$OUT/d12f_adjacent_dialogue_pairs_${MODE}.md" > /dev/null

echo "[snapshot] done: $TS / seals=$SEALS / lines=$LINES"
echo "[snapshot] products:"
for f in "$OUT/d12f_gates_${MODE}.json" "$OUT/d12f_m0_curve_${MODE}.json" "$OUT/d12f_adjacent_dialogue_pairs_${MODE}.md"; do
  echo "  $(sha256sum "$f")"
done
