"""LLM 冻结层（Freeze Layer）——v1.1 生活/涌现实验的 LLM 调用统一入口。

设计目标（对齐 v1.1/00-architecture.md §1.5/§4.6/§5.4/§5.5 与
v1.1/08-engine-stats-extension.md §1.2）：

- 所有 LLM 调用必经 :class:`~freeze.llm_client.LLMClient`，禁止旁路直调。
- **首跑模式**（``run``）：调用真实模型（可插拔 provider），输出同时落盘为缓存并
  记 ``LLM_CALL`` 事件；判定类输出落 ``LLM_JUDGMENT{decision, model,
  context_digest, frozen=true}``。
- **重放模式**（``replay``）：一律读缓存/日志，**绝不重调 LLM**；``llm_calls`` 恒为 0。
- **嵌入冻结**：嵌入结果按 模型名/版本 + engine_version 缓存，重放不重算。
- **成本闸门**：``LLM_BUDGET`` 降级链 ``T2→T1→T0``，超限记 ``LLM_CALL(degraded=true)``。
- 硬纪律：金额/死亡/结算三类数字绝不交给 LLM；缓存键必须含
  ``engine_version`` 与 ``prompt_hash``。

对外主入口：

    from freeze import LLMClient, FreezeConfig, Mode
    from freeze.client import FreezeLLM, LLMResult   # 窄接口，供 life 层使用
"""

from .canonical import canonical_json, sha256_hex, digest
from .config import (
    FreezeConfig,
    Mode,
    Tier,
    TierDecision,
    Priority,
    ThinkingPolicy,
    ALLOWED_PURPOSES,
    assert_purpose_allowed,
)
from .events import EventLog
from .cache import FrozenStore
from .budget import (
    LLMBudget,
    default_safety_budget,
    DEFAULT_RUN_CALL_LIMIT,
    DEFAULT_ROUND_CALL_LIMIT,
)
from .providers import (
    Provider,
    ProviderResponse,
    MockProvider,
    OpenAICompatProvider,
    OllamaProvider,
    LexicalProvider,
    provider_from_env,
)
from .relevance import RelevanceRanker, cosine, lexical_overlap
from .llm_client import (
    LLMClient,
    LLMResponse,
    FrozenJudgment,
    CacheMissError,
    InvalidDecisionError,
)
from .embedding import EmbeddingFreezer

__all__ = [
    "canonical_json",
    "sha256_hex",
    "digest",
    "FreezeConfig",
    "Mode",
    "Tier",
    "TierDecision",
    "Priority",
    "ThinkingPolicy",
    "ALLOWED_PURPOSES",
    "assert_purpose_allowed",
    "EventLog",
    "FrozenStore",
    "LLMBudget",
    "default_safety_budget",
    "DEFAULT_RUN_CALL_LIMIT",
    "DEFAULT_ROUND_CALL_LIMIT",
    "Provider",
    "ProviderResponse",
    "MockProvider",
    "OpenAICompatProvider",
    "OllamaProvider",
    "LexicalProvider",
    "provider_from_env",
    "RelevanceRanker",
    "cosine",
    "lexical_overlap",
    "LLMClient",
    "LLMResponse",
    "FrozenJudgment",
    "CacheMissError",
    "InvalidDecisionError",
    "EmbeddingFreezer",
]
