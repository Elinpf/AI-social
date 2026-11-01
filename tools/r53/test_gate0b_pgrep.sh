#!/usr/bin/env bash
# 闸门0b pgrep 收窄 —— 离线回归自测（不起跑批、不调 LLM、不写 evidence）
#
# 证明三件事（对应 R2-tools 缺陷 1 的验收要求）：
#   1) 修前模式（裸 `[r]un_[b]atch`）对「只读监视壳」**误报**
#      —— 复现 v2/evidence/r53-gate0b-falsepositive-20261102/launch_evidence_FAILED_*.txt
#   2) 修后模式对同一个只读壳**不误报**
#   3) 修后模式对「真实形态的并发跑批」**仍然命中**（没有降级成永远 pass）
#
# 用法（仓库根，确认当前无跑批在跑后）：
#   bash tools/r53/test_gate0b_pgrep.sh
# 退出码：0 = 全部断言通过；1 = 有断言失败。
#
# ⚠ 副作用窗口：本脚本会在进程表里出现「文件名含 run_batch.sh / arm_inner.sh」的**假进程**
#   （各 ~6s，探测完立即 kill）。这 6 秒内若有别的成员跑 preflight / launch_arm 的并发探针，
#   会被正确判定为「并发」而失败。故只在该窗口前后无跑批时手动执行。
set -uo pipefail

# ---- 被比较的两套模式（旧 = 修前；新 = 修后，与 tools/r53/launch_arm.sh 闸门0b 逐字一致）----
OLD_PATTERNS=(
  "orchestration[[:space:]]+run"
  "[r]un_[b]atch"
  "[n]ightly\.py"
)
NEW_PATTERNS=(
  "[-]m[[:space:]]+orchestration[[:space:]]+run"
  "[r]un_batch\.sh([[:space:]]|$)"
  "[a]rm_inner\.sh([[:space:]]|$)"
  "[n]ightly\.py([[:space:]]|$)"
)

FAILS=0
ok()   { echo "  PASS  $*"; }
bad()  { echo "  FAIL  $*"; FAILS=$((FAILS+1)); }

# ---------- 1) 字符串口径：把「真实 cmdline」当字符串，用同一套 ERE 判定 ----------
# `pgrep -f` 就是对 /proc/<pid>/cmdline（argv 以空格连接）做 ERE 匹配，故此口径与运行时等价；
# 唯一差别是不需要真的把进程挂在进程表上（零副作用，可覆盖 orchestration run / nightly.py）。
matches_any() { # $1=cmdline字符串, 其余=模式集合
  local line="$1"; shift
  local pat
  for pat in "$@"; do
    if printf '%s' "$line" | grep -qE -- "$pat"; then echo "$pat"; return 0; fi
  done
  return 1
}

echo "==== 1) 字符串口径（真实 cmdline 形态 vs 两套模式）===="

WATCHER='/bin/sh -c sleep 300; cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment && wc -l v2/evidence/r53-schedule-offset-off-20261102_n16r36_s42/run.jsonl; ls v2/evidence/ | grep -E "meta.json|run_batch.rc" || echo "no meta/rc"; date "+%T"'
# 同类误报第二形态：只读壳里出现裸 `orchestration run` 子串（rg/pgrep 命令行、聊天记录粘贴等），
# 不含 `-m` 前缀 ⇒ 不是真跑批。修前模式 a 也会命中。
WATCHER2='/bin/sh -c sleep 300; pgrep -af "orchestration run|run_batch" | grep -v pgrep'
REAL_RUNBATCH='bash /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/tools/d2/run_batch.sh --out-dir /x --seed 42 --agents 16 --rounds 36'
REAL_INNER='bash /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/tools/r53/arm_inner.sh on'
REAL_ORCH='python3 -m orchestration run --life --seed 42 --agents 16 --rounds 36 --out /x/run.jsonl --flush-every 2'
REAL_NIGHTLY='python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/tools/nightly.py'

for pair in \
  "只读监视壳(含 run_batch.rc)|${WATCHER}" \
  "只读壳(裸 orchestration run)|${WATCHER2}" \
  "真跑批 run_batch.sh|${REAL_RUNBATCH}" \
  "真跑批 arm_inner.sh|${REAL_INNER}" \
  "真跑批 orchestration run|${REAL_ORCH}" \
  "真跑批 nightly.py|${REAL_NIGHTLY}" ; do
  label="${pair%%|*}"; line="${pair#*|}"
  old_hit="$(matches_any "$line" "${OLD_PATTERNS[@]}" || true)"
  new_hit="$(matches_any "$line" "${NEW_PATTERNS[@]}" || true)"
  printf '  %-28s old=%-38s new=%s\n' "$label" "${old_hit:-<no-hit>}" "${new_hit:-<no-hit>}"
done

