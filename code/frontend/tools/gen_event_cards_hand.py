#!/usr/bin/env python3
"""gen_event_cards_hand.py — 20 张事件卡 ·「手绘像素场景」版（自包含，无外部模块依赖）。

结构：〔像素插画区（peeps 像素角色 + 像素场景）〕＋〔机制标注区（对照条/勾叉/算式/二选一/状态条）〕
     ＋〔木牌标签（中英）〕＋〔图标徽章（icons_atlas）〕。
输出：assets/generated/event_cards_hand/<slug>.png + _sheet.png + .json
确定性；只读素材；不碰 engine/config。
"""
from __future__ import annotations
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                     # frontend/
ASSETS = os.path.join(ROOT, "assets")
OUTDIR = os.path.join(ASSETS, "generated", "event_cards_hand"); os.makedirs(OUTDIR, exist_ok=True)

def font(sz, bold=True):
    for p in [("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
              "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
    return ImageFont.load_default()

F_CN = font(19, True); F_EN = font(11, False); F_SM = font(10, False); F_B = font(13, True)

PEEPS = Image.open(os.path.join(ASSETS, "peeps.png")).convert("RGBA")
ICONS = Image.open(os.path.join(ASSETS, "generated", "icons_atlas.png")).convert("RGBA")
ICON_COLS, ICON_SZ = 12, 32
BANDS = [(21, 92), (120, 188), (216, 284), (312, 380), (405, 476), (501, 572), (597, 668), (693, 764)]
INDEX = json.load(open(os.path.join(ASSETS, "assets_manifest.json")))["iconAtlas"]["atlas"]["index"]

def peep(r, g, f=0):
    b = BANDS[r]; x = (g * 3 + f) * 48
    return PEEPS.crop((x, b[0] - 1, x + 48, b[1] + 1))

OL, YG, EL = peep(0, 0), peep(4, 0), peep(0, 2)
RD, BL, GH = peep(0, 1), peep(1, 1), peep(0, 3)

PAL = {"ECON": (232, 184, 75), "LIFE": (111, 207, 107), "SOCIAL": (176, 124, 232),
       "COGN": (92, 200, 255), "SYS": (139, 152, 171), "WARN": (228, 87, 46)}
INK = (26, 28, 44)
CW, CH = 300, 224
ILL_H = 178

def tint(c, f): return tuple(int(c[i] * f) for i in range(3))

def h2(x, y, s=0):
    n = (int(x) * 374761393 + int(y) * 668265263 + int(s) * 2246822519) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFFFFFF) / 4294967296.0

def texturize(img):
    """微纹理 + 色阶 + 轻微不规则（每像素确定性抖动，仅作用于插画区）"""
    px = img.load()
    for y in range(ILL_H):
        for x in range(CW):
            r, g, b, a = px[x, y]
            if a < 40: continue
            d = int(h2(x, y, 7) * 15) - 7            # -7..+7 色阶抖动
            px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)), a)
    return img

