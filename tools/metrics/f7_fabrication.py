#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-7 越界编造率 · 规则可判档只读出数器（零 LLM、零联网、零写日志）。

口径来源（唯一）
----------------
* `reports/R4-life-texture.md:43` F-7 定义：
  「judge 拿到该线程时段内**真实发生的事件摘要**，判每条是否编造了日志中不存在的事件；
    率 = 编造条数 / 受检条数」——统计单位 **per-message**。
* `v2/refs/F7-offscreen-criteria.md`（`20cb6aed…`）：提及层 P1/P2 口径、名字表来源、
  point-in-time 在场性（`place_at(seq)`）、旁白剔除（narration=exclude）。
* 仓内既有「编造」判定先例：`code/devtools/storyteller.py::qc_story` Q-6
  「句中数字须逐字来自日志 payload」——即「用日志事实反证文本断言」的规则式做法。

诚实性分层（本任务的核心产物）
------------------------------
R4 的 F-7 原义是**语义级编造判定**；仓内**没有**实现它的规则或 judge
（`LLM_JUDGMENT` 只有 weekly_focus/stance/affection/rel_affinity/respect 五维，无 fabrication）。
故本工具只出「能被日志事实直接反证的窄子集」，并把不可判部分显式计数：

  L1 fabricated_entity        虚构居民：正文出现 `P\\d{3}` 但不在 personas 名单 → 可判
  L2 location_claim_conflict  在场断言矛盾：显式「我…在<场所名>」vs **日志在场事实** → 可判
  L3 prehistory_reference     世界第 0 天引用「昨天/昨晚」→ **不可判**（前史 vs 编造）
  L4 semantic_fabrication     R4 原义 → **不可判**（无 judge 维度，属 code/ 冻结区）

日志里的三处「在场」事实（v2 修订要点：正因有第三处，责任被定位到引擎注入而非模型）
--------------------------------------------------------------------------------
| 事实 | 来源 | 覆盖（scene_anchor ON / OFF 实证） |
|---|---|---|
| `payload.place` | `msg.payload.place` | ON 167/191、OFF 167/191 |
| 位置链 point-in-time | `PLACE_ARRIVED`/`PLACE_MOVE` 链（判据卡 §2.3） | 两臂均有 |
| `ctx.scene.place` | `msg.payload.ctx.scene.place`（scene_anchor 注入给模型的场景块） | **仅 ON 臂**（OFF 191/191 缺失） |

实测关系（两臂同形）：`payload.place` 与位置链 **167/167 完全一致、0 矛盾**；
`ctx.scene.place` 与 `payload.place` 在 167 条同时存在者中 **76 条不一致（45.5%）**。
⇒ 在场**事实基**取 `payload.place`（缺失时回落位置链）；`ctx.scene` 单列为**诊断项**：
它不是事实，而是「引擎喂给模型的场景」。L2 命中若能被 `ctx.scene` 解释，则矛盾源头是
**注入场景过期/错位**，不是模型凭空编造。

确定性
------
输入只读 `--log` / personas.json / places.json；输出无时间戳（`--timestamp` 才写）、
`sort_keys=True`、样本按 seq 升序、无集合序遍历 ⇒ 同输入两次运行逐字节相等（已 `cmp` 实测）。

用法
----
    python3 tools/metrics/f7_fabrication.py \
        --log v2/evidence/run_scene_anchor_on_seed42_n16r24/run.jsonl \
        --out v2/evidence/f7/f7_fabrication_scene_anchor_on_seed42_n16r24.json \
        --batch-id scene_anchor_on_seed42_n16r24

退出码：0 成功 / 2 输入不可用
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "f7-fabrication/2.0"
CALIBER_VERSION = "f7-fabrication-rule/2.0"  # 改任何常量/事实基必须同步升版本

# ---------------------------------------------------------------- 判据常量（写死）

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
PLACE_TYPES = ("PLACE_ARRIVED", "PLACE_MOVE")
PERSONA_PREFIX = "青溪镇·"

# 旁白剔除（判据卡 §4 P1 主判据）：括号整段先删再判定
PAREN_NARRATION_RE = re.compile(r"(?:（[^）]*）|\([^)]*\))")

# 裸 ID：P + 3 位数字，后瞻防 4 位（与 dialogue_metrics.py::AGENT_ID_RE 一致）
AGENT_ID_RE = re.compile(r"P\d{3}(?!\d)")

# L2 窄句式：自我在场断言 = 「我」+ 至多 8 字（不含句读）+「在」+ 场所名（places.json name_cn）
SELF_LOC_HEAD = r"我[^。！？，,；;：:\s]{0,8}?在"

