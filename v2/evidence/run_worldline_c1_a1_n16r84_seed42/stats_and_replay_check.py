#!/usr/bin/env python3
"""C-1 窗口结论定级所需的三项补充复算（只读 run.jsonl + config，不跑批、不改代码）。

Part A 统计判据：0/48 vs 11/48 的 Fisher 精确检验（双侧）＋ 两臂 Wilson 95% CI
                （无 scipy，二项系数自算，可复算）
Part B 排除「复读机」：11 条命中消息 vs C-1 注入行原文的 8-gram 重叠
                三档：无重叠（自己组织语言）/ 部分重叠（复用词组重组）/ 高重叠（照抄，计负面）
Part C L-7 同 cut 对照：round<40 内两臂的官方 8-gram dup 率（tools/l7 口径）

用法：cd v2/evidence && python3 run_worldline_c1_a1_n16r84_seed42/stats_and_replay_check.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]   # 本文件在 v2/evidence/<run>/ 下 ⇒ 上溯 3 层到仓根
sys.path.insert(0, str(ROOT))
from tools.d5.dialogue_metrics import normalize_body          # noqa: E402
from tools.l7.l7_baseline_recount import dup_index, load_msgs  # noqa: E402

A1 = ROOT / "v2/evidence/run_worldline_c1_a1_n16r84_seed42/run.jsonl"
CTRL = ROOT / "v2/evidence/run_worldline_c1_ctrl_n16r84_seed42/run.jsonl"
LO, HI = 30, 35
PROXY_WORDS = ("镇上", "镇里", "集市", "市集", "眼下", "节庆", "气氛", "紧俏", "供货",
               "灾", "闹了场病", "通告", "修公共设施", "外乡人", "大活动")


# ---------------------------------------------------------------- Part A
def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2 表 [[a,b],[c,d]] 的双侧 Fisher 精确检验 p 值（超几何概率求和法）。"""
    n = a + b + c + d
    r1, r2 = a + b, c + d
    c1 = a + c

    def p_of(x: int) -> float:
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)

    p_obs = p_of(a)
    lo = max(0, c1 - r2)
    hi = min(r1, c1)
    return sum(p_of(x) for x in range(lo, hi + 1) if p_of(x) <= p_obs + 1e-12)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


# ---------------------------------------------------------------- Part B
def prompt_phrases() -> list[str]:
    """C-1 注入行的内容片段全集（不含 meta 指令句）。"""
    cfg = json.loads((ROOT / "code/config/places.json").read_text(encoding="utf-8"))
    names = sorted({p.get("name_cn") or p["place_id"] for p in cfg["places"]})
    kinds = ["刚换了季", "镇上在办节庆", "镇上有了新机会", "镇里在修公共设施", "集市供货有点紧",
             "东西不太好买", "镇上气氛有点紧", "出了点小乱子", "遭了点灾", "闹了场病",
             "来了外乡人", "镇里发了新通告", "大家在议一件事", "有场大活动"]
    return [f"你眼下在{n}" for n in names] + kinds + ["集市上东西有点紧俏"]


def shingles(t: str, k: int = 8) -> set[str]:
    return {t[i:i + k] for i in range(max(0, len(t) - k + 1))}


def longest_common_run(a: str, b: str) -> int:
    """最长公共子串长度（字符）。"""
    best = 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def part_b() -> int:
    phrases = prompt_phrases()
    norm_phrases = [normalize_body(p) for p in phrases]
    prompt_sh: set[str] = set()
    for p in norm_phrases:
        prompt_sh |= shingles(p)
    hits = []
    for line in A1.open(encoding="utf-8"):
        e = json.loads(line)
        if e.get("round") is None or not (LO <= e["round"] <= HI):
            continue
        if e.get("type") not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            continue
        body = (e.get("payload") or {}).get("body") or ""
        if not any(w in body for w in PROXY_WORDS):
            continue
        hits.append({"round": e["round"], "seq": e.get("seq"), "body": body})

    print(f"[Part B] 命中消息 {len(hits)} 条，逐条对 C-1 注入行做 8-gram 重叠：")
    buckets = {"无重叠": 0, "部分重叠": 0, "高重叠": 0}
    for h in hits:
        nb = normalize_body(h["body"])
        bsh = shingles(nb)
        inter = bsh & prompt_sh
        ratio = len(inter) / len(prompt_sh) if prompt_sh else 0.0
        verbatim = [p for p in norm_phrases if len(p) >= 6 and p in nb]
        run = max((longest_common_run(nb, p) for p in norm_phrases), default=0)
        if verbatim or ratio >= 0.5:
            cls = "高重叠"
        elif inter:
            cls = "部分重叠"
        else:
            cls = "无重叠"
        buckets[cls] += 1
        print(f"  r{h['round']:>2} seq={h['seq']:<7} 最长公共串={run:>2}字符  "
              f"8gram交集={len(inter):>2}/{len(prompt_sh)} 比={ratio:.3f}  逐字成句={bool(verbatim)}  => {cls}")
        print(f"        body={h['body'][:70]}")
        if inter:
            print(f"        共有的 8-gram={sorted(inter)[:4]}")
    print(f"  三档分布：{buckets}   高重叠占 {buckets['高重叠']}/{len(hits)}")
    print(f"  ⇒ {'负面：表达生硬（≥一半为高重叠）' if hits and buckets['高重叠'] >= len(hits)/2 else '未达负面阈值（高重叠 < 一半）'}")
    print()
    return buckets["高重叠"]


