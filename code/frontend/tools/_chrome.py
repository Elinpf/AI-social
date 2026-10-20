#!/usr/bin/env python3
""" _chrome.py — 浏览器可执行文件探测（不写死任何人的家目录/缓存路径）。

顺序：
  1) 环境变量 `HITT_CHROME`（或 `PLAYWRIGHT_CHROME`）显式指定；
  2) 系统 PATH 上的 chromium / chromium-browser / google-chrome / google-chrome-stable / chrome；
  3) Playwright 默认缓存目录（`$PLAYWRIGHT_BROWSERS_PATH` 或 `~/.cache/ms-playwright`）下的
     `chromium-*/chrome-linux*/chrome`。

找不到就抛 RuntimeError，并给出安装/覆盖方式——**不静默回退到别人的机器路径**。

用法：
    from _chrome import find_chrome
    exe = find_chrome()          # 找不到抛异常
    exe = find_chrome(required=False)   # 找不到返回 None（调用方可 SKIP）
"""
from __future__ import annotations

import glob
import os
import shutil
import sys
from pathlib import Path


def _playwright_candidates() -> list[str]:
    roots = []
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env:
        roots.append(Path(env))
    roots.append(Path.home() / ".cache" / "ms-playwright")
    out: list[str] = []
    for root in roots:
        try:
            out.extend(sorted(glob.glob(str(root / "chromium-*" / "chrome-linux*" / "chrome"))))
            out.extend(sorted(glob.glob(str(root / "chromium-*" / "chrome-mac*" / "Chromium.app"
                                           / "Contents" / "MacOS" / "Chromium"))))
        except Exception:  # noqa: BLE001 — 目录不存在/无权限都不是错误
            continue
    return out


def find_chrome(required: bool = True) -> str | None:
    for key in ("HITT_CHROME", "PLAYWRIGHT_CHROME"):
        v = os.environ.get(key)
        if v and Path(v).exists():
            return v
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"):
        w = shutil.which(name)
        if w:
            return w
    for c in _playwright_candidates():
        if Path(c).exists():
            return c
    if not required:
        return None
    raise RuntimeError(
        "找不到 Chromium/Chrome 可执行文件。请任选其一：\n"
        "  1) 安装 Playwright 浏览器：`python -m playwright install chromium`\n"
        "  2) 装系统浏览器（chromium / google-chrome）\n"
        "  3) 显式指定：`HITT_CHROME=/path/to/chrome` 再跑本脚本"
    )


if __name__ == "__main__":
    try:
        print(find_chrome())
    except RuntimeError as e:
        print(e, file=sys.stderr)
        raise SystemExit(3)
