#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「句式模板化 / 记忆回指污染」只读复算尺子（零 LLM、零联网、零跑批、零写冻结区）。

口径来源（唯一）
----------------
`v2/evidence/template_ruler_r32/prereg-caliber.md`（**先于出数落盘**，commit `ea52f23`）。
本文件只是那份预登记口径的**执行体**；任何常量改动都必须升 `CALIBER_VERSION` 并同步改口径卡。

指标（逐项独立，禁止相加/求平均）
--------------------------------
M1 记忆回指命中率（主锚点，对拍 `reports/recon-20261028.md` §7.1 的 407/510 = 79.8%）
M2 回指词族矩阵（12 词逐词，各是独立指标）
M3 量化词复用率（quantity–measure pair 的词表级复用）
M4 句式骨架占比（S1..S5，逐类独立；S5 为首 6 字骨架）
M5 回指句式种类数（回指帧归一化后的 distinct 数 + top-10 帧）
M6 会话/人维度粗分布（定位用，分母 < 30 记 `probe`，只报事件数）

诚实性分层
----------
- **可判（字面/规则层）**：M1–M5 全部。它们是「字面命中」的事实，不含任何语义判断。
- **不可判（语义层）**：①消息是否真的在回忆过去（无 judge 维度）；②F-6 读数是否被该句式
  污染（只给共现，不给因果）；③模型是否自发产生该句式（单批无对照臂）。三者显式列出、不猜。

确定性
------
输入只读；输出无时间戳（`--timestamp` 才写）、`sort_keys=True`；样本按 `seq` 升序；
无集合遍历（一律 sorted）⇒ 同输入两次运行逐字节相等（报告复算区有 `sha256sum` 对拍）。

用法
----
    python3 tools/metrics/template_repetition.py \
        --log v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl \
        --out v2/evidence/template_ruler_r32/template_repetition_d12d_on.json \
        --batch-id d12d_on_n16r60_seed42

退出码：0 成功 / 2 输入不可用
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "template-repetition/1.0"
CALIBER_VERSION = "template-repetition-rule/1.0"   # 改任何常量必须同步升版本 + 改口径卡

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")

# ---- M1：主锚点词（写死，口径卡 §2 M1）
ANCHOR_WORD = "上回"

# ---- M2：回指词族（写死，口径卡 §2 M2；顺序即输出顺序，确保确定性）
BACKREF_WORDS = ("上回", "上次", "上个月", "去年", "年前", "那天",
                 "前些日子", "之前", "记得", "想起", "小时候", "那年")

# ---- M3：量化词对（写死，口径卡 §2 M3）
QTY_PAIR_RE = re.compile(
    r"[一二三四五六七八九十两半几数]\s*(指|格|钱|勺|寸|尺|斤|步|刻|个月|年|天|回|次|趟|位|个|把|碗|升)")

# ---- M4：句式骨架（写死，口径卡 §2 M4）
PAREN_NARRATION_HEAD_RE = re.compile(r"^\s*[（(]")
BA_WANG_RE = re.compile(r"把[^。！？]{0,12}往")
BACKREF_QUOTE_RE = re.compile(r"(?:上回|上次)[^。！？]{0,12}(?:说|讲|提|问)")
SHORTFALL_RE = re.compile(r"还差")
SENT_SPLIT_RE = re.compile(r"[。！？；]")
PAREN_STRIP_RE = re.compile(r"(?:（[^）]*）|\([^)]*\))")
PID_RE = re.compile(r"P\d{3}(?!\d)")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
WS_RE = re.compile(r"\s+")

FIRST6_CHARS = 6
TOP_N = 10
PROBE_MIN_DENOM = 30          # 沿用 R4/R14 分母纪律：< 30 只报事件数


# ---------------------------------------------------------------- 基础工具


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> Optional[List[float]]:
    """Wilson score 95% CI（n=0 返回 None）。"""
    if n <= 0:
        return None
    p = k / n
    d = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return [round(lo, 6), round(hi, 6)]


def rate_bundle(k: int, n: int) -> Dict[str, Any]:
    return {
        "numerator": k,
        "denominator": n,
        "rate": (k / n) if n else None,
        "rate_pct": round(100.0 * k / n, 4) if n else None,
        "wilson95": wilson_ci(k, n),
    }


