#!/usr/bin/env python3
"""update_manifest_hand.py — T107：把手绘资产接入 assets_manifest.json。

- `place.<id>` → `hand/buildings128/<id>.png`；`char.<id>` → `hand/chars/<id>.png`。
- 重算 size / sha256；保留 anchor / frames / category / type（尺寸未变）。
- **不新增 place id**：`residence_v2/v3` 作为「同一 place 的视觉变体」写入**顶层** `placeVariants`，
  由渲染层按 place id 哈希选择（config/places.json 与拓扑不变）。
- 其余条目（prop/tile/road/icon）不动。
用法：python tools/update_manifest_hand.py [--write] [--diff]
"""
from __future__ import annotations
import json, hashlib, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FROOT = os.path.dirname(HERE)
MAN = os.path.join(FROOT, "assets", "assets_manifest.json")

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()

def main():
    write = "--write" in sys.argv
    m = json.load(open(MAN))
    diff = []
    for e in m.get("assets", []):
        eid = e["id"]
        if eid.startswith("place."):
            base = eid[len("place."):]
            rel = f"hand/buildings128/{base}.png"
        elif eid.startswith("char."):
            base = eid[len("char."):]
            rel = f"hand/chars/{base}.png"
        else:
            continue
        ap = os.path.join(FROOT, "assets", rel)
        if not os.path.exists(ap):
            print("MISSING hand file:", rel); continue
        w, h = Image.open(ap).size
        old = e.get("file")
        e["file"] = rel
        e["size"] = [w, h]
        e["sha256"] = sha256(ap)
        diff.append((eid, old, rel, w, h, e["sha256"][:12]))
    # 顶层变体映射（不新增 place id）
    vdir = os.path.join(FROOT, "assets", "hand", "buildings128")
    variants = {}
    for f in sorted(os.listdir(vdir)):
        if f.endswith(".png") and "_v" in f:
            base = f.rsplit("_v", 1)[0]
            variants.setdefault(base, []).append("hand/buildings128/" + f)
    m["placeVariants"] = variants
    m["_handWired"] = "T107: place.*/char.* -> hand/ (variants via placeVariants; config place ids unchanged)"

    gen_refs = [e["id"] for e in m["assets"] if e.get("file", "").startswith("generated/buildings") or e.get("file", "").startswith("generated/characters")]
    hand_refs = [e["id"] for e in m["assets"] if e.get("file", "").startswith("hand/")]
    print(f"changed={len(diff)} hand_refs={len(hand_refs)} generated_buildings|characters_refs={len(gen_refs)}")
    print("placeVariants:", variants)
    if "--diff" in sys.argv or not write:
        for d in diff[:8]:
            print(" ", d[0], d[1], "->", d[2], d[3:5], d[5])
    if write:
        json.dump(m, open(MAN, "w"), ensure_ascii=False, indent=2)
        print("WROTE", MAN)

if __name__ == "__main__":
    main()
