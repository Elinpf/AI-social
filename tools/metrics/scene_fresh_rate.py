#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R52 尺子：处境锚「指对率」（机制层）+ 处所-内容一致性（效果层）两臂对照（只读、零 LLM、零跑批）。

## 为什么需要它

B-8 的缺陷是**时序**问题：`ctx.scene.place` 取自本轮 perceive 阶段的快照，消息落盘的
`payload.place` 是 COMMUNICATE 阶段的实时场所；居民在本轮内搬过地方时两者不一致
（R46-A1 实测 87/191 = 45.55%，且 100% 等于同轮前一次 `PLACE_MOVE.from_place` ⇒ 锚点说的是**上一站**）。

所以本尺子**分开量两层**，不把机制与效果混成一个数：

  * **机制层 `anchor_fresh_rate`（本文件主算）**：`ctx.scene.place == payload.place` 的对话条数
    ÷ 含 `ctx.scene` 键的对话条数。分母只含带 `scene` 键的条目（无该键 ⇒ 分母 0，读数写 `null`，**不写 0**）。
  * **效果层 `consistency_rate`（照抄 C1 预登记主指标）**：直接 `import` 冻结尺子
    `tools/metrics/place_content_consistency.py` 的 `DOMAINS` / `classify` 计算，
    **不复制 second 套词表**；输出里打印同一个 `lexicon_sha256` 供两臂核对判据未漂移。

## 口径（先冻结，再读数；改这里 = 改尺子）

  * 样本 = `run.jsonl` 里 `type ∈ {MSG_PUBLIC, MSG_DM}` 的记录（与 C1 预登记卡 §3.1 一致）。
  * 机制层分母 = 其中 `payload.ctx.scene` 为 dict 的条目；分子 = `scene.place` 与 `payload.place` 相等的条目。
  * 错位归因：`anchor_eq_from_place` = 错位条目里 `scene.place == 同轮内前一次 PLACE_MOVE.from_place`
    （结构性证据：锚点 = 上一站）；`neither` = 既非 from 也非 to（**判伪反例**，>0 即推翻"移动前快照"解释）。
  * 两侧比率都给 Wilson95；两臂差异给 Fisher 精确检验双侧 p（纯标准库）。

用法:
  python3 tools/metrics/scene_fresh_rate.py --run <arm_dir>/run.jsonl [--label off] [--out-json x.json]
  python3 tools/metrics/scene_fresh_rate.py --compare-off <off>/run.jsonl --compare-on <on>/run.jsonl \
      --out-json v2/evidence/r52-scene-fresh/compare.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import place_content_consistency as PCC  # noqa: E402  （冻结尺子，只 import 不复制）

RULER_VERSION = "r52-scene-fresh-v1"
DIALOGUE_TYPES = ("MSG_PUBLIC", "MSG_DM")


