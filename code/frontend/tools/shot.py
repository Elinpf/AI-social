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

## T282 根因结论（首帧偶发白/黑）—— 写给下一个人，别再追一遍
- **现象**：still 单帧偶发**整幅单色**（白 (240,240,240) 或黑 (0,0,0)）—— 是"canvas 完全没被呈现"，**不是半张图/渲染坏了**。
- **根因**：**截图瞬时竞态**——`pg.screenshot()` 抓合成器已提交帧，软件 GL（`--use-gl=swiftshader`）下 WebGL
  后缓冲→合成的**首帧 readback** 极低概率未提交 → 截到清屏色。**不在应用渲染路径上**。
  证据：就绪时 app 状态恒正常（`placeLayer.children>0`、`renderer 尺寸>0`，探针 40/40）；与**负载/画幅/日志大小/节流无关**。
- **受控尝试矩阵 0 / 193 未复现**（idle/并行/CPU节流/大日志/1500×950…）→ **未声称修复、未改渲染路径**。
  详见 `v2/evidence/T282-first-frame-blank-rootcause.md`。
- **重试（`--retry-blank`）仅作"取证容错"，不掩盖问题**：必打印"本次空白/重试次数" + **跨次累计** `blank_cumulative`。
  **若哪天累计变频繁**（如一夜 >N 次）→ 说明环境变了（软件 GL / 驱动 / 负载），**那时要重新追**（本工具只留痕，不抑制、不告警）。
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
    ap.add_argument("--retry-blank", type=int, default=2,
                    help="遇空白帧自动重试次数（取证容错，不降标准；会打印空白/重试次数，默认 2）。")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401（探测依赖是否可用）
    except Exception as e:
        print("SHOT SKIP: 未找到 Python playwright（依赖缺失），未执行:", e)
        return 3

    still = "still=1" in args.url
    t0 = time.time()
    attempts = max(1, args.retry_blank + 1)
    blanks = 0
    rc = 1
    for attempt in range(1, attempts + 1):
        st, msg = _try_capture(args, still)
        if st == "ok":
            extra = f"  blank_retries={blanks}/{attempts - 1}" if attempts > 1 else ""
            print(f"SHOT OK: {args.out}  elapsed={time.time()-t0:.2f}s"
                  f"  mean_brightness={_mean_brightness(args.out)}  max_color_frac={msg}{extra}")
            if blanks:
                print(f"  ⚠ 本次取证出现空白帧 {blanks} 次（已重试通过；"
                      f"空白是零星 bug 的信号，勿被重试抹掉）")
            rc = 0
            break
        if st == "blank":
            blanks += 1
            last = attempt == attempts
            print(f"SHOT {'FAIL' if last else 'WARN'}: 画面近乎单色（{msg}）"
                  f" —— 第 {blanks} 次空白{'（重试耗尽）' if last else '，重试'}")
            if last:
                print(f"  ⚠ 空白 {blanks}/{attempts} 次；重试是取证容错、不是修白帧")
                rc = 1
                break
            continue
        print("SHOT FAIL:", msg)   # 非空白类失败（未就绪/pageerror）：不重试
        rc = 1
        break
    # 观察哨：跨次累计留痕（只记录，不抑制/不告警）。若累计变频繁 → 环境变了，重新追。
    cum = _stats_bump(blanks)
    print(f"  blank_cumulative={cum['blanks']}/{cum['runs']} 次空白/总取证（T282 观察哨，仅留痕）")
    return rc


def _stats_bump(blanks: int) -> dict:
    """跨次累计空白/取证次数（默认 /tmp/hitt_shot_blank_stats.json，可用 SHOT_STATS 覆盖）。绝不因失败而中断。"""
    import json, os
    p = os.environ.get("SHOT_STATS", "/tmp/hitt_shot_blank_stats.json")
    try:
        d = json.loads(open(p, encoding="utf-8").read()) if os.path.exists(p) else {}
    except Exception:
        d = {}
    d["runs"] = int(d.get("runs", 0)) + 1
    d["blanks"] = int(d.get("blanks", 0)) + int(blanks)
    try:
        open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
    except Exception:
        pass
    return d


def _try_capture(args, still):
    """单次抓取 → ('ok'|'blank'|'fail', 说明)。blank 可被外层重试；fail 直接返回。"""
    from playwright.sync_api import sync_playwright
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
                try:
                    pg.wait_for_function("() => window.__RENDER_READY__ === true || "
                                         "document.documentElement.getAttribute('data-render-ready') === '1'",
                                         timeout=int(args.timeout * 1000))
                except Exception:
                    return ("fail", "等待 __RENDER_READY__ 超时（未就绪，拒绝产出可能的黑图）")
            else:
                try:
                    if args.wait_fn:
                        pg.wait_for_function(args.wait_fn, timeout=int(args.timeout * 1000))
                    else:
                        pg.wait_for_selector("#pixi-host canvas", timeout=int(args.timeout * 1000))
                except Exception:
                    return ("fail", "等待就绪失败（wait-fn/canvas）")
                time.sleep(1.2)
            if errs:
                return ("fail", "页面报错 pageerror: " + " | ".join(errs[:2]))
            pg.screenshot(path=args.out)
        finally:
            b.close()
    # ★ T259「非空白校验」：就绪 ≠ 非空白。防"盲测撞上白帧被判 1 分"。
    frac, col = _largest_color_frac(args.out)
    if frac >= _BLANK_FRAC:
        return ("blank", f"最大单色占比 {frac:.2%} ≥ {_BLANK_FRAC:.0%}，色≈{col}")
    return ("ok", f"{frac:.2%}")


# T259 非空白判据：整帧量化(16级/通道)后**最大单色占比**上限。
# 标定：正常帧 ≈0.12–0.15；曾出现的白帧 ≈0.57。取 0.5 分隔，两侧余量大。
_BLANK_FRAC = 0.5


def _largest_color_frac(path: str):
    """整帧最大单色占比（量化到 16 级/通道以吸收抗锯齿），及该颜色。用于"非空白"判据。"""
    try:
        from PIL import Image
        from collections import Counter
        im = Image.open(path).convert("RGB")
        q = im.resize((max(1, im.width // 4), max(1, im.height // 4)))
        px = list(q.getdata())
        c = Counter(((r >> 4) << 4, (g >> 4) << 4, (b >> 4) << 4) for r, g, b in px)
        n = len(px) or 1
        col, v = c.most_common(1)[0]
        return v / n, col
    except Exception:
        return 0.0, None


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
