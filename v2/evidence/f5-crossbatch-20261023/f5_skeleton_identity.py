#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次「行为骨架」同一性检查（解释性证据，不是指标）。

动机：F-5 / F-5b 只看 (agent, slot, place) × day 的重复，而这些字段由**调度/移动骨架**
决定，不由对话正文决定。若两批的骨架序列逐条相同，则它们的 F-5 必然逐位相同 ——
此时两批 F-5 的差异为 0 是**结构性必然**，不能当作任何开关的效果。

做法：抽每条对话消息的 (round, from, day, slot, place, to, thread_id) 组成序列，
对整序列取 sha256，比较批次之间是否逐条相同。不读正文、不算任何指标。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

MSG_TYPES = {"MSG_DM", "MSG_PUBLIC", "MSG_GROUP"}


def skeleton(path: str):
    keys = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:  # noqa: BLE001
                continue
            if r.get("type") not in MSG_TYPES:
                continue
            p = r.get("payload") or {}
            keys.append([r.get("round"), str(p.get("from") or r.get("actor")), str(p.get("day")),
                         str(p.get("slot")), str(p.get("place")), str(p.get("to")), str(p.get("thread_id"))])
    h = hashlib.sha256(json.dumps(keys, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"n_msgs": len(keys), "skeleton_sha256": "sha256:" + h}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", action="append", required=True, help="tag=path 形式，可多次")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = []
    for item in a.log:
        tag, path = item.split("=", 1)
        s = skeleton(path)
        rows.append({"tag": tag, "log": os.path.abspath(path), **s})
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r["skeleton_sha256"], []).append(r["tag"])
    out = {
        "skeleton_definition": "(round, from, day, slot, place, to, thread_id) of each MSG_DM/MSG_PUBLIC/MSG_GROUP",
        "per_batch": rows,
        "identical_groups": {k: v for k, v in groups.items()},
        "note": "骨架相同 ⇒ 该组内 F-5/F-5b 逐位相同是结构性必然，不能作为开关效果证据",
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
    print(json.dumps({"out": a.out, "n_groups": len(groups)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
