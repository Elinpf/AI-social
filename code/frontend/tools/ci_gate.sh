#!/usr/bin/env bash
# ci_gate.sh — 前端两道回归门禁一键跑（T107/T108 归一）
#   ① 无浏览器快速门禁：node smoke_test.js（PIXI mock；快，但抓不到真 Pixi 运行期错误）
#   ② 真渲染门禁：python gate_render.py（真 Chromium/SwiftShader；抓 pageerror / 画面空）
#
# 退出码（供 CI 区分「通过 / 失败 / 未跑」，严禁把"没跑"当"通过"）：
#   0 = PASS（两道门禁均通过）
#   1 = FAIL（任一断言失败 / 真实渲染报错）
#   3 = SKIP（真渲染门禁依赖缺失，未执行；不算通过）
#
# 用法：bash frontend/tools/ci_gate.sh
#   GATE_PY=/path/to/gate_render.py  可覆盖门禁脚本（用于反向验证/替换实现）
#   HITT_SKIP_SMOKE=1                可跳过快速门禁（仅调试用）
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"   # -> code/
cd "$ROOT"
export PATH="/root/.local/share/pi-node/node-v22.23.1-linux-x64/bin:$PATH"
GATE_PY="${GATE_PY:-frontend/tools/gate_render.py}"
rc=0

echo "== [1/2] 无浏览器快速门禁：smoke_test.js =="
if [ "${HITT_SKIP_SMOKE:-0}" = "1" ]; then
  echo "  (跳过：HITT_SKIP_SMOKE=1)"
else
  t0=$(date +%s.%N)
  node frontend/tools/smoke_test.js; smoke_rc=$?
  t1=$(date +%s.%N)
  echo "  smoke exit=$smoke_rc  elapsed=$(awk "BEGIN{printf \"%.2f\", $t1-$t0}")s"
  [ "$smoke_rc" -ne 0 ] && rc=1
fi

echo "== [2/2] 真渲染门禁：$GATE_PY =="
if ! ss -ltn 2>/dev/null | grep -q ':8848'; then
  echo "  启动静态服务 0.0.0.0:8848 ..."
  setsid nohup python3 frontend/tools/serve.py --host 0.0.0.0 --port 8848 >/tmp/hitt_serve.log 2>&1 < /dev/null &
  sleep 1.5
fi
python3 "$GATE_PY"; gate_rc=$?
case "$gate_rc" in
  0) : ;;
  3) echo "  → 真渲染门禁 SKIP（依赖缺失，未执行）"; [ "$rc" -eq 0 ] && rc=3 ;;
  *) rc=1 ;;
esac

echo
case "$rc" in
  0) echo "CI GATE: PASS" ;;
  3) echo "CI GATE: SKIP（真渲染门禁未跑，不算通过）" ;;
  *) echo "CI GATE: FAIL" ;;
esac
exit "$rc"
