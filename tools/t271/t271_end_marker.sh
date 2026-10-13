#!/usr/bin/env bash
# T374 跑批结束标记 —— 把"跑完即报"从纪律变机制。
#
# 在【批体结束后】写固定名 `END`（JSON）到 run 目录，并尽力主动通知：
#   - 固定告警路径（供周期自检一眼看到）：/root/t271/alert/last_end.json（最新）+ ends.log（逐条 append）
#   - host.log / journal（固定前缀 [END-MARKER]，可 grep）
# ⚠️ 不进热路径：本脚本只在子进程退出后调用，不参与批体计时。
#
# 用法: t271_end_marker.sh <run_dir> <rc>           # 写 END（若已存在则幂等跳过）
#       t271_end_marker.sh <run_dir> <rc> --force   # 覆盖重写
set -uo pipefail
RUN_DIR="${1:?用法: t271_end_marker.sh <run_dir> <rc> [--force]}"
RC="${2:?缺少 rc}"
FORCE="${3:-}"
END="$RUN_DIR/END"
ALERT_DIR="${T271_ALERT_DIR:-/root/t271/alert}"
mkdir -p "$ALERT_DIR"

# 幂等：已写过则不重复（除非 --force）
if [ -f "$END" ] && [ "$FORCE" != "--force" ]; then
  exit 0
fi

export T374_RUN_DIR="$RUN_DIR" T374_RC="$RC" T374_END="$END" T374_ALERT_DIR="$ALERT_DIR"
python3 - <<'PY'
import json, os, time
rd = os.environ["T374_RUN_DIR"]; rc = os.environ["T374_RC"]
endp = os.environ["T374_END"]; adir = os.environ["T374_ALERT_DIR"]

def load(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return {}

meta = load(os.path.join(rd, "meta.json"))
out = meta.get("out") or os.path.join(rd, "run.jsonl")

# 起止：优先 meta.started_at 与心跳首/末行
started = meta.get("started_at")
hb = meta.get("heartbeat_file")
hb_first = hb_last = None
if hb and os.path.exists(hb):
    ls = [l for l in open(hb, encoding="utf-8").read().splitlines() if l.strip()]
    if ls:
        hb_first = ls[0].split("\t")[0]; hb_last = ls[-1].split("\t")[0]
started = started or hb_first
ended = time.strftime("%F %T")

# 批体实测：末 round / 事件数 / final_state_hash（只读 tail，post-batch，不进热路径）
rounds = events = None; fsh = None
if os.path.exists(out):
    try:
        events = sum(1 for _ in open(out, "rb"))
    except Exception:
        events = None
    try:
        with open(out, "rb") as f:
            f.seek(0, 2); size = f.tell()
            f.seek(max(0, size - 1_000_000))
            tail = f.read().decode("utf-8", "ignore").splitlines()
        for ln in tail:
            try: r = json.loads(ln)
            except Exception: continue
            if isinstance(r, dict) and "round" in r:
                rounds = r["round"]
            if r.get("type") == "TURN_SEAL":
                p = r.get("payload") or {}
                if p.get("state_hash"): fsh = p["state_hash"]
    except Exception:
        pass

workdir = meta.get("workdir") or ""
tree = ("copy" if "/tmp/t271-" in workdir
        else ("main" if workdir.rstrip("/").endswith("/code") else "unknown"))
mark = {
    "marker_version": "T374-1",
    "batch": meta.get("batch"),
    "unit": meta.get("unit"),
    "rc": int(rc) if str(rc).lstrip("-").isdigit() else rc,
    "started_at": started, "ended_at": ended,
    "heartbeat_first": hb_first, "heartbeat_last": hb_last,
    "rounds_last": rounds, "events": events,
    "final_state_hash": fsh,
    "tree": tree, "sha": meta.get("sha"), "workdir": workdir,
    "out": out, "host_log": os.path.join(rd, "host.log"),
    "ended_marker_path": endp,
}
json.dump(mark, open(endp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
# 固定告警路径（周期自检一眼可读）
json.dump(mark, open(os.path.join(adir, "last_end.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
with open(os.path.join(adir, "ends.log"), "a", encoding="utf-8") as f:
    f.write(f"{ended}\t{mark['batch']}\trc={mark['rc']}\trounds_last={rounds}\tevents={events}\t{endp}\n")
print(f"[END-MARKER] batch={mark['batch']} rc={mark['rc']} ended={ended} rounds_last={rounds} events={events} fsh={fsh} -> {endp}")
PY
# 尽力主动通知（best-effort，不影响批体）
logger -t t271-end "batch=${RUN_DIR##*/} rc=$RC end=$END" 2>/dev/null || true
