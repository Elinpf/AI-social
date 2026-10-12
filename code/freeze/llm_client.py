"""统一 LLM 调用入口——冻结层的核心（对齐 00 §4.6/§5.5、08 §1.2）。

**所有 LLM 调用必经此处，禁止旁路直调。**

三种高层能力：

- :meth:`LLMClient.complete` —— 通用补全（首跑真实调用并落盘冻结；重放只读缓存）。
- :meth:`LLMClient.judge` —— 软判定层（IF-2b）：RNG 分支给定后做**定性判断**，
  结果冻结为 ``LLM_JUDGMENT``（必带四要素）；重放走 :meth:`get_frozen_judgment`
  （IF-6）**绝不重问 LLM**。
- :meth:`LLMClient.narrate` —— 叙事层（IF-7）：把已定事实叙述为文本，记
  ``NARRATIVE{affects_state=false}``，不改状态。

计价与判定**分列**：每次真实/缓存 LLM 调用记 ``LLM_CALL``，判定另记
``LLM_JUDGMENT``。

用法::

    cfg = FreezeConfig(engine_version="v1.1+abc", mode=Mode.RUN, cache_dir="...")
    client = LLMClient(cfg, provider=MockProvider(), event_log=EventLog(),
                       budget=LLMBudget(limit=100))
    r = client.complete(purpose="plan", system="...", user="...")
    assert client.llm_calls == 1
    # 重放
    cfg2 = replace(cfg, mode=Mode.REPLAY)
    client2 = LLMClient(cfg2, provider=MockProvider(), event_log=EventLog())
    r2 = client2.complete(purpose="plan", system="...", user="...")  # 命中缓存
    assert client2.llm_calls == 0
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .budget import LLMBudget
from .cache import FrozenStore
from .canonical import canonical_json, digest
from .config import (
    FreezeConfig,
    Mode,
    Priority,
    Tier,
    TierDecision,
    assert_purpose_allowed,
)
from .embedding import EmbeddingFreezer
from .events import (
    EventLog,
    llm_call_payload,
    llm_judgment_payload,
    narrative_payload,
)
from .providers import Provider


class CacheMissError(RuntimeError):
    """重放模式下缓存未命中——绝不回退到真实调用。"""


class InvalidDecisionError(ValueError):
    """判定结果不在 ``envelope.options`` 内。"""


@dataclass
class LLMResponse:
    """通用补全结果（内部规范化形式）。"""

    text: str
    model: str
    prompt_hash: str
    cache_key: str
    cached: bool
    tier: str
    degraded: bool
    tokens_in: int = 0
    tokens_out: int = 0
    provider: str = ""
    #: 可空：判别式路径的 `choices[0].logprobs`（用于取候选分差 margin）。
    logprobs: Optional[Dict[str, Any]] = None


@dataclass
class FrozenJudgment:
    """冻结判定（IF-6 读回结果）。"""

    judgment_id: str
    decision: Any
    model: str
    context_digest: str
    frozen: bool
    prompt_hash: str
    parties: List[str]
    dimension: str
    question_ref: str
    envelope: Dict[str, Any]
    effect_ref: Optional[int] = None
    #: 可空：判别式路径的候选分差（top1−top2）与标签概率分布。
    margin: Optional[float] = None
    label_probs: Optional[Dict[str, float]] = None
    event: Optional[Dict[str, Any]] = None


# --------------------------------------------------------------------------- #
# 窄接口（供 life 层使用；字段与 life-layer-dev 约定一致）
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class LLMResult:
    """life 层窄接口返回结构（字段与 life-layer-dev 约定一致）。"""

    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    cache_key: str = ""
    model: str = ""
    degraded: bool = False


class LLMClient:
    """冻结层统一调用入口。"""

    def __init__(
        self,
        config: FreezeConfig,
        *,
        provider: Provider,
        event_log: Optional[EventLog] = None,
        budget: Optional[LLMBudget] = None,
        store: Optional[FrozenStore] = None,
        fallback: Optional[Any] = None,
        embed_provider: Optional[Any] = None,
        embed_model: Optional[str] = None,
        embed_version: str = "v1",
        audit_sink: Optional[Callable[[str, Dict[str, Any], int, int], None]] = None,
    ) -> None:
        self.config = config
        self.provider = provider
        self.event_log = event_log if event_log is not None else EventLog(
            time_unit=config.time_unit
        )
        self.budget = budget
        self.store = store or FrozenStore(config.cache_dir)
        #: T0 兜底：确定性函数 (purpose, system, user, params) -> str；缺省返回空串。
        self.fallback = fallback
        #: IF-2c 审计桥（可选）：把 LLM_CALL/LLM_JUDGMENT/NARRATIVE 的 payload 回流内核账本。
        #: 签名 ``audit_sink(kind, payload, round, phase)``；**仅 run 模式回调，replay 不回调**。
        #: 由 orchestration 侧接线到 ``engine.emit_specs([spec(...)])``（Arbiter 仍唯一写入者）。
        self.audit_sink = audit_sink

        #: 计数：真实 provider 调用次数（重放应为 0）。
        self.llm_calls = 0

        self.embedder = EmbeddingFreezer(
            store=self.store,
            provider=embed_provider or provider,
            engine_version=config.engine_version,
            mode=config.mode,
            model=embed_model,
            version=embed_version,
        )

        # T227：可选 prompt 正文落盘（默认关；四控见 freeze.capture）。
        from .capture import PromptCapture

        cap_cfg = config.capture
        cap_root = cap_cfg.dir or str(Path(config.cache_dir) / "prompts")
        redact_terms: List[str] = []
        for _env in ("LLM_API_KEY", "VISION_API_KEY", "FREEZE_LLM_API_KEY", "OPENAI_API_KEY"):
            _v = os.environ.get(_env)
            if _v:
                redact_terms.append(_v)
        _base = getattr(provider, "base_url", None)
        if _base:
            redact_terms.append(_base)
        self.capture = PromptCapture(cap_cfg, root=cap_root, redact_terms=redact_terms)

    def _maybe_capture(self, *, purpose: str, system: str, user: str, cache_key: str,
                       prompt_hash: str, output: str, model: str, thinking: bool,
                       tier: str, round: int, phase: int, cached: bool) -> None:
        cap = getattr(self, "capture", None)
        if cap is None or not cap.is_active():
            return
        if not cap.should_capture(purpose, sample_key=cache_key):
            cap.skipped += 1
            return
        cap.write({
            "purpose": purpose, "cache_key": cache_key, "prompt_hash": prompt_hash,
            "system": system, "user": user, "output": output, "model": model,
            "thinking": thinking, "tier": tier, "round": round, "phase": phase,
            "cached": cached, "engine_version": self.config.engine_version,
        })

    # ------------------------------------------------------------------ #
    @property
    def embed_calls(self) -> int:
        return self.embedder.embed_calls

    @property
    def is_replay(self) -> bool:
        return self.config.mode == Mode.REPLAY

    # ------------------------------------------------------------------ #
    def _prompt_hash(
        self,
        system: str,
        user: str,
        params: Dict[str, Any],
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """规范 prompt 哈希（含 system/user/消息/采样参数）。"""
        return digest(
            {
                "system": system,
                "user": user,
                "messages": messages or [],
                "params": params,
            }
        )

    def make_cache_key(
        self,
        prompt_hash: str,
        *,
        kind: str,
        model: str,
        tier: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """缓存键——**必含 ``engine_version`` 与 ``prompt_hash``**（硬纪律）。"""
        return digest(
            {
                "cache_schema": self.config.cache_schema,
                "kind": kind,
                "engine_version": self.config.engine_version,
                "prompt_hash": prompt_hash,
                "model": model,
                "tier": tier,
                "params": params or {},
            }
        )

    # ------------------------------------------------------------------ #
    def _resolve_model(self, model: Optional[str], tier: Tier) -> str:
        if model:
            return model
        mbt = getattr(self.provider, "model_by_tier", None) or {}
        return mbt.get(tier.value) or getattr(self.provider, "model", "unknown")

    # ------------------------------------------------------------------ #
    def complete(
        self,
        *,
        purpose: str,
        system: str = "",
        user: str = "",
        tier: Tier = Tier.T2,
        priority: Priority = Priority.NORMAL,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        response_format: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        round: int = 0,
        phase: int = 2,
        meta: Optional[Dict[str, Any]] = None,
        thinking: Optional[bool] = None,
        options: Optional[List[str]] = None,
        logprobs: bool = False,
        top_logprobs: Optional[int] = None,
    ) -> LLMResponse:
        """统一补全入口（首跑落盘 / 重放零调用）。"""
        assert_purpose_allowed(purpose)
        tier = Tier(tier) if isinstance(tier, str) else tier
        priority = Priority(priority) if isinstance(priority, str) else priority

        # thinking 策略：显式传入优先，否则按集中策略（config.thinking_policy）裁决。
        eff_thinking = (
            thinking if thinking is not None
            else self.config.thinking_flag(purpose, tier)
        )

        params: Dict[str, Any] = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format,
            "thinking": eff_thinking,
            "logprobs": bool(logprobs),
            "top_logprobs": top_logprobs,
        }
        prompt_hash = self._prompt_hash(system, user, params, messages)
        requested_model = self._resolve_model(model, tier)
        cache_key = self.make_cache_key(
            prompt_hash,
            kind=purpose,
            model=requested_model,
            tier=tier.value,
            params=params,
        )

        # ---- 缓存命中：首跑与重放共用（命中不重复计费） ---- #
        hit = self.store.get_response(cache_key)
        if hit is not None:
            self._emit_call(
                purpose=purpose,
                model=hit["model"],
                prompt_hash=prompt_hash,
                cache_key=cache_key,
                tier=hit.get("tier", tier.value),
                priority=priority.value,
                degraded=hit.get("degraded", False),
                cached=True,
                tokens_in=0,
                tokens_out=0,
                cost_units=0,
                round=round,
                phase=phase,
                meta=meta,
                thinking=hit.get("thinking", eff_thinking),
            )
            self._maybe_capture(purpose=purpose, system=system, user=user, cache_key=cache_key,
                                prompt_hash=prompt_hash, output=hit["text"], model=hit["model"],
                                thinking=bool(hit.get("thinking", eff_thinking)),
                                tier=hit.get("tier", tier.value), round=round, phase=phase, cached=True)
            return LLMResponse(
                text=hit["text"],
                model=hit["model"],
                prompt_hash=prompt_hash,
                cache_key=cache_key,
                cached=True,
                tier=hit.get("tier", tier.value),
                degraded=hit.get("degraded", False),
                tokens_in=hit.get("tokens_in", 0),
                tokens_out=hit.get("tokens_out", 0),
                provider=hit.get("provider", ""),
                logprobs=hit.get("logprobs"),
            )

        # ---- 未命中：重放模式一律报错，绝不回退真实调用 ---- #
        if self.is_replay:
            raise CacheMissError(
                f"重放模式缓存未命中（禁止真实调用）：purpose={purpose} key={cache_key}"
            )

        # ---- 成本闸门与降级链 ---- #
        decision: TierDecision
        if self.budget is not None:
            decision = self.budget.resolve(tier, priority, round_no=round)
        else:
            decision = TierDecision(tier, False, reason="no_budget")
        eff_tier = decision.tier

        # ---- T0：确定性兜底，不调用 LLM ---- #
        if eff_tier == Tier.T0:
            text = self._run_fallback(purpose, system, user, params)
            record = {
                "text": text,
                "model": f"T0:{self.provider.name}",
                "provider": "none",
                "prompt_hash": prompt_hash,
                "cache_key": cache_key,
                "tier": Tier.T0.value,
                "degraded": True,
                "tokens_in": 0,
                "tokens_out": 0,
                "thinking": eff_thinking,
            }
            self.store.put_response(cache_key, record)
            self._emit_call(
                purpose=purpose,
                model=record["model"],
                prompt_hash=prompt_hash,
                cache_key=cache_key,
                tier=Tier.T0.value,
                priority=priority.value,
                degraded=True,
                cached=False,
                tokens_in=0,
                tokens_out=0,
                cost_units=0,
                round=round,
                phase=phase,
                meta=meta,
                thinking=eff_thinking,
            )
            return LLMResponse(
                text=text,
                model=record["model"],
                prompt_hash=prompt_hash,
                cache_key=cache_key,
                cached=False,
                tier=Tier.T0.value,
                degraded=True,
                provider="none",
            )

        # ---- 真实调用（仅 run 模式可到达） ---- #
        eff_model = self._resolve_model(model, eff_tier)
        resp = self.provider.complete(
            system=system,
            user=user,
            model=eff_model,
            temperature=temperature,
            max_tokens=max_tokens,
            tier=eff_tier.value,
            extra={"purpose": purpose, "response_format": response_format,
                   "thinking": eff_thinking, "options": options,
                   "logprobs": bool(logprobs), "top_logprobs": top_logprobs},
        )
        self.llm_calls += 1
        if self.budget is not None:
            self.budget.charge(eff_tier, round_no=round)

        record = {
            "text": resp.text,
            "model": resp.model,
            "provider": getattr(self.provider, "name", ""),
            "prompt_hash": prompt_hash,
            "cache_key": cache_key,
            "tier": eff_tier.value,
            "degraded": decision.degraded,
            "tokens_in": resp.tokens_in,
            "tokens_out": resp.tokens_out,
            "thinking": eff_thinking,
            "logprobs": getattr(resp, "logprobs", None),
        }
        self.store.put_response(cache_key, record)
        self._emit_call(
            purpose=purpose,
            model=resp.model,
            prompt_hash=prompt_hash,
            cache_key=cache_key,
            tier=eff_tier.value,
            priority=priority.value,
            degraded=decision.degraded,
            cached=False,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_units=self.budget.costs.get(eff_tier, 0) if self.budget else 0,
            round=round,
            phase=phase,
            meta=meta,
            thinking=eff_thinking,
        )
        self._maybe_capture(purpose=purpose, system=system, user=user, cache_key=cache_key,
                            prompt_hash=prompt_hash, output=resp.text, model=resp.model,
                            thinking=bool(eff_thinking), tier=eff_tier.value, round=round,
                            phase=phase, cached=False)
        return LLMResponse(
            text=resp.text,
            model=resp.model,
            prompt_hash=prompt_hash,
            cache_key=cache_key,
            cached=False,
            tier=eff_tier.value,
            degraded=decision.degraded,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            provider=getattr(self.provider, "name", ""),
            logprobs=getattr(resp, "logprobs", None),
        )

    # ------------------------------------------------------------------ #
    def _run_fallback(self, purpose: str, system: str, user: str, params: Dict[str, Any]) -> str:
        if self.fallback is None:
            return ""
        return self.fallback(purpose=purpose, system=system, user=user, params=params)

    def _emit_audit(self, kind: str, payload: Dict[str, Any], round: int, phase: int) -> None:
        """IF-2c：把事件 payload 回流内核账本（经 orchestration 接线的 audit_sink）。

        **仅 run（非 replay）回调**——重放绝不回灌，否则会重复提交。freeze 不 import 内核，
        只回调；Arbiter 仍为唯一写入者（ADR-08：回滚时随本回合缓冲丢弃）。
        """
        if self.audit_sink is not None and not self.is_replay:
            self.audit_sink(kind, dict(payload), int(round), int(phase))

    def _emit_call(
        self,
        *,
        purpose: str,
        model: str,
        prompt_hash: str,
        cache_key: str,
        tier: str,
        priority: str,
        degraded: bool,
        cached: bool,
        tokens_in: int,
        tokens_out: int,
        cost_units: int,
        round: int,
        phase: int,
        meta: Optional[Dict[str, Any]],
        thinking: Optional[bool] = None,
    ) -> Dict[str, Any]:
        extra: Dict[str, Any] = {}
        if meta:
            extra["meta_digest"] = digest(meta)
        if thinking is not None:
            extra["thinking"] = bool(thinking)
        payload = llm_call_payload(
            purpose=purpose,
            model=model,
            engine_version=self.config.engine_version,
            prompt_hash=prompt_hash,
            cache_key=cache_key,
            tier=tier,
            priority=priority,
            degraded=degraded,
            cached=cached,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_units=cost_units,
            provider=getattr(self.provider, "name", ""),
            phase=phase,
            extra=extra,
        )
        event = self.event_log.append("LLM_CALL", payload, round=round, phase=phase)
        self._emit_audit("LLM_CALL", payload, round, phase)
        return event

    # ================================================================== #
    # 软判定层 IF-2b → IF-6
    # ================================================================== #
    def judge(
        self,
        *,
        judgment_id: str,
        dimension: str,
        question_ref: str,
        envelope: Dict[str, Any],
        context: Dict[str, Any],
        rng_branch: Any = None,
        parties: Optional[List[str]] = None,
        created_round: int = 0,
        phase: int = 2,
        tier: Tier = Tier.T2,
        priority: Priority = Priority.NORMAL,
        model: Optional[str] = None,
        context_ref: Optional[str] = None,
        effect_ref: Optional[int] = None,
        round: Optional[int] = None,
    ) -> FrozenJudgment:
        """软判定层出口（IF-2b）。

        硬内核先在 ``envelope`` 内给定约束（options/threshold/rng_branch），
        软判定层做**定性判断**，硬内核校验后**冻结**为 ``LLM_JUDGMENT``。

        冻结判定**必带四要素**：decision / model / context_digest / frozen=true。
        重放模式直接读回已冻结判定，**绝不重问 LLM**。
        """
        round = created_round if round is None else round
        # 重放：读冻结判定（IF-6），零 LLM 调用。
        if self.is_replay:
            return self.get_frozen_judgment(judgment_id)

        parties = list(parties or [])
        context_digest = digest(context)
        system = (
            "你是社会仿真中的【软判定层】。只做定性社会判断，"
            "不产出任何金额/死亡/结算数字；结果必须严格选自给定选项。"
        )
        user = canonical_json(
            {
                "question_ref": question_ref,
                "dimension": dimension,
                "parties": parties,
                "envelope": envelope,
                "rng_branch": rng_branch,
                "context": context,
            }
        )
        resp = self.complete(
            purpose="judge",
            system=system,
            user=user,
            tier=tier,
            priority=priority,
            model=model,
            round=round,
            phase=phase,
            meta={"judgment_id": judgment_id, "dimension": dimension},
            options=list(envelope.get("options")) if envelope.get("options") else None,
        )
        decision: Any = self._normalize_decision(resp.text, envelope.get("options"))

        options = envelope.get("options")
        if options is not None and decision not in options:
            self.event_log.append(
                "SYSTEM_ERROR",
                {
                    "kind": "invalid_judgment_decision",
                    "judgment_id": judgment_id,
                    "decision": decision,
                    "options": options,
                },
                round=round,
                phase=phase,
            )
            raise InvalidDecisionError(
                f"判定 {decision!r} 不在 envelope.options={options} 内"
            )

        payload = llm_judgment_payload(
            judgment_id=judgment_id,
            decision=decision,
            model=resp.model,
            context_digest=context_digest,
            prompt_hash=resp.prompt_hash,
            envelope=envelope,
            rng_branch=rng_branch,
            parties=parties,
            dimension=dimension,
            question_ref=question_ref,
            created_round=created_round,
            context_ref=context_ref,
            effect_ref=effect_ref,
            frozen=True,
        )
        event = self.event_log.append(
            "LLM_JUDGMENT",
            payload,
            actor=parties[0] if parties else "SYSTEM",
            round=round,
            phase=phase,
        )
        record = dict(payload)
        record["cache_key"] = resp.cache_key
        record["seq"] = event["seq"]
        self.store.put_judgment(judgment_id, record)
        self._emit_audit("LLM_JUDGMENT", payload, round, phase)

        return FrozenJudgment(
            judgment_id=judgment_id,
            decision=decision,
            model=resp.model,
            context_digest=context_digest,
            frozen=True,
            prompt_hash=resp.prompt_hash,
            parties=parties,
            dimension=dimension,
            question_ref=question_ref,
            envelope=envelope,
            effect_ref=effect_ref,
            event=event,
        )

    @staticmethod
    def _option_probs(logprobs: Optional[Dict[str, Any]], options: List[str]) -> Optional[Dict[str, float]]:
        """从 provider 的 `choices[0].logprobs` 取候选标签的概率分布（归一化到 options）。"""
        if not logprobs or not isinstance(logprobs, dict):
            return None
        content = logprobs.get("content")
        if not content:
            return None

        def _norm(s: Any) -> str:
            return re.sub(r"[^a-z0-9]", "", str(s).lower())

        for tok in content:
            probs: Dict[str, float] = {}
            nv = _norm(tok.get("token"))
            for o in options:
                if nv == _norm(o) and tok.get("logprob") is not None:
                    probs[o] = math.exp(float(tok["logprob"]))
            for t in (tok.get("top_logprobs") or []):
                for o in options:
                    if _norm(t.get("token")) == _norm(o) and t.get("logprob") is not None:
                        probs[o] = max(probs.get(o, 0.0), math.exp(float(t["logprob"])))
            if probs:
                tot = sum(probs.values()) or 1.0
                return {o: probs[o] / tot for o in probs}
        return None

    def judge_discriminative(
        self,
        *,
        judgment_id: str,
        dimension: str,
        question_ref: str,
        envelope: Dict[str, Any],
        context: Dict[str, Any],
        rng_branch: Any = None,
        parties: Optional[List[str]] = None,
        created_round: int = 0,
        phase: int = 2,
        round: Optional[int] = None,
        model: Optional[str] = None,
        context_ref: Optional[str] = None,
        effect_ref: Optional[int] = None,
        top_logprobs: Optional[int] = None,
        method: Optional[str] = None,
    ) -> FrozenJudgment:
        """**判别式软判定**（受限选择 + `thinking=false`，T222 的 provider 支撑路径）。

        与 :meth:`judge` 对齐的签名；差异：
        - 强制 `response_format=json_schema(enum=envelope.options)`，即**受限选择**；
        - `thinking=false`（求快；端点判别式路径 `reasoning=0`）；
        - 请求 `logprobs`，回传 **`margin`（top1−top2）** 与可选 `label_probs`；
        - `LLM_JUDGMENT` **四要素只增不改**，另加可选 `confidence`/`margin`（+ 调用方传入的 `method`）；
        - **非法/拒答/解析失败 → 抛 `InvalidDecisionError`**（不吞；交调用方回退）。
        重放模式直接读冻结判定（IF-6），**零 LLM 调用**。
        """
        round = created_round if round is None else round
        if self.is_replay:
            return self.get_frozen_judgment(judgment_id)

        parties = list(parties or [])
        options = list(envelope.get("options") or [])
        if not options:
            raise ValueError("judge_discriminative 需要 envelope.options（受限候选）")
        context_digest = digest(context)
        system = (
            "你是社会仿真中的【软判定层】。只做定性社会判断，只输出一个标签，"
            "必须严格选自给定选项，不产出任何金额/死亡/结算数字。"
        )
        user = canonical_json(
            {
                "question_ref": question_ref,
                "dimension": dimension,
                "parties": parties,
                "envelope": envelope,
                "rng_branch": rng_branch,
                "context": context,
            }
        )
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "judgment",
                "schema": {
                    "type": "object",
                    "properties": {"label": {"type": "string", "enum": options}},
                    "required": ["label"],
                    "additionalProperties": False,
                },
            },
        }
        k = top_logprobs if top_logprobs is not None else max(2, min(len(options), 8))
        resp = self.complete(
            purpose="judge",
            system=system,
            user=user,
            tier=Tier.T1,
            thinking=False,
            response_format=schema,
            options=options,
            logprobs=True,
            top_logprobs=k,
            model=model,
            round=round,
            phase=phase,
            meta={"judgment_id": judgment_id, "dimension": dimension, "method": method or "discriminative"},
        )
        decision = self._normalize_decision(resp.text, options)
        if decision not in options:
            self.event_log.append(
                "SYSTEM_ERROR",
                {"kind": "invalid_judgment_decision", "judgment_id": judgment_id,
                 "decision": decision, "options": options, "path": "discriminative"},
                round=round, phase=phase,
            )
            raise InvalidDecisionError(
                f"判定 {decision!r} 不在 envelope.options={options} 内"
            )

        label_probs = self._option_probs(resp.logprobs, options)
        confidence = label_probs.get(decision) if label_probs else None
        margin = None
        if label_probs and len(label_probs) >= 2:
            vs = sorted(label_probs.values(), reverse=True)
            margin = float(f"{vs[0] - vs[1]:.6f}")

        payload = llm_judgment_payload(
            judgment_id=judgment_id,
            decision=decision,
            model=resp.model,
            context_digest=context_digest,
            prompt_hash=resp.prompt_hash,
            envelope=envelope,
            rng_branch=rng_branch,
            parties=parties,
            dimension=dimension,
            question_ref=question_ref,
            created_round=created_round,
            context_ref=context_ref,
            effect_ref=effect_ref,
            frozen=True,
            confidence=confidence,
            margin=margin,
            method=method,
        )
        event = self.event_log.append(
            "LLM_JUDGMENT", payload,
            actor=parties[0] if parties else "SYSTEM", round=round, phase=phase,
        )
        record = dict(payload)
        record["cache_key"] = resp.cache_key
        record["seq"] = event["seq"]
        self.store.put_judgment(judgment_id, record)
        self._emit_audit("LLM_JUDGMENT", payload, round, phase)

        return FrozenJudgment(
            judgment_id=judgment_id,
            decision=decision,
            model=resp.model,
            context_digest=context_digest,
            frozen=True,
            prompt_hash=resp.prompt_hash,
            parties=parties,
            dimension=dimension,
            question_ref=question_ref,
            envelope=envelope,
            effect_ref=effect_ref,
            margin=margin,
            label_probs=label_probs,
            event=event,
        )

    @staticmethod
    def _normalize_decision(text: str, options: Optional[List[Any]]) -> str:
        """把模型原始输出归一到某个 option。

        **仍要求 decision ∈ envelope.options**——归一只是去除引号/反引号/标点/多行
        等噪声，绝不放宽「LLM 只能在硬内核给定分支内选择」的约束。找不到匹配则原样
        返回，交由上层 ``decision not in options`` 校验并记 ``SYSTEM_ERROR``。
        """
        raw = (text or "").strip()
        if not options:
            return raw
        opts = [str(o) for o in options]
        # 直接命中
        if raw in opts:
            return raw
        # 逐行/逐词剥离引号与标点后匹配（大小写不敏感）
        candidates = [raw] + raw.replace("\n", " ").split(" ")
        for tok in candidates:
            cleaned = tok.strip().strip("\"'`.,:;!?（）()[]{} ").strip()
            for o in opts:
                if cleaned == o or cleaned.lower() == o.lower():
                    return o
        # 兜底：在原始文本中按**词边界**搜索选项（处理 JSON / 包裹文本，如 {"d":"not_formed"}）。
        # 长选项优先，避免 "formed" 误配 "not_formed" 的子串。
        for o in sorted(opts, key=len, reverse=True):
            if re.search(r"(?<![0-9A-Za-z_])" + re.escape(o) + r"(?![0-9A-Za-z_])", raw, re.IGNORECASE):
                return o
        return raw

    def get_frozen_judgment(self, judgment_id: str) -> FrozenJudgment:
        """IF-6：读回已冻结判定，**不调用 LLM**。"""
        rec = self.store.get_judgment(judgment_id)
        if rec is None:
            raise KeyError(f"冻结判定不存在：{judgment_id}")
        return FrozenJudgment(
            judgment_id=rec["judgment_id"],
            decision=rec["decision"],
            model=rec["model"],
            context_digest=rec["context_digest"],
            frozen=rec["frozen"],
            prompt_hash=rec["prompt_hash"],
            parties=list(rec.get("parties", [])),
            dimension=rec.get("dimension", ""),
            question_ref=rec.get("question_ref", ""),
            envelope=rec.get("envelope", {}),
            effect_ref=rec.get("effect_ref"),
            margin=rec.get("margin"),
        )

    # ================================================================== #
    # 叙事层 IF-7（纯输出，不改状态）
    # ================================================================== #
    def narrate(
        self,
        *,
        fact_event_seqs: List[int],
        narrative_id: str,
        body_ref: str,
        facts: Optional[Any] = None,
        style: str = "chronicle",
        pov: str = "omniscient",
        created_round: int = 0,
        phase: int = 2,
        tier: Tier = Tier.T1,
        priority: Priority = Priority.NORMAL,
        model: Optional[str] = None,
        round: Optional[int] = None,
    ) -> str:
        """叙事层出口（IF-7）：把**已定事实**叙述为文本，记 ``NARRATIVE``。

        ``affects_state=false``；判定/统计永不读叙事文本。
        """
        round = created_round if round is None else round
        anchor = self.compute_anchor_digest(fact_event_seqs, facts)
        system = "你是社会仿真的【叙事层】。只把已发生的事实叙述成情节/对话，不改变任何状态。"
        user = canonical_json(
            {
                "style": style,
                "pov": pov,
                "anchor_digest": anchor,
                "fact_event_seqs": list(fact_event_seqs),
                "facts": facts if facts is not None else None,
            }
        )
        resp = self.complete(
            purpose="describe",
            system=system,
            user=user,
            tier=tier,
            priority=priority,
            model=model,
            round=round,
            phase=phase,
            meta={"narrative_id": narrative_id},
        )
        payload = narrative_payload(
            narrative_id=narrative_id,
            fact_event_seqs=fact_event_seqs,
            body_ref=body_ref,
            model=resp.model,
            prompt_hash=resp.prompt_hash,
            anchor_digest=anchor,
            style=style,
            pov=pov,
        )
        payload["degraded"] = resp.degraded
        self.event_log.append("NARRATIVE", payload, round=round, phase=phase)
        self._emit_audit("NARRATIVE", payload, round, phase)
        return resp.text

    @staticmethod
    def compute_anchor_digest(fact_event_seqs: List[int], facts: Optional[Any] = None) -> str:
        """锚点集指纹（**确定性、与 LLM 无关**）：同一事实集逐位一致。"""
        if facts is not None:
            return digest({"facts": facts, "fact_event_seqs": list(fact_event_seqs)})
        return digest({"fact_event_seqs": list(fact_event_seqs)})

    # ================================================================== #
    # 嵌入
    # ================================================================== #
    def embed(self, text: str, *, model: Optional[str] = None) -> List[float]:
        """嵌入（缓存并冻结；重放不重算）。"""
        return self.embedder.embed(text, model=model).vector
