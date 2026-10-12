"""M4 分时调度 + M6 预算与可观测降级（T215 骨架）。

红线：**降级必须可观测**（发 `DEGRADE` 事件，禁止静默变差）。
设计依据：`v2/refs/scale-50-efficiency.md` §3（M4）/§5（M6）。

- M6：按**仿真日**从 `LLM_CALL` 事件折叠 token 用量，超阈（L1 80% / L2 100% / L3 150%）
  或 `judge` 超日 cap → 级位上升时发一条 `DEGRADE{level,rule,...}`（单调；由 fold 记入 `state.budget_level`）。
- M4：峰值削平原语 `schedule_llm_agents`（≤Kc，优先级 + 确定性错峰），纯函数。
"""

from __future__ import annotations

from .canon import hash_obj
from .constants import PHASE_COMMIT
from .events import spec
from .time import derive_time

_RULE = {1: "judge_sample", 2: "model_downgrade", 3: "critical_only"}


def _budget_cfg(config) -> dict:
    pol = (config or {}).get("policy", {}) if isinstance(config, dict) else {}
    b = pol.get("llm_budget", {}) if isinstance(pol, dict) else {}
    return b if isinstance(b, dict) else {}


def sim_day(round_no: int, config=None) -> int:
    tcfg = (config or {}).get("time_config") if isinstance(config, dict) else None
    return int(derive_time(int(round_no), tcfg)["day"])


def daily_token_usage(state, day: int, config=None) -> int:
    from .event_acc import recs_of_type  # T295：读路径增量聚合（等价全表扫）
    tot = 0
    for rec in recs_of_type(state, "LLM_CALL"):
        if sim_day(rec.get("round", 0), config) != day:
            continue
        p = rec.get("payload", {}) or {}
        tot += int(p.get("tokens_in", 0) or 0) + int(p.get("tokens_out", 0) or 0)
    return tot


def daily_judge_calls(state, day: int, config=None) -> int:
    from .event_acc import recs_of_type  # T295：读路径增量聚合（等价全表扫）
    n = 0
    for rec in recs_of_type(state, "LLM_CALL"):
        if sim_day(rec.get("round", 0), config) != day:
            continue
        if (rec.get("payload", {}) or {}).get("purpose") == "judge":
            n += 1
    return n


