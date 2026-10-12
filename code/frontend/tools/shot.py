#!/usr/bin/env python3
"""shot.py — 无头截图：**等渲染就绪**再截（防"假黑图 / false negative"）。

## 已知坑（务必知道）：大日志下会产出"整列发黑"的假图
- 触发条件：**大日志（≥10MB）+ still 单帧（?still=1）**。页面前端仍在解析日志 / 构建场景时，
  若立刻截图，会得到一张**黑图**——这**不是渲染 bug，是截图时序问题**（多等一会即正常）。
- 危害：这是**"假红"**（false negative），与"假绿"同族：**证据管线不可靠会让判断两头都出错**
  （假红会让人去修一个并不存在的问题）。
- 对策（本工具的做法）：**绝不靠固定 sleep**，而是等页面前端置好的**就绪信号**：
  `window.__RENDER_READY__ === true`（等价 `<html data-render-ready="1">`）——由 `main.js` 在
  **素材加载完成 + 首帧渲染后**设置。**等不到就超时 → 非零退出**，绝不默默产出一张黑图。

## 用法
    python frontend/tools/shot.py --url 'http://127.0.0.1:8848/?log=...&round=45&still=1' \
        --out /root/shot.png [--width 1500 --height 950] [--timeout 60]

## 退出码
    0 = OK（已就绪并出图）
    1 = FAIL（超时未就绪 / 页面报错）——**非零，CI 会红**
    3 = SKIP（无 playwright，依赖缺失；**不算通过**）
"""
from __future__ import annotations
import argparse, sys, time

CHROME = "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1500)
    ap.add_argument("--height", type=int, default=950)
    ap.add_argument("--timeout", type=float, default=60.0, help="等待就绪的总超时（秒）")
    ap.add_argument("--wait-fn", default=None,
                    help="可选：等待该 JS 表达式为真再截（用于非 still 页面，如 devtools 查看器）。"
                         "省略且 URL 无 still=1 时，退化为等 #pixi-host canvas。")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("SHOT SKIP: 未找到 Python playwright（依赖缺失），未执行:", e)
        return 3

    still = "still=1" in args.url
    t0 = time.time()
    with sync_playwright() as p:
        b = p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"],
        )
        try:
            pg = b.new_page(viewport={"width": args.width, "height": args.height}, device_scale_factor=1)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(args.url, wait_until="load", timeout=int(args.timeout * 1000))
            if still:
                # ★ 等前端就绪信号，而非固定 sleep
                try:
                    pg.wait_for_function("() => window.__RENDER_READY__ === true || "
                                         "document.documentElement.getAttribute('data-render-ready') === '1'",
                                         timeout=int(args.timeout * 1000))
                except Exception:
                    print("SHOT FAIL: 等待 __RENDER_READY__ 超时（未就绪，拒绝产出可能的黑图）"
                          f"  elapsed={time.time()-t0:.2f}s")
                    return 1
            else:
                # 非 still：优先用 --wait-fn（devtools 等），否则等 canvas 出现（惰性回退，明确标注）
                try:
                    if args.wait_fn:
                        pg.wait_for_function(args.wait_fn, timeout=int(args.timeout * 1000))
                    else:
                        pg.wait_for_selector("#pixi-host canvas", timeout=int(args.timeout * 1000))
                except Exception:
                    print("SHOT FAIL: 等待就绪失败（wait-fn/canvas）"); return 1
                time.sleep(1.2)
            if errs:
                print("SHOT FAIL: 页面报错 pageerror:", " | ".join(errs[:2])); return 1
            pg.screenshot(path=args.out)
        finally:
            b.close()
    print(f"SHOT OK: {args.out}  elapsed={time.time()-t0:.2f}s  mean_brightness={_mean_brightness(args.out)}")
    return 0


def _mean_brightness(path: str) -> str:
    """**口径（唯一权威）**：整帧灰度均值 = 0.299*R + 0.587*G + 0.114*B（ITU-R BT.601），
    对**整张图所有像素**取平均，范围 0–255（0=全黑）。**黑图判据：< 8**。
    注意：不要与"RGB 三通道分别平均再取平均"或"只算地图区域"混用——**同名不同义会制造假绿/假红**。
    """
    try:
        from PIL import Image
        im = Image.open(path).convert("L")   # L = BT.601 亮度
        data = im.getdata()
        n = len(data)
        v = (sum(data) / n) if n else 0.0
        return f"{v:.1f}(gray601,0-255,黑<8)"
    except Exception as e:
        return f"n/a({e})"


if __name__ == "__main__":
    sys.exit(main())
