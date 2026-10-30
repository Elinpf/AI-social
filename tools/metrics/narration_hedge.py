#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""narration_hedge.py —— 旁白（narration）增量 × 生活气息 F-1…F-7 同表联报 + 对冲判决。

背景
----
旁白通道已默认 ON（`code/config/life_v2.json :: prompt.narration.enabled=true`），
但仓库里没有任何工具把「旁白统计」与「生活气息 F 指标」放在同一张表上联报。
reports/R4-life-texture.md:76-78 写死的判据是：**用旁白换生活气息「不算改善」**。
本工具就是那把「并肩闸」尺子：同一份 run 日志上同时给出旁白读数与 F 读数，
并在两臂对照下给出 `hedge_verdict`。

复算命令（一条，仓库根执行；零 LLM、零跑批、不改任何既有文件）
--------------------------------------------------------------
    python3 tools/metrics/narration_hedge.py \
      --log v2/evidence/d9m-ab-off_n16r24_s42 --label OFF \
      --log v2/evidence/d9m-ab-on_n16r24_s42  --label ON \
      --log v2/evidence/round1_narration_default_n16r24_s42 --label ROUND1-default-ON \
      --baseline-arm OFF --treatment-arm ON \
      --out-json v2/evidence/narration_hedge/readings.json \
      --out-md   v2/evidence/narration_hedge/table.md

口径来源（**不重写任何口径**）
------------------------------
* F-1…F-7a：直接调用 `tools/d5/dialogue_metrics.py` 的 `main()`（同一条 CLI 代码路径），
  读它产出的 JSON 块。本工具不含任何 F 指标的重算逻辑。
* 旁白成对括号口径：复用 `tools/d9i/narration_stats.py` 的 `PAIRED_RE` / `ACTION_WORDS`
  / `_is_action`（同一口径，同一份人工动作词表）；并额外用 dialogue_metrics 的
  `L_wording.L-3_paren_block_any` 做第三方交叉核对（两者正则不同，必须同时打印）。
* 「旁白是否顶掉内容」的诊断列 `F_onscreen_only`：把成对括号旁白剥掉后，用**同一个**
  `dialogue_metrics.compute()` 重算 F 表。仅用于检验「F 读数是否本来就长在旁白文字里」，
  是诊断量，不是 headline 读数。

输出
----
* 人读：Markdown 表（旁白读数 / F 读数 / 两臂 delta / 判决）。
* 机读：`--json` 或 `--out-json`，结构见 SCHEMA_VERSION。
* `--json` 时把同一份 JSON 打到 stdout。

