#!/usr/bin/env python3
"""D8 两臂读数（只读、零 LLM）：世界事件 → 记忆 → 对话上下文 → 措辞。

用法: python3 /tmp/d8_check.py <run.jsonl> [tag]
输出 JSON（print 到 stdout）。
"""
import json
import sys
from collections import Counter

WORLD_TYPES = ("WORLD_DIRECTIVE", "WORLD_GROUP_EVENT")


def main():
    path = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else ""
    world_seqs = set()
    world_by_type = Counter()
    world_rounds = Counter()
    obs_world = 0
    obs_world_seqs = set()
    mw_world = 0
    mw_world_seqs = set()
    msg_total = 0
    msg_world_ctx = 0
    msg_world_ctx_prompted = 0
    world_ctx_refs = set()
    mem_world_text = Counter()
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        t = r.get("type")
        p = r.get("payload") or {}
        if t in WORLD_TYPES:
            world_seqs.add(int(r["seq"]))
            world_by_type[t] += 1
            world_rounds[int(r.get("round", -1))] += 1
        elif t == "OBSERVATION":
            tev = p.get("target_event_seq")
            if tev is not None and int(tev) in world_seqs:
                obs_world += 1
                obs_world_seqs.add(int(tev))
        elif t == "MEMORY_WRITE":
            sev = p.get("source_event_seq")
            if sev is not None and int(sev) in world_seqs:
                mw_world += 1
                mw_world_seqs.add(int(sev))
                mem_world_text[str(p.get("text", ""))[:60]] += 1
        elif t in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            msg_total += 1
            wc = p.get("world_ctx")
            if wc:
                msg_world_ctx += 1
                if wc.get("prompted"):
                    msg_world_ctx_prompted += 1
                for ref in (wc.get("refs") or []):
                    world_ctx_refs.add(str(ref))
    out = {
        "tag": tag,
        "log": path,
        "world_events_total": sum(world_by_type.values()),
        "world_by_type": dict(world_by_type),
        "world_rounds": dict(sorted(world_rounds.items())),
        "M0_memory_write_ref_world": mw_world,
        "M0_distinct_world_seqs_in_memory": len(mw_world_seqs),
        "observation_ref_world(信息位)": obs_world,
        "msg_total": msg_total,
        "msg_with_world_ctx": msg_world_ctx,
        "msg_with_world_ctx_prompted": msg_world_ctx_prompted,
        "world_ctx_refs": len(world_ctx_refs),
        "memory_text_samples": mem_world_text.most_common(5),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
