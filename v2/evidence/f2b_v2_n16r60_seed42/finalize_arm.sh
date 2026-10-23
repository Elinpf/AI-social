#!/usr/bin/env bash
# 收批后补齐一臂的「代码身份 + meta 断言 + 真跑验真」三件套（幂等、只读 run.jsonl）
# 背景同 R19 finalize_arm.sh：tools/d2/run_batch.sh 未传 --git-status-start ⇒
# meta.assertions.code_unchanged_during_run 为 null；本脚本用单一真源 tools/d2/emit_run_meta.py
# 重生成 meta，并传入**起跑时留存的 worktree git status 快照**。
#
# 用法：bash finalize_arm.sh <arm_dir> <switch_value(unset|1)>
set -euo pipefail
ARM_DIR="${1:?arm dir}"
SWITCH="${2:?switch value (unset|1)}"
E="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$E/../../.." && pwd)"
WT="$REPO/.worktrees/f2b-v2-n16r60"
cd "$WT"

echo "== 1) 四子树指纹（跑后，worktree 内）"
python3 "$WT/v2/evidence/r19_topicbreadth_n8r24_seed42/fingerprint_4trees.py" --out "$ARM_DIR/code_fingerprint.txt"

echo "== 2) 开关落证（可解析行）"
{ echo "# 开关最终取值（行为侧硬证据另见：off 臂 ctx.topic_breadth 出现次数必须=0）"
  echo "LIFE_PROMPT_TOPIC_BREADTH=$SWITCH"; } >> "$ARM_DIR/env_dump.txt"
tail -3 "$ARM_DIR/env_dump.txt"

echo "== 3) 重生成 meta.json（沿用 run_batch 记下的 started/finished/duration，传起跑快照）"
python3 - "$ARM_DIR/meta.json" > "$ARM_DIR/meta_times.env" <<'PY'
import json,sys
m=json.load(open(sys.argv[1],encoding="utf-8"))
for k in ("started_at","finished_at","duration_sec","events","llm_calls","code_sha"):
    v=m.get(k)
    print(f'{k.upper()}={v}')
PY
cat "$ARM_DIR/meta_times.env"
. "$ARM_DIR/meta_times.env"
python3 tools/d2/emit_run_meta.py --run-dir "$ARM_DIR" --seed 42 --n 16 --rounds 60 \
  --git-status-start "$E/git_status_start_wt.txt" \
  --git-status-start-source "实拍：起跑前 worktree git status --porcelain 快照（$E/git_status_start_wt.txt，0 行）" \
  --started-at "${STARTED_AT}" --finished-at "${FINISHED_AT}" --duration-sec "${DURATION_SEC}" | tail -3

echo "== 4) 断言核对"
python3 - "$ARM_DIR/meta.json" <<'PY'
import json,sys
m=json.load(open(sys.argv[1],encoding="utf-8"))
print("assertions.code_unchanged_during_run =", m["assertions"]["code_unchanged_during_run"])
print("code_sha =", m["code_sha"], "| events =", m["events"], "| llm_calls =", m["llm_calls"])
print("llm_provider_in_events =", m["llm_provider_in_events"])
PY

echo "== 5) 真跑验真（obs llm-cost；rc 必须 0）"
set +e
( cd "$WT/code" && python3 -m obs llm-cost --log "$ARM_DIR/run.jsonl" \
      --require-provider openai_compat --out "$ARM_DIR/llmcost.json" ) \
  > "$ARM_DIR/llmcost_stdout.txt" 2>&1
RC=$?
set -e
echo "rc=$RC" | tee -a "$ARM_DIR/llmcost_stdout.txt"
python3 - "$ARM_DIR/llmcost.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
e=d.get("engine_log") or d
t=e.get("total",{})
print("by_provider =", e.get("by_provider"), "| calls =", t.get("calls"),
      "| tokens_in =", t.get("tokens_in"), "| tokens_out =", t.get("tokens_out"),
      "| cached =", t.get("cached"), "| degraded =", t.get("degraded"))
print("provider_guard =", d.get("provider_guard"))
bp = e.get("by_purpose") or {}
print("by_purpose.dialogue =", bp.get("dialogue"))
PY
echo "== done: $ARM_DIR rc_llmcost=$RC"
