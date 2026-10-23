#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.2 预登记前的**离线可行性**：近因加权抽会把多少人换掉？换掉后 repeat_pair_rate 会变成多少？

⚠ 这是**离线代理**，不是真跑。两点近似必须写在结论里：
  1. 真实计划发生在**周初**（`_weekly_slots`），本工具按**发起时刻**取最近互动轮 ⇒ Δround 偏小、权重偏尖；
  2. 真实 `seed` 含 `slot_id`（day{dow}-{slot}），本工具用 `agent|round|tid|p0` 作代理种子。

仍足以回答一件事：**这个机制值不值得花一次 50 分钟跑批**（若 change_rate 极低或 repeat 几乎不动 ⇒ 不值得）。

权重（预登记里将写死同一式）：
    w(peer) = 1 + 2 * exp(-Δ/20)        Δ = 当前轮 − 与该 peer 最近一次互动轮（无记录 ⇒ w=1）
    确定性加权抽：u = sha256(seed)[:8]/2^64；落点 = u * Σw，按 peers 排序累积取首个跨越者

用法：python3 tools/d21/d22_recency_feasibility.py --log path [--tau 20] [--alpha 2]
"""
import argparse, hashlib, json, math
from collections import defaultdict, Counter

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
# code/config/default.json: ROUNDS_PER_SLOT=3, SLOTS_PER_DAY 4 项
_SLOTS = ["morning", "afternoon", "evening", "night"]


def h01(s):
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:8], 16) / float(1 << 32)


def orig_pick(seed, options):
    """与 master `planner._pick` 逐字节同式。"""
    return options[int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % len(options)]


def weighted_pick(seed, peers, w):
    """确定性加权抽：u 取自同一 sha256 前 8 hex，映射到累积权重轴。"""
    tot = sum(w[p] for p in peers)
    u = h01(seed) * tot
    acc = 0.0
    for p in peers:
        acc += w[p]
        if u < acc:
            return p
    return peers[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--tau", type=float, default=20.0)
    ap.add_argument("--alpha", type=float, default=2.0)
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()

    events = []
    for line in open(a.log, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG_TYPES:
            continue
        pl = e.get("payload") or {}
        if pl.get("from") is None:
            continue
        events.append({"ts": e.get("round"), "frm": pl["from"], "to": pl.get("to"),
                       "turn": pl.get("turn_index"), "topic": pl.get("topic"),
                       "slot": pl.get("slot"), "uid": pl.get("msg_uid")})
    events = [x for x in events if isinstance(x["ts"], int)]
    events.sort(key=lambda r: (r["ts"], str(r["uid"])))
    agents = sorted({r["frm"] for r in events} | {r["to"] for r in events if r["to"]})

    last = {}                                   # (a,b) -> round
    n_init = 0
    same_as_actual_orig = 0                     # A 与原实际一致（自检：应 100%）
    n_total_change = 0                          # B != A（总换人，去重后，≤100%）
    n_map_only = 0                              # C != A（纯映射差异）
    n_weight_only = 0                           # B != C（纯权重差异）
    seen_actual, seen_c, seen_b = set(), set(), set()
    rep_actual = rep_c = rep_b = 0
    deltas = []

    for r in events:
        A, B, t = r["frm"], r["to"], r["ts"]
        if r["turn"] == 0 and B:
            n_init += 1
            peers = [p for p in agents if p != A]
            w = {}
            for p in peers:
                lr = last.get((A, p))
                if lr is None:
                    w[p] = 1.0
                else:
                    d = max(0, t - lr)
                    deltas.append(d)
                    w[p] = 1.0 + a.alpha * math.exp(-d / a.tau)
            # 精确复现：slot_id = day{dow}-{slot}，dow = round//12，slot = SLOTS[(round%12)//3]
            dow, si = t // 12, (t % 12) // 3
            seed = f"{A}|day{dow}-{_SLOTS[si]}|{r['topic']}|p0"
            pA = orig_pick(seed, peers)
            w_eq = {x: 1.0 for x in peers}
            pC = weighted_pick(seed, peers, w_eq)      # 等权：只反映映射差异
            pB = weighted_pick(seed, peers, w)         # 权重：映射 + 权重
            same_as_actual_orig += (pA == B)
            n_total_change += (pB != pA)
            n_map_only += (pC != pA)
            n_weight_only += (pB != pC)
            for tag, pick, seen, cnt in (("a", B, seen_actual, "a"), ("c", pC, seen_c, "c"), ("b", pB, seen_b, "b")):
                k = tuple(sorted((A, pick)))
                if k in seen:
                    if tag == "a": rep_actual += 1
                    elif tag == "c": rep_c += 1
                    else: rep_b += 1
                seen.add(k)
        # 更新双向最近互动
        if B:
            last[(A, B)] = t
            last[(B, A)] = t

    deltas.sort()

    def pct(x, n):
        return round(100.0 * x / n, 2) if n else None

    out = {
        "log": a.log, "tau": a.tau, "alpha": a.alpha,
        "round_scale": "e.get('round')  (0..59)",
        "n_init": n_init,
        "self_check_orig_matches_actual_rate": pct(same_as_actual_orig, n_init),
        "map_only_change_rate_C_vs_A": pct(n_map_only, n_init),
        "weight_only_change_rate_B_vs_C": pct(n_weight_only, n_init),
        "total_change_rate_B_vs_A": pct(n_total_change, n_init),
        "repeat_pair_rate_actual": pct(rep_actual, n_init),
        "repeat_pair_rate_equalweight_C": pct(rep_c, n_init),
        "repeat_pair_rate_weighted_B": pct(rep_b, n_init),
        "delta_pp_weight_effect_B_minus_C": round(pct(rep_b, n_init) - pct(rep_c, n_init), 2),
        "delta_pp_total_B_minus_actual": round(pct(rep_b, n_init) - pct(rep_actual, n_init), 2),
        "delta_round_p50": deltas[len(deltas) // 2] if deltas else None,
        "delta_round_p10_p90": [deltas[int(0.1 * len(deltas))], deltas[int(0.9 * len(deltas)) - 1]] if deltas else None,
        "caveat": ("seed 已精确复现（`agent|day{dow}-{slot}|{tid}|p0`，自检须 100%）；"
                   "Δ 取自**发起时刻**而非周初计划时刻（真实 Δ 偏大 ⇒ 权重更平 ⇒ 本表偏保守地高估权重效应）；"
                   "**仅用于'值不值得跑'的预判，不作判定读数**。"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.out_json:
        json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
