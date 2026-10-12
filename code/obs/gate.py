"""复现门禁（CI 硬门禁，v1.2 §6.4 G1–G5 / P0-13）。

观测层可独立断言的门禁：
  - G2a `metrics()` 两次调用的规范 JSON **字节相等**；
  - G2b `semantic_census()` 两次字节相等；
  - G3 计算过程 `llm_calls == 0`；
  - G4 货币守恒不变量成立（由日志折叠）。

重放状态哈希相等（G2c）需内核 `replay`，属测试层（`tests/test_obs_repro_gate.py`），
以免观测层依赖写路径（架构 §1.3）。
"""

from __future__ import annotations

from engine.canon import canonical_json

from .econ import econ_metrics
from .params import DEFAULT_PARAMS, ObsParams
from .reader import ReadOnlyLog
from .report import metrics
from .runtime import llm_calls, reset_llm_calls


def check_metrics_bitwise(log, t=None, time_cfg=None, params: ObsParams | None = None) -> dict:
    params = params or DEFAULT_PARAMS
    a = canonical_json(metrics(log, t, time_cfg, params))
    b = canonical_json(metrics(log, t, time_cfg, params))
    return {"name": "metrics_bitwise_equal", "ok": a == b,
            "detail": {"digest": _digest(a)}}


def check_census_bitwise(log, params: ObsParams | None = None) -> dict:
    from .census import semantic_census
    params = params or DEFAULT_PARAMS
    log = log if isinstance(log, ReadOnlyLog) else ReadOnlyLog(log)
    a = canonical_json(semantic_census(log.records, params.emergence))
    b = canonical_json(semantic_census(log.records, params.emergence))
    return {"name": "census_bitwise_equal", "ok": a == b, "detail": {"digest": _digest(a)}}


def check_llm_zero(log, t=None, time_cfg=None, params: ObsParams | None = None) -> dict:
    params = params or DEFAULT_PARAMS
    before = llm_calls()
    metrics(log, t, time_cfg, params)
    after = llm_calls()
    return {"name": "llm_calls_zero", "ok": after == before == 0,
            "detail": {"before": before, "after": after}}


def check_conservation(log) -> dict:
    log = log if isinstance(log, ReadOnlyLog) else ReadOnlyLog(log)
    eco = econ_metrics(log.records)
    residual = eco["conservation_residual"]
    return {"name": "money_conservation", "ok": residual == 0,
            "detail": {"residual": residual,
                       "money_minted_total": eco["money_minted_total"],
                       "money_burned_total": eco["money_burned_total"],
                       "money_supply": eco["money_supply_final"]}}


def check_llm_judged_zero(log, t=None, time_cfg=None, params: ObsParams | None = None) -> dict:
    params = params or DEFAULT_PARAMS
    snap = metrics(log, t, time_cfg, params)
    n = snap["metrics"]["emergence"]["llm_judged_metric_count"]
    return {"name": "llm_judged_metric_count_zero", "ok": n == 0, "detail": {"count": n}}


def run_gates(log, t=None, time_cfg=None, params: ObsParams | None = None) -> dict:
    """运行观测层门禁，返回 {ok, gates:[...]}。"""
    reset_llm_calls()
def check_distribution(log, baseline, time_cfg=None) -> dict:
    """G6：黄金基线 / 事件量-分布回归门禁。

    动机（Leader 2026-10-10）：一次静默回归——`run --life` 跑完、
    `chain_ok/replay_parity/conservation_ok` 全绿，但世界**停摆**
    （N=20 只产 523 事件、`SYSTEM_ERROR`=83、`MEMORY_WRITE`=0、
    `ACTIVITY_COMPLETED`=0、`TIME_MARK`=1），既有门禁全部漏检。

    断言（baseline 为 `obs.golden.compute_baseline` 产物或 baseline_id）：
      1) 事件总量 ≥ 基线 × `min_event_ratio`（默认 0.8）；
      2) `require_zero` 全为 0（默认 `SYSTEM_ERROR == 0`，硬断言）；
      3) `TIME_MARK == ceil(rounds / ROUNDS_PER_DAY)`（**每跨日一条**，权威口径 08 §1.2-A）。
         ⚠️ 停摆的最早信号是 `TIME_MARK == 1`（连一次日边界都没跨过），
         比事件量更直接地暴露「世界没在推进」——故单列断言。
      4) `required_nonzero` 关键事件族全部 > 0。
    失败时 detail 附「实际 vs 基线」逐类型对照表。
    """
    from .golden import expected_time_marks, type_counts, load_baselines, auto_match

    log = log if isinstance(log, ReadOnlyLog) else ReadOnlyLog(log)
    # 三态解析（fail-loud，T220）：dict(已解析) / "auto"(自动匹配) / "<id>"(显式基线)。
    # **未命中一律 FAIL** —— 不再把「没找到基线」当「基线通过」（假绿）。
    resolved, reason = baseline, None
    if isinstance(baseline, str):
        if baseline == "auto":
            resolved = auto_match(log)
            if resolved is None:
                reason = "baseline_auto_unmatched"
        else:
            resolved = load_baselines().get(baseline)
            if resolved is None:
                reason = "baseline_id_not_found"
    if reason is not None:
        return {"name": "distribution_regression", "ok": False,
                "detail": {"reason": reason, "baseline_arg": baseline,
                           "hint": "未命中黄金基线 = 拒绝通过（fail-loud）；"
                                   "如确实不要分布门禁，请显式 `--baseline none`"}}
    if resolved is None:  # 理论不可达：run_gates 对显式 none 不调用本函数
        return {"name": "distribution_regression", "ok": None,
                "detail": {"reason": "baseline_none_self_managed",
                           "hint": "显式 none 应由 CLI 打印，不应到此处"}}
    baseline = resolved

    actual = type_counts(log.records)
    n_actual = sum(actual.values())
    n_base = int(baseline["n_events"])
    ratio = float(baseline.get("min_event_ratio", 0.8))

    problems = []
    if n_actual < ratio * n_base:
        problems.append(f"事件总量 {n_actual} < {ratio}×基线 {n_base}")

    for t in baseline.get("require_zero", ()):
        c = actual.get(t, 0)
        if c != 0:
            problems.append(f"{t}={c}（要求 0）")

    exp_marks = baseline.get("time_mark_expected")
    if time_cfg is not None:
        exp_marks = expected_time_marks(int(baseline.get("rounds", 0)), time_cfg)
    if exp_marks is not None:
        got = actual.get("TIME_MARK", 0)
        if got != exp_marks:
            problems.append(f"TIME_MARK={got}（预期 {exp_marks} 个日/周边界）")

    for t in baseline.get("required_nonzero", ()):
        if actual.get(t, 0) <= 0:
            problems.append(f"{t}=0（要求 > 0，关键事件族缺失）")

    comparison = _distribution_table(actual, baseline.get("type_counts", {}))
    return {
        "name": "distribution_regression",
        "ok": not problems,
        "detail": {
            "baseline_id": baseline.get("baseline_id"),
            "baseline_feature_set": baseline.get("feature_set"),
            "baseline_engine_version": baseline.get("engine_version"),
            "baseline_note": baseline.get("update_policy"),
            "n_events": n_actual,
            "baseline_n_events": n_base,
            "min_event_ratio": ratio,
            "time_mark_actual": actual.get("TIME_MARK", 0),
            "time_mark_expected": exp_marks,
            "problems": problems,
            "comparison": comparison,
        },
    }


