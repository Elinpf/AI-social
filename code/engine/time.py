"""时间派生（D-1，纯函数，无墙钟）。

round → {week, day, day_of_week, day_type, slot, tick_in_slot}
默认参数（00 §3 / 08 §3.1，已冻结）：1 时段=3 回合，1 日=4 时段=12 回合，1 周=84 回合。
"""

from __future__ import annotations

DEFAULT_TIME_CONFIG = {
    "ROUNDS_PER_SLOT": 3,
    "SLOTS_PER_DAY": ["morning", "afternoon", "evening", "night"],
    "DAYS_PER_WEEK": 7,
    "DAY_TYPES": ["workday"] * 5 + ["weekend"] * 2,
    "TIME_UNIT": 1000,
}


def derive_time(round_no: int, time_config: dict | None = None) -> dict:
    cfg = time_config or DEFAULT_TIME_CONFIG
    rps = int(cfg["ROUNDS_PER_SLOT"])
    slots = cfg["SLOTS_PER_DAY"]
    spd = len(slots)
    dpw = int(cfg["DAYS_PER_WEEK"])
    day_types = cfg["DAY_TYPES"]
    rounds_per_day = rps * spd
    day = round_no // rounds_per_day
    slot_idx = (round_no % rounds_per_day) // rps
    tick_in_slot = round_no % rps
    week = day // dpw
    day_of_week = day % dpw
    day_type = day_types[day_of_week]
    return {
        "week": week,
        "day": day,
        "day_of_week": day_of_week,
        "day_type": day_type,
        "slot": slots[slot_idx],
        "tick_in_slot": tick_in_slot,
    }
