"""T-RIFT-EVENTS 三档 mock 自证（worktree 内、不调真 LLM、不改 code/ 行为默认值）。

档：
  A `enabled=1, rift_events=0`（默认） ⇒ **不产 RIFT_*、`dialogue_rift` 无 `rift_ids`**
  B `enabled=1, rift_events=1`          ⇒ 产 `RIFT_OPEN` / `RIFT_CLOSE{repair}`，且与台账/快照对账
  C `enabled=0, rift_events=1`          ⇒ 全无（总开关关 ⇒ 开关无效果）

注入方式（不依赖 LLM 产出负向词）：
  在已提交账本上**追加**两条 MSG（`Arbiter.emit + commit` 官方路径）：
    ① `from=P001,to=P002,thread=T1,body="你什么意思，我很生气"`（负向 ⇒ 应登记 rift）
    ② 同线程 `from=P001,to=P002,body="对不起，我不是那个意思"`（修复 ⇒ 应注销）
  随后跑若干轮，让 P002 在 `_communicate` 里 `DR.ingest` 吸收（observer 由开关决定是否传入）。

对账口径：
  `RIFT_OPEN` 条数 == 该 agent 台账登记数（= 出现过的不同 `rift_id` 数）
  `RIFT_CLOSE` 条数 == 台账注销数（`reason` 分布）
  `dialogue_rift.rift_ids` ⊆ 当时仍 open 的集合（逐条校验）

用法（worktree 的 `code/` 下）：
    python3 ../tools/dr/rift_events_proof.py [--n 4] [--rounds 6] [--out /tmp/x.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_ROOT, "code"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ENVS = ("HITT_DIALOGUE_REPAIR", "HITT_DR_RIFT_EVENTS", "HITT_DR_REPAIR_ASK",
        "HITT_DR_RECORD_ONLY", "HITT_DR_PICK_MARK")
NEG_BODY = "你什么意思，我很生气"
REP_BODY = "对不起，我不是那个意思"
THREAD = "dm:P002:P001:r1"


def _inject(eng, actor: str, payload: dict) -> int:
    """在**已提交账本**上追加一条 MSG（走 Arbiter 官方 emit+commit，会 fold 到 state）。"""
    from engine.constants import PHASE_COMMUNICATE
    from engine.events import spec
    rnd = int(eng.state.round)
    eng.state, seqs = eng.arbiter.emit(eng.state, [spec(rnd, PHASE_COMMUNICATE, actor, "MSG_DM", payload)])
    eng.state, _ = eng.arbiter.commit(eng.state)
    return seqs[0]


def _run_arm(mode: str, n: int, rounds: int, seed: int) -> dict:
    import life.dialogue_repair as DR
    from orchestration.integration import build_world

    saved = {k: os.environ.get(k) for k in ENVS}
    os.environ.pop("HITT_LLM_PROVIDER", None)
    for k in ENVS:
        os.environ.pop(k, None)
    if mode in ("B", "C"):
        os.environ["HITT_DR_RIFT_EVENTS"] = "1"
    if mode in ("A", "B"):
        os.environ["HITT_DIALOGUE_REPAIR"] = "1"
    DR._cache = None
    DR.set_override(None)

    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    try:
        eng.run_round(0)
        p1 = {"from": "P001", "to": "P002", "participants": ["P001", "P002"],
              "thread_id": THREAD, "msg_uid": "INJ-1", "msg_id": "INJ-1",
              "body": NEG_BODY, "place": "market", "slot": "am", "topic": "工钱",
              "turn_index": 0, "refs": [], "tag_hints": [], "ctx": {}}
        _inject(eng, "P001", p1)
        for r in range(1, max(2, rounds // 2)):
            eng.run_round(r)
        p2 = dict(p1)
        p2.update({"msg_uid": "INJ-2", "msg_id": "INJ-2", "body": REP_BODY,
                   "turn_index": 1, "reply_to": "INJ-1"})
        _inject(eng, "P001", p2)
        for r in range(max(2, rounds // 2), rounds):
            eng.run_round(r)

        recs = eng.ledger.records
        opens = [r for r in recs if r.get("type") == "RIFT_OPEN"]
        closes = [r for r in recs if r.get("type") == "RIFT_CLOSE"]
        msgs = [r for r in recs if str(r.get("type", "")).startswith("MSG")]
        with_ids = [m for m in msgs
                    if isinstance((m.get("payload") or {}).get("dialogue_rift"), dict)
                    and "rift_ids" in (m["payload"]["dialogue_rift"] or {})]
        with_rift = [m for m in msgs
                     if isinstance((m.get("payload") or {}).get("dialogue_rift"), dict)]

        # 对账：open 的不同 rift_id 数 vs close 的不同 rift_id 数
        open_ids = [o["payload"]["rift_id"] for o in opens]
        close_ids = [c["payload"]["rift_id"] for c in closes]
        # 逐条校验快照 rift_ids ⊆ "当时仍 open" 的集合（按 seq 顺序推进）
        sorted_ids = set()
        bad_snapshot = 0
        events_sorted = sorted([*opens, *closes], key=lambda r: int(r.get("seq", 0)))
        idx = 0
        for m in sorted(msgs, key=lambda r: int(r.get("seq", 0))):
            while idx < len(events_sorted) and int(events_sorted[idx]["seq"]) < int(m["seq"]):
                ev = events_sorted[idx]
                if ev["type"] == "RIFT_OPEN":
                    sorted_ids.add(ev["payload"]["rift_id"])
                else:
                    sorted_ids.discard(ev["payload"]["rift_id"])
                idx += 1
            snap = ((m.get("payload") or {}).get("dialogue_rift") or {})
            ids = snap.get("rift_ids")
            if ids is not None and not set(ids) <= sorted_ids:
                bad_snapshot += 1

        return {
            "mode": mode,
            "env": {k: os.environ.get(k, "unset") for k in ENVS},
            "rift_events_flag": DR.load_params().get("rift_events"),
            "enabled_flag": DR.load_params().get("enabled"),
            "n": n, "rounds": rounds, "seed": seed,
            "events_total": len(recs),
            "msg_total": len(msgs),
            "msgs_with_dialogue_rift": len(with_rift),
            "msgs_with_rift_ids_key": len(with_ids),
            "RIFT_OPEN_count": len(opens),
            "RIFT_CLOSE_count": len(closes),
            "rift_open_ids": open_ids,
            "rift_close_ids": close_ids,
            "rift_close_reasons": sorted({c["payload"].get("reason") for c in closes}),
            "distinct_open_ids": len(set(open_ids)),
            "distinct_close_ids": len(set(close_ids)),
            "snapshot_ids_subset_of_open": bad_snapshot == 0,
            "snapshot_subset_violations": bad_snapshot,
        }
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        DR._cache = None


def _reason_probes() -> dict:
    """函数级逼出 `prune` / `expire` 两条真实 `RIFT_CLOSE`（不改默认配置，只在本进程用 override 参数）。

    ⚠ 为什么只能在函数级做：默认 `max_open=3` / `max_age_rounds=84`，mock 小世界跑不到
    （要同时存在 4 条旧账，或跑满 85 轮）。这里用**极小参数**直接驱动 `ingest` 的 `_prune` 分支。
    """
    import life.dialogue_repair as DR

    def ev(seq: int, frm: str, body: str, thread: str, uid: str):
        return type("E", (), {"type": "MSG_DM", "seq": seq, "round": 0,
                              "payload": {"from": frm, "to": "P002", "body": body,
                                          "thread_id": thread, "msg_uid": uid}})()

    out = {}
    # ---- D 档：max_open=1，连登两条不同线程 ⇒ 较早那条被容量截断 ⇒ close{prune}
    p = dict(DR.DEFAULTS); p.update({"enabled": True, "max_open": 1, "max_age_rounds": 999})
    rifts, seen, calls = {}, set(), []
    obs = lambda k, d: calls.append((k, d))
    DR.ingest(rifts, seen, [ev(1, "P001", "你什么意思，我很生气", "T1", "m1")], "P002", p, 0, observer=obs)
    DR.ingest(rifts, seen, [ev(2, "P003", "烦死了，凭什么", "T2", "m2")], "P002", p, 0, observer=obs)
    out["D_prune"] = {
        "params": {"max_open": 1, "max_age_rounds": 999},
        "closes": [d for k, d in calls if k == "close"],
        "open_after": sorted(rifts),
        "reason_observed": sorted({d["reason"] for k, d in calls if k == "close"}),
    }

    # ---- E 档：max_age_rounds=1，rift 登记于 round 0，到 round 5 触发超龄 ⇒ close{expire}
    p2 = dict(DR.DEFAULTS); p2.update({"enabled": True, "max_age_rounds": 1, "max_open": 99})
    rifts2, seen2, calls2 = {}, set(), []
    obs2 = lambda k, d: calls2.append((k, d))
    DR.ingest(rifts2, seen2, [ev(1, "P001", "你什么意思，我很生气", "T1", "m1")], "P002", p2, 0, observer=obs2)
    DR.ingest(rifts2, seen2, [], "P002", p2, 5, observer=obs2)     # 无新事件，只为触发 _prune
    out["E_expire"] = {
        "params": {"max_age_rounds": 1, "max_open": 99},
        "closes": [d for k, d in calls2 if k == "close"],
        "open_after": sorted(rifts2),
        "reason_observed": sorted({d["reason"] for k, d in calls2 if k == "close"}),
    }
    return out


def main(argv: list) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv[1:])

    arms = {m: _run_arm(m, args.n, args.rounds, args.seed) for m in ("A", "B", "C")}
    reason_probes = _reason_probes()
    A, B, C = arms["A"], arms["B"], arms["C"]
    checks = {
        # ① 默认关：无事件、无 rift_ids 键
        "A_no_rift_events": A["RIFT_OPEN_count"] == 0 and A["RIFT_CLOSE_count"] == 0,
        "A_no_rift_ids_key": A["msgs_with_rift_ids_key"] == 0,
        # ② 开关开：事件与台账对账
        "B_has_open": B["RIFT_OPEN_count"] > 0,
        "B_open_ids_unique": B["distinct_open_ids"] == B["RIFT_OPEN_count"],
        "B_has_close": B["RIFT_CLOSE_count"] > 0,
        "B_close_reason_repair": "repair" in B["rift_close_reasons"],
        "B_open_close_same_ids": set(B["rift_open_ids"]) >= set(B["rift_close_ids"]),
        "B_has_rift_ids_key": B["msgs_with_rift_ids_key"] > 0,
        "B_snapshot_subset_of_open": B["snapshot_ids_subset_of_open"],
        # ③ enabled=0 ⇒ 开关无效果
        "C_no_rift_events": C["RIFT_OPEN_count"] == 0 and C["RIFT_CLOSE_count"] == 0,
        "C_no_rift_ids_key": C["msgs_with_rift_ids_key"] == 0,
        # ④ expire / prune **各有独立样例**（函数级极小参数逼出）
        "D_prune_reason_observed": "prune" in reason_probes["D_prune"]["reason_observed"],
        "E_expire_reason_observed": "expire" in reason_probes["E_expire"]["reason_observed"],
        # ⑤ 三种已知 reason 各有证据（repair 由 B 档给）
        "all_three_reasons_have_samples": (
            "repair" in B["rift_close_reasons"]
            and "prune" in reason_probes["D_prune"]["reason_observed"]
            and "expire" in reason_probes["E_expire"]["reason_observed"]),
    }
    checks["all_pass"] = all(checks.values())
    out = {"tool": "tools/dr/rift_events_proof.py", "card": "T-RIFT-EVENTS / T-RIFT-EVENTS-FIX",
           "arms": arms, "reason_probes": reason_probes, "checks": checks}
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    return 0 if checks["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
