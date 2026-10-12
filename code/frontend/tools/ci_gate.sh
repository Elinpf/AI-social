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
IMMERSION_LOG="${IMMERSION_LOG:-sample/run_c_n20.play.jsonl}"
GATE_PY="${GATE_PY:-frontend/tools/gate_render.py}"
rc=0

# T220 三：门禁结论必须说明「在哪个 git 状态上跑的」（证据绑版本）。
# 打头三行 sha/dirty_files/状态；DIRTY 时结论仅供参考。CI 可用 GIT_STAMP_STRICT=1 强制脏树即失败。
_GS="$(cd "$ROOT/.." && pwd)/tools/git_stamp.sh"
if [ -f "$_GS" ]; then bash "$_GS"; fi

echo "== [1/3] 无浏览器快速门禁：smoke_test.js =="
if [ "${HITT_SKIP_SMOKE:-0}" = "1" ]; then
  echo "  (跳过：HITT_SKIP_SMOKE=1)"
else
  t0=$(date +%s.%N)
  node frontend/tools/smoke_test.js; smoke_rc=$?
  t1=$(date +%s.%N)
  echo "  smoke exit=$smoke_rc  elapsed=$(awk "BEGIN{printf \"%.2f\", $t1-$t0}")s"
  [ "$smoke_rc" -ne 0 ] && rc=1
fi

echo "== [2/3] 真渲染门禁：$GATE_PY =="
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

echo "== [3/3] R9 沉浸/质感口径：immersion_metrics.js =="
echo "  （校准条件：view=default · scale=1 · 960×720；日志 $IMMERSION_LOG）"
node frontend/tools/immersion_metrics.js --log "$IMMERSION_LOG"; imm_rc=$?
[ "$imm_rc" -ne 0 ] && rc=1

# T267 D 段：前端资产/常量「定义了却零引用」（睡着的资产）。含反向验证自检。
echo "== [D] 睡着的资产核对：tools/check_inert_registry.py（D 段）=="
python3 ../tools/check_inert_registry.py --self-test | sed 's/^/  /'
python3 ../tools/check_inert_registry.py 2>&1 | sed -n '/\[D\]/,/^-\{10,\}/p' | sed 's/^/  /'
python3 ../tools/check_inert_registry.py >/dev/null 2>&1; ir_rc=$?
if [ "$ir_rc" -ne 0 ]; then echo "  → D 段红：棘轮不一致 / 自动枚举命中（详见上方 [D]）"; rc=1; else echo "  D 段 ok（含反向验证）"; fi

echo
case "$rc" in
  0) echo "CI GATE: PASS" ;;
  3) echo "CI GATE: SKIP（真渲染门禁未跑，不算通过）" ;;
  *) echo "CI GATE: FAIL" ;;
esac
exit "$rc"
