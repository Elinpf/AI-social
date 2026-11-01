#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R50 标定读数器：在 R49 两个**已冻结** `run.jsonl` 上跑 `r50_detail_position.py` 的四档位置口径，
输出对照 JSON（只读、零 LLM、零跑批、纯标准库）。

## 这份读数的性质（先写在最前面，防止被误用）

* **post-hoc 开发集标定**：数据（R49 OFF/ON 两臂）在尺子 v2 设计**之前**就已存在于盘上，
  新窗口是在看过这批数据之后才定的 ⇒ 本轮所有差异数字**不是效果判决**，
  **不得**据此写「有效 / 无效 / 显著改善 / 生活气息提升」中的任何一条。
* 唯一用途：
  1. **选点消歧**——看清 R49 的 `opener6` 到底漏判了什么；
  2. **下一轮功效估算**——用 OFF 臂 `p1` 复算 MDE，填进 R50 预登记卡 §MDE。

判据口径见 `tools/metrics/r50_detail_position.py` 模块 docstring（已冻结）。

用法:
  python3 tools/metrics/r50_calib.py \
      --off v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl \
      --on  v2/evidence/r49-diversity-on-20261101_n16r24_s42/run.jsonl \
      --out-json v2/evidence/r50-calib-20261101.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r50_detail_position as R  # noqa: E402

STRATA = ("opener6", "first_clause", "first_clause_skip", "anywhere")

#: R49 报告 §3 已公布的读数（对账基准，硬编码以免"记得的数"漂移）
R49_PUBLISHED = {
    "off": {"n_msgs": 191, "opener6": 42, "anywhere": 187, "paren_lead": 172},
    "on": {"n_msgs": 191, "opener6": 57, "anywhere": 191, "paren_lead": 180},
}


def mde_pp(p1: float, n1: int, n2: int, z_a: float = 1.96, z_b: float = 0.8416) -> float | None:
    """与 R49 预登记卡 §5 **同一算法**：两独立比例、双侧 α=0.05、power=0.80，反解最小可检效应。"""
    for i in range(1, 900):
        p2 = p1 - i * 0.001
        if p2 <= 0.0005:
            break
        pbar = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = math.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n2))
        if se and abs(p1 - p2) / se - z_b >= z_a:
            return round((p1 - p2) * 100, 2)
    return None


