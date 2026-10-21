#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""g1_metrics_fixed.py —— G 系列「第三方提及 / 越界提及」权威读数脚本（修正版）

作者：verifier（独立验证与审计专家）｜R15 权威版
口径依据：`experiments/gossip-third-party/DESIGN-preregistration.md` §2.1/§2.2/§2.4
        + `recon/r15-guards-frozen.md` §6（本轮冻结参数，唯一判定依据）

═══════════════════════════════════════════════════════════════════════
## 1. 修正了什么（以及原实现为何恒真）

PREREG:72 要求「排除提到自己在场伙伴 —— 已由 `− participants` 实现」。但
`experiments/gossip-third-party/g_metrics.py:184-189, 232-234` 是这样写的：

    parts = participants_of(m, schema)          # {'P002','P004'}   ← 日志里 participants 是 persona_id
    own   = pid2name.get(m["author"])           # '秀娘'
    third = [nm for nm in names if nm != own and nm not in parts]     # nm 是 '老石'

`'老石' not in {'P002','P004'}` **恒真** ⇒ 在场伙伴从未被排除。
实测基线臂 b0（`run_g1_b0_n16r60_seed42`）：现状脚本得 **301/510 = 59.02%**，
其中绝大多数是「DM 里喊一声对方名字」（称呼率），不是预注册定义的第三方提及；
按契约口径复算为 **2/510 = 0.39%**。

本脚本把 participants 先按 `persona_id -> 主干名` 映射再比较（`participants_names()`），
其余口径（主干名子串匹配、per-message 分母、G-1b 宁漏不虚增、L-2/L-8/U8b 定义）与 PREREG 一致，
**不做任何放松**。原脚本本轮不修改（保留历史可追溯），本文件 supersede 其口径。

## 2. 与 `v2/evidence/g1_metrics_crosscheck.py`（report-writer 独立实现）的关系

保留两份的理由 = **互证、防单实现 bug**：
 - 本文件为权威版（口径来源见上），crosscheck 版由另一人从不同代码路径独立实现；
 - 二者对同一 `run.jsonl` 必须给出**逐位一致**的分子/分母/比率/Wilson CI；
 - 若不一致，以本文件为准并必须查清差异（不得择一取用）。

## 3. 噪声带：为什么 n 必须跟着分母走

PREREG:100 引的 `±10.6pp` 是 **n=170 档**（v0-anchor 分母 187）。本轮两臂分母 ≈510，
必须用 n=510 档。本脚本按 `v2/evidence/d3_noiseband_bootstrap.py` 的**发布方法**复算：
「同配置语料池有放回重采样 m 条 × 2 个伪臂，B=2000, seed=42，取 2.5/97.5 分位」。

⚠️ 注意：`d3_noiseband_bootstrap.py:70-75` 里 `B_ = rows["t355"]` 被赋值但**从未使用**，
两个伪臂都从 `t300` 池重采样 ⇒ 已发布带是**单池（t300）抽样噪声带**，不是 t300-vs-t355 的池间差。
本脚本如实复现该发布方法（`pool='t300'`），并额外给一份 `two_pool` 敏感性带（t300 池 vs t355 池），
供审计披露；**判定用发布方法那一条**（对 L-7 上升方向更严，属保守选择）。

## 4. 用法（两种 CLI 写法完全等价）

    python3 v2/evidence/g1_metrics_fixed.py \
        --run v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl \
        --meta v2/evidence/run_g1_b0_n16r60_seed42/meta.json \
        --out v2/evidence/g1_readings_b0_fixed.json

    # 等价旧写法：--log / --out-json / --names / --personas
    # 噪声带来源可指定基线臂（推荐：两臂都用同一来源的带）
    #   --bootstrap-from v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl

只读、零 LLM、确定性（B=2000, seed=42）。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
CHANNEL = {"MSG_DM": "dm", "MSG_PUBLIC": "public", "MSG_GROUP": "group"}
PAREN_OPEN = ("（", "(")
PAREN_BLOCK = re.compile(r"[（(]([^）)]{0,60})[）)]")
AGENT_ID_RE = re.compile(r"P\d{3}(?!\d)")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NAMES = REPO_ROOT / "code" / "config" / "personas.json"
DEFAULT_D3_CORPUS = REPO_ROOT / "v2" / "evidence" / "d3_annotated_corpus.jsonl"


