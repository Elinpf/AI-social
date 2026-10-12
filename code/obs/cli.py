"""obs CLI：`python -m obs <cmd>`。

命令：
  metrics           --log LOG [--t T] [--out OUT]     确定性指标快照
  emergence-report  --log LOG [--out OUT]             涌现判定报告
  wellbeing-report  --log LOG [--out OUT]             幸福感报告
  census            --log LOG [--out OUT]             事件普查报告（15 §3）
  gate              --log LOG                          复现门禁（PASS/FAIL）

只读日志：使用标准 json 逐行解析 JSONL，不依赖任何写路径。
"""

from __future__ import annotations

import argparse
import json
import sys

from .reader import ReadOnlyLog
from .report import (
    census_report, emergence_report, metrics, to_canonical, wellbeing_report,
)
from . import gate as _gate


def read_log(path: str) -> list:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _emit(obj: dict, out: str | None, human: str | None = None) -> None:
    text = to_canonical(obj)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"written: {out}")
    else:
        print(text)
    if human:
        print(human, file=sys.stderr)


def _human_census(rep: dict) -> str:
    lines = ["# 事件普查报告", f"rounds={rep['rounds']} weeks={rep['weeks']} N={rep['N']}"]
    lines.append(f"log_hash={rep['log_hash']}")
    lines.append("## 语义命中（20 类）")
    for k, v in rep["semantic_hits"].items():
        mark = "✓" if v["hit"] else "·"
        lines.append(f"  {mark} {k}: hit={v['hit']} first={v['first_round']} "
                     f"participants={v['participants']} count={v['count']}")
    lines.append(f"## 未命中：{rep['miss_list']}")
    lines.append(f"## 覆盖度：{rep['coverage']}")
    return "\n".join(lines)


def _cmd_metrics(args) -> int:
    log = ReadOnlyLog(read_log(args.log))
    rep = metrics(log, args.t, None)
    _emit(rep, args.out)
    return 0


def _cmd_emergence(args) -> int:
    log = ReadOnlyLog(read_log(args.log))
    rep = emergence_report(log, args.t)
    _emit(rep, args.out)
    return 0


def _cmd_wellbeing(args) -> int:
    log = ReadOnlyLog(read_log(args.log))
    rep = wellbeing_report(log, args.t)
    _emit(rep, args.out)
    return 0


def _cmd_census(args) -> int:
    log = ReadOnlyLog(read_log(args.log))
    rep = census_report(log, args.t, strict=not getattr(args, "non_strict", False))
    _emit(rep, args.out, human=_human_census(rep))
    return 0


def _cmd_gate(args) -> int:
    log = ReadOnlyLog(read_log(args.log))
    # 三态（T220）：none（显式跳过，必须打印）/ auto（默认）/ <id>
    if args.baseline == "none":
        baseline = None
        print("[gate] baseline=none（显式跳过分布门禁）")
    else:
        baseline = args.baseline or "auto"
    res = _gate.run_gates(log, args.t, baseline=baseline)
    for g in res["gates"]:
        status = "PASS" if g["ok"] else ("SKIP" if g["ok"] is None else "FAIL")
        print(f"[{status}] {g['name']} {g['detail']}")
        if g["ok"] is False and g["name"] == "distribution_regression":
            d = g["detail"]
            if d.get("reason"):
                print(f"  未命中：reason={d.get('reason')} baseline_arg={d.get('baseline_arg')}")
                print(f"  {d.get('hint')}")
            else:
                print(f"  基线：id={d.get('baseline_id')} feature_set={d.get('baseline_feature_set')} "
                      f"engine_version={d.get('baseline_engine_version')}")
                print(f"  判定：事件量 ≥ 基线×{d.get('min_event_ratio')}（增长应通过、塌陷才失败）")
                _print_distribution_table(d.get("comparison", []))
    print("GATE " + ("PASS" if res["ok"] else "FAIL"))
    return 0 if res["ok"] else 1


def _print_distribution_table(rows) -> None:
    print("  实际 vs 基线（逐类型，|Δ| Top）：")
    print(f"    {'type':<24}{'actual':>10}{'baseline':>10}{'delta':>10}")
    for r in rows:
        print(f"    {r['type']:<24}{r['actual']:>10}{r['baseline']:>10}{r['delta']:>10}")


def _cmd_golden_freeze(args) -> int:
    """从一份已验证良好的日志固化/更新黄金基线。"""
    from .golden import compute_baseline, load_baselines, save_baselines
    recs = read_log(args.log)
    b = compute_baseline(recs, args.baseline_id, min_event_ratio=args.min_ratio,
                         feature_set=args.feature_set)
    data = load_baselines()
    data[args.baseline_id] = b
    save_baselines(data)
    print(f"golden baseline '{args.baseline_id}' frozen: n_events={b['n_events']} "
          f"N={b['n_agents']} rounds={b['rounds']} time_mark_expected={b['time_mark_expected']} "
          f"feature_set={b['feature_set']} engine_version={b['engine_version']}")
    return 0


