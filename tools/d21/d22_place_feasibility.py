#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.3 离线可行性：**同地点优先选对端**（place-aware partner choice）值不值得跑批？

背景：`planner._participants` 从**全部 15 人**均匀抽，**连 place 都不读**
（见 `v2/evidence/d21_partner_choice.md` §0）。所以现在"在饭馆吃饭"也可能约城另一头的人。
本工具离线模拟"只在**同一 round 同 place** 的人里抽"的效果。

三档（遵 runbook §3.115，判定只用 B−C）：
  A 现状      = 原 `_pick`（%len），目标 100% 复现历史（自检）
  C 等权映射  = 全员池 + 累积权重轴（w≡1）      ⇒ 隔离**映射伪影**
  B 同地点    = 同 place 池（回退：±1 round → 全员）+ 累积权重轴（w≡1）
判据读数：`repeat_pair_rate`、`same_place_hit_rate`（选中者是否与发起人同 place）、换人率。

⚠ 近似：真实"谁在某 place"由 plan 决定；本工具用**该 round 内发过消息的 (agent,place)** 近似在场集合。
  若某 round 在场信息稀疏，会退化到 ±1 round 或全员 —— 退化比例单独报（`fallback_rate_*`）。

用法：python3 tools/d21/d22_place_feasibility.py --log path [--out-json ...]
"""
import argparse, hashlib, json
from collections import defaultdict, Counter

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
_SLOTS = ["morning", "afternoon", "evening", "night"]


def hsh(seed):
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)


def orig_pick(seed, options):
    return options[hsh(seed) % len(options)]


def axis_pick(seed, options):
    """等权累积轴取点：与加权抽同映射，w≡1。"""
    u = (hsh(seed) / float(1 << 32)) * len(options)
    return options[min(int(u), len(options) - 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()

    rows = []
    for line in open(a.log, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG_TYPES or e.get("round") is None:
            continue
        pl = e.get("payload") or {}
        if not pl.get("from"):
            continue
        rows.append({"r": e["round"], "frm": pl["from"], "to": pl.get("to"),
                     "turn": pl.get("turn_index"), "place": pl.get("place"),
                     "topic": pl.get("topic")})
    rows.sort(key=lambda x: (x["r"], str(x.get("topic"))))
    agents = sorted({x["frm"] for x in rows} | {x["to"] for x in rows if x["to"]})

    # 每 round 的在场集合：{round: {place: set(agents)}}
    pres = defaultdict(lambda: defaultdict(set))
    for x in rows:
        if x["place"]:
            pres[x["r"]][x["place"]].add(x["frm"])

    def same_place_pool(A, r, place):
        for rr, tag in ((r, "exact"), (r - 1, "minus1"), (r + 1, "plus1")):
            if place and rr in pres:
                pool = sorted(p for p in pres[rr].get(place, set()) if p != A)
                if pool:
                    return pool, tag
        return [p for p in agents if p != A], "fallback_all"

    n_init = same_orig = 0
    seenA, seenC, seenB = set(), set(), set()
    repA = repC = repB = 0
    hit_actual = hit_B = 0
    tags = Counter()
    nB_ne_A = 0

    for x in rows:
        if x["turn"] != 0 or not x["to"]:
            continue
        A, B0, r, place, tid = x["frm"], x["to"], x["r"], x["place"], x["topic"]
        n_init += 1
        dow, si = r // 12, (r % 12) // 3
        seed = f"{A}|day{dow}-{_SLOTS[si]}|{tid}|p0"
        allp = [p for p in agents if p != A]
        pA = orig_pick(seed, allp)
        pC = axis_pick(seed, allp)
        poolB, tag = same_place_pool(A, r, place)
        tags[tag] += 1
        pB = axis_pick(seed, poolB)
        nB_ne_A += (pB != pA)
        same_orig += (pA == B0)

        for tagk, pick, seen in (("A", B0, seenA), ("C", pC, seenC), ("B", pB, seenB)):
            k = tuple(sorted((A, pick)))
            hit = (k in seen)
            seen.add(k)
            if tagk == "A":
                repA += hit
            elif tagk == "C":
                repC += hit
            else:
                repB += hit
        # 同 place 命中：选中者与发起人是否同 place（用该 round 在场集合）
        present = pres[r].get(place, set()) if place else set()
        hit_actual += (B0 in present)
        hit_B += (pB in present)

    def pct(x, n):
        return round(100.0 * x / n, 2) if n else None

    out = {
        "log": a.log, "n_init": n_init,
        "self_check_orig_matches_actual_rate": pct(same_orig, n_init),
        "repeat_pair_rate_A_actual": pct(repA, n_init),
        "repeat_pair_rate_C_equalweight_all_pool": pct(repC, n_init),
        "repeat_pair_rate_B_same_place": pct(repB, n_init),
        "map_artifact_pp_C_minus_A": round(pct(repC, n_init) - pct(repA, n_init), 2),
        "mechanism_pp_B_minus_C": round(pct(repB, n_init) - pct(repC, n_init), 2),
        "same_place_hit_rate_actual": pct(hit_actual, n_init),
        "same_place_hit_rate_B": pct(hit_B, n_init),
        "change_rate_B_vs_A": pct(nB_ne_A, n_init),
        "pool_tags": dict(tags),
        "caveat": ("在场集合用'该 round 发过消息的 (agent,place)'近似，非 plan 真值；"
                   "退化到全员的比例见 pool_tags.fallback_all；仅作值不值得跑的预判，不作判定读数。"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.out_json:
        json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
