"""Soft-judgment (IF-2b) & narrative (IF-7) access for the life main loop (T54).

Wraps the (freezable) LLM client so the agent can:
  * `judge(...)`: at a relation threshold crossing, run the frozen flow
    **RNG picks the branch -> LLM fills a qualitative label inside the envelope ->
    frozen as `LLM_JUDGMENT`** (00 §4.6/§5.5). The LLM only emits a LABEL; the
    numeric consequence is derived deterministically by the hard kernel (M3 §6.3).
  * `narrate(...)`: turn already-decided facts into a story -> `NARRATIVE`
    `affects_state=false` (17-narrative).

If the underlying client is the team freeze layer (has `.client.judge/.narrate`),
it emits the events through the IF-2c audit bridge itself. Otherwise (offline
rule client, e.g. the mini test-double) `judge/narrate` return the payload with
`emitted=False` and the caller submits it via the kernel's `submit_audit`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .util import canonical_hash, draw


@dataclass
class SoftLayer:
    base: Any

    def _inner(self) -> Any:
        return getattr(self.base, "client", None)

    @property
    def emits_events(self) -> bool:
        inner = self._inner()
        return inner is not None and hasattr(inner, "judge")

    def judge(self, *, judgment_id: str, dimension: str, question_ref: str, envelope: dict,
              rng_branch: str, parties: list[str], context: dict, round_no: int,
              phase: int = 2, mode: str = "generative") -> tuple[dict, bool]:
        inner = self._inner()
        options = envelope.get("options") or ["not_formed"]
        decision = rng_branch if rng_branch in options else options[0]
        if inner is not None and hasattr(inner, "judge"):
            if mode == "discriminative" and hasattr(inner, "judge_discriminative"):
                return self._judge_discriminative(
                    inner, judgment_id=judgment_id, dimension=dimension,
                    question_ref=question_ref, envelope=envelope, rng_branch=rng_branch,
                    parties=parties, context=context, round_no=round_no, phase=phase)
            try:
                j = inner.judge(judgment_id=judgment_id, dimension=dimension,
                                question_ref=question_ref, envelope=envelope, context=context,
                                rng_branch=rng_branch, parties=list(parties),
                                created_round=round_no, round=round_no, phase=phase)
                payload = {"judgment_id": judgment_id, "decision": j.decision, "model": j.model,
                           "context_digest": j.context_digest, "frozen": True,
                           "dimension": dimension, "question_ref": question_ref,
                           "envelope": envelope, "rng_branch": rng_branch,
                           "parties": list(parties)}
                return payload, True
            except Exception:
                # model failed to yield a valid option -> the RNG branch is authoritative
                # (00 §5.4). Visible fallback: `fallback=true` + model tag, so a provider
                # defect is never silently swallowed (Leader T54 point 1).
                payload = {"judgment_id": judgment_id, "decision": decision, "model": "rng-branch",
                           "fallback": True, "context_digest": canonical_hash(context),
                           "frozen": True, "dimension": dimension, "question_ref": question_ref,
                           "envelope": envelope, "rng_branch": rng_branch,
                           "parties": list(parties)}
                self._emit_frozen_via(inner, payload, parties, round_no, phase)
                return payload, True
        payload = {"judgment_id": judgment_id, "decision": decision, "model": "rule-based-v1",
                   "context_digest": canonical_hash(context), "frozen": True,
                   "dimension": dimension, "question_ref": question_ref, "envelope": envelope,
                   "rng_branch": rng_branch, "parties": list(parties)}
        return payload, False

    def _judge_discriminative(self, inner: Any, *, judgment_id: str, dimension: str,
                              question_ref: str, envelope: dict, rng_branch: str,
                              parties: list[str], context: dict, round_no: int,
                              phase: int) -> tuple[dict, bool]:
        """M2b 受限选择路径（T222）。freeze 侧 `judge_discriminative` 负责 provider 调用 +
        约束解码 + 落 `LLM_JUDGMENT`（四要素只增不改，加 `method`/`margin`）。此处只：
          1) 失败（provider/解析/越界）→ **可见回退** rng-branch（method=rng-branch，不静默）；
          2) **逃生项解析**：若模型选了 `undecidable`（escape），按 `ESCAPE_FALLBACK` 落到
             确定性兜底值供**下游消费**（日志里 LLM_JUDGMENT.decision 仍保留模型原话=undecidable，
             故 `escape_rate` 可从日志聚合 —— 不新增事件）。
        """
        from . import constants as C
        from . import policy
        try:
            j = inner.judge_discriminative(
                judgment_id=judgment_id, dimension=dimension, question_ref=question_ref,
                envelope=envelope, context=context, rng_branch=rng_branch, parties=list(parties),
                created_round=round_no, round=round_no, phase=phase, method="discriminative")
        except Exception:
            payload = {"judgment_id": judgment_id, "decision": rng_branch, "model": "rng-branch",
                       "fallback": True, "method": "rng-branch",
                       "context_digest": canonical_hash(context), "frozen": True,
                       "dimension": dimension, "question_ref": question_ref,
                       "envelope": envelope, "rng_branch": rng_branch, "parties": list(parties)}
            self._emit_frozen_via(inner, payload, parties, round_no, phase)
            return payload, True
        raw = getattr(j, "decision", None)
        margin = getattr(j, "margin", None)
        method = "discriminative"
        resolved = raw
        fallback_note = None
        # (1) 逃生项 -> 确定性兜底（供下游消费；日志保留 raw 以便 escape_rate 聚合）
        if raw == C.ESCAPE_OPTION and dimension in C.ESCAPE_FALLBACK:
            resolved = C.ESCAPE_FALLBACK[dimension]
            fallback_note = "escape_option"
        # (2) margin 回退（分支 B；默认 none/θ=0 → 永不触发）
        fb, theta = policy.m2b_fallback(), policy.m2b_margin_theta()
        if fb == "margin" and margin is not None and float(margin) < float(theta):
            try:
                j2 = inner.judge(judgment_id=judgment_id, dimension=dimension,
                                 question_ref=question_ref, envelope=envelope, context=context,
                                 rng_branch=rng_branch, parties=list(parties),
                                 created_round=round_no, round=round_no, phase=phase)
                resolved, method, fallback_note = j2.decision, "generative", "margin_low"
            except Exception:
                pass
        payload = {"judgment_id": judgment_id, "decision": resolved, "model": j.model,
                   "context_digest": j.context_digest, "frozen": True, "dimension": dimension,
                   "question_ref": question_ref, "envelope": envelope, "rng_branch": rng_branch,
                   "parties": list(parties), "method": method, "model_decision": raw}
        if margin is not None:
            payload["margin"] = margin
        if fallback_note:
            payload["fallback"] = fallback_note
        return payload, True


    @staticmethod
    def _emit_frozen_via(inner: Any, payload: dict, parties: list, round_no: int, phase: int) -> None:
        log = getattr(inner, "event_log", None)
        if log is not None and hasattr(log, "append"):
            log.append("LLM_JUDGMENT", payload,
                       actor=(parties[0] if parties else "SYSTEM"), round=round_no, phase=phase)
        sink = getattr(inner, "_emit_audit", None)
        if sink is not None:
            sink("LLM_JUDGMENT", payload, round_no, phase)

    def narrate(self, *, narrative_id: str, fact_event_seqs: list, body_ref: str,
                style: str = "chronicle", pov: str = "omniscient", facts: Any = None,
                round_no: int = 0, phase: int = 6) -> tuple[dict, bool]:
        inner = self._inner()
        if inner is not None and hasattr(inner, "narrate"):
            inner.narrate(fact_event_seqs=list(fact_event_seqs), narrative_id=narrative_id,
                          body_ref=body_ref, facts=facts, style=style, pov=pov,
                          created_round=round_no, round=round_no, phase=phase)
            payload = {"narrative_id": narrative_id, "fact_event_seqs": list(fact_event_seqs),
                       "body_ref": body_ref, "affects_state": False}
            return payload, True
        payload = {"narrative_id": narrative_id, "fact_event_seqs": list(fact_event_seqs),
                   "body_ref": body_ref, "affects_state": False}
        return payload, False


def get_soft_layer(base) -> SoftLayer:
    return SoftLayer(base)


def rng_branch(agent_id: str, dimension: str, other: str, round_no: int,
               options: list[str]) -> str:
    """Deterministic RNG branch (D-8): LLM does NOT roll the dice (00 §5.4)."""
    d = draw(0, f"judge:{agent_id}:{dimension}:{other}", round_no, 0, 1)[0]
    return options[d % len(options)]
