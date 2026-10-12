#!/usr/bin/env bash
# T271 回填 meta.json —— 批跑完后回填 engine_version 指纹与结束时刻（可溯性收尾）。
# 用法: finalize_meta.sh <run_dir>
set -euo pipefail
RUN_DIR="${1:?用法: finalize_meta.sh <run_dir>}"
python3 - "$RUN_DIR" <<'PY'
import json, os, sys
rd = sys.argv[1]
mp = os.path.join(rd, "meta.json")
m = json.load(open(mp, encoding="utf-8"))
fp = None
log = m.get("out")
if log and os.path.exists(log):
    with open(log, encoding="utf-8") as f:
        first = f.readline()
    try:
        r = json.loads(first)
        fp = (r.get("payload") or {}).get("fingerprint") or r.get("fingerprint")
    except Exception:
        pass
ended = None
hb = m.get("heartbeat_file")
if hb and os.path.exists(hb):
    lines = [l for l in open(hb, encoding="utf-8").read().splitlines() if l.strip()]
    if lines:
        ended = lines[-1].split("\t")[0]
m["engine_version_fingerprint"] = fp
m["ended_at"] = ended
json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("engine_version_fingerprint =", fp)
print("ended_at =", ended)
PY
