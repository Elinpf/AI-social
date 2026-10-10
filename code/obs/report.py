"""观测层入口：metrics / emergence_report / wellbeing_report / census_report。

契约（IF-4 / 07 §0.1）：`metrics(log, T, TIME_CONFIG) = f(EventLog, turn_seal, TIME_CONFIG)`
——只读、纯函数、逐位一致、计算过程 `llm_calls == 0`。

D 类入门禁；F 类（含冻结 LLM 判定）单列 `emergence_soft`/`wellbeing_soft`，
**不进判定/门禁**。
"""

from __future__ import annotations

from engine.canon import canonical_json
from engine.time import derive_time

from . import antifraud
from .atomic import atomic_freq, coverage, economic_family
from .census import SEMANTIC_EVENT_ORDER, semantic_census
from .econ import econ_metrics, lifecycle_metrics
from .emergence import emergence_metrics
from .life import life_metrics
from .params import DEFAULT_PARAMS, ObsParams
from .reader import ReadOnlyLog
from .runtime import LlmCallGuard, llm_calls
from .wellbeing import wellbeing_metrics, wellbeing_soft

SCHEMA_VERSION = "1.1"


def _as_log(log) -> ReadOnlyLog:
    return log if isinstance(log, ReadOnlyLog) else ReadOnlyLog(log)


def _engine_version(log: ReadOnlyLog) -> str:
    for r in log.records:
        if r["type"] == "WORLD_INIT":
            return str((r.get("payload") or {}).get("engine_version", "unknown"))
    return "unknown"


def metrics(log, t: int | None = None, time_cfg: dict | None = None,
            params: ObsParams | None = None) -> dict:
    """IF-4：确定性指标快照（D/K 主 + F 单列）。"""
    log = _as_log(log)
    params = params or DEFAULT_PARAMS
    log.require_chain()
    if t is None:
        t = max(log.max_round(), 0)
    time_cfg = time_cfg or {}
    with LlmCallGuard("metrics"):
        econ = econ_metrics(log.records, params)
        lc = lifecycle_metrics(log.records, params)
        life = life_metrics(log.records)
        emg = emergence_metrics(log.records, params.emergence)
        soft = semantic_census(log.records, params.emergence)["soft"]
        wb = wellbeing_metrics(log.records, params.wellbeing)
        wbs = wellbeing_soft(log.records)

        from .metrics_social import social_metrics, social_soft
        sm = social_metrics(log.records, params.emergence)
        ss = social_soft(log.records)
        from .metrics_econ_loop import econ_loop_metrics
        el = econ_loop_metrics(log.records, params)

        anti = antifraud.analyze(log.records, params.antifraud)
        ie = antifraud.ie_eff(log.records, anti["tx_flags"], params.antifraud)

    tm = derive_time(int(t), time_cfg) if time_cfg.get("ROUNDS_PER_SLOT") else derive_time(int(t))
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "engine_version": _engine_version(log),
        "round": int(t),
        "week": tm["week"],
        "day": tm["day"],
        "day_type": tm["day_type"],
        "log_hash": log.log_hash(),
        "log_last_seq": log.last_seq(),
        "metrics": {
            "econ": econ,
            "lifecycle": lc,
            "life": life,
            "emergence": emg,
            "emergence_soft": soft,
            "wellbeing": wb,
            "wellbeing_soft": wbs,
            "social": sm,
            "social_soft": ss,
            "econ_loop": el,
        },
        "antifraud": {
            "flagged_tx_count": anti["flagged_tx_count"],
            "flags_by_type": anti["flags_by_type"],
            "I_eff": ie,
        },
        "reproducibility": {
            "same_log_bitwise": None,   # 由 gate 填充/断言
            "llm_calls": llm_calls(),
            "llm_judged_metric_count": emg["llm_judged_metric_count"],
            "frozen_llm_metric_count": len(soft.get("counts_by_dimension", {})),
            "contains_frozen_llm": bool(soft.get("contains_llm_judgment")),
            "narrative_reads_in_decision": 0,
        },
    }
    return snapshot


def emergence_report(log, t: int | None = None, params: ObsParams | None = None,
                     time_cfg: dict | None = None) -> dict:
    """涌现判定报告（侧产物，不入世界日志）。"""
    log = _as_log(log)
    params = params or DEFAULT_PARAMS
    log.require_chain()
    if t is None:
        t = max(log.max_round(), 0)
    snap = metrics(log, t, time_cfg, params)
    cen = semantic_census(log.records, params.emergence)
    report = {
        "report": "emergence",
        "schema_version": SCHEMA_VERSION,
        "engine_version": snap["engine_version"],
        "round": snap["round"],
        "log_hash": snap["log_hash"],
        "log_last_seq": snap["log_last_seq"],
        "emergence": snap["metrics"]["emergence"],
        "emergence_soft": snap["metrics"]["emergence_soft"],
        "semantic_hits": cen["semantic_hits"],
        "miss_list": cen["miss_list"],
        "reproducibility": snap["reproducibility"],
        "guard_diagnostics": _guard_diagnostics(log, snap),
    }
    return report


