"""R53 作息「个体差异 / 错峰」臂 —— 单 env 开关，**默认关 = 逐字节等价**。

口径卡：`reports/R53-prereg-schedule-offset-20261102.md`（判据/接口契约先于本文件冻结）。
本模块只做两件确定性的事，其余一律不动（不改 config、不新增事件类型、不改 state_hash 口径）：

1. **相位偏移（时间轴错峰）**：每个居民有一个**常量**相位 `tick_offset`，把该居民
   `SCHEDULE_PLANNED.slots[*].planned_tick` 在**本 slot 内**整体后移 `{0, +1}` 个 tick。
   - 由 `sha256(agent_id|kind)` 决定（`util.sha256_hex`，不用 `random`/墙钟/进程内状态）；
   - 契约允许 `{-1, 0, +1}`；`planned_tick` 的基准恰在 slot 首 tick（`tick_in_slot == 0`），
     故 `-1` **越过 slot 边界** ⇒ 按 §9.4.3「冲突回退 0」回退 0，实际取值域 = `{0, +1}`。
   - **为什么相位是常量而不是每 slot 重抽**（这条是机制正确性的关键，写死在此便于审计）：
     `settlement._due_completions` 里活动时长恒为 `ROUNDS_PER_SLOT`(=3)，且
     `resolve_schedule` 只在 `current_activity` 为空时起下一个 slot，故实际
     `start_tick_k = 3k + max_{j<=k} offset_j`。若 offset 每 slot 抽样，running-max 会
     在十几个 slot 内**饱和到最大档**（`1-(2/3)^12 ≈ 99.2%`），全居民又回到同一 tick，
     「错峰」名存实亡。常量相位则是「每人固定早到晚到 1 个 tick」，一天 12 tick 恰好
     装下 4 slot × 3 tick，不产生饥饿（不会把某个 slot 挤掉）。
2. **活动类型个体化**：同一 `(agent_id, slot_id)` 的确定性哈希在该 slot 的**既有合法候选**
   （`constants.ACTIVITY_TO_PLACES` ∩ `place.open_slots`/`affordances`，经 `Agent._valid`）
   里选一个，替代 `_base_activity` 的「同 role 同 slot 必然同一套」。
   - **不新造活动类型/场所**（候选全部取自既有常量表）；
   - **锁定**（`slot_locked`）：`night` 恒 `rest/residence` 不动；workday 的
     `morning`/`afternoon` 里 `work` 不得被改成非 work（守卫 G1 在代码层的对应约束）。

关（`HITT_SCHEDULE_OFFSET` 未设 / 其它值）⇒ `Agent._weekly_slots` 完全不调用本模块，
产出与接入前逐字节相同。
"""
from __future__ import annotations

import os

from . import constants as C
from .util import sha256_hex

#: 开关名（预登记卡 §9.1）：{1,true,yes,on} 为开，未设/其它 = 关（默认关）
OFFSET_ENV = "HITT_SCHEDULE_OFFSET"

#: 相位哈希的 kind 段（改这里等于改机制，必须同步改预登记卡）
PHASE_KIND = "r53-phase"
ACT_KIND = "r53-act"

#: 固定 `rest/residence` 的时段（契约 §9.4.4：night 不许动）
_FIXED_SLOTS = frozenset({"night"})

#: 生产性时段：workday 的 morning/afternoon 里 `work` 不许被换成非 work（守卫 G1）
_PROTECTED = frozenset({("workday", "morning"), ("workday", "afternoon")})


def offset_enabled() -> bool:
    """作息错峰臂开关（env `HITT_SCHEDULE_OFFSET` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(OFFSET_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _h(*parts: str) -> int:
    """确定性哈希（整数）：`sha256("a|b|c")` 前 8 个 hex 位。"""
    return int(sha256_hex("|".join(parts))[:8], 16)


def phase_raw(agent_id: str) -> int:
    """相位原始档位 ∈ {-1, 0, +1}（契约 §9.4.1 的取值域）。"""
    return _h(str(agent_id), PHASE_KIND) % 3 - 1


def tick_offset(agent_id: str) -> int:
    """`planned_tick` 在 slot 内的后移量（tick）：`{0, +1}`。

    `-1` 会把 `planned_tick` 推到**上一个 slot**（基准恰为 slot 首 tick），
    按契约 §9.4.3「冲突回退 0」回退到 0 ⇒ 实际取值域 `{0, +1}`。
    """
    off = phase_raw(agent_id)
    return off if off > 0 else 0


def slot_locked(day_type: str, slot: str, atype: str) -> bool:
    """该 (day_type, slot) 的**这个**活动类型是否锁定（不得被个体化改动）。"""
    if slot in _FIXED_SLOTS:
        return True
    if (day_type, slot) in _PROTECTED and atype == "work":
        return True
    return False


def candidates(day_type: str, slot: str, base: tuple[str, str], valid) -> list[tuple[str, str]]:
    """该 slot 下的**既有合法候选**（不含 base 自身），按 (atype, place) 字典序稳定排序。

    候选池 = `constants.ACTIVITY_TO_PLACES` 里所有活动类型 × 其登记场所，
    逐个过 `valid(atype, place, slot)`（= `Agent._valid`：场所 open_slots ∧ affordances）。
    `day_type` 只用于锁定判定，候选池本身不依赖它（不新造类型/场所）。
    """
    base_at, base_pl = base
    out: list[tuple[str, str]] = []
    for atype in sorted(C.ACTIVITY_TO_PLACES):
        for place in C.ACTIVITY_TO_PLACES[atype]:
            if (atype, place) == (base_at, base_pl):
                continue
            try:
                ok = bool(valid(atype, place, slot))
            except Exception:
                ok = False
            if ok:
                out.append((atype, place))
    return sorted(out)


def plan_activity(agent_id: str, day_type: str, slot: str, slot_id: str,
                  value: tuple[str, str], valid, habitual: bool = True) -> tuple[str, str, bool]:
    """个体化本 slot 的活动类型：返回 `(activity_type, place, changed)`。

    * `habitual=False`（本 slot 的取值已被**需求剥夺**覆盖：`needs < θ_dep`）⇒ 原样返回。
      这条保证「个体习惯只作用于习惯时段，不抢需求驱动的补偿行为」——与
      `_choose_activity` 既有语义同向，且避免"饿了不去吃饭"这类退化；
    * 锁定（`slot_locked`）⇒ 原样返回；
    * 否则在该 slot 的**既有合法候选池**里按 `sha256(agent_id|slot_id|kind)` 确定性取一个
      （候选池为空 ⇒ 原样返回，不编造）。
    """
    at, pl = value
    if not habitual:
        return at, pl, False
    if slot_locked(day_type, slot, at):
        return at, pl, False
    bucket = _h(str(agent_id), str(slot_id), ACT_KIND)
    cands = candidates(day_type, slot, (at, pl), valid)
    if not cands:
        return at, pl, False
    atype, place = cands[bucket % len(cands)]
    if (atype, place) == (at, pl):
        return at, pl, False
    return atype, place, True
