#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-3「情绪呼应」双臂零跑批复算器（R14）。

输入 = 两臂 run.jsonl（F-3 OFF / F-3 ON），零跑批，仅读日志。
输出 = 规范 JSON：双口径读数 + Wilson 95% 区间 + 差分区间（Newcombe）+ 与官方实现的一致性核对。

两个口径并列（不替换历史口径）：
  A) 官方口径（`tools/d5/dialogue_metrics.py` 的 `F-3_emotion_echo`，R1–R13 沿用）：
     分母 = 线程内相邻消息对中「上一句极性≠0」的对数；
     命中 = 下一句极性相同 或 命中共情标记（EMPATHY_MARKERS）。
     本脚本**独立重实现同一规则**并与官方 JSON 逐值核对（rate/denominator 必须一致）。
  B) 机制口径（F-3 开关打开后代码写入的可审计字段 `dialogue_emotion_echo`，v=f3/echo/1）：
     分母 = 机制判定为「可呼应轮次」（`eligible` 为真 / 字段存在且候选非空）的相邻对；
     命中 = 字段里 `echoed` 为真（即机制实际让回应方命中对方情绪状态）。
     字段名按 `emotion_echo` 子串自动发现，避免与实现细节耦合。

分母纪律：分母 <30 ⇒ 只报事件数（`band=count_only`）；<68 ⇒ `band=probe`；否则 `band=ok`。
退出码：0 = 正常；2 = 输入缺失/无 MSG；5 = 与官方实现不一致（spec 不符）。

用法：
  python3 tools/f3/f3_metrics.py \
    --off v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
    --on  v2/evidence/run_f3_on_n16r60_seed42/run.jsonl \
    --official-off v2/evidence/f3_off_alldialogue.json \
    --official-on  v2/evidence/f3_on_alldialogue.json \
    --out v2/evidence/f3_readings.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
EMOTION = os.path.join(ROOT, "tools", "d5", "emotion_lexicon.txt")

# 与 tools/d5/dialogue_metrics.py 保持逐字节一致的共情标记（不另写一份）
EMPATHY_MARKERS = ("我懂", "我也", "别难过", "恭喜", "辛苦", "真惨", "太好了", "确实", "是啊", "可不是")

MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson(k: int, n: int, z: float = 1.959963984540054) -> Tuple[Optional[float], Optional[float]]:
    """二项比例 Wilson 95% 区间（与 tools/f6/f6_metrics.py 同式）。"""
    if not n:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - h) / d, 4), round((c + h) / d, 4))


def newcombe_diff(k1: int, n1: int, k2: int, n2: int, z: float = 1.959963984540054):
    """Newcombe(1998) hybrid score 区间：两独立比例之差的 95% CI。"""
    if not n1 or not n2:
        return (None, None)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (round(lo, 4), round(hi, 4))


def band(n: Optional[int]) -> str:
    if n is None:
        return "no_den"
    if n < 30:
        return "count_only"
    if n < 68:
        return "probe"
    return "ok"


def load_emotion(path: str) -> Dict[str, int]:
    emo: Dict[str, int] = {}
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


def polarity(body: str, emo: Dict[str, int]) -> int:
    pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
    neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def find_echo_field(payload: Dict[str, Any]) -> Optional[Tuple[str, Any]]:
    """在 payload 及其 ctx 里找 F-3 审计字段（实现细节解耦，兼容两种命名）。

    已确认实现（`life/emotion_echo.py`，v=`f3/1`）写在 `payload["ctx"]["echo"]`；
    另外也接受键名含 `emotion_echo` 的字段，避免实现改名后脚本失效。
    """
    for holder_name, holder in (("payload", payload), ("ctx", payload.get("ctx") or {})):
        if not isinstance(holder, dict):
            continue
        for k, v in holder.items():
            if not isinstance(k, str):
                continue
            if "emotion_echo" in k:
                return (f"{holder_name}.{k}", v)
            if k == "echo" and isinstance(v, dict) and str(v.get("v", "")).startswith("f3/"):
                return (f"{holder_name}.{k}", v)
    return None


