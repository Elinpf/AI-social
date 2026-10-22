#!/usr/bin/env bash
# R19 · 收批后补齐一臂的「代码身份 + meta 断言 + 真跑验真」三件套（幂等、只读 run.jsonl）
#
# 背景：`tools/d2/run_batch.sh` 未传 `--git-status-start`，因此它生成的 meta 里
# `assertions.code_unchanged_during_run` 是 null；S1 门禁要求必须为 true。
# 本脚本用**单一真源** `tools/d2/emit_run_meta.py` 重生成 meta，并把起跑时留存的
# `git status --porcelain` 快照传给它（快照文件由调用方给出，缺省用本目录的 git_status_start.txt）。
#
# 用法：
#   bash finalize_arm.sh <arm_dir> <switch_value> <git_status_start_file> <started_at> <finished_at> <duration_sec>
# 例：
#   bash finalize_arm.sh .../run_off unset .../git_status_start.txt 2026-10-22T20:15:21+08:00 ... 520
set -euo pipefail

ARM_DIR="${1:?arm dir}"
SWITCH="${2:?switch value (unset|0|1)}"
GS_START="${3:?git status start file}"
STARTED="${4:-}"
FINISHED="${5:-}"
DURATION="${6:-}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
cd "$REPO"

echo "== 1) 四子树指纹（跑后）"
python3 "$HERE/fingerprint_4trees.py" --out "$ARM_DIR/code_fingerprint.txt"

echo "== 2) 开关落证（可解析行）"
{
  echo "# 开关最终取值（行为侧硬证据另见：off 臂 ctx.topic_breadth 计数必须=0）"
  echo "LIFE_PROMPT_TOPIC_BREADTH=$SWITCH"
} >> "$ARM_DIR/env_dump.txt"
tail -3 "$ARM_DIR/env_dump.txt"

echo "== 3) 重生成 meta.json（传起跑快照 ⇒ code_unchanged_during_run=true）"
ARGS=(--run-dir "$ARM_DIR" --seed 42 --n 8 --rounds 24
      --git-status-start "$GS_START"
      --git-status-start-source "实拍：起跑时留存的 git status --porcelain 快照文件；跑后由 finalize_arm.sh 传入单一真源工具重生成 meta")
[[ -n "$STARTED" ]] && ARGS+=(--started-at "$STARTED")
[[ -n "$FINISHED" ]] && ARGS+=(--finished-at "$FINISHED")
[[ -n "$DURATION" ]] && ARGS+=(--duration-sec "$DURATION")
python3 tools/d2/emit_run_meta.py "${ARGS[@]}" | tail -4

echo "== 4) 断言核对"
python3 - "$ARM_DIR/meta.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1], encoding="utf-8"))
print("assertions.code_unchanged_during_run =", m["assertions"]["code_unchanged_during_run"])
print("code_sha =", m["code_sha"], "| events =", m["events"], "| llm_calls =", m["llm_calls"])
print("llm_provider_in_events =", m["llm_provider_in_events"])
PY

echo "== 5) 真跑验真（obs llm-cost；rc 必须 0）"
( cd code && python3 -m obs llm-cost --log "../$ARM_DIR/run.jsonl" \
      --require-provider openai_compat --out "../$ARM_DIR/llmcost.json" ) \
  > "$ARM_DIR/llmcost_stdout.txt" 2>&1
echo "rc=$?" | tee -a "$ARM_DIR/llmcost_stdout.txt"
python3 - "$ARM_DIR/llmcost.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
e = d.get("engine_log") or d
t = e.get("total", {})
print("by_provider =", e.get("by_provider"), "| calls =", t.get("calls"),
      "| tokens_in =", t.get("tokens_in"), "| tokens_out =", t.get("tokens_out"),
      "| cached =", t.get("cached"), "| degraded =", t.get("degraded"),
      "| thinking =", t.get("thinking"))
print("provider_guard =", d.get("provider_guard"))
PY

echo "== done: $ARM_DIR"
