"""成本闸门 ``LLM_BUDGET`` 与降级链 ``T2→T1→T0``（对齐 00 §7.2 / 08 §5.5）。

语义：
- 预算以「成本单位」计（``TIER_COST``：T2=3、T1=1、T0=0）。
- 请求档位超出剩余预算时，按 ``T2→T1→T0`` **逐级降级**到第一个可负担档位。
- 优先级 ``CRITICAL``（濒死求生）**绕过预算**，但仍记审计。
- 降级一律记入 ``LLM_CALL`` 载荷的 ``degraded`` 字段。
- T0 不调用 LLM（确定性 fallback），故不计入 ``llm_calls``。

**安全阀（防跑飞，非防花钱）**：除成本单位上限外，另设 **调用计数** 上限——
``call_limit``（单次 run 总调用）与 ``round_call_limit``（单回合调用）。真实 LLM
单次最长可达十几秒、耗时是 rule-based 的数千倍，若忘记限规模（如误跑
N=20 × 12 周），需靠闸门兜底：任一上限触顶即降级到 T0 并记 ``degraded=true``。

预算应按 N 缩放（08 §5.5）；默认安全阀见 :func:`default_safety_budget`。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .config import (
    BYPASS_PRIORITY,
    TIER_COST,
    TIER_ORDER,
    Priority,
    Tier,
    TierDecision,
)

#: 单次 run 的默认总 LLM 调用上限（安全阀，宽松）。覆盖 N=20 × 12 周满配
#: （00 §7.2 估 ≈1×10⁴ 次）仍有 2× 余量。
DEFAULT_RUN_CALL_LIMIT = 20000
#: 单回合默认 LLM 调用上限（安全阀）。N=20 满配约 10–25 次/回合，留足余量。
DEFAULT_ROUND_CALL_LIMIT = 60
#: 大项目可显式关闭（传 None）；默认建议开启。
DEFAULT_COST_UNIT_LIMIT: Optional[int] = None


class LLMBudget:
    """可审计的 LLM 预算闸门（成本单位 + 调用计数双重安全阀）。"""

    def __init__(
        self,
        limit: Optional[int] = None,
        costs: Optional[Dict[Tier, int]] = None,
        *,
        call_limit: Optional[int] = None,
        round_call_limit: Optional[int] = None,
    ) -> None:
        #: 成本单位上限。None 表示不限。
        self.limit = limit
        self.costs = dict(costs or TIER_COST)
        #: 单次 run 总调用上限（安全阀）。None 表示不限。
        self.call_limit = call_limit
        #: 单回合调用上限（安全阀）。None 表示不限。
        self.round_call_limit = round_call_limit
        self.spent = 0
        #: 已发生的真实 LLM 调用数（T0 兜底不计入）。
        self.calls = 0
        self._round_calls: Dict[int, int] = {}
        self.degraded_count = 0

    # ------------------------------------------------------------------ #
    def remaining(self) -> Optional[int]:
        if self.limit is None:
            return None
        return max(self.limit - self.spent, 0)

    def can_afford(self, tier: Tier) -> bool:
        rem = self.remaining()
        if rem is None:
            return True
        return self.costs.get(tier, 0) <= rem

    # ------------------------------------------------------------------ #
    def _cap_exceeded(self, round_no: Optional[int]) -> Optional[str]:
        """返回触顶原因（None 表示未触顶）。"""
        if self.call_limit is not None and self.calls >= self.call_limit:
            return f"run_call_limit({self.call_limit})_reached"
        if (round_no is not None and self.round_call_limit is not None
                and self._round_calls.get(round_no, 0) >= self.round_call_limit):
            return f"round_call_limit({self.round_call_limit})_reached@r{round_no}"
        return None

    def resolve(
        self,
        requested: Tier,
        priority: Priority = Priority.NORMAL,
        *,
        round_no: Optional[int] = None,
    ) -> TierDecision:
        """裁决实际执行档位。

        - ``CRITICAL`` 优先级：不降级（绕过所有闸门）。
        - 计数安全阀触顶：降到 ``T0``（确定性兜底，零 LLM 调用）。
        - 成本单位不足：从请求档位沿降级链找到第一个可负担档位。
        """
        if priority in BYPASS_PRIORITY:
            return TierDecision(requested, False, reason="critical_bypass")

        cap = self._cap_exceeded(round_no)
        if cap is not None:
            self.degraded_count += 1
            return TierDecision(Tier.T0, True, reason=cap)

        if self.limit is None:
            return TierDecision(requested, False, reason="no_budget_limit")

        start = TIER_ORDER.index(requested)
        for tier in TIER_ORDER[start:]:
            if self.can_afford(tier):
                degraded = tier != requested
                reason = "ok" if not degraded else f"degraded_{requested.value}_to_{tier.value}"
                if degraded:
                    self.degraded_count += 1
                return TierDecision(tier, degraded, reason=reason)

        # 理论上 T0 成本为 0，必可负担；兜底返回 T0。
        self.degraded_count += 1
        return TierDecision(Tier.T0, True, reason="exhausted_to_T0")

    # ------------------------------------------------------------------ #
    def charge(self, tier: Tier, *, round_no: Optional[int] = None) -> None:
        """按实际执行档位扣减预算并登记计数（仅真实调用会调用本方法）。"""
        self.spent += self.costs.get(tier, 0)
        self.calls += 1
        if round_no is not None:
            self._round_calls[round_no] = self._round_calls.get(round_no, 0) + 1

    def snapshot(self) -> Dict[str, Optional[int]]:
        return {
            "limit": self.limit,
            "spent": self.spent,
            "remaining": self.remaining(),
            "call_limit": self.call_limit,
            "round_call_limit": self.round_call_limit,
            "calls": self.calls,
            "degraded_count": self.degraded_count,
        }


def default_safety_budget(
    n_agents: int = 20,
    *,
    weeks: int = 12,
    headroom: float = 2.0,
) -> LLMBudget:
    """构造带**安全阀**的默认预算（防跑飞）。

    默认值（明确、可查）：
    - ``call_limit``：``DEFAULT_RUN_CALL_LIMIT``（20000）——覆盖 N=20 × 12 周满配。
    - ``round_call_limit``：``DEFAULT_ROUND_CALL_LIMIT``（60）。
    - 成本单位上限默认不限（不计费则无需成本闸；开启时传 ``limit``）。

    超限行为：沿 ``T2→T1→T0`` 降级，触顶记 ``LLM_CALL(degraded=true)``；
    优先级 ``CRITICAL``（濒死求生）可绕过。
    """
    return LLMBudget(
        limit=DEFAULT_COST_UNIT_LIMIT,
        call_limit=DEFAULT_RUN_CALL_LIMIT,
        round_call_limit=DEFAULT_ROUND_CALL_LIMIT,
    )
