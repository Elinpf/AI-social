#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R51「需求的人话化 + 紧迫门控」读数器（只读、零 LLM、零跑批）。

## 问题定性（为什么需要这条尺子）

`code/life/agent.py::_mood_line()` 过去**无条件**把机器口径的最紧需求拼进提示词：
`情绪：饥饿；最紧的需求：satiety=12`。两个后果：

  1. **噪声注入**：六维需求里只有一维是"最紧"，它常常并不紧迫（值 ≥40，`dialogue_threads.mood_label`
     此时已返回「平和」），却照样占了提示词预算，诱导模型去说"我缺什么"。
  2. **生活语汇缺席**：提示词里全是英文维名 + 裸数值，对话正文里几乎不出现"累/困/饿"这类人话
     （R49-off 冻结批实测：疲劳族 2/191 = 1.05%）。

所以本尺子**分开量三件事**，避免把它们混成一个数：

  * **注入率类（结构性读数，来自 `payload.ctx`）**：噪声需求注入率、真紧迫需求保留率。
  * **表层生活语汇（来自 `payload.body`）**：疲劳族 / 饮食族 词命中率。
  * **分布（描述项）**：最紧需求维度分布、情绪标签分布。

## 口径（先冻结，再读数；改这里 = 改尺子）

  * 样本 = `run.jsonl` 里 `type ∈ {MSG_DM, MSG_PUBLIC, MSG_GROUP}` 且 `payload.body` 非空的记录。
  * **紧迫线 `URGENT_THRESHOLD = 40`**：与 `code/life/dialogue_threads.py::mood_label` 的 40 **同源**
    （全维 ≥40 时 `mood_label` 返回「平和」）。`need_value < 40` ⇒ 真紧迫；`>= 40` ⇒ 噪声。
  * **注入判定**：
      - 若记录里带 `payload.ctx.need_speech`（ON 臂的 additive 审计键）⇒ 用其 `injected` 布尔值，
        这是**观测值**；
      - 若无该键（OFF 臂 / 未开臂）⇒ 按**改前代码语义**（`_mood_line()` 无条件注入）记为
        `injected = True`，并在输出里标 `inject_source="structural_pre_change"`，
        **明确标注这是结构默认而非观测**。
  * **生活语汇**两族词表冻结在下方常量里（不读外部词表文件；sha256 记入输出）：
      - `FATIGUE`（疲劳族）：累 / 困 / 乏 / 歇 / 打盹 / 打哈欠 / 睁不开眼 / 缓口气
      - `FOOD`（饮食族）：吃 / 饭 / 饿 / 面包 / 菜 / 汤 / 茶 / 粥 / 饼 / 干粮
    只做**子串命中**，不做分词（中文短句场景下分词只会引入第二套口径）。

输出 JSON（每个比率带 `num/den/rate/wilson95`；`den=0` 写 `null`，**不写 0**）。
本脚本不改日志、不联网、不调 LLM；两次运行输出逐字节相等。

用法:
  python3 tools/metrics/need_to_speech.py --log v2/evidence/<dir>/run.jsonl --label off \
      --out-json v2/evidence/<dir>/r51_readings_off.json
  # 两臂对照（Fisher 双侧 p + 与预登记阈值机械比对）
  python3 tools/metrics/need_to_speech.py --compare-off <off>/run.jsonl --compare-on <on>/run.jsonl \
      --out-json v2/evidence/r51-need-speech-compare.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys

MSG_TYPES = {"MSG_DM", "MSG_PUBLIC", "MSG_GROUP"}

#: 尺子版本（**改词表 = 改尺子**，必须在报告里标注版本变化）
RULER_VERSION = "r51-need-speech-v1"

#: 紧迫线：与 `code/life/dialogue_threads.py::mood_label` 的 40 同源
URGENT_THRESHOLD = 40

#: 疲劳族词表（生活语汇·累/困）—— 冻结，不增删
FATIGUE = ("累", "困", "乏", "歇", "打盹", "打哈欠", "睁不开眼", "缓口气")
#: 饮食族词表（生活语汇·饿/吃）—— 冻结，不增删
FOOD = ("吃", "饭", "饿", "面包", "菜", "汤", "茶", "粥", "饼", "干粮")


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


