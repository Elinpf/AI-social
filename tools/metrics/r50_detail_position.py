#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R50「具体性·位置分层」读数器 v2（只读、零 LLM、零跑批）。

## 为什么要有 v2（R49 判据选点缺陷）

R49 的机制闸 `detail_opener6` 只取「剥掉开头括号旁白后**前 6 个字符**」是否命中具体物词表。
R49 报告 §11 与 `docs/team-board.md` 都登记了这条缺陷：模型常把具体物放在**称呼之后**或
**旁白之后的第一个分句里**，例如（R49 ON 臂原文）：

    金先生，（把琴弓在松香上蹭了两下）天刚亮我就开练了，这段揉弦总差口气。

这条消息里「琴弓」「松香」「天刚亮」都是具体物/具体事，但前 6 字是「金先生，（把」⇒ 判 0。
**尺子测的是"有没有立刻说物"，不是"有没有说具体物"**——判据与假设错位。

v2 不换词表、不换样本口径，只把**位置窗口**这一维分层，让"选点"本身可被读数暴露。

## 口径（先冻结，再读数；改这里 = 改尺子）

样本 = `run.jsonl` 里 `type ∈ {MSG_DM, MSG_PUBLIC, MSG_GROUP}` 的**全部**消息正文
（`payload.body`），与 R49 **逐字相同**（同一 `collect_bodies` 逻辑）。

四档位置窗口（**词表全部相同**，只有"在正文的哪一段里找"不同）：

| 档 | 定义 | 与 R49 的关系 |
|---|---|---|
| `opener6` | `strip_lead_paren(body)` 的**前 6 字符**命中 | **= R49 `detail_opener6`，逐字同口径**（必须与 R49 已公布读数对账） |
| `first_clause` | `strip_lead_paren(body)` 的**首个分句**命中 | 新档：把 6 字窗口放宽到"第一个分句"（停在第一个分句终止符） |
| `first_clause_skip` | `strip_lead_paren(body)` 起，**跳过最多 2 个「≤8 字且无具体物」的前导分句**（称呼/寒暄/旁白式开口），再取首个分句命中 | 新档：**选点修正主候选**，专门打掉"称呼之后才说物"的漏判 |
| `anywhere` | **未剥旁白**的整条正文命中 | = R49 `detail_body`（含旁白整句，近天花板，只作对照，**不作判据**） |

补充读数：
* `paren_lead`：正文以括号旁白起头（与 R49 同正则）。
* `no_cue`：**整条正文（未剥旁白）任何位置都不命中词表**的条数 = `n - anywhere.num`。
  （预登记卡的不可判条件之一要看两臂 `no_cue` 差，故单列。）

分句终止符：`，,。！!？?；;：:` 与换行。**不含 `、`**（顿号在短语内部，如「米、面、油」，
切开会把同一短语拆碎）；**不含 `.`**（避免把小数 `3.5` 切开）。

## 词表（不自行加词）

具体性词表**逐字复用** `tools/metrics/r49_detail_opener.py::DETAIL_PATTERNS`（其 `lexicon_sha256`
与 R49 预登记卡 §3.1 一致），运行时断言 sha 相等；取不到模块时回落到
`v2/evidence/d12c_proxy_lexicon.txt` §P1 三行并同样断言 sha。
**本 v2 没有任何扩展词**（`lexicon_extensions: []`）；若将来必须扩展，扩展词必须单独成列并在
输出里标 `preregistered=false`，不得混进主档。

## 输出

固定 JSON（`sort_keys=True`、`indent=2`，两次运行逐字节相等）：每档 `num/den/rate/rate_pct/
wilson95/status`；`den=0` 写 `null` 不写 0；附 `lexicon_sha256`、`impl_sha256`、输入 `sha256`。

用法:
  python3 tools/metrics/r50_detail_position.py --log v2/evidence/<dir>/run.jsonl --label off
  python3 tools/metrics/r50_detail_position.py --log <run.jsonl> --out-json <out.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

