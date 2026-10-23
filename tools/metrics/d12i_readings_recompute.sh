#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# D12-I 收批后「读数复算 + 真实截图」一键落盘（**纯只读、零跑批、零 LLM**）。
#
# 纪律：
#   * 只读 D12-I 已收批日志，不起任何跑批；
#   * 不改 code/life|orchestration|config|engine（本脚本只写 v2/evidence/ 下的新目录）；
#   * 不 commit / 不 push；
#   * 每个落盘件都在 SHA256SUMS 里逐个实测。
#
# 用法（必须在**主 checkout**仓库根执行，tools/metrics/ 与 tools/d5/ 在这棵树）：
#     bash tools/metrics/d12i_readings_recompute.sh
#
# 产出目录：v2/evidence/d12i_readings_20261024/
#   identity_attest.json       批次身份（sha256 / 行数 / meta 对账 / HEAD）
#   form_metrics_full.json     全批形态读数（六元组：值/分母/判据/来源/sha256/命令）
#   shape_gate_points.json     F1/F2/F3 三时点核（20/30/60 轮）
#   shape_gate_full.json       收尾形态闸（全 run）
#   selector_stats_full.json   argmin_unique 与 not_all_equal 并列
#   llm_cost.txt / llm_cost.rc obs llm-cost 原始单行 JSON + 退出码
#   shots/                     真实截图（PNG + threads + render_report + render.log）
#   SHA256SUMS                 以上所有文件的 sha256（逐件实测，最后生成）
set -euo pipefail

cd "$(dirname "$0")/../.."          # → 主 checkout 仓库根
REPO=$(pwd)
OUT=v2/evidence/d12i_readings_20261024
WT=.worktrees/d12i-aligned
RUNDIR=$WT/v2/evidence/run_d12i_aligned_n16r60_seed42
LOG=$RUNDIR/run.jsonl
SHOTS=$OUT/shots
mkdir -p "$OUT" "$SHOTS"

echo "== repo=$REPO"
echo "== out=$OUT"
echo "== log=$LOG"

# ---------------------------------------------------------------- 0) 身份复核
python3 - "$OUT/identity_attest.json" "$LOG" "$RUNDIR/meta.json" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path

out_path, log_path, meta_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()

meta = json.loads(meta_path.read_text(encoding="utf-8"))
log = Path(log_path)
n_lines = 0
with open(log, "rb") as f:
    for _ in f:
        n_lines += 1
