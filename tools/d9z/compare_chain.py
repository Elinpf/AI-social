"""D9z：逐事件 hash 链比对（不是首末比对）。

对两份 `run.jsonl`：
  1. 各自校验**链自洽**：`prev_hash[i] == hash[i-1]`（首事件 `prev_hash` 允许为 null/空/创世值）；
  2. 逐事件比 `hash`（即逐字节内容）；`seq` 必须逐条相同；
  3. 输出：共同前缀长度、**第一个分叉的 seq 与事件类型**、分叉处两侧的 `type`/`actor`/`round`。

用法：
    python3 tools/d9z/compare_chain.py A.jsonl B.jsonl [--report out.json]
"""

from __future__ import annotations

import hashlib
import json
import sys


def load(path: str) -> list:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def chain_ok(recs: list) -> tuple[bool, int]:
    """返回 (链是否自洽, 第一个坏链接的下标或 -1)。"""
    for i in range(1, len(recs)):
        if recs[i].get("prev_hash") != recs[i - 1].get("hash"):
            return False, i
    return True, -1


def compare(a_path: str, b_path: str) -> dict:
    a, b = load(a_path), load(b_path)
    ok_a, bad_a = chain_ok(a)
    ok_b, bad_b = chain_ok(b)
    n = min(len(a), len(b))
    first = -1
    for i in range(n):
        if a[i].get("seq") != b[i].get("seq") or a[i].get("hash") != b[i].get("hash"):
            first = i
            break
    same_prefix = n if first < 0 else first
    rep = {
        "a": {"path": a_path, "sha256": sha256_file(a_path), "events": len(a),
              "chain_self_consistent": ok_a, "first_bad_link": bad_a},
        "b": {"path": b_path, "sha256": sha256_file(b_path), "events": len(b),
              "chain_self_consistent": ok_b, "first_bad_link": bad_b},
        "events_compared": n,
        "identical_prefix_events": same_prefix,
        "identical": (first < 0 and len(a) == len(b)),
        "first_divergence": None,
    }
    if first >= 0:
        ea, eb = a[first], b[first]
        rep["first_divergence"] = {
            "index": first,
            "seq_a": ea.get("seq"), "seq_b": eb.get("seq"),
            "type_a": ea.get("type"), "type_b": eb.get("type"),
            "actor_a": ea.get("actor"), "actor_b": eb.get("actor"),
            "round_a": ea.get("round"), "round_b": eb.get("round"),
            "hash_a": ea.get("hash"), "hash_b": eb.get("hash"),
            "prev_hash_a": ea.get("prev_hash"), "prev_hash_b": eb.get("prev_hash"),
        }
    elif len(a) != len(b):
        rep["first_divergence"] = {"index": n, "note": "前缀相同但长度不同",
                                   "events_a": len(a), "events_b": len(b)}
    return rep


def main(argv: list) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    rep = compare(argv[1], argv[2])
    if "--report" in argv:
        p = argv[argv.index("--report") + 1]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if (rep["identical"] or rep["first_divergence"]) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
