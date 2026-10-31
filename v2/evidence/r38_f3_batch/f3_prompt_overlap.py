#!/usr/bin/env python3
"""F-3 两臂 dialogue prompt_hash 重合度（只读 run.jsonl）。
用法: python3 v2/evidence/r38_f3_batch/f3_prompt_overlap.py <off/run.jsonl> <on/run.jsonl>
"""
import json, sys

def dlg_hashes(path):
    hs = set(); n = 0
    with open(path) as f:
        for line in f:
            try: e = json.loads(line)
            except Exception: continue
            pl = e.get("payload") or {}
            if e.get("type") == "LLM_CALL" and pl.get("purpose") == "dialogue":
                n += 1
                h = pl.get("prompt_hash") or pl.get("cache_key")
                if h: hs.add(h)
    return hs, n

a, na = dlg_hashes(sys.argv[1])
b, nb = dlg_hashes(sys.argv[2])
inter = a & b
print("off dialogue_calls=%d distinct_prompt_hash=%d" % (na, len(a)))
print("on  dialogue_calls=%d distinct_prompt_hash=%d" % (nb, len(b)))
print("intersection=%d  |  on_only=%d  off_only=%d" % (len(inter), len(b - a), len(a - b)))
print("on_diff_ratio=%.4f (=|on_only|/on_distinct)" % (len(b - a) / len(b) if b else 0))
