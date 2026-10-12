"""冻结层配置：运行模式、执行档位、优先级、用途白名单。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .capture import CaptureConfig


class Mode(str, Enum):
    """运行模式。"""

    RUN = "run"        # 首跑：允许真实调用并落盘冻结
    REPLAY = "replay"  # 重放：只读缓存/日志，绝不重调 LLM


class Tier(str, Enum):
    """决策分层档位（对齐 00 §1.1 / §7.2 的 T0/T1/T2）。

    - ``T2``：完整 LLM（关键事件，最强模型）
    - ``T1``：小模型 / 常规调用
    - ``T0``：规则兜底（**不调用 LLM**，确定性 fallback）
    """

    T2 = "T2"
    T1 = "T1"
    T0 = "T0"


#: 降级链顺序（从强到弱）。成本闸门按此顺序逐级降级。
TIER_ORDER: List[Tier] = [Tier.T2, Tier.T1, Tier.T0]

#: 各档位消耗的预算单位（T0 不耗 LLM 预算）。
TIER_COST: Dict[Tier, int] = {Tier.T2: 3, Tier.T1: 1, Tier.T0: 0}


class Priority(str, Enum):
    """调用优先级（对齐 00 §7.2：濒死 > 投资/结盟 > 常规）。"""

    CRITICAL = "critical"      # 濒死求生——可绕过预算
    INVESTMENT = "investment"  # 投资 / 结盟
    NORMAL = "normal"          # 常规


PRIORITY_RANK: Dict[Priority, int] = {
    Priority.CRITICAL: 3,
    Priority.INVESTMENT: 2,
    Priority.NORMAL: 1,
}

#: 这些优先级可绕过预算闸门（仍记 degraded 审计，但不降级）。
BYPASS_PRIORITY = {Priority.CRITICAL}


@dataclass
class TierDecision:
    """成本闸门的裁决结果。"""

    tier: Tier
    degraded: bool
    reason: str = ""


# --------------------------------------------------------------------------- #
# 用途白名单（硬纪律：金额 / 死亡 / 结算三类数字绝不交给 LLM）
# --------------------------------------------------------------------------- #

#: 允许交由 LLM 的用途（内容与定性判断类，对齐 00 §5.2 N-1..N-8）。
ALLOWED_PURPOSES = {
    "plan",         # 日/周计划内容
    "dialogue",     # 对话正文
    "negotiation",  # 议价/条款内容（T132：只产内容/条款，不判可行性、不写账）
    "reflect",      # 反思文本
    "importance",   # 记忆重要性（定性打分，非结算）
    "decide_t2",    # T2 决策内容/意图
    "describe",     # 描述性文字（涌现/叙事）
    "judge",        # 软判定层定性判断（IF-2b）
    "narrate",      # 叙事层纯输出（IF-7）
}

#: 明令禁止的用途（命中即拒绝）：金额 / 死亡 / 结算三类数字。
FORBIDDEN_PURPOSES = {
    "settle",
    "settlement",
    "settle_market",
    "settle_obligations",
    "apply_tax",
    "apply_metabolism",
    "apply_penalty",
    "check_lifecycle",
    "check_death",
    "resolve_revival",
    "money",
    "mint",
    "burn",
    "transfer_amount",
    "death_judgment",
    "currency",
}


def assert_purpose_allowed(purpose: str) -> None:
    """校验用途：禁止结算类，且必须在白名单内。

    这是「金额/死亡/结算三类数字绝不交给 LLM」的**入口级硬拦截**。
    """
    if purpose in FORBIDDEN_PURPOSES:
        raise ValueError(
            f"用途 {purpose!r} 属金额/死亡/结算类，硬纪律禁止交给 LLM"
        )
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError(
            f"未知用途 {purpose!r}；白名单：{sorted(ALLOWED_PURPOSES)}"
        )


@dataclass
class ThinkingPolicy:
    """`chat_template_kwargs.thinking` 的**集中式**策略（用户明确要求）。

    分层原则（**不散落硬编码**）：
    - ``thinking=false``（更快）——AI 居民的**常规决策与对话**（T1 常规协商、
      回信、标准报价、计划/反思/重要性等）。
    - ``thinking=true``（更高质量）——**世界侧/高质量判断**：软判定层
      （``judge``）、叙事层（``narrate``/``describe``），以及 **T2 重大战略决策**
      （投资/结盟/濒死求生）。

    默认值写入 config，并通过 :meth:`fingerprint` 纳入 ``engine_version`` 指纹。
    """

    default: bool = False
    #: 无论 tier 一律开启 thinking 的用途（软判定 / 叙事层）。
    true_purposes: frozenset = frozenset({"judge", "narrate", "describe"})
    #: 一律开启 thinking 的档位（T2 重大战略决策）。
    true_tiers: frozenset = frozenset({Tier.T2.value})

    def resolve(self, purpose: str, tier: "Tier") -> bool:
        tier_val = tier.value if isinstance(tier, Tier) else str(tier)
        if purpose in self.true_purposes:
            return True
        if tier_val in self.true_tiers:
            return True
        return self.default

    def fingerprint(self) -> Dict[str, object]:
        return {
            "default": self.default,
            "true_purposes": sorted(self.true_purposes),
            "true_tiers": sorted(self.true_tiers),
        }


@dataclass
class FreezeConfig:
    """冻结层配置。

    缓存键必含 ``engine_version`` 与 ``prompt_hash``（后者由 prompt 内容派生）。
    ``engine_version`` 应聚合时间结构、拓扑、嵌入模型版本等复现输入指纹
    （对齐 00 §5.3 AR-C5 / 08 §5.6）。
    """

    engine_version: str
    mode: Mode = Mode.RUN
    cache_dir: str = "./freeze_cache"
    #: 逻辑时间单位：mono_ts = round * time_unit + phase_seq（非墙钟）。
    time_unit: int = 1000
    #: 缓存键 schema 版本，升级缓存结构时递增以隔离旧缓存。
    cache_schema: str = "freeze-v1"
    #: thinking 控制策略（按 purpose/tier 集中裁决，不散落硬编码）。
    thinking_policy: ThinkingPolicy = field(default_factory=ThinkingPolicy)
    #: prompt 正文落盘（T227；默认关；配置进 engine_version 指纹）。
    capture: "CaptureConfig" = field(default_factory=lambda: CaptureConfig())

    def __post_init__(self) -> None:
        if isinstance(self.mode, str):
            self.mode = Mode(self.mode)
        if not self.engine_version:
            raise ValueError("engine_version 不能为空：缓存可复现依赖它")

    def thinking_flag(self, purpose: str, tier: "Tier") -> bool:
        """按集中策略裁决某次调用是否开启 thinking。"""
        return self.thinking_policy.resolve(purpose, tier)

    def engine_version_with_policy(self) -> str:
        """把 thinking 策略与 prompt 落盘配置指纹折进 engine_version（复现口径）。"""
        from .canonical import digest

        return (
            f"{self.engine_version}"
            f"|thinking={digest(self.thinking_policy.fingerprint())[:16]}"
            f"|capture={digest(self.capture.fingerprint())[:16]}"
        )

    @property
    def is_replay(self) -> bool:
        return self.mode == Mode.REPLAY

    @property
    def is_run(self) -> bool:
        return self.mode == Mode.RUN
