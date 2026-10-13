"""黄金基线（事件量 / 分布回归门禁 G6）之冻结与匹配。

动机（T24 评审 + Leader 2026-10-10）：一次静默回归——`run --life` 跑完、
`chain_ok/replay_parity/conservation_ok` 全绿，但世界**停摆**（N=20 只产 523 事件、
`SYSTEM_ERROR`=83、`MEMORY_WRITE`=0、`ACTIVITY_COMPLETED`=0、`TIME_MARK`=1）。
既有门禁（哈希链/重放/守恒/字节一致）**全部漏检**。G6 用来区分「跑完了」与「真的在运转」。

口径说明：
  - `TIME_MARK` 是**日/周边界锚点**（08 §1.2-A：每跨日一条），
    **不是每回合一条**；预期条数 = `ceil(rounds / ROUNDS_PER_DAY)`（由 TIME_CONFIG 派生）。
  - 基线从**已验证良好的运行日志**冻结（当前：T34 的 n3/n10 单周日志）。

文件：`golden_baseline.json`（本模块同目录），可由 `python -m obs golden-freeze` 重新固化。
"""

from __future__ import annotations

import json
from pathlib import Path

BASELINE_PATH = Path(__file__).resolve().parent / "golden_baseline.json"

DEFAULT_MIN_EVENT_RATIO = 0.8
DEFAULT_REQUIRE_ZERO = ("SYSTEM_ERROR",)
DEFAULT_REQUIRED_NONZERO = (
    "MEMORY_WRITE", "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "NEED_UPDATE",
)

DEFAULT_TIME_CONFIG = {
    "ROUNDS_PER_SLOT": 3,
    "SLOTS_PER_DAY": ["morning", "afternoon", "evening", "night"],
    "DAYS_PER_WEEK": 7,
}


def rounds_per_day(time_cfg: dict | None) -> int:
    cfg = time_cfg or DEFAULT_TIME_CONFIG
    rps = int(cfg.get("ROUNDS_PER_SLOT", 3))
    spd = len(cfg.get("SLOTS_PER_DAY", ["m", "a", "e", "n"]))
    return rps * spd


def expected_time_marks(rounds: int, time_cfg: dict | None = None) -> int:
    """预期 TIME_MARK 条数 = [0, rounds) 内 `round % ROUNDS_PER_DAY == 0` 的个数。"""
    rpd = rounds_per_day(time_cfg)
    if rounds <= 0 or rpd <= 0:
        return 0
    return (int(rounds) - 1) // rpd + 1


def log_meta(records) -> dict:
    n_agents = 0
    seed = None
    engine_version = None
    time_model = None
    rounds = set()
    for r in records:
        t = r["type"]
        if t == "WORLD_INIT":
            p = r.get("payload") or {}
            seed = p.get("seed")
            engine_version = p.get("engine_version")
            # T287 期① 起，WORLD_INIT 总带 `time_model`（off=`atomic`）。
            # 更早（分界线 A 前）的日志无此戳 ⇒ None，由消费方按 `atomic` 归并。
            time_model = p.get("time_model")
        elif t == "AGENT_BORN":
            n_agents += 1
        rounds.add(int(r["round"]))
    return {
        "seed": seed,
        "n_agents": n_agents,
        "rounds": (max(rounds) + 1) if rounds else 0,
        "engine_version": engine_version,
        "time_model": time_model,
    }


def type_counts(records) -> dict:
    c: dict[str, int] = {}
    for r in records:
        c[r["type"]] = c.get(r["type"], 0) + 1
    return {k: c[k] for k in sorted(c)}


def compute_baseline(records, baseline_id: str, *, time_cfg: dict | None = None,
                     feature_set: str = "unspecified",
                     min_event_ratio: float = DEFAULT_MIN_EVENT_RATIO,
                     require_zero=DEFAULT_REQUIRE_ZERO,
                     required_nonzero=DEFAULT_REQUIRED_NONZERO) -> dict:
    """从一份已验证良好的日志冻结基线。

    ⚠️ 基线随**功能集**演进更新（如 T39 补实 M3/L5–L7 → 事件量预期上升）；
    更新须在 commit message 说明原因。判定用 **≥ 基线 × min_event_ratio**，
    单调友好：**增长通过、塌陷失败**。
    """
    meta = log_meta(records)
    counts = type_counts(records)
    return {
        "baseline_id": baseline_id,
        "seed": meta["seed"],
        "n_agents": meta["n_agents"],
        "rounds": meta["rounds"],
        "engine_version": meta["engine_version"],
        # 时间模型口径（T339 §4 / 08 §5.10）：跨 sha 自描述，**必须落进元数据**——
        # 分界线只写文档不够，否则将来仍会把两套曲线画在一起。缺戳（旧日志）⇒ `atomic`。
        "time_model": meta["time_model"] or "atomic",
        "feature_set": feature_set,
        "n_events": sum(counts.values()),
        "type_counts": counts,
        "time_mark_expected": expected_time_marks(meta["rounds"], time_cfg),
        "min_event_ratio": float(min_event_ratio),
        "require_zero": list(require_zero),
        "required_nonzero": list(required_nonzero),
        "source": "frozen from a verified-good run log",
        "update_policy": ("基线随功能集演进更新；事件量增长应通过（≥基线×ratio），"
                          "塌陷才失败；更新须在 commit message 说明原因。"),
    }


BASELINE_POLICY = {
    "rule": "event_total >= baseline * min_event_ratio（单调友好：增长通过、塌陷失败）",
    "time_mark": "TIME_MARK == ceil(rounds / ROUNDS_PER_DAY)（每跨日一条；停摆最早信号为 =1）",
    "update": "基线随功能集演进更新；更新 golden_baseline.json 须在 commit message 说明原因",
}


def load_baselines() -> dict:
    if BASELINE_PATH.exists():
        with open(BASELINE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_baselines(data: dict) -> None:
    data = dict(data)
    data["_policy"] = dict(BASELINE_POLICY)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def auto_match(log_or_meta, baselines: dict | None = None):
    """按 (n_agents, rounds, seed) 匹配基线；无 seed 时退化为 (n_agents, rounds)。

    不按 engine_version 严格匹配：基线为**下界参照**，判据是 `≥ 基线×ratio`，
    版本/功能集演进导致的**增长**应通过。
    """
    baselines = baselines if baselines is not None else load_baselines()
    meta = log_or_meta if isinstance(log_or_meta, dict) else log_meta(log_or_meta)
    for bid in sorted(baselines):
        if bid.startswith("_"):
            continue
        b = baselines[bid]
        if b.get("n_agents") == meta.get("n_agents") and b.get("rounds") == meta.get("rounds"):
            if meta.get("seed") is None or b.get("seed") in (None, meta.get("seed")):
                return b
    return None


__all__ = [
    "BASELINE_PATH", "BASELINE_POLICY", "DEFAULT_MIN_EVENT_RATIO",
    "DEFAULT_REQUIRE_ZERO", "DEFAULT_REQUIRED_NONZERO", "rounds_per_day",
    "expected_time_marks", "log_meta", "type_counts", "compute_baseline",
    "load_baselines", "save_baselines", "auto_match",
]
