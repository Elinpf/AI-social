#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.3 「池口径」证据 → **生产函数**的功能等价复算（纯离线、不调模型）。

卡点：`v2/evidence/d23_place_offline_verdict.md` 的 B 臂（`repeat_pair_rate 50.88%`、
`same_place_hit_rate 90.35%`）是 `tools/d21/d22_place_feasibility.py` 自己实现的口径，
**不是** `code/life/` 里的任何函数。⇒ 即便将来接线，也可能"接的不是那个东西"。

本工具用**生产侧函数** `life.place_pool.pick_same_place_first()`（同地点优先 + 累积等权轴）
在同一条真日志上重算同样两个量，要求与离线工具**逐项相同**（容差 0pp；不等即报 MISMATCH）。

在场集合口径沿用离线工具（该 round 发过消息的 `(agent, place)`，
回退 `r-1 → r+1 → 全员`），并**照抄**它的近似声明：这是**近似**，不是 plan 真值。

用法：
    python3 tools/d23/pool_arm_repro.py --log <run.jsonl> [--out-json x.json]
退出码：0 = 与离线工具一致 / 1 = 不一致
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
_SLOTS = ["morning", "afternoon", "evening", "night"]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "code"))
from life.place_pool import pick_same_place_first  # noqa: E402


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

    pres = defaultdict(lambda: defaultdict(set))
    for x in rows:
        if x["place"]:
            pres[x["r"]][x["place"]].add(x["frm"])

    def peer_place_map(r, place, me):
        """`{peer: place}`——**严格照抄**离线工具的回退顺序（r → r-1 → r+1），
        且只在**第一个"除发起人外还有人"的那一轮**取快照（不做跨轮合并，否则会凭空多出同地点候选 ⇒ 口径漂移）。
        全都没有 ⇒ 返回 `{}`（⇒ 生产函数退化为原池 = 离线工具的 `fallback_all`）。
        ⚠ 必须排除发起人自己：离线工具判的是 `pres[rr][place] - {A}` 非空，否则回退轮次就会错位。"""
        if not place:
            return {}
        for rr in (r, r - 1, r + 1):
            if rr in pres:
                who = {p for p in pres[rr].get(place, set()) if p != me}
                if who:
                    return {p: place for p in who}
        return {}

    seen = set()
    rep = hit = n_init = 0
    for x in rows:
        if x["turn"] != 0 or not x["to"]:
            continue
        A, r, place, tid = x["frm"], x["r"], x["place"], x["topic"]
        n_init += 1
        dow, si = r // 12, (r % 12) // 3
        seed = f"{A}|day{dow}-{_SLOTS[si]}|{tid}|p0"
        pool = [p for p in agents if p != A]
        pm = peer_place_map(r, place, A)
        pick = pick_same_place_first(seed, pool, place, pm)   # ← 生产侧函数
        k = tuple(sorted((A, pick)))
        rep += (k in seen)
        seen.add(k)
        # 命中口径与离线工具逐字相同：只看**该 round**的在场集合（不走回退）
        present = pres[r].get(place, set()) if place else set()
        hit += (pick in present)

    def pct(v, n):
        return round(100.0 * v / n, 2) if n else None

    out = {
        "log": a.log, "n_init": n_init,
        "pool_arm_repeat_pair_rate_pct": pct(rep, n_init),
        "pool_arm_same_place_hit_rate_pct": pct(hit, n_init),
        "evidence_reference": {"repeat_pair_rate_B_same_place": 50.88,
                               "same_place_hit_rate_B": 90.35,
                               "source": "v2/evidence/d23_place_offline_verdict.md"},
        "caveat": "在场集合用'该 round 发过消息的 (agent,place)'近似（沿离线工具回退 r→r-1→r+1），非 plan 真值。",
    }
    ref = out["evidence_reference"]
    same = (out["pool_arm_repeat_pair_rate_pct"] == ref["repeat_pair_rate_B_same_place"]
            and out["pool_arm_same_place_hit_rate_pct"] == ref["same_place_hit_rate_B"])
    out["match_offline_tool"] = same
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.out_json:
        json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
