#!/usr/bin/env bash
# render_d27_shots.sh —— D2.7 真实截图（同一 thread_id 的 C vs B 对照）
# 用法（仓库根，静态服务已在 8848）：bash v2/evidence/d27_shots/render_d27_shots.sh [base_url]
# 空白检测**不绕过**（不传 --no-blank-check）；逐字落日志 render_wrap.log。
set -uo pipefail
BASE="${1:-http://127.0.0.1:8848}"
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT="$REPO/v2/evidence/d27_shots"
SHOT="$REPO/code/frontend/tools/shot.py"
LOG="$OUT/render_wrap.log"
cd "$REPO/code" || exit 2
mkdir -p "$OUT"; : > "$LOG"

sha8 () { python3 -c "
import json,sys
d=json.load(open('frontend/sample/dialogue_d27_$1/threads.json',encoding='utf-8'))
print((d['source']['run_sha256'])[:8])"; }

shot () { # arm name w h query
  local arm="$1" name="$2" w="$3" h="$4" q="$5"
  local s8 out
  s8=$(sha8 "$arm")
  out="$OUT/d27-$arm-$name-$s8.png"
  echo "→ CMD: python3 code/frontend/tools/shot.py --url \"${BASE}/dialogue.html?${q}&data=sample/dialogue_d27_${arm}/threads.json\" --out \"$out\" --width $w --height $h" | tee -a "$LOG"
  python3 "$SHOT" --url "${BASE}/dialogue.html?${q}&data=sample/dialogue_d27_${arm}/threads.json" \
      --out "$out" --width "$w" --height "$h" 2>&1 | tee -a "$LOG"
  local rc=${PIPESTATUS[0]}
  [ -f "$out" ] && echo "   SIZE $(basename "$out") $(stat -c %s "$out") bytes  rc=$rc" | tee -a "$LOG"
  return "$rc"
}

TID=TH-P009-P008-24
QC=$(python3 -c "import urllib.parse;print(urllib.parse.quote('算盘珠子拨了一早上'))")
QB=$(python3 -c "import urllib.parse;print(urllib.parse.quote('冷馍顶不了账'))")

# 视图1/2：同一线程单卡聚焦（C 无旁白 / B 有旁白）——"台词被挤短"的直接对照
shot C thread-focus 1400 1000 "still=1&min=0&sort=turns&thread=$TID&q=$QC"
shot B thread-focus 1400 1000 "still=1&min=0&sort=turns&thread=$TID&q=$QB"
# 视图3：B 的对话流（多轮口径，看旁白在整页上的密度）
shot B chat-multi 1400 900 "still=1&multi=1&min=0&sort=turns"

echo "=== OK_COUNT=$(grep -c 'SIZE ' "$LOG") FAIL_COUNT=$(grep -cE 'rc=[1-9]' "$LOG") ===" | tee -a "$LOG"
