#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-C 统计辅助：只用**冻结读数器**的常量与口径，额外补 bootstrap CI。

定位：**不重新定义任何指标**。P1/P2/len/结构的**定义、正则、词表全部来自**
`v2/evidence/d12c_metrics.py`（sha256 c41cb5ac…，import 其模块常量），
本脚本只做两件事：
  1) 逐项 0/1 或数值序列的**有放回重采样**，得到 Δ(ON−OFF) 的 2.5%/97.5% 分位（B=2000，seed=42）；
  2) Wilson 95% CI（比率型，按两侧各自分母）。

用法：
  python3 v2/evidence/d12c_ci.py --off <OFF>/run.jsonl --on <ON>/run.jsonl \
      --out-json v2/evidence/d12c_ci.json

判读纪律（照任务卡）：
- **CI 含 0 ⇒ 无结论**；
- 比率型必须写清分子/分母；
- 本脚本不产出判定词（判定词由人按判读表 5 档写）。
"""
import argparse, hashlib, importlib.util, json, os, random, re, statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = os.path.join(HERE, "d12c_metrics.py")


def load_frozen():
    spec = importlib.util.spec_from_file_location("d12c_metrics_frozen", FROZEN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_rows(path, m):
    rows = []
    for line in open(path, encoding="utf-8"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") in m.MSG:
            rows.append(e)
    return rows


def item_flags(rows, m):
    """逐消息：P1/P2/len/paren（**常量全部取自冻结模块**）；逐线程：size/turns。"""
    nm = m.names()
    P1, P2, LEN, PAR = [], [], [], []
    th = defaultdict(list)
    for e in rows:
        pl = e.get("payload") or {}
        b = pl.get("body") or ""
        speaker = pl.get("from") or pl.get("author")
        present = {speaker}
        if pl.get("to"):
            present.add(pl["to"])
        present.update(pl.get("participants") or [])
        P1.append(1 if any(re.search(x, b) for x in m.DETAIL) else 0)
        P2.append(1 if any(x in b and x not in present for x in nm) else 0)
        PAR.append(1 if b.lstrip().startswith(("（", "(")) else 0)
        LEN.append(len(m.PAREN.sub("", b).strip()))
        tid = pl.get("thread_id") or f"legacy-{pl.get('msg_uid')}"
        th[tid].append((pl.get("from") or pl.get("author")))
    sizes = [len(v) for v in th.values()]
    turns = []
    for v in th.values():
        spk = v
        turns.append(1 + sum(1 for i in range(1, len(spk)) if spk[i] != spk[i - 1]))
    return {"P1": P1, "P2": P2, "paren": PAR, "len": LEN,
            "thread_sizes": sizes, "thread_turns": turns}


def q(vals, p):
    s = sorted(vals)
    if not s:
        return None
    pos = (len(s) - 1) * p
    lo = int(pos); hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (pos - lo), 4)


def boot_rate_diff(a, b, B, rng):
    diffs = []
    for _ in range(B):
        ra = sum(rng.choice(a) for _ in range(len(a))) / len(a)
        rb = sum(rng.choice(b) for _ in range(len(b))) / len(b)
        diffs.append(100.0 * (rb - ra))
    return {"delta_pp": round(100 * (sum(b) / len(b) - sum(a) / len(a)), 4),
            "ci95_lo": q(diffs, .025), "ci95_hi": q(diffs, .975),
            "contains_zero": q(diffs, .025) <= 0 <= q(diffs, .975)}


def boot_median_diff(a, b, B, rng):
    diffs = []
    for _ in range(B):
        ra = statistics.median([rng.choice(a) for _ in range(len(a))])
        rb = statistics.median([rng.choice(b) for _ in range(len(b))])
        diffs.append(rb - ra)
    return {"delta": round(statistics.median(b) - statistics.median(a), 4),
            "ci95_lo": q(diffs, .025), "ci95_hi": q(diffs, .975),
            "contains_zero": q(diffs, .025) <= 0 <= q(diffs, .975)}


def wilson(k, n, z=1.959963985):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    hw = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [round(100 * (c - hw) / d, 2), round(100 * (c + hw) / d, 2)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()

    m = load_frozen()
    rng = random.Random(a.seed)
    off, on = load_rows(a.off, m), load_rows(a.on, m)
    fo, fn = item_flags(off, m), item_flags(on, m)
    out = {
        "frozen_reader": {"path": FROZEN, "sha256": sha256(FROZEN)},
        "policy": {"B": a.B, "seed": a.seed,
                   "note": "仅补 CI；P1/P2/len/结构的定义与常量全部来自冻结读数器（import 其模块常量）",
                   "rule": "CI 含 0 ⇒ 无结论"},
        "n_msgs": {"off": len(off), "on": len(on)},
        "rates": {}, "medians": {}, "structure": {},
    }
    for key, label in (("P1", "P1_specificity"), ("P2", "P2_thirdparty"), ("paren", "paren_rate_observe")):
        k_o, n_o = sum(fo[key]), len(fo[key])
        k_n, n_n = sum(fn[key]), len(fn[key])
        out["rates"][label] = {
            "off": {"k": k_o, "n": n_o, "pct": round(100 * k_o / n_o, 2), "wilson95": wilson(k_o, n_o)},
            "on": {"k": k_n, "n": n_n, "pct": round(100 * k_n / n_n, 2), "wilson95": wilson(k_n, n_n)},
            "diff": boot_rate_diff(fo[key], fn[key], a.B, rng),
        }
    out["medians"]["len_p50"] = {
        "off": statistics.median(fo["len"]) if fo["len"] else None,
        "on": statistics.median(fn["len"]) if fn["len"] else None,
        "diff": boot_median_diff(fo["len"], fn["len"], a.B, rng),
    }
    out["medians"]["turns_A_p50"] = {
        "off": statistics.median(fo["thread_turns"]) if fo["thread_turns"] else None,
        "on": statistics.median(fn["thread_turns"]) if fn["thread_turns"] else None,
        "diff": boot_median_diff(fo["thread_turns"], fn["thread_turns"], a.B, rng),
    }
    out["structure"] = {
        "n_threads": {"off": len(fo["thread_sizes"]), "on": len(fn["thread_sizes"]),
                      "rel_pct": round(100 * (len(fn["thread_sizes"]) - len(fo["thread_sizes"])) / max(1, len(fo["thread_sizes"])), 2)},
        "n_msgs": {"off": len(off), "on": len(on),
                   "rel_pct": round(100 * (len(on) - len(off)) / max(1, len(off)), 2)},
        "threads_p50": {"off": statistics.median(fo["thread_sizes"]) if fo["thread_sizes"] else None,
                        "on": statistics.median(fn["thread_sizes"]) if fn["thread_sizes"] else None},
        "note": "n_threads / n_msgs 为确定性总数，比值直接给；turns_A_p50 的 CI 见 medians",
    }
    out["limitation"] = "单 seed / 单规模 / 中性树；bootstrap 仅反映抽样不确定性，不含 run 间非确定性（见 D5 §5 同 seed 21.3% 逐条一致率）"
    json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