def wellbeing_report(log, t: int | None = None, params: ObsParams | None = None,
                     time_cfg: dict | None = None) -> dict:
    """幸福感 / 生活质量报告（侧产物，不入世界日志）。"""
    log = _as_log(log)
    params = params or DEFAULT_PARAMS
    log.require_chain()
    if t is None:
        t = max(log.max_round(), 0)
    snap = metrics(log, t, time_cfg, params)
    return {
        "report": "wellbeing",
        "schema_version": SCHEMA_VERSION,
        "engine_version": snap["engine_version"],
        "round": snap["round"],
        "log_hash": snap["log_hash"],
        "wellbeing": snap["metrics"]["wellbeing"],
        "wellbeing_soft": snap["metrics"]["wellbeing_soft"],
        "reproducibility": snap["reproducibility"],
        "guard_diagnostics": _guard_diagnostics(log, snap),
    }


def census_report(log, t: int | None = None, params: ObsParams | None = None,
                  time_cfg: dict | None = None, *, repeat_check: bool = True,
                  strict: bool = True) -> dict:
    """事件普查报告（15 §3 格式）。

    `strict=True`（默认）：前置异常（缺字段/锚点悬空）**硬报错**（规格要求）。
    `strict=False`：降级为 `preflight_anomalies` 记录并继续产出（供证据包
    在如实记录问题的同时仍给出普查结果）；未知类型/链断裂仍硬报错。
    """
    from .atomic import preflight
    log = _as_log(log)
    params = params or DEFAULT_PARAMS
    log.require_chain()
    if strict:
        preflight(log)
        anomalies = []
    else:
        anomalies = preflight(log, strict=False)
    if t is None:
        t = max(log.max_round(), 0)

    cen = semantic_census(log.records, params.emergence)
    tm = derive_time(int(t), time_cfg) if (time_cfg and time_cfg.get("ROUNDS_PER_SLOT")) else derive_time(int(t))
    from .econ import rounds_per_week
    rpw = rounds_per_week(time_cfg)
    rounds_elapsed = int(t) + 1                      # 回合计数（0..t）
    weeks_elapsed = (int(t) // rpw) + 1 if rpw else 0
    n_agents = len(set(
        (r.get("payload") or {}).get("agent_id") for r in log.records if r["type"] == "AGENT_BORN"))

    same_bitwise = None
    if repeat_check:
        a = canonical_json(semantic_census(log.records, params.emergence))
        b = canonical_json(semantic_census(log.records, params.emergence))
        same_bitwise = (a == b)

    hits = cen["semantic_hits"]
    report = {
        "schema_version": SCHEMA_VERSION,
        "engine_version": _engine_version(log),
        "seed": log.seed(),
        "rounds": rounds_elapsed,
        "weeks": weeks_elapsed,
        "N": n_agents,
        "log_hash": log.log_hash(),
        "log_last_seq": log.last_seq(),
        "atomic_freq": atomic_freq(log),
        "economic_family": economic_family(log),
        "semantic_hits": hits,
        "miss_list": cen["miss_list"],
        "hard_to_trigger": [k for k in cen["miss_list"]
                            if k in ("E4_creative_collab", "E8_diff_scoring",
                                     "E12_passion_vs_salary", "E13_group_proposal",
                                     "E17_power_conflict")],
        "coverage": coverage(log),
        "preflight_ok": not anomalies,
        "preflight_anomalies": anomalies,
        "reproducibility": {
            "same_log_bitwise": same_bitwise,
            "cross_run_same_seed": False,
            "llm_judged_metric_count": 0,
            "contains_frozen_llm": bool(cen["soft"].get("contains_llm_judgment")),
            "llm_calls": llm_calls(),
        },
        "guard_diagnostics": _guard_diagnostics(log, None),
        "semantic_order": list(SEMANTIC_EVENT_ORDER),
    }
    return report


def _guard_diagnostics(log: ReadOnlyLog, snap) -> dict:
    """护栏 / 干预标注（07 §5.2）。"""
    seed_count = sum(1 for r in log.records if r["type"] == "SEED_EVENT")
    death_count = sum(1 for r in log.records if r["type"] == "AGENT_DIED")
    revived = sum(1 for r in log.records if r["type"] == "AGENT_REVIVED")
    safety_valve = any(
        r["type"] == "LOAN_ISSUED" and (r.get("payload") or {}).get("reason") in
        ("safety_valve", "rescue", "revival")
        for r in log.records)
    guardrail_ok = True
    if snap is not None:
        guardrail_ok = bool(snap["metrics"]["econ"]["conservation_ok"])
    return {
        "observer_injection_count": seed_count,
        "safety_valve_triggered": bool(safety_valve),
        "rescue_flag_count": sum(
            1 for r in log.records
            if (r.get("payload") or {}).get("flag") == "rescue"),
        "guardrail_ok": guardrail_ok,
        "death_count": death_count,
        "revival_count": revived,
    }


def to_canonical(snapshot: dict) -> str:
    """规范化 JSON（字节可比的唯一输出形态）。"""
    return canonical_json(snapshot)


__all__ = [
    "metrics", "emergence_report", "wellbeing_report", "census_report",
    "to_canonical", "SCHEMA_VERSION",
]
