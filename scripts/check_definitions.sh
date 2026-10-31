#!/usr/bin/env bash
# check_definitions.sh —— 扫「率/占比」是否写了 §11 四行、外推是否写了 §12「假定不变」
#
# 由来：§11（四行定义）与 §12（假定不变）此前只有条文、没有可执行物；
# repro-verifier 2026-11-01 指出「能被扫出来的缺行，才是规则；扫不出来的只是提醒」。
#
# ⚠ 首版精确率低，**只作提示，不作门禁**（2026-11-01 实测）：
#   起跑清单件触发 38 处、判定件触发 9 处，多数是"表头含『倍率』""叙述性提及率" ⇒ 假阳性为主。
#   ⇒ --strict 暂不用于任何闸门；须按真实夹具调精确率（与 check_citations 同一路径：先有失败案例再收严）。
#
# 用法：scripts/check_definitions.sh <file> [--strict] [--selftest]
#   默认：只报告（rc=0）；--strict：有缺行即 rc=1
set -uo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp); RC=0
  cat > "$T" <<'EOT'
这里有个占比 38.40%，但后面没写四行
相邻对随 agents 外推，倍率 ≈4，但没写前提
EOT
  out=$(bash "$0" "$T" 2>&1); n11=$(printf '%s' "$out" | grep -c 'MISS-§11' || true)
  n12=$(printf '%s' "$out" | grep -c 'MISS-§12' || true)
  printf '%s\n' "$out" | grep -E 'MISS-§1[12]' || true
  if [ "${n11:-0}" -ge 1 ] && [ "${n12:-0}" -ge 1 ]; then echo "selftest PASS（§11 缺 $n11、§12 缺 $n12）"; RC=0
  else echo "selftest FAIL（§11=$n11 §12=$n12，各期望≥1）"; RC=1; fi
  rm -f "$T"; exit $RC
fi

FILE="${1:-}"
[ -n "$FILE" ] || { echo "用法: $0 <file> [--strict] [--selftest]" >&2; exit 2; }
[ -f "$FILE" ] || { echo "找不到文件: $FILE" >&2; exit 2; }
STRICT=0; [ "${2:-}" = "--strict" ] && STRICT=1
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "FATAL: 不在 git 仓库内" >&2; exit 4; }
echo "== 执行上下文 repo=$ROOT file=$FILE =="

miss=0
# §11：出现"率/占比/每 X 平均" ⇒ 其后 6 行内须同时含 分子/分母/计算式/纳入
while IFS=: read -r ln _; do
  [ -z "${ln:-}" ] && continue
  win=$(sed -n "${ln},$((ln+6))p" "$FILE")
  ok=1
  for w in 分子 分母 计算式 纳入; do printf '%s' "$win" | grep -q "$w" || ok=0; done
  if [ "$ok" -eq 0 ]; then
    echo "  MISS-§11  L$ln  「率/占比」后 6 行内缺四行定义：$(printf '%s' "$win" | head -1 | cut -c1-40)"
    miss=$((miss+1))
  fi
done < <(grep -nE '占比|[0-9.]+ ?%|平均' "$FILE" | grep -vE '^\s*[0-9]+:\s*(#|>)' | head -50)

# §12：出现"倍率/等比/外推/≈N 倍" ⇒ 其后 3 行内须含"假定不变"或"不变"
while IFS=: read -r ln _; do
  [ -z "${ln:-}" ] && continue
  win=$(sed -n "${ln},$((ln+3))p" "$FILE")
  if ! printf '%s' "$win" | grep -qE '假定不变|不变'; then
    echo "  MISS-§12  L$ln  外推/倍率后 3 行内缺「假定不变」：$(printf '%s' "$win" | head -1 | cut -c1-40)"
    miss=$((miss+1))
  fi
done < <(grep -nE '倍率|等比|外推|≈ ?[0-9.]+ ?倍' "$FILE" | grep -vE '^\s*[0-9]+:\s*(#|>)' | head -50)

echo "== 缺行合计 $miss =="
if [ "$miss" -gt 0 ] && [ "$STRICT" -eq 1 ]; then echo "结论: HAS_MISSING(strict)"; exit 1; fi
[ "$miss" -gt 0 ] && { echo "结论: REPORT_ONLY（非 strict 不阻塞）"; exit 0; }
echo "结论: ALL_DECLARED"; exit 0
