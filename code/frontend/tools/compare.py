#!/usr/bin/env python3
"""compare.py — 并排对比截图（现状 vs 目标/参考），一键出对比 PNG。

用于把「我们的小镇」与「AI Town 参考」或「迭代前后」左右拼接，加标题条，便于给用户看差距。

用法：
    python frontend/tools/compare.py \
        --left  frontend/sample/qingxi_demo_r12_browser.png  --left-label "现状：青溪镇" \
        --right /root/aitown_ref.png                          --right-label "目标：a16z AI Town" \
        --out   frontend/sample/compare_qingxi_vs_aitown.png

    # 迭代前后对比（同一标签即可）
    python frontend/tools/compare.py --left before.png --right after.png \
        --left-label 前 --right-label 后 --out compare.png

可选：--height 720（统一缩放到该高度，保持比例）。依赖 Pillow。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    print("需要 Pillow：pip install pillow", file=sys.stderr)
    sys.exit(2)

BG = (20, 24, 31)
FG = (230, 235, 242)
BAR = (36, 44, 56)
PAD = 16
BAR_H = 34


def _font(size=18):
    for p in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def fit(img: Image.Image, h: int) -> Image.Image:
    if h <= 0 or img.height == h:
        return img
    w = int(img.width * h / img.height)
    return img.resize((w, h), Image.LANCZOS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--left", required=True)
    ap.add_argument("--right", required=True)
    ap.add_argument("--left-label", default="左")
    ap.add_argument("--right-label", default="右")
    ap.add_argument("--out", required=True)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    for p in (args.left, args.right):
        if not Path(p).exists():
            print(f"图片不存在: {p}", file=sys.stderr)
            return 2

    l = fit(Image.open(args.left).convert("RGB"), args.height)
    r = fit(Image.open(args.right).convert("RGB"), args.height)
    font = _font(18)

    w = PAD + l.width + PAD + r.width + PAD
    h = PAD + BAR_H + max(l.height, r.height) + PAD
    canvas = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(canvas)

    def draw_panel(img, x, label):
        d.rectangle([x, PAD, x + img.width, PAD + BAR_H], fill=BAR)
        d.text((x + 10, PAD + 8), label, fill=FG, font=font)
        canvas.paste(img, (x, PAD + BAR_H))

    draw_panel(l, PAD, args.left_label)
    draw_panel(r, PAD + l.width + PAD, args.right_label)

    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"wrote {out}  ({w}x{h})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
