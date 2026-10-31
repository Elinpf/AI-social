#!/usr/bin/env bash
# check_citations.sh —— 扫一件内每个 sha，验"存在性 / 是否当前版 / 口径"
#
# 由来：一晚"引用纪律"事故 5 次（旧 sha 返工×3、口径混用×2）——共同点是"知道规则却漏一处"。
# 审计（repro-verifier, 4d17cc71）指出本脚本第一版两个漏洞，均已修：
#   ① 整行有一个白名单词 ⇒ 该行所有 sha 免检    → 改为**只作用于 token 前后 20 字窗口**
#   ② object 判 OK 但可能是历史版 blob          → 区分 object(当前版) / object(历史版)，后者须显式标注
#
# 六分类：
#   commit            git cat-file -e <tok>^{commit}
#   object(当前版)    blob/tree 且 blobs 出现在 $REV 的树里
#   object(历史版)    blob/tree 但不在 $REV 树里 ⇒ 须标注（历史/旧版/已废弃…）
#   content(核过)     同行有路径，git show $REV:<path> | sha256sum 前缀一致
#   content(待配)     看着像内容 sha 但取不到路径（--strict 下算漏）
#   已声明            紧邻 20 字窗口内有 不存在/已废弃/作废/未入库/未落地/MISSING/文本切片/字符串级/内容 sha/历史版/旧版
#
# 用法：scripts/check_citations.sh <file> [--strict] [--selftest] [<rev>]
set -uo pipefail

# ---------- 自测：检查工具必须用"已知会失败"的输入验一次 ----------
if [ "${1:-}" = "--selftest" ]; then
  T=$(mktemp); RC=0
  cat > "$T" <<'EOF'
L3 deadbeef12345678 修订史（死 sha，应被抓）
L4 cafebabe1234 与 badbadbad999 历史版（前者坏，应被抓）
L5 feedface9999（无标注，应被抓）
EOF
  echo "== selftest ①：无标注死 sha 必须被抓（期望≥2）=="
  bash "$0" "$T" > /tmp/st1.out 2>&1; bad=$(grep -c '\*\*BAD' /tmp/st1.out || true)
  grep '\*\*BAD' /tmp/st1.out || true
  echo "== selftest ②：--strict 下'已声明'的也必须列入待审（期望≥1）=="
  bash "$0" "$T" --strict > /tmp/st2.out 2>&1; pend=$(grep -c '需人工确认' /tmp/st2.out || true)
  grep '需人工确认' /tmp/st2.out || true
  if [ "${bad:-0}" -ge 2 ] && [ "${pend:-0}" -ge 1 ]; then
    echo "selftest PASS（无标注抓到 $bad 个；strict 待审 $pend 个）"; RC=0
  else
    echo "selftest FAIL（无标注 $bad <2 或 strict 待审 $pend <1）"; RC=1
  fi
  rm -f "$T"; exit $RC
fi

FILE="${1:-}"
[ -n "$FILE" ] || { echo "用法: $0 <file> [--strict] [--selftest] [<rev>]" >&2; exit 2; }
[ -f "$FILE" ] || { echo "找不到文件: $FILE" >&2; exit 2; }
STRICT=0; shift
REV="origin/master"
for a in "$@"; do
  case "$a" in --strict) STRICT=1 ;; *) REV="$a" ;; esac
done

ANN='不存在|已废弃|作废|未入库|未落地|MISSING|文本切片|字符串级|内容 sha|历史版|旧版|非当前版'
echo "== 扫 $FILE（rev=$REV）=="
mapfile -t RAW < <(grep -nEo '\b[0-9a-f]{7,40}\b' "$FILE")
TREE_BLOBS=$(git ls-tree -r "$REV" 2>/dev/null | awk '{print $3}')

seen=""; bad=0; count=0; c_ok=0; c_pend=0
for entry in "${RAW[@]}"; do
  lineno="${entry%%:*}"; tok="${entry#*:}"
  case "$tok" in *[a-f]*) ;; *) continue ;; esac
  case "$tok" in 0000000*) continue ;; esac
  key="$lineno:$tok"
  case " $seen " in *" $key "*) continue ;; esac
  seen="$seen $key"
  line_text=$(sed -n "${lineno}p" "$FILE")
  # 紧邻窗口（不是整行）
  ctx=$(printf '%s' "$line_text" | grep -oE ".{0,20}${tok}.{0,20}" | head -1)
  [ -n "$ctx" ] || ctx="$line_text"
  declared=0
  printf '%s' "$ctx" | grep -qE "$ANN" && declared=1

  if git cat-file -e "${tok}^{commit}" 2>/dev/null; then
    echo "  commit         L$lineno  $tok"; count=$((count+1)); c_ok=$((c_ok+1)); continue
  fi
  if git cat-file -e "$tok" 2>/dev/null; then
    full=$(git rev-parse "$tok")
    if printf '%s\n' "$TREE_BLOBS" | grep -qx "$full"; then
      echo "  object(当前版) L$lineno  $tok"; count=$((count+1)); c_ok=$((c_ok+1))
    elif [ "$declared" -eq 1 ]; then
      echo "  object(历史版·已声明) L$lineno  $tok"; count=$((count+1)); c_ok=$((c_ok+1))
    else
      echo "  **BAD(object 历史版未声明)** L$lineno  $tok  ← 不在 $REV 树里，读者会以为是当前版"
      count=$((count+1)); bad=$((bad+1))
    fi
    continue
  fi

  path=$(printf '%s' "$line_text" | grep -oE '[A-Za-z0-9_./-]+\.(md|py|json|sh|txt|yaml|yml)' | head -1)
  if [ -n "$path" ] && git cat-file -e "$REV:$path" 2>/dev/null; then
    actual=$(git show "$REV:$path" | sha256sum | cut -c1-${#tok})
    if [ "$actual" = "$tok" ]; then
      echo "  content(核过)  L$lineno  $tok  <- $path"; count=$((count+1)); c_ok=$((c_ok+1))
    else
      echo "  **BAD(content 不符)** L$lineno  $tok  <- $path 实际 $actual"; count=$((count+1)); bad=$((bad+1))
    fi
    continue
  fi

  if [ "$declared" -eq 1 ]; then
    echo "  已声明缺失     L$lineno  $tok"; count=$((count+1))
    if [ "$STRICT" -eq 1 ]; then echo "    ^ --strict: 需人工确认不算漏"; c_pend=$((c_pend+1)); else c_ok=$((c_ok+1)); fi
    continue
  fi
  if [ -n "$path" ]; then
    echo "  content(待配)  L$lineno  $tok  <- 路径 $path 在 $REV 上不存在"; count=$((count+1)); c_pend=$((c_pend+1))
  else
    echo "  **BAD** L$lineno  $tok  ← 非对象、无路径、窗口内也未声明"; count=$((count+1)); bad=$((bad+1))
  fi
done

echo "== 共 $count 个：可核 $c_ok，待审 $c_pend，漏 $bad =="
[ "$bad" -gt 0 ] && { echo "结论: HAS_UNEXPLAINED"; exit 1; }
[ "$STRICT" -eq 1 ] && [ "$c_pend" -gt 0 ] && { echo "结论: HAS_PENDING(strict)"; exit 1; }
echo "结论: ALL_EXPLAINED"; exit 0
