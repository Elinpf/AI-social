#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G 系列 · 闲话八卦（第三方提及 / 谈话链）指标 —— 只读、可复算、零 LLM

作者：sim-engineer（模拟实现工程师）｜ 本轮维度：勘测第一名「闲话八卦 / 第三方提及」
类型：**只读统计脚本**。不调 LLM、不改世界态、不写项目 `code/**` 与 `config/**`。
口径来源：
  * 勘测排序与口径草案：`artifacts/recon/round-recon.md` §7 🥇
  * 噪声带：`v2/evidence/D3-noiseband-two-level.md`（n=170 档 ±10.6pp）
  * 可对账的既有指标：`tools/d5/dialogue_metrics.py::F-7a_offscreen_mention`（1.07% = 2/187）
  * 措辞层守卫指标：`v2/evidence/d3_corpus_annotate.py` 的 U4(裸 ID)/U2(旁白)

指标定义（分子/分母写死，任何比率都必须带分母输出）：

G-1 第三方提及率（per-message）
  分子 = 正文中出现的**居民主干名**里，至少有一个属于「第三方集合」的消息条数
  第三方集合 = 全部 20 个居民主干名 − 本条发送者 − 本条线程的 participants
  分母 = 该 run 全部 MSG_DM / MSG_PUBLIC / MSG_GROUP 条数
  排除噪声：① 排除「提到自己在场伙伴」（已由 − participants 实现）；
           ② 名字匹配用「主干名子串包含」、不做分词（与 D5 口径一致，保证可复算）；
           ③ 重名已在 personas.json 检查为 0（脚本每次运行重新校验，重名则 fail-loud）。

G-1b_strict / G-1b_upper 越界提及率（per-message，**优先级高于 G-1**；两臂并列发表）
  共同部分：在 G-1 命中的消息中，若「任一提及者在同一 round 的位置 ≠ **本条消息的说话地点**」
            ⇒ 该条记为越界提及。提及者位置取自 PLACE_ARRIVED / PLACE_MOVE 的 payload.place，
            按 (round, agent_id) 索引；该 round 内取 seq ≤ 本条 seq 的最后一条（无则取该 round 首条并计 fallback）。
  **说话地点的两种取法（这就是唯一差别）**：
    G-1b_strict（主口径）：说话地点 = 本条 MSG 的 payload.place。
        本条 place 为空（MSG_PUBLIC 恒为 null）⇒ **不可判**，计入 unknown_place_base，不计入越界。
    G-1b_upper（敏感性臂，Leader 18:12 要求）：payload.place 为空时，用**发送者自己在同一 round
        最近一条 PLACE_ARRIVED/PLACE_MOVE 的 place** 作为说话地点。
        这样 48 条 MSG_PUBLIC 不再整块落在否决范围外（"否决要宽，结论要严"）。
        发送者当回合无任何位置事件 ⇒ 记 unknown_place_base_upper，仍不计入越界（宁漏不虚增）。
  位置查不到（提及者）⇒ 计入 unknown_place_lookups，不计入越界。
  分母：两者都用该 run 全部 MSG 条数（便于与 G-1 并排）。
  否决规则：**用 upper 判**——ΔG-1b_upper > 0 即一票否决；strict 仅作辅助说明。
  不可判比例：unknown_place_base_upper / G-1 命中条数；>20% ⇒ 不出 G-1 结论，只报事实。

G-2 闲话传播链（per-topic-cluster，**仅当日志有 `ctx.topic` / `topic` 时可用**）
  分子 = 被 ≥3 个不同 agent 先后提及同一 topic 的簇数
  分母 = 有非空 topic 的簇数
  无 topic 字段的旧日志（v0-anchor）⇒ `applicable=false`，不出比率。

