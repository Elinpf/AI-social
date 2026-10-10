#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""术语合规检查器（青溪镇 Lexicon linter）· v3（可操作化：行号 + 建议替换）。

在 v2（基线/棘轮、mention vs violation）基础上，把输出变成**可操作的**：
- 每条违规**直接打印**：① 精确 `文件:行:列` + 原文片段；② **建议替换**（取自
  `lexicon.json` 的 `forbidden[].canonical`，并给「族」写法如 `OFFER_*`）；
- **命名空间错**（如 `INTENT.OFFER` 应为 `INTENT.ECON.OFFER`）给出专门提示；
- 若疑似**合法提及**（别名/映射），提示「可加提及标记（`→` / 已废弃 / 写 `OFFER_*`）」。

保留 v2 能力：`mention vs violation`、基线/棘轮（`--baseline`，仅"基线外新违规"非 0）、
`--update-baseline`、`--show-baseline`、`--dir-stats`、`--json`。

用法：
    python glossary/tools/lint_terms.py --root .
    python glossary/tools/lint_terms.py --root . --baseline glossary/term_baseline.json
    python glossary/tools/lint_terms.py --root . --update-baseline glossary/term_baseline.json

无第三方依赖，仅标准库。
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterator

MD_GLOBS = ("**/*.md",)
PY_GLOBS = ("code/**/*.py",)
EXCLUDE_DIR_PARTS = {
    "glossary", "__pycache__", ".pytest_cache", ".git", "node_modules",
    "data", "freeze_cache", "licenses",
}
EXCLUDE_SUFFIXES = {".jsonl"}

HISTORICAL_DIRS = {"v1"}

MENTION_MARKERS = (
    "→", "->", "⇒", "=>",
    "已废弃", "废弃", "已并入", "并入", "不新增", "已裁定", "需统一", "已统一",
    "已登记", "已改为", "改为", "替代", "不设", "旧稿", "旧称", "禁用",
    "已关闭", "已解决", "统一到", "采用 08", "采纳 08", "旧", "弃", "vs", "对照",
)

#: 命名空间映射：命中「错命名空间」时给出的正确写法
NAMESPACE_HINTS = (
    (re.compile(r"INTENT\.OFFER\b"), "INTENT.ECON.OFFER",
     "命名空间错：`INTENT.OFFER` → 应为 `INTENT.ECON.OFFER`（意向族统一 `INTENT.ECON.*`）"),
)

DEFAULT_LEXICON = Path(__file__).resolve().parents[1] / "lexicon.json"


def load_forbidden(lexicon_path: Path) -> list[dict]:
    data = json.loads(lexicon_path.read_text(encoding="utf-8"))
    forbidden = data.get("forbidden", [])
    if not forbidden:
        print(f"[lint_terms] 警告：{lexicon_path} 无 forbidden 规则", file=sys.stderr)
    return forbidden


def compile_rules(forbidden: list[dict]) -> list[dict]:
    rules = []
    for f in forbidden:
        variant = f["variant"]
        mode = f.get("mode", "word")
        pattern = r"\b" + re.escape(variant) + r"\b" if mode == "word" else re.escape(variant)
        rules.append({
            "variant": variant,
            "canonical": f.get("canonical", ""),
            "reason": f.get("reason", ""),
            "mode": mode,
            "regex": re.compile(pattern),
            "exclude": f.get("exclude"),
            "allow_line_contains": f.get("allow_line_contains", []),
        })
    return rules


def _is_excluded(line: str, match: re.Match, exclude: str | None) -> bool:
    if not exclude:
        return False
    start = match.start()
    idx = line.find(exclude)
    while idx != -1:
        if idx <= start < idx + len(exclude):
            return True
        idx = line.find(exclude, idx + 1)
    return False


def _is_mention(line: str, rule: dict) -> bool:
    if any(m in line for m in MENTION_MARKERS):
        return True
    if any(w in line for w in rule.get("allow_line_contains", [])):
        return True
    return False


def build_suggestion(line: str, rule: dict, category: str, match: re.Match | None = None) -> str:
    """给一条命中生成**可操作的建议**（供作者直接照改）。"""
    variant = rule["variant"]
    canonical = rule.get("canonical", "")
    # 1) 命名空间错优先（仅当**本次命中**落在 `INTENT.OFFER` 上，避免误伤同一行的裸词）
    for pat, correct, msg in NAMESPACE_HINTS:
        for mm in pat.finditer(line):
            if match is not None and mm.start() < match.end() and match.start() < mm.end():
                return msg
    # 2) 常规：给规范名 + 族写法
    family = ""
    if canonical and re.match(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)+$", canonical):
        family = canonical.split("_", 1)[0] + "_*"
    if canonical:
        sug = f"改为 `{canonical}`"
        if family:
            sug += f"（或其族 `{family}`）"
    else:
        sug = "改为规范名（见 glossary/LEXICON.md）"
    # 3) 合法提及提示
    if category == "violation":
        hint = family or canonical or "规范名"
        sug += f"；若此处是【别名/映射提及】，请加提及标记（`→`、`已废弃`、或改写为 `{hint}`）"
    return sug


