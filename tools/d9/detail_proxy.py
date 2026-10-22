#!/usr/bin/env python3
"""detail_proxy.py — 「具体性代理」的**唯一判定实现**（冻结版，2026-10-23）

背景（D12-A 问题 (a) 事故）：同一 `DETAIL_WORDS` 词表存在两套实现，
OFF 臂读数相差 1.04pp（95.29% vs 96.33%），足以把 ON−OFF 的 Δ 从 +3.14pp 翻成 +2.09pp，
而判定阈值是 +3pp ⇒ 同一份数据能得出相反判定。

因此本文件是**判定用（canonical）实现**，规则写死如下，不得在别处另写一版参与判定：

1. **单位**：per-message（一条 MSG_* 计 1），分母 = 该臂全部 MSG_*（含 DM/GROUP/PUBLIC）。
2. **body**：取 `payload["body"]` 原文，**不做任何预处理**（不去括号、不去空白、不规范化）。
3. **匹配语义**：对 `DETAIL_WORDS` 中每一条正则依次 `re.search`；**任一条命中即记 1**（`any()` 语义，非计次）。
4. **词表来源**：`v2/evidence/d4_metrics.py::DETAIL_WORDS`（逐字复制于下，含 sha256 记录）。
5. **不做**：不去括号、不按词累加、不做 stemming、不做同义扩展、不使用 LLM。

用法：
  python3 tools/d9/detail_proxy.py --run <run.jsonl> [--max-round 23] [--json]
  # 输出：{"n":…, "detail":…, "ratio":…, "impl_sha256":…, "words_sha256":…}

也作为库使用：`from detail_proxy import detail_stats`。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys

# ---- 词表（逐字来自 v2/evidence/d4_metrics.py::DETAIL_WORDS，不得改） -----------
DETAIL_WORDS = [
    r"[0-9０-９一二三四五六七八九十百千万两]",
    r"[斤两把钱文斗升只条块张副担捆]",
    r"米|面|柴|油|盐|糖|布|木|铁|药|茶|酒|鸡|鱼|菜|糕|饼|书|笔|伞|鞋|绳|灯|碗|锅",
]
MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")


def words_sha256() -> str:
    """词表的规范形状 sha256（判定用的"词表身份"）。"""
    payload = json.dumps(list(DETAIL_WORDS), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def impl_sha256() -> str:
    """本实现**判定逻辑源码**的 sha256（不含注释/docstring，避免无关改动改变身份）。"""
    src = (
        "unit=per-message\n"
        "body=raw_no_normalize\n"
        "match=any_re.search\n"
        "words=" + json.dumps(list(DETAIL_WORDS), ensure_ascii=False, sort_keys=True) + "\n"
        "msg_types=" + ",".join(MSG_TYPES) + "\n"
    )
    return hashlib.sha256(src.encode("utf-8")).hexdigest()


_COMPILED = [re.compile(w) for w in DETAIL_WORDS]


def hits(body: str) -> bool:
    """判定语义：任一条正则命中即 True（any，不计次）。"""
    if not body:
        return False
    return any(p.search(body) for p in _COMPILED)


def detail_stats(path: str, max_round: int | None = None) -> dict:
    n = 0
    d = 0
    bad = 0
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            bad += 1
            continue
        if r.get("type") not in MSG_TYPES:
            continue
        if max_round is not None and int(r.get("round", 0)) > max_round:
            continue
        n += 1
        if hits((r.get("payload") or {}).get("body") or ""):
            d += 1
    return {
        "source": path,
        "max_round": max_round,
        "n": n,
        "detail": d,
        "ratio": round(d / n, 4) if n else 0.0,
        "bad_lines": bad,
        "impl_sha256": impl_sha256(),
        "words_sha256": words_sha256(),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--max-round", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    s = detail_stats(a.run, a.max_round)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, sort_keys=True))
    else:
        print(f"{s['source']}  max_round={s['max_round']}  n={s['n']}  detail={s['detail']}  ratio={s['ratio']:.4f}")
        print(f"impl_sha256={s['impl_sha256']}")
        print(f"words_sha256={s['words_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
