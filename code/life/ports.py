"""Life-layer <-> deterministic kernel ports (IF-1 / IF-2 / IF-3 subset).

Contract source: `v1.1/00-architecture.md` §4.1 (IF-1..IF-7),
`v1.1/08-engine-stats-extension.md` §1.1/§2 and `v1/03-engine-stats.md` §2.

The life layer ONLY talks to the world through these two calls:
  * IF-1  perceive(agent_id) -> WorldView        (read-only, no side effect)
  * IF-2  submit_intent(agent_id, intent) -> IntentResult

It never mutates world state directly. Everything the agent "does" becomes an
Intent handed to the arbiter; the arbiter decides whether it becomes a fact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# ---- intent classes (00 §4.2) -------------------------------------------------
INTENT_PLAN = "INTENT.PLAN"
INTENT_MOVE = "INTENT.MOVE"
INTENT_ACTIVITY = "INTENT.ACTIVITY"
INTENT_MEMORY = "INTENT.MEMORY"
INTENT_OBSERVE = "INTENT.OBSERVE"
INTENT_RELATION = "INTENT.RELATION"
INTENT_GOAL = "INTENT.GOAL"
INTENT_SOCIAL = "INTENT.SOCIAL"

# ---- economy / exchange intents (v2/04 §5, 08 §1.2 R) ------------------------
# Existing econ intents (v1) + the T126/T129 additions. Declared here so the
# kernel adapter (which validates against `ALL_INTENT_CLASSES`) can route them.
INTENT_ECON_ORDER_PLACE = "INTENT.ECON.ORDER_PLACE"   # v1: place an order
INTENT_ECON_ORDER_CANCEL = "INTENT.ECON.ORDER_CANCEL"  # v1/new: cancel (must be observable)
INTENT_ECON_TRANSFER = "INTENT.ECON.TRANSFER"          # v1: pay transfer
INTENT_ECON_LOAN_APPLY = "INTENT.ECON.LOAN_APPLY"      # v1: loan apply
INTENT_ECON_TRADE = "INTENT.ECON.TRADE"                # new: bilateral exchange -> EXCHANGE_SETTLED
INTENT_ECON_OFFER = "INTENT.ECON.OFFER"                # new: -> OFFER_CREATED/COUNTERED/...
INTENT_ECON_CONTRACT_SIGN = "INTENT.ECON.CONTRACT_SIGN"  # new: -> CONTRACT_CREATED

ALL_INTENT_CLASSES = (
    INTENT_PLAN, INTENT_MOVE, INTENT_ACTIVITY, INTENT_MEMORY, INTENT_OBSERVE,
    INTENT_RELATION, INTENT_GOAL, INTENT_SOCIAL,
    INTENT_ECON_ORDER_PLACE, INTENT_ECON_ORDER_CANCEL, INTENT_ECON_TRANSFER,
    INTENT_ECON_LOAN_APPLY, INTENT_ECON_TRADE, INTENT_ECON_OFFER,
    INTENT_ECON_CONTRACT_SIGN,
)

# ---- INTENT.SOCIAL payload contract (v2 P1, T100/T98 ↔ engine T97) -----------
# Life produces the wording; the kernel validates legality and wraps it into
# MSG_DM / MSG_PUBLIC / MSG_GROUP (one of the three channels). Field names are the
# contract locked with kernel-dev:
#   {
#     "scope": "private" | "place_group" | "global",   # channel selector
#     "to": <AgentId> | None,        # required for scope=private
#     "group_id": <str> | None,      # required for scope=place_group
#     "body": "<LLM 生成并冻结的措辞>",
#     "body_ref": <str> | None,      # long text -> side storage (optional)
#     "refs": [<msg_id>|<event_seq>],# 转述类必填；原创为 []（T27）
#     "tag_hints": [<str>],
#   }
# scope -> channel/visibility (kernel, via visible_events()/PERCEPTION_SCOPE):
#   private -> MSG_DM (visibility=private) ; global -> MSG_PUBLIC (global) ;
#   place_group -> MSG_GROUP (members).
SOCIAL_SCOPES = ("private", "place_group", "global")


@dataclass(frozen=True)
class TimeCoord:
    week: int
    day: int
    day_of_week: int
    day_type: str
    slot: str
    tick_in_slot: int

    @classmethod
    def from_dict(cls, d: dict) -> "TimeCoord":
        return cls(
            week=int(d["week"]), day=int(d["day"]), day_of_week=int(d["day_of_week"]),
            day_type=str(d["day_type"]), slot=str(d["slot"]), tick_in_slot=int(d["tick_in_slot"]),
        )


@dataclass(frozen=True)
class EventView:
    """A read-only projection of one ledger event, as seen by an agent."""
    seq: int
    round: int
    phase: int
    actor: str
    type: str
    payload: dict
    place: str | None = None


@dataclass(frozen=True)
class MemoryRef:
    """A reference to a memory node (body/embedding live in side storage, 06 §3.2)."""
    mem_id: str
    kind: str
    body_ref: str
    embed_ref: str
    importance: int
    day: int
    slot: str
    subject: str | None = None
    source_event_seq: int | None = None
    last_access: int = 0
    access_count: int = 0


@dataclass(frozen=True)
class WorldView:
    """IF-1 output: everything an agent may observe at `round`, nothing more."""
    agent_id: str
    round: int
    time: TimeCoord
    status: str
    location: str
    cash: int
    net_worth: int
    visible_events: tuple[EventView, ...] = ()
    memory_refs: tuple[MemoryRef, ...] = ()
    # 自有库存（仅本人可见）：((good_id, qty), ...)，按 good_id 升序，qty>0
    inventory: tuple[tuple[str, int], ...] = ()
    # 自有且**可转让**的 goods（good_id 升序）：供 life 过滤不可转让品（如 service）
    transferable_goods: tuple[str, ...] = ()
    # M4 分时调度：本回合是否允许该 agent 调用 LLM。默认恒 True（仅当
    # policy.llm_budget.schedule_enabled=true 时按 Kc 限流，否则**行为与现状一致**）。
    llm_permit: bool = True
    # optional: unconsumed messages addressed to the agent
    inbox: tuple[EventView, ...] = ()
    # T354 期②：当前进行中的活动（纯派生：`ACTIVITY_STARTED` 无对应 `COMPLETED`）；
    # 形如 `{"activity_type":..., "place":...}`，None=无。**不新增真相源、不入 state_hash**；
    # `time.ongoing.enabled=False` 时恒 None。
    current_activity: dict | None = None

    @property
    def day(self) -> int:
        return self.time.day

    @property
    def slot(self) -> str:
        return self.time.slot


@dataclass(frozen=True)
class Intent:
    intent_class: str
    agent_id: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IntentResult:
    ok: bool
    reason: str | None = None
    event_seqs: tuple[int, ...] = ()


@runtime_checkable
class KernelPort(Protocol):
    """The narrow surface the life layer depends on (implemented by engine/)."""

    def perceive(self, agent_id: str) -> WorldView: ...

    def submit_intent(self, agent_id: str, intent: Intent) -> IntentResult: ...

    def current_round(self) -> int: ...

    def derive_time(self, round_no: int) -> TimeCoord: ...

    def round_events(self, round_no: int, types: tuple | None = None) -> list[dict]:
        """某回合的事件记录（`seq` 升序、顺序不变；只读，不得原地改元素）。

        `types=None` ⇒ 该回合全部；`types=(t1,...)` ⇒ 仅这些 type。内核走派生累加器
        （T312/T295），life 不再全扫 `event_index`。签名与 `KernelAdapter.round_events` 一致。
        """
        ...
