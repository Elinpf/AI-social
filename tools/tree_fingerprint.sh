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

{
  git ls-files -- $PATHS 2>/dev/null
  git ls-files --others --exclude-standard -- $PATHS 2>/dev/null
} | sort -u | eval "$KEEP" | while IFS= read -r f; do
    [ -f "$f" ] && sha256sum "$f" 2>/dev/null
  done | sha256sum | awk '{print $1}'
