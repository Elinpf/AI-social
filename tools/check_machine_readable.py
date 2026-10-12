#!/usr/bin/env python3
"""机器可读文件「可解析」检查 —— pre-commit「本次提交范围」（T242）

背景：sim-engine-stats-architect 提交时把 `tools/inert_registry.json` 写成**无效 JSON**
（Python 命令里 `"` 未转义），自己事后 `json.load` 才发现（`036f8c3` 修复）。
→ 同一族病：「写入了机器可读文件却没校验，发现得太晚」。跑一次 `json.load` 成本 0.1 秒。

范围（克制，只做"可解析"，不校验 schema 语义）：
- `*.json`  → `json.load`
- `*.jsonl` → 每行 `json.load`（报断行号）
- `*.yaml` / `*.yml` → `yaml.safe_load`（若环境无 PyYAML：**可见地**标 `skipped (no parser)`）
- `*.toml`  → `tomllib.load`（stdlib，Python≥3.11）
- 大文件 > `--size-cap`（默认 5 MiB）→ **跳过并打印 `skipped (size)`（可见，不静默）**

只读、无副作用。退出码：0 = 全通过（可含可见 skipped）；1 = 存在解析失败；2 = 用法错。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_SIZE_CAP = 5 * 1024 * 1024  # 5 MiB


def _read_text(p: Path) -> tuple[str | None, str | None]:
    try:
        return p.read_text(encoding="utf-8"), None
    except UnicodeDecodeError as e:
        return None, f"非 UTF-8（{e}）"
    except OSError as e:
        return None, f"读取失败（{e}）"


def check_json(p: Path, rel: str) -> list[str]:
    text, err = _read_text(p)
    if err:
        return [f"{rel}: {err}"]
    try:
        json.loads(text)
        return []
    except json.JSONDecodeError as e:
        return [f"{rel}:{e.lineno}:{e.colno}: JSON 解析失败：{e.msg}"]


def check_jsonl(p: Path, rel: str) -> list[str]:
    text, err = _read_text(p)
    if err:
        return [f"{rel}: {err}"]
    errs: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            errs.append(f"{rel}:{i}: JSONL 第 {i} 行解析失败：{e.msg}")
    return errs


def check_yaml(p: Path, rel: str) -> list[str]:
    try:
        import yaml  # noqa: WPS433 (optional dep, honest visible skip if absent)
    except ImportError:
        print(f"skipped (no parser): {rel} — 环境缺少 PyYAML")
        return []
    text, err = _read_text(p)
    if err:
        return [f"{rel}: {err}"]
    try:
        yaml.safe_load(text)
        return []
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        pos = f":{mark.line + 1}:{mark.column + 1}" if mark is not None else ""
        return [f"{rel}{pos}: YAML 解析失败：{e}"]


def check_toml(p: Path, rel: str) -> list[str]:
    try:
        import tomllib  # Python >= 3.11
    except ImportError:
        print(f"skipped (no parser): {rel} — 环境无 tomllib（Python<3.11）")
        return []
    try:
        with p.open("rb") as fh:
            tomllib.load(fh)
        return []
    except tomllib.TOMLDecodeError as e:
        return [f"{rel}: TOML 解析失败：{e}"]


_CHECKERS = {
    ".json": check_json,
    ".jsonl": check_jsonl,
    ".yaml": check_yaml,
    ".yml": check_yaml,
    ".toml": check_toml,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="机器可读文件可解析检查（T242）")
    ap.add_argument("--root", default=".")
    ap.add_argument("--paths-from-stdin", action="store_true",
                    help="从 stdin 逐行读取路径（pre-commit 提交范围）")
    ap.add_argument("--paths", nargs="*", default=None, help="直接给出路径")
    ap.add_argument("--size-cap", type=int, default=DEFAULT_SIZE_CAP,
                    help=f"超过此字节数跳过并打印 skipped (size)（默认 {DEFAULT_SIZE_CAP}）")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if args.paths_from_stdin:
        raw_paths = [s.strip() for s in sys.stdin.read().splitlines() if s.strip()]
    else:
        raw_paths = list(args.paths or [])

    errors: list[str] = []
    checked = skipped = 0
    for raw in raw_paths:
        p = Path(raw)
        if not p.is_absolute():
            p = root / raw
        if not p.is_file():
            continue
        checker = _CHECKERS.get(p.suffix.lower())
        if checker is None:
            continue  # 非机器可读目标格式：不处理（静默，非"跳过"语义）
        try:
            size = p.stat().st_size
        except OSError as e:
            errors.append(f"{raw}: stat 失败（{e}）")
            continue
        if size > args.size_cap:
            print(f"skipped (size): {raw} ({size} B > {args.size_cap} B)")
            skipped += 1
            continue
        checked += 1
        errors.extend(checker(p, raw))

    if errors:
        print("❌ 机器可读文件解析失败（本次提交范围）：")
        for e in errors:
            print(f"  - {e}")
        print(f"（checked={checked}, skipped(size)={skipped}）")
        return 1

    print(f"✅ 机器可读文件可解析（checked={checked}, skipped(size)={skipped}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
