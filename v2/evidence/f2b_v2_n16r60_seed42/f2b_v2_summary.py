#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-2b 话题展开 · B.4-v2 放量复验（n16r60/seed42）双臂读数 + 判定件生成。

口径单一真源：`tools/d5/dialogue_metrics.py`（不重复实现指标）。
预登记：`v2/refs/prereg-f2b-v2-n16r60.md`（含 §6 修订 R-1/R-2）。

本脚本做四件事：
  1) 调官方复算器取两臂指标，抽 `ctx.topic_breadth` 审计字段算 D / landed / 追加事件；
  2) **双取样**（Leader 2026-10-23T14:48 强制稳健性检验）：
     (a) 主判 = 固定种子系统抽样 30 条（SAMPLING_SEED=20261023，step=N//30，start=Random(seed).randrange(step)）；
     (b) 对照 = 修订前首段方案 `appends[0::step][:30]`（step=N//30）。
     两方案取到的条目**并集**导出成抽样件，人工按 seq 逐条判定；
  3) 若给了人工判定（judgements.json），算两个 precision 并按规则出 verdict.json：
     (a)(b) 结论一致 ⇒ 主判定按 (a)，sampling_sensitivity="insensitive"；
     (a)(b) 结论不一致 ⇒ 主判定 = 不可判，sampling_sensitivity="sensitive"（不得择优取 a）；
     N<30 ⇒ 不可判（样本不足）。四个守卫任一 broken ⇒ 主判定降为不可判（与双取样并列、互不替代）。
  4) 落 `prereg_amendment` 字段（修订时点 / 修订前后 sha256 / 确认人 / 确认消息号）。

用法：
  python3 v2/evidence/f2b_v2_n16r60_seed42/f2b_v2_summary.py \
      --off v2/evidence/f2b_v2_n16r60_seed42/run_off \
      --on  v2/evidence/f2b_v2_n16r60_seed42/run_on \
      --out v2/evidence/f2b_v2_n16r60_seed42/summary.json \
      --sample v2/evidence/f2b_v2_n16r60_seed42/precision_sample.md \
      --sample-json v2/evidence/f2b_v2_n16r60_seed42/precision_sample.json \
      --prereg v2/refs/prereg-f2b-v2-n16r60.md \
      [--judgements .../judgements.json --verdict .../verdict.json]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DM = os.path.join(REPO, "tools", "d5", "dialogue_metrics.py")
MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
SAMPLE_N = 30             # 预登记写死：判定样本固定 30 条
PASS_TRUE = 20            # 预登记写死：真展开 ≥20 条 ⇒ 达标
SAMPLING_SEED = 20261023  # 预登记 §6 R-1：固定种子系统抽样

PREREG_AMENDMENT = {      # Leader 2026-10-23T14:48 要求落盘的修订元数据
    "time": "2026-10-23T14:46:23+08:00",
    "what": "抽样起点 appends[0::step] → 固定种子系统抽样（step=N//30≥2 时 start=Random(SAMPLING_SEED).randrange(step)，index=start+i*step）",
    "denominator_changed": False,
    "pass_line_changed": False,
    "judged_object_changed": False,
    "retroactive": False,
    "confirmed_by": "team-leader",
    "confirm_message_ids": ["0b96afdb-10fd-4e34-9f7d-ac9f48ba47a7", "80c1908b-b314-4be5-9ecd-e8cca0d117b4"],
    "irrelevance_note": "修订时点早于任何判定读数产生（当时 off 43/60、on 未起、零判定读数），故不构成须降级的改口径",
    "sha256_before": "2445aff19d628ba94ac0b0941445fce8fd6b61d7235e99cba86c671256658a7b",
    "sha256_after": "47b5200d5d567498aedacd3f20af226facf17b12e5ddc3802542b50b56e3ae82",
    "sha256_before_how": "append-only 修订 ⇒ 修订前字节 = 当前预登记文件在 '\\n---\\n\\n## 6. 修订记录' 之前的部分，可复算",
    "mtime_after": None,
    "mtime_before_gap": "如实登记：修订前的 mtime 未在修订动作前单独留存（本角色的疏漏），因此只给「修订前字节 sha256」+「修订后 sha256/mtime」，不宣称留存过修订前 mtime",
}