# ------------------------------------------------------------------ 名字表
def load_names(path: Path) -> tuple[dict, dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    pid2name, name2pid = {}, {}
    for p in d.get("personas", []):
        pid = str(p.get("persona_id") or "")
        nm = str(p.get("display_name") or "").split("·")[-1].strip()
        if pid and nm:
            pid2name[pid] = nm
            name2pid[nm] = pid
    if not pid2name:
        raise SystemExit("[FAIL] personas.json 解析出 0 个主干名")
    dup = [k for k, v in Counter(pid2name.values()).items() if v > 1]
    if dup:
        raise SystemExit(f"[FAIL] 主干名重名，G-1 无法唯一归因：{dup}")
    return pid2name, name2pid


# ------------------------------------------------------------------ 读日志
def load_run(path: str) -> dict:
    msgs, place_ev = [], defaultdict(list)
    nlines = 0
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        nlines += 1
        e = json.loads(line)
        t, rnd, seq = e.get("type"), e.get("round"), e.get("seq")
        p = e.get("payload") or {}
        if t in ("PLACE_ARRIVED", "PLACE_MOVE"):
            aid = p.get("agent_id") or e.get("actor")
            plc = p.get("place") or p.get("to_place")
            if aid and plc and rnd is not None:
                place_ev[(int(rnd), str(aid))].append((int(seq or 0), str(plc)))
            continue
        if t not in MSG_TYPES:
            continue
        msgs.append({
            "seq": seq, "round": rnd, "type": t, "channel": CHANNEL[t],
            "author": str(p.get("author") or p.get("from") or "") or None,
            "to": p.get("to"), "place": p.get("place"), "topic": p.get("topic"),
            "participants": p.get("participants"), "thread_id": p.get("thread_id"),
            "body": p.get("body") or "",
        })
    for k in place_ev:
        place_ev[k].sort()
    schema = "explicit" if any(m["thread_id"] for m in msgs) else "legacy"
    return {"path": path, "msgs": msgs, "place_ev": dict(place_ev),
            "thread_schema": schema, "lines": nlines}


def place_of(place_ev, rnd, pid, seq):
    if rnd is None:
        return None
    arr = place_ev.get((int(rnd), str(pid)))
    if not arr:
        return None
    s = int(seq or 0)
    before = [x for x in arr if x[0] <= s]
    return before[-1][1] if before else arr[0][1]


def participants_names(m: dict, pid2name: dict, name2pid: dict) -> tuple[set, str]:
    """在场参与者主干名集合 —— **本脚本相对 g_metrics.py 的唯一口径修正点**。

    日志里 participants 是 persona_id（`["P002","P004"]`），必须映射成主干名
    （`{'老石','秀娘'}`）后才能与正文命中的名字比较；否则 `nm not in parts` 恒真。
    兼容 participants 直接给主干名的情况（防御性），并回报实际值类型供审计。
    """
    raw = m.get("participants")
    if raw:
        out, kinds = set(), set()
        for v in [str(x) for x in raw]:
            if v in pid2name:
                out.add(pid2name[v]); kinds.add("persona_id")
            elif v in name2pid:
                out.add(v); kinds.add("name")
            else:
                kinds.add("unknown")
        return out, "+".join(sorted(kinds))
    s = {m["author"]} if m["author"] else set()
    if m["channel"] == "dm" and m.get("to"):
        s.add(str(m["to"]))
    return {pid2name.get(x, x) for x in s}, "fallback_from_to"


# ------------------------------------------------------------------ 统计工具
def rate(k, n):
    return round(100.0 * k / n, 2) if n else None


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(100 * max(0.0, c - h), 2), round(100 * min(1.0, c + h), 2)]


def grams8(s: str) -> set:
    s = re.sub(r"\s+", "", s)
    return {s[i:i + 8] for i in range(len(s) - 7)}


