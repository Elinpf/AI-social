#!/usr/bin/env bash
# T311 · resume 回归守护
#   在【current HEAD】（或 T271_REPRO_SHA 指定的 sha）上，对若干 cut 跑 repro_resume_cut.sh，
#   断言【resume 世界语义 == oneshot】且 state_hash 不等数=0；任一 cut 分歧即红。
#
# 与 T311 的 frozen 负向夹具方向相反：
#   · 本守护 = current HEAD 上【都必须绿】（防"续跑一致性再回归"）；
#   · must-be-red 夹具 = pre-fix【必须红】（证明门能报红）。二者别混。
#
# 装置前提（务必随结论一起报告，否则复算不出来）：
#   分进程（每 cut 独立 bash；repro 内 warm/oneshot/2×resume 各自子进程）·
#   脚本内先 warm（冷热缓存对等）· 固定 prefix 截断（非墙钟 kill）·
#   sha 固定（T271_REPRO_SHA）· 每次先清 /tmp/t271-repro（防 repro 复用陈旧副本、无视 sha）。
#   注：git archive 副本不含"未跟踪 config"（如 code/config/time.json 若非跟踪则副本里没有）。
#
# 用法：bash tools/t271/resume_regression_guard.sh
#   环境：T271_REPRO_SHA（默认 current HEAD）· T271_GUARD_CUTS（默认 "75 89"）·
#         T271_GUARD_TIMEOUT（每 cut 秒数，默认 1800）
# 成本：每 cut ≈ 4 次 150r run（warm+oneshot+2×resume）⇒ 较慢；**与 `make verify` 一人一次**。
set -uo pipefail
BIN="$(cd "$(dirname "$0")" && pwd)"
REPO="${T271_REPO:-/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment}"
SHA="${T271_REPRO_SHA:-$(git -C "$REPO" rev-parse HEAD)}"
CUTS="${T271_GUARD_CUTS:-75 89}"
TMO="${T271_GUARD_TIMEOUT:-1800}"

echo "[guard] repo=$REPO"
echo "[guard] sha =$SHA ($(git -C "$REPO" rev-parse --short "$SHA"))"
echo "[guard] cuts=[$CUTS]  timeout/cut=${TMO}s"
echo "[guard] 装置前提：分进程 / 先 warm / 固定 prefix 非墙钟 / sha 固定 / 清陈旧副本"

PASS=1
for C in $CUTS; do
  echo "=== cut=$C ==="
  rm -rf /tmp/t271-repro    # 关键：repro_resume_cut.sh 的 CO 按存在性判断 -> 不清会复用陈旧副本、无视 SHA
  OUT="$(T271_REPRO_SHA="$SHA" timeout "$TMO" bash "$BIN/repro_resume_cut.sh" "$C" 2>&1)"
  echo "$OUT" | sed -n '1,20p'
  DEC="$(printf '%s\n' "$OUT" | grep -o '判决：.*' || true)"
  SHN="$(printf '%s\n' "$OUT" | grep -o 'state_hash 不等数=[0-9]*' || true)"
  if printf '%s' "$DEC" | grep -q '==oneshot? yes' && [ "$SHN" = "state_hash 不等数=0" ]; then
    echo "  [cut=$C] OK（resume==oneshot 且 $SHN）"
  else
    echo "  [cut=$C] FAIL：$DEC ; $SHN"
    PASS=0
  fi
done
rm -rf /tmp/t271-repro

if [ "$PASS" = 1 ]; then
  echo "############ RESUME-REGRESSION GUARD: PASS ############"
  exit 0
else
  echo "############ RESUME-REGRESSION GUARD: FAIL（续跑一致性回归！）############"
  exit 1
fi