def read_msgs(path: str) -> Tuple[List[dict], int]:
    msgs: List[dict] = []
    n_lines = 0
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
            if rec.get("type") not in MSG_TYPES:
                continue
            p = rec.get("payload") or {}
            body = p.get("body")
            if not isinstance(body, str):
                continue
            msgs.append({
                "seq": rec.get("seq"),
                "round": rec.get("round"),
                "type": rec.get("type"),
                "from": p.get("from"),
                "to": p.get("to"),
                "participants": p.get("participants") or [],
                "thread_id": p.get("thread_id"),
                "reply_to": p.get("reply_to"),
                "body": body,
                "payload": p,
            })
    return msgs, n_lines


def thread_key(m: dict) -> str:
    if m.get("thread_id"):
        return str(m["thread_id"])
    if m.get("type") == "MSG_PUBLIC":
        return "PUB|" + "|".join(sorted(str(x) for x in m.get("participants") or []))
    parts = sorted(str(x) for x in (m.get("participants") or [m.get("from"), m.get("to")]))
    return m["type"] + "|" + "|".join(parts)


def official_replica(msgs: List[dict], emo: Dict[str, int]) -> Dict[str, Any]:
    """独立重实现 tools/d5/dialogue_metrics.py 的 F-3 规则（用于与官方值互核）。

    输出三块（并列，不替换）：
      * 全消息口径（与 tools/d5 逐值一致，历史可比）
      * reply_path 子集（F-3 只在 `_send_reply` 生效 ⇒ 主口径）
      * dedup_by_body（按「当前句 body 原文」去重，防止重复措辞把比率刷高）
    """
    threads: Dict[str, List[dict]] = defaultdict(list)
    for m in msgs:
        threads[thread_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))
    pairs: List[Dict[str, Any]] = []
    for k in sorted(threads):
        th = threads[k]
        for i in range(1, len(th)):
            p_prev = polarity(th[i - 1]["body"], emo)
            if p_prev == 0:
                continue
            cur = th[i]
            p_cur = polarity(cur["body"], emo)
            loose = (p_cur == p_prev) or any(w in cur["body"] for w in EMPATHY_MARKERS)
            # loose_no_agree：只剔除 anchor 已确认的附和词「我懂」，仍承认其它共情标记
            no_agree_markers = tuple(w for w in EMPATHY_MARKERS if w != "我懂")
            no_agree = (p_cur == p_prev) or any(w in cur["body"] for w in no_agree_markers)
            # polarity_match（原 A，leader 裁决改名：**禁止称"严格"**）：只认极性一致
            polarity_match = (p_cur == p_prev)
            # marker_based（原 B，**主指标**）：只认「真实回应标记」，剔除附和词，不要求极性一致
            real_markers = tuple(w for w in EMPATHY_MARKERS
                                 if w not in ("我懂", "确实", "是啊", "可不是"))
            marker_based = any(w in cur["body"] for w in real_markers)
            pairs.append({
                "cur_seq": cur["seq"], "prev_polarity": p_prev, "cur_polarity": p_cur,
                "loose": bool(loose), "no_agree": bool(no_agree),
                "polarity_match": bool(polarity_match), "marker_based": bool(marker_based),
                "real_markers_hit": [w for w in real_markers if w in cur["body"]],
                "reply_path": bool(cur.get("reply_to")),
                "body": cur["body"],
            })

    def agg(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        den = len(rows)
        lo = sum(1 for r in rows if r["loose"])
        na = sum(1 for r in rows if r["no_agree"])
        sa = sum(1 for r in rows if r["polarity_match"])
        sb = sum(1 for r in rows if r["marker_based"])
        ded = {r["body"] for r in rows if r["loose"]}
        return {
            "den": den,
            "loose_ok": lo, "loose_no_agree_ok": na,
            "polarity_match_ok": sa, "marker_based_ok": sb,
            "loose_rate": round(lo / den, 4) if den else None,
            "loose_no_agree_rate": round(na / den, 4) if den else None,
            "polarity_match_rate": round(sa / den, 4) if den else None,
            "marker_based_rate": round(sb / den, 4) if den else None,
            "wilson95_loose": wilson(lo, den),
            "wilson95_loose_no_agree": wilson(na, den),
            "wilson95_polarity_match": wilson(sa, den),
            "wilson95_marker_based": wilson(sb, den),
            "definitions": {
                "loose": "tools/d5 原式：极性相同 ∪ 任意 EMPATHY_MARKERS",
                "loose_no_agree": "极性相同 ∪ 标记剔「我懂」",
                "polarity_match": "只认极性一致(p_cur==p_prev)，标记一律不算。**禁止称「严格」**：它把「负→负各说各话」全数保留为命中，是另一种宽松，不是严格",
                "marker_based": "只认真实回应标记(剔 我懂/确实/是啊/可不是)，不要求极性一致 —— **主指标**",
            },
            "main_口径": "marker_based（leader 2026-10-22 裁决）；polarity_match 仅作技术对照，C(A∪B) 已弃用",
            "dedup_by_body_loose": len(ded),
            "dedup_by_body_polarity_match": len({r["body"] for r in rows if r["polarity_match"]}),
            "dedup_by_body_marker_based": len({r["body"] for r in rows if r["marker_based"]}),
            "dedup_delta": lo - len(ded),
            "band": band(den),
        }

    allm = agg(pairs)
    rp = agg([r for r in pairs if r["reply_path"]])
    neg = agg([r for r in pairs if r["prev_polarity"] < 0])
    n_reply = sum(1 for m in msgs if m.get("reply_to"))
    return {
        "hits": allm["loose_ok"],
        "den": allm["den"],
        "rate": allm["loose_rate"],
        "wilson95": allm["wilson95_loose"],
        "band": allm["band"],
        "口径标签": "全消息口径（上一句极性≠0 的相邻对）",
        "rule": "上一句极性≠0 时，下一句极性相同 或 含共情标记 → 呼应（tools/d5 同式）",
        "reply_path": {
            **rp,
            "口径标签": "回复路径子集（main）：当前句 reply_to 非空 且 上一句极性≠0",
            "n_messages_reply_path": n_reply,
            "denominator_adjacent_pairs_with_prev_polarity": rp["den"],
            "loose_official_ok": rp["loose_ok"],
            "polarity_match_ok": rp["polarity_match_ok"],
            "marker_based_ok": rp["marker_based_ok"],
            "note": ("F-3 仅在 `_send_reply` 生效，`_initiate` 路径即使 ON 也与 OFF 逐字节相同；"
                     "故主口径用本子集，全消息口径并列作对照（两者数值相同属该臂巧合，不可外推）"),
        },
        "dedup_by_body": {
            "key": "当前句 body 原文（不是 cur_seq）",
            "全消息_events_loose": allm["loose_ok"], "全消息_dedup_loose": allm["dedup_by_body_loose"],
            "全消息_delta": allm["dedup_delta"],
            "回复路径_events_loose": rp["loose_ok"], "回复路径_dedup_loose": rp["dedup_by_body_loose"],
            "回复路径_delta": rp["dedup_delta"],
        },
        "conflict_subset": {
            **neg,
            "hits": neg["loose_ok"],
            "polarity_match_ok": neg["polarity_match_ok"], "marker_based_ok": neg["marker_based_ok"],
            "口径标签": "F-3 负向前句子集（上一句极性<0）",
            "note": ("R13 报告的 3 / 0 / 1 是**三臂各自的 F-4 张力分母**（人际冲突子集：张力句须含 "
                     "生气/烦/委屈/失望/后悔/吵/凭什么/你什么意思/别这样 之一），既不是 hits，也不是本字段；"
                     "22 / 15 / 15 是同一批三臂的旧口径张力分母（极性相反 或 当前句为负）。"
                     "本字段只按「上一句极性<0」判定，是 F-3 专用子集，与上述口径数值**不可比**，"
                     "数值偶然相同不代表同义。"),
        },
        "n_threads": len(threads),
        "n_msgs": len(msgs),
    }


def mechanism_replica(msgs: List[dict], emo: Dict[str, int]) -> Dict[str, Any]:
    """机制口径：读 F-3 开关写入的可审计字段，统计「机制宣称可呼应」与「实际命中」。"""
    threads: Dict[str, List[dict]] = defaultdict(list)
    for m in msgs:
        threads[thread_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))
    field_names: Dict[str, int] = {}
    field_present = 0
    captured = 0
    prompted = 0
    sign_dist: Dict[str, int] = {}
    source_dist: Dict[str, int] = {}
    kind_dist: Dict[str, int] = {}
    prev_polarity_hit = 0          # 字段 sign 与日志复算的上一句极性是否一致
    prev_polarity_checked = 0
    for k in sorted(threads):
        th = threads[k]
        for i in range(1, len(th)):
            found = find_echo_field(th[i]["payload"])
            if not found:
                continue
            field_present += 1
            name, val = found
            field_names[name] = field_names.get(name, 0) + 1
            if not isinstance(val, dict):
                continue
            if val.get("prompted"):
                prompted += 1
            sign = val.get("sign")
            sign_dist[str(sign)] = sign_dist.get(str(sign), 0) + 1
            src = str(val.get("source"))
            source_dist[src] = source_dist.get(src, 0) + 1
            kind = str(val.get("kind"))
            kind_dist[kind] = kind_dist.get(kind, 0) + 1
            # 「接住」= 模型输出极性与该条情绪方向一致，或用了共情标记
            body = th[i]["body"]
            if (sign in (1, -1) and polarity(body, emo) == int(sign)) \
                    or any(w in body for w in EMPATHY_MARKERS):
                captured += 1
            # 交叉核对：source 含 text 时，字段 sign 应等于日志复算的上一句极性（防字段自说自话）
            if "text" in src:
                prev_polarity_checked += 1
                p_prev = polarity(th[i - 1]["body"], emo)
                if sign is not None and int(sign) == p_prev:
                    prev_polarity_hit += 1
    return {
        "hits": captured,
        "den": field_present,
        "rate": round(captured / field_present, 4) if field_present else None,
        "wilson95": wilson(captured, field_present),
        "band": band(field_present),
        "rule": "分母=机制判定可呼应的轮次(ctx.echo 存在)；命中=模型输出接住该情绪(极性一致或含共情标记)",
        "口径标签": "机制可呼应轮次（payload.ctx.echo 存在）",
        "field_names": field_names,
        "field_present_msgs": field_present,
        "prompted_msgs": prompted,
        "sign_dist": sign_dist,
        "source_dist": source_dist,
        "kind_dist": kind_dist,
        "prev_polarity_crosscheck": {
            "checked": prev_polarity_checked,
            "agree": prev_polarity_hit,
            "all_agree": (prev_polarity_checked > 0 and prev_polarity_hit == prev_polarity_checked),
            "note": "仅对 source 含 text 的条目核对：字段 sign 是否等于日志复算的上一句极性",
        },
    }


