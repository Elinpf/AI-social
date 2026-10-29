#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-3「情绪呼应」宽机会口径读数器（零 LLM、只读 run.jsonl）。

口径唯一来源（**本脚本不得自造口径**）：
    v2/refs/P-F3-verdictable-r32.md   ←  预登记口径卡（本脚本把它的 sha256 写进输出）

两把尺子并列输出（**不可混比**）：
    A) old_caliber   —— 仓库历史口径（线程内相邻消息对、上一句词表极性≠0），用于「同证据旧读数」对照；
    B) wide_caliber  —— 本卡新口径：
         机会集 O = { m ∈ MSG_* : reply_to≠null ∧ parent(m) 可解析 ∧ affect(parent(m)) }
         affect(x) := (mood(x)≠null ∧ mood(x)∉NEUTRAL_MOOD) ∨ pol(body(x))≠0
         主命中 P1 = H1(极性一致) ∪ H2(共情标记)  ——  H1/H2 必须分列报，不得只给合并数
         次级 H3(情绪标签回声) / S1(结构化 mood 共振，受状态持续性混淆，只作对照)
         机制侧 M = payload.ctx.echo / verify.present / verify.adopted（仅 ON 臂有值，不参与两臂比较）

极性判定（两臂同一份，本轮不改）：
    词表   tools/d5/emotion_lexicon.txt   （"<权重> <词>"，子串计数）
    算法   tools/d5/dialogue_metrics.py::polarity() 的等价重实现（见 polarity()）
    ⇒ 若词表 sha256 与 §1 记录不一致，输出会立刻暴露（分母随之失去可比性）。

判档（照抄仓库纪律，不得放宽）：
    den < 30            → count_only（只报事件数）
    30 ≤ den < 68       → 不可判(count_only)（只报事件数 + 抬到 68 的最小代价外推）
    den ≥ 68            → ok（报率 + Wilson95）；并给 MDE 提示（分母够 ≠ 能检出小效应）
    PROBE_MIN_DENOM = 68

确定性：零随机、零网络、零时间戳、JSON sort_keys ⇒ 同卡同臂两次运行逐字节相同。

用法：
    python3 tools/metrics/f3_echo_rate.py --log-dir v2/evidence/cycle33_f3_off_n16r84_seed42 \
            --json v2/evidence/cycle35_f3_verdictable/off.json \
            --md   v2/evidence/cycle35_f3_verdictable/off.md
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

SCHEMA = "f3-echo-rate/1.0"
PROBE_MIN_DENOM = 68          # 仓库纪律，不得下调（口径卡 §4.3）
COUNT_ONLY_MIN = 30           # 仓库纪律（<30 只报事件数）

DEFAULT_CARD = os.path.join(ROOT, "v2", "refs", "P-F3-verdictable-r32.md")
DEFAULT_EMOTION = os.path.join(ROOT, "tools", "d5", "emotion_lexicon.txt")

# 与 tools/d5/dialogue_metrics.py::EMPATHY_MARKERS 逐字节同一份（口径卡 §1；不得增删）
EMPATHY_MARKERS = ("我懂", "我也", "别难过", "恭喜", "辛苦", "真惨", "太好了", "确实", "是啊", "可不是")

NEUTRAL_MOOD = ("平和",)      # 口径卡 §3.1
MOOD_TERMS = ("紧绷", "孤单", "疲惫", "饥饿")   # H3：母消息 mood 字面词（口径卡 §4.2）

Z95 = 1.959963984540054
Z80 = 0.8416212335729143


# ---------------------------------------------------------------- 基础工具
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson(k: int, n: int, z: float = Z95):
    """二项比例 Wilson 95% 区间（与 tools/f3/f3_metrics.py 同式）。"""
    if not n:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - h) / d, 6), round((c + h) / d, 6))


def newcombe_diff(k1: int, n1: int, k2: int, n2: int, z: float = Z95):
    """Newcombe(1998) hybrid score：两独立比例之差的 95% CI。"""
    if not n1 or not n2:
        return (None, None)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (round(lo, 6), round(hi, 6))


def mde_abs(p_bar: float, n: int, alpha_z: float = Z95, power_z: float = Z80):
    """最小可检测绝对率差 MDE（口径卡 §4.3.1，公式写死）。"""
    if not n or p_bar is None:
        return None
    se = math.sqrt(2 * p_bar * (1 - p_bar) / n)
    return round((alpha_z + power_z) * se, 6)


