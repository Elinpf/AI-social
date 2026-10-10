"""Phase 3.5 LIFE 内部 hook L1–L7（默认占位实现）。

顺序（08 §2.3，固定）：
  L1 advance_time       派生 week/day/slot；跨日/周发 TIME_MARK
  L2 resolve_schedule   到期 slot 提升为 ACTIVITY_STARTED 意图
  L3 settle_activities  活动结算，产出 resource_intents[]（货币后果交 4.x）
  L4 apply_needs        需求自然衰减/满足 → NEED_UPDATE
  L5 update_relations   关系维度更新 → RELATION_CHANGE / RELATION_ENCOUNTER
  L6 write_memories     确定性 salience 规则 → MEMORY_WRITE / OBSERVATION / MEMORY_REFLECT
  L7 emit_tags          标签发射 → TAG_EMITTED；跑 NORM_* 阈值判定

除 L1（内核时间锚点，D-1，确定性）外均为空占位，由 life 层通过
`engine.hooks.register_phase35_hook(name, fn)` 注入实现。
契约：fn(state, round_no, ctx) -> list[EventSpec]；不得直写 state、不得含货币 delta。
"""

from __future__ import annotations

from ..constants import PHASE_LIFE
from ..events import spec
from ..time import derive_time


def advance_time(state, round_no, ctx):
    """L1：内核时间锚点。跨日（round % rounds_per_day == 0）发 TIME_MARK。"""
    tcfg = ctx.config.get("time_config", {}) if isinstance(ctx.config, dict) else {}
    t = derive_time(round_no, tcfg)
    rounds_per_day = int(tcfg.get("ROUNDS_PER_SLOT", 3)) * len(tcfg.get("SLOTS_PER_DAY", ["m", "a", "e", "n"]))
    out = []
    if round_no % rounds_per_day == 0:
        out.append(spec(round_no, PHASE_LIFE, "SYSTEM", "TIME_MARK", {
            "round": round_no,
            "week": t["week"],
            "day": t["day"],
            "slot": t["slot"],
            "day_type": t["day_type"],
        }))
    return out


def resolve_schedule(state, round_no, ctx):
    return []


def settle_activities(state, round_no, ctx):
    return []


def apply_needs(state, round_no, ctx):
    return []


def update_relations(state, round_no, ctx):
    return []


def write_memories(state, round_no, ctx):
    return []


def emit_tags(state, round_no, ctx):
    return []
