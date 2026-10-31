#!/usr/bin/env bash
# push_and_verify.sh —— 推送 master 并**同时**验四样：rc / 服务端 ref / 目标 blob / EXPECT 比对
#
# 由来：2026-10-31 一晚两次同类事故——
#   ① 造树用了过期本地 master ⇒ 内容倒退（V-6）；
#   ② `git push … | tail; echo $?` 拿到的是 tail 的 rc ⇒ GnuTLS 报错仍打印 push_rc=0（§9.3②）。
# 手拼一次错一次，故固化成脚本。
#
# 用法：
#   scripts/push_and_verify.sh <待推的 commit sha> <相对路径1> [<相对路径2> ...]
# 例：
#   scripts/push_and_verify.sh bde6aed v2/refs/D9t-launch-checklist.md
#
# 退出码：0=四样全过；非 0=有检查未过（且会打印是哪一样）。
set -uo pipefail

if [ $# -lt 2 ]; then
  echo "用法: $0 <commit-sha> <path> [<path>...]" >&2
  exit 2
fi

SHA="$1"; shift
# 短 sha 归一化：否则 "server = <full40>" 与 "期望 <short>" 会假报警（本脚本首次干跑就踩过）
SHA=$(git rev-parse --verify "$SHA^{commit}") || { echo "FAIL: 无法解析 commit: $1" >&2; exit 2; }
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-master}"
fail=0

echo "== 0) 推送前三道自查（V-6）=="
git fetch -q "$REMOTE" "$BRANCH" || { echo "FAIL: fetch 失败"; exit 3; }
BEHIND=$(git log --oneline "$REMOTE/$BRANCH..$BRANCH" 2>/dev/null | wc -l | tr -d ' ')
echo "本地 $BRANCH 落后 $REMOTE/$BRANCH 的提交数 = $BEHIND（必须 0）"
[ "$BEHIND" = "0" ] || { echo "FAIL: 本地 $BRANCH 落后于 $REMOTE/$BRANCH，先对齐再推"; fail=1; }

if git merge-base --is-ancestor "$REMOTE/$BRANCH" "$SHA"; then
  echo "$REMOTE/$BRANCH 是新提交的祖先 ✓"
else
  echo "FAIL: $SHA 不以 $REMOTE/$BRANCH 为祖先（会倒退内容）"; fail=1
fi

echo "== 0b) V-6 第 3 道：树快照不得有非本意删除（不依赖调用方传哪些路径）=="
# 由来：d5c386e 的伤害有两层——文件被删（复核件整个消失）+ 内容回退。
# 只验传入路径只能抓第二层；第一层必须在这里抓。
DELS=$(git show --diff-filter=D --name-only --format="" "$SHA" | wc -l | tr -d ' ')
if [ "$DELS" != "0" ]; then
  echo "FAIL: 本提交删除了 $DELS 个文件（若非本意即内容倒退）："
  git show --diff-filter=D --name-only --format="" "$SHA"
  fail=1
else
  echo "删除文件数 = 0 ✓"
fi
BIG=$(git show --numstat --format="" "$SHA" | awk '$2>50' | wc -l | tr -d ' ')
if [ "$BIG" != "0" ]; then
  echo "FAIL: 有 $BIG 个文件的删除行 >50（疑似回退，逐条看）:"
  git show --numstat --format="" "$SHA" | awk '$2>50'
  fail=1
else
  echo "大删除（>50 行）文件数 = 0 ✓"
fi
echo "-- 触及路径清单（人眼过一遍）--"
git show --name-status --format="" "$SHA"

echo "== 1) 记录 EXPECT（变更后的内容本身；绝不取 $REMOTE/$BRANCH:<path>）=="
# bash3 兼容：用并行数组
EXPECTS=()
for p in "$@"; do
  e=$(git rev-parse "$SHA:$p" 2>/dev/null || echo MISSING)
  EXPECTS+=("$e")
  echo "  EXPECT[$p] = $e"
done

[ "$fail" = "0" ] || { echo "== 中止：推送前自查未过 =="; exit 4; }

echo "== 2) 推送（不串管道，先拿真 rc）=="
git push "$REMOTE" "$SHA:refs/heads/$BRANCH"
RC=$?
echo "push rc=$RC"
[ "$RC" = "0" ] || { echo "FAIL: push rc=$RC"; exit 5; }

echo "== 3) 服务端直读 =="
SERVER=$(git ls-remote "$REMOTE" "refs/heads/$BRANCH" | cut -f1)
echo "server = $SERVER"
if [ "$SERVER" = "$SHA" ]; then echo "SERVER_OK"; else echo "SERVER_MISMATCH（期望 $SHA）"; fail=1; fi

echo "== 4) 逐文件比对 blob =="
git fetch -q "$REMOTE" "$BRANCH"
i=0
for p in "$@"; do
  b=$(git rev-parse "$REMOTE/$BRANCH:$p" 2>/dev/null || echo MISSING)
  if [ "$b" = "${EXPECTS[$i]}" ]; then
    echo "  BLOB_OK   $b  $p"
  else
    echo "  BLOB_MISMATCH  远端=$b  期望=${EXPECTS[$i]}  $p"; fail=1
  fi
  i=$((i+1))
done

echo "== 结论 =="
if [ "$fail" = "0" ]; then echo "ALL_OK"; exit 0; else echo "HAS_FAILURE"; exit 1; fi