def arm(name: str, run_path: str, official_path: Optional[str], emo: Dict[str, int]) -> Dict[str, Any]:
    if not os.path.exists(run_path):
        raise SystemExit(f"[FAIL] run.jsonl 不存在: {run_path}")
    msgs, n_lines = read_msgs(run_path)
    if not msgs:
        raise SystemExit(f"[FAIL] 日志中没有 MSG 事件: {run_path}")
    off = official_replica(msgs, emo)
    mech = mechanism_replica(msgs, emo)
    out: Dict[str, Any] = {
        "arm": name,
        "run_jsonl": os.path.abspath(run_path),
        "run_sha256": sha256_file(run_path),
        "n_lines": n_lines,
        "n_msgs": len(msgs),
        "official_口径": off,
        "mechanism_口径": mech,
    }
    if official_path and os.path.exists(official_path):
        offi = json.load(open(official_path, encoding="utf-8"))
        f3 = (offi.get("F_series") or {}).get("F-3_emotion_echo") or offi.get("F-3_emotion_echo")
        if f3 is None:
            # dialogue_metrics 的 JSON 结构可能把 F 系列放在别处，递归找键
            def dig(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k == "F-3_emotion_echo":
                            return v
                        r = dig(v)
                        if r is not None:
                            return r
                return None
            f3 = dig(offi)
        if f3:
            out["official_impl"] = {
                "path": os.path.abspath(official_path),
                "sha256": sha256_file(official_path),
                "echo_rate": f3.get("echo_rate"),
                "denominator": f3.get("denominator"),
                "agree_with_replica": (
                    (f3.get("denominator") == off["den"])
                    and (
                        (f3.get("echo_rate") is None and off["rate"] is None)
                        or (f3.get("echo_rate") is not None and off["rate"] is not None
                            and abs(float(f3["echo_rate"]) - float(off["rate"])) < 1e-4)
                    )
                ),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="F-3 情绪呼应双臂零跑批复算器")
    ap.add_argument("--off", required=True, help="OFF 臂 run.jsonl")
    ap.add_argument("--on", required=True, help="ON 臂 run.jsonl")
    ap.add_argument("--official-off", default=None, help="OFF 臂 dialogue_metrics 输出 JSON")
    ap.add_argument("--official-on", default=None, help="ON 臂 dialogue_metrics 输出 JSON")
    ap.add_argument("--out", required=True, help="读数 JSON 落盘路径")
    ap.add_argument("--emotion", default=EMOTION)
    a = ap.parse_args()

    emo = load_emotion(a.emotion)
    off = arm("off", a.off, a.official_off, emo)
    on = arm("on", a.on, a.official_on, emo)

    def diff_block(key: str) -> Dict[str, Any]:
        o = off[key]
        t = on[key]
        return {
            "off_hits": o["hits"], "off_den": o["den"], "off_rate": o["rate"],
            "off_wilson95": o["wilson95"],
            "on_hits": t["hits"], "on_den": t["den"], "on_rate": t["rate"],
            "on_wilson95": t["wilson95"],
            "abs_diff": (round(t["rate"] - o["rate"], 4)
                         if (t["rate"] is not None and o["rate"] is not None) else None),
            "diff_ci95_newcombe": newcombe_diff(t["hits"], t["den"], o["hits"], o["den"]),
            "band_off": o["band"], "band_on": t["band"],
            "min_den": min(x for x in (o["den"], t["den"]) if x is not None) if (o["den"] or t["den"]) else 0,
        }

    res: Dict[str, Any] = {
        "schema": "f3-readings/1.0",
        "script": os.path.abspath(__file__),
        "script_sha256": sha256_file(os.path.abspath(__file__)),
        "emotion_lexicon": {"path": os.path.abspath(a.emotion), "sha256": sha256_file(a.emotion),
                            "n": len(emo)},
        "empathy_markers": list(EMPATHY_MARKERS),
        "arms": {"off": off, "on": on},
        "compare": {
            "official_口径": diff_block("official_口径"),
            "mechanism_口径": diff_block("mechanism_口径"),
        },
        "judge_rule": ("分母<30 只报事件数；<68 标 probe；两臂差分用 Newcombe hybrid score 95%CI，"
                       "CI 跨 0 即不得宣称有差异；跨批/跨时间窗不做显著性外推。"),
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(res["compare"], ensure_ascii=False, indent=2))
    print(f"[written] {os.path.abspath(a.out)}")

    # spec 一致性门禁：与官方实现不一致 ⇒ 退出码 5
    bad = [n for n, v in (("off", off), ("on", on))
           if v.get("official_impl") and not v["official_impl"].get("agree_with_replica")]
    if bad:
        print(f"[FAIL] 与官方 F-3 实现不一致: {bad}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