def n_required(p1: float, delta_pp: float, z_a: float = 1.96, z_b: float = 0.8416) -> int | None:
    """给定 p1 与目标效应，反解每臂所需样本量（正态近似，纯标准库）。"""
    p2 = p1 - delta_pp / 100.0
    if p2 <= 0 or p2 >= 1:
        return None
    pbar = (p1 + p2) / 2
    num = (z_a * math.sqrt(2 * pbar * (1 - pbar)) + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    den = (p1 - p2) ** 2
    return int(math.ceil(num / den))


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2 精确检验（双侧，取 P ≤ P(obs) 的超几何概率之和）。纯标准库。"""
    n1, n2 = a + b, c + d
    m = a + c
    total = math.comb(n1 + n2, m)

    def prob(x: int) -> float:
        if x < 0 or x > min(n1, m) or (m - x) > n2:
            return 0.0
        return math.comb(n1, x) * math.comb(n2, m - x) / total

    p_obs = prob(a)
    p = sum(prob(x) for x in range(0, min(n1, m) + 1) if prob(x) <= p_obs + 1e-12)
    return round(min(1.0, p), 6)


def arm_block(path: str) -> dict:
    bodies = R.collect_bodies(path)
    res = R.measure(bodies)
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    #: 旧口径漏判/新口径丢判的逐条集合差（说明"选点"到底差在哪）
    o6 = [bool(R._DETAIL_RE.search(R.strip_lead_paren(b)[: R.OPENER_CHARS])) for b in bodies]
    fcs = [bool(R._DETAIL_RE.search(R.first_clause_skip(b))) for b in bodies]
    fc = [bool(R._DETAIL_RE.search(R.first_clause(R.strip_lead_paren(b)))) for b in bodies]
    gap = {
        "opener6_hit": sum(o6),
        "skip_hit": sum(fcs),
        "opener6_missed_but_skip_hit": sum(1 for a, b2 in zip(o6, fcs) if not a and b2),
        "opener6_hit_but_skip_miss": sum(1 for a, b2 in zip(o6, fcs) if a and not b2),
        "first_clause_hit": sum(fc),
        "skip_only": sum(1 for a, b2 in zip(fc, fcs) if not a and b2),
    }
    return {"log": {"path": path, "sha256": sha}, **res, "opener6_gap": gap}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R50 标定读数（post-hoc，只读）")
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args(argv)

    off = arm_block(args.off)
    on = arm_block(args.on)
    n_off, n_on = off["n_msgs"], on["n_msgs"]

    contrast = {}
    for k in STRATA:
        o, v = off["strata"][k], on["strata"][k]
        a, b = v["num"], v["den"] - v["num"]
        c, d = o["num"], o["den"] - o["num"]
        p1 = c / n_off if n_off else None
        contrast[k] = {
            "off": {"num": o["num"], "den": o["den"], "rate_pct": o["rate_pct"], "wilson95": o["wilson95"]},
            "on": {"num": v["num"], "den": v["den"], "rate_pct": v["rate_pct"], "wilson95": v["wilson95"]},
            "delta_pp": round(v["rate_pct"] - o["rate_pct"], 4),
            "fisher_two_sided_p": fisher_two_sided(a, b, c, d),
            "wilson95_disjoint": bool(o["wilson95"] and v["wilson95"]
                                      and (v["wilson95"]["lo"] > o["wilson95"]["hi"]
                                           or o["wilson95"]["lo"] > v["wilson95"]["hi"])),
            "mde_pp_from_off_p1": mde_pp(p1, n_off, n_on) if p1 else None,
            "n_per_arm_for_10pp": n_required(p1, 10.0) if p1 else None,
            "preregistered": False,
            "note": "post-hoc 开发集标定读数，不是效果判决",
        }

    reconcile = {}
    for arm, blk in (("off", off), ("on", on)):
        pub = R49_PUBLISHED[arm]
        reconcile[arm] = {
            "n_msgs": {"computed": blk["n_msgs"], "r49_published": pub["n_msgs"],
                       "match": blk["n_msgs"] == pub["n_msgs"]},
            "opener6": {"computed": blk["strata"]["opener6"]["num"], "r49_published": pub["opener6"],
                        "match": blk["strata"]["opener6"]["num"] == pub["opener6"]},
            "anywhere(=r49 detail_body)": {
                "computed": blk["strata"]["anywhere"]["num"], "r49_published": pub["anywhere"],
                "match": blk["strata"]["anywhere"]["num"] == pub["anywhere"]},
            "paren_lead": {"computed": blk["paren_lead"]["num"], "r49_published": pub["paren_lead"],
                           "match": blk["paren_lead"]["num"] == pub["paren_lead"]},
        }
    all_match = all(
        v2["match"] for a in reconcile.values() for v2 in a.values()
    )

    #: 预登记卡要用的 MDE / 样本量反解表（全部由脚本产出，正文不手写数字）
    mde_table = {}
    for k in STRATA:
        p1 = off["strata"][k]["num"] / n_off if n_off else None
        if not p1:
            continue
        mde_table[k] = {
            "p1_off": round(p1, 6),
            "mde_pp_at_n191": mde_pp(p1, n_off, n_on),
            "n_per_arm_for_10pp": n_required(p1, 10.0),
            "n_per_arm_for_12pp": n_required(p1, 12.0),
            "n_per_arm_for_15pp": n_required(p1, 15.0),
        }

    no_cue_off_pp = off["no_cue"]["rate_pct"]
    no_cue_on_pp = on["no_cue"]["rate_pct"]

    #: 「旧尺子到底怎么错的」——压缩效应量化（防止把它写成"只低估某一臂"）
    compression = {"per_arm": {}}
    for arm, blk in (("off", off), ("on", on)):
        g = blk["opener6_gap"]
        old_pp = blk["strata"]["opener6"]["rate_pct"]
        new_pp = blk["strata"]["first_clause_skip"]["rate_pct"]
        compression["per_arm"][arm] = {
            "missed_by_opener6": g["opener6_missed_but_skip_hit"],
            "skip_hit": g["skip_hit"],
            "relative_miss_rate_pct": round(100.0 * g["opener6_missed_but_skip_hit"] / g["skip_hit"], 4),
            "compression_factor_old_over_new": round(old_pp / new_pp, 4),
        }
    d_old = contrast["opener6"]["delta_pp"]
    d_new = contrast["first_clause_skip"]["delta_pp"]
    compression["delta"] = {
        "delta_pp_opener6": d_old,
        "delta_pp_first_clause_skip": d_new,
        "retained_fraction": round(d_old / d_new, 4),
        "compressed_away_pp": round(d_new - d_old, 4),
        "compressed_away_pct": round(100.0 * (1 - d_old / d_new), 2),
    }
    compression["note"] = (
        "两臂压缩因子近似相等（off 0.3750 vs on 0.3904）⇒ 旧尺子是**近似等比压缩**两臂，"
        "不是专门低估某一臂；其后果是 Δ 被压缩约 56%，且 OFF 基线 p1 被低估 36.65pp（用于 MDE 的 p1 因此也错）。"
        "相对漏判率 ON 略低于 OFF，绝对条数 89>70 纯属 ON 基数更大——不得写成「系统性低估干预臂」。"
    )

    payload = {
        "artifact": "r50-calib-20261101",
        "ruler_version": R.RULER_VERSION,
        "impl_sha256": R.IMPL_SHA256,
        "lexicon_sha256": R.LEXICON_SHA256,
        "lexicon_source": R.LEXICON_SOURCE,
        "status": "POST_HOC_DEVELOPMENT_SET_CALIBRATION",
        "disclaimer": (
            "本文件是在 R49 已冻结日志上做的 post-hoc 开发集标定。"
            "其中的 Δ / p / MDE 一律不得写成效果判决、不得写「有效/无效/显著改善/生活气息提升」；"
            "唯一用途是选点消歧与下一轮功效估算。"
        ),
        "strata_definitions": {
            "opener6": "strip_lead_paren(body) 前 6 字符命中词表（= R49 detail_opener6，逐字同口径）",
            "first_clause": "strip_lead_paren(body) 首个分句命中词表",
            "first_clause_skip": "strip_lead_paren(body) 起跳过≤2个「≤8字且无具体物」前导分句后首个分句命中",
            "anywhere": "未剥旁白整条正文命中词表（= R49 detail_body）",
        },
        "mde_method": {
            "formula": "p̄=(p1n1+p2n2)/(n1+n2); SE=sqrt(p̄(1-p̄)(1/n1+1/n2)); |p1-p2|/SE - z_b >= z_a",
            "alpha": 0.05, "two_sided": True, "power": 0.8,
            "z_alpha_2": 1.96, "z_beta": 0.8416, "n1": n_off, "n2": n_on,
        },
        "arms": {"off": off, "on": on},
        "contrast": contrast,
        "mde_table": mde_table,
        "compression_analysis": compression,
        "no_cue": {
            "off": {"num": off["no_cue"]["num"], "den": off["no_cue"]["den"], "rate_pct": no_cue_off_pp},
            "on": {"num": on["no_cue"]["num"], "den": on["no_cue"]["den"], "rate_pct": no_cue_on_pp},
            "diff_pp": round(no_cue_on_pp - no_cue_off_pp, 4),
        },
        "r49_reconcile": {"checks": reconcile, "all_match": all_match},
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    with open(args.out_json, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")

    print("reconcile_all_match=%s" % all_match)
    for k in STRATA:
        c = contrast[k]
        print("%-18s off=%d/%d(%s%%) on=%d/%d(%s%%) d=%+.2fpp p=%.6f MDE=%spp"
              % (k, c["off"]["num"], c["off"]["den"], c["off"]["rate_pct"],
                 c["on"]["num"], c["on"]["den"], c["on"]["rate_pct"],
                 c["delta_pp"], c["fisher_two_sided_p"], c["mde_pp_from_off_p1"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
