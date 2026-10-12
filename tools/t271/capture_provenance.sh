#!/usr/bin/env bash
# T271 副本可溯性留档 —— 源 sha + 副本 config 全文哈希 + 副本↔主树 config diff。
# 用法: capture_provenance.sh <copy_dir> <to_dir>
set -euo pipefail
COPY="${1:?用法: capture_provenance.sh <copy_dir> <to_dir>}"
TO="${2:?}"
REPO="${T271_REPO:-/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment}"
mkdir -p "$TO"
CFG="$COPY/code/config"
{
  echo "source_sha=$(git -C "$REPO" rev-parse HEAD)"
  echo "source_sha_short=$(git -C "$REPO" rev-parse --short HEAD)"
  echo "copy=$COPY"
  echo "captured_at=$(date '+%F %T')"
  echo "source_git_dirty_count=$(git -C "$REPO" status --porcelain 2>/dev/null | wc -l)"
  echo "--- 冻结区脏文件（code/{engine,life,freeze,config,obs,contracts,orchestration}）---"
  git -C "$REPO" status --porcelain -- code/engine code/life code/freeze code/config code/obs code/contracts code/orchestration 2>/dev/null | sed 's/^/  /'
  echo "--- sha256(copy/code/config/*.json) ---"
  ( cd "$CFG" && sha256sum *.json 2>/dev/null | sort )
} | tee "$TO/provenance.txt"

# 副本与主树的差异（消融批次此处应【只有那一个开关文件】）
: > "$TO/switch.diff"
for f in "$CFG"/*.json; do
  b="$(basename "$f")"
  if ! diff -q "$REPO/code/config/$b" "$f" >/dev/null 2>&1; then
    echo "### $b" >> "$TO/switch.diff"
    diff -u "$REPO/code/config/$b" "$f" >> "$TO/switch.diff" 2>&1 || true
  fi
done
echo "[prov] switch.diff 行数=$(wc -l < "$TO/switch.diff")  (0=与非主树完全一致)"
echo "[prov] 留档: $TO/provenance.txt $TO/switch.diff"