def band(n: int) -> str:
    if n < COUNT_ONLY_MIN:
        return "count_only"
    if n < PROBE_MIN_DENOM:
        return "不可判(count_only)"
    return "ok"


def load_emotion(path: str):
    """读词表：每行 '<权重> <词>'（可含空格词）。与 tools/d5 同格式。"""
    emo = {}
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            parts = ln.split()
            if len(parts) < 2:
                continue
            try:
                emo[" ".join(parts[1:])] = int(parts[0])
            except ValueError:
                continue
    return emo


def polarity(body: str, emo) -> int:
    """tools/d5/dialogue_metrics.py::polarity() 的等价重实现（朴素子串计数）。

    pos = #{w : weight(w) > 0 且 w 是 body 的子串}；neg 同理取 weight < 0。
    返回 sign(pos - neg) ∈ {-1, 0, 1}。
    """
    pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
    neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


# ---------------------------------------------------------------- 读日志
def read_msgs(path: str):
    """只读 run.jsonl ⇒ MSG_* 消息列表（口径卡 §3.1 的字段面）。"""
    msgs, n_lines = [], 0
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            n_lines += 1
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if not str(rec.get("type", "")).startswith("MSG_"):
                continue
            p = rec.get("payload") or {}
            body = p.get("body")
            if not isinstance(body, str):
                body = ""
            ctx = p.get("ctx") or {}
            rt = p.get("reply_to")
            msgs.append({
                "seq": rec.get("seq"),
                "round": rec.get("round"),
                "type": rec.get("type"),
                "msg_uid": str(p.get("msg_uid")),
                "reply_to": (str(rt) if rt is not None else None),
                "thread_id": p.get("thread_id"),
                "participants": p.get("participants") or [],
                "from": p.get("from") or p.get("author"),
                "body": body,
                "mood": ctx.get("mood"),
                "echo": ctx.get("echo"),
            })
    return msgs, n_lines


def thread_key(m):
    if m["thread_id"]:
        return str(m["thread_id"])
    parts = sorted(str(x) for x in (m["participants"] or [m["from"]]))
    return str(m["type"]) + "|" + "|".join(parts)


# ---------------------------------------------------------------- A) 旧口径
def old_caliber(msgs, emo):
    """仓库历史口径：线程内相邻对、上一句极性≠0。同证据旧读数，仅供对照。"""
    threads = collections.defaultdict(list)
    for m in msgs:
        threads[thread_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: ((m["round"] if m["round"] is not None else -1),
                                       (m["seq"] if m["seq"] is not None else -1)))
    rows = []
    for k in sorted(threads):
        th = threads[k]
        for i in range(1, len(th)):
            p_prev = polarity(th[i - 1]["body"], emo)
            if p_prev == 0:
                continue
            cur = th[i]
            p_cur = polarity(cur["body"], emo)
            rows.append({
                "prev_pol": p_prev,
                "cur_pol": p_cur,
                "polarity_match": (p_cur == p_prev),
                "marker_hit": any(w in cur["body"] for w in EMPATHY_MARKERS),
                "loose": (p_cur == p_prev) or any(w in cur["body"] for w in EMPATHY_MARKERS),
                "reply_path": bool(cur["reply_to"]),
            })

    def agg(rs):
        n = len(rs)
        lo = sum(1 for r in rs if r["loose"])
        pm = sum(1 for r in rs if r["polarity_match"])
        mk = sum(1 for r in rs if r["marker_hit"])
        return {
            "den": n,
            "hits_loose": lo, "hits_polarity_match": pm, "hits_marker": mk,
            "rate_loose": (round(lo / n, 6) if n else None),
            "wilson95_loose": wilson(lo, n),
            "band": band(n),
        }

    return {
        "rule": "线程内相邻消息对，且上一句词表极性≠0（= tools/d5 / tools/f3 历史口径）",
        "all_messages": agg(rows),
        "reply_path": agg([r for r in rows if r["reply_path"]]),
        "note": "本块仅作「同证据旧读数」对照；**新口径的率不可与它直接比大小**（分母放大 15 倍以上）",
    }


