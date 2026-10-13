#!/usr/bin/env bash
# serve_ctl.sh — 看板/回放/实时跟随的本地开发服务，一键管理（T348）。
#
# ⚠️ 这是**本地开发服务，不对外暴露**（只读动态端点 + 白名单根）。
# 端口默认 8848；实时跟随白名单根 HITT_LIVE_ROOTS 默认 /root/t271/runs。
# 托管：systemd **transient** 单元（运行时创建、不安装 unit 文件；可 status/restart/log）。
#   —— 无 systemd 环境用 `start-nohup` 兜底（setsid 后台，写 pid 文件，可用 stop-nohup 停）。
#
# 用法：
#   bash code/frontend/tools/serve_ctl.sh start         # systemd transient 起（推荐）
#   bash code/frontend/tools/serve_ctl.sh restart|stop|status|log
#   bash code/frontend/tools/serve_ctl.sh start-nohup   # 无 systemd 兜底
#   bash code/frontend/tools/serve_ctl.sh stop-nohup
#
# 环境变量：PORT(8848) HOST(0.0.0.0) HITT_LIVE_ROOTS(/root/t271/runs) UNIT(hitt-dashboard)
set -uo pipefail
FRONTEND="$(cd "$(dirname "$0")/.." && pwd)"      # -> code/frontend
PORT="${PORT:-8848}"; HOST="${HOST:-0.0.0.0}"
ROOTS="${HITT_LIVE_ROOTS:-/root/t271/runs}"
UNIT="${UNIT:-hitt-dashboard}"
PIDF="/tmp/hitt-dashboard.pid"
URL="http://127.0.0.1:${PORT}/dashboard.html"

say(){ printf '%s\n' "$*"; }
status_check(){ curl -s -o /dev/null -w "  ${URL} -> %{http_code}\n" --max-time 3 "$URL" || true; }

case "${1:-status}" in
  start)
    say "systemd-run transient 单元 $UNIT（Workdir=$FRONTEND, HITT_LIVE_ROOTS=$ROOTS, port=$PORT）"
    systemd-run --unit="$UNIT" --collect --property=Restart=always --property=RestartSec=2 \
      --property=WorkingDirectory="$FRONTEND" --setenv="HITT_LIVE_ROOTS=$ROOTS" \
      python3 "$FRONTEND/tools/serve.py" --host "$HOST" --port "$PORT"
    sleep 2; systemctl is-active "$UNIT"; status_check ;;
  restart) systemctl restart "$UNIT"; sleep 2; systemctl is-active "$UNIT"; status_check ;;
  stop)    systemctl stop "$UNIT"; say "stopped $UNIT" ;;
  status)  systemctl is-active "$UNIT"; status_check ;;
  log)     journalctl -u "$UNIT" -n 50 --no-pager ;;
  start-nohup)
    say "nohup fallback（无 systemd）: port=$PORT roots=$ROOTS"
    cd "$FRONTEND"
    HITT_LIVE_ROOTS="$ROOTS" setsid nohup python3 "$FRONTEND/tools/serve.py" --host "$HOST" --port "$PORT" \
      >/tmp/hitt-dashboard.log 2>&1 < /dev/null &
    echo $! > "$PIDF"; sleep 2; say "pid=$(cat "$PIDF")"; status_check ;;
  stop-nohup) [ -f "$PIDF" ] && kill "$(cat "$PIDF")" 2>/dev/null; rm -f "$PIDF"; say "stopped (nohup)" ;;
  *) say "用法: $0 {start|restart|stop|status|log|start-nohup|stop-nohup}" ;;
esac
