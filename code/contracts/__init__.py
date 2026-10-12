"""`contracts` —— 层间契约（纯类型/协议包，零业务依赖）。

依据 `v1.2/01-implementation-architecture.md` §1.1/§1.3（B1）/§2：
  - `models.py`    基础数据模型（Event/TurnSeal/WorldView/Intent/JudgmentRequest/AuditPayload）
  - `errors.py`    类型化错误（HashChainBroken/UnknownEventType/RoundRollback/IllegalJudgment）
  - `interfaces.py` IF-1~IF-7 + IF-2b/IF-2c 的 Protocol
  - `hooks.py`     中央裁决器 hook（L1–L7 / 4.1–4.8）Protocol + Ctx/Delta

**铁律**：本包只依赖 stdlib；被 kernel/life/freeze/emergence/orchestration 依赖，
自身**不依赖任何业务包**（import-linter 强制）。
"""

from .errors import (
    KernelError,
    HashChainBroken,
    UnknownEventType,
    RoundRollback,
    IllegalJudgment,
)
from .models import (
    AgentId, Round, Mu, Phase,
    Event, TurnSeal,
    TimeCoord, EventView, MemoryRef, WorldView, Intent, IntentResult,
    JudgmentRequest, AuditPayload,
)
from .hooks import Ctx, Delta, HookFn
from .actors import NON_AGENT_ACTORS, is_agent_actor, agent_or_none

__all__ = [
    "KernelError", "HashChainBroken", "UnknownEventType", "RoundRollback", "IllegalJudgment",
    "AgentId", "Round", "Mu", "Phase",
    "Event", "TurnSeal",
    "TimeCoord", "EventView", "MemoryRef", "WorldView", "Intent", "IntentResult",
    "JudgmentRequest", "AuditPayload",
    "Ctx", "Delta", "HookFn",
    "NON_AGENT_ACTORS", "is_agent_actor", "agent_or_none",
]