# ---------------------------------------------------------------- B) 新宽口径
def wide_caliber(msgs, emo):
    """口径卡 §3.2 / §4.1：机会集 O + 主命中 P1=H1∪H2 + 次级 H3。"""
    by_uid = {}
    for m in msgs:
        by_uid.setdefault(m["msg_uid"], m)

    n_reply = 0
    n_unresolvable = 0
    n_excl_neutral = 0
    opportunity = []
    for m in msgs:
        if not m["reply_to"]:
            continue
        n_reply += 1
        parent = by_uid.get(m["reply_to"])
        if parent is None:
            n_unresolvable += 1
            continue
        p_prev = polarity(parent["body"], emo)
        mood_affect = (parent["mood"] is not None and parent["mood"] not in NEUTRAL_MOOD)
        if not (mood_affect or p_prev != 0):
            n_excl_neutral += 1
            continue
        opportunity.append({"m": m, "parent": parent, "parent_pol": p_prev})

    h1 = h2 = h3 = 0
    by_parent_mood = collections.defaultdict(lambda: {"den": 0, "p1": 0})
    by_type = collections.defaultdict(lambda: {"den": 0, "p1": 0})
    hit_rows = []
    for o in opportunity:
        m, parent, p_prev = o["m"], o["parent"], o["parent_pol"]
        p_cur = polarity(m["body"], emo)
        is_h1 = bool(p_prev != 0 and p_cur == p_prev)
        is_h2 = any(w in m["body"] for w in EMPATHY_MARKERS)
        is_h3 = any(w in m["body"] for w in MOOD_TERMS)
        p1 = is_h1 or is_h2
        h1 += int(is_h1)
        h2 += int(is_h2)
        h3 += int(is_h3)
        key_mood = str(parent["mood"])
        by_parent_mood[key_mood]["den"] += 1
        by_parent_mood[key_mood]["p1"] += int(p1)
        by_type[str(m["type"])]["den"] += 1
        by_type[str(m["type"])]["p1"] += int(p1)
        if p1:
            hit_rows.append({
                "msg_uid": m["msg_uid"], "type": m["type"], "round": m["round"],
                "parent_uid": parent["msg_uid"], "parent_mood": parent["mood"],
                "parent_pol": p_prev, "cur_pol": p_cur,
                "H1": is_h1, "H2": is_h2,
                "H2_markers": [w for w in EMPATHY_MARKERS if w in m["body"]],
                "body": m["body"][:160],
            })

    den = len(opportunity)
    p1 = h1 + h2  # 注：H1/H2 可能重叠，合并命中数单独统计如下
    p1_union = sum(1 for o in opportunity
                   if (o["parent_pol"] != 0 and polarity(o["m"]["body"], emo) == o["parent_pol"])
                   or any(w in o["m"]["body"] for w in EMPATHY_MARKERS))
    overlap = h1 + h2 - p1_union
    rate = round(p1_union / den, 6) if den else None

    # —— 次级 S1：结构化 mood 共振（受状态持续性混淆，只作对照，§5.5）
    s1_den = s1_match = 0
    s1_pairs = collections.Counter()
    for o in opportunity:
        m, parent = o["m"], o["parent"]
        if parent["mood"] is None or parent["mood"] in NEUTRAL_MOOD:
            continue
        s1_den += 1
        key = "%s→%s" % (parent["mood"], m["mood"])
        s1_pairs[key] += 1
        if m["mood"] == parent["mood"]:
            s1_match += 1

    # —— 机制侧 M：ctx.echo / verify（仅 ON 臂有值，不参与两臂比较）
    echo_msgs = 0
    verify_present = verify_adopted = 0
    echo_sources = collections.Counter()
    for m in msgs:
        e = m["echo"]
        if not isinstance(e, dict) or not e:
            continue
        echo_msgs += 1
        echo_sources[str(e.get("source"))] += 1
        v = e.get("verify")
        if isinstance(v, dict):
            verify_present += 1
            verify_adopted += int(bool(v.get("adopted")))

    rounds_seen = len({m["round"] for m in msgs if m["round"] is not None})

    return {
        "rule": "机会 = reply 消息 ∧ 父消息可解析 ∧ (父 ctx.mood∉{平和} ∨ 父正文词表极性≠0)",
        "den": den,
        "hits": {
            "H1_polarity_match": h1,
            "H2_empathy_markers": h2,
            "H1_H2_overlap": overlap,
            "P1_union": p1_union,
            "H3_mood_term_echo": h3,
        },
        "rate": rate,
        "wilson95": wilson(p1_union, den),
        "band": band(den),
        "rate_components": {
            "H1": (round(h1 / den, 6) if den else None),
            "H2": (round(h2 / den, 6) if den else None),
            "H3": (round(h3 / den, 6) if den else None),
        },
        "opportunity_breakdown": {
            "n_reply_msgs": n_reply,
            "excluded_no_reply_to": len(msgs) - n_reply,
            "parent_unresolvable": n_unresolvable,
            "excluded_parent_no_affect": n_excl_neutral,
            "counted_opportunity": den,
        },
        "by_parent_mood": {k: dict(sorted(v.items())) for k, v in sorted(by_parent_mood.items())},
        "by_msg_type": {k: dict(sorted(v.items())) for k, v in sorted(by_type.items())},
        "hits_detail": hit_rows,
        "mde_hint": {
            "p_bar": rate if rate is not None else 0.0,
            "n": den,
            "mde_abs": mde_abs(rate if rate is not None else 0.0, den),
            "note": "分母≥68 只代表『允许报率』；MDE 是本臂规模下能检出的最小绝对率差（α=0.05 双侧、power=0.80）",
        },
        "secondary_mood_resonance_S1": {
            "den": s1_den,
            "match": s1_match,
            "rate": (round(s1_match / s1_den, 6) if s1_den else None),
            "wilson95": wilson(s1_match, s1_den),
            "band": band(s1_den),
            "pairs": dict(sorted(s1_pairs.items())),
            "warning": "受 agent 需求状态持续性混淆（非对话驱动）；只作对照，不得当作情绪呼应主判据（口径卡 §4.2/§5.5）",
        },
        "mechanism_M": {
            "echo_msgs": echo_msgs,
            "echo_by_source": dict(sorted(echo_sources.items())),
            "verify_present": verify_present,
            "verify_adopted": verify_adopted,
            "adoption_rate": (round(verify_adopted / verify_present, 6) if verify_present else None),
            "arm_has_field": bool(echo_msgs),
            "warning": "仅 ON 臂有值，**不参与两臂比较**；机制接线成立 ≠ 行为被采纳（口径卡 §4.2/§5.5）",
        },
        "n_rounds_seen": rounds_seen,
        "opportunity_per_round": (round(den / rounds_seen, 6) if rounds_seen else None),
    }


