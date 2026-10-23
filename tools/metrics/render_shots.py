#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键渲染真实截图（**只读既有日志、零跑批、零 LLM**）。

把「给一个 run 目录 → 出可溯源 PNG」这条链落盘化，链路上**不改** `code/frontend/` 任何文件：
    源 run.jsonl ──gen_threads.py──▶ threads.json ──(本地静态服务)──▶ shot.py(Chromium 现场截图)──▶ PNG

为什么需要它（`Q-20`）：D12-H 的渲染链断在「没有 threads.json ⇒ 没有 PNG」，
`v2/evidence/d12h_shots/` 只有渲染脚本、0 张 PNG。本脚本把缺的那一段（派生 threads.json + 起服务 + 落三件套）补齐。

## 截图三件套纪律（`reports/README.md:116` 原文要求）
每张图必须可溯源到 **① 来源 run 目录 + ② 渲染命令 + ③ 日志 sha256**，
文件名格式 `<batch_id>-<视图>-<sha8>.png`。本脚本把三件套逐张写进 `render_report.json`，
**禁止拼图、禁止跨批混拼、禁止用历史旧图冒充**（本脚本只现算、现截，不复用任何既有 PNG）。

## 隔离做法（关键：不碰 `code/`）
不在 `code/frontend/sample/` 下写 threads.json（那属于 `code/`，跑批/冻结期不得改动）。
改为建一个临时目录，**符号链接** `code/frontend/*`（`sample` 除外），并把本次的 `threads.json`
放进临时目录自己的 `sample/<stem>/` 下 —— 前端代码与素材一字未变，磁盘上也不产生 `code/` 新文件。

## 用法
    python3 tools/metrics/render_shots.py \
        --run-dir <RUN 目录（含 run.jsonl）> \
        --batch-id D12-H \
        --outdir v2/evidence/form_metrics/shots \
        [--views chat,rhythm] [--timeout 180]

退出码：0 全成功 / 1 有视图失败（逐条记录 rc） / 2 前置条件缺失（日志或依赖不存在）
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True          # 不在 code/ 下留 __pycache__

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FRONTEND = REPO / "code" / "frontend"
GEN_THREADS = FRONTEND / "tools" / "gen_threads.py"
SHOT = FRONTEND / "tools" / "shot.py"