退出码：0 成功；2 输入不可用（日志缺失 / 不可解析 / 无 MSG 事件 / 参数自相矛盾）。
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "narration-hedge/1.0"

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
D5_DIR = os.path.join(REPO_ROOT, "tools", "d5")
D9I_DIR = os.path.join(REPO_ROOT, "tools", "d9i")
for _p in (D5_DIR, D9I_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dialogue_metrics as dm  # noqa: E402
import narration_stats as ns  # noqa: E402  （旁白口径的唯一来源；只导入常量与 _is_action）

PAIRED_RE = ns.PAIRED_RE  #: 成对括号旁白正则（与 D9i 同一对象，同一口径）
ANY_RE = ns.ANY_RE        #: 任意左括号口径（辅助对照）

#: F 指标的「生活气息方向」：+1 = 升高为改善，-1 = 下降为改善，0 = 方向不唯一/不作判据
F_DIRECTION = {
    "F-1": +1,    # 非功能性闲聊占比 ↑ = 更多「不为办事说的话」
    "F-2b": +1,   # 多话题线程占比 ↑
    "F-3": +1,    # 情绪呼应率 ↑
    "F-4": +1,    # 修复闭环率 ↑
    "F-5": +1,    # 习惯强度 ↑
    "F-6": +1,    # 跨天记忆引用率 ↑（同时看 L-6/L-7 重复率，见 R4 陷阱 2）
    "F-7a": -1,   # 越界提及率 ↓ = 改善
    "F-2": 0,     # 内容漂移高未必是好事：只报方向，不判好坏
}

#: 参与 hedge 判决的「可判」最小分母（与 R4-life-texture.md 的纪律一致：分母 <30 只报事件数）
MIN_DEN_FOR_VERDICT = 30
#: 判「有改善/有恶化」的最小 delta（百分点计，per-message 类指标）
DELTA_THRESHOLD = 0.02
#: 判「旁白确有增量」的最小旁白覆盖率差
NARRATION_LIFT_THRESHOLD = 0.05
#: 措辞层重复率（L-6/L-7）恶化到多少就按 R4 陷阱 2 取消 F-6 的改善资格
REPEAT_WORSEN_THRESHOLD = 0.02
#: R4-life-texture.md:86-89 三条「不算改善」陷阱的实体行号（leader 更正）
R4_TRAP_LINES = "reports/R4-life-texture.md:86-89"


# ------------------------------------------------------------------ 小工具


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def r6(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(float(x), 6)


def derive_num(rate_val: Optional[float], den: Optional[int]) -> Optional[int]:
    """dialogue_metrics 部分 F 块只给 rate+denominator（如 F-3/F-6）。
    仅在 rate×den 能**精确**还原整数时给 num，否则 None（不猜）。"""
    if rate_val is None or not den:
        return None
    x = float(rate_val) * int(den)
    n = int(round(x))
    return n if abs(x - n) < 1e-4 else None


def resolve_log(path: str) -> Tuple[str, Optional[str]]:
    """--log 既可以是 run.jsonl，也可以是含 run.jsonl/meta.json 的目录。"""
    p = os.path.abspath(path)
    if os.path.isdir(p):
        jsonl = os.path.join(p, "run.jsonl")
        meta = os.path.join(p, "meta.json")
        return jsonl, (meta if os.path.exists(meta) else None)
    return p, (p[:-6] + "meta.json" if p.endswith(".jsonl") and os.path.exists(p[:-6] + "meta.json") else None)


# --------------------------------------------------- 调用既有口径（不重写）


def run_dialogue_metrics(jsonl: str, meta: Optional[str]) -> Dict[str, Any]:
    """走 dialogue_metrics.main() 同一 CLI 代码路径，返回其 JSON。"""
    with tempfile.TemporaryDirectory() as td:
        out_json = os.path.join(td, "metrics.json")
        argv = ["--log", jsonl, "--out-json", out_json]
        if meta:
            argv += ["--meta", meta]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = dm.main(argv)
        if rc != 0:
            raise RuntimeError(f"dialogue_metrics 失败 rc={rc}: {jsonl}")
        with open(out_json, encoding="utf-8") as f:
            return json.load(f)


def load_compute_inputs() -> Dict[str, Any]:
    """与 dialogue_metrics.main() 完全相同的默认词表装载（同一常量、同一文件）。"""
    lexicon = dm.load_lines(dm.DEFAULT_LEXICON) if os.path.exists(dm.DEFAULT_LEXICON) else []
    tmpl_raw = dm.load_lines(dm.DEFAULT_TEMPLATES) if os.path.exists(dm.DEFAULT_TEMPLATES) else []
    templates = [re.compile(t) for t in tmpl_raw if not t.startswith("#")]
    names, _pinfo = dm.load_personas(dm.DEFAULT_PERSONAS)

    def load_words(path: str) -> List[str]:
        if not os.path.exists(path):
            return []
        return [ln.strip() for ln in open(path, encoding="utf-8")
                if ln.strip() and not ln.strip().startswith("#")]

    emotion: Dict[str, int] = {}
    for ln in load_words(dm.DEFAULT_EMOTION):
        parts = ln.split()
        if len(parts) >= 2:
            try:
                emotion[" ".join(parts[1:])] = int(parts[0])
            except ValueError:
                continue
    return {
        "lexicon": lexicon,
        "templates": templates,
        "names": names,
        "extra": {
            "emotion": emotion,
            "repair": load_words(dm.DEFAULT_REPAIR),
            "timeref": load_words(dm.DEFAULT_TIMEREF),
            "task_tags": load_words(dm.DEFAULT_TASK_TAGS),
        },
    }


def f_onscreen_only(jsonl: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """把成对括号旁白剥掉后，用同一个 compute() 重算 F 表（诊断：读数是否长在旁白文字上）。"""
    recs, _parse = dm.read_run(jsonl)
    msgs = dm.extract_messages(recs)
    stripped = []
    for m in msgs:
        m2 = dict(m)
        m2["body"] = dm.strip_paren(m.get("body") or "")
        stripped.append(m2)
    extra = dict(inputs["extra"])
    extra["events"] = recs
    out = dm.compute(stripped, inputs["lexicon"], inputs["templates"], inputs["names"], extra)
    return out


# ------------------------------------------------------------ 旁白读数


def narration_readings(jsonl: str) -> Dict[str, Any]:
    recs, parse = dm.read_run(jsonl)
    msgs = dm.extract_messages(recs)
    n_msg = len(msgs)
    if n_msg == 0:
        raise RuntimeError(f"日志中没有 MSG_DM/MSG_PUBLIC/MSG_GROUP 消息事件: {jsonl}")

    paired_msg = any_msg = 0
    body_chars = onscreen_chars = 0
    blocks_total = 0
    action_blocks = 0
    block_counter: Counter = Counter()
    samples_action: List[str] = []
    samples_other: List[str] = []

    for m in msgs:
        body = m.get("body") or ""
        onscreen = dm.strip_paren(body)
        body_chars += len(body)
        onscreen_chars += len(onscreen)
        blocks = PAIRED_RE.findall(body)
        if blocks:
            paired_msg += 1
            blocks_total += len(blocks)
            for b in blocks:
                inner = b[1:-1]
                block_counter[inner] += 1
                if ns._is_action(inner):
                    action_blocks += 1
                    if len(samples_action) < 6:
                        samples_action.append(inner[:60])
                else:
                    if len(samples_other) < 6:
                        samples_other.append(inner[:60])
        if ANY_RE.search(body):
            any_msg += 1

    def rate(a, b):
        return r6(a / b) if b else None

    unique_blocks = len(block_counter)
    repeat_blocks = sum(1 for v in block_counter.values() if v > 1)
    repeated_occurrences = sum(v for v in block_counter.values() if v > 1)

    return {
        "log": os.path.abspath(jsonl),
        "log_sha256": sha256_file(jsonl),
        "log_parse": parse,
        "denominator_msg_total": n_msg,
        "paired": {
            "regex": PAIRED_RE.pattern,
            "msgs_with_paired_paren": paired_msg,
            "coverage_rate": rate(paired_msg, n_msg),
            "blocks_total": blocks_total,
            "blocks_per_msg": rate(blocks_total, n_msg),
            "unique_blocks": unique_blocks,
            "unique_ratio": rate(unique_blocks, blocks_total),
            "repeat_blocks": repeat_blocks,
            "repeated_occurrences": repeated_occurrences,
            "action_blocks": action_blocks,
            "action_share_of_blocks": rate(action_blocks, blocks_total),
            "top_blocks": [{"inner": k, "count": v} for k, v in block_counter.most_common(8)],
            "samples_action": samples_action,
            "samples_other": samples_other,
        },
        "any_paren": {
            "regex": ANY_RE.pattern,
            "msgs_with_any_open_paren": any_msg,
            "rate": rate(any_msg, n_msg),
        },
        "text_ratio": {
            "body_chars": body_chars,
            "onscreen_chars": onscreen_chars,
            "narration_chars": body_chars - onscreen_chars,
            "narration_char_share": rate(body_chars - onscreen_chars, body_chars),
            "mean_narration_chars_per_msg": rate(body_chars - onscreen_chars, n_msg),
        },
    }


# ------------------------------------------------------------ F 读数表


def f_rows(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """把 dialogue_metrics 的 F 块整理成同表行（只搬运，不重算）。"""
    n_msg = metrics["meta"]["n_messages"]
    n_threads = metrics["meta"]["n_threads"]
    rows: List[Dict[str, Any]] = []

    def add(mid, key, value, num, den, unit, evidence):
        rows.append({"metric": mid, "source_key": key, "value": r6(value), "num": num,
                     "den": den, "unit": unit, "evidence_level": evidence})

    ch = metrics.get("F-1_chatter") or {}
    if ch:
        v = ch.get("nonfunctional_chatter_rate")
        add("F-1", "F-1_chatter.nonfunctional_chatter_rate", v,
            derive_num(v, n_msg), n_msg, "per-message", "evidence")

    cd = metrics.get("F-2_content_drift") or {}
    if cd:
        add("F-2", "F-2_content_drift.drift_rate", cd.get("drift_rate"),
            derive_num(cd.get("drift_rate"), cd.get("denominator_adjacent_pairs")),
            cd.get("denominator_adjacent_pairs"), "per-adjacent-pair", "evidence")

    m2 = metrics.get("F-2b_multi_topic_threads") or {}
    if m2:
        add("F-2b", "F-2b_multi_topic_threads.multi_topic_thread_ratio",
            m2.get("multi_topic_thread_ratio"), m2.get("n_multi_topic_threads"),
            m2.get("denominator_threads"), "per-thread", "evidence")

    e3 = metrics.get("F-3_emotion_echo") or {}
    if e3:
        v = e3.get("echo_rate")
        den = e3.get("denominator")
        add("F-3", "F-3_emotion_echo.echo_rate", v, derive_num(v, den), den,
            "per-adjacent-pair",
            "probe" if (den or 0) < MIN_DEN_FOR_VERDICT else "evidence")

    e4 = metrics.get("F-4_tension_repair") or {}
    if e4:
        v = e4.get("closed_loop_rate")
        den = e4.get("tension_events")
        add("F-4", "F-4_tension_repair.closed_loop_rate", v, derive_num(v, den), den,
            "per-event", "probe" if (den or 0) < MIN_DEN_FOR_VERDICT else "evidence")

    e5 = metrics.get("F-5_habit_repetition") or {}
    if e5:
        v = e5.get("habit_strength")
        add("F-5", "F-5_habit_repetition.habit_strength", v,
            derive_num(v, metrics["meta"].get("n_agents") or 16),
            metrics["meta"].get("n_agents") or 16, "per-agent", "probe")

    e6 = metrics.get("F-6_crossday_memory") or {}
    if e6:
        v = e6.get("timeref_rate")
        add("F-6", "F-6_crossday_memory.timeref_rate", v, derive_num(v, n_msg), n_msg,
            "per-message", "evidence")

    e7 = metrics.get("F-7a_offscreen_mention") or {}
    if e7:
        v = e7.get("offscreen_mention_rate")
        den = e7.get("denominator") or n_msg
        add("F-7a", "F-7a_offscreen_mention.offscreen_mention_rate", v,
            derive_num(v, den), den, "per-message", "evidence")
    rows.append({
        "metric": "F-7b", "source_key": "（仓库内无实现）", "value": None, "num": None,
        "den": None, "unit": "per-message", "evidence_level": "未验证",
        "note": "F-7b 编造事件率无法用规则算，必须 judge 判定；本轮不跑，故恒为 None",
        "missing_premise": {
            "需要什么判据": ("按 F-7 定义（reports/R4-life-texture.md:39-40，F-7 行）：judge 拿到该线程时段内"
                        "**真实发生的事件摘要**，逐条判该消息是否编造了日志中不存在的事件；"
                        "率 = 编造条数 / 受检条数。F-7a 只测『引用了当时不在场的人』（规则可测），"
                        "F-7b 测『引用了不可能知道/不存在的事件』（规则不可测）"),
            "需要什么脚本": ("仓库内**没有** F-7b 实现：tools/metrics 与 tools/d5 下只有规则版 F-7a；"
                        "需新写一个 judge 脚本（读 run.jsonl 抽事件摘要 → 喂 judge → 按 msg_uid 记录判定），"
                        "并遵循团队纪律『真 LLM 调用必须用 obs llm-cost 验证真实性』"),
            "为什么本轮没跑": ("本轮任务书锁死零 LLM、零跑批（只读既有日志）；judge 调用属 LLM 调用，"
                        "因此 F-7b 只能留 None/未验证，不得估算、不得用 F-7a 冒充"),
            "下一轮接手前提": ("新开分支写 judge 脚本 + 选受检样本（可按线程分层）+ obs llm-cost 取证；"
                         "在此之前任何『旁白没有带来编造』的说法都不成立"),
        },
    })

    # 旁白文字是否就是读数来源（诊断列）
    onscreen6 = metrics.get("__onscreen_only__", {}).get("F-6_crossday_memory") or {}
    if onscreen6:
        v = onscreen6.get("timeref_rate")
        add("F-6_onscreen_only", "compute(strip_paren) → F-6_crossday_memory.timeref_rate",
            v, derive_num(v, n_msg), n_msg, "per-message", "diagnostic")
    return rows


def f_value_map(rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    return {r["metric"]: r["value"] for r in rows}


# ------------------------------------------------------------ 判决


def judge(per_arm: Dict[str, Dict[str, Any]], baseline: Optional[str],
          treatment: Optional[str]) -> Dict[str, Any]:
    labels = list(per_arm.keys())
    if len(labels) < 2:
        return {
            "hedge_verdict": "inconclusive",
            "verdict_reason": "只给了 1 份日志：没有旁白开/关两臂，无法判定旁白增量是否换来生活气息。",
            "missing_premises": ["至少两份仅旁白开关不同的可比 run 日志（--baseline-arm / --treatment-arm）"],
            "comparison": None,
        }
    if not baseline or not treatment or baseline not in per_arm or treatment not in per_arm:
        return {
            "hedge_verdict": "inconclusive",
            "verdict_reason": "未指定有效的 --baseline-arm / --treatment-arm（或标签不存在），不做跨臂判决。",
            "missing_premises": ["有效的 --baseline-arm / --treatment-arm 标签"],
            "comparison": None,
        }

    b, t = per_arm[baseline], per_arm[treatment]
    cov_b = b["narration"]["paired"]["coverage_rate"]
    cov_t = t["narration"]["paired"]["coverage_rate"]
    narration_lift = None if (cov_b is None or cov_t is None) else r6(cov_t - cov_b)

    fb = f_value_map(b["f_rows"])
    ft = f_value_map(t["f_rows"])
    numb = {r["metric"]: r["num"] for r in b["f_rows"]}
    numt = {r["metric"]: r["num"] for r in t["f_rows"]}
    lb = b.get("L_wording") or {}
    lt = t.get("L_wording") or {}

    deltas: Dict[str, Dict[str, Any]] = {}
    improvements: List[str] = []
    regressions: List[str] = []
    unjudgeable: Dict[str, str] = {}
    disqualified: Dict[str, List[str]] = {}

    for mid, direction in F_DIRECTION.items():
        if mid not in fb or mid not in ft or fb[mid] is None or ft[mid] is None:
            unjudgeable[mid] = "该臂缺读数（None）"
            continue
        den_b, den_t = b["f_den"].get(mid), t["f_den"].get(mid)
        d = r6(ft[mid] - fb[mid])
        favorable = None if direction == 0 else (d * direction > 0)
        deltas[mid] = {"value_baseline": fb[mid], "value_treatment": ft[mid], "delta": d,
                       "direction": direction, "favorable": favorable,
                       "den_baseline": den_b, "den_treatment": den_t,
                       "num_baseline": numb.get(mid), "num_treatment": numt.get(mid)}
        if direction == 0:
            unjudgeable[mid] = "方向不唯一（漂移高低本身不是好坏判据），只报不判"
            continue
        if (den_b or 0) < MIN_DEN_FOR_VERDICT or (den_t or 0) < MIN_DEN_FOR_VERDICT:
            unjudgeable[mid] = f"分母 <{MIN_DEN_FOR_VERDICT}（b={den_b}, t={den_t}），本规模下不可判"
            continue
        is_improvement = (d >= DELTA_THRESHOLD) if direction > 0 else (d <= -DELTA_THRESHOLD)
        is_regression = (d <= -DELTA_THRESHOLD) if direction > 0 else (d >= DELTA_THRESHOLD)
        if is_regression:
            regressions.append(mid)
            continue
        if not is_improvement:
            continue
        # ---- R4 三条「不算改善」陷阱（reports/R4-life-texture.md:86-89）的前置闸 ----
        dq: List[str] = []
        if mid in ("F-1", "F-6") and (narration_lift or 0) >= NARRATION_LIFT_THRESHOLD:
            dq.append(f"R4 陷阱1（{R4_TRAP_LINES} 第1条）：F-1/F-6 升高**同时**旁白率也升高"
                      f"（旁白 {cov_b}→{cov_t}）⇒ 判为「用旁白换生活气息」，不算改善")
        if mid == "F-6":
            l6b, l6t = lb.get("L-6_dup_exact_rate"), lt.get("L-6_dup_exact_rate")
            l7b, l7t = lb.get("L-7_dup_ngram8_rate"), lt.get("L-7_dup_ngram8_rate")
            l6d = r6(l6t - l6b) if None not in (l6b, l6t) else None
            l7d = r6(l7t - l7b) if None not in (l7b, l7t) else None
            deltas[mid]["L-6_delta"] = l6d
            deltas[mid]["L-7_delta"] = l7d
            worst = max([x for x in (l6d, l7d) if x is not None], default=None)
            if worst is not None and worst >= REPEAT_WORSEN_THRESHOLD:
                dq.append(f"R4 陷阱2（{R4_TRAP_LINES} 第2条）：F-6 升高的同时措辞层重复率恶化"
                          f"（L-6 Δ={l6d}, L-7 Δ={l7d} ≥ {REPEAT_WORSEN_THRESHOLD}）⇒ 不算改善")
        if dq:
            disqualified[mid] = dq
        else:
            improvements.append(mid)

    # 旁白文字本身是否就是读数来源：F-6 剥掉括号后还剩多少 delta
    swap_evidence: Dict[str, Any] = {}
    f6b, f6t = fb.get("F-6"), ft.get("F-6")
    o6b, o6t = fb.get("F-6_onscreen_only"), ft.get("F-6_onscreen_only")
    if None not in (f6b, f6t, o6b, o6t):
        full_delta = f6t - f6b
        onscreen_delta = o6t - o6b
        keep = None if full_delta == 0 else r6(onscreen_delta / full_delta)
        swap_evidence["F-6"] = {
            "delta_full_body": r6(full_delta),
            "delta_onscreen_only": r6(onscreen_delta),
            "share_of_delta_surviving_paren_strip": keep,
            "num_full_body": "%s/%s → %s/%s" % (numb.get("F-6"), b["f_den"].get("F-6"),
                                                numt.get("F-6"), t["f_den"].get("F-6")),
            "num_onscreen_only": "%s/%s → %s/%s" % (numb.get("F-6_onscreen_only"), b["f_den"].get("F-6_onscreen_only"),
                                                    numt.get("F-6_onscreen_only"), t["f_den"].get("F-6_onscreen_only")),
            "explicit_statement": ("剥掉成对括号旁白后，ON 臂 F-6 仍是 %s/%s（OFF 臂 %s/%s），"
                                   "delta 存活比 = %s ⇒ 这次 F-6 的移动**落在台词正文，不在旁白文字本身**；"
                                   "但它与旁白开关同时发生且伴随 L-7 ngram8 重复率恶化，"
                                   "按 reports/R4-life-texture.md:86-89 陷阱1/2 的文字口径仍判『不算改善』"
                                   % (numt.get("F-6_onscreen_only"), t["f_den"].get("F-6_onscreen_only"),
                                      numb.get("F-6_onscreen_only"), b["f_den"].get("F-6_onscreen_only"), keep)),
            "note": ("这是本轮唯一有诊断价值的线索：旁白不是靠『写景物』把 F-6 顶上去的，"
                     "而是改变了台词里对『昨天/上次』的提及；要证实它，需要独立重采样 + F-7b judge，"
                     "本轮两臂均为缓存回放，做不到"),
        }

    missing: List[str] = []
    if narration_lift is None or narration_lift < NARRATION_LIFT_THRESHOLD:
        missing.append(
            f"旁白覆盖率差不足（{cov_b} → {cov_t}，差 {narration_lift} < {NARRATION_LIFT_THRESHOLD}）：两臂旁白没有实质增量")

    verdict: str
    reasons: List[str] = []
    if missing:
        verdict = "inconclusive"
        reasons.extend(missing)
    elif not improvements:
        verdict = "swap_only"
        reasons.append(
            "旁白有实质增量（%s → %s），但去掉 R4 陷阱1/2 后**没有任何可判 F 指标构成同向改善**"
            % (cov_b, cov_t))
        if disqualified:
            reasons.append("被取消改善资格的读数：" + "；".join(
                f"{k}（{' | '.join(v)}）" for k, v in disqualified.items()))
        if regressions:
            reasons.append("另有可判同向恶化：" + "、".join(regressions))
    elif "F-7a" in regressions:
        verdict = "inconclusive"
        reasons.append("可判指标里有改善，但 F-7a（越界提及率）同向恶化：trust 相关维度转差，"
                       "而 F-7b（编造事件）零 LLM 无法判定，故不能宣布 lift_confirmed")
    elif improvements and not regressions:
        swap = swap_evidence.get("F-6") or {}
        keep = swap.get("share_of_delta_surviving_paren_strip")
        if improvements == ["F-6"] and keep is not None and keep < 0.5:
            verdict = "swap_only"
            reasons.append("唯一改善是 F-6，且剥掉旁白后 delta 只剩 %s（<50%%）⇒ 提升长在旁白文字里，属换词" % keep)
        else:
            verdict = "lift_confirmed"
            reasons.append("旁白有实质增量，且可判指标出现同向改善、无同向恶化")
    else:
        verdict = "inconclusive"
        reasons.append("可判指标同时出现改善与恶化，方向不一致")

    # 复现前提：缓存回放 + 缺失前提
    caveats: List[str] = []
    for lab in (baseline, treatment):
        info = per_arm[lab]
        cr = info.get("llm_cached_ratio")
        ct = info.get("cached_over_total")
        if cr is not None and cr >= 0.99:
            caveats.append(f"{lab} 臂 cached/total = {ct}（llm_cached_ratio={cr}）：全部命中缓存，"
                           f"响应是历史真 LLM 产物、本批未重生成 ⇒ 本对照是**两份日志正文的文本统计对比**，"
                           f"不是两次独立采样")
        elif cr is not None:
            caveats.append(f"{lab} 臂 cached/total = {ct}（llm_cached_ratio={cr}）：大部分为缓存回放")
    if unjudgeable:
        caveats.append("不可判维度原因见 unjudgeable")

    significance = {
        "p_value": None,
        "test": None,
        "reason": ("两臂为同一 prompt 集的缓存回放（见 caveats 的 cached/total），非独立重采样，"
                   "样本不满足独立性假设 ⇒ 按纪律不给 p 值/置信区间，任何『显著』说法都不成立"),
    }

    return {
        "hedge_verdict": verdict,
        "verdict_reason": "；".join(reasons),
        "baseline_arm": baseline,
        "treatment_arm": treatment,
        "narration_coverage_baseline": cov_b,
        "narration_coverage_treatment": cov_t,
        "narration_lift": narration_lift,
        "delta_threshold": DELTA_THRESHOLD,
        "judgeable_improvements": improvements,
        "judgeable_regressions": regressions,
        "disqualified": disqualified,
        "unjudgeable": unjudgeable,
        "swap_evidence": swap_evidence,
        "significance": significance,
        "caveats": caveats,
        "missing_premises": missing + [
            "F-7b（编造事件率）需 judge 判定；本工具零 LLM ⇒ 恒为 None/未验证",
            "独立重采样（两臂均为缓存回放，不能支撑显著性/批间方差结论）",
        ],
        "deltas": deltas,
    }


# ------------------------------------------------------------ 渲染


def render_md(res: Dict[str, Any]) -> str:
    L: List[str] = []
    L.append("# 旁白 × 生活气息 F-1…F-7 同表联报（narration_hedge）\n")
    L.append("> 由 `tools/metrics/narration_hedge.py` 生成，零 LLM、零跑批。")
    L.append("> F 指标口径来源：`tools/d5/dialogue_metrics.py`（本工具只搬运，不重算）。")
    L.append("> 判据来源：`reports/R4-life-texture.md:86-89` 三条「不算改善」陷阱"
             "（陷阱1 旁白顶掉生活气息 / 陷阱2 F-6 与重复率 / 陷阱3 编造事件）。\n")

    L.append("## 0. 复算命令\n")
    L.append("```bash")
    L.append(res["recompute_command"])
    L.append("```\n")

    L.append("## 1. 输入日志\n")
    L.append("| 臂 | 日志 | messages | admission | code_sha | cached/total | run_sha256 |")
    L.append("|---|---|---|---|---|---|---|")
    for lab, info in res["arms"].items():
        n = info["narration"]["denominator_msg_total"]
        adm = (info.get("admission") or {}).get("verdict")
        L.append(f"| {lab} | `{os.path.relpath(info['log'], REPO_ROOT)}` | {n} | {adm} | "
                 f"{(info.get('code_sha') or 'None')[:12]} | {info.get('cached_over_total')} | "
                 f"{info['narration']['log_sha256'][:19]}… |")
    L.append("")
    roles = res.get("arms_role") or {}
    refs = [lab for lab, r in roles.items() if r == "reference_only"]
    L.append(f"> 参与判决的臂：baseline=`{roles.get('__baseline__')}` / treatment=`{roles.get('__treatment__')}`"
             f"（唯一差异是旁白开关，code_sha 相同）。")
    if refs:
        L.append(f"> **仅作参照读数、不作为对照、不参与判决**："
                 + "、".join(f"`{x}`（code_sha 与两臂不同，非同一开关对，不能当第三臂）" for x in refs) + "。")
    L.append("")

    L.append("## 2. 旁白读数（成对括号口径，与 D9i 同口径）\n")
    L.append("| 臂 | 覆盖率(条) | 括号块数 | 去重后唯一块 | 唯一率 | 重复块(≥2次) | 动作类占比 | 旁白字数占正文 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for lab, info in res["arms"].items():
        p = info["narration"]["paired"]
        tr = info["narration"]["text_ratio"]
        L.append(f"| {lab} | {p['msgs_with_paired_paren']}/{info['narration']['denominator_msg_total']}"
                 f" = {p['coverage_rate']} | {p['blocks_total']} | {p['unique_blocks']} | "
                 f"{p['unique_ratio']} | {p['repeat_blocks']} | {p['action_share_of_blocks']} | "
                 f"{tr['narration_char_share']} |")
    L.append("")

    L.append("## 3. F-1…F-7 同表读数\n")
    metric_order = ["F-1", "F-2", "F-2b", "F-3", "F-4", "F-5", "F-6", "F-6_onscreen_only", "F-7a", "F-7b"]
    labels = list(res["arms"].keys())
    L.append("| 指标 | " + " | ".join(labels) + " | 单位 | 证据级 |")
    L.append("|---|" + "---|" * len(labels) + "---|---|")
    for mid in metric_order:
        cells, unit, ev = [], None, None
        for lab in labels:
            row = next((r for r in res["arms"][lab]["f_rows"] if r["metric"] == mid), None)
            if row is None:
                cells.append("None"); continue
            unit = unit or row["unit"]
            ev = ev or row["evidence_level"]
            if row["value"] is None:
                cells.append("None")
            elif row["num"] is not None and row["den"]:
                cells.append(f"{row['num']}/{row['den']} = {row['value']}")
            else:
                cells.append(f"{row['value']}（/{row['den']}）")
        L.append(f"| {mid} | " + " | ".join(cells) + f" | {unit} | {ev} |")
    L.append("")
    L.append("> `F-6_onscreen_only` = 剥掉成对括号旁白后用同一 `compute()` 重算的 F-6，"
             "用于判断 F-6 提升是否长在旁白文字上（诊断列，不作 headline）。")
    swap6 = (res["judgement"].get("swap_evidence") or {}).get("F-6") or {}
    if swap6.get("explicit_statement"):
        L.append(f"> **F-6 诊断（唯一有价值的线索）**：{swap6['explicit_statement']}")
    L.append("> **`F-7b` 为什么是 None**：F-7b 测「编造了日志中不存在的事件」，规则不可测，必须 judge "
             "（拿到该线程时段真实事件摘要逐条判，率 = 编造条数/受检条数）；仓库内没有该脚本，"
             "且本轮锁死零 LLM ⇒ 只能留 None/未验证。下一轮接手需要：新写 judge 脚本 + 选受检样本 + "
             "`obs llm-cost` 取证；在此之前「旁白没有带来编造」不成立。")
    L.append("> delta 表的「方向有利」只表示数值方向，是否算改善还要过 §4 的 R4 陷阱闸（见 disqualified）。\n")

    j = res["judgement"]
    L.append("## 4. 对冲判决\n")
    L.append(f"- **hedge_verdict = `{j['hedge_verdict']}`**")
    L.append(f"- 依据：{j['verdict_reason']}")
    if j.get("comparison") is not None or j.get("deltas"):
        L.append(f"- baseline=`{j.get('baseline_arm')}`，treatment=`{j.get('treatment_arm')}`，"
                 f"旁白覆盖率 {j.get('narration_coverage_baseline')} → {j.get('narration_coverage_treatment')}"
                 f"（lift={j.get('narration_lift')}）")
        L.append(f"- 可判改善：{j.get('judgeable_improvements') or '无'}；"
                 f"可判恶化：{j.get('judgeable_regressions') or '无'}")
        L.append(f"- 不可判：{json.dumps(j.get('unjudgeable'), ensure_ascii=False)}")
        if j.get("disqualified"):
            L.append("- 被 R4 陷阱取消改善资格：")
            for k, v in j["disqualified"].items():
                for one in v:
                    L.append(f"  - {k}：{one}")
        if j.get("significance"):
            sig = j["significance"]
            L.append(f"- 显著性：p_value = {sig.get('p_value')}（不可算原因：{sig.get('reason')}）")
        if j.get("swap_evidence"):
            L.append(f"- swap 证据：{json.dumps(j['swap_evidence'], ensure_ascii=False)}")
    if j.get("caveats"):
        L.append("- 复现前提/告警：")
        for c in j["caveats"]:
            L.append(f"  - {c}")
    if j.get("missing_premises"):
        L.append("- 缺失前提：")
        for m in j["missing_premises"]:
            L.append(f"  - {m}")
    L.append("")

    if j.get("deltas"):
        L.append("## 5. 两臂 delta（treatment − baseline）\n")
        L.append("| 指标 | baseline | treatment | 分子(b/t) | delta | 方向 | 方向有利(未过R4闸) | 分母(b/t) |")
        L.append("|---|---|---|---|---|---|---|---|")
        for mid, d in j["deltas"].items():
            L.append(f"| {mid} | {d['value_baseline']} | {d['value_treatment']} | "
                     f"{d.get('num_baseline')}/{d.get('num_treatment')} | {d['delta']} | "
                     f"{d['direction']} | {d['favorable']} | {d['den_baseline']}/{d['den_treatment']} |")
        L.append("")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------ 主流程


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="旁白统计 × F-1…F-7 同表联报 + 对冲判决（零 LLM）")
    ap.add_argument("--log", action="append", required=True,
                    help="run.jsonl 或包含 run.jsonl/meta.json 的 run 目录；可重复")
    ap.add_argument("--label", action="append", default=None,
                    help="与 --log 一一对应的臂标签；缺省用目录名")
    ap.add_argument("--baseline-arm", default=None, help="旁白关闭臂的标签")
    ap.add_argument("--treatment-arm", default=None, help="旁白开启臂的标签")
    ap.add_argument("--json", action="store_true", help="把机读 JSON 打到 stdout")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args(argv)

    if args.label and len(args.label) != len(args.log):
        print(f"[FAIL] --label 数({len(args.label)}) 与 --log 数({len(args.log)}) 不一致", file=sys.stderr)
        return 2

    labels = list(args.label) if args.label else []
    if not labels:
        for p in args.log:
            base = os.path.basename(os.path.normpath(p))
            labels.append(base)

    inputs = load_compute_inputs()
    arms: Dict[str, Any] = {}
    errors: List[str] = []
    for lab, raw in zip(labels, args.log):
        jsonl, meta = resolve_log(raw)
        if not os.path.exists(jsonl):
            errors.append(f"日志不存在: {jsonl}（来自 --log {raw}）")
            continue
        try:
            metrics = run_dialogue_metrics(jsonl, meta)
            onscreen = f_onscreen_only(jsonl, inputs)
        except Exception as e:  # noqa: BLE001 — 明确报错，不静默给 0
            errors.append(f"{lab}: {e}")
            continue
        metrics["__onscreen_only__"] = onscreen
        rows = f_rows(metrics)
        meta_obj = json.load(open(meta, encoding="utf-8")) if meta and os.path.exists(meta) else {}
        arms[lab] = {
            "log": jsonl,
            "meta": meta,
            "code_sha": meta_obj.get("code_sha"),
            "llm_cached_ratio": meta_obj.get("llm_cached_ratio"),
            "llm_cached": meta_obj.get("llm_cached"),
            "cached_over_total": ("%s/%s" % (meta_obj.get("llm_cached"), meta_obj.get("llm_calls"))
                                  if meta_obj.get("llm_cached") is not None else None),
            "llm_calls": meta_obj.get("llm_calls"),
            "admission": metrics.get("admission"),
            "narration": narration_readings(jsonl),
            "f_rows": rows,
            "f_den": {r["metric"]: r["den"] for r in rows},
            "L_wording": {
                k: metrics.get("L_wording", {}).get(k)
                for k in ("L-2_narration_rate_proxy", "L-3_paren_block_any",
                          "L-6_dup_exact_rate", "L-7_dup_ngram8_rate")
            },
        }

    if errors:
        for e in errors:
            print(f"[FAIL] {e}", file=sys.stderr)
        return 2

    per_arm_for_judge = {lab: {"narration": a["narration"], "f_rows": a["f_rows"], "f_den": a["f_den"],
                               "llm_cached_ratio": a["llm_cached_ratio"],
                               "cached_over_total": a["cached_over_total"],
                               "L_wording": a["L_wording"]} for lab, a in arms.items()}

    recompute = (
        "python3 tools/metrics/narration_hedge.py \\\n"
        + " \\\n".join(f"  --log {p} --label {l}" for p, l in zip(args.log, labels))
        + (f" \\\n  --baseline-arm {args.baseline_arm}" if args.baseline_arm else "")
        + (f" --treatment-arm {args.treatment_arm}" if args.treatment_arm else "")
        + (" \\\n  --out-json v2/evidence/narration_hedge/readings.json --out-md v2/evidence/narration_hedge/table.md")
    )

    res: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": {"script": os.path.abspath(__file__), "script_sha256": sha256_file(os.path.abspath(__file__))},
        "caliber_sources": {
            "F_metrics": {"path": os.path.join(D5_DIR, "dialogue_metrics.py"),
                          "sha256": sha256_file(os.path.join(D5_DIR, "dialogue_metrics.py"))},
            "narration_regex_and_action_words": {"path": os.path.join(D9I_DIR, "narration_stats.py"),
                                                 "sha256": sha256_file(os.path.join(D9I_DIR, "narration_stats.py"))},
        },
        "recompute_command": recompute,
        "arms": arms,
        "judgement": judge(per_arm_for_judge, args.baseline_arm, args.treatment_arm),
        "arms_role": dict(
            [("__baseline__", args.baseline_arm), ("__treatment__", args.treatment_arm)]
            + [(lab, ("baseline" if lab == args.baseline_arm else
                      "treatment" if lab == args.treatment_arm else "reference_only"))
               for lab in arms]
        ),
    }

    txt = json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True)
    md = render_md(res)
    if args.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8") as f:
            f.write(txt + "\n")
    if args.out_md:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
        with open(args.out_md, "w", encoding="utf-8") as f:
            f.write(md)
    if args.json or not args.out_json:
        print(txt)
    else:
        summary = {
            "hedge_verdict": res["judgement"]["hedge_verdict"],
            "reason": res["judgement"]["verdict_reason"],
            "arms": {lab: {"messages": a["narration"]["denominator_msg_total"],
                           "narration_coverage": a["narration"]["paired"]["coverage_rate"]}
                     for lab, a in arms.items()},
            "out_json": args.out_json, "out_md": args.out_md,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