def wilson95(k: int, n: int, z: float = 1.96) -> dict | None:
    if n <= 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"k": k, "n": n, "rate": round(p, 6), "lo": round(max(0.0, c - h), 6),
            "hi": round(min(1.0, c + h), 6)}


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2×2 表 [[a,b],[c,d]] 的双侧 Fisher 精确检验 p（超几何求和，纯标准库）。"""
    n = a + b + c + d
    r1, r2, c1 = a + b, c + d, a + c

    def lcomb(n_: int, k_: int) -> float:
        return math.lgamma(n_ + 1) - math.lgamma(k_ + 1) - math.lgamma(n_ - k_ + 1)

    def prob(x: int) -> float:
        return math.exp(lcomb(r1, x) + lcomb(r2, c1 - x) - lcomb(n, c1))

    lo, hi = max(0, c1 - r2), min(r1, c1)
    p_obs = prob(a)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs * (1 + 1e-9)))


def measure(path: str) -> dict:
    raw = open(path, "rb").read()
    run_sha = hashlib.sha256(raw).hexdigest()

    moves = collections.defaultdict(list)   # actor -> [(round, seq, from_place, to_place)]
    msgs = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        t = e.get("type")
        if t == "PLACE_MOVE":
            p = e.get("payload") or {}
            actor = e.get("actor") or p.get("agent_id")
            if actor:
                moves[actor].append((e.get("round"), e.get("seq"),
                                     str(p.get("from_place") or ""), str(p.get("to_place") or "")))
        elif t in DIALOGUE_TYPES:
            msgs.append(e)

    n_dialogue = len(msgs)
    n_scene = n_match = 0
    stale = []
    for e in msgs:
        p = e.get("payload") or {}
        ctx = p.get("ctx") or {}
        scene = ctx.get("scene") if isinstance(ctx.get("scene"), dict) else None
        if scene is None:
            continue
        n_scene += 1
        anchor = str(scene.get("place") or "")
        msg_place = str(p.get("place") or "")
        if anchor == msg_place:
            n_match += 1
            continue
        actor, rnd, seq = e.get("actor"), e.get("round"), e.get("seq")
        prior = [m for m in moves.get(actor, ())
                 if m[0] == rnd and m[1] is not None and seq is not None and m[1] < seq]
        last = prior[-1] if prior else None
        stale.append({
            "seq": seq, "actor": actor, "msg_place": msg_place, "anchor": anchor,
            "move": ("%s→%s" % (last[2], last[3])) if last else "NO_MOVE_THIS_ROUND",
            "eq_from": bool(last) and anchor == last[2],
        })

    n_stale = len(stale)
    eq_from = sum(1 for r in stale if r["eq_from"])
    neither = sum(1 for r in stale if not r["eq_from"])

    # 效果层（照抄 C1 预登记口径）
    n_judged = n_agree = n_no_cue = n_missing = 0
    for e in msgs:
        p = e.get("payload") or {}
        place = (p.get("place") or "").strip()
        body = (p.get("body") or "").strip()
        if not place or not body:
            n_missing += 1
            continue
        doms, _cues = PCC.classify(body)
        if not doms:
            n_no_cue += 1
            continue
        n_judged += 1
        if any(place in PCC.DOMAINS[d]["places"] for d in doms):
            n_agree += 1

    return {
        "ruler_version": RULER_VERSION,
        "lexicon_sha256": PCC.LEXICON_DIGEST,
        "run_sha256": run_sha,
        "n_dialogue": n_dialogue,
        "scene_key": n_scene,
        "anchor_fresh": wilson95(n_match, n_scene),
        "anchor_stale": n_stale,
        "anchor_eq_from_place": eq_from,
        "anchor_neither_from_nor_to": neither,
        "missing_place_or_body": n_missing,
        "no_cue": n_no_cue,
        "no_cue_share": round(n_no_cue / n_dialogue, 6) if n_dialogue else None,
        "judged": n_judged,
        "agree": n_agree,
        "consistency": wilson95(n_agree, n_judged),
    }


def _delta(a: dict | None, b: dict | None) -> float | None:
    if not a or not b or a["rate"] is None or b["rate"] is None:
        return None
    return round((b["rate"] - a["rate"]) * 100, 2)


def compare(off_path: str, on_path: str) -> dict:
    off, on = measure(off_path), measure(on_path)
    out = {"off": off, "on": on, "verdict": {}}

    # 机制层：锚点指对率（Fisher，分子/分母 = 含 scene 键的对话）
    am, bm = off["anchor_fresh"], on["anchor_fresh"]
    mech = {"rate_off": None, "rate_on": None, "delta_pp": None, "fisher_p": None}
    if am and bm:
        mech["rate_off"] = am["rate"]
        mech["rate_on"] = bm["rate"]
        mech["delta_pp"] = _delta(am, bm)
        mech["fisher_p"] = round(fisher_exact_two_sided(am["k"], am["n"] - am["k"],
                                                        bm["k"], bm["n"] - bm["k"]), 6)
    out["mechanism"] = mech

    # 效果层：处所-内容一致性（C1 预登记主指标）
    ac, bc = off["consistency"], on["consistency"]
    eff = {"rate_off": None, "rate_on": None, "delta_pp": None, "fisher_p": None}
    if ac and bc:
        eff["rate_off"] = ac["rate"]
        eff["rate_on"] = bc["rate"]
        eff["delta_pp"] = _delta(ac, bc)
        eff["fisher_p"] = round(fisher_exact_two_sided(ac["k"], ac["n"] - ac["k"],
                                                       bc["k"], bc["n"] - bc["k"]), 6)
    out["effect"] = eff

    # 与预登记阈值机械比对（阈值逐字抄自 reports/R52-prereg-scene-fresh-20261102.md §4）
    M1_DELTA_MIN_PP = 15.0     # 效果层：ON − OFF ≥ +15.0pp
    M1_RATE_MIN = 0.55         # 效果层：ON 绝对下限
    MECH_MIN_RATE = 0.95       # 机制层：ON 锚点指对率 ≥ 95%
    N_FLOOR = 68               # 每臂可判定分母下限（<68 ⇒ probe=true，只报条数）
    NO_CUE_SHIFT_MAX = 0.10    # 两臂 no_cue 占比差 ≥10pp ⇒ 效果层降级「不可判（子集构成漂移）」

    probe = (off["judged"] < N_FLOOR) or (on["judged"] < N_FLOOR)
    no_cue_shift = None
    if off["no_cue_share"] is not None and on["no_cue_share"] is not None:
        no_cue_shift = round(abs(off["no_cue_share"] - on["no_cue_share"]), 6)

    verdict: dict = {"probe": probe, "no_cue_shift": no_cue_shift,
                     "thresholds": {"M1_delta_min_pp": M1_DELTA_MIN_PP,
                                    "M1_rate_min": M1_RATE_MIN,
                                    "mech_min_rate": MECH_MIN_RATE,
                                    "n_floor": N_FLOOR,
                                    "no_cue_shift_max": NO_CUE_SHIFT_MAX}}
    verdict["M1_mechanism"] = ("pass" if (mech["rate_on"] is not None
                                         and mech["rate_on"] >= MECH_MIN_RATE) else
                               ("fail" if mech["rate_on"] is not None else "na"))
    if eff["delta_pp"] is None or eff["rate_on"] is None:
        verdict["E1_effect"] = "na"
    elif no_cue_shift is not None and no_cue_shift >= NO_CUE_SHIFT_MAX:
        verdict["E1_effect"] = "undecidable_no_cue_drift"
    elif probe:
        verdict["E1_effect"] = "probe_only"
    elif eff["delta_pp"] >= M1_DELTA_MIN_PP and eff["rate_on"] >= M1_RATE_MIN:
        verdict["E1_effect"] = "achieved"
    else:
        verdict["E1_effect"] = "not_achieved"
    out["verdict"] = verdict
    return out


def _render(label: str, m: dict) -> None:
    af, cs = m["anchor_fresh"], m["consistency"]
    print("[%s] dialogue=%d scene_key=%d anchor_match=%s/%s fresh_rate=%s stale=%d "
          "(eq_from=%d neither=%d) | judged=%d agree=%s rate=%s"
          % (label, m["n_dialogue"], m["scene_key"],
             (af or {}).get("k", 0), (af or {}).get("n", 0),
             ("%.4f" % af["rate"]) if af else "NA", m["anchor_stale"],
             m["anchor_eq_from_place"], m["anchor_neither_from_nor_to"],
             m["judged"], (cs or {}).get("k", 0), ("%.4f" % cs["rate"]) if cs else "NA"))


def main() -> int:
    ap = argparse.ArgumentParser(description="R52 处境锚指对率 + C1 一致性 两臂对照（只读、零 LLM）")
    ap.add_argument("--run", default=None)
    ap.add_argument("--label", default="arm")
    ap.add_argument("--compare-off", default=None)
    ap.add_argument("--compare-on", default=None)
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()

    if a.run:
        m = measure(a.run)
        m["label"] = a.label
        _render(a.label, m)
        payload = m
    elif a.compare_off and a.compare_on:
        payload = compare(a.compare_off, a.compare_on)
        _render("off", payload["off"])
        _render("on", payload["on"])
        print("mechanism: " + json.dumps(payload["mechanism"], ensure_ascii=False, sort_keys=True))
        print("effect:    " + json.dumps(payload["effect"], ensure_ascii=False, sort_keys=True))
        print("verdict:   " + json.dumps(payload["verdict"], ensure_ascii=False, sort_keys=True))
    else:
        print("usage: --run <run.jsonl> | --compare-off <off.jsonl> --compare-on <on.jsonl>",
              file=sys.stderr)
        return 2

    if a.out_json:
        Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2,
                                               sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