def _cmd_evidence(args) -> int:
    from .evidence import build_evidence
    run_stdout = None
    if args.run_stdout:
        run_stdout = open(args.run_stdout, "r", encoding="utf-8").read()
    segments = []
    for spec in (args.compare_census or []):
        if "=" in spec:
            label, path = spec.split("=", 1)
        else:
            label, path = spec.rsplit("/", 1)[-1].replace(".json", ""), spec
        segments.append({"label": label, "path": path})
    summary = build_evidence(args.log, args.out_dir, run_stdout=run_stdout,
                             baseline=args.baseline, notes=args.note,
                             compare_segments=segments or None,
                             current_label=args.current_label,
                             compare_note=args.compare_note)
    print(f"evidence written: {args.out_dir}")
    print(f"  events={summary['n_events']} bytes={summary['log_bytes']} "
          f"N={summary['n_agents']} rounds={summary['rounds']} "
          f"chain_ok={summary['chain_ok']} conservation_ok={summary['conservation_ok']} "
          f"bitwise={summary['metrics_bitwise_equal']} gate_ok={summary['gate_ok']} "
          f"economic_active={summary.get('economic_family', {}).get('active_total')}")
    return 0 if summary["gate_ok"] else 1


def _cmd_llm_cost(args) -> int:
    from .llmcost import llm_cost_from_records, freeze_cache_cost, check_provider
    out = {}
    cost = None
    if args.log:
        cost = llm_cost_from_records(read_log(args.log))
        out["engine_log"] = cost
    if args.cache_dir:
        cost = freeze_cache_cost(args.cache_dir)
        out["freeze_cache"] = cost
    rc = 0
    if args.require_provider:
        guard = check_provider(cost or {}, args.require_provider)
        out["provider_guard"] = guard
        rc = 0 if guard["ok"] else 1
    _emit(out, args.out)
    return rc


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="obs", description="涌现观测层 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn in (("metrics", _cmd_metrics), ("emergence-report", _cmd_emergence),
                     ("wellbeing-report", _cmd_wellbeing), ("census", _cmd_census),
                     ("gate", _cmd_gate)):
        sp = sub.add_parser(name)
        sp.add_argument("--log", required=True)
        sp.add_argument("--t", type=int, default=None)
        if name == "gate":
            sp.add_argument("--baseline", default="auto",
                            help="黄金基线：auto（默认，按 N/rounds/seed 匹配）| <id> | none")
        else:
            sp.add_argument("--out", default=None)
        if name == "census":
            sp.add_argument("--non-strict", action="store_true",
                            help="前置异常降级为记录（仍产出），而非硬报错")
        sp.set_defaults(func=fn)

    ev = sub.add_parser("evidence", help="构建证据包（四类报告 + 门禁 + 摘要 + README）")
    ev.add_argument("--log", required=True)
    ev.add_argument("--out-dir", required=True)
    ev.add_argument("--baseline", default="auto")
    ev.add_argument("--run-stdout", default=None,
                    help="orchestration run 的 stdout 文件（记录 seconds/replay_parity 等）")
    ev.add_argument("--note", action="append", default=None,
                    help="写入 README 的备注（可重复）")
    ev.add_argument("--compare-census", action="append", default=None,
                    help="对比用的既往 census_report.json，格式 label=path（可重复，构成多段对比）")
    ev.add_argument("--current-label", default="post_life_fix",
                    help="本次运行在对比表中的段名")
    ev.add_argument("--compare-note", default=None,
                    help="census_compare.md 顶部根因标注")
    ev.set_defaults(func=_cmd_evidence)

    gf = sub.add_parser("golden-freeze", help="从良好日志固化黄金基线（G6）")
    gf.add_argument("--log", required=True)
    gf.add_argument("--baseline-id", required=True)
    gf.add_argument("--min-ratio", type=float, default=0.8)
    gf.add_argument("--feature-set", default="unspecified",
                    help="功能集标识（如 T34-initial / T39-life-full）")
    gf.set_defaults(func=_cmd_golden_freeze)

    lc = sub.add_parser("llm-cost", help="LLM 成本报告（引擎日志 LLM_CALL / freeze 缓存）")
    lc.add_argument("--log", default=None)
    lc.add_argument("--cache-dir", default=None)
    lc.add_argument("--require-provider", default=None,
                    help="缓存污染防护：断言仅由该 provider 服务（如 openai_compat）")
    lc.add_argument("--out", default=None)
    lc.set_defaults(func=_cmd_llm_cost)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
