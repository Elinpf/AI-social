#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""judge 协议 v2 自证：重复 3 次的多数票达成率 + 两两 ρ（均值）+ 参数核验

判据（leader）：
  * 多数票达成率 = 每条消息、三个维度中**至少两维**满足"三人一致(3/3)"的比例
  * ρ = 两两之间（0-1,0-2,1-2）取均值，逐维；≥0.70 达标
  * 达标线：ρ ≥ 0.70（逐维，至少主要维度）且多数票 ≥ 80%
输出：md + json
"""
import argparse, itertools, json, statistics
from collections import defaultdict

DIMS = ("naturalness", "persona_fit", "specificity", "is_reply")


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    def rank(v):
        """**并列取平均秩**（关键修正）：不加并列修正会让 ρ 在"分数大量重复"的 judge 数据上严重失真。"""
        order = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0]*len(v); i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys); n = len(xs)
    mx, my = sum(rx)/n, sum(ry)/n
    num = sum((a-mx)*(b-my) for a, b in zip(rx, ry))
    den = (sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))**0.5
    return round(num/den, 4) if den else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.runs, encoding="utf-8")]
    params = rows[0].get("request_params") if rows else {}
    tpl = rows[0].get("template_sha256") if rows else None
    by = defaultdict(dict)
    for r in rows:
        if r.get("parsed"):
            by[r.get("msg_uid")][r["rep"]] = r["parsed"]

    complete = {k: v for k, v in by.items() if all(i in v for i in range(3))}
    # 逐维：3/3 一致率 + 两两 ρ 均值
    dim_stats = {}
    for dim in DIMS:
        full = agree = 0
        rhos = []
        for uid, reps in complete.items():
            vals = [reps[i].get(dim) for i in range(3)]
            if dim == "is_reply":
                if any(not isinstance(x, (int, float)) or x <= 0 for x in vals):
                    continue
            if not all(isinstance(x, (int, float)) for x in vals):
                continue
            full += 1
            if len(set(vals)) == 1:
                agree += 1
            for i, j in itertools.combinations(range(3), 2):
                rho = spearman([vals[i]], [vals[j]])  # 单点无法算 ρ
        # 两两 ρ 需跨消息对齐
        for i, j in itertools.combinations(range(3), 2):
            xs, ys = [], []
            for uid, reps in complete.items():
                v1, v2 = reps[i].get(dim), reps[j].get(dim)
                if dim == "is_reply" and (not isinstance(v1, (int, float)) or not isinstance(v2, (int, float)) or v1 <= 0 or v2 <= 0):
                    continue
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    xs.append(v1); ys.append(v2)
            r = spearman(xs, ys)
            if r is not None:
                rhos.append(r)
        dim_stats[dim] = {"n_msgs": full, "agree_3of3": agree,
                          "agree_rate": round(agree/full, 4) if full else None,
                          "rho_pairwise": rhos,
                          "rho_mean": round(statistics.mean(rhos), 4) if rhos else None,
                          "rho_pass_070": (statistics.mean(rhos) >= 0.70) if rhos else False}

    # 消息级多数票：三维里至少两维 3/3 一致
    msg_majority = 0
    n_msg = 0
    for uid, reps in complete.items():
        dims_ok = 0
        counted = 0
        for dim in DIMS:
            vals = [reps[i].get(dim) for i in range(3)]
            if dim == "is_reply" and any(not isinstance(x, (int, float)) or x <= 0 for x in vals):
                continue
            if not all(isinstance(x, (int, float)) for x in vals):
                continue
            counted += 1
            if len(set(vals)) == 1:
                dims_ok += 1
        if counted >= 3:
            n_msg += 1
            if dims_ok >= 3:
                msg_majority += 1
    rate = round(msg_majority/n_msg, 4) if n_msg else None

    verdict = []
    if (dim_stats["naturalness"]["rho_mean"] or 0) < 0.70:
        verdict.append("naturalness ρ<0.70")
    if rate is None or rate < 0.80:
        verdict.append("多数票达成率<80%")
    out = {"runs": a.runs, "n_calls": len(rows), "request_params": params,
           "template_sha256": tpl, "n_msgs_complete3": len(complete),
           "dims": dim_stats, "msg_majority": {"n_msgs": n_msg, "n_pass": msg_majority, "rate": rate},
           "pass": len(verdict) == 0, "fail_reasons": verdict}

    md = ["# judge 协议 v2 · 自证结果（重复 3 次，只验一致性、不判臂）", "",
          f"> 数据 `{a.runs}`（{len(rows)} 次调用）；完整 3 次的样本 = **{len(complete)} 条消息**", "",
          "## 1. 参数核验（协议 v2 §1）", "",
          f"- **请求参数（首条实测 dump）**：`{json.dumps(params, ensure_ascii=False)}`",
          f"- **模板 sha256**：`{tpl}`", "",
          "## 2. 一致性（逐维）", "",
          "| 维度 | 可用消息 | 3/3 一致 | 一致率 | 两两 ρ | ρ 均值 | ≥0.70 |", "|---|---|---|---|---|---|---|"]
    for dim in DIMS:
        d = dim_stats[dim]
        md.append(f"| {dim} | {d['n_msgs']} | {d['agree_3of3']} | {d['agree_rate']} | {d['rho_pairwise']} | **{d['rho_mean']}** | {'✅' if d['rho_pass_070'] else '❌'} |")
    md += ["", "## 3. 消息级多数票（三维中至少两维 3/3 一致）", "",
           f"- 可计消息 **{n_msg}** 条（四维中至少三维可用），达成多数票（≥3 维 3/3 一致）**{msg_majority}** 条 ⇒ **{rate}**（达标线 ≥0.80）", "",
           "## 4. 判定", "",
           f"**{'PASS：v2 自证通过' if not verdict else 'FAIL：v2 仍不达标'}**" + (f"；卡在：{', '.join(verdict)}" if verdict else ""), ""]
    json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)
    open(a.out_md, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
