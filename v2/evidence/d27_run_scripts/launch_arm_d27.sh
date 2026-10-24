#!/usr/bin/env bash
# launch_arm_d27.sh —— D2.7 单臂起跑器（两臂共用，只做「起跑前自检 + 退出码落盘 + 调 run_batch.sh」）
#
# 为什么需要这一层：
#   主树 tools/d2/run_batch.sh **不**写 run_batch.rc / run_batch.end（那是 e1_run_scripts/launch_arm.sh 的职责，
#   但它把 --rounds 硬编成 84 且强制要求 --switch-env，D2.7 没有 env 开关，且两臂必须同为 n16r60）。
#   本脚本不改任何仓库代码，只做四件事：
#     1) 断言该树冻结区（code/{life,orchestration,config,engine}）git diff 为空 —— 起跑前自检，失败退出 9
#     2) 保证该树 code/.env.local 存在（缺失则软链到主树那份，gitignored 不脏树）
#     3) 记录起跑瞬间 HEAD=code_sha_start、launch_cmd 原文、arm 名
#     4) 调 tools/d2/run_batch.sh（内含 preflight 串行闸 + meta + obs llm-cost 门禁），
#        并在**任何退出路径**写 run_batch.rc / run_batch.end
#
# 用法：
#   setsid nohup bash <本脚本> --worktree <树的绝对路径> --out-dir <该树内的 out 目录> --arm C|B \
#     > <out>/host.log 2>&1 &
# 退出码：透传 run_batch.sh（0 成功；3=行数!=events；6=llm-cost 门禁失败；9=preflight/自检失败）
set -uo pipefail

WT=""
OUT_DIR=""
ARM=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worktree) WT="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --arm) ARM="$2"; shift 2 ;;
    -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
    *) echo "[launch_arm_d27] unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$WT" && -n "$OUT_DIR" && -n "$ARM" ]] || {
  echo "[launch_arm_d27] FAIL: 需要 --worktree --out-dir --arm" >&2; exit 2; }

_rc_dump() {
  local rc=$?
  mkdir -p "$OUT_DIR" 2>/dev/null || true
  printf '%s\n' "$rc" > "$OUT_DIR/run_batch.rc" 2>/dev/null || true
  printf 'arm=%s\nfinished_at=%s\nrc=%s\nout_dir=%s\nworktree=%s\n' \
    "$ARM" "$(date -Iseconds)" "$rc" "$OUT_DIR" "$WT" > "$OUT_DIR/run_batch.end" 2>/dev/null || true
}
trap _rc_dump EXIT

mkdir -p "$OUT_DIR" || { echo "[launch_arm_d27] FAIL: 无法创建 $OUT_DIR" >&2; exit 2; }
cd "$WT" || { echo "[launch_arm_d27] FAIL: 树不存在 $WT" >&2; exit 2; }

echo "== 1) 起跑前自检（只读） $(date -Iseconds)"
{
  echo "arm=$ARM"
  echo "worktree=$WT"
  echo "branch=$(git rev-parse --abbrev-ref HEAD)"
  echo "code_sha_start=$(git rev-parse HEAD)"
  echo "started_at=$(date -Iseconds)"
  echo "launch_cmd=bash $0 --worktree $WT --out-dir $OUT_DIR --arm $ARM"
} | tee "$OUT_DIR/code_id_start.txt"

git status --porcelain > "$OUT_DIR/git_status_start.txt"
git diff -- code/life code/orchestration code/config code/engine > "$OUT_DIR/frozen_diff_start.txt"
if [[ -s "$OUT_DIR/frozen_diff_start.txt" ]]; then
  echo "[launch_arm_d27] FAIL: 起跑前冻结区有未提交差异，拒绝起跑（见 frozen_diff_start.txt）" >&2
  exit 9
fi
echo "frozen_diff_start: 空 ✅"

echo "== 2) 凭据软链"
MAIN_TREE="/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment"
if [[ ! -e "$WT/code/.env.local" ]]; then
  ln -s "$MAIN_TREE/code/.env.local" "$WT/code/.env.local" || {
    echo "[launch_arm_d27] FAIL: 软链 .env.local 失败" >&2; exit 2; }
  echo "已软链 $WT/code/.env.local -> $MAIN_TREE/code/.env.local"
fi
ls -l code/.env.local | tee -a "$OUT_DIR/code_id_start.txt"

echo "== 3) run_batch.sh 起跑 $(date -Iseconds)"
bash tools/d2/run_batch.sh --out-dir "$OUT_DIR" --seed 42 --agents 16 --rounds 60 \
  --side-root "/tmp/d27_${ARM}_side" > "$OUT_DIR/run_batch.log" 2>&1
RC=$?
echo "== run_batch.sh rc=$RC $(date -Iseconds)"
tail -20 "$OUT_DIR/run_batch.log"
exit "$RC"
