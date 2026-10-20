#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D5/D6 双臂对比器：Δ + 同分母 B2 上界 + band_source + 判定 + 单变量守恒检查。

输入 = 2–3 份 `dialogue_metrics.py` 产出的指标 JSON（角色依次 v0-anchor / A0 / A1）+ B2 带 JSON。
输出 = 规范 JSON + Markdown 表（可直接粘进 D6 报告）。

判定规则（leader 裁决，2026-10-20）：
- 阈值只用 B2（同分母上界）。B1 观测差与 `|Δ|>2pp` 已作废。
- B2 退化（两臂恒 0/恒 1）⇒ 改 rule-of-three（0 事件时 95% 上界 ≈ 3/n），band_source=`rule-of-three(3/n)`。
- 分母 < 68 或无同分母档 ⇒ `无可用带`，结论只能写「仅描述」，不得进摘要。
- 两臂分母差 > 30% ⇒ 标 `不可比`。

结构类指标（S/K/F）另做**单变量守恒检查**：
- II-a 可解释的二阶影响（方向与预登记 `expected_direction` 一致）；
- II-b 泄露信号（方向不符或出现在与对话无关的指标上）。

用法：
    python3 tools/d5/compare_arms.py \
        --roles v0-anchor:v2/evidence/d5_metrics_v0anchor.json \
                A0:v2/evidence/d5_metrics_a0.json \
                A1:v2/evidence/d5_metrics_a1.json \
        --band v2/evidence/d5_noiseband_bootstrap_t300_t355.json \
        --out-json v2/evidence/d6_compare.json --out-md v2/evidence/d6_compare.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = "d6-compare/1.0"

