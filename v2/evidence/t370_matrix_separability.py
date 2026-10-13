#!/usr/bin/env python3
"""T370 非作者独立核：T355 收口 —— ④ 2×2 消融矩阵可分离性（只读）。

给定 4 格 `time.ongoing ∈ {off,on}` × `world_director.propagate ∈ {off,on}`：
  A0=(off,off)  B=(off,on)  C=(on,off)  D=(on,on)
判据（leader 写死）：**可分离 = 可加**（`D − C − B + A0 ≈ 0`）；存在显著交互项 X1 ⇒ **不可分离 ⇒ 退回"一期一冻"**。
X1 = (D − C) − (B − A0)   （propagate 的效应在 ongoing 开/关下的差）。

用法：python3 v2/evidence/t370_matrix_separability.py MATRIX.json
MATRIX.json：{"cells": {"A0":{"n_events":..,"state_hash":"..","families":{...}}, "B":{...}, "C":{...}, "D":{...}}}
（fields: n_events / state_hash / families 可选）
"""
import sys
import json
import os

TOL = int(os.environ.get("T370_TOL", "0"))   # 计数残差容差（默认严格 0）


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        print("PENDING: 未提供 MATRIX.json（T355 矩阵未产出）")
        return 2
    m = json.load(open(sys.argv[1]))
    c = m["cells"]
    need = ["A0", "B", "C", "D"]
    for k in need:
        if k not in c:
            print(f"PENDING: 缺格 {k}")
            return 2

    def n( k):
        return c[k].get("n_events")

    print("=== 2×2 矩阵可分离性 ===")
    for k in need:
        print(f"  {k}: n_events={c[k].get('n_events')} state_hash={c[k].get('state_hash')}")

    # 主效应 + 交互（n_events）
    if all(n(k) is not None for k in need):
        A0, B, C, D = (n(k) for k in need)
        eff_ong_off = C - A0      # ongoing 在 prop=off 的效应
        eff_ong_on = D - B        # ongoing 在 prop=on 的效应
        eff_prop_off = B - A0     # prop 在 ongoing=off 的效应
        eff_prop_on = D - C       # prop 在 ongoing=on 的效应
        X1 = eff_ong_on - eff_ong_off
        resid = D - C - B + A0
        print(f"\n  ongoing 效应: prop=off {eff_ong_off:+d} ; prop=on {eff_ong_on:+d}")
        print(f"  prop    效应: ongoing=off {eff_prop_off:+d} ; ongoing=on {eff_prop_on:+d}")
        print(f"  可加残差 D−C−B+A0 = {resid:+d} ; 交互项 X1 = {X1:+d} (tol={TOL})")
        sep = abs(resid) <= TOL
        print(f"  ⇒ 可分离: {'是（可加）' if sep else '否（存在交互）'}")
    else:
        print("  （cells 未提供 n_events，跳过数值判据）")

    # state_hash 关系（辅助）
    sh = {k: c[k].get("state_hash") for k in need}
    if all(sh.values()):
        eqs = []
        for a, b in [("A0", "B"), ("A0", "C"), ("C", "D"), ("B", "D")]:
            eqs.append(f"{a}=={b}: {sh[a]==sh[b]}")
        print("  state_hash 关系:", "; ".join(eqs))

    # 族级残差（若给 families）
    if all(c[k].get("families") for k in need):
        fams = sorted(set().union(*[set(c[k]["families"]) for k in need]))
        print("\n  族级 可加残差 D−C−B+A0（非零才列）:")
        anynz = False
        for f in fams:
            g = [c[k]["families"].get(f, 0) for k in need]  # A0,B,C,D
            r = g[3] - g[2] - g[1] + g[0]
            if r:
                anynz = True
                print(f"    {f:28s} A0={g[0]} B={g[1]} C={g[2]} D={g[3]} 残差={r:+d}")
        if not anynz:
            print("    （全 0）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