IMPL_SHA256 = _sha256_text(
    RULER_VERSION + "\n" + str(URGENT_THRESHOLD) + "\n" + "|".join(FATIGUE) + "\n" + "|".join(FOOD)
)
LEXICON_SHA256 = _sha256_text("|".join(FATIGUE) + "\n" + "|".join(FOOD))


def wilson95(k: int, n: int, z: float = 1.96) -> dict | None:
    if n <= 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"p": round(p, 6), "lo": round(max(0.0, c - h), 6), "hi": round(min(1.0, c + h), 6)}


def ratio(k: int, n: int) -> dict:
    if n <= 0:
        return {"num": k, "den": 0, "rate": None, "rate_pct": None, "status": "no_denominator",
                "wilson95": None}
    return {"num": k, "den": n, "rate": round(k / n, 6), "rate_pct": round(100.0 * k / n, 4),
            "status": "ok", "wilson95": wilson95(k, n)}


def _hit(body: str, words: tuple) -> bool:
    return any(w in body for w in words)


def collect(path: str) -> list[dict]:
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") not in MSG_TYPES:
                continue
            payload = rec.get("payload") or {}
            body = payload.get("body")
            if not isinstance(body, str) or not body.strip():
                continue
            ctx = payload.get("ctx") or {}
            need = ctx.get("need") or {}
            dim, val = "", None
            if isinstance(need, dict) and need:
                dim, val = next(iter(need.items()))
                try:
                    val = int(val)
                except (TypeError, ValueError):
                    val = None
            ns = ctx.get("need_speech")
            out.append({"body": body.strip(), "dim": dim, "val": val,
                        "mood": ctx.get("mood"), "need_speech": ns})
    return out


