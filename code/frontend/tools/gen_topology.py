#!/usr/bin/env python3
"""生成青溪镇拓扑 `config/topology.json`（确定性、可审计）。

权威依据：`v1.1/00-architecture.md` §2.3「中心–外围拓扑」。
    * plaza 为枢纽（ring 0）；
    * market / cafe / park / town_hall 环绕中心（ring 1）；
    * residence 位于外围带（ring 2）；
    * farm / gate 在最外围（ring 3）。
    * travel_ticks：相邻场所 = 1 tick，跨一个环层 = 2 ticks，最远 = 3 ticks；gate↔中心 = 3。

本脚本只做「环层 → 常数矩阵 + 渲染坐标」的纯函数展开，不引入任何随机/墙钟，
输出可直接 diff，保证可复现（ARP: AR-D2 建议落常数）。

用法（从 `code/` 运行）：
    python frontend/tools/gen_topology.py            # 写 config/topology.json
    python frontend/tools/gen_topology.py --print    # 只打印不落盘

输出同时写入：
    code/config/topology.json     （权威 config，供内核/生活层/前端共用）
    code/frontend/data/*.json     （前端离线 bundle 的副本）
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = Path(__file__).resolve().parents[1]

# 环层归属（§2.3，常量落定，保可复现）
RING_OF = {
    "plaza": 0,
    "market": 1, "cafe": 1, "park": 1, "town_hall": 1,
    "residence": 2, "bank": 2, "library": 2, "community_center": 2,
    "school": 2, "clinic": 2, "office": 2, "kitchen": 2, "workshop": 2, "hall": 2,
    "farm": 3, "gate": 3,
}

# 渲染半径（世界坐标，SVG/Pixi 均可直接用）
RADIUS = {0: 0, 1: 135, 2: 250, 3: 330}
CENTER = (480, 360)  # 960x720 世界坐标中心

# 每个环层的起始角度（度），让节点分布错开、避免重叠
START_ANGLE = {0: 0.0, 1: -90.0, 2: -108.0, 3: -90.0}


def _travel(a: int, b: int, ra: int, rb: int) -> int:
    if a == b:
        return 0
    d = abs(ra - rb)
    if d == 0:
        return 1          # 同环相邻
    if d == 1:
        return 2          # 跨一个环层
    return 3              # 最远（含 gate↔中心，ring 差 3）


def build(places: list[dict]) -> dict:
    ids = [p["place_id"] for p in places]
    by_ring: dict[int, list[str]] = {}
    for pid in ids:
        by_ring.setdefault(RING_OF[pid], []).append(pid)
    # 稳定顺序：环内保持 places.json 出现顺序
    for r in by_ring:
        by_ring[r].sort(key=lambda pid: ids.index(pid))

    nodes = []
    for pid in ids:
        r = RING_OF[pid]
        grp = by_ring[r]
        k = grp.index(pid)
        n = len(grp)
        ang = math.radians(START_ANGLE[r] + (360.0 * k / n if n else 0.0))
        x = CENTER[0] + RADIUS[r] * math.cos(ang)
        y = CENTER[1] + RADIUS[r] * math.sin(ang)
        nodes.append({
            "place_id": pid,
            "ring": r,
            "x": round(x, 2) if r else float(CENTER[0]),
            "y": round(y, 2) if r else float(CENTER[1]),
        })

    ring_of = {pid: RING_OF[pid] for pid in ids}
    matrix = {a: {b: _travel(a, b, ring_of[a], ring_of[b]) for b in ids} for a in ids}

    return {
        "schema_version": "1.1",
        "world": {"name_cn": "青溪镇", "width": 960, "height": 720},
        "ring_rule": "ring0=hub(plaza); ring1=环绕中心; ring2=外围带; ring3=最外围",
        "travel_rule": "same ring=1; ring diff 1=2; else=3; gate<->plaza=3",
        "nodes": nodes,
        "travel_ticks": matrix,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="do_print", action="store_true")
    args = ap.parse_args()

    places = json.loads((CODE_DIR / "config" / "places.json").read_text(encoding="utf-8"))["places"]
    topo = build(places)

    if args.do_print:
        print(json.dumps(topo, ensure_ascii=False, indent=2))
        return 0

    out1 = CODE_DIR / "config" / "topology.json"
    out2 = FRONTEND_DIR / "data" / "topology.json"
    for out in (out1, out2):
        out.write_text(json.dumps(topo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    n = len(topo["nodes"])
    # 对称性 / 三角不等式自检
    m = topo["travel_ticks"]
    assert all(m[a][b] == m[b][a] for a in m for b in m[a]), "travel 矩阵不对称"
    assert all(m[a][c] <= m[a][b] + m[b][c] for a in m for b in m[a] for c in m[a]), "违反三角不等式"
    print(f"ok: {n} nodes, matrix {n}x{n}, symmetric, triangle-inequality holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