def iter_targets(root: Path) -> Iterator[Path]:
    seen: set[Path] = set()
    for glob in MD_GLOBS + PY_GLOBS:
        for p in sorted(root.glob(glob)):
            if not p.is_file() or p in seen:
                continue
            if any(part in EXCLUDE_DIR_PARTS for part in p.parts):
                continue
            if p.suffix in EXCLUDE_SUFFIXES:
                continue
            seen.add(p)
            yield p


def scan_file(path: Path, rules: list[dict], root: Path) -> list[dict]:
    findings = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings
    rel = str(path.relative_to(root)) if str(path).startswith(str(root)) else str(path)
    for lineno, line in enumerate(text.splitlines(), start=1):
        for r in rules:
            for m in r["regex"].finditer(line):
                if _is_excluded(line, m, r["exclude"]):
                    continue
                category = "mention" if _is_mention(line, r) else "violation"
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "col": m.start() + 1,
                    "variant": r["variant"],
                    "canonical": r["canonical"],
                    "reason": r["reason"],
                    "category": category,
                    "suggestion": build_suggestion(line, r, category, m),
                    "text": line.strip()[:200],
                })
    return findings


def top_dir(rel: str) -> str:
    return rel.split("/")[0] if "/" in rel else "(root)"


def counts_of(findings: list[dict]) -> dict[str, int]:
    c: dict[str, int] = defaultdict(int)
    for f in findings:
        c[f"{f['file']}|{f['variant']}"] += 1
    return dict(c)


def run_scan(root: Path, lexicon_path: Path, max_per_file: int) -> tuple[list[dict], int]:
    rules = compile_rules(load_forbidden(lexicon_path))
    targets = list(iter_targets(root))
    findings: list[dict] = []
    for p in targets:
        hits = scan_file(p, rules, root)
        if max_per_file and len(hits) > max_per_file:
            hits = hits[:max_per_file]
        findings.extend(hits)
    return findings, len(targets)


def load_baseline(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_baseline(path: Path, findings: list[dict]) -> dict:
    viol = [f for f in findings if f["category"] == "violation"]
    entries = [{"file": f["file"], "line": f["line"], "variant": f["variant"],
                "canonical": f["canonical"], "reason": f["reason"]} for f in viol]
    baseline = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": "术语检查器基线快照（棘轮模式）：仅『违规』入基线；『提及(mention)』不计。"
                "对比按 (file|variant) 计数，对行号偏移稳健。历史目录 v1/** 为历史快照，不强制改写。",
        "historical_dirs": sorted(HISTORICAL_DIRS),
        "total_violations": len(viol),
        "counts": counts_of(viol),
        "entries": entries,
    }
    path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    return baseline


def dir_stats(findings: list[dict]) -> dict:
    s: dict[str, dict] = defaultdict(lambda: {"violation": 0, "mention": 0})
    for f in findings:
        s[top_dir(f["file"])][f["category"]] += 1
    out = {}
    for d, v in sorted(s.items()):
        out[d] = {"violation": v["violation"], "mention": v["mention"],
                  "total": v["violation"] + v["mention"],
                  "historical": d in HISTORICAL_DIRS}
    return out


