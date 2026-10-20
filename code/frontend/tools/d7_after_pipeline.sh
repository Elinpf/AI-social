#!/usr/bin/env bash
# d7_after_pipeline.sh — A0（改造后）数据集一键流水线：选目录 → 断言完整性 → 生成 → 出图 → 双跑门禁 → 打印报告回填值。
#
# 设计约束（对应 team-leader 的口径）：
#   * **只认**「带 meta.json 且 --require-complete 断言通过」的那一份；
#     `ABORTED_*` / 续跑目录 / 半截目录一律跳过（断言会挡）。
#   * 全部候选都不通过 → **不生成、不出图**，只打印各目录的断言输出并 rc=3。
#   * 本脚本是重活（扫大日志 + 起 chromium），**只在跑批窗口外执行**。
#
# 用法（在仓库根执行）：
#   bash code/frontend/tools/d7_after_pipeline.sh \
#        --pattern 'run_d2_after*' [--base-url http://127.0.0.1:8848] [--evidence v2/evidence]
#
# 成功后输出 KEY=VALUE 块（供回填 reports/D7-演示页面.md 的 [[A0_*]] 占位）。
set -uo pipefail

PATTERN="run_d2_after*"
BASE="http://127.0.0.1:8848"
EVID="v2/evidence"
while [ $# -gt 0 ]; do
  case "$1" in
    --pattern) PATTERN="$2"; shift 2;;
    --base-url) BASE="$2"; shift 2;;
    --evidence) EVID="$2"; shift 2;;
    *) echo "未知参数: $1" >&2; exit 2;;
  esac
done

GEN="code/frontend/tools/gen_threads.py"
echo "[1/5] 候选目录（模式 $PATTERN）："
CAND=$(ls -d "$EVID"/$PATTERN 2>/dev/null || true)
[ -n "$CAND" ] || { echo "没有匹配的目录，rc=3" >&2; exit 3; }
echo "$CAND" | sed 's/^/  - /'

echo "[2/5] 逐个跑完整性断言（--require-complete，不写文件）"
PICK=""
PICK_LOG=""
while IFS= read -r d; do
  [ -d "$d" ] || continue
  if [ ! -f "$d/run.jsonl" ] || [ ! -f "$d/meta.json" ]; then
    echo "  SKIP $(basename "$d")：缺 run.jsonl 或 meta.json"; continue
  fi
  if python3 "$GEN" --log "$d/run.jsonl" --meta "$d/meta.json" --summary --require-complete >/tmp/d7assert.log 2>&1; then
    echo "  PASS $(basename "$d")：$(grep -o 'TURN_SEAL.*' /tmp/d7assert.log | head -1)"
    PICK="$d"; PICK_LOG="$(cat /tmp/d7assert.log)"
  else
    echo "  FAIL $(basename "$d")：$(tail -1 /tmp/d7assert.log)"
  fi
done <<< "$CAND"

if [ -z "$PICK" ]; then
  echo "[3/5] 全部候选都不完整 → **不生成数据集、不出图**（没有数据比半截数据好）" >&2
  exit 3
fi
echo "[3/5] 采用：$PICK"

DIRNAME=$(basename "$PICK")
OUT="code/frontend/sample/dialogue_${DIRNAME}/threads.json"
python3 "$GEN" --log "$PICK/run.jsonl" --meta "$PICK/meta.json" --out "$OUT" --require-complete || exit 1

echo "[4/5] 出四张对照截图"
( cd code && bash frontend/tools/dialogue_shots.sh "$BASE" "sample/dialogue_${DIRNAME}/threads.json" ) || exit 1

echo "[5/5] 双跑门禁（改造前 + 改造后，两个都必须 PASS）"
BEFORE_OK=0; AFTER_OK=0
( cd code && python3 frontend/tools/verify_dialogue_page.py \
    --base-url "$BASE" --data sample/dialogue_v0anchor_n16_seed42/threads.json \
    --run v2/evidence/run_d2_before_n16_seed42/run.jsonl ) && BEFORE_OK=1
( cd code && python3 frontend/tools/verify_dialogue_page.py \
    --base-url "$BASE" --data "sample/dialogue_${DIRNAME}/threads.json" \
    --run "$PICK/run.jsonl" ) && AFTER_OK=1

python3 - "$OUT" "$DIRNAME" <<'PY'
import json, sys, pathlib
p = pathlib.Path(sys.argv[1]); d = json.loads(p.read_text(encoding="utf-8"))
s, st, comp = d["source"], d["stats"], d.get("completeness") or {}
print("\n===== 报告回填值 =====")
print("A0_DIR      =", sys.argv[2])
print("A0_LABEL    =", s.get("run_label"))
print("A0_SHA256   =", s.get("run_sha256"))
print("A0_SHA8     =", (s.get("run_sha256") or "")[:8])
print("A0_EVENTS   =", s.get("events_total_in_log"))
print("A0_MSGS     =", st.get("messages"))
print("A0_THREADS  =", st.get("threads"))
print("A0_MULTI    =", st.get("multi_turn_threads"))
print("A0_MAXTURNS =", st.get("max_turns"))
print("A0_SCHEMA   =", d.get("thread_schema"))
print("A0_MOVES    =", st.get("moves"))
print("A0_REFEDGES =", st.get("ref_edges"))
print("A0_COMPLETE =", comp.get("complete"), "/", comp.get("turn_seals"), "seals")
PY
echo "BEFORE_VERIFY_PASS=$BEFORE_OK  AFTER_VERIFY_PASS=$AFTER_OK"
[ "$BEFORE_OK" = "1" ] && [ "$AFTER_OK" = "1" ] && echo "PIPELINE PASS" || { echo "PIPELINE FAIL（门禁未双绿）" >&2; exit 1; }
