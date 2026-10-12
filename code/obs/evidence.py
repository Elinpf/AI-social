"""证据包构建器：把「只读日志」的报告固化成可归档、可复查的产物。

用法（CLI）：`python -m obs evidence --log <run.jsonl> --out-dir <dir> [--label <id>]`

产出：
  - `metrics.json` / `metrics.md`
  - `census_report.json` / `census_report.md`（15 号规格：原子频次 + 20 类命中 + 未命中 + 覆盖度）
  - `emergence_report.json` / `emergence_report.md`
  - `wellbeing_report.json` / `wellbeing_report.md`
  - `gate.txt`（`obs.gate` 门禁，含 G6）
  - `summary.json`（日志摘要：sha256/事件数/大小/seed/N/rounds/engine_version/守恒/字节相等）
  - `README.md`（索引 + 重现命令）

全部**只读日志**、可复现；F 类单列、不入门禁。
"""

from __future__ import annotations

import json
from pathlib import Path

from . import gate as _gate
from .econ import econ_metrics
from .golden import log_meta
from .reader import ReadOnlyLog
from .report import (
    census_report, emergence_report, metrics, to_canonical, wellbeing_report,
)

SEMANTIC_LABELS_CN = {
    "E1_mentorship": "师徒关系", "E2_gift_giving": "赠礼", "E3_combat_training": "对抗训练",
    "E4_creative_collab": "创作协作", "E5_saving_money": "储蓄", "E6_whispered_comm": "私语",
    "E7_emotion_burnout": "情绪倦怠", "E8_diff_scoring": "差异化评分",
    "E9_scarcity_buy": "稀缺购买", "E10_skill_practice": "技能练习",
    "E11_polite_rejection": "礼貌婉拒", "E12_passion_vs_salary": "热爱vs薪资",
    "E13_group_proposal": "群体提案", "E14_academic_collab": "学术协作",
    "E15_counter_propose": "反提案", "E16_select_location": "场所选择",
    "E17_power_conflict": "权力冲突", "E18_rel_acceptance": "关系接纳",
    "E19_ice_breaking": "破冰", "E20_rel_maintenance": "关系维护",
}


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _md_table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def metrics_md(snap: dict) -> str:
    m = snap["metrics"]
    eco, lc = m["econ"], m["lifecycle"]
    lines = [
        f"# 指标快照 · metrics",
        "",
        f"- round={snap['round']} week={snap['week']} day={snap['day']} "
        f"engine_version=`{snap['engine_version']}`",
        f"- log_hash=`{snap['log_hash']}` log_last_seq={snap['log_last_seq']}",
        f"- 复现：`llm_calls={snap['reproducibility']['llm_calls']}`、"
        f"`llm_judged_metric_count={snap['reproducibility']['llm_judged_metric_count']}`、"
        f"`narrative_reads_in_decision={snap['reproducibility']['narrative_reads_in_decision']}`",
        "",
        "## K 类 · 经济 / 生命周期（口径冻结）",
        "",
        _md_table(["指标", "值"], [
            ["money_supply_final", eco["money_supply_final"]],
            ["money_minted_total", eco["money_minted_total"]],
            ["money_burned_total", eco["money_burned_total"]],
            ["conservation_residual", eco["conservation_residual"]],
            ["conservation_ok", eco["conservation_ok"]],
            ["gini_cash_final", eco["gini_cash_final"]],
            ["n_transfers", eco["n_transfers"]],
            ["transfer_volume", eco["transfer_volume"]],
            ["n_alive_final", lc["n_alive_final"]],
            ["n_dead_final", lc["n_dead_final"]],
            ["survival_rate", lc["survival_rate"]],
            ["death_events", lc["death_events"]],
        ]),
        "",
        "## D 类 · 涌现（摘要）",
        "",
        _md_table(["指标", "值"], [
            ["n_strong_edges", _g(m, "emergence", "relation", "n_strong_edges")],
            ["reciprocity", _g(m, "emergence", "relation", "reciprocity")],
            ["n_communities", _g(m, "emergence", "community", "n_communities")],
            ["modularity_q", _g(m, "emergence", "community", "modularity_q")],
            ["n_norms_adopted", _g(m, "emergence", "norm", "n_norms_adopted")],
            ["n_role_changes", _g(m, "emergence", "role", "n_role_changes")],
            ["n_tags", _g(m, "emergence", "tag", "n_tags")],
            ["observer_injection_count", m["emergence"]["observer_injection_count"]],
            ["llm_judged_metric_count", m["emergence"]["llm_judged_metric_count"]],
        ]),
        "",
        "## 观测偏差自查 / 反作弊",
        "",
        _md_table(["指标", "值"], [
            ["flagged_tx_count", snap["antifraud"]["flagged_tx_count"]],
            ["flags_by_type", json.dumps(snap["antifraud"]["flags_by_type"], ensure_ascii=False)],
        ]),
        "",
        "> F 类（含冻结 LLM 判定）单列于 `metrics.emergence_soft` / `metrics.wellbeing_soft`，"
        "**不进入判定与门禁**。",
        "",
    ]
    return "\n".join(lines)