# (名称, 取值路径, 分母来源, B2 键, 类型, 预登记方向)
# 分母来源：per_message / dm_group / threads / pairs / events
SPECS: List[Tuple[str, str, str, Optional[str], str, Optional[str]]] = [
    # ---- 结构层（per-thread）
    ("S-1C 轮数(turn_index 去重) p50", "S-1C_turns_by_turn_index.dist.p50", "threads", None, "struct", "up"),
    ("S-1C 轮数(turn_index 去重) max", "S-1C_turns_by_turn_index.dist.max", "threads", None, "struct", "up"),
    ("S-1A 说话人交替段数 p50", "S-1_turns_per_thread.A_speaker_turns.p50", "threads", None, "struct", "up"),
    ("S-1A 说话人交替段数 max", "S-1_turns_per_thread.A_speaker_turns.max", "threads", None, "struct", "up"),
    ("S-1B 往复对数 p50（仅后臂）", "S-1_turns_per_thread.B_roundtrips.p50", "threads", None, "struct", "up"),
    ("S-2 线程消息数 p50", "S-2_thread_scale.msgs_per_thread.p50", "threads", None, "struct", "up"),
    ("S-2 单条消息线程占比", "S-2_thread_scale.single_msg_thread_ratio", "threads", "thread:single_msg_thread", "struct", "down"),
    ("S-2 单说话人线程占比", "S-2_thread_scale.single_speaker_thread_ratio", "threads", "thread:single_speaker_thread", "struct", "down"),
    ("S-2 多轮线程占比（turns_A≥3）", "S-2_thread_scale.multi_turn_thread_ratio", "threads", "thread:multi_turn_thread", "struct", "up"),
    ("S-3 交替链 p50", "S-3_longest_chain.chain_by_alternation.p50", "threads", None, "struct", "up"),
    ("S-3 交替链 max", "S-3_longest_chain.chain_by_alternation.max", "threads", None, "struct", "up"),
    ("S-3 指针链 max", "S-3_longest_chain.chain_by_pointer.max", "threads", None, "struct", "up"),
    ("S-4 回复指针完整率", "S-4_reply_pointer_coverage.rate", "ptr_nonfirst", None, "struct", "up"),
    ("S-5 孤儿消息率", "S-5_orphan_msg_rate", "per_message", None, "struct", "down"),
    # ---- 话题层（per-adjacent-pair）
    ("K-1 回指承接率", "K-1_topic_continuation.cont_backref", "pairs", "pair:K1_backref", "struct", "up"),
    ("K-1 词汇承接率", "K-1_topic_continuation.cont_lexical", "pairs", "pair:K1_lexical", "struct", "up"),
    ("K-1 同话题率（D2 后可得）", "K-1_topic_continuation.cont_same_topic", "pairs", None, "struct", "up"),
    ("K-1 参考：tag 交集率", "K-1_topic_continuation.tag_overlap_rate_reference", "pairs", "pair:K1_tag", "struct", None),
    # ---- 措辞层（per-message）
    ("L-1 长度 p50", "L_wording.L-1_len.all.p50", "per_message", None, "wording", None),
    ("L-1 去旁白长度 p50", "L_wording.L-1_len.excl_paren.p50", "per_message", None, "wording", None),
    ("L-2 旁白开头率（proxy）", "L_wording.L-2_narration_rate_proxy", "per_message", "item:L-2", "wording", "down"),
    ("L-3 含括号块率", "L_wording.L-3_paren_block_any", "per_message", "item:L-3", "wording", "down"),
    ("L-4 第三人称自述率", "L_wording.L-4_third_person_self_rate", "per_message", None, "wording", "down"),
    ("L-5 模板命中率", "L_wording.L-5_template_hit_rate", "per_message", "item:L-5", "wording", "down"),
    ("L-6 完全重复率", "L_wording.L-6_dup_exact_rate", "per_message", "item:L-6flag", "wording", "down"),
    ("L-7 8-gram 近重复率", "L_wording.L-7_dup_ngram8_rate", "per_message", "item:L-7", "wording", "down"),
    ("L-8 裸内部 ID 率", "L_wording.L-8_agent_id_leak_rate", "per_message", "item:L-8", "wording", "down"),
    ("L-9 元话语率", "L_wording.L-9_meta_talk_rate", "per_message", "item:L-9", "wording", "down"),
    ("L-10 自称错误率", "L_wording.L-10_self_address_error_rate", "per_message", None, "wording", "down"),
    ("L-11 含第二人称率（dm+group）", "L_wording.L-11_second_person_rate_dm_group", "dm_group", "item:L-11", "wording", "up"),
    ("L-12b 对端称呼率（判定用，dm+group）", "L_wording.L-12b_peer_address_rate", "dm_group", "item:L-12", "wording", "up"),
    ("L-12a 对端提及率（描述，dm+group）", "L_wording.L-12_peer_mention_rate", "dm_group", "item:L-12", "wording", "up"),
    ("L-13 token 泄漏率", "L-13_token_leak.token_leak_rate", "per_message", None, "wording", "down"),
    # ---- 生活气息 F 系列
    ("F-1 非功能性闲聊占比", "F-1_chatter.nonfunctional_chatter_rate", "per_message", None, "struct", "up"),
    ("F-2 话题漂移率", "F-2_topic_drift.drift_rate", "pairs", None, "struct", None),
    ("F-2b 多话题线程占比", "F-2_topic_drift.multi_topic_thread_ratio", "threads", None, "struct", "up"),
    ("F-3 情绪呼应率", "F-3_emotion_echo.echo_rate", "events", None, "struct", "up"),
    ("F-4 修复闭环率", "F-4_tension_repair.closed_loop_rate", "events", None, "struct", "up"),
    ("F-5 习惯强度", "F-5_habit_repetition.habit_strength", "threads", None, "struct", None),
    ("F-6 跨天记忆引用率", "F-6_crossday_memory.timeref_rate", "per_message", None, "struct", "up"),
    ("F-7a 越界提及率", "F-7a_offscreen_mention.offscreen_mention_rate", "per_message", None, "struct", "down"),
]

EVENT_DENOM_PATHS = {
    "F-3_emotion_echo.echo_rate": "F-3_emotion_echo.denominator",
    "F-4_tension_repair.closed_loop_rate": "F-4_tension_repair.tension_events",
}


def get(d: Any, path: str) -> Any:
    cur = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def denominator(metrics: Dict[str, Any], src: str, path: str) -> Optional[int]:
    if src == "per_message":
        return get(metrics, "L_wording.denominators.per_message") or get(metrics, "meta.n_messages")
    if src == "dm_group":
        return get(metrics, "L_wording.denominators.dm_group")
    if src == "threads":
        return get(metrics, "L_wording.denominators.threads") or get(metrics, "meta.n_threads")
    if src == "ptr_nonfirst":
        return get(metrics, "S-4_reply_pointer_coverage.denominator_nonfirst_msgs")
    if src == "pairs":
        return get(metrics, "K-1_topic_continuation.denominator_adjacent_pairs")
    if src == "events":
        return get(metrics, EVENT_DENOM_PATHS.get(path, ""))
    return None


