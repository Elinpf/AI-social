#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""char_game_size_check.py — 角色「游戏尺寸」两两剪影可辨性（T258 续作）

判据在**真实观看尺寸**下成立（非放大镜下）：把 8 角色帧缩放到目标显示高度（默认 34px，
与游戏内 ~0.46 缩放一致），逐对算剪影 **IoU**；全部 < 阈值（默认 0.95）→ PASS。
输出 `char_game_size.json`（含 gate_pass）。
用法：python3 frontend/tools/char_game_size_check.py [--height 34] [--threshold 0.95]
"""
import argparse, json, os, sys
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
CDIR=os.path.join(ROOT,"assets","generated","hand","chars")
if not os.path.isdir(CDIR): CDIR=os.path.join(ROOT,"assets","hand","chars")
NAMES=["villager_red","villager_green","villager_blue","villager_yellow","villager_purple","villager_teal","villager_orange","villager_slate"]

def mask_at(name, H):
    im=Image.open(os.path.join(CDIR,name+".png")).convert("RGBA").crop((0,0,48,96))  # 第1帧
    w=max(1,round(48*H/96)); z=im.resize((w,H),Image.NEAREST); px=z.load()
    return [[1 if px[x,y][3]>0 else 0 for x in range(w)] for y in range(H)]

def iou(a,b):
    inter=union=0
    for y in range(len(a)):
        for x in range(len(a[0])):
            pa,pb=a[y][x],b[y][x]
            if pa or pb:
                union+=1
                if pa and pb: inter+=1
    return inter/union if union else 1.0

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--height",type=int,default=34); ap.add_argument("--threshold",type=float,default=0.95)
    a=ap.parse_args()
    masks={n:mask_at(n,a.height) for n in NAMES}
    pairs=[]; mx=0
    for i in range(len(NAMES)):
        for j in range(i+1,len(NAMES)):
            v=round(iou(masks[NAMES[i]],masks[NAMES[j]]),3); mx=max(mx,v)
            pairs.append({"a":NAMES[i],"b":NAMES[j],"iou":v,"ok":v<a.threshold})
    bad=[p for p in pairs if not p["ok"]]
    out={"target_height":a.height,"threshold":a.threshold,"pairs":len(pairs),"max_iou":mx,
         "failed":bad,"gate_pass":{"pass":len(bad)==0,"max_iou":mx}}
    json.dump(out, open(os.path.join(HERE,"char_game_size.json"),"w"), ensure_ascii=False, indent=2)
    print("game-size(%dpx) gate_pass: %s | max_iou=%.3f | fails=%d/%d"%(a.height,out["gate_pass"]["pass"],mx,len(bad),len(pairs)))
    for p in bad: print("  FAIL",p["a"],p["b"],p["iou"])

if __name__=="__main__": main()
