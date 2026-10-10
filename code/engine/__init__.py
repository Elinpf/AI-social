"""HITT 社会实验 · 确定性内核（D0 Hard Kernel）骨架。

权威输入：
  - v1/03-engine-stats.md          （内核契约：回合/事件壳/哈希链/重放）
  - v1.1/00-architecture.md        （P0–P6 阶段、hook 链、IF-1~IF-7）
  - v1.1/08-engine-stats-extension.md（事件表、Phase 3.5、config 表）

铁律：
  C1 世界引擎 / 中央裁决器是确定性代码，绝不是 LLM。
  C3 统计只读日志、纯函数、逐位一致。
  P1 金额一律整数 mu，禁浮点参与记账。
  P2 状态 = reduce(apply, EventLog, InitialState)。
  P5 所有遍历/排序有全序 tie-break。
  P6 只追加日志 + SHA-256 哈希链。
  P7 意图/事实分离：写世界的只有中央裁决器 Arbiter。
"""

from .constants import (
    PHASE_ROUTE,
    PHASE_PERCEIVE,
    PHASE_DECIDE,
    PHASE_COMMUNICATE,
    PHASE_LIFE,
    PHASE_ARBITRATE,
    PHASE_LIFECYCLE,
    PHASE_COMMIT,
)
from .canon import canonical_json, canonical_bytes, hash_obj, sha256_hex, GENESIS_HASH
from .rng import draw_u64, derive_subseed, splitmix64_next, RngStream, Ctx
from .state import WorldState, initial_state, state_hash, money_total
from .ledger import Ledger
from .replay import apply_event, replay_records, verify_chain
from .kernel import Engine
from .runner import run, load_config, default_config

__all__ = [
    "PHASE_ROUTE", "PHASE_PERCEIVE", "PHASE_DECIDE", "PHASE_COMMUNICATE",
    "PHASE_LIFE", "PHASE_ARBITRATE", "PHASE_LIFECYCLE", "PHASE_COMMIT",
    "canonical_json", "canonical_bytes", "hash_obj", "sha256_hex", "GENESIS_HASH",
    "draw_u64", "derive_subseed", "splitmix64_next", "RngStream", "Ctx",
    "WorldState", "initial_state", "state_hash", "money_total",
    "Ledger", "apply_event", "replay_records", "verify_chain",
    "Engine", "run", "load_config", "default_config",
]