def _distribution_table(actual: dict, base: dict, top: int = 25) -> list:
    keys = sorted(set(actual) | set(base))
    rows = [{"type": k, "actual": actual.get(k, 0), "baseline": base.get(k, 0),
             "delta": actual.get(k, 0) - base.get(k, 0)} for k in keys]
    rows.sort(key=lambda r: (-abs(r["delta"]), r["type"]))
    return rows[:top]


def check_schema_conformance(log) -> dict:
    """G7：事件 schema 合约（15 §5）——**阻塞 FAIL**。

    原则（Leader 裁决）：「缺失/不匹配一律硬报错，不得静默容忍」。
    任一事件缺 15 §5 规定字段 / 锚点悬空即 FAIL，并给出**最小复现**（首例事件
    的 seq/type/field 与 `第 N 行`，以及复现命令）。
    """
    from .atomic import preflight, CensusError
    log = log if isinstance(log, ReadOnlyLog) else ReadOnlyLog(log)
    try:
        preflight(log, strict=True)
        return {"name": "schema_conformance", "ok": True, "detail": {"anomalies": 0}}
    except CensusError as e:
        anomalies = []
        try:
            anomalies = preflight(log, strict=False)
        except Exception:
            anomalies = []
        first = anomalies[0] if anomalies else None
        repro = _repro_hint(first)
        return {
            "name": "schema_conformance",
            "ok": False,
            "detail": {
                "error": str(e),
                "anomalies": len(anomalies),
                "first": first,
                "repro": repro,
                "policy": "缺失/不匹配一律硬报错（Leader 裁决）；修好即转 PASS。",
            },
        }


def _repro_hint(first) -> list:
    if not first:
        return ["python -m obs census --log <LOG>  # 严格模式复现"]
    seq = first.get("seq")
    line = (int(seq) + 1) if seq is not None else None
    return [
        f"日志第 {line} 行（seq={seq}）type={first.get('type')} 缺 {first.get('field') or '锚点'}"
        f"；实际键={first.get('actual_keys')}",
        "python -m obs census --log <LOG>            # 严格模式（默认）即硬报错复现",
        f"sed -n '{line}p' <LOG>                      # 直接查看该事件原始记录",
    ]


def run_gates(log, t=None, time_cfg=None, params: ObsParams | None = None,
              baseline=None, schema_strict: bool = True) -> dict:
    """运行观测层门禁，返回 {ok, gates:[...]}。

    `baseline`：None（显式 none，不含 G6，由 CLI 打印跳过）/ 基线 dict / baseline_id 字符串 / "auto"。
      **fail-loud（T220）**：`"auto"` 未命中或 `id` 不存在 → G6 `ok=False`（拒绝通过）。
      仅**显式** `--baseline none`（= None）才跳过，且必须由 CLI 显式打印。
    `schema_strict`：True（默认）→ 纳入 G7 schema 合约（阻塞 FAIL）。
    """
    reset_llm_calls()
    gates = [
        check_metrics_bitwise(log, t, time_cfg, params),
        check_census_bitwise(log, params),
        check_llm_zero(log, t, time_cfg, params),
        check_llm_judged_zero(log, t, time_cfg, params),
        check_conservation(log),
    ]
    if schema_strict:
        gates.append(check_schema_conformance(log))
    if baseline is not None:
        gates.append(check_distribution(log, baseline, time_cfg))
    # ok：忽略 skipped（ok=None）的门禁
    ok = all(g["ok"] is not False for g in gates)
    return {"ok": ok, "gates": gates}


def _digest(s: str) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


__all__ = [
    "check_metrics_bitwise", "check_census_bitwise", "check_llm_zero",
    "check_conservation", "check_llm_judged_zero", "check_distribution",
    "check_schema_conformance", "run_gates",
]
