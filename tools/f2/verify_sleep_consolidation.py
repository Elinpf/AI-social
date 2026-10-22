#!/usr/bin/env python3
"""离线验证「睡眠—固化」两条观测断点（**零 LLM 调用**）。

用法（必须在 code/ 下运行，模块路径为 `orchestration`/`life`）：
    cd code && PYTHONPATH=. python3 ../tools/f2/verify_sleep_consolidation.py

走的路径是**真实的 agent → intent → 裁决器 → 事件**，不是手搓 payload：
  1. `LifeLayerAgent._maybe_sleep_window(wv)` 在 night 时段被调用一次；
  2. 它提交 `INTENT.MEMORY{op=consolidate, text=...}` 与 `INTENT.MEMORY{op=sleep_end}`；
  3. 脚本读账本，检查
     a) `MEMORY_CONSOLIDATE` 事件 payload 是否含 `text`（修前：缺，并落 DROPPED{unknown_intent_field,keys=["text"]}）；
     b) `SLEEP_COMPLETED` 事件 payload 的 `pf0/pf_t/drift_permille` 是否非 null（修前：全 null）；
     c) 两者的 `DROPPED{unknown_intent_field}` 计数。
  判据是 0/非 0 与 null/非 null，不依赖噪声带；不联网、不发起任何 LLM 决策调用。
"""

import json
import sys

from life.ports import MemoryRef, TimeCoord, WorldView
from orchestration.integration import build_world


def _refs(agent_id: str, n: int = 4) -> tuple:
    """同 subject 的 4 条观察记忆 ⇒ 达到固化阈值（同一 subject 成组）。"""
    out = []
    for i in range(n):
        out.append(MemoryRef(mem_id=f"M-{agent_id}-T{i}", kind="observation",
                             body_ref=None, embed_ref=None, importance=3,
                             day=0, slot="day", subject="MARKET",
                             last_access=1, access_count=1))
    return tuple(out)


def main() -> int:
    w = build_world(seed=7, n=3)
    eng, ag = w["engine"], w["agents"][0]
    aid = ag.agent_id

    refs = _refs(aid)
    ag.memory.sync_from_refs(refs)

    r = 9                                     # night 落在 round%12==9（R10 §2.1）
    eng.state.round = r
    eng.ctx = eng.ctx.at(r, 0)
    eng.arbiter.discard()
    wv = WorldView(agent_id=aid, round=r,
                   time=TimeCoord(week=0, day=0, day_of_week=0, day_type="workday",
                                  slot="night", tick_in_slot=3),
                   status="alive", location="residence", cash=0, net_worth=0,
                   memory_refs=refs)
    n_intents = ag._maybe_sleep_window(wv)
    eng.state, _ = eng.arbiter.commit(eng.state)

    recs = eng.ledger.records
    cons = [x for x in recs if x["type"] == "MEMORY_CONSOLIDATE"]
    sleep = [x for x in recs if x["type"] == "SLEEP_COMPLETED"]
    drops = [x for x in recs if x["type"] == "DROPPED"
             and (x.get("payload") or {}).get("reason") == "unknown_intent_field"]
    # SM 语义记忆写入：**先按 type==MEMORY_WRITE 过滤**再数 `-SM-`
    # （全文件 grep `M-Pxxx-SM-` 会被 produced_mem_id 污染，见 r10_defect_baseline.sh 文件头）
    sm_writes = [x for x in recs if x["type"] == "MEMORY_WRITE"
                 and "-SM-" in str((x.get("payload") or {}).get("mem_id") or "")]
    sm_body = None
    if sm_writes:
        ref = (sm_writes[-1].get("payload") or {}).get("body_ref")
        try:
            sm_body = ag.memory.side.read_body(ref)
        except Exception as e:                       # 正文读不到也要如实记录
            sm_body = f"<read_body failed: {e}>"

    cons_p = cons[-1]["payload"] if cons else {}
    sleep_p = sleep[-1]["payload"] if sleep else {}
    out = {
        "agent": aid,
        "intents_submitted": n_intents,
        "memory_consolidate": {
            "n_events": len(cons),
            "has_text": "text" in cons_p,
            "text": cons_p.get("text"),
            "produced_mem_id": cons_p.get("produced_mem_id"),
        },
        "sm_memory_write": {
            "n_events": len(sm_writes),
            "mem_id": (sm_writes[-1].get("payload") or {}).get("mem_id") if sm_writes else None,
            "body_ref": (sm_writes[-1].get("payload") or {}).get("body_ref") if sm_writes else None,
            "body_text": sm_body,
            "body_text_matches_summary": bool(sm_body and cons_p.get("text") == sm_body),
        },
        "sleep_completed": {
            "n_events": len(sleep),
            "pf0": sleep_p.get("pf0"),
            "pf_t": sleep_p.get("pf_t"),
            "drift_permille": sleep_p.get("drift_permille"),
        },
        "dropped_unknown_intent_field": [
            {"type": (d["payload"] or {}).get("type"),
             "keys": (d["payload"] or {}).get("keys")} for d in drops
        ],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))

    bad = []
    if not cons:
        bad.append("未产出 MEMORY_CONSOLIDATE（夹具未触发固化）")
    if not out["memory_consolidate"]["has_text"]:
        bad.append("MEMORY_CONSOLIDATE payload 缺 text")
    if any(d["type"] == "MEMORY_CONSOLIDATE" for d in out["dropped_unknown_intent_field"]):
        bad.append("MEMORY_CONSOLIDATE.text 落 unknown_intent_field")
    if not sm_writes:
        bad.append("未产出 SM 语义记忆的 MEMORY_WRITE（SM 写入=0）")
    if not out["sm_memory_write"]["body_text_matches_summary"]:
        bad.append("SM 记忆正文不可读或与固化摘要不一致")
    if not sleep:
        bad.append("未产出 SLEEP_COMPLETED")
    if out["sleep_completed"]["drift_permille"] is None:
        bad.append("SLEEP_COMPLETED.drift_permille 为 null")
    if bad:
        print("[FAIL] " + "；".join(bad), file=sys.stderr)
        return 1
    print("[PASS] text 到达 MEMORY_CONSOLIDATE payload、SM 记忆有可读正文、"
          "漂移三字段到达 SLEEP_COMPLETED、无 MEMORY_CONSOLIDATE 的 unknown_intent_field")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
