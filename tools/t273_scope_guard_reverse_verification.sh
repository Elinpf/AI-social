#!/bin/sh
# T273 反向验证脚本：亲手造 `git add -A` 裹带场景，证明「提交范围守卫」真的拦得住；
# 并证明正常提交路径不受影响。
#
# 安全：全程在临时分支 t273-scratch 上跑；用**临时 hooksPath**（不改 .git/hooks、不改 code/**）；
#       结束 trap 复原（unstage + 删临时文件 + 回原分支 + 删临时分支 + 删临时 hooks）。
# 运行：sh tools/t273_scope_guard_reverse_verification.sh
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not a git repo"; exit 2; }
cd "$ROOT" || exit 2
ORIG_BRANCH="$(git branch --show-current)"

TMPH="$(mktemp -d)"
cp tools/pre-commit-lexicon.sh "$TMPH/pre-commit"
chmod +x "$TMPH/pre-commit"
GC="git -c core.hooksPath=$TMPH"

cleanup() {
  git reset -q 2>/dev/null
  rm -f tools/_t273_mine.txt tools/_t273_foreign.txt
  git checkout -q "$ORIG_BRANCH" 2>/dev/null
  git branch -D t273-scratch -q 2>/dev/null
  rm -rf "$TMPH"
}
trap cleanup EXIT

git checkout -q -B t273-scratch
echo "== 环境：分支 t273-scratch；hooksPath=$TMPH（临时，不改 .git/hooks）=="

echo
echo "== T1 · 裹带场景（add -A 同时扫入 新鲜文件 + 3 小时前的陈旧文件）-> 期望：红/拦截 =="
printf 'mine\n' > tools/_t273_mine.txt
printf 'foreign\n' > tools/_t273_foreign.txt
touch -d '3 hours ago' tools/_t273_foreign.txt   # T342：判据改为"年龄离群"，需与最新改动差 >30min ⇒ 用 3h
git add -A
b1=$(git rev-list --count HEAD)
OUT1="$($GC commit -m 'T273 incident test' 2>&1)"; rc1=$?
a1=$(git rev-list --count HEAD)
printf '%s\n' "$OUT1"
echo ">>> T1 exit=$rc1 ; commits $b1 -> $a1 （应 0->0，即未产生提交）"
TOKEN="$(printf '%s\n' "$OUT1" | sed -n 's/.*COMMIT_SCOPE_ACK=\([0-9a-f]\{12\}\).*/\1/p' | head -1)"
echo ">>> 解析出的确认令牌：$TOKEN"
git reset -q

echo
echo "== T2 · 正常提交（仅刚改动的 1 个新鲜文件）-> 期望：绿/放行 =="
printf 'mine2\n' > tools/_t273_mine.txt
touch tools/_t273_mine.txt
git add tools/_t273_mine.txt
b2=$(git rev-list --count HEAD)
OUT2="$($GC commit -m 'T273 normal commit' 2>&1)"; rc2=$?
a2=$(git rev-list --count HEAD)
printf '%s\n' "$OUT2" | tail -3
echo ">>> T2 exit=$rc2 ; commits $b2 -> $a2 （应 +1，即正常提交成功）"

echo
echo "== T3 · 裹带场景 + 显式确认令牌 -> 期望：绿/放行（确认后放行，非永久白名单）=="
printf 'foreign2\n' > tools/_t273_foreign.txt
touch -d '3 hours ago' tools/_t273_foreign.txt   # T342：年龄离群判据
printf 'mine3\n' > tools/_t273_mine.txt
touch tools/_t273_mine.txt
# 为不触碰他人 WIP，T3 用定向暂存（同样构成「新鲜+陈旧混批」信号）
git add tools/_t273_mine.txt tools/_t273_foreign.txt
b3=$(git rev-list --count HEAD)
OUT3="$(COMMIT_SCOPE_ACK="$TOKEN" $GC commit -m 'T273 incident ack' 2>&1)"; rc3=$?
a3=$(git rev-list --count HEAD)
printf '%s\n' "$OUT3" | tail -3
echo ">>> T3 exit=$rc3 ; commits $b3 -> $a3 （应 +1，即确认后放行）"

echo
echo "== T4 · 纯陈旧文件、无新鲜文件（如整段重构一次性提交）-> 期望：绿（不误伤）=="
git reset -q
printf 'slow\n' > tools/_t273_foreign.txt
touch -d '40 min ago' tools/_t273_foreign.txt
git add tools/_t273_foreign.txt
b4=$(git rev-list --count HEAD)
OUT4="$($GC commit -m 'T273 slow work commit' 2>&1)"; rc4=$?
a4=$(git rev-list --count HEAD)
printf '%s\n' "$OUT4" | tail -2
echo ">>> T4 exit=$rc4 ; commits $b4 -> $a4 （应 +1，单一陈旧文件不误伤）"

r1=$([ "$rc1" = 1 ] && echo "PASS-拦住了" || echo "FAIL-未拦住")
r2=$([ "$rc2" = 0 ] && echo "PASS-放行" || echo "FAIL-误拦")
r3=$([ "$rc3" = 0 ] && echo "PASS-放行" || echo "FAIL-误拦")
r4=$([ "$rc4" = 0 ] && echo "PASS-不误伤" || echo "FAIL-误伤")
echo
echo "== 结果汇总 =="
echo "T1 裹带场景   exit=$rc1 -> $r1"
echo "T2 正常提交   exit=$rc2 -> $r2"
echo "T3 确认放行   exit=$rc3 -> $r3"
echo "T4 纯陈旧提交 exit=$rc4 -> $r4"
