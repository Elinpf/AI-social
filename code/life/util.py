"""Deterministic helpers for the persona-life layer (M1/M2/M4/M5/M7 skeleton).

All helpers here are pure and integer-first, mirroring v1 `03-engine-stats`:
  - `canonical_json`  : key-sorted, no-whitespace JSON (used for hashing / audit)
  - `sha256_hex`      : SHA-256, hex
  - `SplitMix64`      : integer-only PRNG (no float, cross-language reproducible)
  - `draw`            : hierarchical RNG stream  (seed, stream_id, round, seq)
  - `clamp`           : integer clamp

Nothing here reads wall-clock / env / network.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

MASK64 = (1 << 64) - 1


def canonical_json(obj: Any) -> str:
    """Canonical JSON: keys sorted, no whitespace, UTF-8 preserved."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_hash(obj: Any) -> str:
    return sha256_hex(canonical_json(obj))


class SplitMix64:
    """Integer-only PRNG (Steele et al.), reproducible across languages.

    We intentionally do NOT use Python's built-in `random` (float based).
    """

    __slots__ = ("state",)

    def __init__(self, seed: int) -> None:
        self.state = seed & MASK64

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return (z ^ (z >> 31)) & MASK64

    def next_int(self, lo: int, hi: int) -> int:
        """Uniform integer in [lo, hi] (inclusive). hi >= lo."""
        span = hi - lo + 1
        return lo + (self.next_u64() % span)


def _sub_seed(global_seed: int, stream_id: str, round_no: int, seq: int) -> int:
    h = sha256_hex(f"{global_seed}|{stream_id}|{round_no}|{seq}")
    return int(h[:16], 16)  # first 8 bytes -> uint64


def draw(global_seed: int, stream_id: str, round_no: int, seq: int, n: int) -> list[int]:
    """Deterministic draw of n uint64s; sequence fixed by (seed, stream, round, seq)."""
    rng = SplitMix64(_sub_seed(global_seed, stream_id, round_no, seq))
    return [rng.next_u64() for _ in range(n)]


def clamp(value: int, lo: int, hi: int) -> int:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value
