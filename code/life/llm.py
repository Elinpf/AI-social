"""LLM access for the life layer — a single narrow, freezable entry point.

Per `00-architecture.md` §1.5/§5.4 and `14-agent-impl-reuse-map.md` §E, every LLM
output must be produced once and then *frozen* so replay never re-calls the model.
That mechanism is owned by the freeze layer (T30). The life layer depends only on
the tiny `LLMClient` protocol below.

Resolution order for `get_llm_client()`:
  1. `freeze.client.FreezeLLM` (the team freeze layer, T30) if importable
  2. the built-in `RuleBasedLLM` — deterministic, offline, no network

The life layer never decides world randomness from LLM output; it only fills
already-determined branches with content (00 §5.4 rule 1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

ALLOWED_PURPOSES = frozenset({"plan", "reflect", "importance", "decide_t2", "describe",
                              "judge", "narrate", "dialogue"})


@dataclass(frozen=True)
class LLMResult:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    cache_key: str = ""
    model: str = "rule-based"
    degraded: bool = False


@runtime_checkable
class LLMClient(Protocol):
    def call(self, purpose: str, prompt: str, *, model: str | None = None,
             meta: dict | None = None) -> LLMResult: ...


class RuleBasedLLM:
    """Deterministic offline fallback. Same prompt -> same text, no network.

    This exists so the skeleton runs end-to-end with zero external dependency and
    stays replay-safe (its output is deterministic). It is intentionally *not* a
    real model; swap in `freeze.client.FreezeLLM` for the real thing.
    """

    name = "rule-based-v1"

    def call(self, purpose: str, prompt: str, *, model: str | None = None,
             meta: dict | None = None) -> LLMResult:
        if purpose not in ALLOWED_PURPOSES:
            raise ValueError(f"purpose not allowed: {purpose!r}")
        if purpose == "importance":
            # very rough deterministic importance from prompt length / keywords
            text = prompt
            score = 2
            for kw, bump in (("died", 6), ("born", 5), ("party", 3), ("help", 3),
                             ("trade", 2), ("friend", 3), ("argue", 3)):
                if kw in text.lower():
                    score += bump
            score = max(0, min(10, score))
            out = str(score)
        elif purpose == "reflect":
            out = "（反思）我在小镇的一天：照常作息，关注身边的人与事。"
        elif purpose == "judge":
            # deterministic offline: "fill" the already-RNG-decided branch
            branch = (meta or {}).get("rng_branch", "not_formed")
            out = str(branch)
        elif purpose == "narrate":
            out = "（叙述）" + prompt[:120]
        elif purpose == "plan":
            out = "（计划）按作息工作、休息，留出社交与休闲时间。"
        elif purpose == "dialogue":
            tpl = (meta or {}).get("template", "")
            out = f"（{tpl or '闲聊'}）今天见到你真好，最近可好？"
        else:
            out = "（内容）略。"
        from .util import sha256_hex
        return LLMResult(text=out, tokens_in=len(prompt.split()), tokens_out=len(out.split()),
                         cache_key=f"rule:{purpose}:{sha256_hex(prompt)[:24]}",
                         model=model or self.name)


def get_llm_client(prefer_freeze: bool = True) -> LLMClient:
    """Return the team freeze layer if available, else the offline rule client."""
    if prefer_freeze:
        try:  # pragma: no cover - depends on sibling module being present
            from freeze.client import FreezeLLM  # type: ignore
            return FreezeLLM()
        except Exception:
            pass
    return RuleBasedLLM()
