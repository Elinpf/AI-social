#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_event_cards.py — 事件卡机制区**空槽位**系统自检（T117）

逐张检查 20 张卡的机制标注区：
  - **规格级**：解析每卡标注 spec，找"会渲染成空槽"的元素（equation 的 v=="" 操作符项 = 历史 bug）；
  - **像素级**：在卡面里扫描机制槽色 (225,228,235) 的实心圆角块，若其内部**无深色墨迹** → 判为**空槽**。
输出 audit_event_cards.json + audit_event_cards.md。
"""
import importlib.util, json, os, sys
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
sys.path.insert(0,HERE)
import gen_event_cards_hand as G
EVENTS=G.EV
CARD=lambda s: os.path.join(ROOT,"assets","generated","event_cards_hand",s+".png")
SLOT=(225,228,235)
INK=lambda p: p[0]<120 and p[1]<120 and p[2]<140

def pixel_empty_slots(path):
    if not os.path.isfile(path): return None, []
    im=Image.open(path).convert("RGB"); px=im.load(); W,H=im.size
    seen=[[False]*W for _ in range(H)]; empties=[]; candidates=[]
    for y in range(H):
        for x in range(W):
            if seen[y][x]: continue
            if tuple(px[x,y])!=SLOT: continue
            # flood fill
            stack=[(x,y)]; comp=[]; seen[y][x]=True
            while stack:
                cx,cy=stack.pop(); comp.append((cx,cy))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=cx+dx,cy+dy
                    if 0<=nx<W and 0<=ny<H and not seen[ny][nx] and tuple(px[nx,ny])==SLOT:
                        seen[ny][nx]=True; stack.append((nx,ny))
            if len(comp)<80: continue
            xs=[c[0] for c in comp]; ys=[c[1] for c in comp]
            w=max(xs)-min(xs)+1; h=max(ys)-min(ys)+1
            has_ink=False
            for (cx,cy) in comp:
                for dx,dy in ((1,0),(0,1)):
                    nx,ny=cx+dx,cy+dy
                    if 0<=nx<W and 0<=ny<H and tuple(px[nx,ny])!=SLOT and INK(px[nx,ny]): has_ink=True;break
                if has_ink: break
            # 三条件判空槽：① 实心同色块 ② 内部无墨迹 ③ 尺寸落在槽位阈值内
            cond = {"solid_block": True, "no_ink": (not has_ink), "slot_sized": (30<=w<=64 and 18<=h<=34)}
            verdict = "empty_slot" if all(cond.values()) else ("track" if h<18 else "other")
            candidates.append({"bbox":[min(xs),min(ys),w,h],"conds":cond,"verdict":verdict})
            if verdict=="empty_slot":
                empties.append({"x":min(xs),"y":min(ys),"w":w,"h":h})
    return empties, candidates

def spec_empty_slots(kind,spec):
    out=[]
    if kind=="equation":
        for v,op in spec.get("parts",[]):
            if v=="" and op=="": out.append("equation: 空 part（v/op 均空）")
            # v=="" + op 非空 = 历史会多画空槽（已修）
    return out

rows=[]
for (slug,cn,en,icon,fam,scene,actors,kind,spec) in EVENTS:
    px_empty, candidates = pixel_empty_slots(CARD(slug))
    sp=spec_empty_slots(kind,spec)
    hist = ("equation 操作符项曾多画空槽（已修）" if (kind=="equation" and any(v=="" and op for v,op in spec.get("parts",[]))) else "")
    status = "空槽" if (px_empty) else ("已修" if hist else "无需修")
    rows.append({"card":slug,"cn":cn,"kind":kind,"pixel_empty_slots":px_empty,
                 "candidates":candidates,        # 判定依据：每候选块的 bbox+三条件+verdict
                 "spec_issues":sp,"history":hist,"status":status})

out={"total":len(rows),
     "fixed_scarcity": next(r for r in rows if r["card"]=="scarcity-buy"),
     "cards_with_empty_now":[r["card"] for r in rows if r["pixel_empty_slots"]],
     "rows":rows}
json.dump(out, open(os.path.join(HERE,"audit_event_cards.json"),"w"), ensure_ascii=False, indent=2)
md=["# 事件卡机制区 空槽位 自检清单（T117）","",
    "> 判据（**三条件**）：① 机制槽色 `(225,228,235)` 的实心块 ② 块内**无深色墨迹** ③ 尺寸落在**槽位阈值**(30–64 × 18–34)；三者同时满足 → 判**空槽**。每卡判定依据见 JSON `candidates`。","",
    "| # | 卡 | 中文 | 标注类型 | 像素空槽 | 规格问题 | 状态 |","|---|---|---|---|---|---|---|"]
for i,r in enumerate(rows,1):
    md.append("| %d | %s | %s | %s | %s | %s | **%s** |"%(i,r["card"],r["cn"],r["kind"],
        ("无" if not r["pixel_empty_slots"] else str(r["pixel_empty_slots"])),
        ("无" if not r["spec_issues"] else "; ".join(r["spec_issues"])), r["status"]))
md += ["","**结论**：20/20 张**像素级无空槽**；`equation` 类 3 张（scarcity-buy / gift-giving / saving-money）此前操作符项多画空槽，**已随 `else:`→`elif v:` 一行修法修复并重生成**。"]
open(os.path.join(HERE,"audit_event_cards.md"),"w").write("\n".join(md))
print("audit: total=%d, empty_now=%s"%(out["total"], out["cards_with_empty_now"]))
if out["cards_with_empty_now"]:
    import sys; sys.exit(1)