# 时间偏移上下文 ⇒ 不是"此刻在场"断言，不入分母（宁漏不猜）
TIME_SHIFT_RE = re.compile(
    r"昨天|昨晚|昨儿|前天|前日|早上|上午|中午|下午|傍晚|晚上|夜里|那天|上次|上回|上个月|去年|小时候|以前|当年"
)
# 完成体（过去已做完的动作，不是"此刻在哪"）：如「我刚在礼堂排完那首新歌」
PAST_COMPLETED_RE = re.compile(r"刚[^。！？，,]{0,10}完|刚刚完|刚才")

# L3 前史时间词
PREHISTORY_RE = re.compile(r"昨天|昨晚|昨儿|前天|前日")

FACT_MSG = "fact_payload_place"
FACT_CHAIN = "fact_pos_place_chain_pit"
FACT_SCENE = "fact_ctx_scene_place"

SAMPLE_EXCERPT_CHARS = 80


# ---------------------------------------------------------------- 基础工具


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_personas(path: str) -> Tuple[Dict[str, str], Dict[str, Any]]:
    info: Dict[str, Any] = {"path": path, "exists": os.path.exists(path)}
    names: Dict[str, str] = {}
    if not info["exists"]:
        return names, info
    raw = json.load(open(path, encoding="utf-8"))
    items = raw.get("personas", raw) if isinstance(raw, dict) else raw
    for p in items:
        pid = p.get("persona_id") or p.get("id")
        dn = p.get("display_name") or p.get("name") or ""
        if pid and dn:
            names[str(pid)] = dn.replace(PERSONA_PREFIX, "").strip()
    info["sha256"] = sha256_file(path)
    info["n"] = len(names)
    info["name_table_sha256"] = hashlib.sha256(
        canon(dict(sorted(names.items()))).encode("utf-8")).hexdigest()
    info["field"] = "personas[].persona_id + personas[].display_name(strip '青溪镇·')"
    return names, info


def load_places(path: str) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, Any]]:
    info: Dict[str, Any] = {"path": path, "exists": os.path.exists(path)}
    cn2id: Dict[str, str] = {}
    id2cn: Dict[str, str] = {}
    if not info["exists"]:
        return cn2id, id2cn, info
    raw = json.load(open(path, encoding="utf-8"))
    for p in raw.get("places", []):
        pid = p.get("place_id")
        cn = p.get("name_cn")
        if pid and cn:
            cn2id[str(cn)] = str(pid)
            id2cn[str(pid)] = str(cn)
    info["sha256"] = sha256_file(path)
    info["n"] = len(cn2id)
    info["place_names"] = sorted(cn2id.keys())
    return cn2id, id2cn, info


def read_records(path: str) -> List[dict]:
    recs = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            recs.append(json.loads(ln))
    return recs


# ---------------------------------------------------------------- 日志事实层


class Facts:
    def __init__(self, recs: List[dict]):
        self.msgs: List[dict] = []
        self.place_chain: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        self.day_marks: List[Tuple[int, int]] = []
        for r in recs:
            t = r.get("type")
            p = r.get("payload") or {}
            seq = r.get("seq")
            if t in MSG_TYPES:
                scene = (p.get("ctx") or {}).get("scene") or {}
                self.msgs.append({
                    "seq": seq,
                    "round": r.get("round"),
                    "event_type": t,
                    "from": str(p.get("from") or p.get("author") or r.get("actor") or ""),
                    "to": str(p.get("to") or ""),
                    "body": p.get("body") or p.get("text") or "",
                    "fact_payload_place": p.get("place"),
                    "fact_ctx_scene_place": scene.get("place"),
                    "scene_slot": scene.get("slot"),
                })
            elif t in PLACE_TYPES:
                aid = p.get("agent_id")
                plc = p.get("place") or p.get("to_place")
                if aid and plc and seq is not None:
                    self.place_chain[str(aid)].append((seq, str(plc)))
            if isinstance(p, dict) and "day" in p and seq is not None:
                try:
                    self.day_marks.append((seq, int(p["day"])))
                except (TypeError, ValueError):
                    pass
        for aid in self.place_chain:
            self.place_chain[aid].sort()
        self.chain_seqs = {a: [s for s, _ in c] for a, c in self.place_chain.items()}
        self.day_marks.sort()
        self.day_seqs = [s for s, _ in self.day_marks]
        self.msgs.sort(key=lambda m: (m["seq"] is None, m["seq"] or 0))

    def fact_chain(self, seq: Optional[int], aid: str) -> Optional[str]:
        if seq is None:
            return None
        c = self.place_chain.get(aid)
        if not c:
            return None
        i = bisect.bisect_right(self.chain_seqs[aid], seq) - 1
        return c[i][1] if i >= 0 else None

    def fact(self, m: dict) -> Tuple[Optional[str], str]:
        """在场事实：优先 payload.place（两臂 167/167 与位置链一致），缺失时回落位置链。"""
        pp = m.get("fact_payload_place")
        if pp:
            return str(pp), FACT_MSG
        pc = self.fact_chain(m["seq"], m["from"])
        if pc:
            return pc, FACT_CHAIN
        return None, "none"

    def day_at(self, seq: Optional[int]) -> Optional[int]:
        if seq is None:
            return None
        i = bisect.bisect_right(self.day_seqs, seq) - 1
        return self.day_marks[i][1] if i >= 0 else None


