"""gate0 三样校验（**只读** `run.jsonl`，纯离线；不建 side-root、不调 LLM、不占串行门）。

用途：真批跑完后，判定「本批能否供 `T-D4-2` 的 gate0 用」。三样必须**全部**成立：

  ① **`RIFT_OPEN` 数 == 台账登记数**
     - 事件侧：`RIFT_OPEN` 的 **distinct `rift_id` 数**（同一 id 重复 OPEN 视为异常，单列）
     - 台账侧：离线重放 `DR.ingest_one()`（`enabled=True`）得到的登记数（按 `(agent_id, rift_id)` 计）
  ② **`RIFT_CLOSE` 数 == 台账注销数**
     - 事件侧：`reason ∈ {repair, expire, prune}` 三条之和；**`unknown` 单列、不计入**
     - 台账侧：重放中因"修复词注销 + `_prune` 丢弃"而消失的条数
  ③ **`dialogue_rift.open` 逐 seq 对齐「已 OPEN 未 CLOSE」**
     - 逐条 MSG（按 seq 升序）：维护每个 agent 的"已 OPEN 未 CLOSE"集合
     - 断言 `snapshot.open == len(该集合)` **且** `set(snapshot.rift_ids) == 该集合`
     - 这是 **逐数值相等**，不是子集包含（子集是更弱的自证档，**不足以判 gate0**）

**本脚本只有一条输入路径：显式 `--log <path>`。**
没有默认日志、没有内置样例、没有"小规模试跑"分支；文件不存在即 `exit 2`（不允许静默跳过）。

每样输出三态：`PASS` / `MISMATCH`（算得出但不符）/ `CANNOT-VERIFY(<item>)`（**算不出**，附 `missing` 说明缺什么）。
**`CANNOT-VERIFY` 时不给 `0`、不给百分比**——"算不出"和"等于 0"是两件事。
任何一样非 `PASS` ⇒ `gate0_ready = false`，`blockers` 逐条写明。
**不输出"通过/不通过"以外的效果判断**（D4 数值归 `repro-verifier`）。

用法：
    python3 tools/dr/rift_gate0_check.py --log v2/evidence/rift-on_n16r24_s42/run.jsonl
    python3 tools/dr/rift_gate0_check.py --log A.jsonl --out /tmp/gate0.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_ROOT, "code"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
KNOWN_REASONS = ("repair", "expire", "prune")


def load(path: str) -> list:
    """**唯一输入路径**：显式给的 `--log`。文件不存在 ⇒ `exit 2`（不静默跳过、不回退样例）。"""
    if not os.path.isfile(path):
        sys.stderr.write(f"[FATAL] 日志不存在：{path}\n"
                         f"        本脚本没有默认输入，也不会回退到任何样例/试跑数据（exit 2）\n")
        raise SystemExit(2)
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _visible_to(p: dict, etype: str, aid: str) -> bool:
    """与运行期一致的 MSG 可见性（`perception_scope`）。"""
    if etype == "MSG_PUBLIC":
        return True
    if etype == "MSG_DM":
        return aid in (p.get("from"), p.get("to"))
    if etype == "MSG_GROUP":
        return aid in (p.get("participants") or []) or aid in (p.get("from"),)
    return True


def _replay_ledger(recs: list) -> dict:
    """离线重放台账（`enabled=True`），返回登记/注销/期末条数。"""
    import life.dialogue_repair as DR

    params = dict(DR.DEFAULTS)
    params["enabled"] = True
    msgs = sorted([r for r in recs if str(r.get("type", "")) in MSG_TYPES],
                  key=lambda r: int(r.get("seq", 0)))
    agents = set()
    for m in msgs:
        p = m.get("payload") or {}
        for k in ("from", "author", "to"):
            if isinstance(p.get(k), str):
                agents.add(p[k])
        for x in (p.get("participants") or []):
            if isinstance(x, str):
                agents.add(x)
    agents = sorted(agents)
    rifts = {a: {} for a in agents}
    seen = {a: set() for a in agents}
    registered = resolved_repair = dropped_prune = 0
    last_round = None
    for m in msgs:
        seq = int(m.get("seq", 0))
        rnd = int(m.get("round", 0) or 0)
        etype = m.get("type")
        p = m.get("payload") or {}
        for a in agents:
            if not _visible_to(p, etype, a):
                continue
            before = set(rifts[a])
            DR.ingest_one(rifts[a], seen[a], seq, etype, p, rnd, a, params)
            after = set(rifts[a])
            registered += len(after - before)
            resolved_repair += len(before - after)
        if last_round is not None and rnd != last_round:
            before2 = {a: set(v) for a, v in rifts.items()}
            for a in agents:
                DR.prune(rifts[a], params, rnd)
            dropped_prune += sum(len(before2[a]) - len(rifts[a]) for a in agents)
        last_round = rnd
    return {"agents": len(agents), "registered": registered,
            "resolved_by_repair": resolved_repair, "dropped_by_prune": dropped_prune,
            "open_at_end": sum(len(v) for v in rifts.values())}


def check(recs: list) -> dict:
    opens = [r for r in recs if r.get("type") == "RIFT_OPEN"]
    closes = [r for r in recs if r.get("type") == "RIFT_CLOSE"]
    msgs = sorted([r for r in recs if str(r.get("type", "")) in MSG_TYPES],
                  key=lambda r: int(r.get("seq", 0)))

    # ---- ① 事件侧 OPEN ----
    open_ids = [o["payload"].get("rift_id") for o in opens]
    dup_open = sum(c - 1 for c in Counter(open_ids).values() if c > 1)

    # ---- ② 事件侧 CLOSE（按 reason 分布，unknown 单列）----
    reason_dist = Counter(c["payload"].get("reason") for c in closes)
    known_close = sum(reason_dist.get(k, 0) for k in KNOWN_REASONS)
    unknown_close = reason_dist.get("unknown", 0)
    other_close = sum(v for k, v in reason_dist.items() if k not in KNOWN_REASONS + ("unknown",))

    # ---- ③ 逐 seq：open 值 + rift_ids 与「已 OPEN 未 CLOSE」集合 ----
    events = sorted([*opens, *closes], key=lambda r: int(r.get("seq", 0)))
    live: dict = defaultdict(set)          # agent -> set(rift_id)
    ei = 0
    violations = []
    snap_checked = 0
    ids_key_msgs = 0
    for m in msgs:
        mseq = int(m.get("seq", 0))
        while ei < len(events) and int(events[ei]["seq"]) < mseq:
            ev = events[ei]
            aid = ev["payload"].get("agent_id")
            rid = ev["payload"].get("rift_id")
            if ev["type"] == "RIFT_OPEN":
                live[aid].add(rid)
            else:
                live[aid].discard(rid)
            ei += 1
        snap = ((m.get("payload") or {}).get("dialogue_rift") or None)
        if not isinstance(snap, dict):
            continue
        snap_checked += 1
        aid = ((m.get("payload") or {}).get("from") or (m.get("payload") or {}).get("author"))
        exp = live.get(aid, set())
        got_open = snap.get("open")
        if got_open is not None and int(got_open) != len(exp):
            violations.append({"seq": mseq, "agent": aid, "kind": "open_mismatch",
                               "snapshot_open": got_open, "expected": len(exp)})
        if "rift_ids" in snap:
            ids_key_msgs += 1
            if set(snap["rift_ids"]) != set(exp):
                violations.append({"seq": mseq, "agent": aid, "kind": "rift_ids_mismatch",
                                   "snapshot_ids": sorted(snap["rift_ids"]),
                                   "expected_ids": sorted(exp)})

    led = _replay_ledger(recs)
    blockers = []

    # ---- ① 三态 ----
    if len(opens) == 0 and led["registered"] == 0:
        s1 = {"status": "CANNOT-VERIFY(1_open_vs_ledger)", "missing":
              ["本批没有任何 RIFT_OPEN 事件，且重放台账登记也是 0 ⇒ 无法区分"
               "「没有负向话」与「rift_events 开关没生效」"]}
    elif len(set(open_ids)) == led["registered"] and dup_open == 0:
        s1 = {"status": "PASS"}
    else:
        s1 = {"status": "MISMATCH",
              "detail": f"OPEN 事件 distinct={len(set(open_ids))}（重复 {dup_open}）"
                        f" vs 重放登记={led['registered']}"}
    if s1["status"] != "PASS":
        blockers.append(f"① {s1['status']}")

    # ---- ② 三态 ----
    if len(closes) == 0 and (led["resolved_by_repair"] + led["dropped_by_prune"]) == 0:
        s2 = {"status": "CANNOT-VERIFY(2_close_vs_ledger)", "missing":
              ["本批没有任何 RIFT_CLOSE 事件，重放也无注销 ⇒ 无法区分「没有关闭」与「未接线」"]}
    elif known_close == led["resolved_by_repair"] + led["dropped_by_prune"]:
        s2 = {"status": "PASS"}
    else:
        s2 = {"status": "MISMATCH",
              "detail": f"CLOSE 事件 known={known_close} vs 重放注销(repair+prune)="
                        f"{led['resolved_by_repair']}+{led['dropped_by_prune']}"}
    if s2["status"] != "PASS":
        blockers.append(f"② {s2['status']}")

    # ---- ③ 三态 ----
    if snap_checked == 0:
        s3 = {"status": "CANNOT-VERIFY(3_snapshot_alignment)",
              "missing": ["没有任何 MSG 带 dialogue_rift 快照"]}
    elif ids_key_msgs == 0:
        s3 = {"status": "CANNOT-VERIFY(3_snapshot_alignment)",
              "missing": ["dialogue_rift.rift_ids 一条都没落（检查 rift_events 是否真的为 1）"]}
    elif violations:
        s3 = {"status": "MISMATCH", "detail": f"逐 seq 违例 {len(violations)} 条",
              "first": violations[0]}
    else:
        s3 = {"status": "PASS"}
    if s3["status"] != "PASS":
        blockers.append(f"③ {s3['status']}")

    return {
        "1_open_vs_ledger": {
            **s1,
            "rift_open_events": len(opens),
            "rift_open_distinct_ids": len(set(open_ids)),
            "duplicate_open_ids": dup_open,
            "ledger_registered": led["registered"],
            "match": len(set(open_ids)) == led["registered"] and dup_open == 0,
        },
        "2_close_vs_ledger": {
            **s2,
            "rift_close_events": len(closes),
            "reason_distribution": dict(reason_dist),
            "known_close_sum": known_close,
            "unknown_close": unknown_close,
            "other_close": other_close,
            "ledger_resolved_repair": led["resolved_by_repair"],
            "ledger_dropped_prune": led["dropped_by_prune"],
            "match": known_close == led["resolved_by_repair"] + led["dropped_by_prune"],
        },
        "3_snapshot_alignment": {
            **s3,
            "msgs_with_dialogue_rift": snap_checked,
            "msgs_with_rift_ids_key": ids_key_msgs,
            "violations": len(violations),
            "violation_samples": violations[:5],
            "match": snap_checked > 0 and ids_key_msgs > 0 and not violations,
        },
        "ledger": led,
        "blockers": blockers,
        "gate0_ready": (not blockers),
        "gate0_status": {k: v for k, v in (
            ("1_open_vs_ledger", s1["status"]), ("2_close_vs_ledger", s2["status"]),
            ("3_snapshot_alignment", s3["status"]))},
        "note": "unknown_close > 0 ⇒ **bug 信号**（有调用点没传 reason），单列且不计入 ② 的 match；"
                "gate0 判定不因此放宽，但需先修调用点",
    }


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="gate0 三样校验（只读）")
    ap.add_argument("--log", action="append", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv[1:])
    result = {"tool": "tools/dr/rift_gate0_check.py",
              "gate0_definition": {
                  "1": "RIFT_OPEN distinct rift_id 数 == 台账登记数",
                  "2": "RIFT_CLOSE reason∈{repair,expire,prune} 之和 == 台账注销数（unknown 单列不计）",
                  "3": "逐 seq：dialogue_rift.open == len(已OPEN未CLOSE) 且 set(rift_ids) == 该集合",
              },
              "inputs": []}
    for path in args.log:
        recs = load(path)
        result["inputs"].append({"log": path, "events": len(recs), **check(recs)})
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
