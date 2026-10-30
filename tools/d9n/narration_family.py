#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""D9m 测量仪器：旁白片段「归族」+ 六条判据读数（B 口径判定，A 口径诊断）。

口径**唯一真源**是 `tools/d9n/narration_family_lexicon.json`（exp-designer 冻结，
sha256 记录在 GOLDEN.md）。本文件不硬编码任何词表内容、不硬编码阈值：词表顺序、
`V_judge`/`objs_judge`、两条守卫门限全部从 lexicon 读入并在启动时做结构校验。
**改尺子只能改 lexicon 并重冻结，不得在本文件里裁量。**

规则（lexicon `assignment_rules` R1–R8）：
  R1 一个片段（成对括号内文本 inner）恰好归一族；禁一片多计。
  R2 动词：按 `V_judge`（先 8 闭表、后 13 旋转动词）顺序取首个命中 → v；全不命中 ⇒ unassigned。
  R3 附属：先按 `parts_6` 顺序取首个命中 → p；否则按 `objs_13` 顺序取首个 → o；皆无 ⇒ null。
  R4 族名 `v|p` / `v|o` / `v|null`。
  R5 部位优先于器物。
  R6 不做同义归并。
  R7 介词（把/往）不作动词。
  R8 只去首尾括号，不做其它文本归一。

判据（主件 §4）：
  (a) max_exact_dup ≤ 2                                    辅助
  (b1) 族总量≥3 的族：share ≤ 60% 且 该(角色,族) count ≤ 2   辅助（本轮降级）
  (b2′) 所有族：total ≤ 3 且 n_ge2 ≤ 1                      主判
  (c-1) density = blocks_total / msgs_total ≥ 1.0           主判（仅密度分量）
  (c-2) 咬合率 —— 无实现 ⇒ 恒为「不可判」，本工具不给读数
  (d) max_v ≤ 5 且 unassigned_verb_rate 达守卫              主判
  (e) max_k ≤ 2                                            辅助
守卫：coverage = assigned / blocks_total ≥ lexicon.guards.coverage_guard.threshold_abs；
      unassigned_verb_rate = 1 − coverage ≤ lexicon.guards.unassigned_rate_guard.threshold_abs。

用法：
    python3 tools/d9n/narration_family.py --log <run.jsonl> \
        [--lexicon tools/d9n/narration_family_lexicon.json] \
        [--out <d9m_judgement.json>] [--arm ON|OFF]

只读 run.jsonl；只写 --out 指定路径（默认只打印）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools" / "d5"))

from dialogue_metrics import PAREN_ANY_RE, extract_messages  # noqa: E402

DEFAULT_LEXICON = HERE / "narration_family_lexicon.json"

#: 与 tools/d9i/narration_stats.py 完全一致的成对括号口径（片段级交叉校验必须与它同一正则）
PAIRED_RE = re.compile(r"（[^（）]{1,120}）|\([^()]{1,120}\)")

REQUIRED_KEYS = (
    "schema", "verbs_closed_8", "verbs_rotation_13", "parts_6", "objs_13",
    "assignment_rules", "baseline_reference", "guards",
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_lexicon(path: Path) -> dict:
    lex = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_KEYS if k not in lex]
    if missing:
        raise SystemExit(f"[d9n] lexicon 缺键: {missing}")
    for k, n in (("verbs_closed_8", 8), ("verbs_rotation_13", 13),
                 ("parts_6", 6), ("objs_13", 13)):
        if len(lex[k]) != n:
            raise SystemExit(f"[d9n] lexicon {k} 长度应为 {n}，实际 {len(lex[k])}")
    # D9u 追加项：可缺省（v1.x 词表无此键 ⇒ 行为不变）
    #   v2.0 = verbs_expansion_22（22 个）；v2.1 = verbs_expansion_25（25 个，D9u.1 勘误补 刨/锉/掰）
    for key, n in (("verbs_expansion_22", 22), ("verbs_expansion_25", 25)):
        if key in lex:
            exp = lex[key]
            if len(exp) != n:
                raise SystemExit(f"[d9n] lexicon {key} 长度应为 {n}")
            if len(set(exp)) != len(exp):
                raise SystemExit(f"[d9n] lexicon {key} 有重复项")
    expv = lex.get("verbs_expansion_25", lex.get("verbs_expansion_22", []))
    if expv:
        allv = list(lex["verbs_closed_8"]) + list(lex["verbs_rotation_13"]) + list(expv)
        if len(set(allv)) != len(allv):
            raise SystemExit("[d9n] lexicon 扩展后动词总表有重复项")
    return lex


