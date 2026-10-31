#!/usr/bin/env bash
# 安装仓库 hooks（当前只有 pre-push：挡内容倒退）
# 用法：bash scripts/install_hooks.sh
set -uo pipefail
ROOT=$(git rev-parse --show-toplevel)
HOOKS="$ROOT/hooks"
DEST="$ROOT/.git/hooks"
[ -d "$HOOKS" ] || { echo "没有 $HOOKS"; exit 1; }
[ -d "$DEST" ] || { echo "没有 $DEST（不是 git 仓库根？）"; exit 1; }
for h in "$HOOKS"/*; do
  [ -f "$h" ] || continue
  name=$(basename "$h")
  cp "$h" "$DEST/$name"
  chmod +x "$DEST/$name"
  echo "installed: .git/hooks/$name"
done
echo "完成。绕过方式：git push --no-verify（须写明原因）"