def load_persona_names(path: str) -> Tuple[List[str], Dict[str, Any]]:
    info: Dict[str, Any] = {"path": path, "exists": os.path.exists(path)}
    names: List[str] = []
    if not info["exists"]:
        return names, info
    raw = json.load(open(path, encoding="utf-8"))
    items = raw.get("personas", raw) if isinstance(raw, dict) else raw
    for p in items:
        dn = str(p.get("display_name") or p.get("name") or "").replace("青溪镇·", "").strip()
        if dn:
            names.append(dn)
    # 长名先替换，避免短名先命中把长名切碎；同长按字符串升序 ⇒ 确定性
    names.sort(key=lambda s: (-len(s), s))
    info["sha256"] = sha256_file(path)
    info["n"] = len(names)
    return names, info


def read_messages(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    msgs: List[Dict[str, Any]] = []
    type_total = 0
    body_missing = 0
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            t = r.get("type")
            if t not in MSG_TYPES:
                continue
            type_total += 1
            p = r.get("payload") or {}
            body = p.get("body")
            if body is None or not str(body).strip():
                body = p.get("text")
            if body is None or not str(body).strip():
                body_missing += 1
                continue
            msgs.append({
                "seq": r.get("seq"),
                "round": r.get("round"),
                "event_type": t,
                "from": str(p.get("from") or p.get("author") or r.get("actor") or ""),
                "topic": str(p.get("topic") or ""),
                "body": str(body),
            })
    msgs.sort(key=lambda m: (m["seq"] is None, m["seq"] or 0))
    meta = {
        "msg_type_total": type_total,
        "body_missing": body_missing,
        "messages_analyzed": len(msgs),
        "by_channel": dict(sorted(Counter(m["event_type"] for m in msgs).items())),
    }
    return msgs, meta


# ---------------------------------------------------------------- 指标实现


def m1_anchor(msgs: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(msgs)
    hit = [m for m in msgs if ANCHOR_WORD in m["body"]]
    k = len(hit)
    out = {
        "id": "M1_backref_hit_rate",
        "word": ANCHOR_WORD,
        "definition": f"正文包含子串「{ANCHOR_WORD}」的 MSG_* 条数 / body 非空 MSG_* 条数",
        **rate_bundle(k, n),
        "decidable": True,
    }
    return out


def m2_family(msgs: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(msgs)
    rows = []
    for w in BACKREF_WORDS:
        k = sum(1 for m in msgs if w in m["body"])
        rows.append({"word": w, **rate_bundle(k, n)})
    return {
        "id": "M2_backref_family",
        "definition": "12 个回指词逐词命中率（各词独立指标，禁止相加成『回指率』）",
        "rows": rows,
        "decidable": True,
        "note_no_summing": "同一句可同时命中多个词，故各行不可相加/求平均",
    }


def m3_qty_reuse(msgs: List[Dict[str, Any]]) -> Dict[str, Any]:
    cnt: Counter = Counter()
    total = 0
    for m in msgs:
        for mt in QTY_PAIR_RE.finditer(m["body"]):
            token = WS_RE.sub("", mt.group(0))
            cnt[token] += 1
            total += 1
    types = len(cnt)
    reuse = (1.0 - types / total) if total else None
    top = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]
    return {
        "id": "M3_qty_word_reuse",
        "definition": "量化词对总词次 / 去重词型 / 复用率 = 1 − distinct/词次（词表级复用，非语义判断）",
        "regex": QTY_PAIR_RE.pattern,
        "pair_tokens_total": total,
        "pair_types_distinct": types,
        "reuse_rate": (round(reuse, 6) if reuse is not None else None),
        "top": [{"token": t, "count": c} for t, c in top],
        "decidable": True,
    }


def m4_skeletons(msgs: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(msgs)
    s1 = sum(1 for m in msgs if PAREN_NARRATION_HEAD_RE.search(m["body"]))
    s2 = sum(1 for m in msgs if BA_WANG_RE.search(m["body"]))
    s3 = sum(1 for m in msgs if BACKREF_QUOTE_RE.search(m["body"]))
    s4 = sum(1 for m in msgs if SHORTFALL_RE.search(m["body"]))
    heads: Counter = Counter()
    for m in msgs:
        b = m["body"].strip()
        heads[b[:FIRST6_CHARS]] += 1
    top_heads = sorted(heads.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return {
        "id": "M4_skeleton_share",
        "definition": "5 类句式骨架逐类占比（分母同 M1 分母；S5 另给 distinct 首6字骨架数）",
        "rows": [
            {"id": "S1_narration_paren_open", "regex": PAREN_NARRATION_HEAD_RE.pattern,
             **rate_bundle(s1, n)},
            {"id": "S2_ba_wang_skeleton", "regex": BA_WANG_RE.pattern, **rate_bundle(s2, n)},
            {"id": "S3_backref_quote", "regex": BACKREF_QUOTE_RE.pattern, **rate_bundle(s3, n)},
            {"id": "S4_shortfall_claim", "regex": SHORTFALL_RE.pattern, **rate_bundle(s4, n)},
        ],
        "S5_first6": {
            "n_chars": FIRST6_CHARS,
            "distinct": len(heads),
            "denominator": n,
            "distinct_over_denominator": (round(len(heads) / n, 6) if n else None),
            "top": [{"head": h, "count": c} for h, c in top_heads],
        },
        "decidable": True,
    }


def normalize_frame(body: str, names: List[str]) -> Optional[str]:
    """回指帧：剔旁白 → 取第一个含「上回」的分句 → 归一化 → 去空白。"""
    txt = PAREN_STRIP_RE.sub("", body)
    piece = None
    for seg in SENT_SPLIT_RE.split(txt):
        if ANCHOR_WORD in seg:
            piece = seg.strip()
            break
    if not piece:
        # 回指词只出现在被剔掉的旁白里 ⇒ 该条无可比帧
        return None
    for nm in names:                       # 长名优先（names 已按长度降序排）
        piece = piece.replace(nm, "<NAME>")
    piece = PID_RE.sub("<PID>", piece)
    piece = QTY_PAIR_RE.sub("<QTY>", piece)
    piece = NUM_RE.sub("<NUM>", piece)
    piece = WS_RE.sub("", piece)
    return piece


def m5_frames(msgs: List[Dict[str, Any]], names: List[str]) -> Dict[str, Any]:
    frames: Counter = Counter()
    example: Dict[str, int] = {}
    hit = 0
    no_frame = 0
    for m in msgs:                         # 已按 seq 升序 ⇒ 示例取最小 seq
        if ANCHOR_WORD not in m["body"]:
            continue
        hit += 1
        fr = normalize_frame(m["body"], names)
        if fr is None or not fr:
            no_frame += 1
            continue
        frames[fr] += 1
        if fr not in example and m["seq"] is not None:
            example[fr] = int(m["seq"])
    top = sorted(frames.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]
    return {
        "id": "M5_backref_frames",
        "definition": ("含『上回』的消息（剔旁白后取第一个含该词的分句）归一化为帧后去重；"
                       "归一键：人名表 / P\\d{3} / 数字 / 量化词对 / 空白"),
        "backref_messages": hit,
        "frames_distinct": len(frames),
        "frames_without_piece": no_frame,
        "distinct_frames_per_hit": (round(len(frames) / hit, 6) if hit else None),
        "top": [{"frame": f, "count": c, "example_seq": example.get(f)}
                for f, c in top],
        "decidable": True,
    }


def m6_groups(msgs: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    buckets: Dict[str, List[int]] = {}
    for m in msgs:
        k = m[key] or "(empty)"
        row = buckets.setdefault(k, [0, 0])
        row[0] += 1
        if ANCHOR_WORD in m["body"]:
            row[1] += 1
    rows = []
    for k in sorted(buckets):
        n, hit = buckets[k]
        if n < PROBE_MIN_DENOM:
            rows.append({"key": k, "n": n, "hit": hit, "rate": None,
                         "label": "probe", "note": f"分母 {n} < {PROBE_MIN_DENOM}：只报事件数、不报比率"})
        else:
            rows.append({"key": k, "n": n, "hit": hit, **rate_bundle(hit, n), "label": "ok"})
    return {
        "id": f"M6_by_{key}",
        "definition": f"按 payload.{key} 分桶的 M1 命中率（定位用，非判据；分母 < {PROBE_MIN_DENOM} 记 probe）",
        "rows": rows,
        "decidable": True,
    }


# ---------------------------------------------------------------- 主流程


def build_report(log: str, batch_id: Optional[str], personas: str,
                 anchor_num: int, anchor_den: int) -> Dict[str, Any]:
    if not os.path.exists(log):
        raise SystemExit("log 不存在: " + log)
    names, pinfo = load_persona_names(personas)
    msgs, meta = read_messages(log)
    if not msgs:
        raise SystemExit("日志内无可用消息事件: " + log)

    m1 = m1_anchor(msgs)
    layers = [m1, m2_family(msgs), m3_qty_reuse(msgs), m4_skeletons(msgs),
              m5_frames(msgs, names), m6_groups(msgs, "from"), m6_groups(msgs, "topic")]

    # 与锚点对拍（口径卡 §5）
    k, n = m1["numerator"], m1["denominator"]
    if (k, n) == (anchor_num, anchor_den):
        verdict = "exact"
    elif n and abs(100.0 * k / n - 100.0 * anchor_num / anchor_den) <= 0.05:
        verdict = "rate_only"
    else:
        verdict = "mismatch"
    anchor = {
        "source": "reports/recon-20261028.md §7.1",
        "claimed": {"numerator": anchor_num, "denominator": anchor_den,
                    "rate_pct": round(100.0 * anchor_num / anchor_den, 4)},
        "recomputed": {"numerator": k, "denominator": n,
                       "rate_pct": m1["rate_pct"]},
        "delta_numerator": k - anchor_num,
        "delta_denominator": n - anchor_den,
        "delta_rate_pp": (round(m1["rate_pct"] - 100.0 * anchor_num / anchor_den, 4)
                          if m1["rate_pct"] is not None else None),
        "anchor_match": verdict,
        "denominator_reconciliation": {
            "claimed_denominator": anchor_den,
            "msg_type_total": meta["msg_type_total"],
            "body_missing": meta["body_missing"],
            "messages_analyzed": meta["messages_analyzed"],
            "explanation": ("锚点分母 510 应等于 MSG_DM/MSG_PUBLIC/MSG_GROUP 的总条数；"
                            "与 body_missing 的关系见差值"),
        },
    }

    return {
        "schema": SCHEMA_VERSION,
        "caliber_version": CALIBER_VERSION,
        "metric": "句式模板化 / 记忆回指污染（规则可判档；语义层见 unjudged）",
        "batch_id": batch_id,
        "statistical_unit": "per-message（一条 MSG_DM/MSG_PUBLIC/MSG_GROUP 记 1）",
        "prereg": "v2/evidence/template_ruler_r32/prereg-caliber.md",
        "inputs": {
            "log_path": log,
            "log_sha256": sha256_file(log),
            "log_bytes": os.path.getsize(log),
            "personas": pinfo,
            "script_sha256": sha256_file(os.path.abspath(__file__)),
        },
        "units": meta,
        "anchor_crosscheck": anchor,
        "layers": layers,
        "summary": {
            "rule_decidable_layers": [l["id"] for l in layers],
            "headline": ("本轮只出字面点估计与锚点对拍，**不出改善/恶化判定**（单批、无对照臂）"),
            "note_no_summing": "各指标分母定义不同或可重叠，禁止相加或求平均",
            "unjudged": [
                "U1: 消息是否『真的』在回忆过去（需 judge/事实核验；仓内无 fabrication-like 维度）",
                "U2: F-6 读数是否被该句式污染（只给共现，不给因果）",
                "U3: 该句式是否模型自发（单批无对照臂，不可归因）",
            ],
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="句式模板化/记忆回指 · 规则可判档只读复算尺子（零 LLM，确定性输出）")
    ap.add_argument("--log", required=True, help="run.jsonl 路径（只读）")
    ap.add_argument("--out", required=True, help="输出 JSON 路径（--out-json 同义）")
    ap.add_argument("--out-json", dest="out", help="--out 的别名")
    ap.add_argument("--batch-id", default=None, help="批次标签")
    ap.add_argument("--personas", default=os.path.join("code", "config", "personas.json"),
                    help="人名表（用于帧归一化；只读）")
    ap.add_argument("--anchor-num", type=int, default=407, help="锚点分子（默认 407）")
    ap.add_argument("--anchor-den", type=int, default=510, help="锚点分母（默认 510）")
    ap.add_argument("--timestamp", action="store_true",
                    help="在 JSON 写 generated_at（默认不写，保证逐字节可复现）")
    args = ap.parse_args(argv)
    if not args.out:
        ap.error("必须给 --out 或 --out-json")

    rep = build_report(args.log, args.batch_id, args.personas,
                       args.anchor_num, args.anchor_den)
    if args.timestamp:
        import datetime
        rep["generated_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(rep, ensure_ascii=False, sort_keys=True, indent=2))
        f.write("\n")

    m1 = rep["layers"][0]
    ac = rep["anchor_crosscheck"]
    print(f"[template-repetition] batch={args.batch_id} "
          f"msgs={rep['units']['messages_analyzed']} "
          f"M1={m1['numerator']}/{m1['denominator']}={m1['rate_pct']}% "
          f"anchor={ac['claimed']['numerator']}/{ac['claimed']['denominator']} "
          f"diff({ac['delta_numerator']:+d}/{ac['delta_denominator']:+d}) "
          f"-> {ac['anchor_match']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