def verdict_block(wide, old, arm_name: str):
    """判档结论（照口径卡 §4.3 / §4.3.1 / §4.3.2，不得放宽）。"""
    den = wide["den"]
    b = band(den)
    out = {"arm": arm_name, "den": den, "band": b, "judgeable": den >= PROBE_MIN_DENOM}
    if den < PROBE_MIN_DENOM:
        # R-1 触发：给「抬到 ≥68」的最小代价（外推，非实测）
        per_round = wide["opportunity_per_round"] or 0.0
        need_rounds = math.ceil((PROBE_MIN_DENOM - den) / per_round) if per_round else None
        out["message"] = (
            "不可判(count_only)：机会分母 %d < PROBE_MIN_DENOM=%d，本轮只报事件数、不报率。"
            % (den, PROBE_MIN_DENOM)
        )
        out["min_cost_to_den68"] = {
            "kind": "外推（extrapolation，非实测）",
            "opportunity_per_round": per_round,
            "extra_rounds_needed_at_same_density": need_rounds,
            "note": "按本臂 opp/round 密度线性外推；实际还需保证每轮 seed/agent 与两臂一致。",
        }
    else:
        out["message"] = (
            "可判：机会分母 %d ≥ %d，报率 %s（Wilson95 %s）。"
            "注意分母够 ≠ 能检出小效应：本规模 MDE≈%s（绝对率差），"
            "小于 MDE 的差异只能写『无可检出差异/样本不足以排除小效应』，不得写『证明无差异』。"
            % (den, PROBE_MIN_DENOM, wide["rate"], wide["wilson95"], wide["mde_hint"]["mde_abs"])
        )
    out["old_caliber_den_same_evidence"] = old["all_messages"]["den"]
    out["caliber_change_note"] = (
        "新口径率不可与旧口径(%d)直接比大小：分母从 %d → %d，是尺子变了，不是呼应变好/变坏。"
        % (old["all_messages"]["den"], old["all_messages"]["den"], den)
    )
    return out


