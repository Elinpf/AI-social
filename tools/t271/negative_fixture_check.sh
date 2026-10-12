#!/usr/bin/env bash
# T311 · must-be-red 负向夹具检查
#   对 frozen 夹具（pre-fix 分歧对）跑 T299 语义一致门：断言两文件世界语义投影【不等】。
#   相等 ⇒ 夹具损坏或门失效（不能报红）⇒ 红。
# 说明：这使「门在真实数据上能报红」成为可断言项，不依赖合成 --selftest 的 REVERSE 扰动。
set -uo pipefail
BIN="$(cd "$(dirname "$0")" && pwd)"
FX="${T271_FIXTURE_DIR:-$BIN/fixtures/resume_divergence_cut75}"
O="$FX/oneshot.jsonl"; R="$FX/resume.jsonl"

if [ ! -f "$O" ] || [ ! -f "$R" ]; then
  echo "FAIL: 夹具缺失（$O / $R）"; exit 1
fi

SO="$(python3 "$BIN/semantic_log_sha.py" "$O" | awk '{print $1}')"
SR="$(python3 "$BIN/semantic_log_sha.py" "$R" | awk '{print $1}')"
echo "夹具 oneshot sem_sha = $SO"
echo "夹具 resume  sem_sha = $SR"

# 严格：两者必须都是合法 64-hex；任一为空/非法 ⇒ 工具失败 ⇒ 红（防"空==空/空!=值"的假判）。
HEX='^[0-9a-f]{64}$'    # ERE：区间量词在 grep -E 下写 {64}，不带反斜杠
if ! printf '%s' "$SO" | grep -Eq "$HEX" || ! printf '%s' "$SR" | grep -Eq "$HEX"; then
  echo "FAIL: 语义投影为空/非法（oneshot='$SO' resume='$SR'）⇒ 计算失败，不得判 OK（假绿防护）"
  exit 1
fi

if [ "$SO" != "$SR" ]; then
  echo "OK: 夹具两文件语义投影【不等】⇒ 门在真实数据上【能报红】可断言（must-be-red 成立）"
  exit 0
else
  echo "FAIL: 夹具两文件语义投影【相等】⇒ 夹具损坏 / 门失效（无法报红）"
  exit 1
fi
