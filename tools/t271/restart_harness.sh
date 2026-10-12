#!/usr/bin/env bash
# T271 重启存活验证 —— 反向对照 + 逃逸存活，一次跑清。
#
# 语义等价论证：
#   t271-guard.service 与 jiuwenswarm.service 同为 KillMode=control-group。
#   重启 guard = 复现「memguard 重启平台 → 服务组内 detached 子进程被回收」这一步。
#   若 in-cgroup 受害者【不死】，说明本测试无效（假红防护，反向对照）；它死了才证明机制成立。
#   逃逸到独立 transient unit 的候选批在【同一次重启】中必须存活。
set -u
BIN=/root/t271/bin
source "$BIN/safe_rmrf.sh"   # T313 rm -rf 守卫
RUN=/root/t271/runs/restart-test
CAND="restart-cand"
safe_rmrf "$RUN"; mkdir -p "$RUN"

echo "############ T271 restart-survival ############"
echo "# 开始 $(date '+%F %T')"

# 0) 上线 decoy guard
systemctl stop t271-guard 2>/dev/null || true
systemctl reset-failed t271-guard 2>/dev/null || true
systemctl start t271-guard
sleep 3
VINC=$(readlink -f "$RUN/victim/current" 2>/dev/null || echo '')
V=$(cat "$VINC/victim.pid" 2>/dev/null || echo '')
VHB="$VINC/victim.hb"
VCG=$(cat /proc/$V/cgroup 2>/dev/null || echo '')
echo "[before] victim pid=$V alive=$(kill -0 "$V" 2>/dev/null && echo yes || echo no) cgroup=$VCG inc=$VINC"

# 1) 拉起逃逸候选批（独立 unit）
bash "$BIN/host_batch.sh" --name "$CAND" --out "$RUN/cand/run.jsonl" --heartbeat 30 \
  --workdir /root/t271 -- \
  python3 "$BIN/mock_batch.py" --out "$RUN/cand/run.jsonl" \
    --rounds 100000 --round-seconds 0.3 --flush-every 5 \
    --heartbeat-log "$RUN/cand/mock.hb" --heartbeat-seconds 2 \
  >"$RUN/launch.log" 2>&1
CP=$(cat "$RUN/cand/batch.pid" 2>/dev/null || echo '')
CCG=$(cat /proc/$CP/cgroup 2>/dev/null || echo '')
echo "[before] cand   pid=$CP alive=$(kill -0 "$CP" 2>/dev/null && echo yes || echo no) cgroup=$CCG"

# 2) 让两边都跑几拍心跳
sleep 6

# 3) 复现重启
RESTART_TS=$(date '+%F %T')
echo "[action] $RESTART_TS  systemctl restart t271-guard.service"
systemctl restart t271-guard
sleep 6

# 4) 断言
VA=$(kill -0 "$V" 2>/dev/null && echo yes || echo no)
CA=$(kill -0 "$CP" 2>/dev/null && echo yes || echo no)
echo "[after ] victim(旧inc) pid=$V alive=$VA  其心跳末行: $(tail -1 "$VHB" 2>/dev/null)"
echo "[after ] victim 新inc=$(readlink -f "$RUN/victim/current")"
echo "[after ] cand   pid=$CP alive=$CA cgroup=$(cat /proc/$CP/cgroup 2>/dev/null)"
echo "[after ] cand   hb 末行: $(tail -1 "$RUN/cand/mock.hb" 2>/dev/null)"

# 5) 判定
PASS=1
[ "$VA" = "no" ]  || { echo "[FAIL] 反向对照失效：in-cgroup 受害者没死 → 本测试不能证明任何事"; PASS=0; }
[ "$CA" = "yes" ] || { echo "[FAIL] 逃逸候选批被误杀 → 托管方式不可用"; PASS=0; }
# 日志连续性：候选 hb 必须同时含重启前与重启后的行
if awk -v ts="$RESTART_TS" '$1" "$2 <= ts' "$RUN/cand/mock.hb" 2>/dev/null | grep -q . \
   && awk -v ts="$RESTART_TS" '$1" "$2 > ts' "$RUN/cand/mock.hb" 2>/dev/null | grep -q .; then
  echo "[ok] 候选批心跳跨越重启时刻连续（重启前后都有行）"
else
  echo "[FAIL] 候选批心跳未跨越重启时刻"; PASS=0
fi

# 清理本次自起的 unit（只点自己显式单元名；T313 —— 不留残留 unit）
systemctl stop t271-guard 2>/dev/null; systemctl reset-failed t271-guard 2>/dev/null
systemctl stop t271-restart-cand 2>/dev/null; systemctl reset-failed t271-restart-cand 2>/dev/null

echo "# 结束 $(date '+%F %T')"
if [ "$PASS" = "1" ]; then echo "############ RESULT: PASS ############"; else echo "############ RESULT: FAIL ############"; fi
exit $((1-PASS))
