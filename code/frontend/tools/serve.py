#!/usr/bin/env python3
"""极简静态服务器（只用标准库），用于本地查看 frontend/。

⚠️ **这是本地开发服务，不是可对外暴露的服务**：动态端点只读、且仅限白名单根内。
浏览器需通过 http:// 访问（fetch 读 JSON/JSONL 受同源策略限制，file:// 会失败）。

用法（从 `code/` 或任意位置）：
    python frontend/tools/serve.py                 # http://127.0.0.1:8848/
    python frontend/tools/serve.py --port 9000
    python frontend/tools/serve.py --log /tmp/hitt_run.jsonl
        # 把一份外部日志拷进 sample/ 并以 ?log= 指向它，方便直接验收

端点：
    GET /__gitstamp                      → 当前 git sha + dirty（只读）
    GET /__tail?path=<abs>&off=<byte>[&tailmb=N]
        → 只读**增量尾部**（供"实时跟随"）：path 必须落在白名单根内
          （env `HITT_LIVE_ROOTS`，冒号分隔，默认 `/root/t271/runs`；realpath 规范化后判断，防穿越）；
          off 缺省或首轮时按 `tailmb` 从末尾回退 N MB（默认 4MB）并**对齐到完整行边界**；
          返回 {text, off, size, eof, truncated}（text 只含到最后一个 `\n`）。
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import re
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


def _live_roots() -> list[Path]:
    raw = os.environ.get("HITT_LIVE_ROOTS", "/root/t271/runs")
    return [Path(p).resolve() for p in raw.split(":") if p.strip()]


def _allowed_live(p) -> bool:
    """realpath（非 strict，允文件尚未出现）规范化后判是否落在白名单根内（防 `..` / 符号链接穿越）。"""
    rp = Path(os.path.realpath(str(p)))
    for root in _live_roots():
        try:
            rp.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def tail_read(path: str, off: int | None, tail_mb: int = 4) -> dict:
    """只读增量尾部。off=None ⇒ 从末尾回退 tail_mb MB 并对齐到完整行边界。绝不返回半行。
    文件尚不存在（批未起跑/尚未落盘）⇒ 返回 waiting=True（不是错误，避免误报"越权"）。"""
    p = Path(path)
    if not _allowed_live(p):
        return {"error": "path not allowed (whitelist: HITT_LIVE_ROOTS)"}
    if not p.exists():
        return {"text": "", "off": 0, "size": 0, "eof": False, "truncated": False, "waiting": True}
    try:
        size = p.stat().st_size
    except Exception as e:
        return {"error": f"stat failed: {e}"}
    if off is None:
        start = max(0, size - max(1, tail_mb) * 1024 * 1024)
        trunc = start > 0
    else:
        start = max(0, min(int(off), size))
        trunc = False
    with p.open("rb") as f:
        f.seek(start)
        if trunc and start > 0:            # 跳过半个首行
            f.readline()
            start = f.tell()
        buf = f.read()
    nl = buf.rfind(b"\n")
    if nl < 0:
        text, real_off = "", start       # 还没有完整行
    else:
        text = buf[:nl + 1].decode("utf-8", errors="replace")
        real_off = start + nl + 1
    return {"text": text, "off": real_off, "size": size, "eof": real_off >= size, "truncated": trunc}


def run_info(run_path: str) -> dict:
    """批运行信息（只读）：从同目录 meta.json / heartbeat.tsv 判『是否已结束』。
    供 `?z=live` 在批结束后显示『跟随已结束（批已完成）· 可回放』，而非看起来像坏了。"""
    p = Path(run_path)
    if not _allowed_live(p):
        return {"error": "path not allowed (whitelist: HITT_LIVE_ROOTS)"}
    d = p.parent
    info: dict = {"exists": p.exists(), "ended": False, "size": 0}
    try:
        info["size"] = p.stat().st_size if p.exists() else 0
    except Exception:
        pass
    meta = d / "meta.json"
    if meta.exists():
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
            for k in ("batch", "started_at", "ended_at", "sha", "world_layer_sha", "time_model", "feature_set"):
                if m.get(k) is not None:
                    info[k] = m[k]
            info["ended"] = bool(m.get("ended_at"))
        except Exception:
            pass
    hb = d / "heartbeat.tsv"
    if hb.exists():
        try:
            last = hb.read_text(encoding="utf-8").strip().splitlines()[-1].split("\t")
            info["last_hb"] = last
            if len(last) >= 2 and last[1] == "EXIT":
                info["ended"] = True
            if len(last) >= 3:
                try:
                    info["last_round"] = int(last[2])
                except Exception:
                    pass
        except Exception:
            pass
    # T374 `END` 标记（最权威，派生汇总、不改既有源）→ 优先读；其余兜底。
    endf = d / "END"
    if endf.exists():
        try:
            e = json.loads(endf.read_text(encoding="utf-8"))
            for k in ("rc", "started_at", "ended_at", "rounds_last", "events", "final_state_hash", "tree", "sha"):
                if e.get(k) is not None:
                    info[k] = e[k]
            info["ended"] = True
            info["end_source"] = "END"
        except Exception:
            pass
    # 三态真源：host.log 的 `[runner] batch exited rc=N`（既有真源，兜底）+ meta.ended_at
    hl = d / "host.log"
    if hl.exists():
        try:
            rc = None
            for ln in hl.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.search(r"\[runner\]\s*batch exited\s+rc=(-?\d+)", ln)
                if m:
                    rc = int(m.group(1))
            if rc is not None:
                info["rc"] = rc
                info["ended"] = True
        except Exception:
            pass
    # 三态：running / done(rc=0) / failed(rc≠0)；无 rc 但有 ended_at ⇒ done（保守）
    if info.get("rc") is not None:
        info["state"] = "done" if info["rc"] == 0 else "failed"
    elif info.get("ended"):
        info["state"] = "done"
    else:
        info["state"] = "running"
    return info


class Handler(http.server.SimpleHTTPRequestHandler):
    """静态服务 + 只读动态端点 `/__gitstamp` / `/__tail`。**本地开发用，非对外服务。**"""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(FRONTEND), **kw)

    def _json(self, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):   # noqa: N802（http.server 规定的名字）
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        if u.path == "/__gitstamp":
            self._json(git_stamp())
            return
        if u.path == "/__tail":
            q = parse_qs(u.query)
            off = int(q["off"][0]) if q.get("off") and q["off"][0] not in ("", "null") else None
            tailmb = int(q["tailmb"][0]) if q.get("tailmb") else 4
            self._json(tail_read(q.get("path", [""])[0], off, tailmb))
            return
        if u.path == "/__runinfo":
            q = parse_qs(u.query)
            self._json(run_info(q.get("path", [""])[0]))
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