# ---------------------------------------------------------------- Part C
def l7_cut(path: Path, cut: int, label: str) -> dict:
    msgs = [m for m in load_msgs(str(path)) if True]
    # 需要 round 过滤 → 重新按行读
    keep = []
    for line in path.open(encoding="utf-8"):
        e = json.loads(line)
        if e.get("type") not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            continue
        if e.get("round") is None or e["round"] >= cut:
            continue
        p = e.get("payload") or {}
        keep.append({"seq": e.get("seq"), "type": e["type"], "from": p.get("from"),
                     "body": p.get("body") or "", "memory_refs": []})
    dup = dup_index(keep)
    rate = len(dup) / len(keep) if keep else None
    print(f"  {label} (round<{cut}): MSG={len(keep)} L-7_dup={len(dup)} rate={rate:.4f}" if rate is not None
          else f"  {label}: 无消息")
    return {"label": label, "cut": cut, "n_msg": len(keep), "dup": len(dup), "rate": rate}


def window_msgs(path: Path) -> list[dict]:
    out = []
    for line in path.open(encoding="utf-8"):
        e = json.loads(line)
        if e.get("type") not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            continue
        if e.get("round") is None or not (LO <= e["round"] <= HI):
            continue
        p = e.get("payload") or {}
        out.append({"round": e["round"], "seq": e.get("seq"), "tid": p.get("thread_id"),
                    "body": p.get("body") or ""})
    return out


def part_a2() -> None:
    """聚类修正：消息不是独立观测（16 线程 × 平均 3 条）⇒ 补线程级 2×2 检验。"""
    print("== Part A2 聚类修正（线程级）==")
    res = {}
    for label, p in (("ctrl", CTRL), ("a1", A1)):
        msgs = window_msgs(p)
        tids = {m["tid"] for m in msgs}
        hit_msgs = [m for m in msgs if any(w in m["body"] for w in PROXY_WORDS)]
        hit_tids = [m["tid"] for m in hit_msgs]
        import collections
        dist = collections.Counter(hit_tids)
        res[label] = (len(msgs), len(tids), len(hit_msgs), len(set(hit_tids)), dist)
        print(f"  {label}: 消息 {len(msgs)} / 线程 {len(tids)} / 命中消息 {len(hit_msgs)} / 命中线程 {len(set(hit_tids))}")
        print(f"      命中按线程分布: {dict(dist)}")
        print(f"      线程规模: {dict(collections.Counter(m['tid'] for m in msgs))}")
    a_n, t_n, a_hit, a_th, _ = res["a1"]
    c_n, _, c_hit, c_th, _ = res["ctrl"]
    p2 = fisher_exact_two_sided(a_th, t_n - a_th, c_th, t_n - c_th)
    print(f"  线程级 2x2：a1 {a_th}/{t_n} vs ctrl {c_th}/{t_n}")
    print(f"  线程级 Wilson 95% CI：a1 {wilson(a_th, t_n)}  ctrl {wilson(c_th, t_n)}")
    print(f"  线程级 Fisher 精确检验（双侧）p = {p2:.6g}")
    print(f"  ⇒ {'线程级仍显著（结论不降级）' if p2 < 0.05 else '线程级不显著 ⇒ 降级为方向性信号'}")
    print()


def main() -> int:
    print("== Part A 统计判据（消息级，窗口 rounds 30–35，分母各 48）==")
    a1_k, a1_n = 11, 48
    ct_k, ct_n = 0, 48
    p = fisher_exact_two_sided(a1_k, a1_n - a1_k, ct_k, ct_n - ct_k)
    print(f"  a1  命中 {a1_k}/{a1_n} = {a1_k / a1_n:.4f}   95% CI {wilson(a1_k, a1_n)}")
    print(f"  ctrl 命中 {ct_k}/{ct_n} = {ct_k / ct_n:.4f}   95% CI {wilson(ct_k, ct_n)}")
    print(f"  Fisher 精确检验（双侧）p = {p:.6g}")
    print()
    part_a2()

    print("== Part B 复读机排除 ==")
    part_b()

    print("== Part C L-7 同 cut 对照（官方 8-gram dup 口径）==")
    l7_cut(CTRL, 40, "ctrl cut<40")
    l7_cut(A1, 40, "a1   cut<40")
    print()
    print("  注：cut<40 与窗口 6 轮不是同一分母；另给窗口内读数供对照：")
    l7_cut(CTRL, HI + 1, "ctrl 全批当前(round<=35)")
    l7_cut(A1, HI + 1, "a1   全批当前(round<=35)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
