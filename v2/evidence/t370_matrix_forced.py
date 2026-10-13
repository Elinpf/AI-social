#!/usr/bin/env python3
"""T370 ④ 补强：受控-prop 2×2 矩阵（把"低功效"补成"有功效"）。

夹具：新增机制 `FESTIVALTEST`（kind=festival，place=hall，prob_bp=10000 ⇒ 每回合必发）
⇒ `world_director.propagate` 轴**真被激发**；再 × `time.ongoing` ⇒ 可测 X1 交互。
⚠️ 夹具只用于对照，**不改默认值**（默认仍 conservative）。
life 业态（build_world）；runtime config 覆盖；不写主树。
用法：python3 v2/evidence/t370_matrix_forced.py [n] [rounds] [seed]
"""
import os
import sys
import json
from collections import Counter

os.environ.setdefault("N50_VEC", "0")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "code"))

from orchestration.integration import build_world   # noqa: E402
from engine.runner import default_config            # noqa: E402
from engine.state import state_hash                 # noqa: E402

FAMS = ["PLACE_MOVE", "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "PERSONA_DRIFT",
        "PERSONA_DRIFT_CANDIDATE", "RELATION_CHANGE", "MSG_PUBLIC", "MSG_DM"]


def cell(ongoing, prop, n, rounds, seed):
    cfg = default_config()
    cfg.setdefault("world_director", {}).setdefault("mechanisms", {})["FESTIVALTEST"] = {
        "kind": "festival", "enabled": True, "place": "hall", "scope_level": "global",
        "dose": {"prob_bp": 10000, "capacity": 40, "slots": 3}}
    cfg["world_director"]["propagate"] = {"enabled": prop}
    cfg.setdefault("time", {}).setdefault("ongoing", {})["enabled"] = ongoing
    w = build_world(seed=seed, config=cfg, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    c = Counter(r.get("type") for r in eng.ledger.records)
    n_ev = sum(c.values())
    return {"n_events": n_ev, "state_hash": state_hash(eng.state),
            "families": {f: c.get(f, 0) for f in FAMS}}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    print(f"=== T370 受控-prop 矩阵 n={n} rounds={rounds} seed={seed} ===")
    cells = {"A0": cell(False, False, n, rounds, seed),
             "B": cell(False, True, n, rounds, seed),
             "C": cell(True, False, n, rounds, seed),
             "D": cell(True, True, n, rounds, seed)}
    for k in ["A0", "B", "C", "D"]:
        print(f"  {k}: n={cells[k]['n_events']} state_hash={cells[k]['state_hash']}")
    A0, B, C, D = (cells[k]["n_events"] for k in ["A0", "B", "C", "D"])
    print(f"  ongoing 效应: prop=off {C-A0:+d} ; prop=on {D-B:+d}")
    print(f"  prop    效应: ongoing=off {B-A0:+d} ; ongoing=on {D-C:+d}")
    print(f"  可加残差 D−C−B+A0 = {D-C-B+A0:+d} ; X1 = {(D-C)-(B-A0):+d}")
    print("  族 (A0,B,C,D):")
    for f in FAMS:
        g = [cells[k]["families"][f] for k in ["A0", "B", "C", "D"]]
        if len(set(g)) > 1:
            print(f"    {f:24s} {g}  残差={g[3]-g[2]-g[1]+g[0]:+d}")
    os.makedirs("/tmp/t370", exist_ok=True)
    json.dump({"cells": cells}, open("/tmp/t370/MATRIX_forced.json", "w"), ensure_ascii=False, indent=2)
    print("  -> /tmp/t370/MATRIX_forced.json")


if __name__ == "__main__":
    main()