def degrade_level(state, round_no: int, config=None) -> int:
    cfg = _budget_cfg(config)
    if not cfg.get("enabled", False):
        return 0
    budget = int(cfg.get("daily_token_budget", 0) or 0)
    day = sim_day(round_no, config)
    usage = daily_token_usage(state, day, config)
    ratio_bp = (usage * 10000 // budget) if budget > 0 else 0
    lvl = 0
    if ratio_bp >= int(cfg.get("l1_ratio_bp", 8000)):
        lvl = 1
    if ratio_bp >= int(cfg.get("l2_ratio_bp", 10000)):
        lvl = 2
    if ratio_bp >= int(cfg.get("l3_ratio_bp", 15000)):
        lvl = 3
    cap = int(cfg.get("judge_daily_cap", 0) or 0)
    if cap > 0 and daily_judge_calls(state, day, config) > cap and lvl < 2:
        lvl = 2  # judge 超日 cap → 至少 L2
    return lvl


def degrade_specs(state, round_no: int, config=None) -> list:
    """级位**上升**时发一条 DEGRADE（可观测）；否则返回 []。"""
    lvl = degrade_level(state, round_no, config)
    if lvl <= int(getattr(state, "budget_level", 0) or 0):
        return []
    day = sim_day(round_no, config)
    return [spec(round_no, PHASE_COMMIT, "SYSTEM", "DEGRADE", {
        "level": lvl, "rule": _RULE.get(lvl, ""), "day": day,
        "tokens_used": daily_token_usage(state, day, config),
        "budget": int(_budget_cfg(config).get("daily_token_budget", 0) or 0),
    })]


# ---------------- M4：分时调度原语 ----------------
def _offset(agent_id: str, round_no: int) -> int:
    """确定性错峰偏移（规范哈希，无随机/墙钟）。"""
    return int(hash_obj({"r": int(round_no), "a": str(agent_id)})[7:19], 16)


# ---------------- M6：critical-only 的可列判定（T215 (a)） ----------------
def critical_dimensions(config) -> set:
    cfg = _budget_cfg(config)
    return {str(d) for d in (cfg.get("critical_dimensions") or [])}


def is_critical_dimension(dimension, config) -> bool:
    return str(dimension) in critical_dimensions(config)


def should_skip_judgment(dimension, level: int, config) -> bool:
    """L3 只保 critical 维度；L1/L2 不在此跳过（分别由 freeze 抽样/降模型执行）。

    **保守默认**：若 `critical_dimensions` 未配置（空）→ **一律不跳过**（宁可少降级，
    也不"悄悄把判定全砍掉"）；待与 T213 对齐维度价值表后填入。"""
    if int(level) < 3:
        return False
    crit = critical_dimensions(config)
    if not crit:
        return False  # 无表 → 不跳（保守）
    return str(dimension) not in crit


def skip_spec(round_no: int, dimension, parties, rule: str = "critical_only") -> "object":
    """逐判定**可列**的可观测记录（DEGRADE 的 skipped 明细，而非仅计数）。"""
    return spec(round_no, PHASE_COMMIT, "SYSTEM", "DEGRADE", {
        "level": 3, "rule": rule, "action": "skip_judgment",
        "skipped": [{"dimension": str(dimension),
                     "parties": sorted(parties or []),
                     "round": int(round_no)}],
    })


def should_skip_importance(level: int, config) -> bool:
    """`importance` 不走 `LLM_JUDGMENT.dimension`（另一条轴）→ 单独键 `critical_importance`。

    L3 且 `critical_importance=false` 时跳过；缺省 `false`/缺键 → **保守不跳**。"""
    if int(level) < 3:
        return False
    cfg = _budget_cfg(config)
    return not bool(cfg.get("critical_importance", False))


def schedule_skip_spec(state, round_no: int, config, priority=None):
    """M4「不可静默」：`schedule_enabled` 且本轮有 agent 未被许可 → 发一条**可列**的
    `DEGRADE{action:"schedule_skip", round, skipped_agents:[...]}`（每回合一条汇总，防刷屏）。"""
    cfg = _budget_cfg(config)
    if not cfg.get("schedule_enabled", False):
        return None
    kc = int(cfg.get("max_concurrency_kc", 0) or 0)
    ids = sorted(state.agents)
    pri = priority or (lambda _a: 0)
    permit = set(schedule_llm_agents(ids, round_no, kc, priority=pri))
    skipped = [a for a in ids if a not in permit]
    if not skipped:
        return None
    return spec(round_no, PHASE_COMMIT, "SYSTEM", "DEGRADE", {
        "action": "schedule_skip", "round": int(round_no),
        "level": int(getattr(state, "budget_level", 0) or 0),
        "skipped_agents": skipped})


def schedule_llm_agents(agents, round_no: int, kc: int, priority=None) -> list:
    """把本回合允许调用 LLM 的 agent 限到 ≤`kc`（峰值削平）。

    纯函数、确定性：先按 `(priority desc, agent_id asc)` 取前 `kc` 个许可，
    再按确定性 `offset` 排序返回启动序。`priority(agent_id)->int` 缺省全 0。
    """
    ids = [a if isinstance(a, str) else getattr(a, "agent_id") for a in agents]
    pri = priority or (lambda _x: 0)
    ranked = sorted(ids, key=lambda x: (-int(pri(x)), str(x)))
    permit = ranked[:max(0, int(kc))]
    return sorted(permit, key=lambda x: (_offset(x, round_no), str(x)))


__all__ = [
    "sim_day", "daily_token_usage", "daily_judge_calls", "degrade_level",
    "degrade_specs", "schedule_llm_agents",
    "critical_dimensions", "is_critical_dimension", "should_skip_judgment", "skip_spec",
    "should_skip_importance", "schedule_skip_spec",
]