MSG_TYPES = {"MSG_DM", "MSG_PUBLIC", "MSG_GROUP"}

RULER_VERSION = "r50-detail-position-v2"

#: R49 预登记卡 §3.1 冻结的 lexicon_sha256（拼错即失败，防止悄悄换词表）
R49_LEXICON_SHA256 = "e8507082b0915f93eb62ab200969da17d4a700e1b337e0d97ce2355196dd7477"

#: 开头括号旁白（逐字镜像 tools/metrics/lex_template_rate.py::PAREN_LEAD_RE）
PAREN_LEAD_RE = re.compile(r"^\s*(?:（[^）]{0,120}）|\([^)]{0,120}\))")

#: 分句终止符（不含顿号 `、`、不含 `.`，见模块 docstring）
CLAUSE_END_RE = re.compile(r"[，,。！!？?；;：:\n]")

#: `opener6` 窗口长度（与 R49 一致）
OPENER_CHARS = 6

#: `first_clause_skip` 最多跳过几个前导分句、前导分句最长多少字
SKIP_MAX_CLAUSES = 2
SKIP_MAX_LEN = 8


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_lexicon() -> tuple[tuple[str, ...], str]:
    """逐字复用 R49 词表；返回 (patterns, source描述)。sha 不符直接失败。"""
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        import r49_detail_opener as r49  # noqa: WPS433

        pats = tuple(r49.DETAIL_PATTERNS)
        source = "tools/metrics/r49_detail_opener.py::DETAIL_PATTERNS（逐字复用）"
    except Exception:  # pragma: no cover - 模块缺失时的回落路径
        lex_path = here.parent.parent / "v2" / "evidence" / "d12c_proxy_lexicon.txt"
        lines, in_p1 = [], False
        for raw in lex_path.read_text(encoding="utf-8").splitlines():
            s = raw.strip()
            if s.startswith("#"):
                in_p1 = "P1" in s and "具体性" in s
                continue
            if in_p1 and s:
                lines.append(s)
        pats = tuple(lines)
        source = "v2/evidence/d12c_proxy_lexicon.txt §P1（逐字）"
    got = _sha256_text("\n".join(pats))
    if got != R49_LEXICON_SHA256:
        raise SystemExit(
            "FATAL: 词表 sha256 与 R49 冻结值不符，拒绝读数（got=%s want=%s）"
            % (got, R49_LEXICON_SHA256)
        )
    return pats, source


DETAIL_PATTERNS, LEXICON_SOURCE = _load_lexicon()
_DETAIL_RE = re.compile("|".join(DETAIL_PATTERNS))
LEXICON_SHA256 = _sha256_text("\n".join(DETAIL_PATTERNS))
IMPL_SHA256 = _sha256_text(
    RULER_VERSION + "\n" + "\x00".join(DETAIL_PATTERNS)
    + "\n%s|%d|%d|%s" % (CLAUSE_END_RE.pattern, OPENER_CHARS, SKIP_MAX_CLAUSES, SKIP_MAX_LEN)
)


def strip_lead_paren(s: str) -> str:
    """去掉开头括号旁白段（只剥开头；与 lex_template_rate 同正则）。"""
    return PAREN_LEAD_RE.sub("", s).strip()


def split_first_clause(s: str) -> tuple[str, str]:
    """切成 (首个分句正文, 该分句之后剩下的串)。无终止符 ⇒ rest 为空串。"""
    m = CLAUSE_END_RE.search(s)
    if not m:
        return s.strip(), ""
    return s[: m.start()].strip(), s[m.end():].lstrip()


def first_clause(s: str) -> str:
    return split_first_clause(s)[0]


def first_clause_skip(s: str) -> str:
    """跳过最多 SKIP_MAX_CLAUSES 个「短且无具体物」的前导分句，再取首个分句。"""
    rest = strip_lead_paren(s)
    for _ in range(SKIP_MAX_CLAUSES):
        head, tail = split_first_clause(rest)
        if not tail:
            return head
        if len(head) <= SKIP_MAX_LEN and not _DETAIL_RE.search(head):
            rest = tail.lstrip()
            continue
        return head
    return first_clause(rest)


