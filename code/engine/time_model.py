"""tick 内时间区间 · 纯函数口径（T287 期① / 08 §5.10）。

红线（scope）：
- **纯函数、无 I/O、无状态**；**不改结算**；默认 off ⇒ 与现状逐位一致。
- **事实序 = `seq`**（日志唯一事实序，红线）；本模块提供**语义时间序**
  `(start_μt, agent_id, seq)` 供排序，**二者不可混用**（08 §5.10）。
- `μt = round*U + sub`；`span` 缺省 = 瞬时 `(round, 0)`。

配置：`config/time.json`（进 `engine_version` 指纹）。开关 `interval.enabled` 默认 false。
"""

from __future__ import annotations

DEFAULT_U = 6


def time_cfg(config: dict | None) -> dict:
    return (config or {}).get("time", {}) or {}


def U_of(config: dict | None) -> int:
    u = int(time_cfg(config).get("U", DEFAULT_U) or DEFAULT_U)
    return u if u > 0 else DEFAULT_U


def interval_enabled(config: dict | None) -> bool:
    return bool((time_cfg(config).get("interval", {}) or {}).get("enabled", False))


def time_model_of(config: dict | None) -> str:
    """版本戳：off=`atomic`；on=`interval-U<U>`（跨 sha 自描述；08 §5.10）。"""
    return f"interval-U{U_of(config)}" if interval_enabled(config) else "atomic"


def micro_time(round_no: int, sub: int, U: int = DEFAULT_U) -> int:
    return int(round_no) * int(U) + int(sub)


def span_bounds(rec: dict, U: int = DEFAULT_U) -> tuple[int, int]:
    """返回 (start_μt, end_μt)；缺省 span ⇒ 瞬时 `(round,0)`。"""
    r = int(rec.get("round", 0))
    sp = rec.get("span")
    if not isinstance(sp, dict):
        mt = micro_time(r, 0, U)
        return mt, mt
    sr = int(sp.get("start_round", r))
    ss = int(sp.get("start_sub", 0))
    er = int(sp.get("end_round", sr))
    es = int(sp.get("end_sub", ss))
    return micro_time(sr, ss, U), micro_time(er, es, U)


def semantic_key(rec: dict, U: int = DEFAULT_U) -> tuple[int, str, int]:
    """语义时间序键 `(start_μt, agent_id, seq)`（agent_id = actor；08 §5.10）。"""
    start, _ = span_bounds(rec, U)
    return (start, str(rec.get("actor", "")), int(rec.get("seq", 0)))


def derive_order(records, config: dict | None = None) -> list:
    """纯函数：返回按语义时间序**稳定排序**的新列表（不改原列表、不改结算）。

    ⚠️ 本期只在**显式需要时**被调用；默认路径不调用 ⇒ off 行为不变。
    """
    U = U_of(config)
    return sorted(records, key=lambda r: semantic_key(r, U))
