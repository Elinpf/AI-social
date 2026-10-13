#!/usr/bin/env bash
# T370 ④ 独立复算：T355 2×2 消融矩阵（time.ongoing × world_director.propagate）。
# 非作者版：自建、走 run_override.py（runtime cfg 覆盖，文件不动 ⇒ 指纹不变）、同 sha、同 side 共享 cache。
# 规模小（判分离性）：N=8×24r seed=42（+可另 seed）。
set -euo pipefail
R=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
BASE=/root/t271/runs/t370_matrix
N="${N:-8}"; ROUNDS="${ROUNDS:-24}"; SEED="${SEED:-42}"; SIDE="${SIDE:-$BASE/side}"
mkdir -p "$BASE"
cd "$R/code"
run_cell () { # name ongoing prop
  local name=$1 og=$2 prop=$3
  echo "[t370-matrix] cell=$name ongoing=$og propagate=$prop"
  python3 "$R/tools/t271/run_override.py" --seed "$SEED" --agents "$N" --rounds "$ROUNDS" \
    --out "$BASE/${name}.jsonl" --side-root "$SIDE" --flush-every 2 \
    --override "time.ongoing.enabled=${og}" \
    --override "world_director.propagate.enabled=${prop}" > "$BASE/${name}.log" 2>&1
}
run_cell A_off_off false false
run_cell B_off_on  false true
run_cell C_on_off  true  false
run_cell D_on_on   true  true
echo "[t370-matrix] done -> $BASE/{A_off_off,B_off_on,C_on_off,D_on_on}.jsonl"
