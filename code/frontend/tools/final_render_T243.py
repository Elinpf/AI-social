#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""final_render_T243.py — T243 定妆图（G-1 统一风格 + G-3 挤拥场景可辨）

用已固化管线产出的资产（`assets/hand/buildings128|chars|props`）拼一张**游戏尺度定妆图**：
  · 天空/地面用 **Bayer 4×4 有序抖动**（G-1：有限色阶 + 抖动，禁平滑渐变）；
  · 建筑 + 8 角色（**同屏挤拥**）+ 道具 + **接地软影**（渲染层口径）；
  · 底部附：调色板条 + 抖动放大样 + 角色体型/头身比标注。
纯确定性（无随机时间戳）；只读资产、只写本图。输出：
  `code/frontend/assets/hand/final_render_T243.png`
"""
import json, os, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # frontend/
A = os.path.join(ROOT, "assets")
HAND = os.path.join(A, "hand")
sys.path.insert(0, os.path.join("/root/.jiuwenswarm/agent/workspace/skills/qingxi-pixel-art/scripts"))
import hand_tex as TEX

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def hx(s):
    s = s.lstrip("#"); return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)


def dither_band(img, x0, y0, x1, y1, c_lo, c_hi, t0=0.0, t1=1.0, axis="y"):
    """Bayer 4×4 有序抖动：在两色之间按渐变因子（y 或 x）混合——替代平滑渐变。"""
    px = img.load(); a, b = hx(c_lo), hx(c_hi)
    for y in range(y0, y1):
        for x in range(x0, x1):
            t = (y - y0) / max(1, (y1 - y0 - 1)) if axis == "y" else (x - x0) / max(1, (x1 - x0 - 1))
            t = t0 + (t1 - t0) * t
            thr = (BAYER[y % 4][x % 4] + 0.5) / 16.0
            px[x, y] = b if t > thr else a


def main():
    W, H, SKY = 1120, 640, 210
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255)); d = ImageDraw.Draw(img)
    # 天空：Bayer 抖动（上亮下暖），禁平滑渐变
    dither_band(img, 0, 0, W, SKY, "#7fb8d6", "#a8d8ee", 0.15, 0.95, "y")
    for i in range(70):                                        # 离散雪点
        x = (i * 149) % W; y = (i * 61) % SKY
        img.putpixel((x, y), (255, 255, 255, 255))
    # 地面：草（抖动）+ 土路
    dither_band(img, 0, SKY, W, H, "#3f6b46", "#4f8a53", 0.2, 0.9, "y")
    d.rectangle([0, 470, W, H], fill=hx("#6b5636"))
    dither_band(img, 0, 470, W, H, "#5b4830", "#8a704a", 0.1, 0.9, "y")

    def put(name, xc, ybase, sc=1.0, shadow=True):
        im = Image.open(os.path.join(HAND, name)).convert("RGBA")
        z = im.resize((int(im.width * sc), int(im.height * sc)), Image.NEAREST)
        if shadow:
            sh = Image.new("RGBA", (z.width + 40, z.height + 40), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
            sd.ellipse([24, z.height + 4, 16 + z.width, z.height + 30], fill=(0, 0, 0, 80))
            img.alpha_composite(sh, (int(xc - z.width / 2) - 20, int(ybase - z.height * 0.95) - 20))
        img.paste(z, (int(xc - z.width / 2), int(ybase - z.height * 0.95)), z)

    # 建筑（手绘纹理版，多类）
    put("buildings128/town_hall.png", 250, 500, 1.0)
    put("buildings128/school.png", 430, 500, 0.9)
    put("buildings128/library.png", 600, 495, 0.85)
    put("buildings128/market.png", 780, 505, 0.95)
    put("buildings128/residence.png", 940, 500, 0.9)
    put("buildings128/cafe.png", 1030, 500, 0.8)
    # 道具
    put("props/tree.png", 60, 560, 1.6)
    put("props/tree.png", 1080, 560, 1.6)
    put("props/well.png", 360, 600, 1.6)
    put("props/barrel.png", 700, 610, 1.6)
    put("props/fence.png", 520, 620, 1.6)

    # 8 角色：**同屏挤拥**（广场上，游戏尺度），验证 G-3 可辨
    chars = ["villager_red", "villager_green", "villager_blue", "villager_yellow",
             "villager_purple", "villager_teal", "villager_orange", "villager_slate"]
    cx0, cy0 = 300, 620
    for i, c in enumerate(chars):
        im = Image.open(os.path.join(HAND, "chars", c + ".png")).convert("RGBA").crop((0, 0, 48, 96))
        z = im.resize((int(48 * 1.1), int(96 * 1.1)), Image.NEAREST)
        # 同屏并排（间距 > 角色宽 → 剪影不遮叠，验证可辨）
        x = cx0 + i * 78; y = cy0 - 100
        sh = Image.new("RGBA", (z.width + 20, z.height + 20), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([6, z.height - 2, 14 + z.width, z.height + 14], fill=(0, 0, 0, 90))
        img.alpha_composite(sh, (x - 10, y - 10))
        img.paste(z, (int(x - 26), y - int(96 * 1.05 * 0.95)), z)

    d = ImageDraw.Draw(img)
    d.text((14, 8), "青溪镇 · 定妆图 T243  (G-1 统一风格 + G-3 挤拥场景可辨)", fill=(244, 244, 244))
    d.text((14, 24), "Bayer 4x4 有序抖动天空/地面 · 手绘纹理建筑 · 接地软影 · 8 角色同屏", fill=(210, 226, 240))

    # 底部信息带：调色板 + 抖动放大 + 角色轴
    info = Image.new("RGBA", (W, 200), (26, 28, 44, 255)); dd = ImageDraw.Draw(info)
    dd.text((12, 6), "调色板（手绘 ramp，每材质 4–6 阶）", fill=(244, 244, 244))
    cols = TEX.RAMP["roof_red"] + TEX.RAMP["wood"] + TEX.RAMP["stone"] + TEX.RAMP["green"] + TEX.RAMP["glass"]
    for i, c in enumerate(cols):
        dd.rectangle([12 + i * 40, 22, 12 + i * 40 + 34, 56], fill=hx(c), outline=(40, 44, 60))
    dd.text((12, 64), "Bayer 4×4 抖动放大 8×（有限色阶→纹理；禁平滑渐变）", fill=(244, 244, 244))
    dt = Image.new("RGBA", (96, 24), (0, 0, 0, 0))
    dither_band(dt, 0, 0, 96, 24, TEX.RAMP["roof_red"][1], TEX.RAMP["roof_red"][4], 0.1, 0.95, "x")
    info.alpha_composite(dt.resize((96 * 4, 24 * 4), Image.NEAREST), (12, 82))
    dd.text((800, 64), "8 角色体型/头身比轴", fill=(244, 244, 244))
    xs = ["red normal", "green tall", "blue normal", "yellow stout",
          "purple short·大头", "teal stout", "orange tall", "slate normal"]
    for i, t in enumerate(xs):
        dd.text((800, 84 + i * 13), t, fill=(230, 220, 150))

    out = Image.new("RGBA", (W, H + 200), (0, 0, 0, 255))
    out.alpha_composite(img, (0, 0)); out.alpha_composite(info, (0, H))
    p = os.path.join(HAND, "final_render_T243.png")
    out.convert("RGB").save(p)
    print("final_render ->", p, out.size)


if __name__ == "__main__":
    main()
