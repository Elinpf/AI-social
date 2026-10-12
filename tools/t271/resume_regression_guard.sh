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
#   sha 固定（T271_REPRO_SHA）· 每次先清自己名下副本目录（防 repro 复用陈旧副本、无视 sha）·
#   输出根/副本用自己名下（T271_REPRO_ROOT/COPY，默认 repro_guard / t271-repro-guard），
#   避免与他人的并发 repro 撞同一目录（默认会落 release 的 /root/t271/runs/repro，互 rm -rf ⇒ 假红）。
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
# 隔离：用【自己名下】的输出根/副本目录，避免与 release 的并发 repro 撞同一目录
# （默认落 release 的 /root/t271/runs/repro 会互相 rm -rf，制造"假红"）。T271_REPRO_ROOT/COPY 为 T313 新增。
ROOT="${T271_REPRO_ROOT:-/root/t271/runs/repro_guard}"
COPY="${T271_REPRO_COPY:-/tmp/t271-repro-guard}"
export T271_REPRO_ROOT="$ROOT" T271_REPRO_COPY="$COPY"

echo "[guard] repo=$REPO"
echo "[guard] sha =$SHA ($(git -C "$REPO" rev-parse --short "$SHA"))"
echo "[guard] cuts=[$CUTS]  timeout/cut=${TMO}s"
echo "[guard] 自有输出根 ROOT=$ROOT  副本 COPY=$COPY（隔离并发）"
echo "[guard] 装置前提：分进程 / 先 warm / 固定 prefix 非墙钟 / sha 固定 / 清陈旧副本"

PASS=1
for C in $CUTS; do
  echo "=== cut=$C ==="
  rm -rf "$COPY"    # 关键：repro_resume_cut.sh 的 CO 按存在性判断 -> 不清会复用陈旧副本、无视 SHA
  OUT="$(T271_REPRO_SHA="$SHA" timeout "$TMO" bash "$BIN/repro_resume_cut.sh" "$C" 2>&1)"; RC=$?
  echo "$OUT" | sed -n '1,20p'
  # 严格解析：必须拿到【三个 64-hex 非空且恒等】的世界语义投影，否则视为"探测失败"→红。
  # （防假绿：repro 内部 s() 在工具失败时可能返回空，两空串相等会打印 "==oneshot? yes"。）
  ON="$(printf '%s\n' "$OUT" | sed -n 's/^oneshot sem_sha = \([0-9a-f]\{64\}\)$/\1/p' | head -1)"
  R1="$(printf '%s\n' "$OUT" | sed -n 's/^resume1 sem_sha = \([0-9a-f]\{64\}\)$/\1/p' | head -1)"
  R2="$(printf '%s\n' "$OUT" | sed -n 's/^resume2 sem_sha = \([0-9a-f]\{64\}\)$/\1/p' | head -1)"
  SHN="$(printf '%s\n' "$OUT" | grep -o 'state_hash 不等数=[0-9]*' | head -1)"
  if [ "$RC" -eq 0 ] && [ -n "$ON" ] && [ "$ON" = "$R1" ] && [ "$ON" = "$R2" ] \
     && [ "$SHN" = "state_hash 不等数=0" ]; then
    echo "  [cut=$C] OK（oneshot==resume1==resume2=$ON ; $SHN）"
  else
    echo "  [cut=$C] FAIL（rc=$RC ; oneshot='$ON' r1='$R1' r2='$R2' ; ${SHN:-<无 state_hash 行>}）"
    echo "           —— 含『探测失败/无输出/超时』情形：一律判红（假绿防护）"
    PASS=0
  fi
done
rm -rf "$COPY"

if [ "$PASS" = 1 ]; then
  echo "############ RESUME-REGRESSION GUARD: PASS ############"
  exit 0
else
  echo "############ RESUME-REGRESSION GUARD: FAIL（续跑一致性回归！）############"
  exit 1
fi