def band_for(band_json: Dict[str, Any], key: Optional[str], denom: Optional[int]) -> Tuple[Optional[float], str]:
    """返回 (band 半宽, band_source)。"""
    if key is None or denom is None:
        return None, "无可用带"
    table = (band_json.get("B2_band_by_denom") or {}).get(key)
    if not table:
        return None, "无可用带"
    dens = sorted(int(k) for k in table)
    if denom < min(dens):
        return None, "无可用带"
    m = next((d for d in dens if d >= denom), dens[-1])
    hw = table.get(str(m), {}).get("halfwidth_pp")
    if hw is None:
        return None, "无可用带"
    if hw == 0:
        return round(300.0 / max(denom, 1), 3), "rule-of-three(3/n)"
    return float(hw), f"B2(m={m})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D5/D6 双臂对比器")
    ap.add_argument("--roles", nargs="+", required=True, help="name:path，如 v0-anchor:...json A0:...json")
    ap.add_argument("--band", required=True, help="B2 带 JSON（dialogue_noiseband_bootstrap 产出）")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args(argv)

    arms: Dict[str, Dict[str, Any]] = {}
    for spec in args.roles:
        name, path = spec.split(":", 1)
        arms[name] = json.load(open(path, encoding="utf-8"))
    names = list(arms)
    single = len(names) == 1
    if single:
        print("[info] 单臂「事实对照」模式：只出值 + 分母 + band_source，不出 Δ/判定", file=sys.stderr)
    band_json = json.load(open(args.band, encoding="utf-8"))

    rows: List[Dict[str, Any]] = []
    for label, path, dsrc, bkey, kind, expect in SPECS:
        vals = {n: get(arms[n], path) for n in names}
        if all(v is None for v in vals.values()):
            continue
        denoms = {n: denominator(arms[n], dsrc, path) for n in names}
        row: Dict[str, Any] = {"metric": label, "path": path, "kind": kind,
                               "values": vals, "denominators": denoms,
                               "expected_direction": expect}
        # 以最后一臂 vs 第一臂为主差（D6 主对照 = v0-anchor vs A1）；单臂时跳过
        first, last = names[0], names[-1]
        a, b = vals.get(first), vals.get(last)
        da, db = denoms.get(first), denoms.get(last)
        comparable = True
        if da and db and max(da, db) / max(min(da, db), 1) > 1.30:
            comparable = False
        row["delta_pp"] = None
        if not single and isinstance(a, (int, float)) and isinstance(b, (int, float)):
            row["delta_pp"] = round(100 * (b - a), 3) if abs(a) <= 1 and abs(b) <= 1 else round(b - a, 6)
        hw, src = band_for(band_json, bkey, db or da) if not single else (None, "single-arm")
        row["band_halfwidth"] = hw
        row["band_source"] = src
        row["comparable"] = comparable
        if single:
            row["verdict"] = "事实（单臂，无对照）"
        elif not comparable:
            row["verdict"] = "不可比（分母差>30%）"
        elif hw is None:
            row["verdict"] = "仅描述（无可用带）"
        elif row["delta_pp"] is None:
            row["verdict"] = "仅描述"
        else:
            d = abs(row["delta_pp"])
            row["vs_band"] = round(d / hw, 3) if hw else None
            if d > hw:
                direction_ok = (expect is None) or ((row["delta_pp"] > 0 and expect == "up")
                                                    or (row["delta_pp"] < 0 and expect == "down"))
                row["verdict"] = "带外（结构性变化）" if direction_ok else "带外·方向不符（需回查）"
            else:
                row["verdict"] = "带内（仅印象）"
        # 单变量守恒检查（结构类，A0 vs A1）
        if kind == "struct" and len(names) >= 3:  # 单臂/两臂时无守恒检查列
            a0, a1 = get(arms[names[-2]], path), get(arms[names[-1]], path)
            if isinstance(a0, (int, float)) and isinstance(a1, (int, float)):
                hw2, src2 = band_for(band_json, bkey, denoms.get(names[-1]) or denoms.get(names[-2]))
                delta = round(100 * (a1 - a0), 3) if abs(a0) <= 1 and abs(a1) <= 1 else round(a1 - a0, 6)
                row["conservation"] = {
                    "delta_a0_to_a1": delta, "band_halfwidth": hw2, "band_source": src2,
                    "decision": ("II-a 可解释的二阶影响" if (expect is None or (
                        (delta > 0 and expect == "up") or (delta < 0 and expect == "down") or delta == 0))
                        else "II-b 泄露信号（方向不符，需回查）"),
                }
        rows.append(row)

    res = {"schema_version": SCHEMA, "mode": ("single-arm-facts" if single else "compare"),
           "arms": {n: {"path": p} for n, p in (s.split(":", 1) for s in args.roles)},
           "rules": {"threshold": "B2 同分母上界（B1 与 2pp 已作废）",
                     "degenerate": "两臂恒 0/恒 1 ⇒ rule-of-three(3/n)"
                                   if False else "两臂恒 0/1（band=0）⇒ rule-of-three(3/n)",
                     "incomparable": "分母差>30% ⇒ 不可比",
                     "no_band": "分母<68 或无同分母档 ⇒ 仅描述，不得进摘要"},
           "rows": rows}
    txt = json.dumps(res, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if args.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
        open(args.out_json, "w", encoding="utf-8").write(txt + "\n")

    lines = ["# 双臂对比表（脚本生成，勿手改）\n",
             "> **口径声明**：轮数一律用 `S-1C 轮数(turn_index 去重)`，`S-1A` 是「说话人交替段数」（不等于轮数）；"
             "L-12 判定用 **L-12b 称呼**，L-12a 提及为描述列。**旧版曾把 `L-12=49.8%` 写入本表，该值作废**（成因：GROUP 的 `to` 是 group_id，不可命中项仍留在分母）。\n",
             "- 臂：" + " / ".join(f"`{n}`" for n in names),
             "- 阈值：B2 同分母上界；退化用 rule-of-three；无可用带只作描述\n"]
    for kind, title in (("struct", "结构层 + 生活气息（S/K/F）"), ("wording", "措辞层（L）")):
        subset = [r for r in rows if r["kind"] == kind]
        if not subset:
            continue
        lines += [f"## {title}\n"]
        if single:
            hdr = "| 指标 | 值 | 分母 | band_source | 判定 |"
            lines += [hdr, "|---|---|---|---|---|"]
            for r in subset:
                v = r["values"].get(names[0])
                v = "N/A（该臂无此字段）" if v is None else ("N/A（该口径不适用）" if v == "N/A" else v)
                lines.append(f"| {r['metric']} | {v} | {r['denominators'].get(names[0])} "
                             f"| {r['band_source']} | {r['verdict']} |")
            lines.append("")
            continue
        hdr = "| 指标 | " + " | ".join(names) + " | Δ(首→末) | 分母(末) | B2 上界 | band_source | 判定 |"
        lines += [hdr, "|---|---|" + "---|" * (len(names) + 4)]
        def fmt(v):
            if v is None:
                return "N/A（该臂无此字段）"
            if v == "N/A":
                return "N/A（该口径不适用）"
            return str(v)
        for r in subset:
            cell_vals = " | ".join(fmt(r["values"].get(n)) for n in names)
            lines.append(f"| {r['metric']} | {cell_vals} | {r['delta_pp']} | {r['denominators'].get(names[-1])} "
                         f"| {r['band_halfwidth']} | {r['band_source']} | {r['verdict']} |")
        if kind == "struct" and len(names) >= 3:  # 单臂/两臂时无守恒检查列
            lines += ["\n### 单变量守恒检查（A0 → A1，结构类）\n",
                      "| 指标 | Δ(A0→A1) | B2 上界 | band_source | 判定 |", "|---|---|---|---|---|"]
            for r in subset:
                c = r.get("conservation")
                if not c:
                    continue
                lines.append(f"| {r['metric']} | {c['delta_a0_to_a1']} | {c['band_halfwidth']} | "
                             f"{c['band_source']} | {c['decision']} |")
        lines.append("")
    md = "\n".join(lines)
    if args.out_md:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
        open(args.out_md, "w", encoding="utf-8").write(md + "\n")
    print(json.dumps({"n_rows": len(rows), "out_json": args.out_json, "out_md": args.out_md},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