# 视图定义：(名字, 宽, 高, query)
VIEWS = {
    "chat": (1400, 900, "still=1&multi=1&min=0&sort=turns"),
    "rhythm": (1300, 1050, "still=1&multi=1&min=0&view=rhythm"),
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_serve_root(tmp: Path, threads_json: Path, stem: str) -> Path:
    """临时服务根：symlink code/frontend/*，sample 用真实目录只放本次 threads.json。"""
    for entry in sorted(FRONTEND.iterdir()):
        if entry.name == "sample":
            continue
        (tmp / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    sample = tmp / "sample" / stem
    sample.mkdir(parents=True, exist_ok=True)
    # 必须用**绝对路径**建链：相对目标会被解析成「相对链接所在目录」⇒ 断链 ⇒ 前端 404 ⇒ 永不 ready
    # （这个坑在首轮实测里真的踩过，见 README「渲染链断点」）
    (sample / "threads.json").symlink_to(threads_json.resolve())
    return tmp


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):      # 不刷屏；错误仍由 shot.py 的 rc 暴露
        pass


def pixel_selfcheck(png: Path) -> dict:
    """本脚本自算的「非空白」自检（替代 shot.py 对深色页面的假红判据）。

    判据（写死，对深色 UI 有效）：
      distinct_colors ≥ 200 且 top_color_frac ≤ 99% ⇒ OK；否则 SUSPECT（可能真空白）。
    同时报非背景像素占比 non_bg_frac（与最常见色曼哈顿距离 >24 的像素占比），供人工复核。
    """
    try:
        from PIL import Image
    except Exception as e:  # noqa: BLE001
        return {"status": "SKIP", "reason": f"PIL 不可用: {type(e).__name__}: {e}"}
    from collections import Counter

    im = Image.open(png).convert("RGB")
    px = list(im.getdata())
    n = len(px)
    c = Counter(px)
    mc, top = c.most_common(1)[0]
    non_bg = sum(1 for p in px if abs(p[0] - mc[0]) + abs(p[1] - mc[1]) + abs(p[2] - mc[2]) > 24)
    distinct = len(c)
    top_frac = top / n if n else 1.0
    ok = distinct >= 200 and top_frac <= 0.99
    return {"status": "OK" if ok else "SUSPECT", "width": im.width, "height": im.height,
            "distinct_colors": distinct, "top_color": list(mc),
            "top_color_frac": round(top_frac, 4),
            "non_bg_frac": round(non_bg / n, 4) if n else None,
            "rule": "distinct_colors ≥ 200 且 top_color_frac ≤ 0.99 ⇒ OK（深色 UI 不按单色占比判死）"}


def start_server(root: Path):
    handler = partial(_Quiet, directory=str(root))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    return httpd, httpd.server_address[1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="一键渲染真实截图（只读既有日志）")
    ap.add_argument("--run-dir", required=True, help="含 run.jsonl 的跑批目录（必须是已收批）")
    ap.add_argument("--batch-id", required=True, help="批次标签，用于 PNG 文件名 <batch>-<视图>-<sha8>.png")
    ap.add_argument("--outdir", required=True, help="输出目录（PNG + threads.json + render_report.json）")
    ap.add_argument("--views", default="chat,rhythm", help="逗号分隔，可选 chat / rhythm")
    ap.add_argument("--timeout", type=float, default=180.0, help="单张截图等就绪超时（秒）")
    ap.add_argument("--retry-blank", type=int, default=2, help="空白帧取证容错重试次数（不降判据）")
    ap.add_argument("--blank-check", choices=["off", "shot"], default="off",
                    help="off（默认）：不给 shot.py 传空白判据，改用本脚本自算的像素自检；"
                         "shot：沿用 shot.py 的单色判据（对 dialogue.html 这种深色页面会误判为空白）")
    a = ap.parse_args(argv)

    run_dir = Path(a.run_dir).resolve()
    log = run_dir / "run.jsonl"
    meta = run_dir / "meta.json"
    if not log.exists():
        print(f"[FAIL] 缺少 {log}", file=sys.stderr)
        return 2
    if not GEN_THREADS.exists() or not SHOT.exists():
        print(f"[FAIL] 渲染工具缺失：{GEN_THREADS} / {SHOT}", file=sys.stderr)
        return 2
    try:
        import playwright  # noqa: F401
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] 未安装 python playwright，无法截图：{type(e).__name__}: {e}", file=sys.stderr)
        return 2

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    outdir_abs = outdir.resolve()
    log_sha = sha256_file(log)

    # ---- 1) 派生 threads.json（落在 outdir，不落 code/）
    threads_json = outdir_abs / f"threads_{a.batch_id}.json"   # 按批命名，两批并存不互相覆盖
    cmd_gen = [sys.executable, str(GEN_THREADS), "--log", str(log),
               "--out", str(threads_json), "--label", a.batch_id]
    if meta.exists():
        cmd_gen[4:4] = ["--meta", str(meta)]
    print("[1/4] gen_threads: " + " ".join(cmd_gen), file=sys.stderr)
    r = subprocess.run(cmd_gen, capture_output=True, text=True)
    sys.stderr.write(r.stdout[-2000:] + r.stderr[-2000:])
    if r.returncode != 0 or not threads_json.exists():
        print(f"[FAIL] gen_threads rc={r.returncode}", file=sys.stderr)
        return 1
    thr_sha = sha256_file(threads_json)

    d = json.loads(threads_json.read_text(encoding="utf-8"))
    src = d.get("source") or {}
    run_sha = src.get("run_sha256") or ""
    run_label = src.get("run_label") or a.batch_id
    sha8 = (run_sha.split(":")[-1] if ":" in run_sha else run_sha)[:8]
    if not sha8:
        print("[FAIL] threads.json 缺 source.run_sha256 ⇒ 文件名无法溯源", file=sys.stderr)
        return 2
    stem = f"dialogue_{a.batch_id}"
    print(f"[2/4] threads.json {thr_sha[:16]}…  run_sha256={run_sha[:16]}…  sha8={sha8}  "
          f"threads={len(d.get('threads') or [])}", file=sys.stderr)

    # ---- 2) 临时服务根 + 本地静态服务（daemon 线程，进程退出即回收，不 kill 任何外部进程）
    tmp = Path(tempfile.mkdtemp(prefix="hitt_render_"))
    results = []
    httpd = None
    try:
        root = build_serve_root(tmp, threads_json, stem)
        httpd, port = start_server(root)
        base = f"http://127.0.0.1:{port}"
        print(f"[3/4] static server {base}  root={root}", file=sys.stderr)
        data_rel = f"sample/{stem}/threads.json"

        wanted = [v.strip() for v in a.views.split(",") if v.strip()]
        for view in wanted:
            if view not in VIEWS:
                print(f"[WARN] 未知视图 {view}，跳过（可选 {list(VIEWS)}）", file=sys.stderr)
                continue
            w, h, q = VIEWS[view]
            png = outdir_abs / f"{a.batch_id}-{view}-{sha8}.png"
            if png.exists():
                png.unlink()          # 只认本次现截，绝不复用旧图
            url = f"{base}/dialogue.html?{q}&data={data_rel}"
            cmd = [sys.executable, str(SHOT), "--url", url, "--out", str(png),
                   "--width", str(w), "--height", str(h), "--timeout", str(a.timeout),
                   "--retry-blank", str(a.retry_blank)]
            if a.blank_check == "off":
                # 依据 shot.py 自身 docstring：「--no-blank-check 用于非小镇画布的普通页面：
                # 深色/大色块页面会被误判为空白」。dialogue.html 是**深色**页面，
                # 其单色判据（max_color_frac ≥50%）在实测中把**正常渲染**的页面判成空白（80.09%），
                # 属**假红**。故此处改用本脚本的像素自检（见 pixel_selfcheck），并把该缺陷写进 README。
                cmd.append("--no-blank-check")
            print(f"[4/4] shot {view}: " + " ".join(cmd), file=sys.stderr)
            rs = subprocess.run(cmd, capture_output=True, text=True)
            tail = (rs.stdout or "") + (rs.stderr or "")
            print(tail[-1500:], file=sys.stderr)
            rec = {
                "view": view,
                "png": str(png),
                "rc": rs.returncode,
                "shot_stdout_tail": tail.strip().splitlines()[-3:] if tail.strip() else [],
                "triplet": {
                    "run_dir": str(run_dir),
                    "mock_log_sha256": None,
                    "log": str(log),
                    "log_sha256": log_sha,
                    "threads_json": str(threads_json),
                    "threads_json_sha256": thr_sha,
                    "render_cmd": " ".join(cmd),
                    "gen_threads_cmd": " ".join(cmd_gen),
                },
            }
            if png.exists():
                st = png.stat()
                rec["pixel_selfcheck"] = pixel_selfcheck(png)
                rec.update({"png_sha256": sha256_file(png), "png_bytes": st.st_size,
                            "png_mtime_ns": st.st_mtime_ns,
                            "png_mtime_iso": __import__("datetime").datetime.fromtimestamp(
                                st.st_mtime).astimezone().isoformat(timespec="seconds")})
            results.append(rec)
    finally:
        if httpd is not None:
            httpd.shutdown()          # 只停本进程内的 daemon 服务，不触碰任何外部进程
            httpd.server_close()
        shutil.rmtree(tmp, ignore_errors=True)

    report = {
        "schema_version": "render-shots/1.0",
        "batch_id": a.batch_id,
        "run_dir": str(run_dir),
        "log": str(log),
        "log_sha256": log_sha,
        "threads_json": str(threads_json),
        "threads_json_sha256": thr_sha,
        "run_sha256_in_threads": run_sha,
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(
            timespec="seconds"),
        "views": results,
        "ok_count": sum(1 for x in results if x["rc"] == 0 and x.get("png_sha256")),
        "fail_count": sum(1 for x in results if x["rc"] != 0 or not x.get("png_sha256")),
        "policy": {
            "no_stitching": "每张图独立截图，禁止拼图/跨批混拼",
            "no_reuse": "输出同名 PNG 若已存在则先删除，只认本次现截",
        "blank_check": ("自行像素自检（distinct_colors/top_color_frac/non_bg_frac 逐张落盘）；"
                        "未沿用 shot.py 的单色判据——该判据对深色 dialogue.html 会假红（实测 80.09% 误判）"),
            "code_untouched": "服务根为临时目录 + 符号链接；未在 code/frontend 下写入任何文件",
        },
    }
    rp = outdir_abs / f"render_report_{a.batch_id}.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                  encoding="utf-8")
    print(json.dumps({"report": str(rp), "report_sha256": sha256_file(rp),
                      "threads_json_sha256": thr_sha,
                      "ok_count": report["ok_count"], "fail_count": report["fail_count"],
                      "pngs": [{"view": x["view"], "png": x["png"], "rc": x["rc"],
                                "png_sha256": x.get("png_sha256"),
                                "png_bytes": x.get("png_bytes")} for x in results]},
                     ensure_ascii=False, indent=2))
    return 0 if report["fail_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
