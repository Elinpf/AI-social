"""G-1 形态测量（M1/M2/M3）—— 只读、零 LLM、可复算。

口径（冻结于读数落盘前）：
  total_hits        = 该 agent 作为 author、且 G-1 判为「第三方提及」的消息**条数**
  per-target count  = 该 agent 命中消息中提到该对象的**消息条数**（一条消息可同时计多个对象）
  distinct_targets  = 该 agent 命中过的不同对象个数 k
  M1 命中分散度      = distinct_targets / total_hits
  M2 最大单对象占比  = max_count(单一对象) / total_hits
  M3 order_score    = 1 − inv / C(k,2)，仅**处理臂**（有 hint 名单）可算：
        L = 该 agent 提示词渲染出的名单字面顺序（`v2/evidence/g1_hint_order.txt`，
            实现为 sorted(display_name) 码点序）
        H = 该 agent 的命中对象按**首次命中时间**（round, seq）升序
        inv = H 在 L 中的下标序列的逆序对数；C(k,2)=k(k−1)/2
        同一时刻出现多个「首次命中」⇒ 该 agent 记 n/a 并计入 tie_agents
        k<3 ⇒ n/a
  hits_outside_hint = 命中落在「G-1 候选 18 人里但不在 hint 14 人内」的**消息条数**
        （n16 下这 4 人是未实例化的 书言/弦歌/石头/阿散 ⇒ 只能来自模型自发，不是照单念）

用法（仓库根）：
  python3 v2/evidence/g1_form_metrics.py --run <run.jsonl> --tag treat \
      --sha8 <sha8> --instantiated 16 --out-json v2/evidence/g1_form_metrics_treat_<sha8>.json
  B0（无名单）加 `--no-list` ⇒ order_score 一律 n/a（无 L，不定义）。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
GM = REPO / "experiments" / "gossip-third-party" / "g_metrics.py"


def _load_gm():
    import importlib.util
    spec = importlib.util.spec_from_file_location("g_metrics", GM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def inv_count(seq: list[int]) -> int:
    return sum(1 for i in range(len(seq)) for j in range(i + 1, len(seq)) if seq[i] > seq[j])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--tag", required=True, help="b0 / treat")
    ap.add_argument("--sha8", required=True)
    ap.add_argument("--instantiated", type=int, default=16)
    ap.add_argument("--no-list", action="store_true", help="B0：无 hint 名单 ⇒ M3 一律 n/a")
    ap.add_argument("--hint-order", default=str(REPO / "v2/evidence/g1_hint_order.txt"))
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", default=None)
    a = ap.parse_args()

    gm = _load_gm()
    pid2name, all_names = gm.load_names(REPO / "code" / "config" / "personas.json")
    run = gm.load_run(a.run, pid2name)

    # 实例化 roster 与 hint 名单（与运行期同源）
    sys.path.insert(0, str(REPO / "code"))
    from life.persona import load_personas
    from life.dialogue_threads import build_display_map
    ps = load_personas(REPO / "code" / "config" / "personas.json")
    roster = sorted(ps)[: a.instantiated]
    disp = build_display_map(ps)
    name2pid = {v: k for k, v in pid2name.items()}
    outside_pool = [nm for nm in all_names if name2pid.get(nm) not in roster]

    # ---- 收集命中
    per_agent = defaultdict(lambda: {"total_hits": 0, "counts": Counter(),
                                     "first": {}, "outside": 0, "msgs": 0})
    for m in run["msgs"]:
        nm_hit = gm.names_in(m["body"], all_names)
        if not nm_hit:
            continue
        parts = gm.participants_of(m, run["thread_schema"])
        own = pid2name.get(m["author"] or "")
        third = [nm for nm in nm_hit if nm != own and nm not in parts]
        if not third:
            continue
        rec = per_agent[m["author"]]
        rec["total_hits"] += 1
        for nm in third:
            rec["counts"][nm] += 1
            key = (m["round"], m["seq"])
            rec["first"].setdefault(nm, key)
        # M4：按**消息条数**计（一条消息含多个名单外名字也只计 1）
        if any(nm in outside_pool for nm in third):
            rec["outside"] += 1

    # ---- hint 名单顺序 L（按 (agent, partner) 逐对；这里按 agent 给出"与 partner 无关的全集序"）
    # 说明：真实渲染时 L 依赖当轮对话对象（名单剔除在场对象）。本脚本按 agent 记录全部可能 L，
    # 取**与命中对象集合相容**的那一个用于 M3；若多个 partner 的 L 都相容，取第一条并记 partner。
    hint_L = {}
    if not a.no_list:
        for ag in roster:
            variants = {}
            for partner in roster:
                if partner == ag:
                    continue
                L = sorted(nm for nm in (disp[p] for p in roster) if nm not in (disp[ag], disp[partner]))
                variants[partner] = L
            hint_L[ag] = variants

    rows = []
    tie_agents = []
    for ag in roster:
        rec = per_agent.get(ag) or {"total_hits": 0, "counts": Counter(), "first": {}, "outside": 0}
        k = len(rec["counts"])
        total = rec["total_hits"]
        max_count = max(rec["counts"].values()) if rec["counts"] else 0
        row = {
            "agent_id": ag, "agent_name": disp.get(ag),
            "total_hits": total, "distinct_targets": k,
            "max_count": max_count,
            "M1_dispersion": round(k / total, 4) if total else None,
            "M2_max_share": round(max_count / total, 4) if total else None,
            "hits_outside_hint": rec["outside"] or 0,
            "hint_len": None, "k": k, "C_k_2": k * (k - 1) // 2,
            "order_score": None, "order_note": "",
            "objects": dict(rec["counts"].most_common()),
        }
        if a.no_list:
            row["order_note"] = "n/a（无 L：B0 提示词不含名单，order_score 不定义）"
        elif k < 3:
            row["order_note"] = f"n/a（k={k}<3）"
        else:
            # 选相容的 L：命中对象 ⊆ L 的第一个 partner 变体
            chosen = None
            for partner, L in hint_L.get(ag, {}).items():
                if set(rec["counts"]).issubset(set(L)):
                    chosen = (partner, L); break
            if chosen is None:
                row["order_note"] = "n/a（命中对象不落在任何 partner 变体的名单内）"
            else:
                partner, L = chosen
                row["hint_len"] = len(L)
                row["hint_partner"] = partner
                # 首次命中时刻
                H = sorted(rec["counts"], key=lambda nm: rec["first"][nm])
                times = [rec["first"][nm] for nm in H]
                if len(set(times[:1])) and len([t for t in times if t == times[0]]) > 1:
                    pass
                # tie 判定：是否存在多个对象共享同一「最早」时刻
                first_time = min(times)
                tied = [nm for nm in H if rec["first"][nm] == first_time]
                if len(tied) > 1:
                    row["order_note"] = f"n/a（并列首个命中：{tied}）"
                    tie_agents.append(ag)
                else:
                    idx = [L.index(nm) for nm in H]
                    inv = inv_count(idx)
                    ck = k * (k - 1) // 2
                    row["order_score"] = round(1 - inv / ck, 4) if ck else None
                    row["order_inv"] = inv
                    row["order_note"] = "ok"
        rows.append(row)

    summary = {
        "tag": a.tag, "sha8": a.sha8, "run": a.run,
        "definitions": {
            "total_hits": "该 agent 作者的 G-1 命中消息条数",
            "M1_dispersion": "distinct_targets / total_hits",
            "M2_max_share": "max_count(单对象消息数) / total_hits",
            "M3_order_score": "1 - inv / C(k,2)；L=渲染名单字面序（sorted(display_name) 码点序）",
            "hits_outside_hint": "命中未实例化居民（n16：书言/弦歌/石头/阿散）的消息条数",
        },
        "instantiated": a.instantiated,
        "roster": roster,
        "outside_hint_pool": outside_pool,
        "outside_hint_pool_detail": [{"pid": name2pid[nm], "display_name": nm} for nm in outside_pool],
        "outside_hint_note": ("这 4 人本轮 n16 世界内未实例化、无位置事件 ⇒ 按「宁漏不虚增」不计入 G-1b 越界，"
                              "故单独列；M4 只作形态登记，不作 F5 或改善判据。"),
        "n_msgs": len(run["msgs"]),
        "total_hits_all_agents": sum(r["total_hits"] for r in rows),
        "tie_agents": tie_agents,
        "agents": rows,
    }
    Path(a.out_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if a.out_md:
        L = [f"# G-1 形态测量 · {a.tag}（sha8={a.sha8}）", "",
             f"- run: `{a.run}`", f"- MSG 条数: **{len(run['msgs'])}**", f"- roster n={a.instantiated}",
             f"- 全 agent G-1 命中消息合计: **{summary['total_hits_all_agents']}**",
             f"- tie_agents: {tie_agents or '无'}", "",
             "| agent | 名 | total_hits | k(distinct) | C(k,2) | M1 | M2 max_share | order_score | 名单外命中 |",
             "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            L.append(f"| {r['agent_id']} | {r['agent_name']} | {r['total_hits']} | {r['k']} | {r['C_k_2']} | "
                     f"{r['M1_dispersion']} | {r['M2_max_share']} | {r['order_score'] if r['order_score'] is not None else 'n/a'} | "
                     f"{r['hits_outside_hint']} |")
        L.append("")
        Path(a.out_md).write_text("\n".join(L), encoding="utf-8")

    print(f"[ok] {a.tag} msgs={len(run['msgs'])} hits={summary['total_hits_all_agents']} "
          f"tie_agents={tie_agents} -> {a.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