守卫指标（防「用称呼换闲聊」，同时输出，不单独下结论）
  L-8 裸 ID 率 = 正文命中 `P\\d{3}` 的消息 / 全部 MSG
  L-2 旁白率 = 正文首字符为（ 或 ( 的消息 / 全部 MSG
  L-3 括号块率 = 正文任意位置含（…）/ (…) 的消息 / 全部 MSG

F-7a 对账块（同一份原始输出内，用于证明本实现与既有口径同源）
  按 tools/d5/dialogue_metrics.py 的 F-7a 规则复算一遍（提及任意非发送者名字 + 位置不符），
  期望在 v0-anchor 上等于 2/187 = 1.07%。**若不等，先查本脚本，不许改口径。**

用法（在仓库根执行）：
  python3 experiments/gossip-third-party/g_metrics.py \
      --run v0anchor=v2/evidence/run_d2_before_n16_seed42/run.jsonl \
      --out-json experiments/gossip-third-party/g_metrics_v0anchor.json \
      --out-quotes experiments/gossip-third-party/g_quotes_v0anchor.md

  # 两臂对照（A0/A1 都落盘后）：
  python3 experiments/gossip-third-party/g_metrics.py \
      --run A0=v2/evidence/run_d2_after_n16_seed42/run.jsonl \
      --run A1=v2/evidence/run_gossip_a1_n16_seed42/run.jsonl \
      --out-json ... --out-quotes ...

退出码：0 正常；2 = personas 重名 / 名字表为空（fail-loud）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
CHANNEL = {"MSG_DM": "dm", "MSG_PUBLIC": "public", "MSG_GROUP": "group"}

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]                      # experiments/gossip-third-party/ -> 仓库根
DEFAULT_NAMES = REPO_ROOT / "code" / "config" / "personas.json"

PAREN_OPEN = ("（", "(")
PAREN_BLOCK = re.compile(r"[（(]([^）)]{0,60})[）)]")
AGENT_ID_RE = re.compile(r"P\d{3}(?!\d)")


# ---------------------------------------------------------------- 名字表
def load_names(path: Path) -> tuple[dict, list[str]]:
    """personas.json -> ({persona_id: 主干名}, [主干名…])；重名/空表 fail-loud。"""
    d = json.loads(path.read_text(encoding="utf-8"))
    pid2name: dict[str, str] = {}
    for p in d.get("personas", []):
        pid = str(p.get("persona_id") or "")
        nm = str(p.get("display_name") or "").split("·")[-1].strip()
        if pid and nm:
            pid2name[pid] = nm
    if not pid2name:
        raise SystemExit("[FAIL] personas.json 解析出 0 个主干名")
    dup = [k for k, v in Counter(pid2name.values()).items() if v > 1]
    if dup:
        raise SystemExit(f"[FAIL] 主干名重名，G-1 无法唯一归因：{dup}")
    return pid2name, list(pid2name.values())


# ---------------------------------------------------------------- 读日志
def load_run(path: str, pid2name: dict) -> dict:
    msgs: list[dict] = []
    # place_by_round[(round, agent_id)] = [(seq, place), …]（按 seq 升序，供"当回合最近一条"取用）
    place_ev: dict[tuple[int, str], list[tuple[int, str]]] = defaultdict(list)
    rounds_seen = set()
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        t = e.get("type")
        rnd = e.get("round")
        seq = e.get("seq")
        if rnd is not None:
            rounds_seen.add(rnd)
        p = e.get("payload") or {}
        if t in ("PLACE_ARRIVED", "PLACE_MOVE"):
            aid = p.get("agent_id") or e.get("actor")
            plc = p.get("place") or p.get("to_place")
            if aid and plc and rnd is not None:
                place_ev[(int(rnd), str(aid))].append((int(seq or 0), str(plc)))
            continue
        if t not in MSG_TYPES:
            continue
        author = p.get("author") or p.get("from")
        msgs.append({
            "seq": seq,
            "round": rnd,
            "type": t,
            "channel": CHANNEL[t],
            "author": str(author) if author else None,
            "to": p.get("to"),
            "group_id": p.get("group_id"),
            "place": p.get("place"),
            "day": p.get("day"),
            "slot": p.get("slot"),
            "topic": p.get("topic"),
            "template": (p.get("tag_hints") or [None])[0],
            "participants": p.get("participants"),
            "thread_id": p.get("thread_id"),
            "body": p.get("body") or "",
        })
    for k in place_ev:
        place_ev[k].sort()
    # 便于 O(log n) 取"当回合最近一条"：直接线性即可（每 round 事件极少）
    schema = "explicit" if any(m["thread_id"] for m in msgs) else "legacy"
    return {"path": path, "msgs": msgs, "place_ev": dict(place_ev),
            "thread_schema": schema, "rounds_seen": len(rounds_seen)}


