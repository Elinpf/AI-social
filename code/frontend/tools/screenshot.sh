#!/usr/bin/env bash
# screenshot.sh — 无头截图（真·浏览器渲染）。T121：**等渲染就绪**再截，防"假黑图"。
#
# ★ 已知坑（false negative / 假红）：**大日志（≥10MB）+ still 单帧**下，若在页面就绪前截图，
#   会得到**整列发黑的假图**——**不是渲染 bug，是截图时序**。故**不靠固定 sleep**，
#   而是等前端就绪信号 `window.__RENDER_READY__`（`main.js` 在素材加载完+首帧后置位），
#   等不到即**超时非零退出**，绝不默默产出黑图。实现见 `tools/shot.py`。
#
# 其它：一次进程一张图、截完即退；**串行（flock）**，禁止并发多浏览器；timeout 兜底 + 退出清理残留进程；
#   输出必须写 $HOME（snap 写 /tmp 会静默失败）。
#
# 前置：静态服务在跑（cd code && python frontend/tools/serve.py --host 0.0.0.0 --port 8848）
# 用法：
#   bash frontend/tools/screenshot.sh [out.png] [logUrl] [round] [WxH] [extraQuery]
# 默认：./hitt_shot.png（当前目录）  sample/demo_run.jsonl  12  1500x980
# 例（加审计抽屉）：bash frontend/tools/screenshot.sh ./a.png sample/demo_run.jsonl 12 1500x950 "&audit=1"
# 拍动画（关 still）：STILL=0 bash frontend/tools/screenshot.sh ...
# 退出码：0=OK；1=FAIL（超时未就绪/页面报错）；3=SKIP（无 playwright）
set -uo pipefail

OUT="${1:-./hitt_shot.png}"
LOG="${2:-sample/demo_run.jsonl}"
ROUND="${3:-12}"
SIZE="${4:-1500x980}"
EXTRA="${5:-}"
STILL="${STILL:-1}"
W="${SIZE%x*}"; H="${SIZE#*x}"

STILL_Q=""; [ "$STILL" = "1" ] && STILL_Q="&still=1"
URL="http://127.0.0.1:8848/?log=${LOG}&round=${ROUND}${STILL_Q}${EXTRA}"

LOCK=/tmp/hitt_screenshot.lock
cleanup() { pkill -f 'chrome.*--no-sandbox' 2>/dev/null || true; }
trap cleanup EXIT

# 串行化：同一时刻只允许一个截图进程
exec 9>"$LOCK"
if ! flock -w 90 9; then echo "另一个截图在进行中（90s 未获锁），放弃" >&2; exit 1; fi

echo "screenshot -> $OUT  ($URL)"
# 等待就绪的总超时（秒）：大日志用更大值；VT_BUDGET 沿用旧名，单位秒
python3 "$(dirname "$0")/shot.py" --url "$URL" --out "$OUT" \
  --width "$W" --height "$H" --timeout "${SHOT_TIMEOUT:-${VT_BUDGET:-90}}"
rc=$?
if [ "$rc" = "0" ] && [ -f "$OUT" ]; then
  ls -la "$OUT"; sha256sum "$OUT"
else
  echo "截图未成功（rc=$rc）；未产出可信图像" >&2
fi
exit "$rc"