# ---------------------------------------------------------------- 输出
def render_md(res) -> str:
    w, o, s1, mm = res["wide_caliber"], res["old_caliber"], \
        res["wide_caliber"]["secondary_mood_resonance_S1"], res["wide_caliber"]["mechanism_M"]
    L = []
    L.append("# F-3 情绪呼应读数 · arm=%s" % res["arm"])
    L.append("")
    L.append("- 输入 `run.jsonl`：`%s`" % res["inputs"]["log"])
    L.append("- run.jsonl sha256：`%s`" % res["inputs"]["log_sha256"])
    L.append("- 口径卡：`%s` sha256 `%s`" % (res["card"]["path"], res["card"]["sha256"]))
    L.append("- 词表：`%s` sha256 `%s`（n=%d）" % (
        res["inputs"]["lexicon"]["path"], res["inputs"]["lexicon"]["sha256"], res["inputs"]["lexicon"]["n"]))
    L.append("- 脚本 sha256：`%s`" % res["script"]["sha256"])
    L.append("")
    L.append("## 1. 宽机会口径（本卡主口径）")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append("| 机会分母 den_wide | **%d** |" % w["den"])
    L.append("| 判档 band | **%s** |" % w["band"])
    L.append("| P1 命中 (H1∪H2) | **%d** |" % w["hits"]["P1_union"])
    L.append("| 率 | **%s** |" % w["rate"])
    L.append("| Wilson 95%% | %s |" % (w["wilson95"],))
    L.append("| MDE（绝对率差） | %s |" % w["mde_hint"]["mde_abs"])
    L.append("")
    L.append("### 1.1 命中分列（不得只看合并数）")
    L.append("")
    L.append("| 子指标 | 命中 | 率 | 定义 |")
    L.append("|---|---|---|---|")
    L.append("| H1 极性一致 | %d | %s | 父消息极性≠0 且回复方极性相同 |" % (
        w["hits"]["H1_polarity_match"], w["rate_components"]["H1"]))
    L.append("| H2 共情标记 | %d | %s | 回复方含 10 个 EMPATHY_MARKERS 之一 |" % (
        w["hits"]["H2_empathy_markers"], w["rate_components"]["H2"]))
    L.append("| H1∩H2 重叠 | %d | — | 两条同时命中 |" % w["hits"]["H1_H2_overlap"])
    L.append("| H3 情绪标签回声 | %d | %s | 回复方含父消息 mood 字面词 |" % (
        w["hits"]["H3_mood_term_echo"], w["rate_components"]["H3"]))
    L.append("")
    L.append("### 1.2 机会集分解（可复算口径，口径卡 §3.4）")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    for k, v in sorted(w["opportunity_breakdown"].items()):
        L.append("| %s | %d |" % (k, v))
    L.append("| n_rounds_seen | %d |" % w["n_rounds_seen"])
    L.append("| opportunity/round | %s |" % w["opportunity_per_round"])
    L.append("")
    L.append("| 父消息 mood | 机会数 | P1 命中 |")
    L.append("|---|---|---|")
    for k, v in sorted(w["by_parent_mood"].items()):
        L.append("| %s | %d | %d |" % (k, v["den"], v["p1"]))
    L.append("")
    L.append("## 2. 旧口径（同证据，仅供对照；**不可与新口径比大小**）")
    L.append("")
    L.append("| 子集 | 分母 | loose 命中 | loose 率 | Wilson95 | band |")
    L.append("|---|---|---|---|---|---|")
    for name in ("all_messages", "reply_path"):
        a = o[name]
        L.append("| %s | %d | %d | %s | %s | %s |" % (
            name, a["den"], a["hits_loose"], a["rate_loose"], a["wilson95_loose"], a["band"]))
    L.append("")
    L.append("## 3. 次级 S1：结构化 mood 共振（受状态持续性混淆，**只作对照**）")
    L.append("")
    L.append("- den=%d，match=%d，率=%s，Wilson95=%s，band=%s" % (
        s1["den"], s1["match"], s1["rate"], s1["wilson95"], s1["band"]))
    L.append("- 共振对分布：" + "、".join("%s=%d" % (k, v) for k, v in sorted(s1["pairs"].items())))
    L.append("- ⚠️ %s" % s1["warning"])
    L.append("")
    L.append("## 4. 机制侧 M（仅 ON 臂有值，**不参与两臂比较**）")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append("| echo_msgs | %d |" % mm["echo_msgs"])
    L.append("| echo_by_source | %s |" % (mm["echo_by_source"],))
    L.append("| verify_present | %d |" % mm["verify_present"])
    L.append("| verify_adopted | %d |" % mm["verify_adopted"])
    L.append("| 采纳率 | %s |" % mm["adoption_rate"])
    L.append("")
    L.append("- ⚠️ %s" % mm["warning"])
    L.append("")
    L.append("## 5. 判档结论")
    L.append("")
    vd = res["verdict"]
    L.append("- 判档：**%s**（judgeable=%s）" % (vd["band"], vd["judgeable"]))
    L.append("- 结论：%s" % vd["message"])
    L.append("- 口径变更声明：%s" % vd["caliber_change_note"])
    if "min_cost_to_den68" in vd:
        L.append("- 抬到 den≥68 的最小代价（**外推非实测**）：%s" % vd["min_cost_to_den68"])
    L.append("")
    return "\n".join(L) + "\n"


