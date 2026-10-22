#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R19 · 四子树逐文件 sha256 聚合指纹（`code_sha` 之外的代码身份硬证据）。

为什么需要：两臂跑的是**同一个 commit**，但 `code_sha` 分辨不出「工作区里被临时改过一个字符」。
本脚本对 `code/life` + `code/orchestration` + `code/config` + `code/engine` 下全部
`*.py` / `*.json` 逐文件 sha256，排序后聚合成一个 16 位指纹；两臂跑前跑后各算一次，
**四个指纹必须逐位相同**，否则「同代码对照」不成立。

口径与侦察员的复核脚本一致（同一子树列表、同一聚合方式 ≤ 排序 + sha256 拼接）。
用法（仓库根执行）：
    python3 v2/evidence/r19_topicbreadth_n8r24_seed42/fingerprint_4trees.py \
        --out v2/evidence/r19_topicbreadth_n8r24_seed42/run_off/fingerprint_before.txt
"""
from __future__ import annotations

import argparse
import hashlib
import os

SUBTREES = ("code/life", "code/orchestration", "code/config", "code/engine")
EXTS = (".py", ".json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="仓库根（默认按脚本位置推断）")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = args.root or os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

    files = []
    for sub in SUBTREES:
        base = os.path.join(root, sub)
        for dirpath, _dirnames, filenames in os.walk(base):
            for fn in filenames:
                if fn.endswith(EXTS):
                    full = os.path.join(dirpath, fn)
                    files.append((os.path.relpath(full, root).replace(os.sep, "/"), full))
    files.sort()

    lines = []
    for rel, full in files:
        h = hashlib.sha256()
        with open(full, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        lines.append(f"{h.hexdigest()}  {rel}")
    agg = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]

    out = [f"subtree_fingerprint = {agg}", f"n_files = {len(lines)}",
           "subtrees = " + ", ".join(SUBTREES), "", *lines, ""]
    text = "\n".join(out)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"subtree_fingerprint = {agg}  n_files = {len(lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
