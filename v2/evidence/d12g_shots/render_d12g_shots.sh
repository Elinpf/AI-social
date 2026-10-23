#!/usr/bin/env bash
# render_d12g_shots.sh — CYCLE-11 / D12-G 真实截图渲染（保留空白检测，不绕过）
#
# 用法（在仓库根执行，静态服务已起在 BASE）：
#   bash v2/evidence/d12g_shots/render_d12g_shots.sh <base_url> <data_rel> <outdir>
# 例：
#   bash v2/evidence/d12g_shots/render_d12g_shots.sh http://127.0.0.1:8848 \
#        sample/dialogue_d12g_diverse2/threads.json v2/evidence/d12g_shots
#
# 事实来源（不靠人填）：threads.json 的 source.run_label / source.run_sha256 → sha8
# 线程清单：<outdir>/threads_selected.txt，每行 "<短标签>|<thread_id>"（由选择依据决定，见 README）
#
# 注意：**不传 --no-blank-check**。空白/单色帧一律按 shot.py 判据 FAIL，
#       会打印 max_color_frac 与 blank_retries，本脚本逐字落进 render_wrap.log。
set -uo pipefail

BASE="${1:?需要 base_url，如 http://127.0.0.1:8848}"
DATA="${2:?需要 threads.json 相对路径（相对 code/frontend）}"
OUTDIR="${3:?需要输出目录}"

REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
SHOT="$REPO/code/frontend/tools/shot.py"
LOG="$OUTDIR/render_wrap.log"
SEL="$OUTDIR/threads_selected.txt"

THREADS_JSON="$REPO/code/frontend/$DATA"
[ -s "$THREADS_JSON" ] || { echo "FAIL: threads.json 不存在 $THREADS_JSON" >&2; exit 2; }

# ---- 从 threads.json 取事实：label + 日志字节 sha，sha8 由此而来，不许人填 ----
META=$(python3 - "$THREADS_JSON" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
s = d.get("source") or {}
print(s.get("run_label") or "")
print(s.get("run_sha256") or "")
PY
) || { echo "FAIL: 读取 threads.json 失败" >&2; exit 2; }
LABEL=$(echo "$META" | sed -n 1p)
RUN_SHA=$(echo "$META" | sed -n 2p)
[ -n "$LABEL" ] || { echo "FAIL: 缺 source.run_label" >&2; exit 2; }
[ -n "$RUN_SHA" ] || { echo "FAIL: 缺 source.run_sha256" >&2; exit 2; }
SHA8="${RUN_SHA:0:8}"
STEM="${LABEL%-$SHA8}"

mkdir -p "$OUTDIR"
: > "$LOG"
echo "=== RENDER_START $(date -Is)  data=$DATA  label=$LABEL  run_sha256=$RUN_SHA  sha8=$SHA8" | tee -a "$LOG"

# ---- 单次渲染 + 逐字落日志（保留空白检测；--retry-blank 2 仅取证容错） ----
shot () { # name w h query expect_sha8
  local name="$1" w="$2" h="$3" q="$4"
  local out="$OUTDIR/${STEM}-${name}-${SHA8}.png"
  local begin rc
  begin=$(date -Is)
  echo "→ BEGIN ${STEM}-${name}-${SHA8}  $begin" | tee -a "$LOG"
  echo "   CMD: python3 code/frontend/tools/shot.py --url \"${BASE}/dialogue.html?${q}&data=${DATA}\" --out \"${out}\" --width ${w} --height ${h} --retry-blank 2" | tee -a "$LOG"
  {
    python3 "$SHOT" --url "${BASE}/dialogue.html?${q}&data=${DATA}" \
        --out "$out" --width "$w" --height "$h" --retry-blank 2
  } 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  echo "→ END ${STEM}-${name}-${SHA8}  $(date -Is)  rc=${rc}" | tee -a "$LOG"

  # 体积 + 读数复核（max_color_frac ≥50% 或 mean_brightness 过低 → 标 SUSPECT）
  if [ -f "$out" ]; then
    local sz; sz=$(stat -c '%s' "$out")
    local mb mcf
    mb=$(grep -o 'mean_brightness=[0-9.]*' "$LOG" | tail -1 | cut -d= -f2)
    mcf=$(grep -o 'max_color_frac=[0-9.]*%' "$LOG" | tail -1 | tr -d '%' | cut -d= -f2)
    echo "   SIZE: $(basename "$out") ${sz} bytes" | tee -a "$LOG"
    python3 - "$mb" "$mcf" "$name" <<'PY' | tee -a "$LOG"
import sys
mb = float(sys.argv[1]) if sys.argv[1] else -1
mcf = float(sys.argv[2]) if sys.argv[2] else -1
flags = []
if mcf >= 50: flags.append(f"max_color_frac {mcf:.2f}% ≥50%")
if 0 <= mb < 20: flags.append(f"mean_brightness {mb:.1f} 偏低")
print("   SELFCHK: " + ("SUSPECT → " + "; ".join(flags) if flags else "OK"))
PY
  else
    echo "   SIZE: (无图，未生成)" | tee -a "$LOG"
  fi
  return "$rc"
}

# ---- 视图 1：对话流（只看多轮 = 生活气息口径） ----
shot chat   1400 900  "still=1&multi=1&min=0&sort=turns"
# ---- 视图 2：节律·串门 ----
shot rhythm 1300 1050 "still=1&multi=1&min=0&view=rhythm"

# ---- 视图 3..N：逐线程聚焦（thread=<id> + q=<该线程唯一短语> 收窄到单卡；见 threads_selected.txt / README） ----
# 为什么还要 q：body.still 下 overflow:hidden，滚不动，单靠 thread= 只会展开但截不到（实测 scrollY 恒 0）。
# q 用该线程正文里「全库只出现一次」的短语，页面因此只渲染 1 张卡，目标线程自然落在视口顶部。
if [ -s "$SEL" ]; then
  while IFS='|' read -r tag tid qph; do
    [ -z "${tag:-}" ] && continue
    case "$tag" in \#*) continue ;; esac
    QENC=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$qph")
    shot "thread-${tag}" 1400 1000 "still=1&min=0&sort=turns&thread=${tid}&q=${QENC}"
  done < "$SEL"
else
  echo "WARN: 缺线程清单 $SEL，跳过逐线程聚焦视图" | tee -a "$LOG"
fi

echo "=== RENDER_END $(date -Is)" | tee -a "$LOG"
grep -c 'rc=0' "$LOG" | sed 's/^/OK_COUNT=/' | tee -a "$LOG"
grep -c 'rc=[1-9]' "$LOG" | sed 's/^/FAIL_COUNT=/' | tee -a "$LOG"