attest = {
    "schema_version": "d12i-identity-attest/1.0",
    "run_dir": str(log.parent),
    "log": str(log),
    "log_sha256_measured": sha256_file(log),
    "log_sha256_expected": "72c0ca97fe6e38632f67e3b2810c65126c0d15d296d068b521dfbb45c8f5d0c4",
    "log_bytes_measured": log.stat().st_size,
    "log_lines_measured": n_lines,
    "log_lines_expected": 117724,
    "meta_run_sha256": meta.get("run_sha256"),
    "meta_derived_from_log_sha256": meta.get("derived_from_log_sha256"),
    "meta_events": meta.get("events"),
    "meta_wc_l": meta.get("wc_l"),
    "meta_run_bytes": meta.get("run_bytes"),
    "meta_code_sha": meta.get("code_sha"),
    "meta_started_at": meta.get("started_at"),
    "meta_finished_at": meta.get("finished_at"),
    "meta_duration_sec": meta.get("duration_sec"),
    "meta_provider": meta.get("provider"),
    "meta_model_requested": meta.get("model_requested"),
    "meta_llm_calls": meta.get("llm_calls"),
    "meta_llm_cached": meta.get("llm_cached"),
    "meta_degraded_calls": meta.get("degraded_calls"),
    "meta_fallback_detected": meta.get("fallback_detected"),
    "meta_git_dirty_code_files": meta.get("git_dirty_code_files"),
    "meta_git_dirty_files": meta.get("git_dirty_files"),
    "run_batch_rc": (log.parent / "run_batch.rc").read_text(encoding="utf-8").strip(),
    "worktree_branch": git("-C", str(log.parents[3]), "rev-parse", "--abbrev-ref", "HEAD"),
    "worktree_head": git("-C", str(log.parents[3]), "rev-parse", "HEAD"),
    "main_checkout_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "main_checkout_head": git("rev-parse", "HEAD"),
    "note_code_sha_semantics": "meta.code_sha = 写 meta 那一刻的 worktree HEAD；收批后该分支又前进（含只读工具 commit），故与当前 worktree HEAD 不同，两值同报。",
}
attest["checks"] = {
    "log_sha256_matches_expected": attest["log_sha256_measured"] == attest["log_sha256_expected"],
    "log_lines_matches_expected": n_lines == attest["log_lines_expected"] == meta.get("wc_l"),
    "log_bytes_matches_meta": attest["log_bytes_measured"] == meta.get("run_bytes"),
    "run_sha256_three_way": len({attest["log_sha256_measured"], meta.get("run_sha256"),
                                 meta.get("derived_from_log_sha256")}) == 1,
    "run_batch_rc_zero": attest["run_batch_rc"] == "0",
}
attest["all_checks_pass"] = all(attest["checks"].values())
out_path.write_text(json.dumps(attest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
print(json.dumps(attest["checks"], ensure_ascii=False))
if not attest["all_checks_pass"]:
    sys.exit(3)
PY

# ---------------------------------------------------------------- 1) 形态读数（全批）
echo "[1/5] form_metrics 全批"
python3 tools/metrics/form_metrics.py \
  --log "$LOG" \
  --code-dir "$WT/code" \
  --out "$OUT/form_metrics_full.json" \
  --batch-id D12-I --no-timestamp

# ---------------------------------------------------------------- 2) 形态闸（三时点 + 收尾）
echo "[2/5] shape_gate 三点核 20/30/60"
python3 tools/d12h/shape_gate.py \
  --log "$LOG" --points 20,30,60 \
  --code-dir "$WT/code" \
  --out-json "$OUT/shape_gate_points.json" || true   # 有越界时 rc=1，读数仍已落盘

echo "[2/5] shape_gate 全 run"
python3 tools/d12h/shape_gate.py \
  --log "$LOG" \
  --code-dir "$WT/code" \
  --out-json "$OUT/shape_gate_full.json" || true

# ---------------------------------------------------------------- 3) 选优机制统计
echo "[3/5] selector_stats 全批"
python3 "$WT/tools/d12i/selector_stats.py" \
  --log "$LOG" --key d12i \
  --out-json "$OUT/selector_stats_full.json"

# ---------------------------------------------------------------- 4) LLM 成本验真
echo "[4/5] obs llm-cost"
OBS_OUT="$REPO/$OUT"
set +e
( cd "$REPO/code" && python3 -m obs llm-cost --log "$REPO/$LOG" --require-provider openai_compat \
    > "$OBS_OUT/llm_cost.txt" 2>"$OBS_OUT/llm_cost.stderr.txt" )
RC=$?
set -e
printf '%s\n' "$RC" > "$OUT/llm_cost.rc"
echo "   obs llm-cost rc=$RC"

# ---------------------------------------------------------------- 4b) 重复度三口径并列
echo "[4b] dup_calibers（raw_exact / norm_exact / norm8_shingle 并列）"
python3 tools/metrics/d12i_dup_calibers.py \
  --log "$LOG" --out "$OUT/dup_calibers.json"

# ---------------------------------------------------------------- 5) 真实截图
echo "[5/5] render_shots（chat/rhythm/spread/chat_thread 四视图）"
python3 tools/metrics/render_shots_extra.py \
  --run-dir "$RUNDIR" \
  --batch-id D12-I \
  --outdir "$SHOTS" \
  --views chat,rhythm,spread,chat_thread \
  --timeout 180 2>&1 | tee "$SHOTS/render.log"
echo "   render rc=${PIPESTATUS[0]}"

# ---------------------------------------------------------------- 6) 逐件 sha256
echo "[6/5] SHA256SUMS"
( cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum ) > "$OUT/SHA256SUMS"
cat "$OUT/SHA256SUMS"

echo "== done"