RULES = {
    "main_judgement": "precision = 真展开条数 / 30 ≥ 20 ⇒ 达标；< 20 ⇒ 未达标；判定样本 < 30 ⇒ 不可判（样本不足）",
    "judged_object": "ctx.topic_breadth.landed = true 的消息（R19 §3.2 口径，不是 len(tag_hints)>=2）",
    "sampling_main_a": "固定种子系统抽样：step=N//30；N>=60 时 start=Random(20261023).randrange(step)，index=start+i*step(i=0..29)；30<=N<60 时 step=1，退回首段 30 条并披露前段偏置",
    "sampling_control_b": "修订前首段方案：step=N//30，取 appends[0::step][:30]（seq 最小的 30 条）",
    "sampling_sensitivity": "a/b 结论一致 ⇒ 主判定按 (a)，sampling_sensitivity=insensitive；不一致 ⇒ 主判定必须为不可判，sampling_sensitivity=sensitive，不得择优取 (a)；N<30 ⇒ 不可判（样本不足）",
    "guards": "L-6/L-5/L-7/F-1 基线 = 同批 off 臂；on > off 即 broken。任一 broken ⇒ 主判定降为不可判（与双取样并列、互不替代）",
    "no_retroactive": "不得用本批口径重判 R19 的 8/10（B.4-v2 不回溯）",
}


