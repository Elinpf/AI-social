"""只追加事件日志 + SHA-256 哈希链（P6 / §6.1）。

- Ledger 是 append-only：只追加、不修改、不删除；
- 每条记录带 prev_hash + hash，形成链式哈希（任一处篡改破坏后续所有 hash）；
- mono_ts = round * TIME_UNIT + phase_seq（逻辑时间，非墙钟）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .canon import GENESIS_HASH
from .events import EventSpec, compute_event_hash


@dataclass
class Ledger:
    time_unit: int = 1000
    engine_version: str = "v0.1-skeleton"
    records: list = field(default_factory=list)
    _round_seq: dict = field(default_factory=dict)  # round -> 本回合内已追加条数

    def append(self, round_no: int, phase: int, actor: str, type_: str, payload: dict | None = None,
               span: dict | None = None) -> dict:
        seq = len(self.records)
        prev_hash = self.records[-1]["hash"] if self.records else GENESIS_HASH
        rs = self._round_seq.get(int(round_no), 0)
        self._round_seq[int(round_no)] = rs + 1
        mono_ts = int(round_no) * self.time_unit + rs
        record = {
            "seq": seq,
            "round": int(round_no),
            "phase": int(phase),
            "actor": actor,
            "type": type_,
            "payload": payload or {},
            "mono_ts": mono_ts,
            "prev_hash": prev_hash,
        }
        if span is not None:  # T287 期①：可选区间；None ⇒ 不写字段（off 字节不变）
            record["span"] = span
        record["hash"] = compute_event_hash(record)  # 哈希覆盖去掉 hash 字段的整条记录
        self.records.append(record)
        return record

    def append_spec(self, ev: EventSpec) -> dict:
        kw = ev.as_kwargs()
        return self.append(kw["round"], kw["phase"], kw["actor"], kw["type"], kw["payload"],
                           span=kw.get("span"))

    # ---- 校验 ----
    def verify_chain(self) -> tuple[bool, str | None]:
        prev = GENESIS_HASH
        for i, r in enumerate(self.records):
            if r.get("seq") != i:
                return False, f"seq 非单调：位置 {i} 的 seq={r.get('seq')}"
            if r.get("prev_hash") != prev:
                return False, f"哈希链断裂：seq={r.get('seq')}"
            body = {k: v for k, v in r.items() if k != "hash"}
            if compute_event_hash(body) != r.get("hash"):
                return False, f"哈希不匹配：seq={r.get('seq')}"
            prev = r["hash"]
        return True, None

    def last_hash(self) -> str:
        return self.records[-1]["hash"] if self.records else GENESIS_HASH

    def turn_seal(self, round_no: int) -> dict | None:
        for r in reversed(self.records):
            if r["type"] == "TURN_SEAL" and r["round"] == round_no:
                return r
            if r["round"] < round_no:
                break
        return None


def verify_chain(records: list) -> tuple[bool, str | None]:
    """独立函数式校验（不依赖 Ledger 实例），供 replay 使用。"""
    prev = GENESIS_HASH
    for i, r in enumerate(records):
        if r.get("seq") != i:
            return False, f"seq 非单调：位置 {i} 的 seq={r.get('seq')}"
        if r.get("prev_hash") != prev:
            return False, f"哈希链断裂：seq={r.get('seq')}"
        body = {k: v for k, v in r.items() if k != "hash"}
        if compute_event_hash(body) != r.get("hash"):
            return False, f"哈希不匹配：seq={r.get('seq')}"
        prev = r["hash"]
    return True, None
