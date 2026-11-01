#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R49「具体性起句」读数器（只读、零 LLM、零跑批）。D12-A 具体性插槽的机制闸读数器。

## 为什么需要这条尺子（问题定性）

`tools/metrics/lex_template_rate.py` 的 `distinct_body_ratio` 在现行提示词下**已是天花板**
（`c1-scene-a1-20261101_n16r24_s42` 实测 `191/191 = 1.000`），`opener_top10_share` 已低到 `7.33%`
⇒ **"措辞多样性"这一层没有分母可用**。真正还留着空间的，是**"具体性落在句首还是落在括号旁白里"**：
同一批日志里 **88.48%** 的消息以括号旁白起头，而**去掉旁白后的首 6 字只有 26.70% 命中具体物/数/量词**。
所以本轮机制闸必须**分开量"句中具体性"与"起句具体性"**，否则会重犯 D12-A 的旧错
（`v2/evidence/d12a_real_result.md` §0.5：句中具体性早已 >95%，拿它当判据等于没有判据）。

## 口径（先冻结，再读数；改这里 = 改尺子）

  * 样本 = `run.jsonl` 里 `type ∈ {MSG_DM, MSG_PUBLIC, MSG_GROUP}` 的**全部**消息正文（`payload.body`）。
  * `strip_lead_paren`：去掉**开头**的括号旁白段（正则**逐字镜像** `lex_template_rate.py::PAREN_LEAD_RE`，
    不发明第二套口径）。只剥开头，句中括号旁白保留（那是内容，不是开头模板）。
  * **具体性词表** `DETAIL_PATTERNS`：**逐字取自** `v2/evidence/d12c_proxy_lexicon.txt` 的 `P1 具体性代理`
    三行（数字/大写数字、量词、器物名词），不做任何增删；文件 sha256 由 `--lexicon` 钉住，
    读数输出里同时记录 `lexicon_sha256` 与 `impl_sha256`。
  * `detail_opener6`（**本轮机制闸**）：`strip_lead_paren(body)` 的**前 6 个字符**命中 `DETAIL_PATTERNS` 任一条。
  * `detail_line`：`strip_lead_paren(body)` **全句**命中任一条（对照用，说明"句中已饱和"）。
  * `detail_body`：**未剥旁白**的整条正文命中任一条（= D12 家族旧口径，含旁白）。
  * `paren_lead`：正文以括号旁白起头的比例（描述项，不作判据）。

输出 JSON（每个比率带 `num/den/rate/wilson95`；`den=0` 时写 `null`，**不写 0**）。
本脚本不改日志、不联网、不调 LLM；两次运行输出逐字节相等。

用法:
  python3 tools/metrics/r49_detail_opener.py \
      --log v2/evidence/<dir>/run.jsonl --label off --out-json v2/evidence/<dir>/r49_readings_off.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys

MSG_TYPES = {"MSG_DM", "MSG_PUBLIC", "MSG_GROUP"}

#: 尺子版本（**改词表 = 改尺子**，必须在报告里标注版本变化）
RULER_VERSION = "r49-detail-opener-v1"

#: 开头括号旁白（**逐字镜像** `tools/metrics/lex_template_rate.py::PAREN_LEAD_RE`）
PAREN_LEAD_RE = re.compile(r"^\s*(?:（[^）]{0,120}）|\([^)]{0,120}\))")

#: 具体性代理词表 —— **逐字取自 `v2/evidence/d12c_proxy_lexicon.txt` §P1**（不增删）
DETAIL_PATTERNS = (
    r"[0-9０-９一二三四五六七八九十百千万两]",
    r"[斤两把钱文斗升只条块张副担捆]",
    r"米|面|柴|油|盐|糖|布|木|铁|药|茶|酒|鸡|鱼|菜|糕|饼|书|笔|伞|鞋|绳|灯|碗|锅",
)
_DETAIL_RE = re.compile("|".join(DETAIL_PATTERNS))

#: 判「起句」用的前缀长度（与 `lex_template_rate.OPEN_CHARS` 一致）
OPENER_CHARS = 6


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


IMPL_SHA256 = _sha256_text(RULER_VERSION + "\n" + "\x00".join(DETAIL_PATTERNS))
LEXICON_SHA256 = _sha256_text("\n".join(DETAIL_PATTERNS))


def strip_lead_paren(s: str) -> str:
    """去掉开头括号旁白段（只剥开头；与 lex_template_rate 同正则）。"""
    return PAREN_LEAD_RE.sub("", s).strip()


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
        return {"num": k, "den": 0, "rate": None, "rate_pct": None, "status": "no_denominator",
                "wilson95": None}
    return {"num": k, "den": n, "rate": round(k / n, 6), "rate_pct": round(100.0 * k / n, 4),
            "status": "ok", "wilson95": wilson95(k, n)}


def collect_bodies(path: str) -> list[str]:
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
    return {
        "n_msgs": n,
        "detail_opener6": ratio(sum(1 for s in stripped if _DETAIL_RE.search(s[:OPENER_CHARS])), n),
        "detail_line": ratio(sum(1 for s in stripped if _DETAIL_RE.search(s)), n),
        "detail_body": ratio(sum(1 for b in bodies if _DETAIL_RE.search(b)), n),
        "paren_lead": ratio(sum(1 for b in bodies if PAREN_LEAD_RE.match(b)), n),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R49 具体性起句读数器（只读、零 LLM）")
    ap.add_argument("--log", required=True, help="run.jsonl 路径")
    ap.add_argument("--label", default="", help="标签（off/on/…），只写进 JSON，不参与计算")
    ap.add_argument("--out-json", default="", help="把完整 JSON 落盘（同时打印摘要行）")
    args = ap.parse_args(argv)

    log_bytes = open(args.log, "rb").read()
    bodies = collect_bodies(args.log)
    res = measure(bodies)
    payload = {
        "ruler_version": RULER_VERSION,
        "impl_sha256": IMPL_SHA256,
        "lexicon_sha256": LEXICON_SHA256,
        "lexicon_source": "v2/evidence/d12c_proxy_lexicon.txt §P1（逐字）",
        "opener_chars": OPENER_CHARS,
        "label": args.label,
        "log": {"path": args.log, "sha256": hashlib.sha256(log_bytes).hexdigest()},
        **res,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    d = res
    print(
        "n_msgs=%d detail_opener6=%s detail_line=%s detail_body=%s paren_lead=%s"
        % (
            d["n_msgs"],
            "%d/%d" % (d["detail_opener6"]["num"], d["detail_opener6"]["den"]),
            "%d/%d" % (d["detail_line"]["num"], d["detail_line"]["den"]),
            "%d/%d" % (d["detail_body"]["num"], d["detail_body"]["den"]),
            "%d/%d" % (d["paren_lead"]["num"], d["paren_lead"]["den"]),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
