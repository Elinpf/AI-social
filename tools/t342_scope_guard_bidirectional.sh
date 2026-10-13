#!/usr/bin/env bash
# T342 双向反向验证：提交范围守卫的「年龄离群」新判据。
#   ① 真混批（新鲜 + 3h 旧）⇒ 必须【拦】(rc1)
#   ② 自己的慢工（新鲜 + 20min 旧）⇒ 必须【不拦】(rc0)
#   ③ 单文件 ⇒ 不拦(rc0)   ④ 纯陈旧(仅 40min，无新鲜) ⇒ 不拦(rc0)   ⑤ 真混批 + ACK ⇒ 放行(rc0)
# 用【隔离索引 GIT_INDEX_FILE】避免影响真实暂存集；不改任何代码。
set -uo pipefail
REPO="$(git rev-parse --show-toplevel)"; cd "$REPO" || exit 2
IDX="$(mktemp)"; export GIT_INDEX_FILE="$IDX"
git read-tree HEAD
CHK="python3 tools/enforce_commit_scope.py"
mk(){ printf 'x\n' > "$1"; }
cleanup(){ rm -f _t342_a.txt _t342_b.txt; rm -f "$IDX"; }
trap cleanup EXIT
reset_idx(){ git reset -q; }

echo "== A 真混批（fresh + 3h 旧）-> 期望 拦(1) =="
mk _t342_a.txt; mk _t342_b.txt
touch _t342_a.txt; touch -d '3 hours ago' _t342_b.txt
git add _t342_a.txt _t342_b.txt
OUT_A="$($CHK 2>&1)"; rcA=$?
printf '%s\n' "$OUT_A" | tail -6
echo ">>> A rc=$rcA"
TOK="$(printf '%s\n' "$OUT_A" | sed -n 's/.*COMMIT_SCOPE_ACK=\([0-9a-f]\{12\}\).*/\1/p' | head -1)"
echo ">>> token=$TOK"
reset_idx

echo "== B 自己的慢工（fresh + 20min 旧）-> 期望 不拦(0) =="
mk _t342_a.txt; mk _t342_b.txt
touch _t342_a.txt; touch -d '20 min ago' _t342_b.txt
git add _t342_a.txt _t342_b.txt
$CHK; rcB=$?
echo ">>> B rc=$rcB"
reset_idx

echo "== C 单文件 -> 期望 不拦(0) =="
mk _t342_a.txt; touch _t342_a.txt
git add _t342_a.txt
$CHK; rcC=$?
echo ">>> C rc=$rcC"
reset_idx

echo "== D 纯陈旧（仅 40min，无新鲜）-> 期望 不拦(0) =="
mk _t342_b.txt; touch -d '40 min ago' _t342_b.txt
git add _t342_b.txt
$CHK; rcD=$?
echo ">>> D rc=$rcD"
reset_idx

echo "== E 真混批 + ACK -> 期望 放行(0) =="
mk _t342_a.txt; mk _t342_b.txt
touch _t342_a.txt; touch -d '3 hours ago' _t342_b.txt
git add _t342_a.txt _t342_b.txt
COMMIT_SCOPE_ACK="$TOK" $CHK; rcE=$?
echo ">>> E rc=$rcE"
reset_idx

echo
rA=$([ "$rcA" = 1 ] && echo "PASS-拦住了" || echo "FAIL")
rB=$([ "$rcB" = 0 ] && echo "PASS-未误拦(慢工)" || echo "FAIL-误拦")
rC=$([ "$rcC" = 0 ] && echo "PASS-未拦" || echo "FAIL")
rD=$([ "$rcD" = 0 ] && echo "PASS-未拦" || echo "FAIL")
rE=$([ "$rcE" = 0 ] && echo "PASS-ACK放行" || echo "FAIL")
echo "A 真混批    → $rA"
echo "B 慢工      → $rB"
echo "C 单文件    → $rC"
echo "D 纯陈旧    → $rD"
echo "E ACK       → $rE"
