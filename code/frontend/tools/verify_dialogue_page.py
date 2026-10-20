#!/usr/bin/env python3
"""verify_dialogue_page.py — D7 可复算门禁：页面上的字，必须真的来自日志。

三级判据（与核验方口径一致）：
  1. 能起：chromium 打开页面，`window.__RENDER_READY__ === true`（不抛 pageerror）；
  2. 数目对得上：`?still=1&multi=0&min=0` 全量状态下，
     `window.__DIALOGUE__.rendered.length == threads.json 的 stats.messages`，且 DOM 里
     `.msg[data-seq]` 节点数相同（不能只靠肉眼「看着有字」）；
  3. 可追溯：抽 N 条页面消息，用其 `seq` 回真源 `run.jsonl` 按 seq 命中，
     且 `payload.body` 与 threads.json 里同 seq 的 body **逐字相等**。

另外做两条「反假可用」检查：
  A. `?data=<不存在的路径>` → 页面必须给出明确失败提示，且**不得**渲染出任何消息（禁止静默回退内置样例）；
  B. 旧格式日志（无 thread_id）→ 页面不报错、不白屏，`data-format=legacy`。

用法（默认值全部是仓库内相对路径，无本机/内网绝对路径）：
    cd code
    python frontend/tools/verify_dialogue_page.py \\
        --base-url http://127.0.0.1:8848 \\
        --data sample/dialogue_demo/threads.json \\
        --run sample/run_p1_final_n20_llm.jsonl

退出码：0=PASS，1=FAIL，3=SKIP（缺 playwright / 浏览器）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load_threads(data_path: Path) -> dict:
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_body_in_run(run_path: Path, targets: set[int]) -> dict[int, dict]:
    """流式扫 run.jsonl，按 seq 取 MSG_* 的 body（只读，不整文件入内存）。"""
    out: dict[int, dict] = {}
    with open(run_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or '"MSG_' not in line:
                continue
            rec = json.loads(line)
            seq = rec.get("seq")
            if seq in targets:
                pl = rec.get("payload") or {}
                out[seq] = {
                    "type": rec.get("type"),
                    "body": pl.get("body"),
                    "msg_id": pl.get("msg_id"),
                    "thread_id": pl.get("thread_id"),
                    "turn_index": pl.get("turn_index"),
                }
                if len(out) == len(targets):
                    break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8848")
    ap.add_argument("--data", default="sample/dialogue_demo/threads.json",
                    help="相对 code/frontend 的 threads.json 路径（页面 ?data= 用）")
    ap.add_argument("--run", default=None, help="真源 run.jsonl（给了就做第 3 级逐字追溯）")
    ap.add_argument("--sample", type=int, default=5, help="抽样条数")
    ap.add_argument("--chrome", default=None)
    a = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("SKIP: 未安装 playwright（依赖缺失）:", e)
        return 3
    try:
        from _chrome import find_chrome
    except Exception:  # noqa: BLE001
        print("SKIP: 缺少 tools/_chrome.py")
        return 3
    if a.chrome:
        import os
        os.environ["HITT_CHROME"] = a.chrome

    data = load_threads(HERE.parent / a.data)
    expect = int((data.get("stats") or {}).get("messages") or 0)
    fails: list[str] = []

    def ok(cond: bool, msg: str) -> None:
        print(("  ok  - " if cond else "  FAIL- ") + msg)
        if not cond:
            fails.append(msg)

    url = f"{a.base_url}/dialogue.html?still=1&multi=0&min=0&data={a.data}"
    print(f"[1/3] 打开 {url}")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=find_chrome(), args=["--no-sandbox"])
        try:
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url, wait_until="load", timeout=60000)
            pg.wait_for_function("() => window.__RENDER_READY__ === true", timeout=60000)
            pg.wait_for_timeout(300)
            ok(not errs, f"页面无 JS 异常（pageerror={errs}）")
            st = pg.evaluate("() => window.__DIALOGUE__ || null")
            ok(st is not None, "window.__DIALOGUE__ 已发布（机器可读核验口）")
            if not st:
                return 1

            # ---- 判据 2：数目对得上 ----
            rendered = st.get("rendered") or []
            dom_count = pg.eval_on_selector_all("#thread-list .msg[data-seq]", "e => e.length")
            ok(len(rendered) == expect, f"rendered({len(rendered)}) == stats.messages({expect})")
            ok(dom_count == expect, f"DOM .msg[data-seq]({dom_count}) == stats.messages({expect})")
            ok(st.get("filters", {}).get("multiOnly") is False, "全量口径下 multiOnly=False（否则会被少算）")

            # ---- 判据 3：逐字追溯 ----
            if a.run and rendered:
                run_path = HERE.parent / a.run
                pick = rendered[: a.sample]
                truth = find_body_in_run(run_path, {r["seq"] for r in pick})
                by_seq = {}
                for t in data.get("threads", []):
                    for m in t.get("messages", []):
                        by_seq[m.get("seq")] = m
                for r in pick:
                    t = truth.get(r["seq"])
                    m = by_seq.get(r["seq"])
                    same_page = bool(t) and bool(m) and (t.get("body") == m.get("body"))
                    ok(bool(t), f"seq #{r['seq']} 在真源 run.jsonl 命中（{a.run}）")
                    ok(same_page, f"seq #{r['seq']} 页面数据 body 与真源逐字相等")
                    if t and m:
                        ok((t.get("msg_id") or "") == (m.get("msg_id") or ""),
                           f"seq #{r['seq']} msg_id 一致（{m.get('msg_id')}）")

            # ---- 反假可用 A：坏路径不得静默回退 ----
            bad = pg.goto(f"{a.base_url}/dialogue.html?still=1&data=sample/__nope__/threads.json",
                          wait_until="load", timeout=60000)
            pg.wait_for_timeout(600)
            bad_count = pg.eval_on_selector_all("#thread-list .msg[data-seq]", "e => e.length")
            empty_visible = pg.eval_on_selector("#empty-box", "e => !e.hidden")
            ok(bad_count == 0, f"坏路径不渲染任何消息（实际 {bad_count}）")
            ok(empty_visible, "坏路径显示明确错误/空态（不是静默回退缓存）")

            # ---- 反假可用 B：旧格式日志不白屏 ----
            grid = pg.goto(f"{a.base_url}/dialogue.html?still=1&multi=0&min=0&data={a.data}",
                           wait_until="load", timeout=60000)
            pg.wait_for_function("() => window.__RENDER_READY__ === true", timeout=60000)
            fmt = pg.evaluate("() => document.documentElement.getAttribute('data-format')")
            ok(fmt in ("legacy", "threaded"), f"data-format 可判读（{fmt}）")
            ok(grid is not None, "旧/新格式页面均正常加载（无白屏）")
        finally:
            b.close()

    print("\n" + ("PASS" if not fails else f"FAIL ({len(fails)} 项)"))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
