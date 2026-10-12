#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""event_card_readability_check.py — 事件卡「真实显示尺寸」可读性门禁（T258 同族检查）

判据条件（务必与实际一致，别在放大图里判）：
  观测台内联缩略图 = CSS `width:150px` + `image-rendering:pixelated`
  → 源 300×224 **NEAREST 半采样**到 150×112（奇数行列的 1px 笔画会被丢掉）。
  机制标注区（卡「灵魂」）= 左上 136×84 → 显示 68×42。

在该条件下实测机制区：
  - contrast  : 墨水 vs 白板 WCAG 对比（≥4.5 为 AA 正文可读）
  - keep      : 半采样后墨水**面密度保留率**（≪1 说明笔画被丢）
  - min_stroke: 原生最小笔画宽（1px 在 NEAREST 半采样下有丢笔画风险，记为 warn）
输出 `event_card_readability.json`（含 gate_pass）；并入 make art。
"""
import glob, json, os, sys
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
CDIR=os.path.join(ROOT,"assets","generated","event_cards_hand")
if not os.path.isdir(CDIR): CDIR=os.path.join(ROOT,"assets","event_cards_hand")
REGION=(0,0,136,84)          # 机制标注区（spec §1）
DISP_W=150                   # 内联显示宽（css .ev-cardart-img width:150px）
CONTRAST_MIN=4.5
KEEP_MIN=0.70

def lum(v): return v  # 已灰度
def contrast(a,b):
    hi,lo=max(a,b),min(a,b); return (hi+5)/(lo+5)

def ink_mask(im, thr=110): 
    return [1 if p<thr else 0 for p in im.get_flattened_data()] if hasattr(im,"get_flattened_data") else [1 if p<thr else 0 for p in list(im.getdata())]

def min_run(im, thr=110):
    w,h=im.size; px=im.load(); mn=None
    for y in range(h):
        x=0
        while x<w:
            if px[x,y]<thr:
                x0=x
                while x<w and px[x,y]<thr: x+=1
                r=x-x0; mn=r if mn is None else min(mn,r)
            else: x+=1
    return mn

def main():
    fs=sorted(glob.glob(os.path.join(CDIR,"*.png")))
    recs=[]; fails=[]
    for f in fs:
        im=Image.open(f).convert("RGB").crop(REGION).convert("L")
        w,h=im.size
        darks=[p for p in im.getdata() if p<110]; lights=[p for p in im.getdata() if p>200]
        c=round(contrast(sum(darks)/len(darks), sum(lights)/len(lights)),2) if darks and lights else 0.0
        ink_native=len(darks)/(w*h)
        dw=round(w*DISP_W/300.0); dh=round(h*DISP_W/300.0)     # NEAREST 到内联显示尺寸
        dsp=im.resize((dw,dh),Image.NEAREST)
        ink_disp=len([p for p in dsp.getdata() if p<110])/(dw*dh)
        keep=round(ink_disp/ink_native,3) if ink_native else 1.0
        mn=min_run(im)
        ok = (c>=CONTRAST_MIN and keep>=KEEP_MIN)
        rec={"card":os.path.basename(f),"contrast":c,"keep":keep,"min_stroke_native":mn,
             "disp_size":[dw,dh],"ok":ok}
        if not ok: fails.append(rec)
        recs.append(rec)
    gp={"pass":len(fails)==0,"condition":{"display_w":DISP_W,"render":"nearest(pixelated)",
        "region":list(REGION)},"contrast_min":CONTRAST_MIN,"keep_min":KEEP_MIN,
        "cards":len(recs),"failed":fails,"min_contrast":min(r["contrast"] for r in recs) if recs else 0,
        "min_keep":min(r["keep"] for r in recs) if recs else 0}
    json.dump({"gate_pass":gp,"cards":recs}, open(os.path.join(HERE,"event_card_readability.json"),"w"), ensure_ascii=False, indent=2)
    print("event-card readability(%dpx inline) gate_pass: %s | min_contrast=%.2f min_keep=%.2f | fails=%d/%d"
          % (DISP_W, gp["pass"], gp["min_contrast"], gp["min_keep"], len(fails), len(recs)))
    for r in fails: print("  FAIL", r)

if __name__=="__main__": main()
