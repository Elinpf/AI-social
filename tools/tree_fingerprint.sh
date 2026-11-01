#!/usr/bin/env bash
# T346：工作树「冻结区」**内容**指纹（**HEAD 无关**）—— 判「跑中树是否被改」。
#
# 与 T340 的差别（T346 修）：
#   ① **只对文件【内容】做哈希**；`HEAD` 由调用方 `verify_tree_guard.sh` **另记、不作比较输入**
#      ⇒ 一个**无关提交**（如只动 `v2/evidence/**`）不再改动指纹、不再把门错判红。
#   ② **分段**：`world`（`config/**` + 世界层 `code/**`，**排除** `code/frontend/**`）
#      与 `front`（`code/frontend/**`）分别出指纹 ⇒ 供分级结论。
#
# 口径：`sha256sum` 每个冻结文件**【工作树内容】**（含路径名，故改名/移动亦变），排序后汇总。
#       tracked 走 `git ls-files`（索引路径集），untracked 走 `--others --exclude-standard`；
#       gitignore 的生成物不计入 ⇒ 免假红。**注意：不读 index 的内容**（只借它列文件名）。
#
# 用法：tree_fingerprint.sh [world|front]   （默认 world）
set -uo pipefail
REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "no-git"; exit 0; }
cd "$REPO" || exit 0
MODE="${1:-world}"

if [ "$MODE" = "front" ]; then
  PATHS="code/frontend"
  KEEP='grep "^code/frontend/"'
else
  PATHS="code config"
  KEEP="grep -v '^code/frontend/'"
fi

# 2026-11-01 改（repro-verifier 提，Leader 采纳）：**文件数必须与指纹同源**。
# 旧版只输出一个 sha，文件数被管道丢掉 => 「起跑贴 283」工具本身给不出，只能人另跑一条命令手贴,
# 两数来自两条命令/两个时点就容易对不上；而「FP 与文件数不同源」是最难查的一类
# （典型形态：换了 rev 得 284，被读成"文件集变了"）。
# 现在：清单先落临时文件，**指纹与文件数都从该清单数出来**，并一并输出。
# ⚠ 注意：tmp 必须在 `{ ... }` **之前**创建（组内是子 shell，赋值不外传——本次首版即踩此坑）。
tmp=$(mktemp) || { echo "no-tmp"; exit 0; }
trap 'rm -f "$tmp"' EXIT

{
  git ls-files -- $PATHS 2>/dev/null
  git ls-files --others --exclude-standard -- $PATHS 2>/dev/null
} | sort -u | eval "$KEEP" | while IFS= read -r f; do
    [ -f "$f" ] && sha256sum "$f" 2>/dev/null
  done > "$tmp"

FILES=$(wc -l < "$tmp" | tr -d ' ')
if [ "${FILES:-0}" -lt 100 ]; then
  echo "FATAL: 计入文件数 ${FILES:-0} < 100 —— 指纹无效（空目录/错路径的稳定指纹没有任何意义）"
  exit 3
fi
SHA=$(sha256sum < "$tmp" | awk '{print $1}')
# 三元组：sha 与文件数同源；rev 由调用方另记（FP 必须写 (rev, files, sha)）
printf 'files=%s\nsha256=%s\nmode=%s\n' "$FILES" "$SHA" "$MODE"