def wilson95(k: int, n: int, z: float = 1.96) -> dict | None:
    if n <= 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"p": round(p, 6), "lo": round(max(0.0, c - h), 6), "hi": round(min(1.0, c + h), 6)}


def ratio(k: int, n: int) -> dict:
    if n <= 0:
        return {
            "num": k,
            "den": 0,
            "rate": None,
            "rate_pct": None,
            "status": "no_denominator",
            "wilson95": None,
        }
    return {
        "num": k,
        "den": n,
        "rate": round(k / n, 6),
        "rate_pct": round(100.0 * k / n, 4),
        "status": "ok",
        "wilson95": wilson95(k, n),
    }


def collect_bodies(path: str) -> list[str]:
    """与 R49 逐字相同的取样本逻辑。"""
    out: list[str] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") not in MSG_TYPES:
                continue
            body = (rec.get("payload") or {}).get("body")
            if isinstance(body, str) and body.strip():
                out.append(body.strip())
    return out


def measure(bodies: list[str]) -> dict:
    n = len(bodies)
    stripped = [strip_lead_paren(b) for b in bodies]

    opener6 = sum(1 for s in stripped if _DETAIL_RE.search(s[:OPENER_CHARS]))
    fc = sum(1 for s in stripped if _DETAIL_RE.search(first_clause(s)))
    fcs = sum(1 for s in stripped if _DETAIL_RE.search(first_clause_skip(s)))
    anywhere = sum(1 for b in bodies if _DETAIL_RE.search(b))
    paren_lead = sum(1 for b in bodies if PAREN_LEAD_RE.match(b))

    return {
        "n_msgs": n,
        "strata": {
            "opener6": ratio(opener6, n),
            "first_clause": ratio(fc, n),
            "first_clause_skip": ratio(fcs, n),
            "anywhere": ratio(anywhere, n),
        },
        "no_cue": ratio(n - anywhere, n),
        "paren_lead": ratio(paren_lead, n),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R50 具体性·位置分层读数器（只读、零 LLM）")
    ap.add_argument("--log", required=True, help="run.jsonl 路径")
    ap.add_argument("--label", default="", help="标签（off/on/…），只写进 JSON，不参与计算")
    ap.add_argument("--out-json", default="", help="把完整 JSON 落盘")
    args = ap.parse_args(argv)

    log_bytes = open(args.log, "rb").read()
    bodies = collect_bodies(args.log)
    res = measure(bodies)
    payload = {
        "ruler_version": RULER_VERSION,
        "impl_sha256": IMPL_SHA256,
        "lexicon_sha256": LEXICON_SHA256,
        "lexicon_source": LEXICON_SOURCE,
        "lexicon_extensions": [],
        "lexicon_extensions_preregistered": None,
        "opener_chars": OPENER_CHARS,
        "clause_end_regex": CLAUSE_END_RE.pattern,
        "skip_max_clauses": SKIP_MAX_CLAUSES,
        "skip_max_len": SKIP_MAX_LEN,
        "sample_rule": "type in {MSG_DM,MSG_PUBLIC,MSG_GROUP} & payload.body 非空（同 R49）",
        "label": args.label,
        "log": {"path": args.log, "sha256": hashlib.sha256(log_bytes).hexdigest()},
        **res,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")

    st = res["strata"]
    print(
        "n_msgs=%d opener6=%d/%d first_clause=%d/%d first_clause_skip=%d/%d anywhere=%d/%d "
        "no_cue=%d/%d paren_lead=%d/%d"
        % (
            res["n_msgs"],
            st["opener6"]["num"], st["opener6"]["den"],
            st["first_clause"]["num"], st["first_clause"]["den"],
            st["first_clause_skip"]["num"], st["first_clause_skip"]["den"],
            st["anywhere"]["num"], st["anywhere"]["den"],
            res["no_cue"]["num"], res["no_cue"]["den"],
            res["paren_lead"]["num"], res["paren_lead"]["den"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