def _claims(text: str, self_loc_re, claim_re, excluded: Counter) -> List[str]:
    out: List[str] = []
    for mt in self_loc_re.finditer(text):
        ctx = text[max(0, mt.start() - 10): mt.end() + 3]
        if TIME_SHIFT_RE.search(ctx):
            excluded["excluded_time_shift"] += 1
            continue
        if PAST_COMPLETED_RE.search(ctx):
            excluded["excluded_past_completed"] += 1
            continue
        cm = claim_re.search(mt.group(0))
        if cm:
            out.append(cm.group(1))
    return sorted(set(out))


# ---------------------------------------------------------------- 各层


def layer_l1(facts: Facts, names: Dict[str, str]) -> dict:
    denom = 0
    hits: List[dict] = []
    for m in facts.msgs:
        text = PAREN_NARRATION_RE.sub("", m["body"])
        ids = [i for i in AGENT_ID_RE.findall(text) if i != m["from"]]
        if not ids:
            continue
        denom += 1
        unknown = sorted({i for i in ids if i not in names})
        if unknown:
            hits.append({
                "layer": "L1", "seq": m["seq"], "round": m["round"], "channel": m["event_type"],
                "from": m["from"], "to": m["to"], "unknown_pids": unknown,
                "mentioned_pids": sorted(set(ids)),
                "body_excerpt": m["body"][:SAMPLE_EXCERPT_CHARS],
            })
    return {
        "id": "L1_fabricated_entity",
        "question": "正文是否引用了 personas 名单里不存在的居民编号？",
        "decidable": True,
        "denominator_definition": "正文（旁白已剔除）含至少 1 个非发言人裸 P-ID 的消息数（per-message）",
        "denominator": denom,
        "numerator": len(hits),
        "rate": (len(hits) / denom) if denom else None,
        "unjudged": {"note": "名单固定 20 人；名单外人类实体无法核验在场性，按判据卡 §2.2 不入分母"},
        "samples": hits,
    }


def layer_l2(facts: Facts, cn2id: Dict[str, str], id2cn: Dict[str, str]) -> dict:
    names_sorted = sorted(cn2id.keys(), key=len, reverse=True)
    place_alt = "|".join(re.escape(x) for x in names_sorted)
    self_loc_re = re.compile(SELF_LOC_HEAD + r"(" + place_alt + r")")
    claim_re = re.compile(r"在(" + place_alt + r")")

    denom = 0
    hits: List[dict] = []
    buckets: Counter = Counter()
    src_counter: Counter = Counter()
    for m in facts.msgs:
        text = PAREN_NARRATION_RE.sub("", m["body"])
        claims = _claims(text, self_loc_re, claim_re, buckets)
        if not claims:
            continue
        fact, src = facts.fact(m)
        if fact is None:
            buckets["no_log_location_fact"] += 1
            continue
        denom += 1
        src_counter[src] += 1
        contradicted = sorted({cn2id[c] for c in claims if cn2id[c] != fact})
        if contradicted:
            scene = m.get("fact_ctx_scene_place")
            hits.append({
                "layer": "L2", "seq": m["seq"], "round": m["round"], "channel": m["event_type"],
                "from": m["from"], "to": m["to"],
                "claimed_places": claims,
                "claimed_place_ids": sorted({cn2id[c] for c in claims}),
                "fact_place": fact, "fact_place_cn": id2cn.get(fact, fact),
                "fact_source": src,
                FACT_SCENE: scene,
                "ctx_scene_matches_claim": (scene is not None and cn2id.get(claims[0]) == scene),
                "contradicted_place_ids": contradicted,
                "body_excerpt": m["body"][:SAMPLE_EXCERPT_CHARS],
            })
    explained = sum(1 for h in hits if h["ctx_scene_matches_claim"])
    return {
        "id": "L2_location_claim_conflict",
        "question": "消息里显式的「我此刻在<场所>」是否与日志记录的在场事实矛盾？",
        "decidable": True,
        "fact_base": "payload.place（缺失时回落 PLACE_ARRIVED/PLACE_MOVE 链的 point-in-time 位置）",
        "denominator_definition": "含 ≥1 条非时间偏移/非完成体的显式自我在场断言、且日志在场事实可查的消息数（per-message）",
        "denominator": denom,
        "numerator": len(hits),
        "rate": (len(hits) / denom) if denom else None,
        "fact_source_counts": dict(sorted(src_counter.items())),
        "unjudged": dict(sorted(buckets.items())),
        "ctx_scene_explains_hits": {
            "hits": len(hits),
            "hits_where_ctx_scene_equals_claim": explained,
            "note": ("若命中能被 ctx.scene.place 解释，则矛盾源头是『引擎注入给模型的场景与真实位置不符』，"
                     "而不是模型凭空编造；此时不得把命中读成模型的 F-7 编造。"),
        },
        "samples": hits,
    }


