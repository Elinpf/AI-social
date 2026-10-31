#!/usr/bin/env bash
# F-3 OFF 臂重跑（全新 side-root，杜绝旧 freeze cache 回放）。
set -uo pipefail
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
OUT=v2/evidence/r38_f3_batch
TL="$REPO/$OUT/timeline_off_rerun.txt"
cd "$REPO"

# 全新目录（先确认为空，再起）
SIDE=/tmp/r38_f3_side_off_fresh
rm -rf "$SIDE"
mkdir -p "$SIDE"
echo "side_root=$SIDE cache_files_before=$(find "$SIDE" -type f | wc -l)" >> "$TL"

echo "off_start=$(date -Is)" >> "$TL"
setsid bash tools/d2/run_batch.sh --out-dir "$OUT/off" \
  --seed 42 --agents 16 --rounds 24 --side-root "$SIDE" \
  > /tmp/r38_f3_off_rerun.stdout 2>&1 < /dev/null
rc=$?
echo "off_rc=$rc off_end=$(date -Is)" >> "$TL"
echo "$rc" > "$REPO/$OUT/off.rc"
exit "$rc"
