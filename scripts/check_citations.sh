#!/usr/bin/env bash
# check_citations.sh —— 扫一件内出现的所有短 sha，验"存在性"与"口径"
#
# 由来：2026-10-31 一晚"引用纪律"类事故 5 次（旧 sha 返工 ×3、口径混用 ×2），
# 共同点不是"不知道规则"，而是"知道规则但漏了一处"。漏靠纪律追不上，只能靠扫。
#
# 判据（写死）：**件里出现的每个 sha，必须落在以下四类之一，否则算漏。**
#   1. commit/object —— git cat-file -e 命中
#   2. content(核过) —— 同行取到路径，git show REV:<path> | sha256sum 前缀一致
#   3. content(待配) —— 像内容 sha 但取不到路径，需人工配对
#   4. 已声明缺失   —— 同行写着 不存在/已废弃/作废/未入库/未落地/MISSING
set -uo pipefail
FILE="${1:-}"
[ -n "$FILE" ] || { echo "用法: $0 <file> [--strict]" >&2; exit 2; }
[ -f "$FILE" ] || { echo "找不到文件: $FILE" >&2; exit 2; }
STRICT=0; [ "${2:-}" = "--strict" ] && STRICT=1
echo "== 扫 $FILE =="
mapfile -t RAW < <(grep -nEo '\b[0-9a-f]{7,40}\b' "$FILE")
REV="${3:-origin/master}"   # 默认对 master 侧核（件多落 master）；可用第 3 参数指定
seen=""; bad=0; count=0; c_ok=0; c_pending=0
for entry in "${RAW[@]}"; do
  lineno="${entry%%:*}"; tok="${entry#*:}"
  case "$tok" in *[a-f]*) ;; *) continue ;; esac
  case "$tok" in 0000000*) continue ;; esac
  key="$lineno:$tok"
  case " $seen " in *" $key "*) continue ;; esac
  seen="$seen $key"
  line_text=$(sed -n "${lineno}p" "$FILE")
  if git cat-file -e "${tok}^{commit}" 2>/dev/null; then
    echo "  commit        L$lineno  $tok"; count=$((count+1)); continue; fi
  if git cat-file -e "$tok" 2>/dev/null; then
    echo "  object        L$lineno  $tok"; count=$((count+1)); continue; fi
  if printf '%s' "$line_text" | grep -qE '不存在|已废弃|作废|未入库|未落地|MISSING|文本切片|字符串级|内容 sha|修订史|历史版'; then
    echo "  已声明缺失    L$lineno  $tok"; count=$((count+1)); c_ok=$((c_ok+1)); continue; fi
  path=$(printf '%s' "$line_text" | grep -oE '[A-Za-z0-9_./-]+\.(md|py|json|sh|txt|yaml|yml)' | head -1)
  if [ -n "$path" ] && git cat-file -e "$REV:$path" 2>/dev/null; then
    actual=$(git show "$REV:$path" | sha256sum | cut -c1-${#tok})
    if [ "$actual" = "$tok" ]; then
      echo "  content(核过) L$lineno  $tok  <- $path"; count=$((count+1)); c_ok=$((c_ok+1))
    else
      echo "  **BAD(content 不符)** L$lineno  $tok  <- $path 实际 $actual"; count=$((count+1)); bad=$((bad+1))
    fi
    continue; fi
  if [ -n "$path" ]; then
    echo "  content(待配) L$lineno  $tok  <- 路径 $path 在 $REV 上不存在"; count=$((count+1)); c_pending=$((c_pending+1))
  else
    echo "  **BAD** L$lineno  $tok  <- 非 git 对象、无路径可配、未声明缺失"; count=$((count+1)); bad=$((bad+1))
  fi
done
echo "== 共 $count 个：可核 $c_ok，待配 $c_pending，漏 $bad =="
if [ "$bad" -gt 0 ]; then echo "结论: HAS_UNEXPLAINED"; exit 1; fi
if [ "$STRICT" -eq 1 ] && [ "$c_pending" -gt 0 ]; then echo "结论: HAS_PENDING(strict)"; exit 1; fi
echo "结论: ALL_EXPLAINED"; exit 0
