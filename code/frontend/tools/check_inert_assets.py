#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_inert_assets.py — 「睡着的资产」核对器（T258e）

类：一个资产/常量**已定义却零引用**（死帧 / 未接线素材）。
案例：grassLight 定义于 sprites.js，town.js 里曾定义 glight 却零使用（人眼发现）。
机械化：解析 sprites.js 的 TILES 常量表，统计每个 key 在 src/*.js 中的引用数；
0 引用 = INERT。输出 tools/inert_assets.json。
"""
import argparse, glob, json, os, re, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)

def parse_tiles(src_dir):
    sp=os.path.join(src_dir,"sprites.js")
    if not os.path.isfile(sp): return {}
    txt=open(sp,encoding="utf-8").read()
    keys={}
    for m in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(\[[^\]]*\]|\d+)\s*,?\s*(?=//|$)', txt, re.M):
        keys[m.group(1)]="sprites.js"
    return keys

def count_refs(src_dir, key):
    n=0
    for f in glob.glob(os.path.join(src_dir,"*.js")):
        n+=len(re.findall(r'\.'+re.escape(key)+r'\b', open(f,encoding="utf-8").read()))
    return n

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--src",default=os.path.join(ROOT,"src"))
    ap.add_argument("--warn-only",action="store_true"); a=ap.parse_args()
    tiles=parse_tiles(a.src); recs=[]; inert=[]
    for k in sorted(tiles):
        refs=count_refs(a.src,k); rec={"key":k,"refs":refs,"inert":refs==0}
        recs.append(rec)
        if refs==0: inert.append(rec)
    out={"scanned":len(recs),"inert":inert,"gate_pass":{"pass":len(inert)==0,"count":len(inert)}}
    json.dump(out, open(os.path.join(HERE,"inert_assets.json"),"w"), ensure_ascii=False, indent=2)
    print("[inert] 扫描 %d 个 TILES 常量；INERT(零引用)=%d" % (len(recs), len(inert)))
    for r in inert: print("  INERT:", r["key"])
    return 0 if (not inert or a.warn_only) else 1

if __name__=="__main__": sys.exit(main())