def fmt_finding(f: dict, indent: str = "  ") -> str:
    """把一条命中渲染成**可操作**的三行：位置 / 原文 / 建议。"""
    return (f"{indent}{f['file']}:{f['line']}:{f['col']}  [{f['variant']}] -> {f['canonical']}\n"
            f"{indent}  原文: {f['text']}\n"
            f"{indent}  建议: {f['suggestion']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="术语合规检查器（Lexicon linter v3 · 可操作化）")
    default_root = Path(__file__).resolve().parents[2]
    ap.add_argument("--root", default=str(default_root))
    ap.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    ap.add_argument("--baseline", help="棘轮基线路径；仅『基线外新违规』返回非 0")
    ap.add_argument("--update-baseline", help="把当前全部违规冻结为该路径的基线")
    ap.add_argument("--show-baseline", action="store_true", help="打印基线内容")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dir-stats", action="store_true")
    ap.add_argument("--include-mentions", action="store_true")
    ap.add_argument("--fail", action="store_true")
    ap.add_argument("--max-list", type=int, default=60, help="可操作清单最多打印条数")
    ap.add_argument("--max-per-file", type=int, default=500)
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    lexicon_path = Path(args.lexicon).resolve()
    if not root.exists():
        print(f"[lint_terms] 根目录不存在：{root}", file=sys.stderr)
        return 2
    if not lexicon_path.exists():
        print(f"[lint_terms] 找不到 lexicon：{lexicon_path}", file=sys.stderr)
        return 2

    findings, n_files = run_scan(root, lexicon_path, args.max_per_file)
    violations = [f for f in findings if f["category"] == "violation"]
    mentions = [f for f in findings if f["category"] == "mention"]

    if args.update_baseline:
        bpath = Path(args.update_baseline)
        if not bpath.is_absolute():
            bpath = (Path.cwd() / bpath)
        baseline = write_baseline(bpath, findings)
        print(f"[lint_terms] 基线已写入：{bpath}（违规 {baseline['total_violations']} 条）")
        if args.json:
            print(json.dumps({"baseline_file": str(bpath),
                              "total_violations": baseline["total_violations"]},
                             ensure_ascii=False, indent=2))
        return 0

    by_variant: dict[str, int] = defaultdict(int)
    for f in violations:
        by_variant[f["variant"]] += 1

    report = {
        "root": str(root),
        "files_scanned": n_files,
        "violations": len(violations),
        "mentions": len(mentions),
        "by_variant": dict(sorted(by_variant.items(), key=lambda kv: (-kv[1], kv[0]))),
        "dir_stats": dir_stats(findings),
    }

    # 棘轮：找出「基线之外的新违规」，并**带上可操作明细**
    new_keys: list[str] = []
    new_samples: dict[str, list[dict]] = {}
    baseline_used = None
    if args.baseline:
        bpath = Path(args.baseline)
        if not bpath.is_absolute():
            bpath = (Path.cwd() / bpath)
        if not bpath.exists():
            print(f"[lint_terms] 基线不存在：{bpath}（先 --update-baseline 生成）", file=sys.stderr)
            return 2
        baseline = load_baseline(bpath)
        baseline_used = str(bpath)
        base_counts = baseline.get("counts", {})
        cur_counts = counts_of(violations)
        by_key: dict[str, list[dict]] = defaultdict(list)
        for f in violations:
            by_key[f"{f['file']}|{f['variant']}"].append(f)
        for key, n in cur_counts.items():
            if n > base_counts.get(key, 0):
                new_keys.append(key)
                new_samples[key] = by_key[key]
        report["baseline"] = baseline_used
        report["new_violations"] = len(new_keys)
        report["baseline_total"] = baseline.get("total_violations")

    # ---------- 输出 ----------
    if args.json:
        print(json.dumps({"summary": report,
                          "new_keys": new_keys,
                          "new_samples": new_samples,
                          "violation_details": violations if (args.fail or args.baseline) else []},
                         ensure_ascii=False, indent=2))
    else:
        print("=" * 78)
        print("青溪镇 Lexicon · 术语合规报告 v3（可操作化：行号 + 建议替换）")
        print("=" * 78)
        print(f"扫描根目录 : {report['root']}")
        print(f"扫描文件   : {n_files}")
        print(f"违规       : {report['violations']}    提及(不罚) : {report['mentions']}")
        if args.baseline:
            print(f"基线       : {baseline_used}（冻结 {report.get('baseline_total')} 条）")
            print(f"新增违规   : {report.get('new_violations')}  ← 棘轮判定依据")
        print("-" * 78)

        # ① 棘轮新违规：逐条可操作
        if new_keys:
            print("⚠ 棘轮：以下为『基线之外的新违规』（请**按建议替换**，不要改基线绕过）：")
            for key in new_keys:
                for f in new_samples[key][: max(1, args.max_list)]:
                    print(fmt_finding(f))
            print("-" * 78)

        # ② 可操作清单
        if args.baseline:
            # 基线模式：历史违规折叠，只提示
            hist = report["violations"] - sum(len(v) for v in new_samples.values()) if new_keys else report["violations"]
            print(f"（历史基线违规 {hist} 条已折叠；`--show-baseline` 查看，`--baseline` 只对**新**违规报错）")
        else:
            print(f"可操作清单（行号 + 原文 + 建议替换，最多 {args.max_list} 条）：")
            for f in violations[: args.max_list]:
                print(fmt_finding(f))
            if len(violations) > args.max_list:
                print(f"  ...（其余 {len(violations) - args.max_list} 条，用 --json 查看全部）")
        print("=" * 78)

    if args.baseline:
        return 1 if new_keys else 0
    if args.fail:
        checked = violations + (mentions if args.include_mentions else [])
        return 1 if checked else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
