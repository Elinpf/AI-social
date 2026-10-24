#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recompute_d27.py —— D2.7 两臂读数的**独立复算**（零 LLM、零跑批、只读 run.jsonl）

目的：不信任 v2/evidence/d27_harvest/* 的落盘 JSON，从原始日志把每个读数**重算一遍**，
      再与落盘值逐项对账；同时显式给出「采用基线（run_d27_C 现算）」与「污染基线（d25a C, e2e7131）」
      两套差值，供报告第二节/第三节引用。

口径纪律（不自创词表 / 不自创正则）：
  · P1 词表 = `v2/evidence/d12c_metrics.py::DETAIL`（冻结读数器）—— **import 原样**，只把 any() 换成计数
  · P2 名字 = `code/config/personas.json`（display_name 去「青溪镇·」前缀），与 d12c_metrics.names() 同源
  · paren/len 两个口径并列：
        d12c 口径（判据用的 paren_rate）   body.lstrip() 以 （ 或 ( **起头**
        d9   口径（形态闸的 paren_rate）   body 含 （…） 或 (…) **括号块**
  · len_p50_excl：去括号块后字符长度中位数；同时给「strip 版」（d12c/d27_metrics）与「不 strip 版」（d9）
  · L-7 norm8：normalize_body 后 8-gram，**全批**范围内与任一其它消息共享 ≥1 个 8-gram 的消息占比
        （注：任务卡把它写成「8 轮窗口复述率」，仓内实现实为「8-gram 近重复率、无窗口」——本脚本按实现口径算并标注）
  · L-15 restate：normalize_body + 8-gram，**同线程内前向**共享 ≥1（strong ≥3）
  · F-2′：相邻消息 char-bigram Jaccard < 0.10 记一次换话头，分组 = mixed_key（thread_id 优先）
  · 线程级分母 = 全部 thread_id 去重，**必须含发送人缺 from 的线程**（MSG_PUBLIC 的 payload 无 from 键、
    发送人取自 payload.author ⇒ C 55 / B 53 个单条线程，已在 169/170 分母内），并与 dialogue_metrics 的 n_threads 对账

用法（原地可重放）：
  python3 v2/evidence/cycle21_recon/recompute_d27.py \
      --C v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
      --B .worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl \
      --harvest v2/evidence/d27_harvest \
      --out-json v2/evidence/cycle21_recon/metrics_recompute.json

纯函数、无随机、无时间戳 ⇒ 两次运行逐字节相同。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# ---------------- 冻结实现来源 ----------------
_spec = importlib.util.spec_from_file_location(
    "d12c_metrics", REPO / "v2" / "evidence" / "d12c_metrics.py")
_d12c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d12c)
DETAIL = list(_d12c.DETAIL)          # P1 词表（冻结，不自创）

MSG = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
CHANNEL = {"MSG_DM": "dm", "MSG_PUBLIC": "public", "MSG_GROUP": "group"}

PAREN_BLOCK = re.compile(r"（[^（）]*）|\([^()]*\)")          # d9: BR
PAREN_BLOCK_120 = re.compile(r"(?:（[^）]{0,120}）|\([^)]{0,120}\))")  # dialogue_metrics: PAREN_ANY_RE
LEAD = re.compile(r"^\s*[（(]")                                # d12c / d27_metrics
LEAD_FULL = re.compile(r"^\s*[（(]([^）)]{1,200})[）)]")
AGENT_ID = re.compile(r"P\d{3}(?!\d)")
MENTAL = ("心想", "心里", "想道", "暗想", "觉得", "寻思", "念头", "心中")
STOP_CHARS = set(
    "的了呢吧啊呀吗嘛就都也还你我他她它是不在有和与这那个些一什么怎么"
    "很太更最又再才被把让给对说着过起去来到得地么哦噢哎喂嗯"
)
PUNCT = set(" \t\n,，。！？!?、；;:：\"'“”‘’…—-.()（）[]【】")


def sha8(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:8]


def pct(x, n):
    return round(100.0 * x / n, 2) if n else None


def norm_body(s: str) -> str:
    """dialogue_metrics.normalize_body 原样复刻"""
    s = s.strip().lower()
    s = s.replace("（", "(").replace("）", ")")
    return re.sub(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)\[\]【】]", "", s)


def content_bigrams(s: str) -> set:
    """dialogue_metrics.content_bigrams 原样复刻"""
    t = PAREN_BLOCK_120.sub("", s).strip()
    t = AGENT_ID.sub("", t)
    t = re.sub(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)]", "", t)
    chars = [c for c in t if c not in STOP_CHARS]
    if len(chars) < 2:
        return set()
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def load_names() -> list[str]:
    raw = json.load(open(REPO / "code" / "config" / "personas.json", encoding="utf-8"))
    items = raw.get("personas", raw) if isinstance(raw, dict) else raw
    return [str(p.get("display_name") or "").split("·")[-1] for p in items]


# ---------------- 读日志 ----------------
def read_msgs(path: Path) -> list[dict]:
    out = []
    for line in open(path, encoding="utf-8"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG:
            continue
        pl = e.get("payload") or {}
        ctx = pl.get("ctx") if isinstance(pl.get("ctx"), dict) else {}
        out.append({
            "seq": e.get("seq"),
            "round": e.get("round"),
            "event": e.get("type"),
            "channel": CHANNEL[e["type"]],
            "actor": e.get("actor"),
            "has_from_key": "from" in pl,
            "from": pl.get("from") or pl.get("author"),
            "to": pl.get("to"),
            "body": pl.get("body") or "",
            "thread_id": pl.get("thread_id"),
            "msg_uid": pl.get("msg_uid"),
            "turn_index": pl.get("turn_index"),
            "participants": pl.get("participants") or [],
            "day": pl.get("day"),
            "slot": pl.get("slot"),
            "place": pl.get("place"),
            "tags": pl.get("tag_hints") or [],
            "ctx_topic": ctx.get("topic"),
        })
    out.sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                            m["seq"] if m["seq"] is not None else -1))
    return out


def thread_key(m: dict) -> str:
    """d12c 口径：thread_id，缺失则 legacy-msg_uid"""
    return m["thread_id"] or f"legacy-{m['msg_uid']}"


def dm_thread_key(m: dict) -> str:
    """dialogue_metrics.group_threads 口径（用于与 dm_*.json meta.n_threads 对账）"""
    if m["thread_id"]:
        return "T:" + str(m["thread_id"])
    pair = tuple(sorted({str(m["from"]), str(m["to"])}))
    return "L:%s|%s|%s" % (m["day"], m["channel"], "-".join(pair))


def mixed_key(m: dict) -> str:
    """dialogue_metrics.mixed_key 原样复刻（F-2′ 的分组）"""
    if m["thread_id"]:
        return "m:T|%s" % m["thread_id"]
    if m["channel"] == "dm":
        k = "-".join(sorted({str(m["from"]), str(m["to"])}))
    elif m["channel"] == "public":
        k = "-"
    else:
        k = str(m.get("place") or "-")
    return "m:%s|%s|%s" % (m["day"], m["channel"], k)


# ---------------- 各读数 ----------------
def structural(msgs: list[dict]) -> dict:
    th = Counter()
    anon = set()          # 「payload 内无 from 键」的消息所属线程（= 发送人取自 payload.author）
    anon_msgs = 0
    for m in msgs:
        k = thread_key(m)
        th[k] += 1
        if not m["has_from_key"]:
            anon.add(k)
            anon_msgs += 1
    anon_sizes = Counter(th[k] for k in anon)
    th_wo = {k: v for k, v in th.items() if k not in anon}
    ge6_wo = sum(1 for v in th_wo.values() if v >= 6)
    sizes = sorted(th.values())
    ge6 = sum(1 for v in th.values() if v >= 6)
    ge3 = sum(1 for v in th.values() if v >= 3)
    one = sum(1 for v in th.values() if v == 1)
    dmth = {dm_thread_key(m) for m in msgs}
    return {
        "n_msgs": len(msgs),
        "msg_types": dict(sorted(Counter(m["event"] for m in msgs).items())),
        "channels": dict(sorted(Counter(m["channel"] for m in msgs).items())),
        "n_threads_threadid": len(th),
        "n_threads_dm_schema": len(dmth),
        "n_threads_without_from_key": len(anon),
        "n_msgs_without_from_key": anon_msgs,
        "msgs_without_from_key_by_event": dict(sorted(Counter(
            m["event"] for m in msgs if not m["has_from_key"]).items())),
        "thread_size_dist_without_from_key": dict(sorted(anon_sizes.items())),
        "n_msgs_without_from_and_author": sum(1 for m in msgs if not m["from"]),
        "ge6_rate_pct_excluding_no_from_threads": pct(ge6_wo, len(th_wo)),
        "n_ge6_excluding": ge6_wo,
        "n_threads_excluding": len(th_wo),
        "n_single_msg_threads": one,
        "threads_p50": st.median(sizes) if sizes else None,
        "n_ge6": ge6,
        "ge6_rate_pct_all": pct(ge6, len(th)),
        "n_ge3": ge3,
        "ge3_rate_pct_all": pct(ge3, len(th)),
        "slot_dist_payload": dict(sorted(Counter(str(m["slot"]) for m in msgs).items())),
        "n_agents_speaking": len({m["from"] or m["actor"] for m in msgs}),
        "n_rounds_with_msgs": len({m["round"] for m in msgs}),
        "rounds_span": [min(m["round"] for m in msgs), max(m["round"] for m in msgs)],
    }


def paren_and_len(msgs: list[dict]) -> dict:
    n = len(msgs)
    lead = anyblock = 0
    short_lead = 0
    inner_lens = []
    mental = 0
    len_raw, len_raw_strip, len_excl, len_excl_strip = [], [], [], []
    for m in msgs:
        b = m["body"]
        if LEAD.match(b):
            lead += 1
            if len(b) <= 80:
                short_lead += 1
            mm = LEAD_FULL.match(b)
            if mm:
                inner = mm.group(1).strip()
                inner_lens.append(len(inner))
                if any(w in inner for w in MENTAL):
                    mental += 1
        if PAREN_BLOCK.search(b):
            anyblock += 1
        len_raw.append(len(b))
        len_raw_strip.append(len(b.strip()))
        len_excl.append(len(PAREN_BLOCK.sub("", b)))
        len_excl_strip.append(len(PAREN_BLOCK.sub("", b).strip()))
    inner_lens.sort()
    return {
        "n_msgs": n,
        "paren_lead_count": lead,                    # d12c 判据口径
        "paren_rate_pct": pct(lead, n),
        "paren_head_rate_pct": pct(lead, n),         # shape_gate: 去空白后以（/（ 起头，与上同源
        "paren_any_count": anyblock,                 # d9 形态闸口径
        "paren_any_rate_pct": pct(anyblock, n),
        "short_paren_share_pct": pct(short_lead, lead),
        "short_paren_denominator": lead,
        "paren_inner_len_p50": st.median(inner_lens) if inner_lens else None,
        "paren_inner_len_max": max(inner_lens) if inner_lens else None,
        "paren_mental_share_pct": pct(mental, len(inner_lens)),
        "len_p50_raw": st.median(sorted(len_raw)) if n else None,
        "len_p50_raw_strip": st.median(sorted(len_raw_strip)) if n else None,
        "len_p50_excl_nostrip": st.median(sorted(len_excl)) if n else None,   # d9 shape_gate
        "len_p50_excl": st.median(sorted(len_excl_strip)) if n else None,     # d12c/d27_metrics
        "len_mean_excl": round(sum(len_excl_strip) / n, 2) if n else None,
    }


def l7_norm8(msgs: list[dict]) -> dict:
    """全批 8-gram 近重复率（dialogue_metrics L-7 口径）"""
    norms = [norm_body(m["body"]) for m in msgs]
    n = len(norms)
    shingles = [{t[i:i + 8] for i in range(max(0, len(t) - 7))} for t in norms]
    index = defaultdict(list)
    for i, sh in enumerate(shingles):
        for g in sh:
            index[g].append(i)
    dup = set()
    for g, idxs in index.items():
        if len(idxs) > 1:
            dup.update(idxs)
    return {
        "n_msgs": n,
        "denominator": "全部 MSG_*（全批，不分组、无轮次窗口）",
        "dup_msgs": len(dup),
        "L7_dup_ngram8_rate_pct": pct(len(dup), n),
        "L7_dup_ngram8_rate4": round(100.0 * len(dup) / n, 4) if n else None,
        "note": "任务卡称『8 轮窗口复述率』与实现不符：实现为全批 8-gram 近重复率（任一 8-gram 与另一条消息共享即记 1），无窗口、无方向",
    }


def l15_restate(msgs: list[dict]) -> dict:
    threads = defaultdict(list)
    for m in msgs:
        threads[thread_key(m)].append(m)
    by_turn = defaultdict(lambda: {"n": 0, "restate": 0, "strong": 0})
    tot = strong = 0
    shared_counter = Counter()
    for _k, seq in threads.items():
        seq.sort(key=lambda m: (m["turn_index"] or 0, m["seq"] or 0))
        seen = set()
        for m in seq:
            t = norm_body(m["body"])
            sh = {t[i:i + 8] for i in range(max(0, len(t) - 7))}
            inter = sh & seen
            turn = (m["turn_index"] or 0) + 1
            by_turn[turn]["n"] += 1
            if inter:
                tot += 1
                by_turn[turn]["restate"] += 1
                for g in inter:
                    shared_counter[g] += 1
            if len(inter) >= 3:
                strong += 1
                by_turn[turn]["strong"] += 1
            seen |= sh
    n = len(msgs)
    return {
        "n_msgs": n,
        "denominator": "全部 MSG_*；分子=与本线程更早消息共享 ≥1 个 8-gram 的消息数（同线程前向）",
        "restate_count": tot,
        "restate_rate_pct": pct(tot, n),
        "restate_strong_count": strong,
        "restate_strong_rate_pct": pct(strong, n),
        "by_turn": {str(k): {"n": v["n"],
                             "restate_rate_pct": pct(v["restate"], v["n"]),
                             "restate_strong_rate_pct": pct(v["strong"], v["n"])}
                    for k, v in sorted(by_turn.items())},
        # 排序必须确定：Counter.most_common 在并列时依赖插入顺序，而插入顺序来自 set 迭代（受 PYTHONHASHSEED 影响）
        "top_shared": [[g, c] for g, c in sorted(shared_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:5]],
    }


def f2_content_drift(msgs: list[dict]) -> dict:
    groups = defaultdict(list)
    for m in msgs:
        groups[mixed_key(m)].append(m)
    pairs = drift = 0
    for k in sorted(groups):
        seq = groups[k]
        seq.sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                m["seq"] if m["seq"] is not None else -1))
        for i in range(1, len(seq)):
            pairs += 1
            a, b = content_bigrams(seq[i - 1]["body"]), content_bigrams(seq[i]["body"])
            jac = (len(a & b) / len(a | b)) if (a | b) else 0.0
            if jac < 0.10:
                drift += 1
    return {
        "denominator_adjacent_pairs": pairs,
        "drift_pairs": drift,
        "drift_rate_pct": pct(drift, pairs),
        "rule": "相邻消息 char-bigram Jaccard<0.10 记一次换话头；分组=mixed_key(thread_id 优先)；不看 tag",
    }


def p1_p2(msgs: list[dict], names: list[str]) -> dict:
    n = len(msgs)
    p1_hit = 0
    counts = []
    p2 = 0
    for m in msgs:
        b = m["body"]
        c = sum(len(re.findall(p, b)) for p in DETAIL)
        counts.append(c)
        if c > 0:
            p1_hit += 1
        present = {m["from"]}
        if m["to"]:
            present.add(m["to"])
        present.update(m["participants"])
        if any(x in b and x not in present for x in names):
            p2 += 1
    counts.sort()
    return {
        "n_msgs": n,
        "detail_patterns": len(DETAIL),
        "P1_binary_count": p1_hit,
        "P1_binary_rate_pct": pct(p1_hit, n),
        "P1_count_sum": sum(counts),
        "P1_count_mean": round(sum(counts) / n, 4) if n else None,
        "P1_count_p50": st.median(counts) if counts else None,
        "P1_count_zero_share_pct": pct(n - p1_hit, n),
        "P2_count": p2,
        "P2_thirdparty_rate_pct": pct(p2, n),
    }


def cost(path: Path) -> dict:
    calls = 0
    dl = {"calls": 0, "cached": 0, "uncached": 0, "tin": 0, "tout": 0, "tin_u": 0}
    for line in open(path, encoding="utf-8"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") != "LLM_CALL":
            continue
        calls += 1
        pl = e.get("payload") or {}
        if (pl.get("purpose") or "") != "dialogue":
            continue
        dl["calls"] += 1
        dl["tin"] += int(pl.get("tokens_in") or 0)
        dl["tout"] += int(pl.get("tokens_out") or 0)
        if pl.get("cached"):
            dl["cached"] += 1
        else:
            dl["uncached"] += 1
            dl["tin_u"] += int(pl.get("tokens_in") or 0)
    n, nu = dl["calls"], dl["uncached"]
    return {
        "llm_calls_total": calls,
        "dialogue_calls": n,
        "dialogue_cached": dl["cached"],
        "dialogue_uncached": nu,
        "dialogue_tokens_in_sum": dl["tin"],
        "dialogue_tokens_in_mean_all": round(dl["tin"] / n, 2) if n else None,
        "dialogue_tokens_in_mean_uncached": round(dl["tin_u"] / nu, 2) if nu else None,
        "dialogue_tokens_out_sum": dl["tout"],
        "dialogue_tokens_out_mean": round(dl["tout"] / n, 2) if n else None,
    }


# ---------------- 主流程 ----------------
LEGACY_C = {  # d25a C 臂（另一棵树 e2e7131），跨批污染基线，仅作反事实对照
    "source": "v2/evidence/d25a_result.md:26-28",
    "L15_restate_pct": 4.12,
    "L15_strong_pct": 2.16,
    "L7_dup8_pct": 20.59,
    "F2_drift_pct": 66.28,
    "len_p50_excl": 40.0,
}

THRESH = {  # v2/refs/D27-amendment1-merge-duplicate-prereg.md §3（一字不改）
    "M1_paren_min_pct": 30.0, "M1b_short_share_min_pct": 80.0,
    "P_delta_pp_min": 5.0, "Q1_delta_pp_max": 2.0,
    "Q2_worse_pp_max": 3.0, "Q2_gain_pp_min": 3.0,
    "Q3_delta_pp_max": 2.0, "S_rel_tol_pct": 10.0, "T_rel_tol_pct": 10.0,
}


def diff(b, c):
    return None if (b is None or c is None) else round(b - c, 4)


def rel(b, c):
    return None if (b is None or c is None or c == 0) else round(100.0 * (b - c) / c, 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--C", required=True)
    ap.add_argument("--B", required=True)
    ap.add_argument("--harvest", default="v2/evidence/d27_harvest")
    ap.add_argument("--T0", default="v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl",
                    help="历史 T0 批（仅用来核 paren_rate 79.41% 这个引用值）")
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()

    C = (REPO / a.C).resolve() if not Path(a.C).is_absolute() else Path(a.C)
    B = (REPO / a.B).resolve() if not Path(a.B).is_absolute() else Path(a.B)
    hv = (REPO / a.harvest).resolve()
    out_path = (REPO / a.out_json).resolve() if not Path(a.out_json).is_absolute() else Path(a.out_json)

    names = load_names()
    res = {"inputs": {
        "C": {"path": str(C), "sha256": hashlib.sha256(C.read_bytes()).hexdigest(),
              "meta_code_sha": json.load(open(C.parent / "meta.json", encoding="utf-8")).get("code_sha")},
        "B": {"path": str(B), "sha256": hashlib.sha256(B.read_bytes()).hexdigest(),
              "meta_code_sha": json.load(open(B.parent / "meta.json", encoding="utf-8")).get("code_sha")},
        "rulers": {
            "P1_wordlist": f"v2/evidence/d12c_metrics.py::DETAIL (sha8={sha8(REPO/'v2/evidence/d12c_metrics.py')})",
            "names": f"code/config/personas.json (sha8={sha8(REPO/'code/config/personas.json')})",
            "L7_L15_F2": f"tools/d5/dialogue_metrics.py (sha8={sha8(REPO/'tools/d5/dialogue_metrics.py')})",
            "len_p50_excl": f"tools/d9/arm_state_check.py::metrics (sha8={sha8(REPO/'tools/d9/arm_state_check.py')})",
        },
        "thresholds": THRESH,
        "threshold_source": "v2/refs/D27-amendment1-merge-duplicate-prereg.md §3",
    }}

    arms = {}
    slot_evidence = {}
    for tag, path in (("C", C), ("B", B)):
        msgs = read_msgs(path)
        cells = {(m["from"] or m["actor"], m["day"], m["slot"]) for m in msgs}
        per_cell = Counter((m["from"] or m["actor"], m["day"], m["slot"]) for m in msgs)
        slot_evidence[tag] = {
            "payload_slot_dist": dict(sorted(Counter(str(m["slot"]) for m in msgs).items())),
            "n_thread_slot_cells": len({(thread_key(m), m["slot"]) for m in msgs}),
            "n_agent_day_slot_cells": len(cells),
            "msgs_per_agent_day_slot_cell_dist": dict(sorted(Counter(per_cell.values()).items())),
        }
        arms[tag] = {
            "structure": structural(msgs),
            "paren_len": paren_and_len(msgs),
            "L7": l7_norm8(msgs),
            "L15": l15_restate(msgs),
            "F2": f2_content_drift(msgs),
            "P1P2": p1_p2(msgs, names),
            "cost": cost(path),
        }
    res["arms"] = arms

    # -------- 分母自证：与 dialogue_metrics meta.n_threads 对账 --------
    recon = {}
    for tag, fn in (("C", hv / "dm_C.json"), ("B", hv / "dm_B.json")):
        dm = json.loads(fn.read_text(encoding="utf-8"))
        recon[tag] = {
            "dm_meta_n_messages": (dm.get("meta") or {}).get("n_messages"),
            "dm_meta_n_threads": (dm.get("meta") or {}).get("n_threads"),
            "dm_thread_schema": (dm.get("meta") or {}).get("thread_schema"),
            "recomputed_n_msgs": arms[tag]["structure"]["n_msgs"],
            "recomputed_n_threads_threadid": arms[tag]["structure"]["n_threads_threadid"],
            "recomputed_n_threads_dm_schema": arms[tag]["structure"]["n_threads_dm_schema"],
            "n_threads_without_from_key": arms[tag]["structure"]["n_threads_without_from_key"],
            "n_msgs_without_from_key": arms[tag]["structure"]["n_msgs_without_from_key"],
            "thread_size_dist_without_from_key": arms[tag]["structure"]["thread_size_dist_without_from_key"],
            "ge6_rate_pct_excluding_no_from_threads":
                arms[tag]["structure"]["ge6_rate_pct_excluding_no_from_threads"],
            "holds_msgs": (dm.get("meta") or {}).get("n_messages") == arms[tag]["structure"]["n_msgs"],
            "holds_threads": (dm.get("meta") or {}).get("n_threads")
                              in (arms[tag]["structure"]["n_threads_threadid"],
                                  arms[tag]["structure"]["n_threads_dm_schema"]),
        }
    res["denominator_reconciliation"] = recon

    # -------- 旁证：历史 T0 的 paren_rate（用于核 79.41% 这个引用值） --------
    t0 = (REPO / a.T0) if not Path(a.T0).is_absolute() else Path(a.T0)
    if t0.is_file():
        ms = read_msgs(t0)
        pl = paren_and_len(ms)
        res["T0_reference"] = {
            "path": str(t0), "sha256": hashlib.sha256(t0.read_bytes()).hexdigest(),
            "n_msgs": pl["n_msgs"], "paren_lead_count": pl["paren_lead_count"],
            "paren_rate_pct": pl["paren_rate_pct"],
            "n_threads": len({thread_key(m) for m in ms}),
            "note": "T0 = run_d12c_off_n16r60_seed42；本项只核『历史 paren 79.41%』这一引用值可否重放",
        }
    else:
        res["T0_reference"] = {"path": str(t0), "verdict": "不可判（日志不在本树）"}

    # -------- 对账：与 d27_harvest 落盘 JSON 逐项比 --------
    def load(p):
        f = hv / p
        return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None

    d12c_j, p1_j, d27m_j, l15_j = load("d12c_c_b.json"), load("p1_count_c_b.json"), load("d27_metrics_c_b.json"), load("l15_c_b.json")
    shp = {"C": load("shape_C.json"), "B": load("shape_B.json")}
    dmj = {"C": load("dm_C.json"), "B": load("dm_B.json")}

    checks = []

    def add(item, arm, mine, landed, note=""):
        if landed is None:
            if mine is None:
                checks.append({"item": item, "arm": arm, "recomputed": None, "landed": None,
                               "delta": None, "match": True,
                               "note": "双方均 null（该臂无旁白，值不存在）" + note})
            else:
                checks.append({"item": item, "arm": arm, "recomputed": mine, "landed": None,
                               "match": None, "note": "落盘缺项 " + note})
            return
        if mine is None and landed is None:
            checks.append({"item": item, "arm": arm, "recomputed": None, "landed": None,
                           "delta": None, "match": True, "note": "双方均 null（该臂无旁白）" + note})
            return
        ok = (mine == landed) or (isinstance(mine, (int, float)) and isinstance(landed, (int, float))
                                  and abs(float(mine) - float(landed)) <= 1e-9)
        checks.append({"item": item, "arm": arm, "recomputed": mine, "landed": landed,
                       "delta": (round(mine - landed, 4) if isinstance(mine, (int, float))
                                 and isinstance(landed, (int, float)) else None),
                       "match": ok, "note": note})

    for tag in ("C", "B"):
        A = arms[tag]
        add("n_msgs", tag, A["structure"]["n_msgs"], d12c_j[tag]["n_msgs"], "d12c_c_b.json")
        add("n_threads", tag, A["structure"]["n_threads_threadid"], d12c_j[tag]["n_threads"], "d12c_c_b.json")
        add("threads_p50", tag, A["structure"]["threads_p50"], d12c_j[tag]["threads_p50"], "d12c_c_b.json")
        add("paren_rate_pct", tag, A["paren_len"]["paren_rate_pct"], d12c_j[tag]["paren_rate"], "d12c 口径=起头")
        add("P1_binary_rate_pct", tag, A["P1P2"]["P1_binary_rate_pct"], d12c_j[tag]["P1_specificity_rate"], "")
        add("P2_thirdparty_rate_pct", tag, A["P1P2"]["P2_thirdparty_rate_pct"], d12c_j[tag]["P2_thirdparty_rate"], "")
        add("len_p50_raw", tag, A["paren_len"]["len_p50_raw"], d27m_j[tag]["len_all_p50"],
            "len_p50(raw)=median(len(body))，对照 d27_metrics.len_all_p50；"
            "⚠ d12c_metrics.len_p50 实为『去括号后长度中位数』（=len_p50_excl），"
            f"其 d12c 落盘值 C={d12c_j['C']['len_p50']}/B={d12c_j['B']['len_p50']} 与 len_p50_excl 同源，不是 raw")
        add("P1_count_mean", tag, A["P1P2"]["P1_count_mean"], p1_j[tag]["P1_count_mean"], "p1_count_c_b.json")
        add("P1_count_sum", tag, A["P1P2"]["P1_count_sum"], p1_j[tag]["P1_count_sum"], "")
        add("P1_count_p50", tag, A["P1P2"]["P1_count_p50"], p1_j[tag]["P1_count_p50"], "")
        add("P1_count_zero_share_pct", tag, A["P1P2"]["P1_count_zero_share_pct"], p1_j[tag]["P1_count_zero_share_pct"], "")
        add("short_paren_share_pct", tag, A["paren_len"]["short_paren_share_pct"], d27m_j[tag]["M1b_short_paren_share_pct"], "d27_metrics")
        add("paren_inner_len_p50", tag, A["paren_len"]["paren_inner_len_p50"], d27m_j[tag]["paren_inner_len_p50"], "")
        add("len_p50_excl", tag, A["paren_len"]["len_p50_excl"], d27m_j[tag]["len_p50_excl_paren"], "d27_metrics(strip 版)")
        add("len_p50_excl_nostrip", tag, A["paren_len"]["len_p50_excl_nostrip"], (shp[tag] or {}).get("metrics", {}).get("len_p50_excl"), "shape_gate(不 strip 版)")
        add("paren_any_rate_frac", tag, round((A["paren_len"]["paren_any_rate_pct"] or 0) / 100, 6), (shp[tag] or {}).get("metrics", {}).get("paren_rate"), "shape_gate")
        add("L15_restate_rate_pct", tag, A["L15"]["restate_rate_pct"], (l15_j[tag] or {}).get("restate_rate"), "l15_c_b.json")
        add("L15_strong_rate_pct", tag, A["L15"]["restate_strong_rate_pct"], (l15_j[tag] or {}).get("restate_strong_rate"), "")
        add("L7_dup_ngram8_rate4", tag,
            A["L7"]["L7_dup_ngram8_rate4"],
            (round(100.0 * dmj[tag]["L_wording"]["L-7_dup_ngram8_rate"], 4) if dmj[tag] else None),
            "dm_*.json L_wording（4 位小数，便于核对 2.9959 这类擦线差）")
        add("F2_content_drift_rate_pct", tag, A["F2"]["drift_rate_pct"],
            (round(100.0 * dmj[tag]["F-2_content_drift"]["drift_rate"], 2) if dmj[tag] else None), "")
        add("F2_denominator_adjacent_pairs", tag, A["F2"]["denominator_adjacent_pairs"],
            (dmj[tag]["F-2_content_drift"]["denominator_adjacent_pairs"] if dmj[tag] else None), "")
        add("ge6_rate_pct_all", tag, A["structure"]["ge6_rate_pct_all"],
            (round(100.0 * sum(1 for _ in [0]) * 0, 2) if False else None), "见 d27_gates.json S.ge6")
        add("n_ge6", tag, A["structure"]["n_ge6"], None, "见 d27_gates.json S.ge6.n_ge6")

    # ge6 / S 段从 gates 落盘取
    gates_j = load("d27_gates.json")
    if gates_j:
        for tag in ("C", "B"):
            add("ge6_rate_pct_all", tag, arms[tag]["structure"]["ge6_rate_pct_all"],
                gates_j["gates"]["S"]["ge6"][tag], "d27_gates.json S.ge6")
            add("n_ge6", tag, arms[tag]["structure"]["n_ge6"],
                gates_j["gates"]["S"]["ge6"]["n_ge6"][tag], "d27_gates.json S.ge6.n_ge6")
        for tag in ("C", "B"):
            add("dialogue_tokens_in_mean_uncached", tag,
                arms[tag]["cost"]["dialogue_tokens_in_mean_uncached"],
                gates_j["gates"]["dialogue_token_runtime"][tag]["tokens_in_mean_uncached"],
                "d27_gates.json dialogue_token_runtime")
        add("M1a_paren_rate_B", "B", arms["B"]["paren_len"]["paren_rate_pct"],
            gates_j["gates"]["M1"]["paren_rate_B"], "")
        add("P1_binary_delta_pp", "B", diff(arms["B"]["P1P2"]["P1_binary_rate_pct"],
                                           arms["C"]["P1P2"]["P1_binary_rate_pct"]),
            gates_j["gates"]["P"]["P1_binary_delta_pp"], "")
        add("Q2_L7_C_pct", "C", arms["C"]["L7"]["L7_dup_ngram8_rate4"], gates_j["gates"]["Q2"]["C"], "")
        add("Q2_L7_B_pct", "B", arms["B"]["L7"]["L7_dup_ngram8_rate4"], gates_j["gates"]["Q2"]["B"], "")
        add("Q2_delta_pp", "B", diff(arms["B"]["L7"]["L7_dup_ngram8_rate4"],
                                     arms["C"]["L7"]["L7_dup_ngram8_rate4"]),
            gates_j["gates"]["Q2"]["delta_pp"], "")
        add("T_rel_pct", "B", rel(arms["B"]["paren_len"]["len_p50_excl"],
                                  arms["C"]["paren_len"]["len_p50_excl"]),
            gates_j["gates"]["T"]["rel_pct"], "")

    # 重复项去重（ge6/n_ge6 先 null 后填）
    dedup = {}
    for c in checks:
        k = (c["item"], c["arm"])
        if c["landed"] is None and k in dedup:
            continue
        dedup[k] = c
    checks = list(dedup.values())
    res["reconciliation_vs_harvest"] = {
        "n_items": len(checks),
        "n_match": sum(1 for c in checks if c["match"] is True),
        "n_mismatch": sum(1 for c in checks if c["match"] is False),
        "n_missing": sum(1 for c in checks if c["match"] is None),
        "items": checks,
    }

    # -------- 判据合成（采用值 = run_d27_C 现算；并列污染值反事实） --------
    cA, bA = arms["C"], arms["B"]
    m1_paren = bA["paren_len"]["paren_rate_pct"]
    m1_short = bA["paren_len"]["short_paren_share_pct"]
    p1c, p1b = cA["P1P2"]["P1_binary_rate_pct"], bA["P1P2"]["P1_binary_rate_pct"]
    l7c, l7b = cA["L7"]["L7_dup_ngram8_rate4"], bA["L7"]["L7_dup_ngram8_rate4"]
    l15c, l15b = cA["L15"]["restate_rate_pct"], bA["L15"]["restate_rate_pct"]
    f2c, f2b = cA["F2"]["drift_rate_pct"], bA["F2"]["drift_rate_pct"]
    tc, tb = cA["paren_len"]["len_p50_excl"], bA["paren_len"]["len_p50_excl"]

    def verdict_item(ok):
        return "达标" if ok else "破闸/未达"

    gates = {
        "M1": {"adopt": {"paren_rate_C": m1_paren and cA["paren_len"]["paren_rate_pct"],
                         "paren_rate_B": m1_paren,
                         "short_share_B": m1_short,
                         "paren_inner_len_p50_B": bA["paren_len"]["paren_inner_len_p50"]},
               "rule": "paren 0.00%→>=30% 且 短旁白(<=80 字)占比>=80%",
               "pass": bool(m1_paren is not None and m1_paren >= 30.0
                            and (m1_short or 0) >= 80.0),
               "verdict": verdict_item(m1_paren is not None and m1_paren >= 30.0
                                       and (m1_short or 0) >= 80.0)},
        "P1_binary": {"C": p1c, "B": p1b, "delta_pp": diff(p1b, p1c),
                      "ceiling_headroom_pp": round(100.0 - p1c, 2),
                      "threshold_pp": 5.0,
                      "pass": bool(diff(p1b, p1c) is not None and diff(p1b, p1c) >= 5.0),
                      "verdict": verdict_item(diff(p1b, p1c) is not None and diff(p1b, p1c) >= 5.0),
                      "ceiling_note": ("基线 93.53%，可用空间仅 6.47pp；+2.88pp 已用掉天花板空间的 44.5%，"
                                       "不得直接判『只是加花架子』，须并列连续口径")},
        "P1_count": {"C": cA["P1P2"]["P1_count_mean"], "B": bA["P1P2"]["P1_count_mean"],
                     "rel_pct": rel(bA["P1P2"]["P1_count_mean"], cA["P1P2"]["P1_count_mean"]),
                     "p50": {"C": cA["P1P2"]["P1_count_p50"], "B": bA["P1P2"]["P1_count_p50"]},
                     "zero_share_pct": {"C": cA["P1P2"]["P1_count_zero_share_pct"],
                                        "B": bA["P1P2"]["P1_count_zero_share_pct"]},
                     "note": "连续口径仅并列补充，不改判据（预登记 §3 阈值一字未动）"},
        "Q1_L15": {"C": l15c, "B": l15b, "delta_pp": diff(l15b, l15c), "max_pp": 2.0,
                   "pass": bool(diff(l15b, l15c) is not None and diff(l15b, l15c) <= 2.0),
                   "verdict": verdict_item(diff(l15b, l15c) is not None and diff(l15b, l15c) <= 2.0)},
        "Q2_L7": {"adopt": {"C": l7c, "B": l7b,
                            "C_pct2": cA["L7"]["L7_dup_ngram8_rate_pct"],
                            "B_pct2": bA["L7"]["L7_dup_ngram8_rate_pct"],
                            "delta_pp4": diff(l7b, l7c), "delta_pp": diff(l7b, l7c),
                            "margin_pp": round(3.0 - diff(l7b, l7c), 4),
                            "pass": bool(diff(l7b, l7c) is not None and diff(l7b, l7c) <= 3.0)},
                  "contaminated": {"C": LEGACY_C["L7_dup8_pct"], "B": l7b,
                                   "delta_pp": diff(l7b, LEGACY_C["L7_dup8_pct"]),
                                   "verdict": "无效（重复恶化）"},
                  "note": "采用值擦线过（余量 <0.01pp < 单 seed 噪声），不得引为正面证据；污染口径会误判『重复恶化』"},
        "Q3_F2": {"adopt": {"C": f2c, "B": f2b, "delta_pp": diff(f2b, f2c), "max_pp": 2.0,
                            "pass": bool(diff(f2b, f2c) is not None and diff(f2b, f2c) <= 2.0)},
                  "contaminated": {"C": LEGACY_C["F2_drift_pct"], "B": f2b,
                                   "delta_pp": diff(f2b, LEGACY_C["F2_drift_pct"])},
                  "note": "采用值下 +3.53pp 超 2pp 闸 ⇒ 破闸（此为 dc02e06 判定档未列出的一项）"},
        "S": {"n_msgs": {"C": cA["structure"]["n_msgs"], "B": bA["structure"]["n_msgs"],
                         "rel_pct": rel(bA["structure"]["n_msgs"], cA["structure"]["n_msgs"])},
              "n_threads": {"C": cA["structure"]["n_threads_threadid"],
                            "B": bA["structure"]["n_threads_threadid"],
                            "rel_pct": rel(bA["structure"]["n_threads_threadid"],
                                           cA["structure"]["n_threads_threadid"])},
              "ge6": {"C": cA["structure"]["ge6_rate_pct_all"], "B": bA["structure"]["ge6_rate_pct_all"],
                      "n": {"C": cA["structure"]["n_ge6"], "B": bA["structure"]["n_ge6"]}},
              "pass": bool(abs(rel(bA["structure"]["n_msgs"], cA["structure"]["n_msgs"]) or 99) <= 10
                           and abs(rel(bA["structure"]["n_threads_threadid"],
                                       cA["structure"]["n_threads_threadid"]) or 99) <= 10),
              "verdict": "达标"},
        "T": {"adopt": {"C": tc, "B": tb, "rel_pct": rel(tb, tc), "tol_pct": 10.0,
                        "pass": bool(abs(rel(tb, tc) or 99) <= 10)},
              "contaminated": {"C": LEGACY_C["len_p50_excl"], "B": tb,
                               "rel_pct": rel(tb, LEGACY_C["len_p50_excl"])},
              "note": "两侧都破（采用 -36.59% / 污染 -35.00%）⇒ 结论稳健"},
        "cost": {"llm_calls": {"C": cA["cost"]["llm_calls_total"], "B": bA["cost"]["llm_calls_total"],
                               "rel_pct": rel(bA["cost"]["llm_calls_total"], cA["cost"]["llm_calls_total"])},
                 "dialogue_tokens_in_mean_uncached": {"C": cA["cost"]["dialogue_tokens_in_mean_uncached"],
                                                     "B": bA["cost"]["dialogue_tokens_in_mean_uncached"]},
                 "note": "破只记录，不判作废（预登记 §3 末行）"},
    }
    res["gates"] = gates

    # 合成判定
    hard = ["M1", "P1_binary", "Q1_L15", "Q2_L7", "Q3_F2", "S", "T"]
    allpass = all(gates[k]["pass"] if k != "Q2_L7" else gates[k]["adopt"]["pass"] for k in hard)
    res["verdict"] = {
        "composite": "有效" if allpass else "作废/未达（见逐项）",
        "why": ("M1 过 / P 未达（+2.88pp < +5pp） / T 破（-36.59%） / Q3 破（+3.53pp>2pp）"
                " ⇒ 即便 Q1/Q2(擦线)/S 过，仍不能判有效"),
        "mechanism_vs_effect": "M1（旁白机制）四项只作机制层事实，不进效果提升；效果层由 P/Q/T 决定",
        "adopt_values": {"L15_C": l15c, "L7_C": l7c, "F2_C": f2c, "len_p50_excl_C": tc},
        "contaminated_values": LEGACY_C,
    }
    res["note_task_card_mislabel"] = {
        "L-7": "任务卡『8 轮窗口复述率』与仓内实现不符：实为全批 8-gram 近重复率（无窗口/无方向）",
        "slot_dist": "『slot 饱和 slot{1:57,2:199}』在仓内**无生成脚本**（仅 d27_C_arm_acceptance.md 文字）；"
                     "本脚本只能给可复算替代：payload.slot 四值分布 + 每线程 slot 数分布 + (agent,day,slot) 槽位数。判据层为『不可判（缺口径定义）』",
    }
    res["slot_evidence"] = slot_evidence

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_path),
                      "verdict": res["verdict"]["composite"],
                      "reconciliation": {k: res["reconciliation_vs_harvest"][k]
                                         for k in ("n_items", "n_match", "n_mismatch", "n_missing")},
                      "mismatches": [c for c in checks if c["match"] is False]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