def layer_l3(facts: Facts) -> dict:
    denom = 0
    hits: List[dict] = []
    for m in facts.msgs:
        text = PAREN_NARRATION_RE.sub("", m["body"])
        mt = PREHISTORY_RE.search(text)
        if not mt:
            continue
        denom += 1
        if facts.day_at(m["seq"]) == 0:
            hits.append({
                "layer": "L3", "seq": m["seq"], "round": m["round"], "channel": m["event_type"],
                "from": m["from"], "to": m["to"], "day": 0, "token": mt.group(0),
                "body_excerpt": m["body"][:SAMPLE_EXCERPT_CHARS],
            })
    return {
        "id": "L3_prehistory_reference",
        "question": "世界第 0 天就引用「昨天/昨晚」——是角色前史还是编造不存在的过往？",
        "decidable": False,
        "why_not_decidable": "日志不含世界开始前的历史；规则无法区分『persona 前史（合法）』与『编造』，需 judge/人判",
        "denominator_definition": "正文出现 昨天/昨晚/昨儿/前天/前日 的消息数（per-message）",
        "denominator": denom,
        "numerator": None,
        "rate": None,
        "candidates_day0": len(hits),
        "samples": hits,
    }


def layer_l4() -> dict:
    return {
        "id": "L4_semantic_fabrication",
        "question": "这条消息所陈述的事件，日志里发生过吗？（R4:43 的 F-7 原义）",
        "decidable": False,
        "why_not_decidable": (
            "仓内不存在 F-7 编造判定的规则或 judge：run.jsonl 的 LLM_JUDGMENT 仅覆盖 "
            "weekly_focus/stance/affection/rel_affinity/respect 5 个维度（见 llm-cost 的 "
            "llm_judgment_by_dimension），无 fabrication 维度；新增 judge 维度需改 code/（本轮冻结区），"
            "故本轮不实现、不猜测。"
        ),
        "caliber_landing_points": {
            "definition": "reports/R4-life-texture.md:43（率 = 编造条数 / 受检条数，单位 per-message）",
            "mention_proxy": "v2/refs/F7-offscreen-criteria.md（P1 提及层，代理口径，不等于编造）",
            "rule_precedent": "code/devtools/storyteller.py::qc_story Q-6（『句中数字须逐字来自 payload』）",
            "judge_hook_needed": "LLM_JUDGMENT.dimension='fabrication' + 事件摘要上下文 + prompt_hash（未实现，属 code/ 冻结区）",
        },
        "denominator": None,
        "numerator": None,
        "rate": None,
        "samples": [],
    }


# ---------------------------------------------------------------- 主流程


