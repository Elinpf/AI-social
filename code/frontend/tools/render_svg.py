#!/usr/bin/env python3
"""render_svg.py — 静态帧 SVG 导出器（无浏览器依赖）。

从「事件日志(JSONL) + config/places.json + config/topology.json」渲染**指定回合 N**
的小镇快照为一张**自包含** SVG（内联样式、无外部依赖/图片/字体）。

纪律：只读日志/config；数据全部来自确定性日志，可复现；不引入外部素材。
配色复用前端 Pixi 的类别常量（`src/sprites.js`），保持两套渲染口径一致。

命令行：
    cd code
    python frontend/tools/render_svg.py --log frontend/sample/demo_run.jsonl \
        --round 12 --out /tmp/qingxi_r12.svg

参数：
    --log    事件日志 JSONL（engine 或 life 产出，格式一致）
    --round  目标回合 N（快照为「回合 N 结束时」的状态）
    --places 默认 config/places.json
    --topo   默认 config/topology.json
    --out    输出 SVG 路径
    --title  可选，覆盖标题前缀（默认「青溪镇」）
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[2]

# ---- 类别配色 / 中文名（与 src/sprites.js CATEGORY_STYLE 对齐）----
CATEGORY_STYLE = {
    "living":          ("居住", "#b07a52", "#7a4a2b"),
    "work_production": ("生产", "#5f9e56", "#3f6f3a"),
    "work_processing": ("加工", "#4fa39a", "#2f6f69"),
    "work_service":    ("服务", "#5b86c4", "#35578a"),
    "work_education":  ("教育", "#8a6fc0", "#5a468a"),
    "work_admin":      ("行政", "#7b8794", "#525c66"),
    "trade":           ("交易", "#c9a13f", "#8f6f1f"),
    "public":          ("公共", "#62a0a8", "#3d7078"),
    "leisure":         ("娱乐", "#c86f9b", "#8f4569"),
    "edge":            ("边缘", "#6b6f76", "#44474c"),
}
AGENT_COLORS = ["#5cc8ff", "#ffcf5c", "#5ddc82", "#ff8f6b", "#c08bff",
                "#66e0c0", "#ff7fb0", "#9ad0ff", "#d6e05c", "#ffa04d",
                "#8be0a0", "#e0b0ff", "#6bd0e0", "#ffc0c0", "#a0e0ff",
                "#f0d060", "#90d090", "#d090f0", "#70c0f0", "#f0a0a0"]


# ---------------------------------------------------------------- log 折叠
def _num(v):
    return v if isinstance(v, (int, float)) else 0


def fold_until(records: list[dict], target_round: int) -> dict:
    """折叠 round ≤ target_round 的事件，返回 {agents, last_time, last_hash, round_seen}。"""
    agents: dict[str, dict] = {}
    last_time = None
    last_hash = None

    def bump(aid: str) -> dict:
        if aid not in agents:
            agents[aid] = {"location": "residence", "status": "alive", "money": 0, "activity": None}
        return agents[aid]

    for ev in records:
        rd = ev.get("round", 0) or 0
        if rd > target_round:
            continue
        p = ev.get("payload", {}) or {}
        t = ev.get("type")
        if ev.get("hash"):
            last_hash = ev["hash"]
        if t == "AGENT_BORN":
            a = bump(p["agent_id"]); a["location"] = p.get("home_place", "residence")
        elif t == "PLACE_MOVE":
            bump(p["agent_id"])["location"] = p.get("to_place") or p.get("place") or bump(p["agent_id"])["location"]
        elif t == "PLACE_ARRIVED":
            bump(p["agent_id"])["location"] = p.get("place") or bump(p["agent_id"])["location"]
        elif t == "ACTIVITY_STARTED":
            bump(p["agent_id"])["activity"] = p.get("activity_type")
        elif t in ("ACTIVITY_COMPLETED", "ACTIVITY_INTERRUPTED"):
            bump(p["agent_id"])["activity"] = None
        elif t == "AGENT_DIED":
            bump(p["agent_id"])["status"] = "dead"; bump(p["agent_id"])["activity"] = None
        elif t == "AGENT_REVIVED":
            bump(p["agent_id"])["status"] = "alive"
        elif t == "STATE_CHANGE":
            a = bump(p.get("agent_id") or ev.get("actor") or "")
            if isinstance(p.get("to"), str):
                a["status"] = p["to"]
            if p.get("status"):
                a["status"] = p["status"]
        elif t == "TIME_MARK":
            last_time = p
        # 货币
        money = {"INIT_ENDOW": ("agent_id", "amount", +1), "TAX_LEVIED": ("agent_id", "amount", -1),
                 "UBI_PAID": ("agent_id", "amount", +1), "METABOLISM": ("agent_id", "amount", -1),
                 "PENALTY_APPLIED": ("agent_id", "amount", -1), "REVIVE_FEE_PAID": ("agent_id", "amount", -1),
                 "DEPOSIT": ("agent_id", "amount", -1), "WITHDRAW": ("agent_id", "amount", +1),
                 "INTEREST_PAID": ("agent_id", "amount", +1)}
        if t in money:
            aid, af, sign = money[t]
            bump(p[aid])["money"] += sign * _num(p.get(af))
        elif t in ("TRANSFER", "MARKET_TRADE"):
            f, to = ("from", "to") if t == "TRANSFER" else ("buyer", "seller")
            amt = p.get("amount") if t == "TRANSFER" else p.get("price")
            if p.get(f) and p.get(to):
                bump(p[f])["money"] -= _num(amt)
                bump(p[to])["money"] += _num(amt)
    return {"agents": agents, "last_time": last_time, "last_hash": last_hash}


# ---------------------------------------------------------------- SVG 生成
def esc(s) -> str:
    return html.escape(str(s), quote=True)


# ---- 挂钟时间（纯展示口径；引擎内部为抽象 tick：12 tick/日、84 tick/周）----
def wall_clock(round_no: int) -> dict:
    r = round_no % 12
    day = round_no // 12
    hour = (6 + r * 2) % 24
    names = ["早晨", "午后", "傍晚", "夜里"]
    return {"day": day + 1, "hour": hour, "hhmm": f"{hour:02d}:00", "slotName": names[r // 3]}


# ---- 地形 tile 网格（与前端 town.js 同规则，确定性）----
TILE = 32

def _h2(x, y, salt):
    n = (x * 374761393 + y * 668265263 + salt * 2246822519) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n = (n ^ (n >> 16)) & 0xFFFFFFFF
    return n / 4294967296

def tile_kind_grid(nodes, W, H):
    cols = (W + TILE - 1) // TILE
    rows = (H + TILE - 1) // TILE
    kind = [[0] * cols for _ in range(rows)]

    def mark(tx, ty, k):
        if 0 <= ty < rows and 0 <= tx < cols:
            kind[ty][tx] = k

    hub = nodes.get("plaza") or {"x": W / 2, "y": H / 2}
    hx, hy = int(hub["x"] // TILE), int(hub["y"] // TILE)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dx * dx + dy * dy <= 5:
                mark(hx + dx, hy + dy, 1)
    for pid, n in nodes.items():
        if pid == "plaza":
            continue
        tx, ty = int(n["x"] // TILE), int(n["y"] // TILE)
        for x in range(min(hx, tx), max(hx, tx) + 1):
            mark(x, hy, 1)
        for y in range(min(hy, ty), max(hy, ty) + 1):
            mark(tx, y, 1)
    park = nodes.get("park")
    if park:
        cx, cy = int(park["x"] // TILE) - 3, int(park["y"] // TILE) + 3
        for dy in range(-1, 2):
            for dx in range(-2, 3):
                if abs(dx) + abs(dy) <= 3:
                    mark(cx + dx, cy + dy, 2)
    farm = nodes.get("farm")
    if farm:
        fx, fy = int(farm["x"] // TILE) + 1, int(farm["y"] // TILE) + 2
        for dy in range(3):
            for dx in range(4):
                mark(fx + dx, fy + dy, 3)
    return kind, cols, rows


def _dist_pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def _layout_terrain(out, layout, world_top, nodes):
    """按前端布局 layout.json（T71）绘制地形：草地/道路/河/塘/农田 + 程序化装饰。"""
    W = layout["world"]["width"]
    H = layout["world"]["height"]
    out.append('<g class="terrain">')
    out.append(f'<rect x="0" y="{world_top}" width="{W}" height="{H}" fill="#5c792d"/>')
    # 草地色块（确定性变体）
    for ty in range(H // 48 + 1):
        for tx in range(W // 48 + 1):
            r = _h2(tx, ty, 1)
            if r > 0.55:
                out.append(f'<rect x="{tx*48}" y="{world_top+ty*48}" width="48" height="48" fill="#638230" opacity="0.45"/>')
            elif r < 0.22:
                out.append(f'<rect x="{tx*48}" y="{world_top+ty*48}" width="48" height="48" fill="#557026" opacity="0.45"/>')

    # 农田
    for fp in layout.get("farm_plots", []):
        x, y, w, h = fp["x"], fp["y"] + world_top, fp["w"], fp["h"]
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#6b5a2f" stroke="#4e421f" stroke-width="3"/>')
        yy = int(y + 10)
        while yy < y + h - 6:
            out.append(f'<rect x="{x+6}" y="{yy}" width="{w-12}" height="5" fill="#4e421f" opacity="0.65"/>')
            yy += 18

    # 河（polyline，half 半宽）
    rv = layout.get("river")
    river_segs = []
    if rv and rv.get("pts"):
        pts = [(float(p[0]), float(p[1])) for p in rv["pts"]]
        half = float(rv.get("half", 16))
        d = " ".join(f"{'M' if i == 0 else 'L'}{x:.0f},{world_top + y:.0f}" for i, (x, y) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="#1d4c5c" stroke-width="{half*2:.0f}" stroke-linejoin="round" stroke-linecap="round"/>')
        out.append(f'<path d="{d}" fill="none" stroke="#215a6c" stroke-width="{half:.0f}" stroke-linejoin="round" stroke-linecap="round" opacity="0.55"/>')
        for i in range(len(pts) - 1):
            river_segs.append((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]))

    # 塘
    pd = layout.get("pond")
    if pd:
        cx, cy, rx, ry = float(pd["x"]), float(pd["y"]) + world_top, float(pd["rx"]), float(pd["ry"])
        out.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="#1d4c5c"/>')
        out.append(f'<ellipse cx="{cx:.0f}" cy="{cy - ry*0.28:.0f}" rx="{rx*0.6:.0f}" ry="{ry*0.22:.0f}" fill="#215a6c" opacity="0.7"/>')

    # 道路
    road_segs = []
    for rd in layout.get("roads", []):
        ax, ay = float(rd["a"][0]), float(rd["a"][1])
        bx, by = float(rd["b"][0]), float(rd["b"][1])
        wpx = float(rd.get("w", 3)) * 16.0
        mat = rd.get("material", "street")
        col = {"street": "#8a7440", "path": "#7d6838", "bridge": "#9a7b4a"}.get(mat, "#8a7440")
        out.append(f'<line x1="{ax:.0f}" y1="{world_top+ay:.0f}" x2="{bx:.0f}" y2="{world_top+by:.0f}" '
                   f'stroke="{col}" stroke-width="{wpx:.0f}" stroke-linecap="round"/>')
        out.append(f'<line x1="{ax:.0f}" y1="{world_top+ay:.0f}" x2="{bx:.0f}" y2="{world_top+by:.0f}" '
                   f'stroke="#000000" stroke-width="{max(2, wpx*0.12):.0f}" opacity="0.10"/>')
        road_segs.append((ax, ay, bx, by))

    out.append("</g>")

    # 装饰（避让场所/道路/河）
    place_r = 78 * 0.62 + 22
    segs = road_segs + river_segs
    out.append('<g class="decor">')
    for ty in range(H // TILE + 1):
        for tx in range(W // TILE + 1):
            cx = tx * TILE + TILE / 2
            cy = ty * TILE + TILE / 2
            if any((n["x"] - cx) ** 2 + (n["y"] - cy) ** 2 <= place_r * place_r for n in nodes.values()):
                continue
            if any(_dist_pt_seg(cx, cy, *s) < 34 for s in segs):
                continue
            if _h2(tx, ty, 99) > 0.30:
                continue
            t = _h2(tx, ty, 7)
            yb = world_top + cy + TILE / 2
            if t < 0.5:
                out.append(f'<rect x="{cx-2:.0f}" y="{yb-8:.0f}" width="4" height="9" fill="#6b4a26"/>')
                out.append(f'<circle cx="{cx:.0f}" cy="{yb-16:.0f}" r="9" fill="#2f5a20"/>')
                out.append(f'<circle cx="{cx-3:.0f}" cy="{yb-19:.0f}" r="6" fill="#3d7229"/>')
            elif t < 0.72:
                out.append(f'<circle cx="{cx:.0f}" cy="{yb-5:.0f}" r="6" fill="#356022"/>')
            elif t < 0.86:
                out.append(f'<rect x="{cx-1:.0f}" y="{yb-6:.0f}" width="2" height="6" fill="#3d7229"/>')
                out.append(f'<circle cx="{cx:.0f}" cy="{yb-8:.0f}" r="3" fill="#e0d24a"/>')
            else:
                out.append(f'<ellipse cx="{cx:.0f}" cy="{yb-4:.0f}" rx="7" ry="5" fill="#8a8f98"/>')
    out.append("</g>")


def build_svg(log_path: Path, target_round: int, places: list, topo: dict,
              agents: dict, last_time: dict | None, last_hash: str | None,
              title_prefix: str = "青溪镇", layout: dict | None = None) -> str:
    # 优先用前端布局（T71，art-director 的 LAYOUT → frontend/data/layout.json）对齐 Pixi 视图；
    # 无 layout 时回退到 config/topology.json（旧口径）。
    if layout:
        nodes = {n["place_id"]: n for n in layout["nodes"]}
        W, H = layout["world"]["width"], layout["world"]["height"]
    else:
        nodes = {n["place_id"]: n for n in topo["nodes"]}
        W, H = topo["world"]["width"], topo["world"]["height"]
    HEAD, FOOT = 84, 92
    svg_w, svg_h = W, H + HEAD + FOOT

    # 标题：挂钟时间（1 tick = 2h，纯展示口径）
    wc = wall_clock(target_round)
    title = f"{title_prefix} · 第 {wc['day']} 日 {wc['hhmm']}（{wc['slotName']}）"
    if last_time:
        sub = f"round {target_round} · week {last_time.get('week')}, {last_time.get('day_type')} · 时段 {last_time.get('slot')}"
    else:
        sub = f"round {target_round} · 1 tick = 2h（展示口径，引擎单位为抽象 tick）"

    log_name = log_path.name
    log_hash = hashlib.sha256(log_path.read_bytes()).hexdigest()[:16]
    short_last = (last_hash or "")[:26] if last_hash else "—"

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
               f'viewBox="0 0 {svg_w} {svg_h}" font-family="\'Noto Serif CJK SC\',\'Noto Sans CJK SC\',\'Source Han Sans SC\',\'Noto Sans SC\',\'PingFang SC\',\'Microsoft YaHei\',\'WenQuanYi Zen Hei\',sans-serif">')
    # 内联样式（自包含，无外部字体/图片）
    out.append(
        "<style>"
        ".bg{fill:#22331f}.frame{fill:#14181f}"
        ".ring{fill:none;stroke:#33502f;stroke-width:1}"
        ".hub{stroke:#2f4a2c;stroke-width:2}"
        ".place rect.wall{stroke:#1a1f26;stroke-width:2}"
        ".place text.name{fill:#ffffff;stroke:#0b0e12;stroke-width:3;paint-order:stroke;font-size:13px;text-anchor:middle}"
        ".place text.cap{fill:#8b98ab;stroke:#0b0e12;stroke-width:2;paint-order:stroke;font-size:10px;text-anchor:middle;font-family:monospace}"
        ".agent text.id{fill:#ffffff;stroke:#0b0e12;stroke-width:3;paint-order:stroke;font-size:10px;text-anchor:middle;font-family:monospace}"
        ".title{fill:#e6ebf2;font-size:20px;font-weight:700}"
        ".subtitle{fill:#8b98ab;font-size:12px}"
        ".legend .lt{fill:#8b98ab;font-size:11px}"
        ".legend .ll{fill:#e6ebf2;font-size:12px}"
        ".footer{fill:#8b98ab;font-size:11px;font-family:monospace}"
        "</style>"
    )
    # 背景
    out.append(f'<rect class="frame" x="0" y="0" width="{svg_w}" height="{svg_h}"/>')
    out.append(f'<rect class="bg" x="0" y="{HEAD}" width="{W}" height="{H}"/>')
    # 标题
    out.append(f'<text class="title" x="24" y="38">{esc(title)}</text>')
    out.append(f'<text class="subtitle" x="24" y="60">{esc(sub)}</text>')

    world_top = HEAD
    if layout:
        _layout_terrain(out, layout, world_top, nodes)
        kind, cols, rows = [], 0, 0     # 跳过旧 tile 地形/装饰循环
    else:
        kind, cols, rows = tile_kind_grid(nodes, W, H)

    # ---- 地形（tilemap：草地 / 土路 / 水塘 / 农田）----
    COL = {0: ("#5c792d", "#638230", "#557026"),   # grass（含变体）
           1: ("#8a7440", "#7d6838"),               # dirt / road（较亮的土黄，区分草地）
           2: ("#1d4c5c", "#215a6c"),               # water
           3: ("#6b5a2f", "#5d4e28")}               # farmland soil
    out.append('<g class="terrain">')
    for ty in range(rows):
        for tx in range(cols):
            k = kind[ty][tx]
            pal = COL[k]
            r = _h2(tx, ty, k + 1)
            fill = pal[0] if len(pal) == 1 else pal[1:][int(r * (len(pal) - 1)) % (len(pal) - 1)]
            out.append(f'<rect x="{tx*TILE}" y="{world_top+ty*TILE}" width="{TILE}" height="{TILE}" fill="{fill}"/>')
    # 水塘波纹
    for ty in range(rows):
        for tx in range(cols):
            if kind[ty][tx] == 2:
                out.append(f'<rect x="{tx*TILE+6}" y="{world_top+ty*TILE+9}" width="{TILE-12}" height="2" fill="#8fd3e6" opacity="0.5"/>')
                out.append(f'<rect x="{tx*TILE+10}" y="{world_top+ty*TILE+20}" width="{TILE-16}" height="2" fill="#8fd3e6" opacity="0.35"/>')
    # 农田垄沟
    for ty in range(rows):
        for tx in range(cols):
            if kind[ty][tx] == 3:
                out.append(f'<rect x="{tx*TILE+3}" y="{world_top+ty*TILE+12}" width="{TILE-6}" height="3" fill="#4e421f" opacity="0.7"/>')
    out.append("</g>")

    # ---- 装饰（树 / 灌木 / 石 / 花；确定性摆放，避让场所）----
    place_r = 78 * 0.62
    nodes_list = list(nodes.values())
    def far_from_places(px, py):
        return all((n["x"] - px) ** 2 + (n["y"] - py) ** 2 > place_r * place_r for n in nodes_list)
    out.append('<g class="decor">')
    for ty in range(rows):
        for tx in range(cols):
            if kind[ty][tx] != 0:
                continue
            cx = tx * TILE + TILE / 2
            cy = ty * TILE + TILE / 2
            if not far_from_places(cx, cy):
                continue
            if _h2(tx, ty, 99) > 0.34:
                continue
            t = _h2(tx, ty, 7)
            yb = world_top + cy + TILE / 2
            if t < 0.5:      # 树
                out.append(f'<rect x="{cx-2:.0f}" y="{yb-8:.0f}" width="4" height="9" fill="#6b4a26"/>')
                out.append(f'<circle cx="{cx:.0f}" cy="{yb-16:.0f}" r="9" fill="#2f5a20"/>')
                out.append(f'<circle cx="{cx-3:.0f}" cy="{yb-19:.0f}" r="6" fill="#3d7229"/>')
            elif t < 0.72:   # 灌木
                out.append(f'<circle cx="{cx:.0f}" cy="{yb-5:.0f}" r="6" fill="#356022"/>')
            elif t < 0.86:   # 花
                out.append(f'<rect x="{cx-1:.0f}" y="{yb-6:.0f}" width="2" height="6" fill="#3d7229"/>')
                out.append(f'<circle cx="{cx:.0f}" cy="{yb-8:.0f}" r="3" fill="#e0d24a"/>')
            else:            # 石
                out.append(f'<ellipse cx="{cx:.0f}" cy="{yb-4:.0f}" rx="7" ry="5" fill="#8a8f98"/>')
                out.append(f'<ellipse cx="{cx-2:.0f}" cy="{yb-6:.0f}" rx="3" ry="2" fill="#a7adb5"/>')
    out.append("</g>")

    # 场所
    S, HT = 78, 78 * 0.72
    for p in places:
        n = nodes.get(p["place_id"])
        if not n:
            continue
        cn, wall, roof = CATEGORY_STYLE.get(p["category"], CATEGORY_STYLE["work_admin"])
        x, y = n["x"], world_top + n["y"]
        x0, y0 = x - S / 2, y - HT / 2
        out.append(f'<g class="place" data-place="{esc(p["place_id"])}" data-category="{esc(p["category"])}" '
                   f'data-ring="{n.get("ring")}">')
        out.append(f'<rect x="{x0-7:.1f}" y="{y0+8:.1f}" width="{S+14}" height="{HT+16:.1f}" rx="9" fill="#1c2a1a" opacity="0.5"/>')
        out.append(f'<rect class="wall" x="{x0:.1f}" y="{y0+12:.1f}" width="{S}" height="{HT-12:.1f}" fill="{wall}"/>')
        # 墙体横纹（像素质感）
        for wy in (y0 + 24, y0 + 38):
            out.append(f'<rect x="{x0:.1f}" y="{wy:.1f}" width="{S}" height="2" fill="#000000" opacity="0.14"/>')
        out.append(f'<rect x="{x0-7:.1f}" y="{y0+3:.1f}" width="{S+14}" height="15" fill="{roof}"/>')
        out.append(f'<rect x="{x0+5:.1f}" y="{y0-8:.1f}" width="{S-10}" height="13" fill="{roof}"/>')
        # 屋顶瓦纹
        for rx in range(int(x0 - 4), int(x0 + S + 4), 8):
            out.append(f'<rect x="{rx:.0f}" y="{y0+3:.0f}" width="2" height="15" fill="#000000" opacity="0.12"/>')
        out.append(f'<rect x="{x0+12:.1f}" y="{y0+32:.1f}" width="15" height="13" fill="#ffe08a" stroke="#3a2f16" stroke-width="2"/>')
        out.append(f'<rect x="{x0+S-27:.1f}" y="{y0+32:.1f}" width="15" height="13" fill="#ffe08a" stroke="#3a2f16" stroke-width="2"/>')
        out.append(f'<rect x="{x0+S/2-9:.1f}" y="{y0+HT-15:.1f}" width="18" height="23" fill="{roof}" stroke="#241a12" stroke-width="2"/>')
        name = p.get("name_cn", p["place_id"])
        nw = max(46, len(str(name)) * 13 * 0.66 + 12)
        out.append(f'<rect x="{x-nw/2:.1f}" y="{y+HT/2+2:.1f}" width="{nw:.1f}" height="17" rx="4" fill="#11170d" opacity="0.72"/>')
        out.append(f'<text class="name" x="{x:.1f}" y="{y+HT/2+15:.1f}">{esc(name)}</text>')
        cap = f'{p["category"]} · 容量 {p.get("capacity")}'
        cw = max(60, len(cap) * 10 * 0.62 + 10)
        out.append(f'<rect x="{x-cw/2:.1f}" y="{y+HT/2+19:.1f}" width="{cw:.1f}" height="13" rx="3" fill="#11170d" opacity="0.6"/>')
        out.append(f'<text class="cap" x="{x:.1f}" y="{y+HT/2+31:.1f}">{esc(cap)}</text>')
        out.append("</g>")

    # Agent：先按场所分组做网格偏移
    by_place: dict[str, list] = {}
    for aid in sorted(agents.keys()):
        by_place.setdefault(agents[aid]["location"] or "residence", []).append(aid)
    agent_idx = {aid: i for i, aid in enumerate(sorted(agents.keys()))}
    for loc, ids in by_place.items():
        n = nodes.get(loc) or nodes.get("residence")
        cols = max(1, int(len(ids) ** 0.5 + 0.999))
        for i, aid in enumerate(ids):
            a = agents[aid]
            ox = ((i % cols) - (cols - 1) / 2) * 26
            oy = ((i // cols) - (len(ids) / cols - 1) / 2) * 30 - 34
            cx, cy = n["x"] + ox, world_top + n["y"] + oy
            dead = a["status"] == "dead"
            color = "#8a8f98" if dead else AGENT_COLORS[agent_idx[aid] % len(AGENT_COLORS)]
            out.append(f'<g class="agent" data-agent="{esc(aid)}" data-status="{esc(a["status"])}" data-place="{esc(loc)}">')
            out.append(f'<ellipse cx="{cx:.1f}" cy="{cy+16:.1f}" rx="10" ry="4" fill="#000000" opacity="0.28"/>')   # 影
            out.append(f'<rect x="{cx-6:.1f}" y="{cy-4:.1f}" width="12" height="15" fill="{color}"/>')              # 躯干
            out.append(f'<rect x="{cx-9:.1f}" y="{cy-3:.1f}" width="3" height="10" fill="{color}"/>')               # 左臂
            out.append(f'<rect x="{cx+6:.1f}" y="{cy-3:.1f}" width="3" height="10" fill="{color}"/>')               # 右臂
            out.append(f'<rect x="{cx-5:.1f}" y="{cy+11:.1f}" width="4" height="6" fill="#3a3226"/>')               # 腿
            out.append(f'<rect x="{cx+1:.1f}" y="{cy+11:.1f}" width="4" height="6" fill="#3a3226"/>')
            out.append(f'<rect x="{cx-5:.1f}" y="{cy-15:.1f}" width="10" height="11" fill="#f2c9a0"/>')             # 头
            out.append(f'<rect x="{cx-5:.1f}" y="{cy-15:.1f}" width="10" height="4" fill="#5a4028"/>')              # 发
            if dead:
                out.append(f'<rect x="{cx-3:.1f}" y="{cy-11:.1f}" width="2" height="2" fill="#c0392b"/>')
                out.append(f'<rect x="{cx+1:.1f}" y="{cy-11:.1f}" width="2" height="2" fill="#c0392b"/>')
            tag = aid + ("·亡" if dead else "")
            out.append(f'<text class="id" x="{cx:.1f}" y="{cy+30:.1f}">{esc(tag)}</text>')
            out.append("</g>")

    # 图例（去重的类别）
    lx, ly = 24, HEAD + H + 20
    out.append('<g class="legend">')
    out.append(f'<text class="lt" x="{lx}" y="{ly}">场所类别：</text>')
    used = []
    for p in places:
        c = p["category"]
        if c not in used:
            used.append(c)
    xx = lx + 76
    for c in used:
        cn, wall, _ = CATEGORY_STYLE.get(c, CATEGORY_STYLE["work_admin"])
        out.append(f'<rect x="{xx}" y="{ly-9}" width="11" height="11" rx="2" fill="{wall}"/>')
        out.append(f'<text class="ll" x="{xx+16}" y="{ly}">{esc(cn)}</text>')
        xx += 16 + 14 * len(cn) + 22
    out.append("</g>")

    # 页脚：数据来源（确定性重绘声明）
    out.append('<g class="footer">')
    out.append(f'<text x="24" y="{svg_h-30}">数据来源（确定性日志重绘）: {esc(log_name)}</text>')
    out.append(f'<text x="24" y="{svg_h-14}">log_hash=sha256:{esc(log_hash)}…  末哈希={esc(short_last)}  rendersvg=v1  (只读日志/config；可复现)</text>')
    out.append("</g>")

    out.append("</svg>")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="静态帧 SVG 导出（无浏览器）")
    ap.add_argument("--log", required=True)
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--places", default=str(CODE_DIR / "config" / "places.json"))
    ap.add_argument("--topo", default=str(CODE_DIR / "config" / "topology.json"))
    ap.add_argument("--layout", default=str(Path(__file__).resolve().parents[1] / "data" / "layout.json"),
                    help="前端布局 layout.json（T71）；存在则优先读它对齐 Pixi 视图，否则回退 --topo")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="青溪镇")
    args = ap.parse_args()

    log_path = Path(args.log).expanduser().resolve()
    if not log_path.exists():
        print(f"日志不存在: {log_path}", file=sys.stderr)
        return 2
    places = json.loads(Path(args.places).read_text(encoding="utf-8"))["places"]
    topo = json.loads(Path(args.topo).read_text(encoding="utf-8"))
    layout = None
    lp = Path(args.layout)
    if lp.exists():
        try:
            layout = json.loads(lp.read_text(encoding="utf-8"))
            if layout.get("schema") != "hitt.layout/1":
                print(f"警告：layout schema 非 hitt.layout/1（{layout.get('schema')}），仍尝试读取", file=sys.stderr)
        except Exception as e:
            print(f"警告：读取 layout 失败，回退 topology：{e}", file=sys.stderr)
            layout = None
    records = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    max_round = max((r.get("round", 0) or 0) for r in records) if records else 0
    target = min(args.round, max_round)
    folded = fold_until(records, target)

    svg = build_svg(log_path, target, places, topo, folded["agents"], folded["last_time"],
                    folded["last_hash"], args.title, layout=layout)
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out}  round={target}/{max_round} places={len(places)} agents={len(folded['agents'])} bytes={len(svg)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
