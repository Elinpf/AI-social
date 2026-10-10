#!/usr/bin/env python3
"""T65 视觉调研取证脚本（只读）。
用本地 Playwright + Chromium 无头浏览器打开运行中的前端页面并整页截图。
不修改任何前端渲染代码，仅导航 / 等待 / 截图 / 采集 console。
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8848/"
SHOTS = [
    ("demo_run.png", "?log=sample/demo_run.jsonl"),
    ("engine_run_r20.png", "?log=sample/engine_run_seed12345_r20.jsonl"),
]

def main() -> int:
    logs = {}
    with sync_playwright() as p:
        exe = "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome"
        if not Path(exe).exists():
            exe = "/root/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome"
        browser = p.chromium.launch(
            headless=True,
            executable_path=exe,
            args=[
                "--no-sandbox",
                "--enable-unsafe-swiftshader",
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--ignore-gpu-blocklist",
            ],
        )
        for fname, qs in SHOTS:
            ctx = browser.new_context(viewport={"width": 1600, "height": 1000},
                                      device_scale_factor=1)
            page = ctx.new_page()
            msgs = []
            page.on("console", lambda m: msgs.append(f"[{m.type}] {m.text}"))
            page.on("pageerror", lambda e: msgs.append(f"[pageerror] {e}"))
            url = BASE + qs
            page.goto(url, wait_until="load", timeout=60000)
            # 等 Pixi 初始化 + 素材加载 + 渲染
            page.wait_for_timeout(9000)
            info = page.evaluate(
                """() => {
                    const c = document.querySelector('#pixi-host canvas');
                    const host = document.querySelector('#pixi-host');
                    return {
                        title: document.title,
                        hasCanvas: !!c,
                        canvasW: c ? c.width : null,
                        canvasH: c ? c.height : null,
                        cssW: c ? c.clientWidth : null,
                        cssH: c ? c.clientHeight : null,
                        hostW: host ? host.clientWidth : null,
                        hostH: host ? host.clientHeight : null,
                        roundLabel: (document.querySelector('#round-label')||{}).textContent,
                        clock: (document.querySelector('#hud-clock')||{}).textContent,
                        source: (document.querySelector('#source-badge')||{}).textContent,
                        errBoxHidden: (document.querySelector('#error-box')||{}).hidden,
                        errText: (document.querySelector('#error-box')||{}).textContent,
                        bboxes: ['#stage-wrap','#pixi-host','#audit','#controls','#layout']
                            .reduce((o,s)=>{const e=document.querySelector(s); if(e){const r=e.getBoundingClientRect(); o[s]=[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)];} return o;},{}),
                    };
                }"""
            )
            page.screenshot(path=str(OUT / fname), full_page=True)
            # 额外截一张仅地图区的图，便于单独看构图
            try:
                stage = page.query_selector("#stage-wrap")
                if stage:
                    mapname = fname.replace(".png", "_map.png")
                    stage.screenshot(path=str(OUT / mapname))
            except Exception as e:  # noqa
                msgs.append(f"[shot-map-warn] {e}")
            logs[fname] = {"url": url, "info": info, "console": msgs[:40]}
            ctx.close()
        browser.close()
    (OUT / "capture_report.json").write_text(
        json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(logs, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
