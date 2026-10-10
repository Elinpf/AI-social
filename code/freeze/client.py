"""窄接口：供人格生活层（``life/llm.py``）使用的单一入口。

约定（与 life-layer-dev 对齐，已冻结）::

    from freeze.client import FreezeLLM, LLMResult

    freeze = FreezeLLM()                       # 离线默认（MockProvider，无网络）
    freeze = FreezeLLM(client=LLMClient(...))  # 注入真实 provider / 重放模式
    result = freeze.call("plan", "请为明日生成计划……", meta={"agent_id": "a1"})

    # result.text / result.tokens_in / result.tokens_out
    # result.cache_key / result.model / result.degraded

语义：
- 用途白名单 = ``config.ALLOWED_PURPOSES``：
  ``{plan, dialogue, reflect, importance, decide_t2, describe, judge, narrate}``
  （其中 ``dialogue`` 用于 M6 对话正文，属 N 类内容；禁结算类）。
- ``dialogue`` 默认 ``thinking=false``（求快），策略见 ``config.ThinkingPolicy``，并进缓存键。
- 首跑真实调用并落盘缓存；重放/重试命中缓存**零 LLM 调用**。
- ``freeze.llm_calls`` 可断言（重放应为 0）。

无参构造（``FreezeLLM()``）默认使用**离线确定性 MockProvider**，保证骨架
无网络可端到端跑通；可用环境变量覆盖：``FREEZE_MODE``（run/replay）、
``FREEZE_CACHE_DIR``、``FREEZE_ENGINE_VERSION``、``FREEZE_BUDGET``。
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .budget import LLMBudget, default_safety_budget
from .config import FreezeConfig, Mode, Priority, Tier
from .events import EventLog
from .llm_client import LLMClient, LLMResult
from .providers import MockProvider

__all__ = ["FreezeLLM", "LLMResult", "build_default_freeze", "build_default_client"]

DEFAULT_CACHE_DIR = "./freeze_cache"
DEFAULT_ENGINE_VERSION = "v1.1-skeleton"


def build_default_client() -> LLMClient:
    """离线默认客户端：MockProvider + 本地缓存，零网络。

    环境变量（可选）：
      - ``FREEZE_MODE``           run | replay（默认 run）
      - ``FREEZE_CACHE_DIR``      缓存目录（默认 ./freeze_cache）
      - ``FREEZE_ENGINE_VERSION`` engine_version（默认 v1.1-skeleton）
      - ``FREEZE_BUDGET``         预算上限（整数成本单位；缺省不限）
    """
    mode = os.environ.get("FREEZE_MODE", Mode.RUN.value)
    cache_dir = os.environ.get("FREEZE_CACHE_DIR", DEFAULT_CACHE_DIR)
    engine_version = os.environ.get("FREEZE_ENGINE_VERSION", DEFAULT_ENGINE_VERSION)
    budget_raw = os.environ.get("FREEZE_BUDGET")
    # 默认开启安全阀（防跑飞）；可用 FREEZE_BUDGET 覆盖成本单位上限。
    budget = LLMBudget(limit=int(budget_raw)) if budget_raw else default_safety_budget()

    cfg = FreezeConfig(
        engine_version=engine_version,
        mode=Mode(mode),
        cache_dir=cache_dir,
    )
    return LLMClient(
        cfg,
        provider=MockProvider(),
        event_log=EventLog(time_unit=cfg.time_unit),
        budget=budget,
    )


class FreezeLLM:
    """life 层窄接口封装。"""

    def __init__(
        self,
        client: Optional[LLMClient] = None,
        *,
        default_tier: Tier = Tier.T1,
        default_priority: Priority = Priority.NORMAL,
        audit_sink: Optional[Any] = None,
    ) -> None:
        #: 无参构造时使用离线默认客户端（MockProvider，无网络）。
        self.client = client if client is not None else build_default_client()
        if audit_sink is not None:
            # IF-2c 审计桥透传（仅供 orchestration 接线；life 层无需关心）。
            self.client.audit_sink = audit_sink
        #: 供 life 层断言：真实 LLM 调用次数（重放应恒为 0）。
        self.llm_calls = 0
        self.default_tier = default_tier
        self.default_priority = default_priority

    def call(
        self,
        purpose: str,
        prompt: str,
        *,
        model: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        system: str = "",
        tier: Optional[Tier] = None,
        priority: Optional[Priority] = None,
        round: Optional[int] = None,
        thinking: Optional[bool] = None,
    ) -> LLMResult:
        """单一调用入口。

        ``meta``（如 ``{"agent_id":..., "round":..., "slot":...}``）并入落盘事件，
        但**不参与缓存键**（保证同 prompt 可跨调用去重）。

        ``round``：显式传入优先；否则从 ``meta["round"]`` 取（life 层惯例）；
        再否则 0。**注意**：审计事件的 round 必须与内核当前回合一致（否则会污染
        `apply_event` 的 `state.round`）——权威值由 orchestration 的 `audit_sink`
        以 `engine.state.round` 兜底（见 IF-2c）。
        """
        eff_round = round
        if eff_round is None:
            eff_round = int(meta["round"]) if (meta and "round" in meta) else 0
        resp = self.client.complete(
            purpose=purpose,
            system=system,
            user=prompt,
            tier=tier or self.default_tier,
            priority=priority or self.default_priority,
            model=model,
            round=eff_round,
            meta=meta,
            thinking=thinking,
        )
        # 同步计数器便于 life 层断言（仅真实调用递增）。
        self.llm_calls = self.client.llm_calls
        return LLMResult(
            text=resp.text,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cache_key=resp.cache_key,
            model=resp.model,
            degraded=resp.degraded,
        )

    @property
    def cache_key(self) -> str:  # pragma: no cover - 便利访问
        return ""


def build_default_freeze(
    *,
    engine_version: str = DEFAULT_ENGINE_VERSION,
    cache_dir: str = DEFAULT_CACHE_DIR,
    mode: str = "run",
    use_mock: bool = True,
    budget_limit: Optional[int] = None,
) -> FreezeLLM:
    """便捷工厂：离线骨架默认用 MockProvider（无网络）。"""
    if not use_mock:  # pragma: no cover - 真实端点由调用方注入
        raise ValueError("use_mock=False 时请显式构造 LLMClient 并注入 provider")
    cfg = FreezeConfig(
        engine_version=engine_version,
        mode=Mode(mode),
        cache_dir=cache_dir,
    )
    budget = LLMBudget(limit=budget_limit) if budget_limit is not None else default_safety_budget()
    client = LLMClient(
        cfg,
        provider=MockProvider(),
        event_log=EventLog(time_unit=cfg.time_unit),
        budget=budget,
    )
    return FreezeLLM(client)
