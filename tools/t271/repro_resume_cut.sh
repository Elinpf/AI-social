#!/usr/bin/env bash
# 最小复现：native resume 与 oneshot 在【前缀 cut 点】处确定性分歧（cut 相关）。
#   cut=89 -> 一致;  cut=75 -> 分歧(state_hash 首个不等 = cut+1)
# 用法: repro_resume_cut.sh [CUT]        # 默认 75；再跑 CUT=89 对照
set -uo pipefail
BIN="$(cd "$(dirname "$0")" && pwd)"
REPO="${T271_REPO:-/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment}"
PY=/opt/openjiuwen/workswarm-venv/bin/python
SHA="${T271_REPRO_SHA:-$(git -C "$REPO" rev-parse HEAD)}"
CUT="${1:-75}"; ROUNDS=150; SEED=9; N=2; FLUSH=5
CO=/tmp/t271-repro          # 固定只读副本（从 SHA 建，避免活树漂移）
[ -d "$CO/code" ] || bash "$BIN/make_batch_copy.sh" repro "$SHA" >/dev/null 2>&1
[ -d "$CO/code" ] || { echo "副本缺失：$CO/code"; exit 2; }
P=/root/t271/runs/repro; S="$P/side"; rm -rf "$P"; mkdir -p "$S"
run(){ ( cd "$CO/code" && "$PY" -m orchestration run --life --seed "$SEED" --agents "$N" \
        --rounds "$ROUNDS" --out "$1" --side-root "$S" --flush-every "$FLUSH" ) ; }
echo "sha=$(git -C "$REPO" rev-parse --short "$SHA")  cut=$CUT"
run "$P/warm.jsonl" >/dev/null 2>&1          # 预热缓存
run "$P/ref.jsonl"  >/dev/null 2>&1          # 一次性基准
python3 - "$P/ref.jsonl" "$P/prefix.jsonl" "$CUT" <<'PY'
import sys, json
keep=[]
for l in open(sys.argv[1], encoding="utf-8"):
    keep.append(l); r=json.loads(l)
    if r.get("type")=="TURN_SEAL" and r.get("round")==int(sys.argv[3]): break
open(sys.argv[2], "w", encoding="utf-8").writelines(keep)
PY
for i in 1 2; do
  cp "$P/prefix.jsonl" "$P/run_$i.jsonl"
  ( cd "$CO/code" && "$PY" -m orchestration run --life --seed "$SEED" --agents "$N" --rounds "$ROUNDS" \
      --resume-from "$P/run_$i.jsonl" --target-round "$ROUNDS" --out "$P/run_$i.jsonl" \
      --side-root "$S" --flush-every "$FLUSH" ) >/dev/null 2>&1
done
s(){ python3 "$BIN/semantic_log_sha.py" "$1" | awk '{print $1}'; }
echo "oneshot sem_sha = $(s "$P/ref.jsonl")"
echo "resume1 sem_sha = $(s "$P/run_1.jsonl")"
echo "resume2 sem_sha = $(s "$P/run_2.jsonl")"
python3 - "$P/ref.jsonl" "$P/run_1.jsonl" <<'PY'
import sys, json
def seals(p):
    d={}
    for l in open(p, encoding="utf-8"):
        try: r=json.loads(l)
        except Exception: continue
        if r.get("type")=="TURN_SEAL": d[r.get("round")]=(r.get("payload") or {}).get("state_hash")
    return d
a,b=seals(sys.argv[1]),seals(sys.argv[2])
bad=sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k))
print(f"state_hash 不等数={len(bad)}  首个不等 round={bad[0] if bad else None}")
PY
echo "判决：resume1==resume2? $([ "$(s "$P/run_1.jsonl")" = "$(s "$P/run_2.jsonl")" ] && echo yes || echo no) ; ==oneshot? $([ "$(s "$P/run_1.jsonl")" = "$(s "$P/ref.jsonl")" ] && echo yes || echo no)"
echo "产物：$P/{prefix.jsonl,ref.jsonl,run_1.jsonl,run_2.jsonl}"