# ------------------------------------------------------------------ 读数
def compute(run: dict, pid2name: dict, name2pid: dict) -> dict:
    msgs, place_ev = run["msgs"], run["place_ev"]
    n = len(msgs)
    all_names = list(name2pid)

    hits, off_strict, off_upper = [], [], []
    base_unknown = base_unknown_upper = lookup_unknown = 0
    parts_kind = Counter()
    excluded_by_participants = 0

    for m in msgs:
        found = [nm for nm in all_names if nm in m["body"]]
        if not found:
            continue
        own = pid2name.get(m["author"] or "")
        pn, kind = participants_names(m, pid2name, name2pid)
        parts_kind[kind] += 1
        third = [nm for nm in found if nm != own and nm not in pn]
        if not third:
            if [nm for nm in found if nm != own]:
                excluded_by_participants += 1     # 修正项生效的计数证据
            continue
        rec = {"seq": m["seq"], "round": m["round"], "channel": m["channel"],
               "author": m["author"], "author_name": own,
               "mentions": third, "place": m["place"], "body": m["body"]}
        hits.append(rec)

        def judging(base):
            nonlocal lookup_unknown
            if not base:
                return False, {}, False
            places = {nm: place_of(place_ev, m["round"], name2pid.get(nm), m["seq"]) for nm in third}
            real = {k: v for k, v in places.items() if v is not None}
            if not real:
                lookup_unknown += 1
                return False, places, True
            return any(v != base for v in real.values()), places, False

        if not m["place"]:
            base_unknown += 1
        else:
            bad, places, _ = judging(m["place"])
            if bad:
                off_strict.append({**rec, "speaking_place": m["place"], "mentioner_places": places})

        base_u = m["place"] or place_of(place_ev, m["round"], m["author"] or "", m["seq"])
        if not base_u:
            base_unknown_upper += 1
        else:
            bad, places, _ = judging(base_u)
            if bad:
                off_upper.append({**rec, "speaking_place": base_u, "mentioner_places": places})

    l8 = sum(1 for m in msgs if AGENT_ID_RE.search(m["body"]))
    l2 = sum(1 for m in msgs if (m["body"].lstrip()[:1] or "") in PAREN_OPEN)
    l3 = sum(1 for m in msgs if PAREN_BLOCK.search(m["body"]))
    g8 = defaultdict(list)
    for i, m in enumerate(msgs):
        for g in grams8(m["body"]):
            g8[g].append(i)
    l7_flags = [1 if any(len(v) > 1 for v in (g8[g] for g in grams8(m["body"]))) else 0 for m in msgs]
    l7 = sum(l7_flags)

    by_ch_total = Counter(m["channel"] for m in msgs)
    by_ch_hit = Counter(h["channel"] for h in hits)
    return {
        "path": run["path"],
        "lines_in_log": run["lines"],
        "n_msgs": n,
        "channels": dict(by_ch_total),
        "thread_schema": run["thread_schema"],
        "participants_value_kinds": dict(parts_kind),
        "G-1_third_party_mention": {
            "hit": len(hits), "denom": n, "rate_pct": rate(len(hits), n),
            "ci95_pct": wilson(len(hits), n), "unit": "per-message",
            "by_channel": {ch: {"hit": by_ch_hit.get(ch, 0), "denom": by_ch_total.get(ch, 0),
                                "rate_pct": rate(by_ch_hit.get(ch, 0), by_ch_total.get(ch, 0))}
                           for ch in ("dm", "group", "public")},
            "mention_targets": dict(Counter(nm for h in hits for nm in h["mentions"]).most_common()),
            "excluded_as_in_room_partner_msgs": excluded_by_participants,
            "needs_manual_review_seq": [h["seq"] for h in hits],
        },
        "G-1b_strict_offscreen_mention": {
            "hit": len(off_strict), "denom": n, "rate_pct": rate(len(off_strict), n),
            "ci95_pct": wilson(len(off_strict), n), "unit": "per-message",
            "unknown_place_base": base_unknown, "unknown_place_lookups": lookup_unknown,
            "needs_manual_review_seq": [h["seq"] for h in off_strict],
        },
        "G-1b_upper_offscreen_mention": {
            "hit": len(off_upper), "denom": n, "rate_pct": rate(len(off_upper), n),
            "ci95_pct": wilson(len(off_upper), n), "unit": "per-message",
            "unknown_place_base": base_unknown_upper, "unknown_place_lookups": lookup_unknown,
            "needs_manual_review_seq": [h["seq"] for h in off_upper],
        },
        "guards": {
            "L-2_narration_head": {"hit": l2, "denom": n, "rate_pct": rate(l2, n)},
            "L-3_paren_any": {"hit": l3, "denom": n, "rate_pct": rate(l3, n)},
            "L-8_naked_id": {"hit": l8, "denom": n, "rate_pct": rate(l8, n)},
            "L-7_ngram8_shared_U8b": {"hit": l7, "denom": n, "rate_pct": rate(l7, n)},
        },
        "_labels": {
            "G-1_third_party_mention": [1 if m["seq"] in {h["seq"] for h in hits} else 0 for m in msgs],
            "G-1b_upper_offscreen_mention": [1 if m["seq"] in {h["seq"] for h in off_upper} else 0 for m in msgs],
            "L-2_narration_head": [1 if (m["body"].lstrip()[:1] or "") in PAREN_OPEN else 0 for m in msgs],
            "L-8_naked_id": [1 if AGENT_ID_RE.search(m["body"]) else 0 for m in msgs],
            "L-7_ngram8_shared_U8b": l7_flags,
        },
        "_hits": hits,
        "_off_hits_strict": off_strict,
        "_off_hits_upper": off_upper,
    }


