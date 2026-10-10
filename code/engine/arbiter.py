"""中央裁决器 Arbiter（C1 / §1.1 / P7 / 蓝图 §1.4 D1）。

**D1 口径（唯一）**：
  - `emit` = 把事件写入**本回合待提交缓冲区**（暂存），并增量折叠状态，**不落盘**；
  - **P6 COMMIT 是唯一 append 点**：一次性把本回合缓冲（含 P2 的 `LLM_CALL`、P3.5、P4）
    按全局固定顺序追加到哈希链；
  - **回滚**：本回合任一 hook 抛异常 / 守恒不成立 → 丢弃整个缓冲区（含已 emit 的
    `LLM_CALL`），仅追加 `SYSTEM_ERROR` / `ECONOMY_INVARIANT_VIOLATION`（自身必落），
    世界状态不变。

`Arbiter` 是唯一写入口：hook / 端口只经它 `emit`，绝不直接 append 或写 state。
"""

from __future__ import annotations

from .events import EventSpec
from .replay import apply_event
from .state import WorldState

_PROV_TIME_UNIT = 1000


class Arbiter:
    def __init__(self, ledger):
        self.ledger = ledger
        self._pending: list[EventSpec] = []

    # ---- 缓冲区状态 ----
    def pending(self) -> list[EventSpec]:
        return list(self._pending)

    def buffer_len(self) -> int:
        return len(self._pending)

    def discard(self) -> None:
        """丢弃整个待提交缓冲区（不触盘、不改已提交状态）。"""
        self._pending = []

    # ---- emit：入缓冲区 + 增量折叠（不落盘）----
    def emit(self, state: WorldState, specs: list) -> tuple[WorldState, list[int]]:
        seqs: list[int] = []
        for ev in specs:
            prov_seq = len(self.ledger.records) + len(self._pending)
            rec = {
                "seq": prov_seq,
                "round": ev.round,
                "phase": ev.phase,
                "actor": ev.actor,
                "type": ev.type,
                "payload": ev.payload,
                "mono_ts": ev.round * _PROV_TIME_UNIT + prov_seq,
                "prev_hash": "PENDING",
                "hash": "PENDING",
            }
            apply_event(state, rec)  # 增量折叠，供后续 hook / 端口读取
            self._pending.append(ev)
            seqs.append(prov_seq)
        return state, seqs

    # ---- commit：唯一 append 点（在 P6 调用）----
    def commit(self, state: WorldState) -> tuple[WorldState, list[dict]]:
        recs: list[dict] = []
        for ev in self._pending:
            rec = self.ledger.append_spec(ev)
            state.event_index[rec["seq"]] = rec  # 用真实记录覆盖临时索引
            recs.append(rec)
        self._pending = []
        return state, recs
