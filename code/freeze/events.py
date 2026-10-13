"""事件账本（哈希链）与冻结层事件封装。

事件外壳沿用 v1/v1.1（08 §1.1）：

    Event = {seq, round, phase, actor, type, payload, mono_ts, prev_hash, hash}

冻结层产出的三类审计事件（08 §1.2 G/I）：

- ``LLM_CALL``    —— 成本审计（**不改账**）。判定/叙事/嵌入等 LLM 调用分列记账。
- ``LLM_JUDGMENT``—— 冻结的 LLM 定性判定，**必带四要素**
  ``decision / model / context_digest / frozen=true``。
- ``NARRATIVE``   —— 叙事层纯输出，``affects_state=false``，恒等折叠。

三条纪律：成本（LLM_CALL）与判定（LLM_JUDGMENT）**分列**；叙事不改状态；
哈希链覆盖全部事件。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .canonical import GENESIS_HASH, hash_obj


class EventLog:
    """append-only 事件日志 + SHA-256 哈希链（纯确定性、无 I/O 依赖）。

    与 v1/v1.1 账本语义一致：``hash_i = SHA256(canonical(event_i without hash))``，
    其中 ``event_i.prev_hash = hash_{i-1}``。
    """

    def __init__(
        self,
        genesis: str = GENESIS_HASH,
        time_unit: int = 1000,
        path: Optional[str] = None,
    ) -> None:
        self.records: List[Dict[str, Any]] = []
        self.time_unit = time_unit
        self._last_hash = genesis
        self._phase_seq: Dict[tuple, int] = {}
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("", encoding="utf-8")

    # ---------------------------------------------------------------- #
    def append(
        self,
        type: str,
        payload: Dict[str, Any],
        *,
        actor: str = "SYSTEM",
        round: int = 0,
        phase: int = 2,
    ) -> Dict[str, Any]:
        """追加一条事件并更新哈希链，返回该事件记录。"""
        seq = len(self.records)
        pkey = (round, phase)
        ps = self._phase_seq.get(pkey, 0)
        self._phase_seq[pkey] = ps + 1
        mono_ts = round * self.time_unit + ps

        body: Dict[str, Any] = {
            "seq": seq,
            "round": round,
            "phase": phase,
            "actor": actor,
            "type": type,
            "payload": payload,
            "mono_ts": mono_ts,
            "prev_hash": self._last_hash,
        }
        h = hash_obj(body)
        body["hash"] = h
        self._last_hash = h
        self.records.append(body)

        if self.path:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(body, ensure_ascii=False) + "\n")
        return body

    # ---------------------------------------------------------------- #
    def last_hash(self) -> str:
        return self._last_hash

    def _recompute(self, record: Dict[str, Any]) -> str:
        body = {k: v for k, v in record.items() if k != "hash"}
        return hash_obj(body)

    def verify(self) -> bool:
        """校验哈希链完整性与 prev_hash 连接。"""
        prev = GENESIS_HASH
        for i, rec in enumerate(self.records):
            if rec["seq"] != i:
                return False
            if rec["prev_hash"] != prev:
                return False
            if self._recompute(rec) != rec["hash"]:
                return False
            prev = rec["hash"]
        return True

    def of_type(self, type: str) -> List[Dict[str, Any]]:
        return [r for r in self.records if r["type"] == type]


# --------------------------------------------------------------------------- #
# 事件载荷构造器（保持字段名与 08 §1.2 对齐；LLM_JUDGMENT 强制四要素）
# --------------------------------------------------------------------------- #

def llm_call_payload(
    *,
    purpose: str,
    model: str,
    engine_version: str,
    prompt_hash: str,
    cache_key: str,
    tier: str,
    priority: str,
    degraded: bool,
    cached: bool,
    tokens_in: int,
    tokens_out: int,
    cost_units: int,
    provider: str,
    phase: int = 2,
    agent_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """``LLM_CALL`` 载荷——成本审计（分列，不改账）。

    ``agent_id``（T360 登记 / T361 实现）：**本次调用的归属主体**，**可选**；
    取值 ∈ ``AgentId ∪ {SYSTEM, DIRECTOR, OBSERVER}``；**缺省（不写该键）= 未归属
    ``UNATTRIBUTED``**（旧日志兼容、不强制迁移）。消费方须先经 `is_agent_actor()` 守卫，
    非 Agent 主体不得伪装成居民。**不改 `actor`**（审计桥的"发射者"仍为 `SYSTEM`）。
    """
    payload: Dict[str, Any] = {
        "purpose": purpose,
        "model": model,
        "provider": provider,
        "engine_version": engine_version,
        "prompt_hash": prompt_hash,
        "cache_key": cache_key,
        "tier": tier,
        "priority": priority,
        "degraded": degraded,
        "cached": cached,
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
        "cost_units": int(cost_units),
    }
    # 仅在明确给出时写入（缺省即"未归属"，不伪装成某居民；旧日志无该键亦合法）。
    if agent_id is not None:
        payload["agent_id"] = agent_id
    if extra:
        payload.update(extra)
    return payload


def llm_judgment_payload(
    *,
    judgment_id: str,
    decision: Any,
    model: str,
    context_digest: str,
    prompt_hash: str,
    envelope: Dict[str, Any],
    rng_branch: Any,
    parties: List[str],
    dimension: str,
    question_ref: str,
    created_round: int,
    context_ref: Optional[str] = None,
    effect_ref: Optional[int] = None,
    frozen: bool = True,
    confidence: Optional[float] = None,
    margin: Optional[float] = None,
    method: Optional[str] = None,
) -> Dict[str, Any]:
    """``LLM_JUDGMENT`` 载荷——强制四要素：decision/model/context_digest/frozen。

    frozen 恒为 True；若调用方传入 False 将直接报错（冻结语义不可协商）。
    可选：`confidence`/`margin`（判别式路径）、`method`（由调用方传入，freeze 不推断语义）。
    """
    if frozen is not True:
        raise ValueError("LLM_JUDGMENT.frozen 必须为 True（冻结语义）")
    payload = {
        "judgment_id": judgment_id,
        "parties": list(parties),
        "dimension": dimension,
        "question_ref": question_ref,
        "envelope": envelope,
        "rng_branch": rng_branch,
        "decision": decision,
        "context_digest": context_digest,
        "context_ref": context_ref,
        "model": model,
        "prompt_hash": prompt_hash,
        "created_round": created_round,
        "frozen": True,
        "effect_ref": effect_ref,
    }
    if confidence is not None:
        payload["confidence"] = float(confidence)
    if margin is not None:
        payload["margin"] = float(margin)
    if method is not None:
        payload["method"] = str(method)
    return payload


def narrative_payload(
    *,
    narrative_id: str,
    fact_event_seqs: List[int],
    body_ref: str,
    model: str,
    prompt_hash: str,
    anchor_digest: str,
    style: str = "chronicle",
    pov: str = "omniscient",
    spec_flags: int = 0,
    degraded: bool = False,
) -> Dict[str, Any]:
    """``NARRATIVE`` 载荷——纯输出，``affects_state=false``（恒等折叠）。"""
    return {
        "narrative_id": narrative_id,
        "fact_event_seqs": list(fact_event_seqs),
        "body_ref": body_ref,
        "affects_state": False,
        "style": style,
        "pov": pov,
        "model": model,
        "prompt_hash": prompt_hash,
        "anchor_digest": anchor_digest,
        "spec_flags": spec_flags,
        "degraded": degraded,
    }
