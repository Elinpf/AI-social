#!/usr/bin/env bash
# T340：`make verify` 自检「跑中树被改」。
#   起跑记冻结区指纹+清单 → 跑真实门 `make verify-inner` → 收尾再算 → 不一致即判「结果不可信」。
# 区分：**起跑时脏**（允许，正常"提交前先 verify"）vs **跑中被改**（报错）。
# 退出码：0=全绿且树未变；非 0=门失败（其原码）；2=跑中树被改（结果不可信）。
set -uo pipefail
REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "no-git"; exit 2; }
cd "$REPO" || exit 2
FP="$REPO/tools/tree_fingerprint.sh"
LIST() { git diff --name-status HEAD -- code config 2>/dev/null; echo "UNTRACKED(code/config):"; git ls-files --others --exclude-standard -- code/config 2>/dev/null; }

STARTL="$(mktemp)"; ENDL="$(mktemp)"
trap 'rm -f "$STARTL" "$ENDL"' EXIT
LIST > "$STARTL"
F0="$(bash "$FP")"
echo "[verify-guard] 起跑指纹(冻结区 code+config) = $F0"

make verify-inner
rc=$?
F1="$(bash "$FP")"
LIST > "$ENDL"
echo "[verify-guard] 收尾指纹 = $F1"

if [ "$F0" != "$F1" ]; then
  echo "[verify-guard] ✗ 跑中树被改（$F0 → $F1）⇒ 本次门结果【不可信】，请重跑。"
  echo "[verify-guard]   变更清单（起→收 的 tracked 改动/未跟踪文件 差异）："
  diff "$STARTL" "$ENDL" | sed 's/^/     /' || true
  echo "[verify-guard]   （这是『验证窗内冻结被验对象』的机器自检：与 T304/T314 同一原理。）"
  exit 2
fi
echo "[verify-guard] OK：跑中树未变，门结果可信。"
exit "$rc"