def build(log_path: str, arm: str, card_path: str, emotion_path: str):
    emo = load_emotion(emotion_path)
    msgs, n_lines = read_msgs(log_path)
    if not msgs:
        raise SystemExit("[FAIL] 日志中没有 MSG_* 事件: %s" % log_path)
    old = old_caliber(msgs, emo)
    wide = wide_caliber(msgs, emo)
    res = {
        "schema": SCHEMA,
        "arm": arm,
        "card": {"path": os.path.relpath(os.path.abspath(card_path), ROOT),
                 "sha256": sha256_file(card_path)},
        "script": {"path": os.path.relpath(os.path.abspath(__file__), ROOT),
                   "sha256": sha256_file(os.path.abspath(__file__))},
        "inputs": {
            "log": os.path.relpath(os.path.abspath(log_path), ROOT),
            "log_sha256": sha256_file(log_path),
            "n_lines": n_lines,
            "n_msgs": len(msgs),
            "n_msg_uid_unique": len({m["msg_uid"] for m in msgs}),
            "lexicon": {"path": os.path.relpath(os.path.abspath(emotion_path), ROOT),
                        "sha256": sha256_file(emotion_path), "n": len(emo)},
            "empathy_markers": list(EMPATHY_MARKERS),
            "neutral_moods": list(NEUTRAL_MOOD),
            "mood_terms": list(MOOD_TERMS),
            "probe_min_denom": PROBE_MIN_DENOM,
            "count_only_min": COUNT_ONLY_MIN,
        },
        "old_caliber": old,
        "wide_caliber": wide,
    }
    res["verdict"] = verdict_block(wide, old, arm)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F-3 情绪呼应宽机会口径读数器（零 LLM、只读 run.jsonl）")
    ap.add_argument("--log-dir", default=None, help="arm 目录（自动读 <dir>/run.jsonl）")
    ap.add_argument("--log", default=None, help="直接指定 run.jsonl 路径")
    ap.add_argument("--arm", default=None, help="臂名（默认取目录名）")
    ap.add_argument("--json", required=True, help="机器可读输出路径")
    ap.add_argument("--md", default=None, help="人读表格输出路径")
    ap.add_argument("--card", default=DEFAULT_CARD, help="口径卡路径（sha256 会写入输出）")
    ap.add_argument("--emotion", default=DEFAULT_EMOTION, help="情绪词表（两臂必须同一份）")
    a = ap.parse_args(argv)

    if a.log:
        log_path = a.log
        arm = a.arm or os.path.basename(os.path.dirname(os.path.abspath(log_path)))
    elif a.log_dir:
        log_path = os.path.join(a.log_dir, "run.jsonl")
        arm = a.arm or os.path.basename(os.path.abspath(a.log_dir.rstrip("/")))
    else:
        ap.error("需要 --log-dir 或 --log")

    if not os.path.exists(log_path):
        raise SystemExit("[FAIL] run.jsonl 不存在: %s" % log_path)
    if not os.path.exists(a.card):
        raise SystemExit("[FAIL] 口径卡不存在（本脚本不自造口径）: %s" % a.card)

    res = build(log_path, arm, a.card, a.emotion)

    out_json = os.path.abspath(a.json)
    os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    if a.md:
        out_md = os.path.abspath(a.md)
        os.makedirs(os.path.dirname(out_md) or ".", exist_ok=True)
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(render_md(res))

    print(json.dumps({
        "arm": res["arm"],
        "den_wide": res["wide_caliber"]["den"],
        "P1_hits": res["wide_caliber"]["hits"]["P1_union"],
        "rate": res["wide_caliber"]["rate"],
        "wilson95": res["wide_caliber"]["wilson95"],
        "band": res["wide_caliber"]["band"],
        "old_den": res["old_caliber"]["all_messages"]["den"],
        "S1": "%s/%s" % (res["wide_caliber"]["secondary_mood_resonance_S1"]["match"],
                         res["wide_caliber"]["secondary_mood_resonance_S1"]["den"]),
        "M": "%s/%s" % (res["wide_caliber"]["mechanism_M"]["verify_adopted"],
                        res["wide_caliber"]["mechanism_M"]["verify_present"]),
        "json": out_json,
        "md": os.path.abspath(a.md) if a.md else None,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
