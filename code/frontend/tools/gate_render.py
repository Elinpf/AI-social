#!/usr/bin/env python3
"""gate_render.py — 无头浏览器渲染回归门禁（T107）。

为什么需要：Node 版 smoke_test 的 PIXI mock 会接受任何参数，**无法**复现
"new PIXI.Sprite(BaseTexture) 抛异常 → town.load() 中止 → placeLayer=0" 这类
**真实 Pixi 运行期错误**。必须有**真浏览器**断言，把"加载静默中止/画面空"变成自动报警。

断言：① 无 pageerror；② window.__HITT_TOWN__ 存在且 _useLib===true；
     ③ placeLayer.children.length === 17；④ agentLayer >= 1。
用法（需先起静态服务）：
    python frontend/tools/serve.py --host 0.0.0.0 --port 8848 &
    python frontend/tools/gate_render.py [--url URL]
退出码 0=PASS，1=FAIL。
"""
from __future__ import annotations
import argparse, sys, time

from _chrome import find_chrome   # 探测式，不写死任何机器路径（可用 HITT_CHROME 覆盖）
EXPECTED_PLACES = 17


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8848/?log=sample/demo_run.jsonl&still=1&round=12")
    ap.add_argument("--timeout", type=int, default=60000)
    args = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        # 依赖降级：无 playwright → **SKIP**（绝不当作 PASS），退出码 3，供 CI 区分「未跑」与「通过」
        print("GATE SKIP: 未找到 Python playwright（CI 依赖缺失），本门禁未执行:", e)
        return 3
    t0 = time.time()

    fails = 0
    def ok(cond, msg):
        nonlocal fails
        print(("  ok  - " if cond else "  FAIL- ") + msg)
        if not cond: fails += 1

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=find_chrome(),
                              args=["--no-sandbox", "--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        try:
            pg = b.new_page(viewport={"width": 1400, "height": 900})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(args.url, wait_until="load", timeout=args.timeout)
            time.sleep(6)
            st = pg.evaluate("""(()=>{const t=window.__HITT_TOWN__; if(!t) return {town:false};
              return {town:true, useLib:!!t._useLib,
                      places: t.placeLayer? t.placeLayer.children.length : -1,
                      agents: t.agentLayer? t.agentLayer.children.length : -1};})()""")
            ok(len(errs) == 0, "无 pageerror（" + " | ".join(errs[:2]) + "）")
            ok(st.get("town"), "window.__HITT_TOWN__ 存在（只读调试钩子）")
            ok(st.get("useLib") is True, "走资产库路径 _useLib=true")
            ok(st.get("places") == EXPECTED_PLACES, f"placeLayer.children.length === {EXPECTED_PLACES}（实际 {st.get('places')}）")
            ok(st.get("agents", -1) >= 1, f"agentLayer 已建立（{st.get('agents')} 项）")
        finally:
            b.close()
    dt = time.time() - t0
    print("\nGATE " + ("FAIL (%d)" % fails if fails else "PASS") + f"  ·  elapsed={dt:.2f}s")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
