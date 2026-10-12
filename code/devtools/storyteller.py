#!/usr/bin/env python3
"""storyteller.py — 故事叙述机（最小端到端，T249）。

从**一份真实日志**长出一篇**可读故事**，并**真跑三条硬门**（不是写在文档里）：
  - **Q-1 锚点覆盖 = 1.0**：每个情节句都锚到真实 `event_seq`；
  - **Q-6 硬事实零违规**：句中的数字（人/事/金额/关系值）**逐字来自日志 payload**；
  - **Q-8 来源诚实**：`directed`（世界导演）/`induced`（观察者注入）**不得被说成自发**。

## 设计（对应 `v2/refs/story-and-event-engine.md` 五段管线）
  选角(cast) → 冲突识别(conflict) → 节拍(setup/escalation/turn/resolution/aftermath) → 成文 → 质检
  最小实现：**成文用确定性模板**（LLM 只产"表达"不产"事实"——本工具**不调用 LLM**，故零编造、
  完全可复算：同一日志两次输出**逐字节一致**）。若日后接 LLM 成文，**必须过同一套 QC**（本文件即判据来源）。

## 铁律
- **只读**：经 `obs.reader.ReadOnlyLog` 读取，构造即校验哈希链；**不写世界、无任何写事件**。
- **口径复用**：时间用 `engine.time.derive_time`；戏剧权重用 `config/narrative_weights.json`（`narrative.weights`）。
- **事实唯一来源 = 日志**：模板只引用 payload 字段；人名取自 `config/personas.json` 的 display_name（冻结映射）。
- **不造结局 / 不改分支**：只叙述**已发生**的事；没锚到的事件**不写**（宁少而真）。

## 用法
    cd code
    python devtools/storyteller.py --log /root/t249_dir/run.jsonl --out /tmp/story_out

产物（写入 --out）：
    story.md           可读故事（每句带 [seq] 锚点；directed/induced 句带来源标记）
    story.qc.json      QC：anchor_coverage / hard_fact_violations / origin_mislabel / 统计
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]           # -> code/
sys.path.insert(0, str(CODE_DIR))

from obs.reader import ReadOnlyLog                        # noqa: E402
from engine.time import derive_time                      # noqa: E402

# --------------------------------------------------------------------------- #
# 配置：人名映射 / 戏剧权重
# --------------------------------------------------------------------------- #
def load_personas(path: Path | None) -> dict[str, str]:
    """persona_id -> display_name（冻结映射；缺失则回退 id 本身）。"""
    out: dict[str, str] = {}
    if path and Path(path).exists():
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        arr = d.get("personas") if isinstance(d, dict) else d
        for p in arr or []:
            pid = p.get("persona_id") or p.get("id")
            if pid:
                out[str(pid)] = str(p.get("display_name") or pid)
    return out


def load_drama_weights() -> dict:
    """戏剧性子维权重（复用叙事层 config；缺失则用内置默认，仍确定性）。"""
    default = {"c_conflict": 0.16, "c_turn": 0.14, "c_contrast": 0.12, "c_plunge": 0.13,
               "c_wbdiv": 0.10, "c_ruin": 0.14, "c_ally": 0.10, "c_rarity": 0.06, "c_impact": 0.05}
    th = {"theta_plunge": 0.25, "theta_drama": 0.35}
    try:
        sys.path.insert(0, str(CODE_DIR))
        from narrative.weights import load_narrative_weights, THRESHOLD_KEYS
        cfg = load_narrative_weights()
        return {"weights": dict(cfg.get("weights") or default),
                "thresholds": dict(cfg.get("thresholds") or th)}
    except Exception:
        return {"weights": default, "thresholds": th}


# --------------------------------------------------------------------------- #
# 读日志 / 时间
# --------------------------------------------------------------------------- #
def load_records(path: Path) -> list[dict]:
    recs = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    recs.sort(key=lambda r: r.get("seq", 0))
    return recs


# 叙述白名单：只把这些类型讲进故事（其余是噪声/内部事件）
NARRATED = {
    "AGENT_BORN", "ROLE_CHANGE", "GOAL_SET", "GOAL_ACHIEVED", "GOAL_ABANDON",
    "SKILL_LEVEL_UP", "SKILL_OUTPUT",
    "TRANSFER", "MARKET_TRADE",
    "RELATION_CHANGE", "RELATION_ENCOUNTER",
    "CONFLICT_STARTED", "CONFLICT_RESOLVED",
    "NORM_PROPOSED", "NORM_ADOPTED", "NORM_VIOLATED",
    "OFFER_CREATED", "OFFER_ACCEPTED", "OFFER_REJECTED", "OFFER_COUNTERED",
    "MSG_PUBLIC", "MSG_DM", "MSG_GROUP",
    "AGENT_DIED", "AGENT_REVIVED", "STATE_CHANGE",
    "SEED_EVENT", "WORLD_DIRECTIVE", "WORLD_GROUP_EVENT",
}

# 来源：directed（世界导演） > induced（观察者注入） > spontaneous
DIRECTED_TYPES = {"WORLD_DIRECTIVE", "WORLD_GROUP_EVENT"}
INDUCED_TYPES = {"SEED_EVENT"}

ORIGIN_MARK = {"directed": "【世界导演】", "induced": "【观察者注入】"}

# kind（原子种类）——用于节拍
KIND_CAST = {"AGENT_BORN", "ROLE_CHANGE"}
KIND_MOTIVE = {"GOAL_SET", "GOAL_ABANDON"}          # inferred=True（动机线索，必须加推测语）
KIND_REL = {"RELATION_CHANGE", "RELATION_ENCOUNTER", "OFFER_REJECTED"}
KIND_OUTCOME = {"SKILL_LEVEL_UP", "SKILL_OUTPUT", "GOAL_ACHIEVED", "NORM_ADOPTED",
                "NORM_VIOLATED", "CONFLICT_RESOLVED", "AGENT_DIED", "AGENT_REVIVED",
                "STATE_CHANGE"}
KIND_INTERVENTION = DIRECTED_TYPES | INDUCED_TYPES

# 节拍归属（setup/escalation/turn/resolution/aftermath）
BEAT_OF = {
    "AGENT_BORN": "setup", "ROLE_CHANGE": "aftermath", "GOAL_SET": "setup",
    "SKILL_LEVEL_UP": "escalation", "SKILL_OUTPUT": "escalation",
    "TRANSFER": "escalation", "MARKET_TRADE": "escalation",
    "MSG_PUBLIC": "escalation", "MSG_DM": "escalation", "MSG_GROUP": "escalation",
    "RELATION_ENCOUNTER": "escalation", "RELATION_CHANGE": "escalation",
    "OFFER_CREATED": "escalation", "OFFER_COUNTERED": "escalation", "OFFER_ACCEPTED": "resolution",
    "OFFER_REJECTED": "turn", "CONFLICT_STARTED": "turn",
    "CONFLICT_RESOLVED": "resolution", "AGENT_DIED": "turn", "AGENT_REVIVED": "resolution",
    "NORM_PROPOSED": "escalation", "NORM_ADOPTED": "resolution", "NORM_VIOLATED": "turn",
    "GOAL_ACHIEVED": "resolution", "GOAL_ABANDON": "turn", "STATE_CHANGE": "turn",
    "SEED_EVENT": "setup", "WORLD_DIRECTIVE": "setup", "WORLD_GROUP_EVENT": "setup",
}
BEAT_CN = {"setup": "起", "escalation": "承", "turn": "转", "resolution": "合", "aftermath": "余波"}


def _q(s: str, n: int = 42) -> str:
    """安全引用日志正文（逐字）；过长截断并标注。"""
    s = str(s or "").replace("\n", " ").strip()
    return (s[:n] + "…") if len(s) > n else s


def _fmt(v) -> str:
    return str(v)


def _actor(p: dict):
    """消息/事件的发言人兜底（不同事件字段名不一）。"""
    return p.get("from") or p.get("author") or p.get("agent_id") or p.get("observer")


def render_fact(t: str, p: dict, nm) -> tuple[str, list[str], bool] | None:
    """把一条事件渲染成事实句。返回 (fact, cast_ids, inferred) 或 None（跳过）。

    ★ 纪律：fact 中的**每个数字**都必须来自 payload；人名由 id 经冻结映射得到。
    """
    g = p.get
    if t == "AGENT_BORN":
        a = g("agent_id") or g("actor");  return (f"{nm(a)} 来到青溪镇。", [a], False)
    if t == "ROLE_CHANGE":
        a = g("agent_id")
        fr = g("from_role", g("from")); to = g("to_role", g("to"))
        if fr is None and to is None:
            return None
        return (f"{nm(a)} 的身份由「{fr}」转为「{to}」。", [a], False)
    if t == "GOAL_SET":
        a = g("agent_id"); return (f"{nm(a)} 似乎立下了一个目标（{g('kind')}）。", [a], True)
    if t == "GOAL_ABANDON":
        a = g("agent_id"); return (f"{nm(a)} 似乎放弃了先前的目标（{g('reason')}）。", [a], True)
    if t == "GOAL_ACHIEVED":
        a = g("agent_id"); return (f"{nm(a)} 达成了目标。", [a], False)
    if t == "SKILL_LEVEL_UP":
        a = g("agent_id")
        return (f"{nm(a)} 的 {g('skill_id')} 从 {g('level_before')} 级升到 {g('level_after')} 级。", [a], False)
    if t == "SKILL_OUTPUT":
        a = g("agent_id"); return (f"{nm(a)} 产出了 {g('skill_id')} 作品（quality={g('quality')}）。", [a], False)
    if t == "TRANSFER":
        f_, to, amt = g("from"), g("to"), g("amount")
        return (f"{nm(f_)} 给了 {nm(to)} {amt} 枚钱（{g('reason')}）。", [f_, to], False)
    if t == "MARKET_TRADE":
        a = _actor(p)
        good = g("good") or g("item") or g("commodity") or ""
        qty = g("qty")
        tail = f"{qty} 单位 {good}".strip() if qty is not None else str(good or "")
        return (f"{nm(a)} 在市集完成了一笔交易（{tail}）。", [a], False)
    if t == "RELATION_CHANGE":
        f_, to, dim = g("from"), g("to"), g("dim")
        return (f"{nm(f_)} 对 {nm(to)} 的{dim}，由 {g('before')} 变成 {g('after')}。", [f_, to], False)
    if t == "RELATION_ENCOUNTER":
        a, b = g("a"), g("b")
        return (f"{nm(a)} 与 {nm(b)} 在{g('place')}相遇。", [a, b], False)
    if t == "CONFLICT_STARTED":
        pt = g("parties") or []
        names = "、".join(nm(x) for x in pt[:3])
        return (f"{names} 之间起了冲突（争夺：{g('stakes')}）。", list(pt), False)
    if t == "CONFLICT_RESOLVED":
        w = g("winner")
        return (f"冲突落幕，{nm(w)} 占了上风。", [w], False)
    if t == "NORM_PROPOSED":
        a = g("proposer"); return (f"{nm(a)} 提出了规范「{g('rule_ref')}」。", [a], False)
    if t == "NORM_ADOPTED":
        ad = g("adopters") or []
        return (f"规范「{g('rule_ref') or g('norm_id')}」获得采纳（{len(ad)} 人附议）。", list(ad), False)
    if t == "NORM_VIOLATED":
        a = g("violator"); return (f"{nm(a)} 违反了规范「{g('norm_id')}」。", [a], False)
    if t == "OFFER_CREATED":
        f_ = g("from")
        to = g("to")
        if isinstance(to, (list, tuple)):
            to0 = to[0] if to else None
        else:
            to0 = to
        return (f"{nm(f_)} 向 {nm(to0) if to0 else '对方'} 发起协商（{g('kind')}）。", [f_, to0], False)
    if t == "OFFER_ACCEPTED":
        a = g("by"); return (f"协商达成，{nm(a)} 接受了条件。", [a], False)
    if t == "OFFER_REJECTED":
        a = g("by"); return (f"{nm(a)} 婉拒了这次协商（{g('reason')}）。", [a], False)
    if t == "OFFER_COUNTERED":
        a = g("by"); return (f"{nm(a)} 还了价（第 {g('round_no')} 轮）。", [a], False)
    if t == "MSG_PUBLIC":
        a = _actor(p); return (f"{nm(a)} 公开说：「{_q(g('body'))}」。", [a], False)
    if t == "MSG_DM":
        a, to = _actor(p), g("to")
        return (f"{nm(a)} 私下对 {nm(to)} 说：「{_q(g('body'))}」。", [a, to], False)
    if t == "MSG_GROUP":
        a = _actor(p); return (f"{nm(a)} 在群里说：「{_q(g('body'))}」。", [a], False)
    if t == "AGENT_DIED":
        a = g("agent_id"); return (f"{nm(a)} 离世了（{g('cause')}）。", [a], False)
    if t == "AGENT_REVIVED":
        a = g("agent_id"); return (f"{nm(a)} 复活了（代价 {g('fee')} 枚钱）。", [a], False)
    if t == "STATE_CHANGE":
        a = g("agent_id"); return (f"{nm(a)} 的状态变为「{g('to') or g('state')}」。", [a], False)
    if t == "WORLD_DIRECTIVE":
        return (f"世界导演下达指令（{g('kind')}，剂量曲线 {g('dose_curve')}）：为小镇带来一场{g('kind')}。", [], False)
    if t == "WORLD_GROUP_EVENT":
        return (f"世界导演引发一场群体事件（{g('kind')}）。", [], False)
    if t == "SEED_EVENT":
        return (f"观察者注入了一个种子事件（{g('kind')}）。", [], False)
    return None


def extract_atoms(records, nm) -> list[dict]:
    tcache: dict[int, dict] = {}
    REL_MIN_DELTA = 10          # 降噪：只叙述关系"显著"变化（|after-before|≥10）

    def tinfo(round_no: int) -> dict:
        if round_no not in tcache:
            tcache[round_no] = derive_time(int(round_no), None)
        return tcache[round_no]

    atoms = []
    for r in records:
        t = r["type"]
        if t not in NARRATED:
            continue
        p = r.get("payload") or {}
        if t == "RELATION_CHANGE":
            try:
                if abs(float(p.get("after") or 0) - float(p.get("before") or 0)) < REL_MIN_DELTA:
                    continue
            except Exception:
                pass
        try:
            rf = render_fact(t, p, nm)
        except Exception:
            rf = None
        if not rf:
            continue
        fact, cast, inferred = rf
        ti = tinfo(int(r["round"]))
        origin = "directed" if t in DIRECTED_TYPES else ("induced" if t in INDUCED_TYPES else "spontaneous")
        atoms.append({
            "seq": int(r["seq"]), "type": t, "round": int(r["round"]), "week": ti["week"],
            "day": ti["day_of_week"], "slot": ti["slot"], "beat": BEAT_OF.get(t, "escalation"),
            "kind": ("CAST" if t in KIND_CAST else "MOTIVE_HINT" if t in KIND_MOTIVE else
                     "REL_DELTA" if t in KIND_REL else "INTERVENTION" if t in KIND_INTERVENTION else
                     "OUTCOME" if t in KIND_OUTCOME else "ACTION"),
            "cast": [c for c in cast if c], "origin": origin, "inferred": bool(inferred),
            "fact": fact, "payload": p,
        })
    atoms.sort(key=lambda a: a["seq"])
    return atoms


# --------------------------------------------------------------------------- #
# 戏剧性打分（确定性；复用 narrative_weights 权重，仅实现可算子维）
# --------------------------------------------------------------------------- #
def score_week(atoms: list[dict], W: dict, TH: dict) -> float:
    w = W["weights"]
    th_plunge = float(TH.get("theta_plunge", 0.25))
    n_conf = sum(1 for a in atoms if a["type"] in ("CONFLICT_STARTED",))
    n_ruin = sum(1 for a in atoms if a["type"] in ("AGENT_DIED", "AGENT_REVIVED"))
    n_plunge = 0
    for a in atoms:
        if a["type"] == "RELATION_CHANGE":
            b, af = a["payload"].get("before"), a["payload"].get("after")
            try:
                if b is not None and af is not None and abs(float(af) - float(b)) >= 50 * th_plunge:
                    n_plunge += 1
            except Exception:
                pass
    n_ally = sum(1 for a in atoms if a["type"] == "TRANSFER")
    c_conflict = min(1.0, n_conf / 3.0)
    c_ruin = min(1.0, n_ruin / 2.0)
    c_plunge = min(1.0, n_plunge / 3.0)
    c_ally = min(1.0, n_ally / 3.0)
    c_impact = min(1.0, len({c for a in atoms for c in a["cast"]}) / 6.0)
    return round(
        w.get("c_conflict", 0) * c_conflict + w.get("c_ruin", 0) * c_ruin +
        w.get("c_plunge", 0) * c_plunge + w.get("c_ally", 0) * c_ally +
        w.get("c_impact", 0) * c_impact, 6)


# --------------------------------------------------------------------------- #
# 质检：Q-1 / Q-6 / Q-8
# --------------------------------------------------------------------------- #
def _flatten_numbers(payload) -> set[str]:
    out: set[str] = set()
    stack = [payload]
    while stack:
        v = stack.pop()
        if isinstance(v, dict):
            stack.extend(v.values())
        elif isinstance(v, (list, tuple)):
            stack.extend(v)
        elif isinstance(v, bool):
            continue
        elif isinstance(v, (int, float)):
            out.add(str(v))
            if isinstance(v, float) and float(v).is_integer():
                out.add(str(int(v)))
        elif isinstance(v, str):
            out.update(re.findall(r"-?\d+", v))
    return out


def qc_story(sentences: list[dict]) -> dict:
    """sentences: [{text, seq, origin, inferred, payload}]。"""
    n = len(sentences)
    anchored = sum(1 for s in sentences if s.get("seq") is not None)
    hard_viol = 0
    viol_examples = []
    origin_mislabel = 0
    mis_examples = []
    for s in sentences:
        # Q-1：必须有锚点
        if s.get("seq") is None:
            hard_viol += 0
        # Q-6：句中每个数字都要在 payload 里
        nums = re.findall(r"-?\d+", s["text"])
        pool = _flatten_numbers(s.get("payload") or {})
        for x in nums:
            if x not in pool:
                hard_viol += 1
                if len(viol_examples) < 5:
                    viol_examples.append({"seq": s["seq"], "num": x, "text": s["text"][:60]})
        # Q-8：directed/induced 必须有来源标记；反之不得误标
        has_mark = ("【世界导演】" in s["text"]) or ("【观察者注入】" in s["text"])
        need_mark = s.get("origin") in ("directed", "induced")
        if need_mark != has_mark:
            origin_mislabel += 1
            if len(mis_examples) < 5:
                mis_examples.append({"seq": s["seq"], "origin": s.get("origin"),
                                     "marked": has_mark, "text": s["text"][:60]})
    return {
        "n_sentences": n,
        "anchor_coverage": round(anchored / n, 6) if n else 0.0,   # Q-1 目标 = 1.0
        "unanchored": n - anchored,
        "hard_fact_violations": hard_viol,                          # Q-6 目标 = 0
        "hard_fact_violation_examples": viol_examples,
        "origin_mislabel": origin_mislabel,                         # Q-8 目标 = 0
        "origin_mislabel_examples": mis_examples,
        "hard_gate_pass": (anchored == n and hard_viol == 0 and origin_mislabel == 0),
    }


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #
def build_story(atoms, *, k_weeks: int, max_sentences: int) -> tuple[str, list[dict], dict]:
    W = load_drama_weights()
    by_week: dict[int, list[dict]] = collections.OrderedDict()
    for a in atoms:
        by_week.setdefault(a["week"], []).append(a)
    scored = [(wk, score_week(ats, W, W["thresholds"]), ats) for wk, ats in by_week.items()]
    scored.sort(key=lambda x: (-x[1], x[0]))                     # 全序 tie-break
    chosen = sorted(scored[:k_weeks], key=lambda x: x[0])
    week_scores = {wk: sc for wk, sc, _ in scored}

    sentences: list[dict] = []
    lines: list[str] = []
    for wk, sc, ats in chosen:
        lines.append(f"\n## 第 {wk + 1} 周　（叙事价值 NV={sc}）\n")
        cur_beat = None
        for a in ats:
            if len(sentences) >= max_sentences:
                break
            if a["beat"] != cur_beat:
                cur_beat = a["beat"]
                lines.append(f"\n**{BEAT_CN.get(cur_beat, cur_beat)}** ——")
            mark = ORIGIN_MARK.get(a["origin"], "")
            hedge = "（推测）" if a["inferred"] else ""
            text = f"{mark}{a['fact']}{hedge}"
            line = f"- {text}　`[{a['seq']}]`"
            lines.append(line)
            sentences.append({"text": text, "seq": a["seq"], "origin": a["origin"],
                              "inferred": a["inferred"], "payload": a["payload"]})
    return "\n".join(lines) + "\n", sentences, week_scores


def main() -> int:
    ap = argparse.ArgumentParser(description="故事叙述机（最小端到端）：真实日志 → 可读故事 + 三硬门 QC")
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--personas", default=str(CODE_DIR / "config" / "personas.json"))
    ap.add_argument("--weeks", type=int, default=2, help="选用 NV 最高的前 K 周")
    ap.add_argument("--max-sentences", type=int, default=120)
    ap.add_argument("--no-verify", action="store_true", help="跳过哈希链校验（仅派生日志）")
    ap.add_argument("--selftest", action="store_true",
                    help="自检：证明 QC 真会抓『编造数字』(Q-6) 与『把 directed 说成自发』(Q-8)")
    args = ap.parse_args()

    if args.selftest:
        demo = [
            {"text": "老周 给了 老石 999 枚钱。", "seq": 1, "origin": "spontaneous",
             "inferred": False, "payload": {"amount": 100}},          # 999 不在 payload → Q-6 违规
            {"text": "有人自发办了一场节庆。", "seq": 2, "origin": "directed",
             "inferred": False, "payload": {}},                          # directed 未标来源 → Q-8 违规
        ]
        q = qc_story(demo)
        ok = (q["hard_fact_violations"] >= 1 and q["origin_mislabel"] >= 1)
        print(f"selftest: Q-6 检出编造数字={q['hard_fact_violations']}（期望≥1）"
              f"  Q-8 检出误标={q['origin_mislabel']}（期望≥1）  => {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1

    log_path = Path(args.log).expanduser().resolve()
    records = load_records(log_path)
    log = ReadOnlyLog(records, verify=not args.no_verify)
    if not args.no_verify:
        log.require_chain()

    nm_map = load_personas(Path(args.personas) if args.personas else None)

    def nm(a):
        if a is None:
            return "某人"
        return nm_map.get(str(a), str(a))

    atoms = extract_atoms(records, nm)
    story_body, sentences, week_scores = build_story(atoms, k_weeks=args.weeks,
                                                     max_sentences=args.max_sentences)
    qc = qc_story(sentences)

    meta = {
        "source_log": str(log_path), "log_hash": log.log_hash(), "seed": log.seed(),
        "max_round": log.max_round(), "chain_ok": log.chain_ok,
        "n_events": len(records), "n_atoms": len(atoms),
        "narrated_types": sorted({a["type"] for a in atoms}),
        "by_origin": dict(collections.Counter(a["origin"] for a in atoms)),
        "week_scores": week_scores,
        "note": "只读派生；成文=确定性模板（无 LLM 调用）；事实唯一来源=日志 payload；"
                "人名=personas 冻结映射。接 LLM 成文须过同一 QC。",
    }
    header = (f"# 青溪镇 · 故事（故事叙述机 P0）\n\n"
              f"> 来源：`{meta['source_log']}`　log_hash=`{meta['log_hash'][:24]}…`\n"
              f"> seed={meta['seed']}　max_round={meta['max_round']}　chain_ok={meta['chain_ok']}　"
              f"事件={meta['n_events']}　原子={meta['n_atoms']}\n"
              f"> **三硬门**：Q-1 锚点覆盖={qc['anchor_coverage']}（目标 1.0）· "
              f"Q-6 硬事实违规={qc['hard_fact_violations']}（目标 0）· "
              f"Q-8 来源误标={qc['origin_mislabel']}（目标 0）· 硬门通过={qc['hard_gate_pass']}\n")
    story = header + story_body

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "story.md").write_text(story, encoding="utf-8")
    (out / "story.qc.json").write_text(
        json.dumps({"meta": meta, "qc": qc}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"story -> {out/'story.md'}")
    print(f"  atoms={meta['n_atoms']} sentences={qc['n_sentences']} weeks={sorted(week_scores)}")
    print(f"  Q-1 anchor_coverage={qc['anchor_coverage']}  Q-6 hard_fact_violations={qc['hard_fact_violations']}"
          f"  Q-8 origin_mislabel={qc['origin_mislabel']}  hard_gate_pass={qc['hard_gate_pass']}")
    print(f"  by_origin={meta['by_origin']}")
    return 0 if qc["hard_gate_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