def place_of(place_ev: dict, rnd, pid: str, seq) -> tuple[str | None, bool]:
    """(round, pid) 在 seq 时刻所在地点；返回 (place|None, 是否为该 round 首条 fallback)。"""
    if rnd is None:
        return None, False
    arr = place_ev.get((int(rnd), str(pid)))
    if not arr:
        return None, False
    s = int(seq or 0)
    before = [(sq, pl) for sq, pl in arr if sq <= s]
    if before:
        return before[-1][1], False
    return arr[0][1], True          # 该 round 内本条之前没有位置事件 ⇒ 用该 round 首条（记 fallback）



# ---------------------------------------------------------------- 口径实现
def participants_of(m: dict, schema: str) -> set:
    """本条消息所在「对话圈子」的在场参与者集合（用于排除『提到在场伙伴』）。

    explicit（D2 起）：直接读 payload.participants。
    legacy（v0-anchor）：没有线程字段，按渠道近似 —— DM={发送者,收件人}；
                        GROUP={发送者}（旧日志不含成员名单，**宁可少排除、不虚增第三方**）；
                        PUBLIC={发送者}。
    """
    if schema == "explicit" and m.get("participants"):
        return {str(x) for x in m["participants"]}
    s = {m["author"]} if m.get("author") else set()
    if m["channel"] == "dm" and m.get("to"):
        s.add(str(m["to"]))
    return s


def names_in(body: str, all_names: list[str]) -> list[str]:
    """正文命中的居民主干名（子串包含，确定性顺序）。"""
    return [nm for nm in all_names if nm in body]


def rate(k: int, n: int) -> float | None:
    return round(100.0 * k / n, 2) if n else None


def wilson(k: int, n: int, z: float = 1.96):
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(100 * max(0.0, c - h), 2), round(100 * min(1.0, c + h), 2)]


