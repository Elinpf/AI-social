"""事件外壳与事件规格（§6.1 / 08 §1.1）。

事件记录（写入 Ledger 的最终形态）字段：
  seq, round, phase, actor, type, payload, mono_ts, prev_hash, hash

哈希：hash = "sha256:" + SHA256(canonical_json(record 去掉 hash 字段))
mono_ts：逻辑时间 = round * TIME_UNIT + phase_seq（非墙钟）。

hook / phase 产出的不是最终记录，而是 EventSpec（无 seq/prev_hash/hash/mono_ts），
由中央裁决器 Arbiter 统一落账，保证「写世界的只有裁决器」。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .canon import GENESIS_HASH, hash_obj

# 事件类型（v1 §2.3 + 08 §1.2）。仅登记骨架需要的类型；
# 新增类型必须在此登记，并在 replay.apply_event 注册对应的确定性折叠器。
EVENT_TYPES = {
    # 世界/创世（内核扩展）
    "WORLD_INIT",
    # v1 经济
    "AGENT_BORN", "INIT_ENDOW", "TRANSFER", "MARKET_TRADE",
    "LOAN_ISSUED", "LOAN_REPAY", "INTEREST_CHARGED", "LOAN_DEFAULT",
    "TAX_LEVIED", "UBI_PAID", "METABOLISM", "PENALTY_APPLIED",
    "REVIVE_FEE_PAID", "MONEY_MINTED", "MONEY_BURNED",
    # v1 生命周期 / 审计
    "STATE_CHANGE", "AGENT_DIED", "AGENT_REVIVED",
    "MSG_PUBLIC", "MSG_DM", "MSG_GROUP", "LLM_CALL", "SYSTEM_ERROR",
    # v1.1 生活/时间/场所
    "TIME_MARK", "PLACE_MOVE", "PLACE_ARRIVED",
    "SCHEDULE_PLANNED", "SCHEDULE_REVISED",
    "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "ACTIVITY_INTERRUPTED",
    "NEED_UPDATE", "GOAL_SET", "GOAL_PROGRESS", "GOAL_ACHIEVED", "GOAL_ABANDON",
    "RELATION_CHANGE", "RELATION_ENCOUNTER",
    "MEMORY_WRITE", "MEMORY_RETRIEVE", "MEMORY_REFLECT",
    # T233 / 08 §1.2 S：睡眠 / 记忆整合遗忘 / 人格漂移（Fork B 口径：可审计）
    "SLEEP_STARTED", "SLEEP_COMPLETED", "MEMORY_CONSOLIDATE", "MEMORY_FORGET", "PERSONA_DRIFT",
    # v1.1 涌现/传播
    "OBSERVATION", "SEED_EVENT", "TAG_EMITTED", "ROLE_CHANGE",
    "NORM_PROPOSED", "NORM_ADOPTED", "NORM_VIOLATED",
    # v1.1 软判定 / 叙事（冻结 / 纯输出）
    "LLM_JUDGMENT", "NARRATIVE",
    # v1.1 银行 / 群组 / 技能 / 协商 / 冲突
    "DEPOSIT", "WITHDRAW", "INTEREST_PAID",
    "GROUP_CREATED", "GROUP_JOINED", "GROUP_LEFT",
    "SKILL_PRACTICE", "SKILL_LEVEL_UP", "SKILL_OUTPUT",
    "OFFER_CREATED", "OFFER_ACCEPTED", "OFFER_REJECTED", "OFFER_COUNTERED", "OFFER_EXPIRED",
    "SCORE_POSTED", "RANKING_EMITTED", "CONFLICT_STARTED", "CONFLICT_RESOLVED",
    # v2 物理层（T90 / 08 §1.2 O）
    "PRODUCE", "CONSUME", "DEPRECIATE", "PRODUCE_OVERFLOW", "VOTE_CAST",
    # v2 交易/契约原语（T129/T131 / 08 §1.2 R/P）
    "EXCHANGE_SETTLED", "CONTRACT_CREATED", "CONTRACT_FULFILLED",
    "CONTRACT_VIOLATED", "CONTRACT_EXPIRED",
    "ORDER_CANCEL",  # v2/04 §6 A2c：撤单可观测
    "SERVICE_DELIVERED",  # T278 / 08 §1.2 V：服务即时交付（inventory-neutral）
    # v2 世界导演 / 事件制造机（T238 登记 / 08 §1.2 T）
    "WORLD_DIRECTIVE", "WORLD_GROUP_EVENT", "WORLD_DIRECTIVE_REJECTED", "FORGE_FIRED",
    # v1.1 审计
    "INTENT_REJECTED", "ECONOMY_INVARIANT_VIOLATION", "DROPPED", "DEGRADE",
    # T265 个体决策节拍（08 §1.2 S / §3.2）：唤醒 / 静默审计
    "WAKE", "IDLE",
    # 每回合封条
    "TURN_SEAL",
}


@dataclass
class EventSpec:
    """未落账的事件规格：由 hook / phase 产出，交 Arbiter 落账。"""

    round: int
    phase: int
    actor: str
    type: str
    payload: dict = field(default_factory=dict)

    def as_kwargs(self) -> dict:
        return {
            "round": self.round,
            "phase": self.phase,
            "actor": self.actor,
            "type": self.type,
            "payload": self.payload,
        }


def spec(round_no: int, phase: int, actor: str, type_: str, payload: dict | None = None) -> EventSpec:
    if type_ not in EVENT_TYPES:
        raise ValueError(f"未登记的事件类型: {type_!r}（请在 engine/events.py 登记并在 apply_event 注册折叠器）")
    return EventSpec(round=round_no, phase=phase, actor=actor, type=type_, payload=payload or {})


def compute_event_hash(record_without_hash: dict) -> str:
    return hash_obj(record_without_hash)


__all__ = ["EventSpec", "spec", "EVENT_TYPES", "GENESIS_HASH", "compute_event_hash"]
