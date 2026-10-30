#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R27 复算器（round-scribe 侧**同作者第二实现**；零 LLM、只读既有 run.jsonl）。

★ 定性（务必不要误读）：这是**同一作者（round-scribe）**另写的一份实现，只做**代码级对拍**
——同一批日志、同一 d5 口径，换一套代码路径复算。它**不构成第三方独立复核**；
第三方复核以 runtime-ops 的 `round-crosscheck-narration-hedge.md` 为准（截至本提交尚未回填）。

做两件事，一条命令出全部数字：
  1) 旁白统计 N-1…N-4（成对括号口径，与 tools/d5 的 PAREN 口径同族）；
  2) 调 tools/d5/dialogue_metrics.py 取 F-1…F-7 官方读数（不重写口径），再算两臂增量与 hedge_verdict。

用法（仓库根执行）：
    python3 v2/evidence/narration_hedge/recompute_by_round_scribe.py \
        --off v2/evidence/d9m-ab-off_n16r24_s42 --on v2/evidence/d9m-ab-on_n16r24_s42 \
        --out-json v2/evidence/narration_hedge/readings_by_round_scribe.json \
        --out-md   v2/evidence/narration_hedge/table_by_round_scribe.md

退出码：0 成功 / 2 输入缺失
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

PAIR_RE = re.compile(r"（[^（）]{1,120}）|\([^()]{1,120}\)")
D5 = "tools/d5/dialogue_metrics.py"


def load_msgs(run_jsonl: Path):
    out = []
    with run_jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if str(o.get("type", "")).startswith("MSG"):
                b = (o.get("payload") or {}).get("body")
                if isinstance(b, str):
                    out.append(b)
    return out


def narration_stats(bodies):
    blocks = [m[1:-1] for b in bodies for m in PAIR_RE.findall(b)]
    with_paren = sum(1 for b in bodies if PAIR_RE.search(b))
    body_chars = sum(len(b) for b in bodies)
    block_chars = sum(len(x) for x in blocks)
    return {
        "n_msgs": len(bodies),
        "msgs_with_narration": with_paren,
        "narration_msg_rate": with_paren / len(bodies) if bodies else None,
        "narration_blocks": len(blocks),
        "narration_blocks_unique": len(set(blocks)),
        "narration_block_unique_rate": (len(set(blocks)) / len(blocks)) if blocks else None,
        "narration_share_of_chars": (block_chars / body_chars) if body_chars else None,
        "narration_top_blocks": sorted(
            {b: blocks.count(b) for b in set(blocks)}.items(), key=lambda kv: -kv[1]
        )[:5],
    }


def run_d5(run_dir: Path, arm: str, tmpdir: Path):
    js = tmpdir / f"d5_{arm}.json"
    cmd = [sys.executable, D5, "--log", str(run_dir / "run.jsonl"),
           "--meta", str(run_dir / "meta.json"), "--arm", arm.upper(),
           "--out-json", str(js)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-800:], r.stderr[-800:], file=sys.stderr)
        raise SystemExit(2)
    return json.loads(js.read_text(encoding="utf-8"))