def v_judge(lex: dict) -> list:
    """V_judge 顺序：closed_8 → rotation_13 → expansion_22（D9u 追加项恒在末尾）。"""
    expansion = lex.get("verbs_expansion_25", lex.get("verbs_expansion_22", []))
    return list(lex["verbs_closed_8"]) + list(lex["verbs_rotation_13"]) + list(expansion)


def read_log(path: Path) -> list:
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
    return recs


def first_hit(inner: str, table) -> str | None:
    for w in table:
        if w in inner:
            return w
    return None


def assign_family(inner: str, V, PARTS, OBJS) -> dict:
    v = first_hit(inner, V)
    p = first_hit(inner, PARTS)
    o = None if p else first_hit(inner, OBJS)
    return {
        "verb": v,
        "part": p,
        "obj": o,
        "family": (None if v is None else f"{v}|{p or o or 'null'}"),
        "assigned": v is not None,
    }


def ratio(n, d):
    return (round(n / d, 6) if d else None)


def analyse(log_path: Path, lex: dict) -> dict:
    V = v_judge(lex)
    PARTS = list(lex["parts_6"])
    OBJS = list(lex["objs_13"])
    th = lex["guards"]["coverage_guard"]
    th_u = lex["guards"]["unassigned_rate_guard"]

    msgs = extract_messages(read_log(log_path))
    msgs_total = len(msgs)

    blocks_total = 0
    assigned = 0
    verb_counts = Counter()
    fam = defaultdict(lambda: {"total": 0, "by_agent": Counter()})
    exact = Counter()
    dist = Counter()          # 单条 MSG 的片段数 k
    a_caliber = Counter()     # A 口径（字面包含，可多计，仅诊断）
    samples_unassigned = []

    for m in msgs:
        body = m.get("body") or ""
        agent = m.get("from") or m.get("actor") or "?"
        blocks = PAIRED_RE.findall(body)
        dist[len(blocks)] += 1
        for b in blocks:
            inner = b[1:-1]
            blocks_total += 1
            exact[inner] += 1
            hits = [v for v in V if v in inner]
            for v in hits:
                verb_counts[v] += 1
            # A 口径：每个命中动词 × 每个命中附属各计一次
            for v in hits:
                for w in PARTS + OBJS:
                    if w in inner:
                        a_caliber[f"{v}|{w}"] += 1
            asg = assign_family(inner, V, PARTS, OBJS)
            if asg["assigned"]:
                assigned += 1
                fam[asg["family"]]["total"] += 1
                fam[asg["family"]]["by_agent"][agent] += 1
            elif len(samples_unassigned) < 8:
                samples_unassigned.append(inner[:60])

    coverage = ratio(assigned, blocks_total)
    unassigned_rate = ratio(blocks_total - assigned, blocks_total)

    # (a)
    max_exact_dup = max(exact.values()) if exact else 0

    # (b1) 族总量≥3
    b1_offenders = []
    b1_max = None
    for f, d in fam.items():
        if d["total"] < 3:
            continue
        for p, c in d["by_agent"].items():
            share = c / d["total"]
            if b1_max is None or share > b1_max["share"]:
                b1_max = {"family": f, "agent": p, "count": c,
                          "total": d["total"], "share": round(share, 6)}
            if share > lex_share_max(lex) or c > lex_count_max(lex):
                b1_offenders.append({"family": f, "agent": p, "count": c,
                                     "total": d["total"], "share": round(share, 6)})

    # (b2′)
    b2p_offenders = []
    for f, d in sorted(fam.items()):
        n_ge2 = sum(1 for c in d["by_agent"].values() if c >= 2)
        if d["total"] > lex_total_max(lex) or n_ge2 > lex_nge2_max(lex):
            b2p_offenders.append({"family": f, "total": d["total"], "n_ge2": n_ge2,
                                  "by_agent": dict(d["by_agent"])})

    # (d) max_v（平手按 V_judge 顺序取先出现者）
    max_v, max_v_verb = 0, None
    for v in V:
        c = verb_counts.get(v, 0)
        if c > max_v:
            max_v, max_v_verb = c, v

    # (e)
    max_k = max(dist) if dist else 0

    density = ratio(blocks_total, msgs_total)
    sample_ok = blocks_total >= 50 and msgs_total >= 50
    cov_ok = coverage is not None and coverage >= th["threshold_abs"]
    una_ok = unassigned_rate is not None and unassigned_rate <= th_u["threshold_abs"]

    def tri(ok_state, bad_state):
        return ok_state if ok_state else bad_state

    verdicts = {
        "a_exact_dup": "不可判" if not sample_ok else tri(max_exact_dup <= 2, False),
        "b1_share": "不可判" if (not sample_ok or not cov_ok or b1_max is None)
                    else tri(not b1_offenders, False),
        "b2p": "不可判" if (not sample_ok or not cov_ok) else tri(not b2p_offenders, False),
        "c1_density": "不可判" if not sample_ok else tri((density or 0) >= 1.0, False),
        "c2_bite": "不可判",
        "d_max_v": "不可判" if not una_ok else tri(max_v <= 5, False),
        "e_max_k": "不可判" if not sample_ok else tri(max_k <= 2, False),
    }
    for k, v in list(verdicts.items()):
        verdicts[k] = "成立" if v is True else ("失败" if v is False else "不可判")

    return {
        "schema": "d9m.judgement/1",
        "lexicon": {"path": str(lex_path_of(lex)), "sha256": lex.get("_sha256"),
                    "lexicon_schema": lex["schema"]},
        "log": {"path": str(log_path), "sha256": sha256_file(log_path)},
        "blocks_total": blocks_total,
        "msgs_total": msgs_total,
        "density": density,
        "coverage": {"assigned": assigned, "blocks_total": blocks_total, "rate": coverage},
        "unassigned_verb_rate": unassigned_rate,
        "verb_counts": {v: verb_counts.get(v, 0) for v in V},
        "max_v": {"value": max_v, "verb": max_v_verb},
        "max_exact_dup": max_exact_dup,
        "exact_dup_top": [{"inner": k, "count": v} for k, v in exact.most_common(10)],
        "families_b": [{"family": f, "total": fam[f]["total"],
                        "by_agent": dict(fam[f]["by_agent"]),
                        "n_ge2": sum(1 for c in fam[f]["by_agent"].values() if c >= 2)}
                       for f in sorted(fam, key=lambda x: (-fam[x]["total"], x))],
        "b1": {"max": b1_max, "offenders": b1_offenders},
        "b2p": {"offenders": b2p_offenders},
        "e_dist": {str(k): v for k, v in sorted(dist.items())},
        "max_k": max_k,
        "a_caliber_diagnostic_top": [{"family_literal": k, "count": v}
                                     for k, v in a_caliber.most_common(10)],
        "guards": {
            "sample_ok": sample_ok,
            "coverage_ok": cov_ok,
            "coverage_threshold_abs": th["threshold_abs"],
            "unassigned_ok": una_ok,
            "unassigned_threshold_abs": th_u["threshold_abs"],
        },
        "verdicts": verdicts,
        "verdict_basis": {
            "c2_bite": "咬合率无文字化判据 + 无冻结实现 ⇒ 本轮恒为不可判（主件 §4.4）",
            "b1_share": "本轮降级为辅助读数：n 小、口径敏感（主件 §4.3）",
        },
        "samples_unassigned": samples_unassigned,
    }


def lex_share_max(lex):
    return float(lex.get("thresholds", {}).get("b1_share_max", 0.6))


def lex_count_max(lex):
    return int(lex.get("thresholds", {}).get("b1_count_max", 2))


def lex_total_max(lex):
    return int(lex.get("thresholds", {}).get("b2p_family_total_max", 3))


def lex_nge2_max(lex):
    return int(lex.get("thresholds", {}).get("b2p_n_ge2_max", 1))


def lex_path_of(lex):
    return Path(lex.get("_path", DEFAULT_LEXICON))


def main(argv=None) -> int:
    global lex_path_of
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    ap.add_argument("--out", default=None)
    ap.add_argument("--arm", default=None)
    args = ap.parse_args(argv)

    lpath = Path(args.lexicon)
    lex = load_lexicon(lpath)
    lex["_sha256"] = sha256_file(lpath)
    lex["_path"] = str(lpath)
    lex_path_of = lambda _l: lpath  # noqa: E731

    out = analyse(Path(args.log), lex)
    out["arm"] = args.arm
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(txt + "\n", encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
