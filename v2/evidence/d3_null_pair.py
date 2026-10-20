#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D3 · null-pair（同 seed 噪声对照）实测：t300 vs t355 台词逐条一致率

作者：prompt-linguist ｜ 只读：不改任何文件、不调 LLM。
对齐算法（与证据文档一致，供独立复算）：
  A1 抽取：按 run.jsonl **文件行序**（= ledger 提交顺序）读取，筛 type ∈ {MSG_DM, MSG_PUBLIC, MSG_GROUP}
  A2 对齐：只做**位置对齐**（第 i 条 MSG ↔ 第 i 条 MSG）；前置校验两臂条数相等且 channel 序列逐位相同
  A3 判定：body 字符串**逐字节相等**（不 strip、不做标点/全半角归一）
  A4 辅助读数（非主口径）：① strip 后相等 ② 同位置 speaker 相同 ③ 归一化（去空白标点、小写）后相等
用法：python3 v2/evidence/d3_null_pair.py
"""
import hashlib, json
from pathlib import Path

RUNS = {
    "t300": "/root/t271/runs/t300/run.jsonl",
    "t355": "/root/t271/runs/t355/run.jsonl",
}
MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def sha256(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def msgs(p: str):
    out = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        t = e.get("type")
        if t not in MSG_TYPES:
            continue
        pl = e.get("payload") or {}
        out.append({
            "seq": e.get("seq"), "round": e.get("round"), "type": t,
            "speaker": pl.get("from") or pl.get("author"),
            "to": pl.get("to") or pl.get("group_id"),
            "body": pl.get("body") or "",
        })
    return out


def norm(s: str) -> str:
    import re
    return re.sub(r"[\s\u3000，。！？、；：“”‘’（）()…—\-\.!?,;:\"']+", "", s).lower()


def main() -> int:
    meta = {}
    data = {}
    for name, p in RUNS.items():
        data[name] = msgs(p)
        meta[name] = {"path": p, "sha256": sha256(p),
                      "n_msgs": len(data[name])}
    a, b = data["t300"], data["t355"]
    out = {"script": "v2/evidence/d3_null_pair.py",
           "runs": meta,
           "align": "positional (i-th MSG <-> i-th MSG), file order = ledger order",
           "guard_n_equal": len(a) == len(b),
           "guard_channel_seq_equal": [m["type"] for m in a] == [m["type"] for m in b]}
    n = min(len(a), len(b))
    same_bytes = sum(1 for i in range(n) if a[i]["body"] == b[i]["body"])
    same_strip = sum(1 for i in range(n) if a[i]["body"].strip() == b[i]["body"].strip())
    same_norm = sum(1 for i in range(n) if norm(a[i]["body"]) == norm(b[i]["body"]))
    same_speaker = sum(1 for i in range(n) if a[i]["speaker"] == b[i]["speaker"])
    same_seq = sum(1 for i in range(n) if a[i]["seq"] == b[i]["seq"])
    out["result"] = {
        "n_pairs": n,
        "same_body_bytes": same_bytes,
        "same_body_bytes_rate_pct": round(100 * same_bytes / n, 2),
        "aux_same_body_strip": same_strip,
        "aux_same_body_normalized": same_norm,
        "aux_same_speaker": same_speaker,
        "aux_same_seq": same_seq,
        "note": "主口径=逐字节相等；其余为辅助读数，不得替代主口径",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