def compute(run: dict, pid2name: dict, all_names: list[str]) -> dict:
    msgs = run["msgs"]
    n = len(msgs)
    schema = run["thread_schema"]
    place_ev = run["place_ev"]
    name2pid = {v: k for k, v in pid2name.items()}

    hits = []            # G-1 命中明细
    off_strict = []      # G-1b_strict 越界明细
    off_upper = []       # G-1b_upper 越界明细
    f7a_hits = []        # F-7a 对账口径命中
    unknown_place_base = 0          # strict：本条 place 为空
    unknown_place_base_upper = 0     # upper：发送者当回合无位置事件（真正不可判）
    upper_fallback_first = 0         # upper：用该 round 首条位置事件兜底
    unknown_place_lookup = 0         # 提及者位置查不到
    hits_with_unknown_upper = 0      # upper 下完全不可判的 G-1 命中条数

    for m in msgs:
        names = names_in(m["body"], all_names)
        if not names:
            continue
        parts = participants_of(m, schema)
        own = pid2name.get(m["author"] or "")
        third = [nm for nm in names if nm != own and nm not in parts]
        if not third:
            continue
        hits.append({"seq": m["seq"], "round": m["round"], "channel": m["channel"],
                     "author": m["author"], "author_name": own,
                     "mentions": third, "place": m["place"], "body": m["body"]})

        def offscreen(base_place, detail_out):
            """在给定说话地点下判越界；返回 True 表示记入越界。"""
            nonlocal unknown_place_lookup
            if not base_place:
                return False
            for nm in third:
                pid = name2pid.get(nm)
                if pid is None:
                    continue
                plc, _fb = place_of(place_ev, m["round"], pid, m["seq"])
                if plc is None:
                    unknown_place_lookup += 1
                    continue
                if plc != base_place:
                    detail_out.append({"seq": m["seq"], "round": m["round"],
                                       "speaking_place": base_place, "mentions": third, "body": m["body"]})
                    return True
            return False

        # ---- G-1b_strict：说话地点 = 本条 payload.place
        if not m["place"]:
            unknown_place_base += 1
        else:
            offscreen(m["place"], off_strict)

        # ---- G-1b_upper：payload.place 为空时回落到发送者当回合最近位置事件
        base_upper = m["place"]
        if not base_upper:
            base_upper, fb = place_of(place_ev, m["round"], m["author"] or "", m["seq"])
            if base_upper:
                if fb:
                    upper_fallback_first += 1
            else:
                unknown_place_base_upper += 1
        if base_upper:
            offscreen(base_upper, off_upper)
        else:
            hits_with_unknown_upper += 1

        # ---- F-7a 对账：提及任意「非发送者」名字 + 位置不符（不排除 participants）
        others = [nm for nm in names if nm != own]
        if others and m["place"]:
            for nm in others:
                pid = name2pid.get(nm)
                if pid is None:
                    continue
                plc, _fb = place_of(place_ev, m["round"], pid, m["seq"])
                if plc is None:
                    continue
                if plc != m["place"]:
                    f7a_hits.append({"seq": m["seq"], "round": m["round"], "mentions": [nm]})
                    break

    # ---- 提及对象分布
    mention_counter = Counter(nm for h in hits for nm in h["mentions"])
    by_ch_total = Counter(m["channel"] for m in msgs)
    by_ch_hit = Counter(h["channel"] for h in hits)

    # ---- 守卫指标
    l8 = sum(1 for m in msgs if AGENT_ID_RE.search(m["body"]))
    l2 = sum(1 for m in msgs if (m["body"].lstrip()[:1] or "") in PAREN_OPEN)
    l3 = sum(1 for m in msgs if PAREN_BLOCK.search(m["body"]))

    # ---- G-2 闲话传播链（仅 topic 可用时）
    topic_agents: dict[str, set] = defaultdict(set)
    for m in msgs:
        if m.get("topic"):
            topic_agents[str(m["topic"])].add(str(m["author"]))
    g2_applicable = bool(topic_agents)
    g2_denom = len(topic_agents)
    g2_hit = sum(1 for v in topic_agents.values() if len(v) >= 3) if g2_applicable else 0

    return {
        "path": run["path"],
        "n_msgs": n,
        "channels": dict(by_ch_total),
        "rounds_seen": run["rounds_seen"],
        "thread_schema": schema,
        "G-1_third_party_mention": {
            "hit": len(hits), "denom": n, "rate_pct": rate(len(hits), n), "ci95_pct": wilson(len(hits), n),
            "unit": "per-message",
            "by_channel": {ch: {"hit": by_ch_hit.get(ch, 0), "denom": by_ch_total.get(ch, 0),
                                "rate_pct": rate(by_ch_hit.get(ch, 0), by_ch_total.get(ch, 0))}
                           for ch in ("dm", "group", "public")},
            "mention_targets": dict(mention_counter.most_common()),
        },
        "G-1b_strict_offscreen_mention": {
            "hit": len(off_strict), "denom": n, "rate_pct": rate(len(off_strict), n),
            "ci95_pct": wilson(len(off_strict), n), "unit": "per-message",
            "speaking_place_source": "本条 MSG 的 payload.place",
            "unknown_place_base": unknown_place_base,
            "unknown_place_lookups": unknown_place_lookup,
            "rule": "G-1 命中中，任一提及者同 round 位置 ≠ 本条 place ⇒ 越界；本条 place 空或提及者位置查不到 ⇒ 不计入（宁漏不虚增）",
        },
        "G-1b_upper_offscreen_mention": {
            "hit": len(off_upper), "denom": n, "rate_pct": rate(len(off_upper), n),
            "ci95_pct": wilson(len(off_upper), n), "unit": "per-message",
            "speaking_place_source": "payload.place；为空时回落到发送者当 round seq≤本条 的最近一条 PLACE_ARRIVED/PLACE_MOVE",
            "unknown_place_base": unknown_place_base_upper,
            "unknown_place_lookups": unknown_place_lookup,
            "fallback_to_round_first": upper_fallback_first,
            "g1_hits_with_unknown_place": hits_with_unknown_upper,
            "unknown_ratio_of_g1_hits_pct": rate(hits_with_unknown_upper, len(hits)) if hits else None,
            "veto_rule": "ΔG-1b_upper > 0 ⇒ 一票否决；不可判比例 >20% ⇒ 不出 G-1 结论",
            "rule": "同 strict，但说话地点对 MSG_PUBLIC 做 sender 位置回落，使 48 条公开消息不落在否决范围外（否决要宽，结论要严）",
        },
        "G-2_rumor_chain": {
            "applicable": g2_applicable,
            "hit": g2_hit if g2_applicable else None,
            "denom": g2_denom if g2_applicable else None,
            "rate_pct": rate(g2_hit, g2_denom) if g2_applicable else None,
            "unit": "per-topic-cluster",
            "rule": "同一 topic 被 ≥3 个不同 agent 提及的簇 / 有非空 topic 的簇；无 topic 字段 ⇒ applicable=false",
        },
        "guards": {
            "L-8_naked_id": {"hit": l8, "denom": n, "rate_pct": rate(l8, n)},
            "L-2_narration_head": {"hit": l2, "denom": n, "rate_pct": rate(l2, n)},
            "L-3_paren_any": {"hit": l3, "denom": n, "rate_pct": rate(l3, n)},
        },
        "F-7a_reconciliation": {
            "hit": len(f7a_hits), "denom": n, "rate_pct": rate(len(f7a_hits), n),
            "note": "按 tools/d5/dialogue_metrics.py::F-7a 规则复算；v0-anchor 期望 2/187=1.07%",
        },
        "_hits": hits,
        "_off_hits_strict": off_strict,
        "_off_hits_upper": off_upper,
    }