def _g(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def census_md(rep: dict) -> str:
    lines = [
        "# 事件普查报告（15 号规格）",
        "",
        f"- seed={rep['seed']} rounds={rep['rounds']} weeks={rep['weeks']} N={rep['N']}",
        f"- log_hash=`{rep['log_hash']}` log_last_seq={rep['log_last_seq']} "
        f"engine_version=`{rep['engine_version']}`",
        f"- 复现：`same_log_bitwise={rep['reproducibility']['same_log_bitwise']}`、"
        f"`llm_judged_metric_count={rep['reproducibility']['llm_judged_metric_count']}`、"
        f"`llm_calls={rep['reproducibility']['llm_calls']}`",
        "",
        "## ① 原子事件频次表（Top）",
        "",
        _md_table(["type", "count"],
                  sorted(rep["atomic_freq"].items(), key=lambda kv: (-kv[1], kv[0]))[:25]),
        "",
    ]
    ef = rep.get("economic_family")
    if ef:
        flag = "⚠️ **经济停摆（无任何真实经济活动）**" if not ef.get("is_active") else "✅ 经济在运转"
        lines += [
            "## ①b 经济事件族（单列盯防：本实验核心设定「货币经济激励成长」）",
            "",
            f"- {flag}：`active_total={ef['active_total']}`"
            f"（创世项 `genesis_total={ef['genesis_total']}` 不计入活跃）",
            "",
            _md_table(["type", "count"], sorted(ef["by_type"].items())),
            "",
        ]
    lines += [
        "## ② 20 类语义事件命中表",
        "",
        _md_table(["#", "语义事件", "含义", "hit", "first_round", "participants", "count"],
                  [[k.split("_")[0], k, SEMANTIC_LABELS_CN.get(k, ""),
                    v["hit"], v["first_round"], v["participants"], v["count"]]
                   for k, v in rep["semantic_hits"].items()]),
        "",
        f"## ③ 未命中清单（{len(rep['miss_list'])}）",
        "",
        ("全部 20 类命中 ✅" if not rep["miss_list"]
         else "- " + "\n- ".join(rep["miss_list"])),
        f"\n**难触发项（E4/E8/E12/E13/E17）命中情况**：",
        "",
        _md_table(["难触发项", "hit"],
                  [[k, rep["semantic_hits"][k]["hit"]]
                   for k in ("E4_creative_collab", "E8_diff_scoring",
                             "E12_passion_vs_salary", "E13_group_proposal",
                             "E17_power_conflict")]),
        "",
        "## ④ 覆盖度",
        "",
        _md_table(["项", "值"], [
            ["atomic_types_registered", rep["coverage"]["atomic_types_registered"]],
            ["atomic_types_observed", rep["coverage"]["atomic_types_observed"]],
            ["unknown_types_seen", rep["coverage"]["unknown_types_seen"]],
            ["atomic_registered_unused（前20）",
             ", ".join(rep["coverage"]["atomic_registered_unused"][:20])],
        ]),
        "",
        "## 护栏 / 干预标注",
        "",
        _md_table(["项", "值"], sorted(rep["guard_diagnostics"].items())),
        "",
    ]
    anoms = rep.get("preflight_anomalies") or []
    if anoms:
        lines += [
            f"## ⚠️ 前置异常（{len(anoms)} 处，schema 不合约，15 §5）",
            "",
            "> 严格模式（`strict=True`）下这些会使普查**硬报错**；本报告按非严格模式产出，"
            "结论可用，但该 schema 偏差**须修复来源模块**。",
            "",
            _md_table(["kind", "type", "field/锚", "seq", "实际键"],
                      [[a.get("kind"), a.get("type"),
                        a.get("field") or a.get("target_event_seq") or a.get("effect_ref"),
                        a.get("seq"), ", ".join(a.get("actual_keys", []))]
                       for a in anoms[:30]]),
            "",
        ]
    return "\n".join(lines)


def emergence_md(rep: dict) -> str:
    e = rep["emergence"]
    lines = [
        "# 涌现判定报告 · emergence_report",
        "",
        f"- round={rep['round']} log_hash=`{rep['log_hash']}`",
        f"- `llm_judged_metric_count={rep['reproducibility']['llm_judged_metric_count']}`"
        f"（核心判定 100% 确定性）",
        "",
        "## 关系网络",
        "",
        _md_table(["指标", "值"], sorted(e["relation"].items()
                  )),
        "",
        "## 圈层 / 社区",
        "",
        _md_table(["指标", "值"], [[k, v] for k, v in sorted(e["community"].items())
                                   if k != "communities"]),
        "",
        "## 规范 / 文化",
        "",
        _md_table(["指标", "值"], sorted(e["norm"].items())),
        "",
        "## 职业 / 身份",
        "",
        _md_table(["指标", "值"], [[k, v] for k, v in sorted(e["role"].items())
                                   if k != "transition_matrix"]),
        "",
        "## 传播级联（种子事件 → 自主传播）",
        "",
    ]
    cas = e["cascade"]
    if cas:
        for sid, c in cas.items():
            lines.append(f"- `{sid}`: " + ", ".join(f"{k}={v}" for k, v in c.items()))
    else:
        lines.append("- （本次运行无 SEED_EVENT 种子级联）")
    lines += [
        "",
        "## F 类（冻结 LLM 判定，单列·不入门禁）",
        "",
        f"- `contains_llm_judgment={rep['emergence_soft']['contains_llm_judgment']}`",
        f"- counts_by_dimension={json.dumps(rep['emergence_soft']['counts_by_dimension'], ensure_ascii=False)}",
        "",
    ]
    return "\n".join(lines)


def wellbeing_md(rep: dict) -> str:
    w = rep["wellbeing"]
    lines = [
        "# 幸福感 / 生活质量报告 · wellbeing_report（W1–W7）",
        "",
        f"- round={rep['round']} log_hash=`{rep['log_hash']}`",
        f"- 激励层（经济机制）与观测层（W1–W7）分离；**禁止单一分数优化**",
        "",
        "## 汇总（D 类）",
        "",
        _md_table(["指标", "值"], sorted(w["summary"].items())),
        "",
        "## 背离检测（金钱 ≠ 幸福，D 类可重算）",
        "",
        _md_table(["项", "值"], [
            ["divergence_count", w["divergence"]["divergence_count"]],
            ["divergence_rate", w["divergence"]["divergence_rate"]],
            ["cases", json.dumps(w["divergence"]["cases"], ensure_ascii=False)],
        ]),
        "",
        "## 维度分量键",
        "",
        "- " + "、".join(k for k in w if k.startswith("W")),
        "",
        f"## F 类（W3 主观满足 / W2 互评 / W7 meaning，单列·不入门禁）",
        "",
        f"- `contains_llm_judgment={rep['wellbeing_soft']['contains_llm_judgment']}`",
        f"- subjective_satisfaction={json.dumps(rep['wellbeing_soft']['subjective_satisfaction'], ensure_ascii=False)}",
        f"- meaning_score={json.dumps(rep['wellbeing_soft']['meaning_score'], ensure_ascii=False)}",
        "",
    ]
    return "\n".join(lines)


_WATCH_TYPES = ("MEMORY_WRITE", "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "NEED_UPDATE",
                "RELATION_CHANGE", "TAG_EMITTED", "NORM_PROPOSED", "NORM_ADOPTED",
                "NORM_VIOLATED", "GOAL_SET", "GOAL_PROGRESS", "GOAL_ACHIEVED",
                "SKILL_PRACTICE", "SKILL_LEVEL_UP", "SEED_EVENT")


def build_summary(log_path: Path, log: ReadOnlyLog, snap: dict, gate_res: dict,
                  run_stdout: str | None = None) -> dict:
    raw = log_path.read_bytes()
    import hashlib
    sha = "sha256:" + hashlib.sha256(raw).hexdigest()
    meta = log_meta(log.records)
    eco = snap["metrics"]["econ"]
    a = to_canonical(metrics(log))
    b = to_canonical(metrics(log))
    summary = {
        "log_path": str(log_path),
        "log_label": log_path.name,
        "log_sha256_of_file": sha,
        "log_hash_canonical": log.log_hash(),
        "n_events": len(log.records),
        "log_bytes": len(raw),
        "seed": meta["seed"],
        "n_agents": meta["n_agents"],
        "rounds": meta["rounds"],
        "engine_version": snap["engine_version"],
        "chain_ok": log.chain_ok,
        "conservation_ok": eco["conservation_ok"],
        "conservation_residual": eco["conservation_residual"],
        "metrics_bitwise_equal": a == b,
        "gate_ok": gate_res["ok"],
        "run_stdout": run_stdout,
    }
    from .golden import type_counts
    from .atomic import economic_family
    tc = type_counts(log.records)
    watch = {t: tc.get(t, 0) for t in _WATCH_TYPES}
    summary["event_family_counts"] = watch
    summary["economic_family"] = economic_family(log)
    summary["known_pending_zero"] = [t for t, v in watch.items()
                                     if t in ("TAG_EMITTED", "NORM_PROPOSED", "NORM_ADOPTED",
                                              "NORM_VIOLATED", "GOAL_ACHIEVED") and v == 0]
    return summary


def census_compare_segments_md(segments: list, note: str | None = None) -> str:
    """多段普查对比（Leader 三段协议：pre_life_fix / post_life_fix / +真实 LLM）。

    segments: [{"label": str, "report": census_report_dict, "meta": {...}?}, ...]
    输出：① 20 类命中并排表 ② 经济事件族并排 ③ 总量/耗时/token 汇总。
    """
    labels = [s["label"] for s in segments]
    reports = [s["report"] for s in segments]
    order = reports[-1].get("semantic_order") or sorted(reports[-1]["semantic_hits"])
    rows = []
    for k in order:
        row = [k.split("_")[0], SEMANTIC_LABELS_CN.get(k, "")]
        for r in reports:
            h = r["semantic_hits"].get(k, {})
            row.append("✓" if h.get("hit") else "·")
            row.append(h.get("count", 0))
        rows.append(row)
    headers = ["#", "语义事件"]
    for lb in labels:
        headers += [f"{lb} hit", f"{lb} n"]
    lines = [
        "# 普查并排对比（多段协议）",
        "",
        "控制变量：同 seed / 同 config / 同 rounds，**只变 LLM 提供方 / 接线修复**。",
        "",
    ]
    if note:
        lines += [f"> **根因标注**：{note}", ""]
    lines += [
        "## ① 20 类语义命中（并排）",
        "",
        _md_table(headers, rows),
        "",
        "## ② 经济事件族（单列盯防）",
        "",
    ]
    econ_rows = []
    econ_types = list((reports[-1].get("economic_family") or {}).get("by_type", {}))
    for t in econ_types:
        r = [t]
        for rep in reports:
            r.append((rep.get("economic_family") or {}).get("by_type", {}).get(t, 0))
        econ_rows.append(r)
    econ_rows.append(["**active_total**"] +
                     [ (rp.get("economic_family") or {}).get("active_total", 0) for rp in reports])
    lines += [_md_table(["type"] + labels, econ_rows), ""]
    lines += [
        "## ③ 总量 / 关键族 / 耗时",
        "",
        _md_table(["指标"] + labels, [
            ["n_events"] + [_tot(r) for r in reports],
            ["TAG_EMITTED"] + [_cnt(r, "TAG_EMITTED") for r in reports],
            ["NORM_ADOPTED"] + [_cnt(r, "NORM_ADOPTED") for r in reports],
            ["GOAL_ACHIEVED"] + [_cnt(r, "GOAL_ACHIEVED") for r in reports],
            ["RELATION_CHANGE"] + [_cnt(r, "RELATION_CHANGE") for r in reports],
            ["seconds"] + [ (s.get("meta") or {}).get("seconds", "—") for s in segments],
            ["tokens"] + [ (s.get("meta") or {}).get("tokens", "—") for s in segments],
        ]),
        "",
    ]
    for s in segments:
        r = s["report"]
        hits = sum(1 for v in r["semantic_hits"].values() if v.get("hit"))
        lines.append(f"- {s['label']}：命中 **{hits}/20**；未命中：{', '.join(r.get('miss_list', [])) or '（无）'}")
    lines.append("")
    return "\n".join(lines)


def _cnt(rep: dict, t: str) -> int:
    return rep.get("atomic_freq", {}).get(t, 0)


def _tot(rep: dict) -> int:
    return sum(rep.get("atomic_freq", {}).values())


def census_compare_md(pre: dict, post: dict, pre_label="pre", post_label="post") -> str:
    """两次普查的 20 类命并排对比（Leader 2026-10-10 ⑤：判断世界是否活起来）。"""
    a = pre["semantic_hits"]
    b = post["semantic_hits"]
    rows = []
    for k in post.get("semantic_order", sorted(b)):
        pa, pb = a.get(k, {}), b.get(k, {})
        rows.append([k.split("_")[0], SEMANTIC_LABELS_CN.get(k, ""),
                     pa.get("hit"), pa.get("count"), pb.get("hit"), pb.get("count")])
    hits_a = sum(1 for v in a.values() if v.get("hit"))
    hits_b = sum(1 for v in b.values() if v.get("hit"))
    return "\n".join([
        "# 普查并排对比（20 类语义命中）",
        "",
        f"- {pre_label}：命中 **{hits_a}/20**",
        f"- {post_label}：命中 **{hits_b}/20**",
        "",
        _md_table(["#", "语义事件", f"{pre_label} hit", f"{pre_label} n",
                   f"{post_label} hit", f"{post_label} n"], rows),
        "",
        f"- {pre_label} 未命中：{', '.join(pre.get('miss_list', [])) or '（无）'}",
        f"- {post_label} 未命中：{', '.join(post.get('miss_list', [])) or '（无）'}",
        "",
    ])


def build_evidence(log_path: str | Path, out_dir: str | Path, *,
                   run_stdout: str | None = None, baseline="auto",
                   notes: list | None = None,
                   compare_census: str | Path | None = None,
                   compare_label: str = "pre_life_fix",
                   compare_segments: list | None = None,
                   current_label: str = "post_life_fix",
                   current_meta: dict | None = None,
                   compare_note: str | None = None,
                   archive: str | Path | None = None,
                   archive_sha256: str | None = None,
                   archive_command: str | None = None) -> dict:
    """构建证据包，落盘全部报告与摘要，返回 summary。"""
    log_path = Path(log_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log = ReadOnlyLog(_iter_lines(log_path))
    log.require_chain()

    snap = metrics(log)
    cen = census_report(log, strict=False)          # 非严格：如实记录异常，仍产出结果
    anomalies = cen.get("preflight_anomalies", [])
    emg = emergence_report(log)
    wb = wellbeing_report(log)
    gate_res = _gate.run_gates(log, baseline=baseline)

    _write(out_dir / "metrics.json", to_canonical(snap) + "\n")
    _write(out_dir / "metrics.md", metrics_md(snap))
    _write(out_dir / "census_report.json", to_canonical(cen) + "\n")
    _write(out_dir / "census_report.md", census_md(cen))
    _write(out_dir / "census_anomalies.json",
           json.dumps(anomalies, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _write(out_dir / "emergence_report.json", to_canonical(emg) + "\n")
    _write(out_dir / "emergence_report.md", emergence_md(emg))
    _write(out_dir / "wellbeing_report.json", to_canonical(wb) + "\n")
    _write(out_dir / "wellbeing_report.md", wellbeing_md(wb))

    segs = []
    if compare_segments:
        for s in compare_segments:
            p = Path(s["path"])
            if p.exists():
                segs.append({"label": s.get("label", p.stem),
                             "report": json.loads(p.read_text(encoding="utf-8")),
                             "meta": s.get("meta") or {}})
    elif compare_census and Path(compare_census).exists():
        segs.append({"label": compare_label,
                     "report": json.loads(Path(compare_census).read_text(encoding="utf-8")),
                     "meta": {}})
    if segs:
        segs.append({"label": current_label, "report": cen,
                     "meta": current_meta or {}})
        _write(out_dir / "census_compare.md", census_compare_segments_md(segs, note=compare_note))

    gate_lines = []
    for g in gate_res["gates"]:
        status = "PASS" if g["ok"] else ("SKIP" if g["ok"] is None else "FAIL")
        gate_lines.append(f"[{status}] {g['name']} {json.dumps(g['detail'], ensure_ascii=False)}")
        if g["ok"] is False and g["name"] == "distribution_regression":
            d = g["detail"]
            gate_lines.append(f"  基线：id={d.get('baseline_id')} "
                              f"feature_set={d.get('baseline_feature_set')} "
                              f"engine_version={d.get('baseline_engine_version')}")
            for r in d.get("comparison", []):
                gate_lines.append(f"    {r['type']:<24}{r['actual']:>10}{r['baseline']:>10}{r['delta']:>10}")
        if g["ok"] is False and g["name"] == "schema_conformance":
            for line in g["detail"].get("repro", []):
                gate_lines.append(f"    复现：{line}")
    # 诊断级（不进退出码）—— Fork B：字节相等降诊断；只打印、不判 FAIL
    for dg in gate_res.get("diagnostics", []):
        ds = "PASS" if dg["ok"] else ("SKIP" if dg["ok"] is None else "FAIL")
        gate_lines.append(f"[DIAG] {dg['name']} ok={ds} {json.dumps(dg['detail'], ensure_ascii=False)}")
    gate_lines.append("GATE " + ("PASS" if gate_res["ok"] else "FAIL"))
    _write(out_dir / "gate.txt", "\n".join(gate_lines) + "\n")

    summary = build_summary(log_path, log, snap, gate_res, run_stdout=run_stdout)
    summary["schema_conformance_ok"] = not anomalies
    summary["schema_anomalies"] = anomalies
    if notes:
        summary["notes"] = list(notes)
    # T229：run 归档**只透传记录**（obs 不产归档）；未提供则不写该键（保字节兼容）
    if archive or archive_sha256:
        import hashlib
        sha = archive_sha256
        if sha is None and archive and Path(archive).exists():
            sha = "sha256:" + hashlib.sha256(Path(archive).read_bytes()).hexdigest()
        summary["archive"] = {
            "sha256": sha,
            "ref": (Path(archive).name if archive else None),
            "command": archive_command,
            "in_git": False,
        }
    _write(out_dir / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _write(out_dir / "README.md", readme_md(out_dir, summary))
    return summary


def readme_md(out_dir: Path, summary: dict) -> str:
    s = summary
    log_name = Path(s.get("log_path", "run.jsonl")).name
    lines = [
        "# P0 验收证据包（N=20 单小镇单周）",
        "",
        "> 全部报告**只读日志**产出、可复现；F 类（含 LLM 冻结判定）单列、**不进入门禁**。",
        "",
    ]
    anoms = summary.get("schema_anomalies") or []
    if anoms:
        lines += [
            f"## ⚠️ 已记录的问题（{len(anoms)} 处 schema 不合约，未隐藏）",
            "",
            f"- `schema_conformance_ok=false`：日志中存在事件**缺 15 §5 规定字段**"
            f"（详见 `census_anomalies.json` 与 `census_report.md` 的「前置异常」节）。",
            f"- 影响：**严格普查（`census_report(strict=True)`）会硬报错**；本包按非严格模式"
            f"仍产出 20 类命中表（结论可用），但该 schema 偏差**须由来源模块修复**。",
            f"- 首例：{anoms[0]}",
            "",
        ]
    wf = summary.get("event_family_counts") or {}
    if wf:
        pending = summary.get("known_pending_zero") or []
        lines += [
            "## 事件族计数（真实内核分布，如实列出）",
            "",
            _md_table(["type", "count"], sorted(wf.items(), key=lambda kv: (-kv[1], kv[0]))),
            "",
        ]
        if pending:
            lines += [
                f"**⚠️ 待排查（真内核为 0，mini_kernel 有值）**：`{'`、`'.join(pending)}`"
                " → 已派 life-layer-dev 与 kernel-dev 联合排查；**如实记录、未掩盖**。",
                "",
            ]
    ef = summary.get("economic_family") or {}
    if ef:
        flag = ("⚠️ **经济停摆（无任何真实经济活动）**" if not ef.get("is_active")
                else "✅ 经济在运转")
        lines += [
            "## 经济事件族（单列盯防：货币经济激励成长）",
            "",
            f"- {flag}：`active_total={ef.get('active_total')}`"
            f"（创世项 `genesis_total={ef.get('genesis_total')}` 不计入活跃）",
            "",
            _md_table(["type", "count"],
                      sorted((ef.get("by_type") or {}).items(), key=lambda kv: (-kv[1], kv[0]))),
            "",
        ]
    lines += [
        "## 一、文件清单与用途",
        "> **T63 最终结果（冻结 trunk）见 `ablation_final.md`（A/B1/B2/C 消融 + 归因）与 `gates_final.txt`（四项门禁原始输出）。**",
        "",
        _md_table(["文件", "用途"], [
            ["ablation_final.md", "**T63 最终消融表**：A/B1/B2(N=20,N=10)+C(N=10)，含 state_hash/命中/经济族/生命周期族/死亡错峰/归因"],
            ["gates_final.txt", "**四项门禁原始输出**：pytest / lint-imports / obs gate G1–G7 / make lexicon-gate"],
            ["run_abl_*.jsonl(.summary.json)", "T63 各段日志 + 摘要（A/B1/B2@N=20、A/B1/B2/C@N=10）"],
            ["census_abl_*.json", "T63 各段事件普查（20 类命中）"],
            ["llm_cost_C.json", "C 段真 LLM 成本 by_purpose（含 judge/describe，thinking>0）"],
            [log_name, "**统一运行日志**（JSONL，哈希链，append-only；本包唯一权威事实源）"],
            ["run_stdout.txt", "`orchestration run` 的 stdout（含 seconds / chain_ok / replay_parity / conservation_ok）"],
            ["summary.json", "**日志摘要**：文件 sha256、规范 log_hash、事件数、字节数、seed/N/rounds、engine_version、守恒、字节相等、门禁汇总"],
            ["metrics.json / .md", "确定性指标快照（`metrics`，7 命名空间：econ/lifecycle/life/emergence/emergence_soft/wellbeing/wellbeing_soft）"],
            ["census_report.json / .md", "**事件普查报告**（15 号规格）：① 原子频次表 ② 20 类语义命中表 ③ 未命中清单 ④ 覆盖度"],
            ["census_anomalies.json", "普查前置异常（事件字段不合约；空数组=无异常）"],
            ["census_compare.md", "两次普查的 20 类命中并排对比（世界是否「活起来」）"],
            ["census_report_pre_life_fix.json", "对比用：life 修复前的普查快照（census_compare.md 的基准）"],
            ["run_n10_*.jsonl / census_report_*_n10.json", "三段对比用：N=10 的 rule 对照 与 真实 LLM 段日志+普查（见 census_compare.md）"],
            ["llm_cost_n10.json", "③ 真实 LLM 段的成本：调用次数 + tokens_in/out（来自独立 FREEZE 缓存）"],
            ["emergence_report.json / .md", "涌现判定报告（关系/圈层/规范/职业/传播级联）"],
            ["wellbeing_report.json / .md", "幸福感报告（W1–W7 + 背离检测）"],
            ["gate.txt", "复现门禁 G1–G7 的 PASS/FAIL 输出（含 G6 分布回归、G7 schema 合约）"],
            ["pytest_report.txt", "`pytest -q` 通过数记录（obs 专属 + 全量）"],
        ]),
        "",
        "## 二、如何从零重现（确切命令）",
        "",
        "```bash",
        "# 0) 依赖：Python 3.11+；在 code/ 下运行（conftest 已把 code/ 加入 sys.path）",
        "cd code",
        "",
        "# 1) 生成 N=20 单周日志（seed=42，20 位居民，84 回合）",
        "python -m orchestration run --life --seed 42 --agents 20 --rounds 84 \\",
        "    --out ../v1.2/evidence/run_n20_seed42_week1.jsonl",
        "",
        "# 2) 构建证据包（四类报告 + 门禁 + 摘要 + 本 README）",
        "python -m obs evidence --log ../v1.2/evidence/run_n20_seed42_week1.jsonl \\",
        "    --out-dir ../v1.2/evidence --baseline auto",
        "",
        "# 3) 单独跑复现门禁",
        "python -m obs gate --log ../v1.2/evidence/run_n20_seed42_week1.jsonl --baseline auto",
        "",
        "# 3b) 单独跑普查（本 N=20 日志存在 GOAL_SET 字段不合约：严格模式会硬报错，",
        "#     故证据包用 --non-strict 产出并记录异常；严格模式见 census_report(strict=True)）",
        "python -m obs census --log ../v1.2/evidence/run_n20_seed42_week1.jsonl \\",
        "    --out ../v1.2/evidence/census_report.json --non-strict",
        "",
        "# 4) 测试（obs 专属 + 全量）",
        "python -m pytest -q tests/test_obs_*.py     # obs 专属",
        "python -m pytest -q                          # 全量",
        "```",
        "",
        "## 三、复现证据",
        "",
        f"- **日志指纹**：`log_sha256_of_file={s.get('log_sha256_of_file')}`，"
        f"规范 `log_hash={s.get('log_hash_canonical')}`，事件数 `{s.get('n_events')}`，"
        f"大小 `{s.get('log_bytes')}` 字节（**磁盘实测，权威**）。",
        "- **`log_bytes` 口径**：`summary.log_bytes` = 磁盘实测（**权威**）；"
        "`run_stdout.txt` 里内核自报的 `log_bytes` 为**次要参考**，两者差异"
        "**待 kernel-dev 解释**（可能为「写出字节数 vs 落盘后大小」或含回滚缓冲差异）。",
        f"- **同一日志两次报告字节相等**：`metrics_bitwise_equal={s.get('metrics_bitwise_equal')}`"
        "（`obs` 用规范 JSON：键排序 + 浮点 round(...,6) + 全序 tie-break；"
        "`python -m obs gate` 会独立复算并断言）。",
        f"- **守恒**：`conservation_ok={s.get('conservation_ok')}`（residual={s.get('conservation_residual')}）。",
        f"- **哈希链**：`chain_ok={s.get('chain_ok')}`。",
        f"- **门禁汇总**：`gate_ok={s.get('gate_ok')}`（详见 gate.txt）；"
        "测试通过数见 `pytest_report.txt`（obs 专属 / 全量）。",
        "",
        "## 四、门禁说明（G1–G7）",
        "",
        "- G1 边界：观测层只读白名单（`tests/test_obs_boundary.py`，AST 断言）。",
        "- G2 复现：重放状态哈希相等、`metrics()`/`census` 两次**字节相等**。",
        "- G3 冻结：重放/观测 `llm_calls == 0`；`llm_judged_metric_count == 0`；F 类单列。",
        "- G4 守恒：货币守恒式(1)。",
        "- G5 稳定：无哈希链断裂/无回滚。",
        "- **G6 黄金基线 / 事件量-分布回归**：区分「跑完了」与「真的在运转」——"
        "`SYSTEM_ERROR == 0`；事件量 ≥ 基线×0.8（**增长通过、塌陷失败**）；"
        "`TIME_MARK == ceil(rounds/ROUNDS_PER_DAY)`（84 回合=7，每跨日一条；"
        "**停摆最早信号是 `TIME_MARK=1`**）；关键事件族（MEMORY_WRITE/ACTIVITY_STARTED/"
        "ACTIVITY_COMPLETED/NEED_UPDATE）> 0。基线冻结于 `code/obs/golden_baseline.json`，"
        "随功能集演进更新（更新须在 commit message 说明原因）。",
        "- **G7 schema 合约（阻塞 FAIL）**：任一事件缺 15 §5 规定字段 / 锚点悬空即 FAIL，"
        "并在失败信息给出最小复现（首例事件 seq/type/field + 日志行号 + 复现命令）。"
        "原则：**缺失/不匹配一律硬报错，不得静默容忍**。",
        "",
    ]
    notes = summary.get("notes")
    if notes:
        lines += ["## 五、备注 / 待补", ""] + [f"- {n}" for n in notes] + [""]
    return "\n".join(lines)


def _iter_lines(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


__all__ = ["build_evidence", "build_summary", "metrics_md", "census_md",
           "emergence_md", "wellbeing_md", "readme_md", "census_compare_md"]
