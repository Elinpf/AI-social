"""M3 — directed relations (06 §6).

Four directed dimensions per (from -> to):
    affinity    [-100,100]   喜爱/好感
    trust       [-100,100]   信任
    respect     [0,100]      尊重
    familiarity [0,100]      熟悉度（单调不减）

Discipline (06 §6.1 / AR-C3 / D-12):
  * numeric updates are a **deterministic function of the event `cause`** — the LLM
    never sets a number;
  * the LLM only ever writes an *impression narrative* (05/N-6), stored to side storage;
  * crossing `epsilon` / `epsilon_strong` (a "qualitative change") follows the
    frozen-judgment flow: **RNG picks the branch -> LLM fills a label inside the
    branch -> the judgment is frozen** (LLM_JUDGMENT, 00 §5.5). The numeric
    consequence is then derived deterministically from the frozen label.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .constants import EPS, EPS_STRONG, RELATION_DELTA_MAX, RELATION_RANGE
from .util import clamp

# coefficients (06 §6.3), defaults from 06 §6.5
RELATION_COEF = {"k_a": 1, "k_t": 2, "k_a2": 1, "k_rescue": 8, "k_t2": 6, "k_pen": 5}
CHAT_DURATION_CAP = 10  # min(duration, cap) for the chat/co-presence term


@dataclass
class RelationState:
    affinity: int = 0
    trust: int = 0
    respect: int = 0
    familiarity: int = 0
    last_interaction_round: int = 0
    interaction_count: int = 0
    impression_ref: str | None = None

    def as_dict(self) -> dict:
        return {"affinity": self.affinity, "trust": self.trust, "respect": self.respect,
                "familiarity": self.familiarity,
                "last_interaction_round": self.last_interaction_round,
                "interaction_count": self.interaction_count,
                "impression_ref": self.impression_ref}


def _sign(x: int) -> int:
    return 1 if x >= 0 else -1


def rel_delta(cause: str, *, current: dict | None = None, amount: int = 0,
              duration: int = 0, coef: dict | None = None) -> dict[str, int]:
    """Deterministic cause -> per-dimension delta (06 §6.3). Never uses the LLM."""
    k = dict(RELATION_COEF)
    if coef:
        k.update(coef)
    cur = current or {}
    d: dict[str, int] = {}
    if cause in ("chat", "copresence"):
        d["affinity"] = k["k_a"] * min(int(duration), CHAT_DURATION_CAP) * _sign(int(cur.get("affinity", 0)))
    elif cause == "trade_success":
        d["trust"] = int(round(k["k_t"] * math.log(1 + max(0, int(amount)))))
        d["affinity"] = k["k_a2"]
    elif cause == "transfer_rescue":
        # recipient's view of the helper (applied on the directed edge)
        d["affinity"] = k["k_rescue"]
        d["trust"] = k["k_t2"]
    elif cause == "ssl_flag":
        d["trust"] = -k["k_pen"]
    elif cause == "encounter":
        d["familiarity"] = 1
    else:
        return {}
    # cap the per-cause magnitude (Δ_max, 06 §6.5)
    return {dim: clamp(v, -RELATION_DELTA_MAX, RELATION_DELTA_MAX) for dim, v in d.items() if v}


def apply_delta(rel: dict, delta: dict[str, int]) -> dict:
    """Apply a delta to a relation dict in place, clamped to the value ranges."""
    for dim, dv in delta.items():
        lo, hi = RELATION_RANGE.get(dim, (-100, 100))
        rel[dim] = clamp(int(rel.get(dim, 0)) + int(dv), lo, hi)
    return rel


def initial_relation(entry: dict) -> RelationState:
    return RelationState(affinity=int(entry.get("affinity", 0)),
                         trust=int(entry.get("trust", 0)),
                         respect=int(entry.get("respect", 0)),
                         familiarity=int(entry.get("familiarity", 0)))


# ---- qualitative change: RNG branch -> LLM label -> freeze (00 §5.5) ---------
def crosses_threshold(before: int, after: int, *, strong: bool = False) -> bool:
    th = EPS_STRONG if strong else EPS
    return (abs(before) < th <= abs(after)) or (abs(after) < th <= abs(before))


def soft_judgment_envelope(dimension: str, before: int, after: int) -> dict:
    """The hard-kernel-given envelope: legal options + the RNG-decided branch.

    NOTE: the branch value itself is supplied by the caller from a seeded RNG stream
    (D-8); this function only shapes the envelope. The LLM may ONLY pick within it.
    """
    return {"dimension": dimension, "options": ["formed", "not_formed"],
            "threshold": EPS_STRONG if abs(after) >= EPS_STRONG else EPS,
            "before": before, "after": after}


def freeze_judgment(judgment_id: str, dimension: str, parties: list[str], envelope: dict,
                    branch: str, context_digest: str, model: str) -> dict:
    """Build a frozen LLM_JUDGMENT payload. `branch` must be in envelope.options."""
    if branch not in envelope["options"]:
        raise ValueError(f"branch {branch!r} not in envelope options {envelope['options']}")
    return {"judgment_id": judgment_id, "parties": list(parties), "dimension": dimension,
            "question_ref": f"rel::{dimension}", "envelope": envelope, "rng_branch": branch,
            "decision": branch, "model": model, "context_digest": context_digest, "frozen": True}


# numeric consequence of a frozen qualitative label (deterministic, D-12)
JUDGMENT_DELTA = {"formed": {"affinity": 5, "trust": 3}, "not_formed": {"affinity": -2}}


def delta_from_frozen_label(label: str) -> dict[str, int]:
    return dict(JUDGMENT_DELTA.get(label, {}))