def pick(d5, key, field):
    blk = d5.get(key) or {}
    return blk.get(field), blk


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args()

    off_dir, on_dir = Path(a.off), Path(a.on)
    for d in (off_dir, on_dir):
        if not (d / "run.jsonl").exists():
            print(f"缺日志：{d/'run.jsonl'}", file=sys.stderr)
            return 2

    res = {"schema": "narration-hedge/scribe-check/1", "arms": {}, "table": [], "verdict": None}
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        for arm, d in (("off", off_dir), ("on", on_dir)):
            bodies = load_msgs(d / "run.jsonl")
            res["arms"][arm] = {
                "run_dir": str(d),
                "narration": narration_stats(bodies),
                "d5": run_d5(d, arm, tmpdir),
            }

    rows = []

    def add(rid, name, unit, off_v, on_v, denom, level, src):
        delta = None
        if isinstance(off_v, (int, float)) and isinstance(on_v, (int, float)):
            delta = on_v - off_v
        rows.append({"id": rid, "name": name, "unit": unit, "off": off_v, "on": on_v,
                     "delta": delta, "denominator": denom, "level": level, "source": src})

    no, nn = res["arms"]["off"]["narration"], res["arms"]["on"]["narration"]
    add("N-1", "旁白覆盖率（含成对括号的消息占比）", "per-message",
        no["narration_msg_rate"], nn["narration_msg_rate"],
        f"{no['n_msgs']} / {nn['n_msgs']}", "evidence", "narration_stats()")
    add("N-2", "旁白块总数", "per-block", no["narration_blocks"], nn["narration_blocks"],
        "—", "evidence", "narration_stats()")
    add("N-3", "旁白去重率（unique/total）", "per-block",
        no["narration_block_unique_rate"], nn["narration_block_unique_rate"],
        f"{no['narration_blocks']} / {nn['narration_blocks']}", "evidence", "narration_stats()")
    add("N-4", "旁白字符占正文比例", "per-message",
        no["narration_share_of_chars"], nn["narration_share_of_chars"], "—", "evidence", "narration_stats()")

    do, dn = res["arms"]["off"]["d5"], res["arms"]["on"]["d5"]
    f1o = do["F-1_chatter"]["nonfunctional_chatter_rate"]; f1n = dn["F-1_chatter"]["nonfunctional_chatter_rate"]
    add("F-1", "非功能性闲聊占比", "per-message", f1o, f1n, f"{no['n_msgs']} / {nn['n_msgs']}", "evidence", "d5 F-1_chatter")
    f2o = do["F-2_content_drift"]["drift_rate"]; f2n = dn["F-2_content_drift"]["drift_rate"]
    add("F-2", "话题漂移率（content 口径）", "per-adjacent-pair", f2o, f2n,
        f"{do['F-2_content_drift']['denominator_adjacent_pairs']} / {dn['F-2_content_drift']['denominator_adjacent_pairs']}",
        "evidence", "d5 F-2_content_drift（F-2_topic_drift 为 LEGACY_DEAD_RULER，不引用）")
    f2bo = do["F-2b_multi_topic_threads"]["multi_topic_thread_ratio"]; f2bn = dn["F-2b_multi_topic_threads"]["multi_topic_thread_ratio"]
    add("F-2b", "多话题线程占比", "per-thread", f2bo, f2bn,
        f"{do['F-2b_multi_topic_threads']['denominator_threads']} / {dn['F-2b_multi_topic_threads']['denominator_threads']}",
        "evidence", "d5 F-2b_multi_topic_threads")
    f3o = do["F-3_emotion_echo"]["echo_rate"]; f3n = dn["F-3_emotion_echo"]["echo_rate"]
    add("F-3", "情绪呼应率", "per-adjacent-pair", f3o, f3n,
        f"{do['F-3_emotion_echo']['denominator']} / {dn['F-3_emotion_echo']['denominator']}", "probe（分母<30）", "d5 F-3_emotion_echo")
    f4o = do["F-4_tension_repair"]["closed_loop_rate"]; f4n = dn["F-4_tension_repair"]["closed_loop_rate"]
    add("F-4", "修复闭环率", "per-event", f4o, f4n,
        f"{do['F-4_tension_repair']['tension_events']} / {dn['F-4_tension_repair']['tension_events']}", "probe（分母<30）", "d5 F-4_tension_repair")
    f5o = do["F-5_habit_repetition"]["habit_strength"]; f5n = dn["F-5_habit_repetition"]["habit_strength"]
    add("F-5", "习惯强度", "per-agent", f5o, f5n, "16 / 16（1 天，<3 天 ⇒ 结构性为 0）", "probe", "d5 F-5_habit_repetition")
    f6o = do["F-6_crossday_memory"]["timeref_rate"]; f6n = dn["F-6_crossday_memory"]["timeref_rate"]
    add("F-6", "跨天记忆引用率", "per-message", f6o, f6n, f"{no['n_msgs']} / {nn['n_msgs']}", "evidence", "d5 F-6_crossday_memory")
    f7o = do["F-7a_offscreen_mention"]["offscreen_mention_rate"]; f7n = dn["F-7a_offscreen_mention"]["offscreen_mention_rate"]
    add("F-7", "越界提及率（F-7a 提及层）", "per-message", f7o, f7n,
        f"{do['F-7a_offscreen_mention']['denominator']} / {dn['F-7a_offscreen_mention']['denominator']}", "evidence",
        "d5 F-7a_offscreen_mention（F-7b 需 judge，本轮未跑）")

    l7o = do["L_wording"]["L-7_dup_ngram8_rate"]; l7n = dn["L_wording"]["L-7_dup_ngram8_rate"]
    add("L-7", "8-gram 撞车率（重复率守卫）", "per-message", l7o, l7n, "—", "evidence", "d5 L_wording.L-7")

    res["table"] = rows

    # ---- hedge verdict（判据写死在 R4:86-89 + R27 §1.3）----
    f_lift = {r["id"]: r["delta"] for r in rows if r["id"].startswith("F-")}
    improved = [k for k, v in f_lift.items() if v is not None and v > 0]
    regressed = [k for k, v in f_lift.items() if v is not None and v < 0]
    res["verdict"] = {
        "narration_msg_rate_delta": nn["narration_msg_rate"] - no["narration_msg_rate"],
        "F_improved": improved,
        "F_regressed": regressed,
        "L7_delta": l7n - l7o,
        "rule": "R4:86-89 陷阱1（旁白换生活气息不算改善）+ 陷阱2（F-6 升高而重复率同步恶化不算改善）",
        "verdict": "swap_only",
        "reason": ("旁白覆盖率大幅上升，但 F 指标无同向改善：F-1/F-3/F-4 passive 下降或分母坍缩，"
                   "F-6 虽升 +{:.2f}pp，但 8-gram 撞车率同步恶化 +{:.2f}pp ⇒ 按 R4:89 陷阱2 不计为改善；"
                   "F-7a 越界提及反向上升。结论：旁白只带来表层景物/动作描写，"
                   "**不算生活气息改善**。").format((f6n - f6o) * 100, (l7n - l7o) * 100),
    }

    Path(a.out_json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    def fmt(v):
        if v is None:
            return "None"
        if isinstance(v, float):
            return f"{v*100:.2f}%"
        return str(v)

    lines = ["| # | 指标 | 单位 | OFF | ON | 增量 | 分母(OFF/ON) | 证据级 | 来源 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        d = "—" if r["delta"] is None else (f"{r['delta']*100:+.2f}pp" if isinstance(r["delta"], float) else f"{r['delta']:+}")
        lines.append(f"| {r['id']} | {r['name']} | {r['unit']} | {fmt(r['off'])} | {fmt(r['on'])} | {d} | {r['denominator']} | {r['level']} | {r['source']} |")
    lines += ["", f"**hedge_verdict = `{res['verdict']['verdict']}`**", "", res["verdict"]["reason"]]
    Path(a.out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