def build_report(log: str, batch_id: Optional[str], personas: str, places: str) -> dict:
    names, pinfo = load_personas(personas)
    cn2id, id2cn, plinfo = load_places(places)
    if not pinfo["exists"] or not names:
        raise SystemExit("personas 不可用（缺失或空名单）: " + personas)
    if not plinfo["exists"] or not cn2id:
        raise SystemExit("places 不可用（缺失或空表）: " + places)
    if not os.path.exists(log):
        raise SystemExit("log 不存在: " + log)

    recs = read_records(log)
    facts = Facts(recs)
    if not facts.msgs:
        raise SystemExit("日志内无消息事件（MSG_DM/MSG_PUBLIC/MSG_GROUP）: " + log)

    n_msg = len(facts.msgs)
    agree = dis = miss = 0
    scene_present = scene_dis = 0
    for m in facts.msgs:
        pp = m["fact_payload_place"]
        pc = facts.fact_chain(m["seq"], m["from"])
        if pp is None or pc is None:
            miss += 1
        elif str(pp) == pc:
            agree += 1
        else:
            dis += 1
        sc = m["fact_ctx_scene_place"]
        if sc is not None:
            scene_present += 1
            if pp is not None and str(sc) != str(pp):
                scene_dis += 1

    layers = [layer_l1(facts, names), layer_l2(facts, cn2id, id2cn),
              layer_l3(facts), layer_l4()]

    return {
        "schema": SCHEMA_VERSION,
        "caliber_version": CALIBER_VERSION,
        "metric": "F-7 越界编造率（规则可判档 only；R4 原义语义级编造仍不可判，见 L4）",
        "batch_id": batch_id,
        "statistical_unit": "per-message（一条 MSG_DM/MSG_PUBLIC/MSG_GROUP 记 1；与 R4:43 一致）",
        "inputs": {
            "log_path": log,
            "log_sha256": sha256_file(log),
            "log_bytes": os.path.getsize(log),
            "personas": pinfo,
            "places": plinfo,
            "script_sha256": sha256_file(os.path.abspath(__file__)),
        },
        "units": {
            "messages_total": n_msg,
            "by_channel": dict(sorted(Counter(m["event_type"] for m in facts.msgs).items())),
            "days_covered": sorted({d for _, d in facts.day_marks}),
            "agents_with_place_events": len(facts.place_chain),
        },
        "log_fact_self_consistency": {
            "payload_place_vs_place_chain": {
                "agree": agree, "disagree": dis, "missing_one_side": miss,
                "messages_total": n_msg,
                "interpretation": "payload.place 与位置链 point-in-time 位置的一致性（实测两臂均为 167/167 一致、0 矛盾 ⇒ 可当同一事实用）",
            },
            "ctx_scene_place_vs_payload_place": {
                "ctx_scene_present": scene_present,
                "disagree": scene_dis,
                "disagree_rate_among_present": (scene_dis / scene_present) if scene_present else None,
                "interpretation": ("ctx.scene.place 是 scene_anchor 注入给模型的场景块，**不是事实**；"
                                   "它与 payload.place 的差异度量『注入场景是否过期/错位』"),
            },
        },
        "layers": layers,
        "summary": {
            "rule_decidable_layers": ["L1_fabricated_entity", "L2_location_claim_conflict"],
            "per_layer_rate": {l["id"]: l["rate"] for l in layers if l["decidable"]},
            "note_no_summing": "各层分母定义不同，禁止相加或求平均",
            "unjudged_layers": ["L3_prehistory_reference", "L4_semantic_fabrication"],
            "f7_rate_headline": None,
            "f7_rate_headline_reason": (
                "R4 原义（语义级编造）无规则/judge 实现 ⇒ 本轮不给单一 F-7 率；只按层给可判读数。"
                "禁止把 L1/L2 任一层读成『越界编造率』。"
            ),
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="F-7 越界编造率 · 规则可判档只读出数器（零 LLM，确定性输出）")
    ap.add_argument("--log", required=True, help="run.jsonl 路径（只读）")
    ap.add_argument("--out", required=True, help="输出 JSON 路径")
    ap.add_argument("--batch-id", default=None, help="批次标签（写进 JSON 便于多批并列）")
    ap.add_argument("--personas", default=os.path.join("code", "config", "personas.json"))
    ap.add_argument("--places", default=os.path.join("code", "config", "places.json"))
    ap.add_argument("--timestamp", action="store_true",
                    help="在 JSON 写 generated_at（默认不写，保证逐字节可复现）")
    args = ap.parse_args(argv)

    rep = build_report(args.log, args.batch_id, args.personas, args.places)
    if args.timestamp:
        import datetime
        rep["generated_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(rep, ensure_ascii=False, sort_keys=True, indent=2))
        f.write("\n")

    l1, l2 = rep["layers"][0], rep["layers"][1]
    c = rep["log_fact_self_consistency"]
    print(f"[f7-fabrication] batch={args.batch_id} msgs={rep['units']['messages_total']} "
          f"L1={l1['numerator']}/{l1['denominator']} L2={l2['numerator']}/{l2['denominator']} "
          f"pp_vs_chain={c['payload_place_vs_place_chain']['agree']}agree/"
          f"{c['payload_place_vs_place_chain']['disagree']}dis "
          f"scene_present={c['ctx_scene_place_vs_payload_place']['ctx_scene_present']} "
          f"scene_dis={c['ctx_scene_place_vs_payload_place']['disagree']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
