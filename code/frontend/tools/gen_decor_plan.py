#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_decor_plan.py — 装饰「件与摆放规则」+ 逐格参考清单（T258f，参考件）

依据 art-director 硬口径：
  · 沿路两侧每 4 tile ≥1 连接件（路灯/花坛/木箱/招牌/长椅交替）
  · 建筑门口必配 1–2 件（招牌 + 花坛/木箱/围栏小段）
  · 街区内每 4×4 tile ≥1 装饰（树/灌木/石/花/桶），簇状不均匀
  · 地标 2–3 处作焦点
本脚本输出**规则**与**逐格参考清单**；**最终落格由 art-director 在 layout 拍板**。
输出：assets/hand/decor_plan.json
"""
import json, os, random
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
COLS,ROWS=24,15
ROAD_Y=8
CONNECT=["lamp","flowerbed","crate","sign","bench"]     # 连接件
BLOCK=["tree","bush","rock","flower","barrel"]          # 街区装饰
def main():
    rnd=random.Random(20261012)
    items=[]
    # 1) 沿路每 4 tile 连接件
    for i,tx in enumerate(range(5,COLS,4)):
        items.append({"rule":"road_side","x":tx,"y":ROAD_Y-1,"prop":CONNECT[i%len(CONNECT)]})
    # 2) 门口必配（示例建筑门口；实际坐标由 layout 给）
    for bx in (8,15):
        items.append({"rule":"door_front","x":bx-2,"y":7,"prop":"sign"})
        items.append({"rule":"door_front","x":bx,"y":7,"prop":"flowerbed"})
    # 3) 街区 4×4 ≥1 装饰（簇状：以格点为簇心，随机偏移，不均匀）
    for ty in range(2,ROWS,4):
        for tx in range(5,COLS,4):
            cx=tx+rnd.randint(-1,1); cy=ty+rnd.randint(-1,1)
            p=BLOCK[(tx+ty)%len(BLOCK)]
            items.append({"rule":"block_cluster","x":cx,"y":cy,"prop":p})
            if rnd.random()<0.5:   # 簇内第二件（不均匀）
                items.append({"rule":"block_cluster","x":cx+1,"y":cy,"prop":BLOCK[(tx+ty+1)%len(BLOCK)]})
    # 4) 地标焦点（2–3）
    items.append({"rule":"landmark","x":12,"y":11,"prop":"well"})
    plan={
      "schema":"hitt.decor_plan/1",
      "note":"参考件：件与摆放规则由 pixel-asset-artist 出；最终落格由 art-director 在 layout 拍板。",
      "region":{"cols":COLS,"rows":ROWS,"tile":32},
      "rules":{
        "road_side":{"desc":"道路两侧每 4 tile ≥1 连接件","props":CONNECT},
        "door_front":{"desc":"建筑门口必配 1–2 件","props":["sign","flowerbed","crate","fence"]},
        "block_cluster":{"desc":"每 4×4 tile ≥1 装饰，簇状不均匀","props":BLOCK},
        "landmark":{"desc":"地标 2–3 处作构图焦点","props":["clocktower","arch_bridge","fountain","windmill"]}
      },
      "items":items,
      "counts":{"total":len(items)}
    }
    out=os.path.join(ROOT,"assets","hand","decor_plan.json")
    json.dump(plan,open(out,"w"),ensure_ascii=False,indent=2)
    print("[decor_plan] items=%d -> %s" % (len(items), out))
if __name__=="__main__": main()