# ---------------------------------------------------------------- 输出
def emit_quotes(res: dict, path: str, k: int = 5) -> None:
    """每条命中按 seq 升序原样摘录（不随机、不挑选），供人工核对。"""
    lines = ["# G 系列 · 第三方提及 / 越界提及 原文样本", "",
             "> 抽样规则：按 `seq` 升序取前 k 条命中，**不随机、不挑选**。全量命中明细见同名 `.json` 的 `_hits` / `_off_hits_strict` / `_off_hits_upper`。",
             ""]
    for name, r in res["runs"].items():
        lines.append(f"## {name}（{r['path']}）")
        lines.append("")
        lines.append(f"- n_msgs={r['n_msgs']} thread_schema={r['thread_schema']} "
                     f"G-1={r['G-1_third_party_mention']['hit']}/{r['G-1_third_party_mention']['denom']}="
                     f"{r['G-1_third_party_mention']['rate_pct']}% "
                     f"G-1b_strict={r['G-1b_strict_offscreen_mention']['hit']}/{r['G-1b_strict_offscreen_mention']['denom']}="
                     f"{r['G-1b_strict_offscreen_mention']['rate_pct']}% "
                     f"G-1b_upper={r['G-1b_upper_offscreen_mention']['hit']}/{r['G-1b_upper_offscreen_mention']['denom']}="
                     f"{r['G-1b_upper_offscreen_mention']['rate_pct']}%")
        lines.append("")
        for label, key in (("G-1 第三方提及", "_hits"),
                           ("G-1b_strict 越界提及", "_off_hits_strict"),
                           ("G-1b_upper 越界提及（敏感性臂）", "_off_hits_upper")):
            lines.append(f"### {label}")
            rows = sorted(r.get(key) or [], key=lambda x: x["seq"] if x["seq"] is not None else 0)
            if not rows:
                lines.append("")
                lines.append("- （本 run 无命中）")
                lines.append("")
                continue
            lines.append("")
            for h in rows[:k]:
                lines.append(f"- seq={h['seq']} round={h['round']} place={h.get('place')} "
                             f"提及={h['mentions']}：{h['body']}")
            if len(rows) > k:
                lines.append(f"- ……（共 {len(rows)} 条，其余见 json）")
            lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="name=path，可多次")
    ap.add_argument("--names", default=str(DEFAULT_NAMES))
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-quotes", default=None)
    a = ap.parse_args()

    pid2name, all_names = load_names(Path(a.names))
    print(f"[names] {len(pid2name)} 个居民主干名，重名=0", file=sys.stderr)

    res = {
        "generated_by": "experiments/gossip-third-party/g_metrics.py",
        "criterion_source": "artifacts/recon/round-recon.md §7 🥇（G-1/G-1b）+ v2/evidence/D3-noiseband-two-level.md",
        "names_sha_note": f"names_file={a.names}; n_names={len(pid2name)}",
        "runs": {},
    }
    for spec in a.run:
        name, _, path = spec.partition("=")
        if not Path(path).exists():
            print(f"[WARN] 跳过缺失 run {name}: {path}", file=sys.stderr)
            continue
        run = load_run(path, pid2name)
        r = compute(run, pid2name, all_names)
        res["runs"][name] = r
        pm = r["G-1_third_party_mention"]
        st = r["G-1b_strict_offscreen_mention"]
        up = r["G-1b_upper_offscreen_mention"]
        print(f"== {name}  n_msgs={r['n_msgs']}  schema={r['thread_schema']}  channels={r['channels']}")
        print(f"   G-1  第三方提及     {pm['hit']}/{pm['denom']} = {pm['rate_pct']}%  ci={pm['ci95_pct']}")
        print(f"   G-1b_strict 越界    {st['hit']}/{st['denom']} = {st['rate_pct']}%  "
              f"(place空={st['unknown_place_base']}, 位置未知={st['unknown_place_lookups']})")
        print(f"   G-1b_upper  越界    {up['hit']}/{up['denom']} = {up['rate_pct']}%  "
              f"(sender位置不可判={up['unknown_place_base']}, round首条兜底={up['fallback_to_round_first']}, "
              f"不可判占G-1命中={up['unknown_ratio_of_g1_hits_pct']}%)")
        print(f"   守卫 L-8={r['guards']['L-8_naked_id']['rate_pct']}%  "
              f"L-2={r['guards']['L-2_narration_head']['rate_pct']}%  "
              f"L-3={r['guards']['L-3_paren_any']['rate_pct']}%")
        print(f"   对账 F-7a       {r['F-7a_reconciliation']['hit']}/{r['F-7a_reconciliation']['denom']} = "
              f"{r['F-7a_reconciliation']['rate_pct']}%")
        print(f"   提及对象        {pm['mention_targets']}")

    # 两臂对照（仅当恰好两臂）
    names = list(res["runs"])
    if len(names) == 2:
        A, B = names
        ra, rb = res["runs"][A], res["runs"][B]
        cmp = {}
        for key in ("G-1_third_party_mention", "G-1b_strict_offscreen_mention",
                    "G-1b_upper_offscreen_mention"):
            va, vb = ra[key], rb[key]
            cmp[key] = {"A_rate_pct": va["rate_pct"], "B_rate_pct": vb["rate_pct"],
                        "delta_pp": (round((vb["rate_pct"] or 0) - (va["rate_pct"] or 0), 2)
                                     if va["rate_pct"] is not None and vb["rate_pct"] is not None else None),
                        "A_ci95": va["ci95_pct"], "B_ci95": vb["ci95_pct"],
                        "denom_A": va["denom"], "denom_B": vb["denom"]}
        res["compare"] = {"A": A, "B": B, "rows": cmp,
                          "band_note": "判定须用 n 对应档的 B2 上界（n=170→±10.6pp）；本脚本只出读数与 CI，不自动下结论"}
        print("== compare (B - A)")
        for k, v in cmp.items():
            print(f"   {k:24s} {v['A_rate_pct']}% -> {v['B_rate_pct']}%  Δ={v['delta_pp']}pp")

    Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out_json).write_text(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[ok] json -> {a.out_json}", file=sys.stderr)
    if a.out_quotes:
        emit_quotes(res, a.out_quotes)
        print(f"[ok] quotes -> {a.out_quotes}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
