#!/usr/bin/env bash
# T346 三向反向验证（+ 控制组）：证明新守卫「世界层红 / 仅前端告警不阻断 / 仅证据提交绿」。
#
# ⚠️ 在**独立克隆**里运行（不改实时树、不跑真 make verify）；内部真门用**假门**（VERIFY_INNER_CMD）——
#    只需它在跑、期间可改树即可，签名/语义无关。
# 运行：bash tools/t346_verify_guard_bidirectional.sh
set -uo pipefail
REPO="$(git rev-parse --show-toplevel)"; cd "$REPO" || exit 2
GUARD="tools/verify_tree_guard.sh"
FAKE='touch /tmp/t346_inner_ready && sleep 4'
MARK=/tmp/t346_inner_ready
pass=0; fail=0

run_bg() {  # 后台起步守卫，等假门就绪
  rm -f "$MARK" "$LOG"
  ( VERIFY_INNER_CMD="$FAKE" bash "$GUARD" > "$LOG" 2>&1; echo $? > "$LOG.rc" ) &
  GPID=$!
  for _ in $(seq 1 60); do [ -f "$MARK" ] && break; sleep 0.2; done
}
finish() { wait "$GPID" 2>/dev/null; RC="$(cat "$LOG.rc" 2>/dev/null)"; }

echo "== T346 三向反向验证（clone=$REPO）=="

# ---------- C0 控制组：不改 ⇒ 世界层/前端均未变 ⇒ 绿 ----------
LOG=/tmp/t346_c0.log; run_bg; finish
echo; echo "== C0 无改动 ==="; grep -E "起跑指纹|收尾指纹|OK：|不可信" "$LOG" | head
[ "$RC" = 0 ] && grep -q "门结果可信" "$LOG" && { echo ">>> C0 PASS（绿）"; pass=$((pass+1)); } || { echo ">>> C0 FAIL（rc=$RC）"; fail=$((fail+1)); }

# ---------- C1 跑中改【世界层】⇒ 必须 exit 2 ----------
LOG=/tmp/t346_c1.log; run_bg
printf 'probe\n' > code/engine/_t346probe.untracked
finish; rm -f code/engine/_t346probe.untracked
echo; echo "== C1 跑中改世界层(code/engine/) =="; grep -E "起跑指纹|收尾指纹|世界层跑中被改|OK" "$LOG" | head
[ "$RC" = 2 ] && grep -q "世界层跑中被改" "$LOG" && { echo ">>> C1 PASS（红/不可信）"; pass=$((pass+1)); } || { echo ">>> C1 FAIL（rc=$RC，应 2）"; fail=$((fail+1)); }

# ---------- C2 跑中只改【前端】⇒ 告警、不阻断（rc=假门 rc=0）----------
LOG=/tmp/t346_c2.log; run_bg
printf 'probe\n' > code/frontend/_t346probe.untracked
finish; rm -f code/frontend/_t346probe.untracked
echo; echo "== C2 跑中只改前端(code/frontend/) =="; grep -E "起跑指纹|收尾指纹|降级为【告警】|世界层结论仍可信|世界层跑中被改" "$LOG" | head
[ "$RC" = 0 ] && grep -q "前端 CI 部分不可信" "$LOG" && ! grep -q "世界层跑中被改" "$LOG" && { echo ">>> C2 PASS（告警不阻断）"; pass=$((pass+1)); } || { echo ">>> C2 FAIL（rc=$RC）"; fail=$((fail+1)); }

# ---------- C3 跑中只提交 v2/evidence/**（改 HEAD、不碰冻结区）⇒ 绿 ----------
LOG=/tmp/t346_c3.log
mkdir -p v2/evidence && printf 'probe\n' > v2/evidence/_t346probe.md
git add v2/evidence/_t346probe.md >/dev/null 2>&1
run_bg
h0="$(git rev-parse HEAD)"
git -c user.email=t@t -c user.name=t commit -q -m "t346 reverse: evidence-only commit (HEAD moves, frozen untouched)" >/dev/null 2>&1
finish
h1="$(git rev-parse HEAD)"
echo; echo "== C3 跑中只提交 v2/evidence/** =="; echo "   HEAD $h0 -> $h1 （应不同：证明 HEAD 确实动了）"
grep -E "起跑指纹|收尾指纹|OK：|不可信" "$LOG" | head
if [ "$RC" = 0 ] && grep -q "门结果可信" "$LOG" && ! grep -q "不可信" "$LOG" && [ "$h0" != "$h1" ]; then
  echo ">>> C3 PASS（HEAD 动而门仍绿 —— 旧 T340 会误红）"; pass=$((pass+1))
else echo ">>> C3 FAIL（rc=$RC）"; fail=$((fail+1)); fi

echo; echo "== 汇总：PASS=$pass FAIL=$fail =="
[ "$fail" = 0 ]
