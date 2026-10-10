#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""术语合规检查器（青溪镇 Lexicon linter）· v2（基线/棘轮模式）。

扫描 `social-experiment/**/*.md` 与 `social-experiment/code/**/*.py`，标出使用
「已废弃 / 非规范叫法」的位置（文件:行:列），并可输出统计。

规则来源：`glossary/lexicon.json` 的 `forbidden` 列表。

**提及 vs 违规（v2 新增）**：
- 若命中所在行含「别名/废弃标记」（如 `→`/`->`/`已废弃`/`已并入`/`不新增`/
  `已裁定`/`需统一`/`替代`/`不设`/`旧称`/`禁用` … ），或命中规则的
  `allow_line_contains` 词表命中，则该命中归类为 **mention（提及）**，
  **不计入违规**（用于「已声明的别名映射」「引用他方术语」等正当场景）。
- 其余命中归类为 **violation（违规）**。

**基线 / 棘轮（ratchet）**：
- `--update-baseline glossary/term_baseline.json`：把**当前全部违规**冻结为基线。
- `--baseline glossary/term_baseline.json`：**仅当出现「基线之外的断违规」时返回非 0**；
  已知历史违规不报错（可用 `--show-baseline` 查看）。
  比较按 `(file, variant)` 的**计数**进行，对行号偏移稳健。

用法：
    python glossary/tools/lint_terms.py --root social-experiment
    python glossary/tools/lint_terms.py --root social-experiment --json
    python glossary/tools/lint_terms.py --root social-experiment --dir-stats
    python glossary/tools/lint_terms.py --root social-experiment \
        --baseline glossary/term_baseline.json            # 棘轮门禁（推荐 CI 用）
    python glossary/tools/lint_terms.py --root social-experiment \
        --update-baseline glossary/term_baseline.json      # 重冻基线

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

#: 历史快照目录（记录当时的决策，不强制改写）
HISTORICAL_DIRS = {"v1"}

#: 「别名/废弃标记」——命中行含其一即归类为 mention（提及），不计违规
MENTION_MARKERS = (
    "→", "->", "⇒", "=>",
    "已废弃", "废弃", "已并入", "并入", "不新增", "已裁定", "需统一", "已统一",
    "已登记", "已改为", "改为", "替代", "不设", "旧稿", "旧称", "禁用",
    "已关闭", "已解决", "统一到", "采用 08", "采纳 08", "旧", "弃", "vs", "对照",
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
            "exclude": f.get("exclude"),                 # 子串：出现在其中即跳过（如成员名）
            "allow_line_contains": f.get("allow_line_contains", []),
        })
    return rules


def _is_excluded(line: str, match: re.Match, exclude: str | None) -> bool:
    """命中落在 `exclude` 子串内则跳过（修 `sim-engine` 误伤 `sim-engine-stats-architect`）。"""
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
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "col": m.start() + 1,
                    "variant": r["variant"],
                    "canonical": r["canonical"],
                    "reason": r["reason"],
                    "category": "mention" if _is_mention(line, r) else "violation",
                    "text": line.strip()[:160],
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="术语合规检查器（Lexicon linter v2 · 基线/棘轮）")
    default_root = Path(__file__).resolve().parents[2]
    ap.add_argument("--root", default=str(default_root))
    ap.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    ap.add_argument("--baseline", help="棘轮基线路径；仅『基线外新违规』返回非 0")
    ap.add_argument("--update-baseline", help="把当前全部违规冻结为该路径的基线")
    ap.add_argument("--show-baseline", action="store_true", help="打印基线内容（含已知历史违规）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--dir-stats", action="store_true", help="按目录统计")
    ap.add_argument("--include-mentions", action="store_true",
                    help="把『提及』也计入 fail 判定（默认不计）")
    ap.add_argument("--fail", action="store_true",
                    help="发现违规即返回码 1（无 --baseline 时；有 --baseline 时自动启用棘轮）")
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

    # 冻结基线
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

    new_findings: list[dict] = []
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
        for key, n in cur_counts.items():
            allowed = base_counts.get(key, 0)
            if n > allowed:
                new_findings.append({"key": key, "count": n, "baseline_allowed": allowed})
        report["baseline"] = baseline_used
        report["new_violations"] = len(new_findings)
        report["baseline_total"] = baseline.get("total_violations")

    if args.show_baseline and args.baseline:
        bpath = Path(args.baseline)
        if not bpath.is_absolute():
            bpath = (Path.cwd() / bpath)
        b = load_baseline(bpath)
        print("=" * 72)
        print(f"基线内容：{bpath}（生成于 {b.get('generated')}；违规 {b.get('total_violations')} 条）")
        print("=" * 72)
        for e in b.get("entries", []):
            print(f"  {e['file']}:{e['line']}  [{e['variant']}] -> {e['canonical']}")

    if args.json:
        print(json.dumps({"summary": report,
                          "new": new_findings,
                          "violation_details": violations if (args.fail or args.baseline) else []},
                         ensure_ascii=False, indent=2))
    else:
        print("=" * 72)
        print("青溪镇 Lexicon · 术语合规报告 v2（violation=违规 / mention=提及·别名说明）")
        print("=" * 72)
        print(f"扫描根目录 : {report['root']}")
        print(f"扫描文件   : {n_files}")
        print(f"违规       : {report['violations']}")
        print(f"提及(不罚) : {report['mentions']}")
        if args.baseline:
            print(f"基线       : {baseline_used}（冻结 {report.get('baseline_total')} 条）")
            print(f"新增违规   : {report.get('new_violations')}  ← 棘轮判定依据")
        print("-" * 72)
        if by_variant:
            print("违规按禁用叫法：")
            for v, n in report["by_variant"].items():
                canon = next((f["canonical"] for f in violations if f["variant"] == v), "")
                print(f"  {n:5d}  {v!r:<32} -> {canon}")
        else:
            print("无违规。")
        print("-" * 72)
        print("按目录统计（violation / mention / 历史目录）：")
        for d, s in report["dir_stats"].items():
            tag = " [历史]" if s["historical"] else ""
            print(f"  {d:<12} violation={s['violation']:<4} mention={s['mention']:<4}{tag}")
        if new_findings:
            print("-" * 72)
            print("⚠ 棘轮：以下为『基线之外的新违规』：")
            for nf in new_findings:
                print(f"  {nf['key']}  (现值 {nf['count']} > 基线 {nf['baseline_allowed']})")
        print("=" * 72)

    # 退出码
    if args.baseline:
        return 1 if new_findings else 0
    if args.fail:
        checked = violations + (mentions if args.include_mentions else [])
        return 1 if checked else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
