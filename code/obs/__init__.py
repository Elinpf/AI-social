"""L2 涌现观测层（emergence observation layer）。

契约（IF-4 / 07 §0.1 / 08 §4）：
    metrics(log, T, TIME_CONFIG) = f(EventLog, turn_seal, TIME_CONFIG)
只读、纯函数、逐位一致；计算过程 `llm_calls == 0`。

分级（07 §0.3）：
  - **D** 纯确定性指标 → `metrics.emergence` / `metrics.life`（判定主力）；
  - **F** 含 LLM 冻结判定 → `metrics.emergence_soft` / `metrics.wellbeing_soft`
    （仅敏感性，不进判定/门禁）；
  - **K** 硬内核指标 → `metrics.econ` / `metrics.lifecycle`（口径冻结，不接 LLM）。

依赖白名单（v1.2 §1.3）：仅 `engine.canon` / `engine.ledger` / `engine.events` /
`engine.time`（纯函数、只读）；**禁止** import 写路径（state/replay/arbiter/hooks）。
"""

from __future__ import annotations

from .reader import ReadOnlyLog
from .params import (
    ObsParams, EmergenceParams, WellbeingParams, AntiFraudParams, DEFAULT_PARAMS,
)
from .report import (
    metrics, emergence_report, wellbeing_report, census_report, to_canonical,
    SCHEMA_VERSION,
)
from .census import semantic_census, soft_judgment_counts, SEMANTIC_EVENT_ORDER
from .atomic import atomic_freq, coverage, preflight, CensusError
from .runtime import llm_calls, note_llm_call, reset_llm_calls, LlmCallGuard
from . import antifraud, gate, golden

__all__ = [
    "ReadOnlyLog",
    "ObsParams", "EmergenceParams", "WellbeingParams", "AntiFraudParams", "DEFAULT_PARAMS",
    "metrics", "emergence_report", "wellbeing_report", "census_report", "to_canonical",
    "SCHEMA_VERSION",
    "semantic_census", "soft_judgment_counts", "SEMANTIC_EVENT_ORDER",
    "atomic_freq", "coverage", "preflight", "CensusError",
    "llm_calls", "note_llm_call", "reset_llm_calls", "LlmCallGuard",
    "antifraud", "gate", "golden",
]
