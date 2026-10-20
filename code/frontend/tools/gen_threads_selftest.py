#!/usr/bin/env python3
"""gen_threads_selftest.py — 无浏览器门禁：验证 gen_threads.py 的聚合口径（确定性、可复跑）。

跑法（不需要 pytest、不联网）：
    cd code && python frontend/tools/gen_threads_selftest.py
    → 全绿输出 PASS；任一断言失败 → 非零退出。

覆盖（每条都对应页面上的一个展示口径）：
  A 新格式（带 thread_id/turn_index/reply_to/participants/ctx）→ 聚成 1 条多轮线程，轮序按 turn_index；
  B 旧格式（无 thread_id）→ 每条各自成一条单发线程（legacy=True），**不合并、不推断**，
    且旧格式 msg_id 撞车（真实历史日志 D-6-0 被多人复用）时**不会**被错误合并；
  C 语境证据只取「本条之前」的真实事件（after 值来自 RELATION_CHANGE，seq 可回指）；
  D 说话人不在 participants 里时不新增人物（不做补造）；
  E 空世界日志（无 MSG_*）→ messages=0，页面走空态而不报错；
  F 同一输入跑两次输出**逐字节一致**（除 generated_at 无关字段外无时间戳 → 天然确定）。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_threads.py"
FRONTEND = HERE.parent


def write_log(path: Path, recs: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def ev(seq, rnd, typ, payload, actor="P001", phase=3):
    return {"seq": seq, "round": rnd, "phase": phase, "actor": actor,
            "type": typ, "payload": payload, "mono_ts": rnd * 12 + seq}


def run(log: Path, out: Path) -> dict:
    r = subprocess.run([sys.executable, str(GEN), "--log", str(log), "--out", str(out),
                        "--personas", str(FRONTEND / "data/personas.json"),
                        "--places", str(FRONTEND / "data/places.json")],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"gen_threads 失败: {r.stderr}"
    return json.loads(out.read_text(encoding="utf-8"))


def case_threaded(tmp: Path) -> None:
    recs = [
        ev(1, 0, "AGENT_BORN", {"agent_id": "P001"}),
        ev(2, 0, "RELATION_CHANGE", {"from": "P001", "to": "P004", "dim": "affinity",
                                     "before": 0, "after": 5, "cause": "copresence"}),
        ev(3, 0, "NEED_UPDATE", {"agent_id": "P001", "dim": "social", "before": 40, "after": 28,
                                 "cause": "decay"}),
    ]
    tid = "TH-P001-0"
    for i, (who, to, body) in enumerate([
        ("P001", "P004", "秀娘，今天的糕蒸得真香。"),
        ("P004", "P001", "来尝尝，刚出笼的。"),
        ("P001", "P004", "那我可不客气了。"),
    ]):
        recs.append(ev(10 + i, i, "MSG_DM", {
            "msg_id": f"D-0-{i}", "from": who, "to": to, "body": body,
            "thread_id": tid, "turn_index": i,
            "reply_to": (f"D-0-{i-1}" if i else None),
            "participants": ["P001", "P004"],
            "ctx": {"relation": 5, "mood": "warm", "need": {"social": 28}, "topic": "点心"},
            "day": 0, "slot": "morning", "place": "kitchen"}, actor=who))
    log = tmp / "threaded.jsonl"
    write_log(log, recs)
    d = run(log, tmp / "threaded.json")

    # A 线程聚合 + 轮序
    assert d["stats"]["threads"] == 1, d["stats"]
    assert d["stats"]["multi_turn_threads"] == 1
    t = d["threads"][0]
    assert t["thread_id"] == tid and t["turns"] == 3 and t["legacy"] is False
    assert [m["turn_index"] for m in t["messages"]] == [0, 1, 2]
    assert [m["reply_to"] for m in t["messages"]] == [None, "D-0-0", "D-0-1"]
    assert t["participants"] == ["P001", "P004"], t["participants"]
    assert t["place"] == "kitchen"
    # C 语境证据：取本条之前最近一次 RELATION_CHANGE / NEED_UPDATE，带 seq
    ctx = t["messages"][0]["context"]
    rel = ctx["relation"]
    assert rel and rel[0]["after"] == 5 and rel[0]["seq"] == 2, rel
    assert ctx["needs"]["P001"][0]["after"] == 28
    assert ctx["ctx_snapshot"]["topic"] == "点心"
    # 消息 seq 原样保留（可回指原始日志）
    assert [m["seq"] for m in t["messages"]] == [10, 11, 12]
    print("  [A/C] 新格式聚合 + 语境证据 OK")


def case_legacy(tmp: Path) -> None:
    # 旧格式：msg_id 撞车（真实日志 D-6-0 同 round 被多人复用）
    recs = [
        ev(1, 6, "MSG_DM", {"msg_id": "D-6-0", "from": "P001", "to": "P002", "body": "甲",
                            "place": "farm", "day": 0, "slot": "morning"}),
        ev(2, 6, "MSG_DM", {"msg_id": "D-6-0", "from": "P003", "to": "P004", "body": "乙",
                            "place": "farm", "day": 0, "slot": "morning"}),
        ev(3, 6, "MSG_PUBLIC", {"msg_id": "P-6-0", "author": "P005", "body": "丙",
                                "scope": "global", "day": 0, "slot": "morning"}),
    ]
    log = tmp / "legacy.jsonl"
    write_log(log, recs)
    d = run(log, tmp / "legacy.json")
    # B 每条单发、不合并（3 条消息 → 3 条线程）
    assert d["stats"]["messages"] == 3, d["stats"]
    assert d["stats"]["threads"] == 3, d["stats"]
    assert d["stats"]["legacy_threads"] == 3
    assert d["stats"]["multi_turn_threads"] == 0
    assert all(t["turns"] == 1 and t["legacy"] for t in d["threads"])
    assert {t["messages"][0]["body"] for t in d["threads"]} == {"甲", "乙", "丙"}
    # D 说话人只来自日志，不补造
    assert d["threads"][2]["participants"] == ["P005"]
    print("  [B/D] 旧格式单发 + msg_id 撞车不误合并 OK")


def case_empty(tmp: Path) -> None:
    recs = [ev(1, 0, "AGENT_BORN", {"agent_id": "P001"}),
            ev(2, 0, "TURN_SEAL", {"round": 0, "last_seq": 2})]
    log = tmp / "empty.jsonl"
    write_log(log, recs)
    d = run(log, tmp / "empty.json")
    # E 空态
    assert d["stats"]["messages"] == 0 and d["threads"] == []
    print("  [E] 无对话事件 → 空态数据 OK")


def case_determinism(tmp: Path) -> None:
    log = tmp / "threaded.jsonl"
    a = run(log, tmp / "a.json")
    b = run(log, tmp / "b.json")
    # F 同一输入两次输出一致（无墙钟字段 → 逐字节相同）
    assert (tmp / "a.json").read_bytes() == (tmp / "b.json").read_bytes(), "同一输入两次输出不一致"
    print("  [F] 确定性（两次输出逐字节一致）OK")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("[gen_threads 自检]")
        case_threaded(tmp)
        case_legacy(tmp)
        case_determinism(tmp)
        case_empty(tmp)
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
