#!/usr/bin/env python3
"""极简静态服务器（只用标准库），用于本地查看 frontend/。

浏览器需通过 http:// 访问（fetch 读 JSON/JSONL 受同源策略限制，file:// 会失败）。

用法（从 `code/` 或任意位置）：
    python frontend/tools/serve.py                 # http://127.0.0.1:8848/
    python frontend/tools/serve.py --port 9000
    python frontend/tools/serve.py --log /tmp/hitt_run.jsonl
        # 把一份外部日志拷进 sample/ 并以 ?log= 指向它，方便直接验收
"""
from __future__ import annotations

import argparse
import http.server
import json
import shutil
import socketserver
import subprocess
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]
REPO = FRONTEND.parents[1]   # …/code/frontend → …/social-experiment（git 根）


def git_stamp() -> dict:
    """当前 git 版本戳（只读）：sha + 是否有未提交改动。

    存在理由（T259 协调）：静态服务**直读磁盘**——只要 `frontend/` 有未提交改动，
    页面就**静默地换了版本**、分数**静默地失去归因**。让页面自己**可见**版本即可
    （**不做门禁**：未提交不一定错，可能正是开发中的人自己要看的）。
    """
    def _run(*a: str) -> str:
        try:
            return subprocess.run(["git", "-C", str(REPO), *a],
                                  capture_output=True, text=True, timeout=5).stdout
        except Exception:
            return ""
    sha = _run("rev-parse", "--short", "HEAD").strip() or "—"
    porcelain = _run("status", "--porcelain")   # 不 strip：保留首行行首状态位（否则首条路径被截）
    # porcelain 每行形如 "XY path"；取第 3 列起的路径
    files = [ln[3:].strip() for ln in porcelain.splitlines() if len(ln) > 3 and ln[2] == " "]
    fe = [f for f in files if f.startswith("code/frontend/")]
    return {"sha": sha, "dirty": bool(files), "dirty_files": files,
            "frontend_dirty": fe, "repo": REPO.name}


class Handler(http.server.SimpleHTTPRequestHandler):
    """静态服务 + 一个只读动态端点 `/__gitstamp`（实时返回 git 版本戳）。"""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(FRONTEND), **kw)

    def do_GET(self):   # noqa: N802（http.server 规定的名字）
        if self.path.split("?", 1)[0] == "/__gitstamp":
            body = json.dumps(git_stamp(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8848)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--log", default=None, help="外部日志文件；拷入 sample/ 后打印带 ?log= 的地址")
    args = ap.parse_args()

    url = f"http://{args.host}:{args.port}/"
    if args.log:
        src = Path(args.log).expanduser().resolve()
        if not src.exists():
            print(f"日志不存在: {src}", file=sys.stderr)
            return 2
        dst = FRONTEND / "sample" / src.name
        shutil.copyfile(src, dst)
        url += "?log=sample/" + src.name

    socketserver.TCPServer.allow_reuse_address = True   # 免 TIME_WAIT 绑定失败（重启更稳）
    with socketserver.TCPServer((args.host, args.port), Handler) as httpd:
        print(f"serving {FRONTEND}")
        print(f"open     {url}")
        print("Ctrl+C 结束")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nbye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