# ------------------------------------------------------------------ 噪声带
def boot_single_pool(labels: list, denom: int, B=2000, seed=42):
    """发布方法：两个伪臂都从**同一标签池**有放回重采样（d3_noiseband_bootstrap.py 的实际做法）。"""
    n = len(labels)
    if not n:
        return None
    rng = random.Random(seed)
    d = []
    for _ in range(B):
        a = sum(labels[rng.randrange(n)] for _ in range(denom)) / denom
        b = sum(labels[rng.randrange(n)] for _ in range(denom)) / denom
        d.append(100 * (a - b))
    d.sort()
    lo, hi = d[int(0.025 * (B - 1))], d[int(0.975 * (B - 1))]
    return {"band_pp": [round(lo, 2), round(hi, 2)], "width_pp": round(hi - lo, 2),
            "method": "single_pool_bootstrap", "B": B, "seed": seed}


def boot_d3_pooled(key: str, denom: int, corpus: Path, two_pool=False, B=2000, seed=42):
    """t300/t355 语料同法换分母。
    two_pool=False ⇒ 复现发布方法（两伪臂都取 t300 池）；
    two_pool=True  ⇒ 敏感性带（一伪臂 t300 池、一伪臂 t355 池）。
    """
    if not corpus.exists():
        return None
    rows = defaultdict(list)
    for line in open(corpus, encoding="utf-8"):
        r = json.loads(line)
        rows[r["run"]].append(r)
    if "t300" not in rows or (two_pool and "t355" not in rows):
        return None
    A = rows["t300"]
    Bp = rows["t355"] if two_pool else A

    def rt(sample):
        return sum(1 for r in sample if r.get(key) is True) / len(sample) if sample else None

    rng = random.Random(seed)
    d = []
    for _ in range(B):
        ra = rt([A[rng.randrange(len(A))] for _ in range(denom)])
        rb = rt([Bp[rng.randrange(len(Bp))] for _ in range(denom)])
        if ra is None or rb is None:
            continue
        d.append(100 * (ra - rb))
    if not d:
        return None
    d.sort()
    lo, hi = d[int(0.025 * (len(d) - 1))], d[int(0.975 * (len(d) - 1))]
    return {"band_pp": [round(lo, 2), round(hi, 2)], "width_pp": round(hi - lo, 2),
            "method": "d3_two_pool_bootstrap" if two_pool else "d3_single_pool_bootstrap",
            "B": B, "seed": seed}


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", "--log", dest="log", required=True, help="run.jsonl 路径")
    ap.add_argument("--meta", default=None, help="同批次 meta.json（可选，用于锚点/完整性核对）")
    ap.add_argument("--personas", "--names", dest="names", default=str(DEFAULT_NAMES))
    ap.add_argument("--bootstrap-from", default=None,
                    help="噪声带标签来源 run.jsonl（推荐给基线臂，使两臂共用同一条带）；缺省=被测 run 自身")
    ap.add_argument("--d3-corpus", default=str(DEFAULT_D3_CORPUS))
    ap.add_argument("--out", "--out-json", dest="out", required=True)
    a = ap.parse_args()

    pid2name, name2pid = load_names(Path(a.names))
    run = load_run(a.log)
    r = compute(run, pid2name, name2pid)
    n = r["n_msgs"]

    meta_info = None
    if a.meta and Path(a.meta).exists():
        m = json.loads(Path(a.meta).read_text(encoding="utf-8"))
        meta_info = {k: m.get(k) for k in ("code_sha", "code_sha_end", "events", "wc_l", "rounds", "n",
                                           "seed", "model", "provider", "llm_calls", "llm_cached",
                                           "llm_cached_ratio", "degraded_calls", "msg_counts", "run_sha256")}
        meta_info["_integrity_lines_equals_events"] = (
            m.get("wc_l") == m.get("events") == r["lines_in_log"])

    # ---- 噪声带
    band_run, band_note = r, "own_labels"
    if a.bootstrap_from:
        band_run = compute(load_run(a.bootstrap_from), pid2name, name2pid)
        band_note = f"from {a.bootstrap_from}"

    bands = {}
    for name, lab in band_run["_labels"].items():
        bands[name] = {"own_label_single_pool": boot_single_pool(lab, n)}
    d3_map = {"L-2_narration_head": "U2_narration_proxy",
              "L-8_naked_id": "U4_agent_id_leak",
              "L-7_ngram8_shared_U8b": "U8b_ngram_shared"}
    for name, key in d3_map.items():
        b1 = boot_d3_pooled(key, n, Path(a.d3_corpus), two_pool=False)
        b2 = boot_d3_pooled(key, n, Path(a.d3_corpus), two_pool=True)
        if b1:
            bands[name]["d3_single_pool_published_method"] = b1
        if b2:
            bands[name]["d3_two_pool_sensitivity"] = b2

    out = {
        "generated_by": "v2/evidence/g1_metrics_fixed.py（R15 权威版，作者 verifier）",
        "supersedes": "experiments/gossip-third-party/g_metrics.py:184-189,232-234"
                      "（participants 为 persona_id 却与主干名比较 ⇒ 'nm not in parts' 恒真）",
        "criterion_source": "experiments/gossip-third-party/DESIGN-preregistration.md §2.1/§2.2/§2.4"
                            " + recon/r15-guards-frozen.md §6",
        "names_file": a.names,
        "n_names": len(pid2name),
        "meta": meta_info,
        "readings": r,
        "noiseband": {
            "denom": n, "label_source": band_note, "bands": bands,
            "note": "判定用 d3_single_pool_published_method（复现 d3_noiseband_bootstrap.py 发布方法）；"
                    "own_label_single_pool 为本池同分布零假设带；d3_two_pool_sensitivity 仅供披露。"
                    "带随分母变化，禁止跨档混用（n=170 的 ±10.6pp 不适用于 n≈510）。",
        },
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    pm, up = r["G-1_third_party_mention"], r["G-1b_upper_offscreen_mention"]
    st = r["G-1b_strict_offscreen_mention"]
    print(f"== {a.log}")
    print(f"   n_msgs={n}  lines={r['lines_in_log']}  schema={r['thread_schema']}  channels={r['channels']}")
    print(f"   participants 值类型={r['participants_value_kinds']}  因在场伙伴被排除条数={pm['excluded_as_in_room_partner_msgs']}")
    print(f"   G-1 第三方提及    {pm['hit']}/{pm['denom']} = {pm['rate_pct']}%  ci={pm['ci95_pct']}  targets={pm['mention_targets']}")
    print(f"   G-1b_strict 越界  {st['hit']}/{st['denom']} = {st['rate_pct']}%  人核seq={st['needs_manual_review_seq']}")
    print(f"   G-1b_upper  越界  {up['hit']}/{up['denom']} = {up['rate_pct']}%  人核seq={up['needs_manual_review_seq']}")
    for k, v in r["guards"].items():
        print(f"   {k:24s} {v['hit']}/{v['denom']} = {v['rate_pct']}%")
    print(f"   noiseband (denom={n}, {band_note}):")
    for k, v in bands.items():
        o = v["own_label_single_pool"]["band_pp"] if v.get("own_label_single_pool") else None
        d1 = v.get("d3_single_pool_published_method", {}).get("band_pp")
        print(f"     {k:30s} own={o}  d3_published={d1}")
    print(f"[ok] json -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
