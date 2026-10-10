"""IF-2 submit_intent：L1 → D0 的唯一写入请求通道。

合法 intent → 交中央裁决器（Phase 3.5 / 4.x）结算；
非法 intent → 落 INTENT_REJECTED（08 §1.2 H），不产生状态变化。
本骨架：校验 + 入队；具体结算由对应 hook 负责。
"""

from __future__ import annotations

from .constants import PHASE_DECIDE
from .events import spec

# 合法意图类（00 §4.2 / 08 §2）
LEGAL_INTENT_CLASSES = {
    "INTENT.PLAN", "INTENT.MOVE", "INTENT.ACTIVITY", "INTENT.MEMORY",
    "INTENT.OBSERVE", "INTENT.RELATION", "INTENT.SOCIAL", "INTENT.TAG",
    "INTENT.NORM_PROPOSE", "INTENT.GOAL",
    "INTENT.ECON.ORDER_PLACE", "INTENT.ECON.ORDER_CANCEL",
    "INTENT.ECON.TRANSFER", "INTENT.ECON.LOAN_APPLY",
    "INTENT.ECON.TRADE", "INTENT.ECON.OFFER", "INTENT.ECON.CONTRACT_SIGN",
}


def submit_intent(engine, agent_id: str, intent: dict) -> dict:
    """返回 {ok, reason?, event_seqs}。"""
    cls = (intent or {}).get("intent_class")
    if cls not in LEGAL_INTENT_CLASSES:
        return _reject(engine, agent_id, cls, "unknown_intent_class", intent)
    if agent_id not in engine.state.agents:
        return _reject(engine, agent_id, cls, "unknown_agent", intent)
    # 合法：入 pending_intents 队列（由 3.5 / 4.x hook 消费；队列不入 state_hash）。
    engine.state.pending_intents.append({"agent_id": agent_id, "intent_class": cls,
                                         "payload": intent.get("payload", {})})
    return {"ok": True, "event_seqs": []}


def _reject(engine, agent_id, cls, reason, requested) -> dict:
    ev = spec(engine.state.round, PHASE_DECIDE, agent_id, "INTENT_REJECTED", {
        "agent_id": agent_id,
        "intent_class": cls,
        "reason": reason,
        "requested": requested,
    })
    seqs = engine.emit_specs([ev])  # 入缓冲区（P6 落盘）
    return {"ok": False, "reason": reason, "event_seqs": list(seqs)}
