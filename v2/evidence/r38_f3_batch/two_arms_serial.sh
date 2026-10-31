#!/usr/bin/env bash
# F-3 OFF/ON 严格串行双臂。前臂拿到 rc 才起后臂。
set -uo pipefail
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
OUT=v2/evidence/r38_f3_batch
TL="$REPO/$OUT/timeline.txt"
cd "$REPO"

echo "off_start=$(date -Is)" >> "$TL"
setsid bash tools/d2/run_batch.sh --out-dir "$OUT/off" \
  --seed 42 --agents 16 --rounds 24 --side-root /tmp/r38_f3_side_off \
  > /tmp/r38_f3_off.stdout 2>&1 < /dev/null
rc_off=$?
echo "off_rc=$rc_off off_end=$(date -Is)" >> "$TL"
echo "$rc_off" > "$REPO/$OUT/off.rc"

if [[ "$rc_off" -ne 0 ]]; then
  echo "OFF ARM FAILED rc=$rc_off -> 不起 ON 臂" >> "$TL"
  exit "$rc_off"
fi

echo "on_start=$(date -Is)" >> "$TL"
setsid env HITT_DIALOGUE_EMOTION_ECHO=1 bash tools/d2/run_batch.sh --out-dir "$OUT/on" \
  --seed 42 --agents 16 --rounds 24 --side-root /tmp/r38_f3_side_on \
  > /tmp/r38_f3_on.stdout 2>&1 < /dev/null
rc_on=$?
echo "on_rc=$rc_on on_end=$(date -Is)" >> "$TL"
echo "$rc_on" > "$REPO/$OUT/on.rc"
exit "$rc_on"
