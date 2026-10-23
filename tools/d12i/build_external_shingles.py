#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-I 只读准备：构建**固定外部语料** `S_ext` = T5 前 40 轮的 8-gram shingle 并集。

为什么要有它（D12-I 的核心）：run 内选优目标要改成"对**固定外部语料**的 `overlap_frac`"，
这样目标/判据/参照系三者同源，且外部语料**不随本臂增长**（避免"自己比自己"）。

口径（与 D12-H 落盘 `/ overlap_frac.py` 完全同源，**改这里等于改判据**）：
- shingle = `code/life/d12e_shingles.py` 的 `normalize` + `shingles`（NGRAM=8）；
- 每 shingle 取 `blake2b(digest_size=8)` 十六进制；
- `S_ext` = T5 前 40 轮（`round < 40`）**全部落库台词**的 shingle 去重并集。

用法：
    python3 tools/d12i/build_external_shingles.py \
        --log <T5 run.jsonl> --out v2/evidence/d12i_external_shingles.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="T5 的 run.jsonl")
    ap.add_argument("--rounds", type=int, default=40, help="取前 N 轮（round < N）")
    ap.add_argument("--out", default="v2/evidence/d12i_external_shingles.json")
    ap.add_argument("--ngram", type=int, default=8,
                    help="shingle 长度（D12-I v2 用 4；默认 8 以保持向后兼容）")
    ap.add_argument("--code-dir", default=None)
    a = ap.parse_args(argv)

    code_dir = Path(a.code_dir) if a.code_dir else (ROOT / "code")
    sys.path.insert(0, str(code_dir))
    import life.d12e_shingles as D  # noqa: E402

    log = Path(a.log)
    raw = log.read_bytes()
    log_sha = hashlib.sha256(raw).hexdigest()

    union, n_msg = set(), 0
    rounds_seen = set()
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not str(r.get("type", "")).startswith("MSG"):
            continue
        rd = r.get("round")
        if not isinstance(rd, int) or rd >= a.rounds:
            continue
        body = ((r.get("payload") or {}).get("body") or "").strip()
        if not body:
            continue
        n_msg += 1
        rounds_seen.add(rd)
        t = D.normalize(body)
        for sh in {t[i:i + a.ngram] for i in range(max(0, len(t) - a.ngram + 1))}:
            union.add(hashlib.blake2b(sh.encode("utf-8"), digest_size=8).hexdigest())

    hashes = sorted(union)
    out = {
        "name": f"S_ext (D12-I external fixed corpus, ngram={a.ngram})",
        "spec": {
            "source_log": str(log),
            "source_log_sha256": log_sha,
            "rounds": a.rounds,
            "rounds_covered": [min(rounds_seen), max(rounds_seen)] if rounds_seen else None,
            "n_messages_used": n_msg,
            "shingle": f"code/life/d12e_shingles.py::normalize + {a.ngram}-gram 窗口（D12-I v2 用 4）",
            "ngram": a.ngram,
            "hash": "blake2b(digest_size=8) hex, sorted unique",
            "n_shingles": len(hashes),
            "content_sha256": hashlib.sha256("\n".join(hashes).encode("utf-8")).hexdigest(),
        },
        "note": ("外置只读语料：run 内不得修改/追加；overlap_frac(c) = |shingles(c) ∩ S_ext| / |shingles(c)|，"
                 "|shingles(c)|=0 ⇒ N/A（不得记 0）。本文件由 tokens 之外的离线步骤生成，不参与任何跑批。"),
        "shingles": hashes,
    }
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[d12i] S_ext 构建完成：ngram={a.ngram}、rounds<{a.rounds}、消息 {n_msg} 条、shingle {len(hashes)} 个")
    print(f"[d12i] content_sha256 = {out['spec']['content_sha256']}")
    print(f"[d12i] source_log_sha256 = {log_sha}")
    print(f"[d12i] out = {p} （文件 sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