def run_metrics(log: str) -> dict:
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        subprocess.run([sys.executable, DM, "--log", log, "--out-json", tmp],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(tmp, encoding="utf-8") as fh:
            return json.load(fh)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def arm_stats(arm_dir: str):
    log = os.path.join(arm_dir, "run.jsonl")
    res = run_metrics(log)
    out = {"dir": os.path.relpath(arm_dir, REPO)}
    out["F1_chatter"] = res["F-1_chatter"]["nonfunctional_chatter_rate"]
    out["F2_content_drift"] = res["F-2_content_drift"]
    out["F2_tag_switch"] = res["F-2_tag_switch"]
    out["F2_tag_change_split"] = res["F-2_tag_change_split"]
    out["F2b_multi_topic"] = res["F-2b_multi_topic_threads"]
    out["L13"] = {"n": res["L-13_token_leak"]["n"], "rate": res["L-13_token_leak"]["token_leak_rate"]}
    out["L5_template_hit"] = res["L_wording"]["L-5_template_hit_rate"]
    out["L6_dup_exact"] = res["L_wording"]["L-6_dup_exact_rate"]
    out["L7_dup_ngram8"] = res["L_wording"]["L-7_dup_ngram8_rate"]

    D = through = msgs = 0
    tag_rows: list[dict] = []
    appends: list[dict] = []
    prev_by_thread: dict[str, str] = {}
    with open(log, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("type") not in MSG_TYPES:
                continue
            msgs += 1
            p = r.get("payload") or {}
            th = str(p.get("thread_id") or "")
            prev = prev_by_thread.get(th)
            prev_by_thread[th] = str(p.get("body") or "")
            tb = (p.get("ctx") or {}).get("topic_breadth")
            if not tb:
                continue
            D += 1
            landed = bool(tb.get("landed"))
            if landed:
                through += 1
            tags = list(p.get("tag_hints") or [])
            row = {"seq": r.get("seq"), "round": r.get("round"),
                   "agent": p.get("from") or p.get("author"),
                   "base": tb.get("base"), "shift": tb.get("shift"), "tags": tags,
                   "body": p.get("body"), "thread": p.get("thread_id"),
                   "turn": p.get("turn_index"), "landed": landed, "prev_body": prev}
            if len(tags) >= 2:
                tag_rows.append(row)
            if landed:
                appends.append(row)
    out.update({"msgs": msgs, "D_dispatched": D, "through_landed": through,
                "through_over_D": round(through / D, 6) if D else None,
                "through_over_msgs": round(through / msgs, 6) if msgs else None,
                "tag_appended_events_len2plus": len(tag_rows),
                "landed_events": len(appends),
                "inherited_tag_msgs": len(tag_rows) - len(appends)})
    return out, appends, tag_rows


def sample_a(appends: list[dict]):
    """主判 (a)：固定种子系统抽样（预登记 §6 R-1）。"""
    appends = sorted(appends, key=lambda r: r["seq"])
    n = len(appends)
    meta = {"mode": None, "N": n, "sample_n": SAMPLE_N, "sampling_seed": SAMPLING_SEED,
            "step": None, "start": None, "indices": [], "seqs": [], "bias_disclosed": None}
    if n < SAMPLE_N:
        meta["mode"] = "insufficient"
        return [], f"(a) N={n} < 30 ⇒ **样本不足**（不得用更小分母凑判定）", meta
    step = n // SAMPLE_N
    meta["step"] = step
    if step >= 2:
        start = random.Random(SAMPLING_SEED).randrange(step)
        idx = [start + i * step for i in range(SAMPLE_N)]
        meta.update({"mode": "seeded_systematic", "start": start, "bias_disclosed": False})
        rule = (f"(a) N={n} ⇒ step=floor({n}/30)={step}，start=Random(seed={SAMPLING_SEED}).randrange({step})={start}，"
                f"index=start+i*step (i=0..29) ⇒ 30 条，覆盖 seq {appends[idx[0]]['seq']} … {appends[idx[-1]]['seq']}")
    else:
        idx = list(range(SAMPLE_N))
        meta.update({"mode": "head_fallback", "start": 0, "bias_disclosed": True})
        rule = (f"(a) N={n} ∈ [30,60) ⇒ step=1，无法等间隔覆盖 30 条 ⇒ 退回首段 30 条"
                f"（**前段偏置已披露**，seed={SAMPLING_SEED} 在此档不参与取点）")
    meta["indices"] = idx
    meta["seqs"] = [appends[i]["seq"] for i in idx]
    return [appends[i] for i in idx], rule, meta


def sample_b(appends: list[dict]):
    """对照 (b)：修订前首段方案 appends[0::step][:30]。"""
    appends = sorted(appends, key=lambda r: r["seq"])
    n = len(appends)
    meta = {"mode": None, "N": n, "sample_n": SAMPLE_N, "step": None, "indices": [], "seqs": []}
    if n < SAMPLE_N:
        meta["mode"] = "insufficient"
        return [], f"(b) N={n} < 30 ⇒ 不产出对照样本", meta
    step = n // SAMPLE_N
    picked = appends[0::step][:SAMPLE_N]
    pos = {r["seq"]: i for i, r in enumerate(appends)}
    idx = [pos[r["seq"]] for r in picked]
    meta.update({"mode": "head_prefix", "step": step, "indices": idx,
                 "seqs": [r["seq"] for r in picked]})
    rule = (f"(b) N={n} ⇒ step={step}，取 appends[0::step][:30] ⇒ {len(picked)} 条，"
            f"seq {picked[0]['seq']} … {picked[-1]['seq']}（修订前取点方式，作稳健性对照）")
    return picked, rule, meta


def render_sample(union_rows, rule_a, rule_b, arm):
    lines = ["# F-2b 话题展开 · B.4-v2 precision 判定抽样（n16r60 / seed=42，双取样并集）", "",
             f"> 臂：`{arm}`；判定对象：`ctx.topic_breadth.landed = true` 的消息。",
             f"> {rule_a}", f"> {rule_b}",
             "> 下列为 **(a)∪(b) 并集**：标题里的 `[A]`/`[B]`/`[AB]` 标明该条属于哪个样本（A=主判、B=对照、AB=两者）。",
             "> 判定标准（预登记 §2）：① 接着同线程上一句在说事；② 原话题之外**自然**带出第二个话题线索",
             "> （shift 话题以动作/对象出现在语义主位，不是修饰语、不与动作矛盾）。",
             "> 真展开=true / 假展开=false / 存疑=undecidable（存疑计入分母、不计入真）。",
             "> 判定者：life-spearman（**未参与** code/life/topic_breadth.py 与 agent.py 的话题展开实现），"
             "**非盲**（判定时已见臂名与 D/T/landed 读数）。", ""]
    for i, r in enumerate(union_rows, 1):
        lines += [f"## {i}. seq={r['seq']} round={r['round']} agent={r['agent']} thread={r['thread']} "
                  f"turn={r['turn']} [{r['sample_membership']}]",
                  f"- base（本线程原话题）：`{r['base']}`",
                  f"- shift（下发的相邻话题）：`{r['shift']}`",
                  f"- 日志 tag_hints：`{r['tags']}`",
                  f"- 上一句（同线程）：{r.get('prev_body') or '（本线程首条，无上一句）'}",
                  f"- 本条正文：{r['body']}", ""]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--sample", default=None)
    ap.add_argument("--sample-json", default=None)
    ap.add_argument("--prereg", default=None)
    ap.add_argument("--judgements", default=None)
    ap.add_argument("--verdict", default=None)
    a = ap.parse_args()

    off, _, _ = arm_stats(a.off)
    on, appends, _ = arm_stats(a.on)
    picked_a, rule_a, meta_a = sample_a(appends)
    picked_b, rule_b, meta_b = sample_b(appends)

    seq_a = {r["seq"] for r in picked_a}
    seq_b = {r["seq"] for r in picked_b}
    by_seq = {r["seq"]: r for r in picked_a}
    by_seq.update({r["seq"]: r for r in picked_b})
    union = []
    for s in sorted(seq_a | seq_b):
        row = dict(by_seq[s])
        row["sample_membership"] = "AB" if (s in seq_a and s in seq_b) else ("A" if s in seq_a else "B")
        union.append(row)

    summary = {"prereg": "v2/refs/prereg-f2b-v2-n16r60.md",
               "rules": RULES,
               "sample_a": {"rule": rule_a, "meta": meta_a},
               "sample_b": {"rule": rule_b, "meta": meta_b},
               "union_size": len(union),
               "off_arm": off, "on_arm": on}
    txt = json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(txt + "\n")
    print(txt)
    if a.sample:
        with open(a.sample, "w", encoding="utf-8") as fh:
            fh.write(render_sample(union, rule_a, rule_b, "on（LIFE_PROMPT_TOPIC_BREADTH=1）"))
        print(f"[sample] {a.sample}")
    if a.sample_json:
        tpl = {"judger": "life-spearman（未参与 code/life/topic_breadth.py 与 agent.py 的话题展开实现）",
               "blind": False,
               "blind_note": "非盲：按构造 tag 追加只可能来自 on 臂，臂标签无法隐去；判定时已见臂名与 D/T/landed 读数",
               "criteria": "预登记 v2/refs/prereg-f2b-v2-n16r60.md §2（真展开=true / 假展开=false / 存疑=undecidable）",
               "samples": {"a": meta_a, "b": meta_b},
               "items": [{"idx": i, "seq": r["seq"], "thread": r["thread"], "membership": r["sample_membership"],
                          "base": r["base"], "shift": r["shift"], "prev_body": r.get("prev_body"),
                          "body": r["body"], "judgement": "", "reason": ""} for i, r in enumerate(union, 1)]}
        with open(a.sample_json, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(tpl, ensure_ascii=False, indent=1) + "\n")
        print(f"[sample-json] {a.sample_json}")

    if a.judgements and a.verdict:
        with open(a.judgements, encoding="utf-8") as fh:
            jd = json.load(fh)
        jmap = {int(x["seq"]): x for x in (jd.get("items") or [])}

        def prec(meta):
            idx = meta["indices"]
            seqs = meta["seqs"]
            if meta["mode"] == "insufficient" or len(seqs) < SAMPLE_N:
                return {"n_judged": len(seqs), "n_true": None, "n_false": None, "n_undecidable": None,
                        "verdict": "不可判（样本不足）", "seqs": seqs, "indices": idx}
            js = [jmap.get(s, {}).get("judgement") or "" for s in seqs]
            nt = sum(1 for x in js if x == "true")
            nf = sum(1 for x in js if x == "false")
            nu = sum(1 for x in js if x == "undecidable")
            unfilled = [s for s in seqs if not (jmap.get(s, {}).get("judgement") or "")]
            base = {"n_judged": len(seqs), "n_true": nt, "n_false": nf, "n_undecidable": nu,
                    "seqs": seqs, "indices": idx}
            if unfilled:
                base.update({"verdict": "不可判（判定未填完）", "unjudged_seqs": unfilled})
                return base
            base["verdict"] = "达标" if nt >= PASS_TRUE else "未达标"
            return base

        pa, pb = prec(meta_a), prec(meta_b)
        guards = {}
        for key, label in (("L6_dup_exact", "L-6"), ("L5_template_hit", "L-5"),
                           ("L7_dup_ngram8", "L-7"), ("F1_chatter", "F-1")):
            o, v = off[key], on[key]
            guards[label] = {"off": o, "on": v, "delta": round(v - o, 6), "broken": bool(v > o)}
        broken = [k for k, v in guards.items() if v["broken"]]

        reasons = []
        va, vb = pa["verdict"], pb["verdict"]
        if va.startswith("不可判") or vb.startswith("不可判"):
            sensitivity = "n/a"
            main_verdict = va if va.startswith("不可判") else vb
            reasons.append(f"主判(a)={va} / 对照(b)={vb} ⇒ 不出效果结论")
        elif va == vb:
            sensitivity, main_verdict = "insensitive", va
            reasons.append(f"(a) {pa['n_true']}/{pa['n_judged']} 与对照 (b) {pb['n_true']}/{pb['n_judged']} 结论一致"
                           f"（同为「{va}」）⇒ sampling_sensitivity=insensitive，主判定按 (a)")
        else:
            sensitivity, main_verdict = "sensitive", "不可判"
            reasons.append(f"(a)={va}({pa['n_true']}/30) vs (b)={vb}({pb['n_true']}/30) 结论不一致 ⇒ "
                           f"**结论对取样方式敏感**，主判定必须为不可判，不得择优取 (a)")
        if broken:
            if main_verdict == "不可判" and not main_verdict.endswith("（样本不足）"):
                reasons.append(f"守卫亦被击穿 {broken}（预登记 §4）")
            else:
                main_verdict = "不可判"
                reasons.append(f"守卫被击穿 {broken}（预登记 §4）⇒ 主判定降为不可判")

        amend = dict(PREREG_AMENDMENT)
        if a.prereg and os.path.exists(a.prereg):
            st = os.stat(a.prereg)
            amend["mtime_after"] = datetime.datetime.fromtimestamp(st.st_mtime).isoformat()
            amend["sha256_now"] = hashlib.sha256(open(a.prereg, "rb").read()).hexdigest()

        verdict = {"prereg": summary["prereg"],
                   "scale": {"agents": 16, "rounds": 60, "seed": 42},
                   "code_sha": "a9c74f5",
                   "batch_tree": ".worktrees/f2b-v2-n16r60",
                   "main_HEAD_at_judgement": None,   # 由调用方/判定备忘补写实取值
                   "rules": RULES,
                   "prereg_amendment": amend,
                   "sampling_sensitivity": sensitivity,
                   "sensitivity_power": ("real" if (meta_a["step"] or 0) >= 2 else "structural_only"),
                   "sensitivity_power_note": ("N>=60（step>=2）⇒ 两方案起点可偏移，双取样检验有真实检验力"
                                              if (meta_a["step"] or 0) >= 2 else
                                              "30<=N<60（step=1）⇒ 两方案取点恒同，insensitive 属结构性必然，不构成稳健性支持"),
                   "precision_main_a": pa,
                   "precision_control_b": pb,
                   "pass_line": f"{PASS_TRUE}/30",
                   "judger": jd.get("judger"), "blind": jd.get("blind"), "blind_note": jd.get("blind_note"),
                   "guards": guards, "guards_broken": broken,
                   "main_verdict": main_verdict, "reason": "；".join(reasons),
                   "mechanism": {"D_off": off["D_dispatched"], "D_on": on["D_dispatched"],
                                 "landed_on": on["through_landed"], "T_on": on["through_over_D"],
                                 "msgs_off": off["msgs"], "msgs_on": on["msgs"],
                                 "F2b_off": off["F2b_multi_topic"], "F2b_on": on["F2b_multi_topic"],
                                 "tag_change_split_off": off["F2_tag_change_split"],
                                 "tag_change_split_on": on["F2_tag_change_split"],
                                 "content_drift_off": off["F2_content_drift"],
                                 "content_drift_on": on["F2_content_drift"],
                                 "L13_off": off["L13"], "L13_on": on["L13"]},
                   "readings": {"off": off, "on": on}}
        with open(a.verdict, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(verdict, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        print(f"[verdict] {a.verdict} => {main_verdict}（{verdict['reason']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
