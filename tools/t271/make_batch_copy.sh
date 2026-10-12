#!/usr/bin/env bash
# T271 一批一「只读副本」—— 把 <sha> 的代码树解到 /tmp，跑批在副本里进行。
# 不做任何 git 操作；副本里跑不往主树写 pyc/缓存/中间产物。
#
# 用法: make_batch_copy.sh <batch> [sha]      (sha 省略=主树当前 HEAD)
set -euo pipefail
BIN="$(cd "$(dirname "$0")" && pwd)"
source "$BIN/safe_rmrf.sh"   # T313 rm -rf 守卫
REPO="${T271_REPO:-/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment}"
ROOT="${T271_COPY_ROOT:-/tmp}"
BATCH="${1:?用法: make_batch_copy.sh <batch> [sha]}"
SHA="${2:-$(git -C "$REPO" rev-parse HEAD)}"
DEST="$ROOT/t271-$BATCH"
safe_rmrf "$DEST"; mkdir -p "$DEST"
git -C "$REPO" archive "$SHA" | tar -x -C "$DEST"
echo "[copy] dest=$DEST"
echo "[copy] source_sha=$SHA ($(git -C "$REPO" rev-parse --short "$SHA"))"
echo "[copy] 开关请以【文件】形式改在 $DEST/code/config 内；不要动 .git"
