"""G-1 源码旁证：按**函数名**寻址求函数体 sha（不吃行号移动）。

行号会因新增方法 `_gossip_hint` 与 3 个 hunk 移动，因此**禁止**按行号区间截取；
本脚本用 AST 取每个函数（含方法、嵌套）的 body 源码段做 sha256，按 `name` 与
`qualname` 双向对齐，两树/两提交之间只比"同名函数体的 sha 是否变化"。

用法：
    python3 v2/evidence/g1_func_sha.py --file code/life/agent.py --out /tmp/f.json
    python3 v2/evidence/g1_func_sha.py --rev d9391a3:code/life/agent.py --out /tmp/g.json
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path


def _read(path: str | None, rev: str | None) -> tuple[str, str]:
    if rev:
        src = subprocess.run(["git", "show", rev], capture_output=True, text=True, check=True).stdout
        return src, rev
    p = Path(path)
    return p.read_text(encoding="utf-8"), str(p)


def funcs(src: str) -> dict:
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    out = {}
    stack = []

    def walk(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = f"{prefix}{child.name}"
                body = child.body
                start = body[0].lineno - 1
                end = max((getattr(n, "end_lineno", None) or getattr(n, "lineno", 0))
                          for n in ast.walk(child))
                seg = "".join(lines[start:end])
                out[qual] = {
                    "body_sha256_16": hashlib.sha256(seg.encode("utf-8")).hexdigest()[:16],
                    "def_lineno": child.lineno,
                    "body_len_lines": end - (child.lineno - 1),
                }
                walk(child, qual + ".")
            else:
                walk(child, prefix)

    walk(tree)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="code/life/agent.py")
    ap.add_argument("--rev", default=None, help="如 d9391a3:code/life/agent.py")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    src, origin = _read(a.file, a.rev)
    rec = {"origin": origin, "n_funcs": len(funcs(src)), "funcs": funcs(src)}
    Path(a.out).write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print("origin =", origin, "| n_funcs =", rec["n_funcs"], "| out =", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
