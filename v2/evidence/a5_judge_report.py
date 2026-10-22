#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A5 judge 分层汇总：分层表 + 五维 Δ + κ/ρ + 一句结论（口径写死，不改）"""
import argparse, json, statistics
from collections import Counter, defaultdict

DIMS = ("naturalness", "persona_fit", "specificity", "is_reply")


def kappa(pairs):
    if not pairs:
        return None
    po = sum(1 for a, b in pairs if (a < 4) == (b < 4)) / len(pairs)
    pa = sum(1 for a, _ in pairs if a < 4) / len(pairs)
    pb = sum(1 for _, b in pairs if b < 4) / len(pairs)
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0]*len(v)
        for pos, i in enumerate(order): r[i] = pos + 1
        return r
    rx, ry = rank(xs), rank(ys); n = len(xs)
    mx, my = sum(rx)/n, sum(ry)/n
    num = sum((a-mx)*(b-my) for a, b in zip(rx, ry))
    den = (sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))**0.5
    return round(num/den, 4) if den else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--sample", action="append", required=True, help="ARM=sample_json")
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()

    layer_of = {}
    for spec in a.sample:
        arm, _, path = spec.partition("=")
        d = json.load(open(path, encoding="utf-8"))
        for s in d["samples"]:
            layer_of[(arm, s.get("msg_uid"))] = s.get("layer")

    rows = [json.loads(l) for l in open(a.runs, encoding="utf-8")]
    ok = [r for r in rows if r.get("parsed")]
    res = {"source": a.runs, "n_calls": len(rows), "n_parsed": len(ok), "by_arm": {}, "by_layer": {}}

    def agg(rs):
        out = {}
        for dim in DIMS:
            v = [r["parsed"].get(dim) for r in rs if isinstance(r["parsed"].get(dim), (int, float))]
            if dim == "is_reply":
                v = [x for x in v if x > 0]
            out[dim] = {"n": len(v), "mean": round(statistics.mean(v), 2) if v else None,
                        "median": statistics.median(v) if v else None,
                        "dist": dict(sorted(Counter(v).items())) if v else {}}
        pairs = defaultdict(dict)
        for r in rs:
            pairs[r.get("msg_uid")][r.get("rep")] = r["parsed"]
        cons = {}
        for dim in DIMS:
            xs, ys, pp = [], [], []
            for _, d in pairs.items():
                if 0 in d and 1 in d:
                    v0, v1 = d[0].get(dim), d[1].get(dim)
                    if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                        if dim == "is_reply" and (v0 <= 0 or v1 <= 0):
                            continue
                        xs.append(v0); ys.append(v1); pp.append((v0, v1))
            if pp:
                cons[dim] = {"n_pairs": len(pp),
                             "exact": round(sum(1 for x, y in pp if x == y)/len(pp), 4),
                             "kappa": kappa(pp), "rho": spearman(xs, ys)}
        return {"dims": out, "consistency": cons}

    for arm in sorted({r["arm"] for r in rows}):
        res["by_arm"][arm] = agg([r for r in ok if r["arm"] == arm])
    for arm in sorted({r["arm"] for r in rows}):
        for layer in ("t2_3", "t4_6", "t7p"):
            rs = [r for r in ok if r["arm"] == arm and layer_of.get((r["arm"], r.get("msg_uid"))) == layer]
            if rs:
                res["by_layer"][f"{arm}|{layer}"] = agg(rs)

    md = ["# A5 judge · 分层配平结果（A1-回复预算 vs A5）", "",
          f"> 来源 `{a.runs}`（{len(rows)} 次调用，可解析 {len(ok)}）；维度 5 项；重复 2 次。", ""]
    arms = sorted(res["by_arm"])
    md += ["## 1. 总体（各层合并）", "",
           "| 维度 | " + " | ".join(arms) + " | Δ(CTRL−A5，正=CTRL 更高) |", "|---" * (len(arms)+2) + "|"]
    for dim in DIMS:
        vals = [res["by_arm"][x]["dims"][dim]["mean"] for x in arms]
        d = round(vals[-1]-vals[0], 2) if all(v is not None for v in vals) else None
        md.append(f"| {dim} | " + " | ".join(f"{v}（n={res['by_arm'][x]['dims'][dim]['n']}）" for v, x in zip(vals, arms)) + f" | **{d}** |")
    md += ["", "## 2. 分层（层内两臂等量抽样的直接对照）", "",
           "| 层 | 维度 | " + " | ".join(arms) + " | Δ |", "|---|---" + "---" * (len(arms)+1) + "|"]
    for layer in ("t2_3", "t4_6", "t7p"):
        keys = [f"{x}|{layer}" for x in arms]
        if not any(k in res["by_layer"] for k in keys):
            md.append(f"| {layer} | — | 两臂该层均为 0 线程（结构上限 max_turns=6） | | |")
            continue
        for dim in DIMS:
            vals = [res["by_layer"].get(k, {}).get("dims", {}).get(dim, {}).get("mean") for k in keys]
            d = round(vals[-1]-vals[0], 2) if vals[0] is not None and vals[-1] is not None else None
            md.append(f"| {layer} | {dim} | " + " | ".join(str(v) for v in vals) + f" | **{d}** |")
    md += ["", "> Δ 列口径：`CTRL − A5`（正值 = CTRL 分更高；负值 = A5 更高）。", "",
           "## 3. 一致性（重复 2 次）", "", "| 臂 | 维度 | 对数 | exact | κ | ρ |", "|---|---|---|---|---|---|"]
    for arm in arms:
        for dim in DIMS:
            c = res["by_arm"][arm]["consistency"].get(dim)
            md.append(f"| {arm} | {dim} | {c['n_pairs']} | {c['exact']} | {c['kappa']} | {c['rho']} |" if c else f"| {arm} | {dim} | – | – | – | – |")
    md += ["", "> κ<0.4 或 ρ<0.5 的维度**不得进结论**，只能作观察（标 `†`）。", "",
           "## 4. 判读（写死口径）", "",
           "- Δ 超带外且方向为 A5 更好 ⇒ 可写「多出来的对话在**主观上也更好**」；",
           "- **Δ ≤ 0.21 ⇒ 只能写「结构上多出了对话，主观自然度无证据」**（最可能，也是可接受结论）；",
           "- Δ 方向为 A5 更差 ⇒ 照实写，并回查「长对话里是否废话变多」。", ""]
    open(a.out_md, "w", encoding="utf-8").write("\n".join(md))
    json.dump(res, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)
    print(f"[ok] {a.out_md} / {a.out_json}")


if __name__ == "__main__":
    main()
