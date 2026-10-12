#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_pack.py — 一条命令：**指定任意日志 → 5 个盲测片段 URL + 汇总表 + 版本角标**（T275）。

- 自动从日志里选 5 个片段，**覆盖昼夜**（晨/午/暮/夜各取一，夜段必进样本）；
- 把日志拷进 `frontend/sample/` 使其可被静态服务；输出 review.html URL（自带 /__gitstamp 版本角标）；
- 可选 `--measure`：无头实测「日志 → 画面就绪」耗时 + JS 堆内存（吃得住 30 万事件）；
- 可选 `--shots DIR`：把 5 个片段各截一张（存档/自评用）。

用法：
    python3 frontend/tools/review_pack.py --log v2/evidence/run_p1_final_n20_llm.jsonl
    python3 frontend/tools/review_pack.py --log <LOG> --measure --shots /root/t275_shots
    python3 frontend/tools/review_pack.py --log <LOG> --base http://10.10.136.128:8848
"""
from __future__ import annotations
import argparse, json, re, shutil, sys, time
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]
ROOT = FRONTEND.parents[1]           # …/social-experiment
CHROME = "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome"
SLOT_NAME = ["晨", "午", "暮", "夜"]


def scan_rounds(log: Path) -> list[int]:
    """扫描日志的 round 集合（正则，避免整行 JSON 解析，够快）。"""
    rounds: set[int] = set()
    rx = re.compile(r'"round"\s*:\s*(\d+)')
    with log.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = rx.search(line)
            if m:
                rounds.add(int(m.group(1)))
    return sorted(rounds)


def slot_of(r: int) -> int:
    return (r % 12) // 3   # 0晨 1午 2暮 3夜（与 main.js wallClock 同口径）


def wallclock(r: int) -> str:
    day = r // 12 + 1
    hour = (6 + (r % 12) * 2) % 24
    return f"第{day}日 {hour:02d}:00 {SLOT_NAME[slot_of(r)]}"


def pick_rounds(rounds: list[int], k: int = 5) -> list[int]:
    """覆盖昼夜：每 slot 取一（若存在），再均匀补足到 k。夜段优先保证在样本内。"""
    by_slot: dict[int, list[int]] = {0: [], 1: [], 2: [], 3: []}
    for r in rounds:
        by_slot[slot_of(r)].append(r)
    chosen: list[int] = []
    for s in (0, 1, 2, 3):                      # 晨午暮夜各取中位
        if by_slot[s]:
            chosen.append(by_slot[s][len(by_slot[s]) // 2])
    i = 0
    while len(chosen) < k and rounds and i < len(rounds) * 2:
        cand = rounds[min(len(rounds) - 1, int(i * len(rounds) / k))]
        if cand not in chosen:
            chosen.append(cand)
        i += 1
    return sorted(chosen[:k])


def ensure_servable(log: Path) -> str:
    """日志须在 frontend/ 下才能被静态服务；否则拷进 sample/。返回相对 frontend 的 URL 片段。"""
    log = log.resolve()
    try:
        rel = log.relative_to(FRONTEND)
        return rel.as_posix()
    except ValueError:
        dst = FRONTEND / "sample" / log.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or dst.stat().st_size != log.stat().st_size:
            shutil.copyfile(log, dst)
        return f"sample/{log.name}"


def measure(url: str, timeout: float = 180.0) -> dict:
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME,
                              args=["--no-sandbox", "--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url, wait_until="load", timeout=int(timeout * 1000))
        try:
            pg.wait_for_function(
                "() => window.__RENDER_READY__===true || document.documentElement.getAttribute('data-render-ready')==='1'",
                timeout=int(timeout * 1000))
        except Exception:
            pass
        t_render = time.time() - t0
        mem = pg.evaluate("() => (performance.memory ? {used: performance.memory.usedJSHeapSize, "
                          "total: performance.memory.totalJSHeapSize, limit: performance.memory.jsHeapSizeLimit} : null)")
        n_ev = pg.evaluate("() => (window.__HITT_TOWN__ && window.__HITT_TOWN__.__n) || null")
        b.close()
    return {"render_s": round(t_render, 2), "mem": mem, "pageerrors": errs[:2]}


def shots(base: str, log_rel: str, rounds: list[int], outdir: Path) -> list[str]:
    from playwright.sync_api import sync_playwright
    outdir.mkdir(parents=True, exist_ok=True)
    outs = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME,
                              args=["--no-sandbox", "--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1200, "height": 760})
        for i, r in enumerate(rounds):
            u = f"{base}/index.html?log={log_rel}&round={r}&still=1&view=default"
            pg.goto(u, wait_until="load", timeout=120000)
            try:
                pg.wait_for_function("() => window.__RENDER_READY__===true", timeout=120000)
            except Exception:
                pass
            o = outdir / f"clip{i+1}_r{r}_{SLOT_NAME[slot_of(r)]}.png"
            pg.screenshot(path=str(o))
            outs.append(str(o))
        b.close()
    return outs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="任意日志路径（相对仓根或绝对）")
    ap.add_argument("--base", default="http://127.0.0.1:8848")
    ap.add_argument("--clips", type=int, default=5)
    ap.add_argument("--rounds", default=None, help="显式指定片段 round（逗号分隔），覆盖自动选段")
    ap.add_argument("--measure", action="store_true", help="实测『日志→画面就绪』耗时 + JS 堆内存")
    ap.add_argument("--shots", default=None, help="截图输出目录（存档/自评）")
    a = ap.parse_args()

    log = Path(a.log)
    if not log.is_absolute():
        log = (ROOT / a.log) if (ROOT / a.log).exists() else (FRONTEND / a.log)
    if not log.exists():
        print(f"日志不存在: {log}", file=sys.stderr)
        return 2

    rounds = scan_rounds(log)
    if a.rounds:
        clips = [int(x) for x in a.rounds.split(",") if x.strip()]
    else:
        clips = pick_rounds(rounds, a.clips)
    log_rel = ensure_servable(log)
    nights = [r for r in clips if slot_of(r) == 3]

    url = f"{a.base}/review.html?log={log_rel}&rounds={','.join(map(str, clips))}"
    print(f"日志      : {log}  （{log.stat().st_size/1e6:.1f} MB）")
    print(f"事件数    : 约 {sum(1 for _ in log.open('rb')) if log.stat().st_size < 3e8 else '?'} 行（含非事件行）")
    print(f"round 范围: {rounds[0] if rounds else '-'} … {rounds[-1] if rounds else '-'}")
    print(f"片段(覆盖昼夜): " + " | ".join(f"r{r} {wallclock(r)}" for r in clips))
    print(f"夜段在样本内: {'✅ ' + str(nights) if nights else '❌ 无夜段（日志不含夜？）'}")
    print(f"\n▶ 一条命令产出（片段 + 汇总表 + 版本角标 /__gitstamp）：\n  {url}\n")

    if a.shots:
        outs = shots(a.base, log_rel, clips, Path(a.shots))
        print("截图:")
        for o in outs:
            print("  " + o)
    if a.measure:
        m = measure(f"{a.base}/index.html?log={log_rel}&round={clips[-1]}&still=1&view=default")
        mem = m.get("mem") or {}
        used = mem.get("used"); lim = mem.get("limit")
        print("实测（无头 Chromium，still 单帧）：")
        print(f"  日志→画面就绪: {m['render_s']} s")
        if used:
            print(f"  JS 堆: used={used/1e6:.1f} MB / limit={lim/1e6:.0f} MB")
        if m["pageerrors"]:
            print(f"  pageerror: {m['pageerrors']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
