#!/usr/bin/env python3
"""D10 C-A 专用：渲染**指定线程**的真实截图（复用 `render_shots.py` 的同一条链路）。

为什么需要它：`render_shots.py` 的 `chat` 视图只渲染页面默认选中的那条线程，
无法指定 `thread`。而 C-A 要佐证的是「**同一角色对在同一条线程里，称呼随轮次变化**」，
必须能把那一条线程单独截出来。本脚本**不修改** `render_shots.py`，只 import 它的
`build_serve_root` / `start_server` / `VIEWS` / `SHOT` / `GEN_THREADS` 常量与函数，
链路完全一致：

    run.jsonl ──gen_threads.py──▶ threads.json ──(本地静态服务)──▶ shot.py(Chromium)──▶ PNG

前端支持 `dialogue.html?thread=<thread_id>`（`code/frontend/src/dialogue.js:469` 实读），
故本脚本只是在同一 URL 上多带一个 `thread=` 参数。

纪律：只读既有日志、零跑批、零 LLM、不写 `code/`；只认本次现截（旧图先删）；
三件套（run 目录 / 渲染命令 / 日志 sha256）逐张写进 report JSON。

用法：
  python3 tools/metrics/d10_thread_shot.py \
      --run-dir v2/evidence/d9m-ab-on_n16r24_s42 --batch-id D10-addr \
      --thread TH-P013-P004-15 \
      --outdir v2/evidence/d10_address_shots --timeout 180
退出码：0 成功；1 截图失败；2 前置条件缺失。
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_shots as RS  # noqa: E402  复用同一条链路（不改它）


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--thread", required=True, help="thread_id，如 TH-P013-P004-15")
    ap.add_argument("--view", default="chat")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--retry-blank", type=int, default=2)
    ap.add_argument("--subset-thread", action="store_true",
                    help="把 threads.json 的 threads[] 过滤成**只含 --thread 这一条**再渲染（消息逐字节不改）。"
                         "用途：前端 `thread=` 参数实测只展开卡片、不切换视口，故用单线程数据把目标线程放到首屏。"
                         "过滤行为会逐项写进 render_report，且原全批图同时保留。")
    a = ap.parse_args()

    run_dir = Path(a.run_dir).resolve()
    log = run_dir / "run.jsonl"
    if not log.exists():
        print(f"[FAIL] 缺少 {log}", file=sys.stderr)
        return 2
    if a.view not in RS.VIEWS:
        print(f"[FAIL] 未知视图 {a.view}", file=sys.stderr)
        return 2

    outdir = Path(a.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    log_sha = RS.sha256_file(log)

    threads_json = outdir / f"threads_{a.batch_id}.json"
    cmd_gen = [sys.executable, str(RS.GEN_THREADS), "--log", str(log),
               "--out", str(threads_json), "--label", a.batch_id]
    meta = run_dir / "meta.json"
    if meta.exists():
        cmd_gen[4:4] = ["--meta", str(meta)]
    print("[1/3] gen_threads: " + " ".join(cmd_gen), file=sys.stderr)
    r = subprocess.run(cmd_gen, capture_output=True, text=True)
    sys.stderr.write((r.stdout or "")[-1500:] + (r.stderr or "")[-1500:])
    if r.returncode != 0 or not threads_json.exists():
        print(f"[FAIL] gen_threads rc={r.returncode}", file=sys.stderr)
        return 1
    thr_sha = RS.sha256_file(threads_json)

    d = json.loads(threads_json.read_text(encoding="utf-8"))
    tids = [t.get("thread_id") or t.get("id") for t in (d.get("threads") or [])]
    if a.thread not in tids:
        print(f"[FAIL] threads.json 中不存在线程 {a.thread}（共 {len(tids)} 条）", file=sys.stderr)
        return 2
    subset_note = None
    if a.subset_thread:
        keep = [t for t in (d.get("threads") or []) if (t.get("thread_id") or t.get("id")) == a.thread]
        if len(keep) != 1:
            print(f"[FAIL] 过滤后线程数 != 1（{len(keep)}）", file=sys.stderr)
            return 2
        subset_note = {
            "filtered": "threads[]",
            "kept_thread": a.thread,
            "threads_before": len(d.get("threads") or []),
            "threads_after": 1,
            "messages_in_kept_thread": len(keep[0].get("messages") or keep[0].get("msgs") or []),
            "note": "只删 threads[] 里的其它线程；被保留线程的消息逐字节未改；"
                    "页面顶部批次级计数（消息数/轮次等）仍是**全批**值，不随过滤变化。",
        }
        d["threads"] = keep
        d.setdefault("subset_filter", subset_note)
        threads_json = outdir / f"threads_{a.batch_id}_subset1.json"
        threads_json.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        thr_sha = RS.sha256_file(threads_json)

    src = d.get("source") or {}
    run_sha = src.get("run_sha256") or ""
    sha8 = (run_sha.split(":")[-1] if ":" in run_sha else run_sha)[:8]

    stem = f"dialogue_{a.batch_id}"
    tmp = Path(tempfile.mkdtemp(prefix="hitt_thread_shot_"))
    httpd = None
    try:
        root = RS.build_serve_root(tmp, threads_json, stem)
        httpd, port = RS.start_server(root)
        base = f"http://127.0.0.1:{port}"
        data_rel = f"sample/{stem}/threads.json"
        w, h, q = RS.VIEWS[a.view]
        png = outdir / f"{a.batch_id}-{a.view}-{a.thread}-{sha8}.png"
        if png.exists():
            png.unlink()
        url = f"{base}/dialogue.html?{q}&data={data_rel}&thread={a.thread}"
        cmd = [sys.executable, str(RS.SHOT), "--url", url, "--out", str(png),
               "--width", str(w), "--height", str(h), "--timeout", str(a.timeout),
               "--retry-blank", str(a.retry_blank)]
        print("[2/3] shot: " + " ".join(cmd), file=sys.stderr)
        rs = subprocess.run(cmd, capture_output=True, text=True)
        tail = ((rs.stdout or "") + (rs.stderr or "")).strip()
        print(tail[-1200:], file=sys.stderr)
        rec = {
            "thread_id": a.thread,
            "view": a.view,
            "png": str(png),
            "rc": rs.returncode,
            "url": url,
            "triplet": {"run_dir": str(run_dir), "log": str(log), "log_sha256": log_sha,
                        "threads_json": str(threads_json), "threads_json_sha256": thr_sha,
                        "gen_threads_cmd": " ".join(cmd_gen), "render_cmd": " ".join(cmd)},
        }
        if png.exists():
            rec["png_sha256"] = RS.sha256_file(png)
            rec["png_bytes"] = png.stat().st_size
            rec["pixel_selfcheck"] = RS.pixel_selfcheck(png)
    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        shutil.rmtree(tmp, ignore_errors=True)

    rep = {"schema_version": "d10-thread-shot/1.0", "batch_id": a.batch_id,
           "run_dir": str(run_dir), "log_sha256": log_sha,
           "threads_json_sha256": thr_sha, "shot": rec}
    rp = outdir / f"render_report_{a.batch_id}_{a.thread}.json"
    rp.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False, indent=1), file=sys.stderr)
    print(f"[3/3] wrote {png} , {rp}")
    return 0 if rec.get("rc") == 0 and rec.get("png_sha256") else 1


if __name__ == "__main__":
    sys.exit(main())
