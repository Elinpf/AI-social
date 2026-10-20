#!/usr/bin/env bash
# D5/D6 跑批后一键评测（只读、零 LLM、无 pytest）。给「批次落地后 5 分钟内出全套读数」用。
#
# 用法：
#   bash tools/d5/run_batch_eval.sh <run_dir> <tag> [batch_landing_sha] [--compare-with <baseline_metrics.json>]
# 例：
#   bash tools/d5/run_batch_eval.sh v2/evidence/run_d2_after_n16_seed42 a0 aeb3243 \
#        --compare-with v2/evidence/d5_metrics_v0anchor.json
#
# 产出（全部落 v2/evidence/）：
#   d5_metrics_<tag>.{json,md}           指标 + 准入
#   d5_llm_purpose_audit_<tag>.{json,md} purpose 审计 + 成本
#   samples_<tag>/samples.{json,md}      原文样本候选 + 指针链一致性
#   d5_s0a_<tag>.json                    S0a/S0b（含 landing..HEAD 代码路径零漂移）
#   d6_compare_<tag>.{json,md}           （可选）与基线指标的比较表
set -euo pipefail

RUN_DIR="${1:?用法: run_batch_eval.sh <run_dir> <tag> [landing_sha] [--compare-with <json>]}"
TAG="${2:?缺少 tag}"
LANDING="${3:-}"
shift 3 2>/dev/null || shift 2
COMPARE_WITH=""
while [ $# -gt 0 ]; do
  case "$1" in
    --compare-with) COMPARE_WITH="$2"; shift 2 ;;
    *) echo "[warn] 未知参数 $1"; shift ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
LOG="$RUN_DIR/run.jsonl"
META="$RUN_DIR/meta.json"

echo "== 0) 输入检查"
[ -f "$LOG" ] || { echo "[FAIL] 缺 run.jsonl: $LOG"; exit 2; }
if [ ! -f "$META" ]; then
  echo "[FAIL] 缺 meta.json（跑批未正常收尾）——按准入清单 B-7 拒绝出数"; exit 2
fi
wc -l "$LOG"
sha256sum "$LOG" "$META"

echo "== 1) 真跑门禁（rc 即判决）"
( cd code && python3 -m obs llm-cost --log "../$LOG" --require-provider openai_compat >/tmp/gate_$TAG.json 2>&1 ) && echo "gate rc=0 OK" || { echo "[FAIL] 门禁 rc!=0"; exit 3; }
python3 - "$TAG" <<'PY'
import json, sys
tag = sys.argv[1]
d = json.load(open(f"/tmp/gate_{tag}.json"))
g = d.get("provider_guard", {})
print("provider_guard.ok =", g.get("ok"), "| by_provider =", g.get("by_provider"))
PY

echo "== 2) S0a/S0b（代码树干净度 + landing..HEAD 零漂移）"
if [ -n "$LANDING" ]; then
  python3 tools/d5/check_clean_tree.py --batch-landing-sha "$LANDING" --out "v2/evidence/d5_s0a_$TAG.json" | tail -20
else
  python3 tools/d5/check_clean_tree.py --out "v2/evidence/d5_s0a_$TAG.json" | tail -20
fi

echo "== 3) 指标复算 + 准入"
python3 tools/d5/dialogue_metrics.py --log "$LOG" --meta "$META" \
  --out-json "v2/evidence/d5_metrics_$TAG.json" --out-md "v2/evidence/d5_metrics_$TAG.md" | tail -12

echo "== 4) purpose 审计 + 成本"
python3 tools/d5/llm_purpose_audit.py --log "$LOG" \
  --out-json "v2/evidence/d5_llm_purpose_audit_$TAG.json" \
  --out-md "v2/evidence/d5_llm_purpose_audit_$TAG.md" | tail -10

echo "== 5) 原文样本候选 + 指针链一致性"
python3 tools/d5/pick_samples.py --log "$LOG" --meta "$META" \
  --out-dir "v2/evidence/samples_$TAG" --top 3 | tail -8

if [ -n "$COMPARE_WITH" ]; then
  echo "== 6) 与基线比较"
  python3 tools/d5/compare_arms.py --roles "baseline:$COMPARE_WITH" "$TAG:v2/evidence/d5_metrics_$TAG.json" \
    --band v2/evidence/d5_noiseband_bootstrap_t300_t355.json \
    --out-json "v2/evidence/d6_compare_$TAG.json" --out-md "v2/evidence/d6_compare_$TAG.md" | tail -6
fi

echo "== 完成。请人工确认：admission.verdict / band_source / 分母 三列齐全后再引用。"
