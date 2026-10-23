#!/usr/bin/env bash
# F-5 / F-5b / F-1 跨批零成本复算 —— 一键复现脚本
# 纪律：只读日志、零 LLM 调用、不跑批、不改 code/
# 口径唯一来源：tools/d5/dialogue_metrics.py（不重写指标实现）
#
# 用法（在仓库根目录 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment 执行）：
#   bash v2/evidence/f5-crossbatch-20261023/run.sh
#
# 产出：
#   raw/metrics_<批>.json / .md   —— 每批完整指标 JSON（含 F-5_habit_repetition / F-1_chatter）
#   raw/coverage_<批>.json        —— 覆盖度事实（天数/槽/place 缺失率/agent 数），非指标实现
#   f5_crossbatch.csv             —— 跨批对照表
#   tool_manifest.txt             —— 工具与词表的路径 / mtime / sha256
set -euo pipefail

REPO="/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment"
OUT="$REPO/v2/evidence/f5-crossbatch-20261023"
TOOL="$REPO/tools/d5/dialogue_metrics.py"
cd "$REPO"
mkdir -p "$OUT/raw"

# ---- 工具与词表身份（可复算前提）----
{
  echo "generated_at: $(date -Iseconds)"
  echo "--- 工具文件 ---"
  for f in tools/d5/dialogue_metrics.py tools/d5/backref_lexicon.txt tools/d5/template_patterns.txt \
           tools/d5/emotion_lexicon.txt tools/d5/repair_lexicon.txt tools/d5/timeref_lexicon.txt \
           tools/d5/task_tags.txt tools/d5/f8_lexicon.json code/config/personas.json code/config/places.json; do
    [ -e "$f" ] && printf '%s\tmtime=%s\tsha256=%s\n' "$f" "$(stat -c %y "$f")" "$(sha256sum "$f" | cut -d' ' -f1)"
  done
  echo "--- 日志文件 ---"
  for f in v2/evidence/run_d12b_off_seed7_n16r24/run.jsonl \
           v2/evidence/run_d12b_on_seed7_n16r24/run.jsonl \
           v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl \
           v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
           v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl \
           v2/evidence/run_scene_anchor_off_seed42_n16r24/run.jsonl \
           v2/evidence/run_scene_anchor_on_seed42_n16r24/run.jsonl; do
    [ -e "$f" ] && printf '%s\tmtime=%s\tsha256=%s\n' "$f" "$(stat -c %y "$f")" "$(sha256sum "$f" | cut -d' ' -f1)"
  done
  echo "--- python ---"
  python3 -V
} > "$OUT/tool_manifest.txt"

# ---- 逐批复算（--meta 存在才传）----
run_one () {
  local tag="$1" log="$2" meta="$3"
  local args=(--log "$log" --out-json "$OUT/raw/metrics_${tag}.json" --out-md "$OUT/raw/metrics_${tag}.md")
  [ -n "$meta" ] && [ -e "$meta" ] && args+=(--meta "$meta")
  echo "[recompute] $tag"
  python3 "$TOOL" "${args[@]}" > "$OUT/raw/stdout_${tag}.txt" 2>&1
  python3 "$OUT/f5_coverage.py" --log "$log" --out "$OUT/raw/coverage_${tag}.json"
  python3 "$OUT/f5_saturation.py" --log "$log" --out "$OUT/raw/saturation_${tag}.json"
}

run_one d12b_off        v2/evidence/run_d12b_off_seed7_n16r24/run.jsonl        v2/evidence/run_d12b_off_seed7_n16r24/meta.json
run_one d12b_on         v2/evidence/run_d12b_on_seed7_n16r24/run.jsonl         v2/evidence/run_d12b_on_seed7_n16r24/meta.json
run_one d12c_off        v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl       v2/evidence/run_d12c_off_n16r60_seed42/meta.json
run_one d12c_on         v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl        v2/evidence/run_d12c_on_n16r60_seed42/meta.json
run_one d12d_on         v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl        v2/evidence/run_d12d_on_n16r60_seed42/meta.json
run_one scene_anchor_off v2/evidence/run_scene_anchor_off_seed42_n16r24/run.jsonl v2/evidence/run_scene_anchor_off_seed42_n16r24/meta.json
run_one scene_anchor_on  v2/evidence/run_scene_anchor_on_seed42_n16r24/run.jsonl  v2/evidence/run_scene_anchor_on_seed42_n16r24/meta.json

# ---- 汇总对照表 ----
python3 "$OUT/f5_build_table.py" --dir "$OUT" --out "$OUT/f5_crossbatch.csv"
echo "OK -> $OUT/f5_crossbatch.csv"

# ---- 批次骨架同一性检查（解释 F-5 为何跨臂逐位相同）----
python3 "$OUT/f5_skeleton_identity.py" \
  --log d12b_off=v2/evidence/run_d12b_off_seed7_n16r24/run.jsonl \
  --log d12b_on=v2/evidence/run_d12b_on_seed7_n16r24/run.jsonl \
  --log d12c_off=v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl \
  --log d12c_on=v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --log d12d_on=v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl \
  --log scene_anchor_off=v2/evidence/run_scene_anchor_off_seed42_n16r24/run.jsonl \
  --log scene_anchor_on=v2/evidence/run_scene_anchor_on_seed42_n16r24/run.jsonl \
  --out "$OUT/raw/skeleton_identity.json"