def measure(records: list[dict]) -> dict:
    n = len(records)
    with_need = [r for r in records if r["val"] is not None]
    urgent = [r for r in with_need if r["val"] < URGENT_THRESHOLD]
    noise = [r for r in with_need if r["val"] >= URGENT_THRESHOLD]

    def injected(r: dict) -> bool:
        ns = r["need_speech"]
        if isinstance(ns, dict) and "injected" in ns:
            return bool(ns["injected"])
        return True  # 改前语义：无条件注入

    def audit_used(rs: list[dict]) -> bool:
        return bool(rs) and all(isinstance(r["need_speech"], dict) and "injected" in r["need_speech"]
                                for r in rs)

    noise_inj = sum(1 for r in noise if injected(r))
    urgent_inj = sum(1 for r in urgent if injected(r))

    dims: dict[str, int] = {}
    for r in with_need:
        dims[r["dim"]] = dims.get(r["dim"], 0) + 1
    moods: dict[str, int] = {}
    for r in records:
        m = r["mood"] or "<none>"
        moods[m] = moods.get(m, 0) + 1

    vals = sorted(r["val"] for r in with_need)
    return {
        "n_msgs": n,
        "n_with_need": len(with_need),
        "need_inject_rate": ratio(len(with_need), n),
        "noise_need_rate": ratio(len(noise), len(with_need)),
        "urgent_need_rate": ratio(len(urgent), len(with_need)),
        "noise_inject_rate": ratio(noise_inj, len(noise)),
        "urgent_keep_rate": ratio(urgent_inj, len(urgent)),
        "inject_source": {
            "noise": "observed_ctx_need_speech" if audit_used(noise) else "structural_pre_change",
            "urgent": "observed_ctx_need_speech" if audit_used(urgent) else "structural_pre_change",
        },
        "need_value": {
            "min": vals[0] if vals else None,
            "median": vals[len(vals) // 2] if vals else None,
            "max": vals[-1] if vals else None,
        },
        "dim_dist": dict(sorted(dims.items(), key=lambda kv: (-kv[1], kv[0]))),
        "mood_dist": dict(sorted(moods.items(), key=lambda kv: (-kv[1], kv[0]))),
        "fatigue_hit": ratio(sum(1 for r in records if _hit(r["body"], FATIGUE)), n),
        "food_hit": ratio(sum(1 for r in records if _hit(r["body"], FOOD)), n),
        "fatigue_or_food_hit": ratio(
            sum(1 for r in records if _hit(r["body"], FATIGUE) or _hit(r["body"], FOOD)), n),
    }


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2×2 表 [[a,b],[c,d]] 的双侧 Fisher 精确检验 p（超几何求和，纯标准库）。"""
    n = a + b + c + d
    r1, r2, c1, c2 = a + b, c + d, a + c, b + d

    def lcomb(n_: int, k_: int) -> float:
        return math.lgamma(n_ + 1) - math.lgamma(k_ + 1) - math.lgamma(n_ - k_ + 1)

    def prob(x: int) -> float:
        return math.exp(lcomb(r1, x) + lcomb(r2, c1 - x) - lcomb(n, c1))

    lo, hi = max(0, c1 - r2), min(r1, c1)
    p_obs = prob(a)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs * (1 + 1e-9)))


def mde_pp(p1: float, n1: int, n2: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """两独立比例双侧检验的最小可检效应（百分点）。p1=基线比例。"""
    from statistics import NormalDist
    z_a = NormalDist().inv_cdf(1 - alpha / 2)
    z_b = NormalDist().inv_cdf(power)

    def ok(delta: float) -> bool:
        p2 = p1 + delta
        if not (0.0 < p2 < 1.0):
            return False
        pbar = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = math.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n2))
        return se > 0 and abs(delta) / se - z_b >= z_a

    step = 0.0001
    d = step
    while d < 1.0:
        if ok(d):
            return round(d * 100, 2)
        d += step
    return float("nan")


def compare(off_path: str, on_path: str) -> dict:
    off = measure(collect(off_path))
    on = measure(collect(on_path))
    # ---- 预登记阈值（逐字抄自 reports/R51-prereg-need-speech-20261101.md §3）----
    M1_NOISE_MAX_PCT = 1.0     # ON 臂噪声需求注入率必须 ≤ 1%（结构性门控）
    M1_KEEP_MIN_PCT = 99.0     # ON 臂真紧迫需求保留率必须 ≥ 99%
    E1_MDE_PP = 5.5            # 疲劳族命中率 ON − OFF 的达标线（= OFF 基线 n=191 双侧 α=.05/power=.80 反解的 MDE 5.47pp）
    E1_MAX_P = 0.05            # 且 Fisher 双侧 p < 0.05
    N_FLOOR = 160              # 每臂消息数下限

    rows = {}
    for key in ("noise_inject_rate", "urgent_keep_rate", "fatigue_hit", "food_hit",
                "fatigue_or_food_hit", "need_inject_rate", "noise_need_rate"):
        o, n_ = off[key], on[key]
        if o["den"] == 0 or n_["den"] == 0:
            rows[key] = {"off": o, "on": n_, "delta_pp": None, "fisher_p": None}
            continue
        p = fisher_exact_two_sided(o["num"], o["den"] - o["num"], n_["num"], n_["den"] - n_["num"])
        rows[key] = {"off": o, "on": n_,
                     "delta_pp": round((n_["rate"] - o["rate"]) * 100, 2),
                     "fisher_p": round(p, 6)}

    verdict = {}
    if off["n_msgs"] < N_FLOOR or on["n_msgs"] < N_FLOOR:
        verdict["U1"] = f"分母不足（off={off['n_msgs']} on={on['n_msgs']} 下限={N_FLOOR}）⇒ 全部不可判"
    else:
        verdict["U1"] = "ok"
    nir = rows["noise_inject_rate"]["on"]["rate_pct"]
    ukr = rows["urgent_keep_rate"]["on"]["rate_pct"]
    verdict["M1"] = "pass" if (nir is not None and nir <= M1_NOISE_MAX_PCT
                               and ukr is not None and ukr >= M1_KEEP_MIN_PCT) else "fail"
    d1 = rows["fatigue_hit"]["delta_pp"]
    p1 = rows["fatigue_hit"]["fisher_p"]
    verdict["E1"] = ("pass" if d1 is not None and d1 >= E1_MDE_PP and p1 is not None and p1 < E1_MAX_P
                     else "not_achieved")

    return {
        "ruler_version": RULER_VERSION,
        "impl_sha256": IMPL_SHA256,
        "lexicon_sha256": LEXICON_SHA256,
        "urgent_threshold": URGENT_THRESHOLD,
        "off": {"log": off_path, "sha256": hashlib.sha256(open(off_path, "rb").read()).hexdigest(),
                **off},
        "on": {"log": on_path, "sha256": hashlib.sha256(open(on_path, "rb").read()).hexdigest(),
               **on},
        "rows": rows,
        "thresholds": {"M1_noise_inject_max_pct": M1_NOISE_MAX_PCT,
                       "M1_urgent_keep_min_pct": M1_KEEP_MIN_PCT,
                       "E1_mde_pp": E1_MDE_PP, "E1_max_p": E1_MAX_P, "n_floor": N_FLOOR},
        "verdict": verdict,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R51 需求人话化/紧迫门控读数器（只读、零 LLM）")
    ap.add_argument("--log", default="", help="单臂 run.jsonl 路径")
    ap.add_argument("--label", default="", help="标签（off/on/…），只写进 JSON，不参与计算")
    ap.add_argument("--out-json", default="", help="把完整 JSON 落盘（同时打印摘要行）")
    ap.add_argument("--mde", action="store_true", help="同时打印各判据 MDE（基于 OFF 臂比例）")
    ap.add_argument("--compare-off", default="", help="两臂模式：OFF 臂 run.jsonl")
    ap.add_argument("--compare-on", default="", help="两臂模式：ON 臂 run.jsonl")
    args = ap.parse_args(argv)

    if args.compare_off and args.compare_on:
        res = compare(args.compare_off, args.compare_on)
        text = json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True)
        if args.out_json:
            with open(args.out_json, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
        r = res["rows"]
        print("n_off=%d n_on=%d" % (res["off"]["n_msgs"], res["on"]["n_msgs"]))
        for k in ("noise_inject_rate", "urgent_keep_rate", "fatigue_hit", "food_hit"):
            o, n_ = r[k]["off"], r[k]["on"]
            print("%-20s off=%s/%s (%.2f%%)  on=%s/%s (%.2f%%)  delta=%+.2fpp  fisher_p=%s"
                  % (k, o["num"], o["den"], o["rate_pct"] or 0.0,
                     n_["num"], n_["den"], n_["rate_pct"] or 0.0,
                     r[k]["delta_pp"] or 0.0, r[k]["fisher_p"]))
        print("verdict=%s" % json.dumps(res["verdict"], ensure_ascii=False, sort_keys=True))
        return 0

    if not args.log:
        ap.error("需要 --log，或 --compare-off/--compare-on")
    log_bytes = open(args.log, "rb").read()
    res = measure(collect(args.log))
    payload = {
        "ruler_version": RULER_VERSION,
        "impl_sha256": IMPL_SHA256,
        "lexicon_sha256": LEXICON_SHA256,
        "urgent_threshold": URGENT_THRESHOLD,
        "fatigue_lexicon": list(FATIGUE),
        "food_lexicon": list(FOOD),
        "label": args.label,
        "log": {"path": args.log, "sha256": hashlib.sha256(log_bytes).hexdigest()},
        **res,
    }
    if args.mde:
        payload["mde"] = {
            "fatigue_hit": mde_pp(res["fatigue_hit"]["rate"] or 0.0, res["n_msgs"], res["n_msgs"]),
            "food_hit": mde_pp(res["food_hit"]["rate"] or 0.0, res["n_msgs"], res["n_msgs"]),
            "noise_inject_rate": mde_pp(res["noise_inject_rate"]["rate"] or 0.0,
                                        res["n_with_need"] or 1, res["n_with_need"] or 1),
        }
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print("n_msgs=%d n_with_need=%d noise_inject=%s/%s urgent_keep=%s/%s fatigue=%s/%s food=%s/%s"
          % (res["n_msgs"], res["n_with_need"],
             res["noise_inject_rate"]["num"], res["noise_inject_rate"]["den"],
             res["urgent_keep_rate"]["num"], res["urgent_keep_rate"]["den"],
             res["fatigue_hit"]["num"], res["fatigue_hit"]["den"],
             res["food_hit"]["num"], res["food_hit"]["den"]))
    if args.mde:
        print("mde=" + json.dumps(payload["mde"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
