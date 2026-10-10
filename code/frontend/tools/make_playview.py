#!/usr/bin/env python3
"""make_playview.py — 从 canonical 日志派生「播放视图」轻量日志 + round 索引（T74）。

背景：B2@N=20 canonical 日志 ~54MB，整份灌进单页会 OOM。本工具生成**派生播放视图**：
- 剔除**高体量、渲染无关**的事件（`MEMORY_WRITE/MEMORY_RETRIEVE/MEMORY_REFLECT/OBSERVATION/LLM_CALL`）；
- 只保留**渲染/审计相关**事件；折叠出的渲染状态（位置/生死/金钱/活动/需求）与 canonical **一致**；
- 紧凑 JSON 编码进一步瘦身；
- 同时输出 **round → 字节偏移** 索引，便于按 round 直取/分片。

**权威源不变**：canonical 日志（`v1.2/evidence/run_abl_B2_N20.jsonl`）才是事实源；
本产物是**派生播放视图**，只读、不改 canonical。

用法：
    cd code
    python frontend/tools/make_playview.py \
        --in  ../v1.2/evidence/run_abl_B2_N20.jsonl \
        --out frontend/sample/run_b2_n20_week.play.jsonl \
        --index frontend/sample/run_b2_n20_week.play.index.json \
        --authority v1.2/evidence/run_abl_B2_N20.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# 渲染无关、体量大的事件（剔除）
DROP = {"MEMORY_WRITE", "MEMORY_RETRIEVE", "MEMORY_REFLECT", "OBSERVATION", "LLM_CALL"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--authority", default="")
    args = ap.parse_args()

    src = Path(args.inp).expanduser().resolve()
    if not src.exists():
        print(f"输入不存在: {src}", file=sys.stderr)
        return 2

    kept = 0
    dropped = 0
    dropped_bytes = 0
    rounds = {}                     # round -> {offset, seq}
    offsets = []                    # parallel to kept events
    out_tmp = Path(args.out).expanduser().resolve()
    out_tmp.parent.mkdir(parents=True, exist_ok=True)

    # 先写内容并记录偏移
    with out_tmp.open("w", encoding="utf-8") as w:
        pos = 0
        for line in src.open("r", encoding="utf-8"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("type") in DROP:
                dropped += 1
                dropped_bytes += len(line)
                continue
            s = json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n"
            r = rec.get("round", 0) or 0
            if r not in rounds:
                rounds[r] = {"offset": pos, "seq": rec.get("seq")}
            w.write(s)
            pos += len(s.encode("utf-8"))
            kept += 1

    idx = {
        "schema": "hitt.playview.index/1",
        "authority": args.authority or str(src),
        "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "view": str(out_tmp.name),
        "note": "派生播放视图：剔除 MEMORY_*/OBSERVATION/LLM_CALL；权威日志见 authority。",
        "kept_events": kept,
        "dropped_events": dropped,
        "rounds": rounds,
    }
    Path(args.index).write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_sz = out_tmp.stat().st_size
    print(f"playview -> {out_tmp}  ({out_sz/1e6:.2f} MB, kept {kept}, dropped {dropped} ≈ {dropped_bytes/1e6:.1f} MB)")
    print(f"index    -> {args.index}  (rounds {len(rounds)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
