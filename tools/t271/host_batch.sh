#!/usr/bin/env bash
# T271 托管启动器 —— 把长跑批拉起在 jiuwenswarm.service 之外的 transient unit 里。
#
# 为什么：jiuwenswarm.service 的 KillMode=control-group —— memguard 重启平台时，
#         服务组内所有进程（含 detached 子进程）被一并回收（T236 死因）。
#         用 systemd-run 起一个独立的 <unit>.service（在 system.slice 下，与服务平级），
#         平台重启只停自己的 cgroup，不碰这个单元。
#
# 用法：
#   host_batch.sh --name BATCH --out RUN_DIR/run.jsonl --workdir <worktree>/code \
#                 --env-file <主树>/code/.env.local --heartbeat 600 \
#                 --meta sha=<sha> --meta switch=<值> --meta side_root=<path> \
#                 --meta flush_every=12 -- <batch cmd...>
set -euo pipefail

NAME=""; OUT=""; WORKDIR="$PWD"; MEM_HIGH="6G"; MEM_MAX="8G"; HB="600"; ENVFILE=""; RUN_DIR_OPT=""
META_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --name) NAME="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --run-dir) RUN_DIR_OPT="$2"; shift 2;;
    --workdir) WORKDIR="$2"; shift 2;;
    --mem-high) MEM_HIGH="$2"; shift 2;;
    --mem-max) MEM_MAX="$2"; shift 2;;
    --heartbeat) HB="$2"; shift 2;;
    --env-file) ENVFILE="$2"; shift 2;;
    --meta) META_ARGS+=("$2"); shift 2;;
    --) shift; break;;
    *) echo "未知参数 $1" >&2; exit 2;;
  esac
done
if [ -z "$NAME" ] || [ -z "$OUT" ]; then
  echo "用法: host_batch.sh --name BATCH --out OUT.jsonl [--workdir DIR] [--env-file F] -- <cmd...>" >&2; exit 2
fi
[ $# -gt 0 ] || { echo "缺少批次命令（-- 之后）" >&2; exit 2; }

BIN="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="${RUN_DIR_OPT:-$(dirname "$OUT")}"
mkdir -p "$RUN_DIR"

echo "[host] preflight"
bash "$BIN/preflight.sh" | tee "$RUN_DIR/preflight.txt"

UNIT="t271-${NAME}"
systemctl stop "$UNIT" 2>/dev/null || true
systemctl reset-failed "$UNIT" 2>/dev/null || true

# 凭据只走 EnvironmentFile（绝不 --setenv：否则密钥进 systemctl show / ps / journal）
ENV_ARGS=()
if [ -n "$ENVFILE" ]; then
  case "$ENVFILE" in /*) : ;; *) ENVFILE="$(cd "$(dirname "$ENVFILE")" && pwd)/$(basename "$ENVFILE")";; esac
  [ -r "$ENVFILE" ] || { echo "[host] FATAL: EnvironmentFile 不可读: $ENVFILE" >&2; exit 4; }
  ENV_ARGS=(-p "EnvironmentFile=$ENVFILE")
  echo "[host] 凭据来自 EnvironmentFile=$ENVFILE（内容不落日志/不入 unit 配置展示）"
fi

systemd-run --unit="$UNIT" --collect \
  --working-directory="$WORKDIR" \
  -p Type=simple \
  -p MemoryHigh="$MEM_HIGH" -p MemoryMax="$MEM_MAX" \
  -p Restart=no \
  -p KillMode=control-group \
  "${ENV_ARGS[@]}" \
  -p StandardOutput=append:"$RUN_DIR/host.log" \
  -p StandardError=append:"$RUN_DIR/host.log" \
  "$BIN/t271_runner.sh" "$RUN_DIR" "$OUT" "$HB" -- "$@"

echo "[host] launched unit=$UNIT"
sleep 1
systemctl show "$UNIT" -p Id -p ControlGroup -p MainPID --no-pager
BPID="$(cat "$RUN_DIR/batch.pid" 2>/dev/null || echo '')"
echo "[host] batch pid=$BPID"
[ -n "$BPID" ] && echo "[host] batch cgroup=$(cat /proc/$BPID/cgroup 2>/dev/null)"

# 每批 run 元数据（缺一不可）落盘 —— 供事后可溯
T271_NAME="$NAME" T271_UNIT="$UNIT" T271_WORKDIR="$WORKDIR" T271_ENVFILE="$ENVFILE" \
T271_OUT="$OUT" T271_HBFILE="$RUN_DIR/heartbeat.tsv" \
T271_MEM_HIGH="$MEM_HIGH" T271_MEM_MAX="$MEM_MAX" T271_CMD="$*" \
T271_META="$(printf '%s\n' "${META_ARGS[@]:-}")" \
python3 - "$RUN_DIR/meta.json" <<'PY'
import json, os, sys, time
p = sys.argv[1]
meta = {}
for ln in os.environ.get("T271_META", "").splitlines():
    ln = ln.strip()
    if ln and "=" in ln:
        k, v = ln.split("=", 1)
        meta[k] = v
d = {
    "batch": os.environ["T271_NAME"], "unit": os.environ["T271_UNIT"],
    "started_at": time.strftime("%F %T"), "ended_at": None,
    "workdir": os.environ["T271_WORKDIR"], "env_file": os.environ["T271_ENVFILE"] or None,
    "out": os.environ["T271_OUT"], "heartbeat_file": os.environ["T271_HBFILE"],
    "mem_high": os.environ["T271_MEM_HIGH"], "mem_max": os.environ["T271_MEM_MAX"],
    "cmd": os.environ["T271_CMD"],
    "sha": None, "worktree": None, "switch": None, "side_root": None,
    "flush_every": None, "engine_version_fingerprint": None,
}
d.update(meta)
json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
print("[host] meta.json:", p)
PY
echo "[host] 心跳: tail -f $RUN_DIR/heartbeat.tsv"
echo "[host] 状态: $BIN/status.sh $RUN_DIR"
