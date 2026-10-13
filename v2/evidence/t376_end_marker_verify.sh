#!/usr/bin/env bash
# T376 非作者独立核：T374 `END` 标记机制（含 SIGKILL 负例）。
# 装置：冻结副本（git archive HEAD）+ 直接跑 t271_runner.sh（不经 systemd）；告警目录隔离到 /tmp。
# 不碰主树、不写 /root/t271。
set -u
REPO="$(git rev-parse --show-toplevel)"
SRC=/tmp/t376_src; RMB=/tmp/t376_runs; ALERT=/tmp/t376_alert
rm -rf "$SRC" "$RMB" "$ALERT" /tmp/t271-t376; mkdir -p "$SRC" "$RMB" "$ALERT" /tmp/t271-t376
git -C "$REPO" archive HEAD | tar -x -C "$SRC"
export T271_ALERT_DIR="$ALERT" N50_VEC=0
RUNNER="$SRC/tools/t271/t271_runner.sh"; CODE="$SRC/code"
pass=0; fail=0
ok(){ echo ">>> $1"; pass=$((pass+1)); }
no(){ echo ">>> $1"; fail=$((fail+1)); }

echo "=== T376 独立核 END 标记（副本 $SRC，tree=copy）==="

# ---- ① 正常 rc=0：END 数字与 host.log 一致 ----
RD="$RMB/ok"; mkdir -p "$RD"
printf '%s' '{"batch":"t376ok","unit":"t376ok","workdir":"/tmp/t271-t376/code","sha":"HEADCOPY","out":"'"$RD"'/run.jsonl"}' > "$RD/meta.json"
( cd "$CODE" && bash "$RUNNER" "$RD" "$RD/run.jsonl" 5 -- python3 -m orchestration run --life --seed 7 --agents 3 --rounds 2 --out "$RD/run.jsonl" --side-root "$RD/side" --flush-every 1 ) > "$RD/host.log" 2>&1
rc=$?
echo "--- ① 正常 rc=$rc ---"; cat "$RD/END" 2>/dev/null; echo "--- host.log 关键行 ---"; grep -E "batch exited|final_state_hash|events=" "$RD/host.log"
E_RC=$(python3 -c "import json;print(json.load(open('$RD/END'))['rc'])" 2>/dev/null)
E_EV=$(python3 -c "import json;print(json.load(open('$RD/END'))['events'])" 2>/dev/null)
E_FSH=$(python3 -c "import json;print(json.load(open('$RD/END'))['final_state_hash'])" 2>/dev/null)
E_TREE=$(python3 -c "import json;print(json.load(open('$RD/END'))['tree'])" 2>/dev/null)
H_FSH=$(grep -o 'final_state_hash=sha256:[0-9a-f]*' "$RD/host.log" | head -1 | cut -d= -f2)
H_EV=$(grep -o 'events=[0-9]*' "$RD/host.log" | head -1 | cut -d= -f2)
[ "$rc" = 0 ] && [ "$E_RC" = 0 ] && [ "$E_FSH" = "$H_FSH" ] && [ "$E_EV" = "$H_EV" ] && [ "$E_TREE" = copy ] \
  && ok "① PASS（END rc=0 / events=$E_EV==host / fsh 一致 / tree=copy）" || no "① FAIL（rc=$rc E_RC=$E_RC E_EV=$E_EV H_EV=$H_EV E_FSH=$E_FSH H_FSH=$H_FSH tree=$E_TREE）"

# ---- ② 非 0（exit 7）----
RD="$RMB/fail"; mkdir -p "$RD"
printf '%s' '{"batch":"t376fail","workdir":"/tmp/t271-t376/code","sha":"X"}' > "$RD/meta.json"
bash "$RUNNER" "$RD" "$RD/run.jsonl" 5 -- bash -c 'exit 7' > "$RD/host.log" 2>&1; rc=$?
E_RC=$(python3 -c "import json;print(json.load(open('$RD/END'))['rc'])" 2>/dev/null)
echo "--- ② 非0 rc=$rc END.rc=$E_RC ---"
[ "$E_RC" = 7 ] && ok "② PASS（END.rc=7）" || no "② FAIL（E_RC=$E_RC）"

# ---- ③ SIGTERM ----
RD="$RMB/term"; mkdir -p "$RD"
printf '%s' '{"batch":"t376term","workdir":"/tmp/t271-t376/code","sha":"X"}' > "$RD/meta.json"
bash "$RUNNER" "$RD" "$RD/run.jsonl" 5 -- bash -c 'sleep 60' > "$RD/host.log" 2>&1 &
RP=$!; sleep 1.5; kill -TERM "$RP"; wait "$RP" 2>/dev/null; rc=$?; pkill -f 'sleep 60' 2>/dev/null
E_RC=$(python3 -c "import json;print(json.load(open('$RD/END'))['rc'])" 2>/dev/null)
echo "--- ③ SIGTERM runner rc=$rc END.rc=$E_RC ---"; grep -E "END-MARKER|batch exited" "$RD/host.log" | head -3
[ "$E_RC" = 143 ] && ok "③ PASS（SIGTERM ⇒ END.rc=143）" || no "③ FAIL（E_RC=$E_RC）"

# ---- ④ SIGKILL 负例：END 不写出 ----
RD="$RMB/kill"; mkdir -p "$RD"
printf '%s' '{"batch":"t376kill","workdir":"/tmp/t271-t376/code","sha":"X"}' > "$RD/meta.json"
bash "$RUNNER" "$RD" "$RD/run.jsonl" 5 -- bash -c 'sleep 60' > "$RD/host.log" 2>&1 &
RP=$!; sleep 1.5; kill -KILL "$RP"; wait "$RP" 2>/dev/null; pkill -f 'sleep 60' 2>/dev/null
if [ -f "$RD/END" ]; then no "④ FAIL（SIGKILL 竟写出 END）"; else ok "④ PASS（SIGKILL ⇒ END 缺失=异常信号）"; fi

# ---- ⑤ 顺序/开销：host.log 先 batch exited 后 END-MARKER ----
echo "--- ⑤ host.log 顺序（① ）---"; grep -nE "batch exited|END-MARKER" "$RMB/ok/host.log"
if [ "$(grep -n 'batch exited' "$RMB/ok/host.log" | head -1 | cut -d: -f1)" -lt "$(grep -n 'END-MARKER' "$RMB/ok/host.log" | head -1 | cut -d: -f1)" ] 2>/dev/null; then
  ok "⑤ PASS（先 batch exited 后 END-MARKER ⇒ marker 在批体之后）"
else no "⑤ FAIL（顺序异常）"; fi

echo; echo "=== 汇总：PASS=$pass FAIL=$fail ==="
