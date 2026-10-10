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
import functools
import http.server
import shutil
import socketserver
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]


def handler_for(directory: str):
    return functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)


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

    with socketserver.TCPServer((args.host, args.port), handler_for(str(FRONTEND))) as httpd:
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