# 断言：只读壳 —— 修前命中（误报），修后不命中
if matches_any "$WATCHER" "${OLD_PATTERNS[@]}" >/dev/null; then ok "修前模式对只读壳**命中**（事故可复现）"; else bad "修前模式居然没命中只读壳，事故复现失败"; fi
if matches_any "$WATCHER" "${NEW_PATTERNS[@]}" >/dev/null; then bad "修后模式仍然命中只读壳（没收窄到）；命中模式=$(matches_any "$WATCHER" "${NEW_PATTERNS[@]}")"; else ok "修后模式对只读壳**不命中**（误报消除）"; fi
if matches_any "$WATCHER2" "${NEW_PATTERNS[@]}" >/dev/null; then bad "修后模式仍命中「裸 orchestration run」只读壳"; else ok "修后模式对「裸 orchestration run」只读壳**不命中**（-m 前缀锚定生效）"; fi

# 断言：四种真跑批形态 —— 修后必须仍然命中（不漏报）
for c in "$REAL_RUNBATCH" "$REAL_INNER" "$REAL_ORCH" "$REAL_NIGHTLY"; do
  if matches_any "$c" "${NEW_PATTERNS[@]}" >/dev/null; then ok "修后模式仍拦住真并发：$(matches_any "$c" "${NEW_PATTERNS[@]}")"; else bad "修后模式漏报真并发：$c"; fi
done

# ---------- 2) 运行时口径：用真进程 + 真 pgrep，证明管道确实按上面口径工作 ----------
echo "==== 2) 运行时口径（真进程 + 真 pgrep）===="
FP="/tmp/r53_gate0b_selftest_$$"
mkdir -p "$FP/tools/d2" || { echo "无法建 $FP"; exit 1; }
printf '#!/usr/bin/env bash\nsleep 6\n' > "$FP/tools/d2/run_batch.sh"
printf '#!/usr/bin/env bash\nsleep 6\n' > "$FP/arm_inner.sh"
chmod +x "$FP/tools/d2/run_batch.sh" "$FP/arm_inner.sh"

PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do [[ -n "${p:-}" ]] && kill "$p" 2>/dev/null || true; done
            for p in "${PIDS[@]:-}"; do [[ -n "${p:-}" ]] && wait "$p" 2>/dev/null || true; done
            rm -rf "$FP"; }
trap cleanup EXIT

wait_for() { # $1=pgrep pattern；最多轮询 100×20ms（无长 sleep）
  local i
  for i in $(seq 1 100); do pgrep -f "$1" >/dev/null 2>&1 && return 0; sleep 0.02; done
  return 1
}

# --- 2a) 只读监视壳 ---
sh -c 'sleep 6; ls /tmp | grep -E "meta.json|run_batch.rc" || echo "no meta/rc"' &
WPID=$!
PIDS+=("$WPID")
wait_for 'run_batch\.rc' || { bad "只读壳假进程没起来"; }
old_rc=1; pgrep -f '[r]un_[b]atch' >/dev/null 2>&1 && old_rc=0
new_rc=1; for pat in "${NEW_PATTERNS[@]}"; do pgrep -f "$pat" >/dev/null 2>&1 && new_rc=0; done
echo "  只读壳 pid=$WPID  cmdline=$(tr '\0' ' ' < "/proc/$WPID/cmdline")"
[[ "$old_rc" -eq 0 ]] && ok "真 pgrep + 修前模式 ⇒ 误判并发（R52/R53 事故现场复现）" || bad "真 pgrep + 修前模式未命中只读壳"
[[ "$new_rc" -ne 0 ]] && ok "真 pgrep + 修后模式 ⇒ 未命中只读壳（误报消除）" || bad "真 pgrep + 修后模式仍命中只读壳"
kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null || true
PIDS=()
for i in $(seq 1 100); do pgrep -f 'run_batch\.rc' >/dev/null 2>&1 || break; sleep 0.02; done

# --- 2b) 真实形态的假跑批（run_batch.sh / arm_inner.sh）---
bash "$FP/tools/d2/run_batch.sh" --out-dir /tmp/x --seed 42 & PIDS+=($!)
bash "$FP/arm_inner.sh" on & PIDS+=($!)
wait_for '[r]un_batch\.sh([[:space:]]|$)' || bad "假 run_batch.sh 没起来"
wait_for '[a]rm_inner\.sh([[:space:]]|$)' || bad "假 arm_inner.sh 没起来"
new_hits=0
for pat in "${NEW_PATTERNS[@]}"; do
  if pgrep -f "$pat" >/dev/null 2>&1; then
    new_hits=$((new_hits+1)); echo "  命中 /$pat/ ⇒ $(pgrep -fa "$pat" | tr '\n' '|')"
  fi
done
[[ "$new_hits" -ge 2 ]] && ok "真 pgrep + 修后模式 ⇒ 拦住真形态并发（$new_hits 条探针命中，未降级为永远 pass）" \
  || bad "真 pgrep + 修后模式漏报真形态并发（命中 $new_hits 条）"

echo "==== 结果 ===="
if [[ "$FAILS" -eq 0 ]]; then echo "ALL PASS"; exit 0; else echo "FAILS=$FAILS"; exit 1; fi