def ill_base(fam):
    img = Image.new("RGBA", (CW, ILL_H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    base = tint(PAL[fam], 0.30)
    d.rounded_rectangle((0, 0, CW, ILL_H + 20), 12, fill=base + (255,))
    for i in range(ILL_H):
        d.line((0, i, CW, i), fill=(255, 255, 255, int(34 * (1 - i / ILL_H))))
    # 地面：木/土色带 + 不规则板缝 + 木纹（加色阶/微纹理/不规则）
    gy = ILL_H - 40
    wood = [(150, 106, 62), (138, 96, 54), (162, 116, 70), (128, 88, 50)]
    x = 0
    while x < CW:
        w = 12 + int(h2(x, 1, 5) * 8)               # 板宽不一
        col = wood[int(h2(x, 2, 9) * len(wood)) % len(wood)]
        d.rectangle((x, gy, min(CW, x + w), ILL_H), fill=col + (255,))
        if h2(x, 3, 11) > 0.5: d.line((x, gy, x, ILL_H), fill=(70, 46, 24, 190))   # 错缝
        for k in range(2):                           # 木纹短线
            yy = gy + 4 + int(h2(x, k + 4, 13) * 30)
            d.line((x + 2, yy, min(CW, x + w - 2), yy), fill=(96, 62, 34, 150))
        x += w
    d.line((0, gy, CW, gy), fill=(60, 40, 22, 200))
    d.ellipse((CW * .5 - 100, ILL_H - 66, CW * .5 + 100, ILL_H - 16), fill=tint(PAL[fam], 0.16) + (170,))
    # 草丛/碎石点缀（不规则分布）
    for i in range(14):
        px2 = int(h2(i, 5, 21) * CW); py2 = gy - 2 - int(h2(i, 6, 23) * 8)
        if h2(i, 7, 25) > 0.6:
            for u in range(3): d.line((px2 + u * 3, py2, px2 + u * 3, py2 - 4 - int(h2(i + u, 8, 27) * 3)), fill=(80, 120, 60, 220))
        else:
            d.rectangle((px2, py2, px2 + 3, py2 + 2), fill=(120, 110, 96, 220))
    return img

def paste_char(img, ch, cx, feet, h=64):
    w = int(ch.width * h / ch.height); ch2 = ch.resize((w, h), Image.NEAREST)
    img.alpha_composite(ch2, (int(cx - w / 2), int(feet - h)))

def dots(img, x, y, col):
    d = ImageDraw.Draw(img)
    for i in range(3): d.ellipse((x + i * 8, y + (0 if i == 1 else 3), x + i * 8 + 4, y + (0 if i == 1 else 3) + 4), fill=col + (255,))

def zig(img, x0, x1, y):
    d = ImageDraw.Draw(img); pts = []; up = True
    for x in range(x0, x1, 8): pts.append((x, y - (10 if up else 0))); up = not up
    d.line(pts, fill=(228, 87, 46, 255), width=3)

def scene(img, tpl, fam, actors):
    F = ILL_H - 34
    if tpl == "pair-talk":
        paste_char(img, actors[0], CW * .36, F, 62); paste_char(img, actors[1], CW * .64, F, 58); dots(img, CW * .5 - 12, F - 82, PAL[fam])
    elif tpl == "trade":
        paste_char(img, actors[0], CW * .32, F, 58); paste_char(img, actors[1], CW * .68, F, 58)
        d = ImageDraw.Draw(img); d.ellipse((CW * .5 - 10, F - 40, CW * .5 + 10, F - 20), fill=(255, 205, 117, 255), outline=(26, 28, 44, 255)); d.text((CW * .5 - 5, F - 40), "¥", font=F_EN, fill=(26, 28, 44, 255))
    elif tpl == "conflict":
        paste_char(img, actors[0], CW * .34, F, 58); paste_char(img, actors[1], CW * .66, F, 58); zig(img, int(CW * .44), int(CW * .58), F - 60)
    elif tpl == "craft":
        paste_char(img, actors[0], CW * .42, F, 64); d = ImageDraw.Draw(img)
        d.rectangle((CW * .66 - 26, F - 26, CW * .66 + 26, F), fill=(122, 74, 43, 255), outline=(26, 28, 44, 255))
        for i in range(4): d.line((CW * .66 + 4 + i * 5, F - 44 - i * 3, CW * .66 + 8 + i * 5, F - 50 - i * 3), fill=(255, 205, 117, 255), width=2)
    elif tpl == "solo":
        paste_char(img, actors[0], CW * .5, F, 70)
    elif tpl == "group":
        for k, cx in enumerate((.28, .5, .72)): paste_char(img, actors[k % len(actors)], CW * cx, F, 56)
        dots(img, CW * .5 - 12, F - 78, PAL[fam])

# ---------------- 机制标注（5 模板） ----------------
PANEL = (14, 12, 150, 96)
def ann(img, kind, fam, spec):
    d = ImageDraw.Draw(img); x0, y0, x1, y1 = PANEL; accent = PAL[fam]
    d.rounded_rectangle((x0 + 2, y0 + 2, x1 + 2, y1 + 2), 8, fill=(0, 0, 0, 60))
    d.rounded_rectangle((x0, y0, x1, y1), 8, fill=(255, 255, 255, 236))
    if kind == "rel-bars":
        bw = x1 - x0 - 58
        for i, (nm, lvl) in enumerate(spec["rows"]):
            yy = y0 + 10 + i * 20
            d.text((x0 + 8, yy - 2), nm, font=F_SM, fill=INK)
            d.rounded_rectangle((x0 + 46, yy, x0 + 46 + bw, yy + 10), 5, fill=(225, 228, 235))
            d.rounded_rectangle((x0 + 46, yy, x0 + 46 + int(bw * lvl), yy + 10), 5, fill=accent)
            if lvl >= 0.6: d.text((x0 + 48 + bw, yy - 2), "✓", font=F_B, fill=(56, 160, 90))
    elif kind == "timeline":
        days = spec["days"]; step = (x1 - x0 - 16) / len(days)
        for i, (lbl, ok) in enumerate(days):
            cx = x0 + 12 + step * (i + .5)
            d.text((cx - 12, y0 + 8), lbl, font=F_SM, fill=INK)
            d.text((cx - 6, y0 + 34), "✓" if ok else "✗", font=font(18), fill=(56, 160, 90) if ok else (210, 70, 60))
        d.text((x0 + 8, y1 - 20), spec.get("note", ""), font=F_SM, fill=(90, 96, 112))
    elif kind == "equation":
        yy = y0 + 34; x = x0 + 10
        for v, op in spec["parts"]:
            if op: d.text((x, yy - 6), op, font=F_B, fill=INK); x += 16
            if v.isdigit():
                d.ellipse((x, yy - 12, x + 26, yy + 14), fill=(255, 205, 117), outline=(168, 112, 46)); d.text((x + 6, yy - 8), v, font=F_B, fill=(90, 58, 12)); x += 30
            elif v:
                d.rounded_rectangle((x, yy - 10, x + 42, yy + 14), 5, fill=(225, 228, 235)); d.text((x + 6, yy - 7), v, font=F_SM, fill=INK); x += 48
        d.text((x0 + 8, y1 - 20), spec.get("note", ""), font=F_SM, fill=(90, 96, 112))
    elif kind == "ab-choice":
        a, b = spec["a"], spec["b"]; yy = y0 + 26
        d.rounded_rectangle((x0 + 8, yy, x0 + 62, yy + 34), 6, fill=(232, 236, 242)); d.text((x0 + 12, yy + 4), a[0], font=F_SM, fill=INK)
        d.text((x0 + 66, yy + 6), "VS", font=F_B, fill=accent)
        d.rounded_rectangle((x0 + 96, yy, x0 + 148, yy + 34), 6, fill=(232, 236, 242)); d.text((x0 + 100, yy + 4), b[0], font=F_SM, fill=INK)
        d.text((x0 + 42, yy + 14), "✓" if a[1] else "✗", font=font(18), fill=(56, 160, 90) if a[1] else (210, 70, 60))
        d.text((x0 + 130, yy + 14), "✓" if b[1] else "✗", font=font(18), fill=(56, 160, 90) if b[1] else (210, 70, 60))
        d.text((x0 + 8, y1 - 18), spec.get("note", ""), font=F_SM, fill=(90, 96, 112))
    elif kind == "status":
        nm, lvl = spec["label"], spec["level"]; yy = y0 + 30
        d.text((x0 + 8, y0 + 10), nm, font=F_SM, fill=INK)
        d.rounded_rectangle((x0 + 8, yy, x1 - 12, yy + 16), 6, fill=(225, 228, 235))
        col = (210, 70, 60) if lvl < .4 else ((232, 184, 75) if lvl < .7 else (56, 160, 90))
        d.rounded_rectangle((x0 + 8, yy, x0 + 8 + int((x1 - 20) * lvl), yy + 16), 6, fill=col)
        d.text((x0 + 8, y1 - 22), spec.get("note", ""), font=F_SM, fill=(90, 96, 112))

def sign(img, cn, en):
    d = ImageDraw.Draw(img); y0 = CH - 46
    d.rectangle((0, y0, CW, CH), fill=(122, 74, 43))
    for i in range(0, CW, 18): d.line((i, y0, i, CH), fill=(96, 58, 34))
    d.rectangle((0, y0, CW, y0 + 2), fill=(160, 104, 60)); d.rectangle((0, CH - 3, CW, CH), fill=(80, 48, 26))
    tw = d.textlength(cn, font=F_CN); d.text(((CW - tw) / 2, y0 + 6), cn, font=F_CN, fill=(255, 244, 224))
    ew = d.textlength(en, font=F_EN); d.text(((CW - ew) / 2, y0 + 28), en, font=F_EN, fill=(240, 220, 190))

def badge(img, key, fam):
    d = ImageDraw.Draw(img); x0, y0 = CW - 44, 10
    d.rounded_rectangle((x0, y0, x0 + 34, y0 + 34), 9, fill=(24, 28, 44, 240), outline=PAL[fam], width=2)
    i = INDEX.get(key)
    if i is not None:
        ic = ICONS.crop(((i % ICON_COLS) * ICON_SZ, (i // ICON_COLS) * ICON_SZ, (i % ICON_COLS) * ICON_SZ + ICON_SZ, (i // ICON_COLS) * ICON_SZ + ICON_SZ)).resize((24, 24), Image.NEAREST)
        img.alpha_composite(ic, (x0 + 5, y0 + 5))

# slug, cn, en, icon, fam, scene, actors, annkind, annspec
EV = [
 ("mentorship","导师指导","Mentorship","skill-up","COGN","pair-talk",[EL,YG],"rel-bars",{"rows":[("尊重",.85),("好感",.8)]}),
 ("gift-giving","赠礼","Gift-giving","gift-ubi","ECON","trade",[YG,OL],"equation",{"parts":[("10",""),("","-"),("0",""),("","="),("礼物","")],"note":"赠予不损好感"}),
 ("combat-training","冲突演练","Combat Training","clash","WARN","conflict",[RD,BL],"status",{"label":"技能熟练度","level":.6,"note":"演练中提升"}),
 ("creative-collab","创意协作","Creative Collab","craft","COGN","group",[YG,YG,OL],"rel-bars",{"rows":[("协作",.9),("好感",.7)]}),
 ("saving-money","储蓄","Saving Money","bank-in","ECON","solo",[OL],"equation",{"parts":[("收入",""),("","-"),("支出",""),("","="),("存款","")],"note":"账户余额↑"}),
 ("whispered-comm","私语","Whispered Comm.","speech-dm","SOCIAL","pair-talk",[YG,OL],"ab-choice",{"a":("公开",False),"b":("私聊",True),"note":"隐私优先"}),
 ("emotion-burnout","情绪耗竭","Emotion Burnout","need","LIFE","solo",[YG],"status",{"label":"精力","level":.2,"note":"Resting to survive"}),
 ("diff-scoring","评分分歧","Diff. Scoring","judge","SYS","group",[GH,BL,OL],"rel-bars",{"rows":[("尊重",.75),("好感",.35)] }),
 ("scarcity-buy","稀缺抢购","Scarcity Buy","shop","ECON","trade",[RD,OL],"equation",{"parts":[("40",""),("","-"),("35",""),("","="),("5","")],"note":"稀缺 → 溢价"}),
 ("skill-practice","技能练习","Skill Practice","skill","COGN","craft",[YG],"status",{"label":"技能熟练度","level":.8,"note":"反复练习"}),
 ("polite-reject","礼貌拒绝","Polite Rejection","offer-no","SOCIAL","pair-talk",[YG,OL],"ab-choice",{"a":("接受",False),"b":("婉拒",True),"note":"维持关系"}),
 ("passion-salary","热爱与薪资","Passion vs Salary","role","ECON","pair-talk",[GH,BL],"ab-choice",{"a":("热爱",False),"b":("薪资",True),"note":"角色权衡"}),
 ("group-proposal","小组提案","Group Proposal","norm-new","SOCIAL","group",[YG,YG,OL],"timeline",{"days":[("日1",True),("日2",True),("日3",True)],"note":"提案通过 ✓"}),
 ("academic-collab","学术协作","Academic Collab","book","COGN","pair-talk",[OL,BL],"rel-bars",{"rows":[("协作",.85),("尊重",.9)]}),
 ("counter-propose","反提案","Counter-propose","offer-alt","SOCIAL","pair-talk",[YG,OL],"timeline",{"days":[("日1",False),("日2",True),("日3",True)],"note":"反提案达成"}),
 ("select-location","选择地点","Select Location","pin","COGN","solo",[GH],"ab-choice",{"a":("音乐室",False),"b":("日落天台",True),"note":"选址达成"}),
 ("power-conflict","权力冲突","Power Conflict","gavel","WARN","conflict",[OL,GH],"rel-bars",{"rows":[("尊重",.3),("好感",.4)]}),
 ("rel-acceptance","关系接纳","Rel. Acceptance","relation","SOCIAL","pair-talk",[YG,YG],"rel-bars",{"rows":[("好感",.9),("尊重",.85)]}),
 ("ice-breaking","破冰","Ice-breaking","meet","SOCIAL","pair-talk",[YG,OL],"ab-choice",{"a":("沉默",False),"b":("搭话",True),"note":"破冰成功"}),
 ("rel-maintain","关系维护","Rel. Maintenance","relation","SOCIAL","trade",[YG,YG],"timeline",{"days":[("日1",True),("日2",True),("日3",True)],"note":"Good night"}),
]

def main():
    sheet = Image.new("RGB", (5 * CW + 36, 4 * CH + 34), (16, 18, 28))
    d = ImageDraw.Draw(sheet)
    d.text((10, 9), "青溪镇 · 20 事件卡（手绘像素场景版：像素插画 + 机制标注 + 木牌标签）", font=font(20), fill=(255, 255, 255))
    cards = []
    for i, (slug, cn, en, key, fam, tpl, actors, akind, aspec) in enumerate(EV):
        img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        art = ill_base(fam); scene(art, tpl, fam, actors)
        img.alpha_composite(art, (0, 0))
        texturize(img)
        ann(img, akind, fam, aspec); sign(img, cn, en); badge(img, key, fam)
        ImageDraw.Draw(img).rounded_rectangle((1, 1, CW - 2, CH - 2), 12, outline=(24, 28, 44, 255), width=3)
        img.convert("RGB").save(os.path.join(OUTDIR, slug + ".png"))
        cards.append({"id": slug, "title_cn": cn, "title_en": en, "icon": key, "family": fam, "scene": tpl, "annotation": akind,
                      "file": "assets/generated/event_cards_hand/" + slug + ".png"})
        sheet.paste(img.convert("RGB"), ((i % 5) * CW + 6, 30 + (i // 5) * CH + 6))
    sheet.save(os.path.join(ASSETS, "generated", "event_cards_hand_sheet.png"))
    json.dump({"schema": "hitt.event-cards.hand/1", "size": [CW, CH], "count": len(cards), "cards": cards},
              open(os.path.join(ASSETS, "generated", "event_cards_hand.json"), "w"), ensure_ascii=False, indent=2)
    print("hand cards:", len(cards), "->", OUTDIR)

if __name__ == "__main__":
    main()
