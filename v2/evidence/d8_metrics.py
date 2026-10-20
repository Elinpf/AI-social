#!/usr/bin/env python3
"""D8 A/B 读数脚本 —— 「世界事件四层传导链」四档 + M-0 双轨去重 + M-1 词表代理。

判据来源（必须与之一致，不得临场改判）：
  - `v2/evidence/D8-mention-criteria-card.md`（repo-scout，sha256 前16 见 --card 输出）
  - leader 追加裁决：事件实体单位 = 唯一 `directive_id`（`D-` 与 `GE-` 成对算 1 条）；
    分子/分母双轨（列A 原始条数 / 列B 去重命中事件数），两列不许合并。

用法：
  python3 v2/evidence/d8_metrics.py --log <run.jsonl> --label A0 [--out-json x.json]

剂量期望（勿再犯错，写死在此）：
  aggressive 曲线 ×2 折算后 = {festival 200, edict 100, tension 160, visitor 80,
  supply_shock 80, disaster 20, epidemic 20, public_works 60} bp，合计 720bp = 7.2%/回合。
  ⇒ 84 回合 λ = 6.048（mock 实测 6 条，P(X=6|λ=6.048)=16.1%，属期望内正常结果）；
    12 回合 λ = 0.864，P(≥1) = 57.9%。
  ⚠ 曾出现的错误值「3.6%/回合、期望 3.0、12 回合 P(≥1)=13%」是把 conservative 的
    1.8% 又乘一次 2（跨行套用曲线）得来的，**不得在任何文档中复现**。

三套口径（R8-2，不得互相代入）：
  - M-0   entity 口径 (agent, directive_id)：分母 = n_alive × N_world = 4×6 = 24，**上界 1.0**
  - M-0_w triple 口径 (agent, directive, round)：分母 = 4×6×6 = 144，上界 0.5
  - 感知覆盖率：感知窗 3 回合 / directive 有效期 slots=6 ⇒ 50%（回合口径，非效果上界）
  ⚠ 「12/24 = 0.5」是单位混用（12 = agent-round，24 = agent-directive），**不可作 M-0 上界**。

口径（写死，不许事后挑）：
  ① N_world = |{unique directive_id}|（成对折叠；缺失时回退 directive_ref）
  ② M-0 分母 = 存活 agent 数 × N_world；per-(agent, directive_id) 去重
  ③ M-1 分母 = 窗口内全部 MSG_DM/MSG_PUBLIC/MSG_GROUP 条数（per-message）
  ④ 窗口 = [start_round|effective_from_round, end_round|expires_round)（与 engine/world_params.py 同一 fallback 链）
  ⑤ M-1 词表命中前先剔除括号内旁白（G-1 教训）；括号内命中一律不算
  ⑥ R2 唯一归属：同一条消息命中多个 directive 窗口时，只归入 issued_round 最早的那个
  ⑦ 零的性质：结构性 / 未观测到 / 仅窗口外 —— 三列分列，不许合并成一个 0

来源标签：本脚本所有数字均为 [真跑]（输入是真跑日志）；M-0_windowed 相关字段为 [后处理推演]。

修订 R9（2026-10-21，metrics-dev｜任务 t7-m1fix）：修 M-1 两个已定位缺陷，**两列并存、不许合并**
  D1 窗口归属错（原 `window_hit_msgs()` 内 `break`，即上面口径 ⑥ 的实现）：
     一条 msg 只归入 issued_round **最早**的覆盖窗口 ⇒ 后发事件的窗口被先发事件抢走。
     本批实例：visitor `[12,18)` 覆盖 edict `[14,20)` 的 r15/r16，三条 edict 措辞消息被归给 visitor。
     改法：新增 `m1_scan(attribution)`；`all`（默认）把 msg 归入**全部**覆盖窗口、任一覆盖实体 kind 命中即算，
           `first` 保留原样口径供对照。被删掉的正是 `window_hit_msgs()` 里那行 `break`。
  D2 词表缺 visitor（`KIND_WORDS` 只有 tension/edict/festival）：被错归的消息再查 visitor 词表必空 ⇒ 双重归零。
     改法：**不擅自新造 visitor 词表**（无可靠未登录词依据，且判据卡要求改词表必须换 sha 重跑）；
           改为显式声明 + 量化：`layer4_M1_lexicon_coverage` 列出 `kinds_without_lexicon` 与
           `msgs_visitor_only`，并在 `layer4_M1_fixed.tag` 写明「visitor 词表未覆盖 ⇒ 下界」。
  兼容：原四个 flat 字段 `layer4_M1_num_msgs/_num_entities/_dup_mentions_same_directive/_denom_msgs`
        **语义不变**（仍是 orig 口径），并新增 `layer4_M1_flat_keys_note` 指明；结论请读 `layer4_M1_fixed`。
  复现：`python3 v2/evidence/d8_metrics.py --log v2/evidence/run_d8_armB_n4r60_seed42/run.jsonl \
        --label B --whitelist on --out-json /tmp/b.json` ⇒ `M1_orig=0/64`、`M1_fixed=3/64`、
        `hit_seqs=[1974,1988,2118]`。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict

WORLD_TYPES = ("WORLD_DIRECTIVE", "WORLD_GROUP_EVENT")
REJECTED = "WORLD_DIRECTIVE_REJECTED"
MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")

# 冻结词表（判据卡 §2；改词表必须换 sha 并重跑两臂）
KIND_WORDS = {
    "tension": ["缺货", "涨价", "紧俏", "买不到"],
    "edict": ["告示", "通告", "新规矩"],
    "festival": ["节日", "庙会", "集会", "热闹"],
}
BAN = re.compile(r"[（(][^）)]*[）)]")


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def parse_window(rec):
    """与 engine/world_params.py 完全相同的 fallback 链。"""
    p = rec.get("payload") or {}
    start = int(p.get("start_round", p.get("effective_from_round", rec.get("round", 0))) or 0)
    end = int(p.get("end_round", p.get("expires_round", start + 1)) or (start + 1))
    return start, end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--label", default="arm")
    ap.add_argument("--card", default="v2/evidence/D8-mention-criteria-card.md")
    ap.add_argument("--out-json", default="")
    ap.add_argument("--whitelist", choices=["on", "off", "unknown"], default="unknown",
                    help="该臂 `_SALIENT_EVENTS` 是否已放开 WORLD_*（决定 zero_nature 标签；必须显式传，脚本不猜）")
    ap.add_argument("--m1-attribution", choices=["first", "all"], default="all",
                    help="M-1 唯一归属规则：first=R2 原样（每个 msg 只归最早窗口，有缺陷，仅对照）；"
                         "all=修正（归入全部覆盖窗口，任一覆盖实体 kind 命中即算）。两列读数恒同时输出，本参数只决定哪列进 md 摘要")
    ap.add_argument("--neg-control", action="store_true",
                    help="负对照：把词表替换为不相关词，用于检测词表误报率")
    args = ap.parse_args()

    rows = load(args.log)

    # ---------- 世界事件实体 ----------
    seq_to_entity = {}
    entity_meta = {}          # directive_id -> {issued_round, start, end, kind, mechanism_id}
    for rec in rows:
        if rec.get("type") not in WORLD_TYPES:
            continue
        p = rec.get("payload") or {}
        eid = p.get("directive_id") or p.get("directive_ref")
        if not eid:
            continue
        seq_to_entity[rec["seq"]] = eid
        start, end = parse_window(rec)
        prev = entity_meta.get(eid)
        meta = {
            "issued_round": int(p.get("issued_round", rec.get("round", start)) or start),
            "start": start,
            "end": end,
            "kind": str(p.get("kind", "")).lower(),
            "mechanism_id": p.get("mechanism_id", ""),
        }
        # 成对 D-/GE- 取较宽窗口 + 保留 issued_round
        if prev is None:
            entity_meta[eid] = meta
        else:
            prev["start"] = min(prev["start"], meta["start"])
            prev["end"] = max(prev["end"], meta["end"])
            prev["kind"] = prev["kind"] or meta["kind"]
            prev["mechanism_id"] = prev["mechanism_id"] or meta["mechanism_id"]

    W = set(seq_to_entity)                       # 匹配集：两型并集（不动）
    n_world = len(entity_meta)                   # 实体单位：唯一 directive_id

    # ---------- agent 计数（⚠ 分母口径在此处，含死亡处理）----------
    # 分母有三种可选口径，本脚本**全部输出**，由报告选定其一并说明（默认用 born 口径）：
    #   A) n_born         = 出生 agent 数（= 名义规模 4）——**默认**，两臂可比性最好（死亡时序不同不会改变分母）
    #   B) n_alive_end    = 跑完时仍存活数（出生 − 死亡）——随死亡时序变化，两臂可能不等，慎用
    #   C) alive_in_window= 每个 directive 窗口内仍存活的 agent 数之和——最贴近"当时谁能知道"，
    #                       但两臂若死亡时序不同，分母不可比
    born = {r["payload"].get("agent_id") for r in rows if r.get("type") == "AGENT_BORN"}
    died_at = {}
    for r in rows:
        if r.get("type") == "AGENT_DIED":
            aid = (r.get("payload") or {}).get("agent_id")
            died_at[aid] = int((r.get("payload") or {}).get("death_round", r.get("round", 0)) or 0)
    alive = sorted(a for a in born - set(died_at) if a)
    n_born = len([a for a in born if a])
    n_alive = len(alive)                                   # 口径 B
    # 口径 C：每个事件窗口内仍存活的 agent 数（未死者视为永不死亡）
    alive_in_window = {}
    for eid, m in entity_meta.items():
        alive_in_window[eid] = sum(
            1 for a in born
            if a and died_at.get(a, 10 ** 9) >= m["start"])

    # ---------- ① 发生 ----------
    occurrences = [r for r in rows if r.get("type") in WORLD_TYPES]
    rejected = [r for r in rows if r.get("type") == REJECTED]

    # ---------- ② 可见（复算，非落盘）----------
    # visible_events 不落盘；此处留接口，由调用方另跑 contracts.visibility 重算后回填。
    visible_recomputed = None

    # ---------- ③ 沉淀（M-0 双轨）----------
    mw_all = [r for r in rows if r.get("type") == "MEMORY_WRITE"]
    mw_world = [r for r in mw_all if (r.get("payload") or {}).get("source_event_seq") in W]
    m0_raw = len(mw_world)                                            # 列A：原始条数（含成对双记）
    m0_dedup = len({((r.get("payload") or {}).get("agent_id") or r.get("actor"),
                     seq_to_entity[(r["payload"])["source_event_seq"]]) for r in mw_world})
    # M-0 分母（entity 口径，单位 = (agent, directive) 对）：
    #   公式 = 口径 agent 数 × N_world（唯一 directive 数）
    #   默认 born 口径 = n_born × N_world；另给 alive_end / alive_in_window 两种
    denom_m0 = n_born * n_world if n_world else 0
    denom_m0_alive_end = n_alive * n_world if n_world else 0
    denom_m0_window = sum(alive_in_window.values()) if n_world else 0

    # ---------- ③b M-0_windowed（后处理推演）----------
    m0w = []
    for r in mw_world:
        p = r.get("payload") or {}
        eid = seq_to_entity[p["source_event_seq"]]
        m = entity_meta[eid]
        rr = int(r.get("round", 0))
        if m["start"] <= rr < m["end"]:
            m0w.append(r)
    m0w_dedup = len({((r.get("payload") or {}).get("agent_id") or r.get("actor"),
                      seq_to_entity[(r["payload"])["source_event_seq"]]) for r in m0w})

    # ---------- ③c M-0_w（三元组口径，R8-2/R8-5，与 M-0 不得互相代入）----------
    # 单位 = (agent, directive, round)。
    # 分母（R8-5 定稿，上界 0.5）：
    #   denom = 口径 agent 数 × Σ_entity(有效期回合数) = n_born × Σ(end - issued)
    #   本批 = 4 × (6×6) = 144；分子理论满额 = 4 × (6×3) = 72 ⇒ 72/144 = 0.5
    #   ⇒ 0.5 的来源是"感知窗 3 < 有效期 6"，不是 agent 数量折损。
    #   ⚠ 曾误写 n_alive × Σ可感知回合 = 4×18 = 72（会变成上界 1.0，自相矛盾），已改正为 144。
    eff_rounds = {}      # 可感知回合数（感知窗 [r-2,r] ∩ 有效期）
    valid_rounds = {}    # 有效期回合数（end - issued）
    for eid, m in entity_meta.items():
        eff_rounds[eid] = len([t for t in range(m["issued_round"], m["end"])
                               if t - m["issued_round"] <= 2])
        valid_rounds[eid] = m["end"] - m["issued_round"]
    denom_m0w = n_born * sum(valid_rounds.values()) if n_world else 0
    m0w_upper_num = n_born * sum(eff_rounds.values())      # 分子理论满额（上界 = m0w_upper_num/denom_m0w）
    m0w_triples = {((r.get("payload") or {}).get("agent_id") or r.get("actor"),
                    seq_to_entity[(r["payload"])["source_event_seq"]], int(r.get("round", 0)))
                   for r in mw_world}
    # 感知覆盖率（回合口径，R8-2）：感知窗 3 / 有效期 slots
    percep_cover = {eid: (eff_rounds[eid], m["end"] - m["issued_round"]) for eid, m in entity_meta.items()}

    # ---------- OBSERVATION 命中（R5-1：按路径分列，两列不相加）----------
    obs_world = [r for r in rows if r.get("type") == "OBSERVATION"
                 and (r.get("payload") or {}).get("target_event_seq") in W]

    # ---------- ④ 提及（M-1）----------
    words = KIND_WORDS
    if args.neg_control:
        words = {k: [w[::-1] for w in v] for k, v in KIND_WORDS.items()}

    msgs = [r for r in rows if r.get("type") in MSG_TYPES]
    ents_by_issue = sorted(entity_meta.items(), key=lambda kv: kv[1]["issued_round"])

    def body_of(r):
        p = r.get("payload") or {}
        return p.get("body") or ""

    def msg_key(r):
        p = r.get("payload") or {}
        return p.get("msg_uid") or f"{r['seq']}"

    def covering_entities(rr: int) -> list:
        """该回合覆盖到的全部世界事件实体（按 issued_round 升序）。"""
        return [(eid, m) for eid, m in ents_by_issue if m["start"] <= rr < m["end"]]

    def m1_scan(attribution: str):
        """M-1 扫描。attribution:
             "first" = R2 原样口径：只归入 issued_round 最早的那个覆盖窗口（有 break）——**有缺陷，仅作对照列**
             "all"   = 修正口径：一条消息属于**所有**覆盖它的窗口，任一覆盖实体的 kind 词表命中即算命中
        返回 (win_pairs, hits)。win_pairs=[(rec, eid)]（同一消息可对多个 eid 出现多次）；
        hits=[(rec, [(eid, kind, word), ...])]，同一消息只出现一次。
        """
        win_pairs, hits = [], []
        for r in msgs:
            rr = int(r.get("round", 0))
            cov = covering_entities(rr)
            if not cov:
                continue
            chosen = cov[:1] if attribution == "first" else cov
            for eid, _m in chosen:
                win_pairs.append((r, eid))
            s = BAN.sub("", body_of(r))        # 剔除括号旁白（G-1 教训）
            matched = []
            for eid, m in chosen:
                kind = m["kind"]
                for w in words.get(kind, []):
                    if w in s:
                        matched.append((eid, kind, w))
                        break
            if matched:
                hits.append((r, matched))
        return win_pairs, hits

    def m1_columns(attribution: str) -> dict:
        win_pairs, hits = m1_scan(attribution)
        msgs_unique = {msg_key(r) for r, _ in win_pairs}
        hit_msgs = {msg_key(r) for r, _ in hits}
        hit_entities = {eid for _, ms in hits for eid, _k, _w in ms}
        by_entity = Counter(eid for _, ms in hits for eid, _k, _w in ms)
        return {
            "attribution": attribution,
            "denom_msgs": len(msgs_unique),
            "num_msgs": len(hit_msgs),
            "num_entities": len(hit_entities),
            "dup_mentions_same_directive": sum(v - 1 for v in by_entity.values() if v > 1),
            "hit_seqs": sorted(int(r["seq"]) for r, _ in hits),
            "by_entity": dict(sorted(by_entity.items())),
            "hits": [{
                "seq": r["seq"],
                "round": r.get("round"),
                "channel": r.get("type"),
                "matched": [{"entity": eid, "kind": k, "word": w} for eid, k, w in ms],
                "body_excerpt": (body_of(r) or "")[:120].replace("\n", " "),
            } for r, ms in hits],
        }

    # 两列都算、都保留：orig=脚本原样口径（有缺陷，不可作结论）；fixed=修正 kind 归属口径（visitor 无词表 ⇒ 下界）
    m1_orig = m1_columns("first")
    m1_fixed = m1_columns("all")

    # ---- visitor 词表缺口量化（决定 fixed 列是"下界"还是"完整"）----
    kinds_all = sorted({m["kind"] for m in entity_meta.values()})
    kinds_no_lex = [k for k in kinds_all if not words.get(k)]
    cov_stats = {"msgs_covering": 0, "msgs_measurable": 0,
                 "msgs_visitor_only": 0, "msgs_visitor_overlap": 0}
    for r in msgs:
        cov = covering_entities(int(r.get("round", 0)))
        if not cov:
            continue
        cov_stats["msgs_covering"] += 1
        ks = {m["kind"] for _e, m in cov}
        lex_kinds = {k for k in ks if words.get(k)}
        if lex_kinds:
            cov_stats["msgs_measurable"] += 1
            if "visitor" in ks:
                cov_stats["msgs_visitor_overlap"] += 1
        else:
            cov_stats["msgs_visitor_only"] += 1

    # 旧 flat 字段（向后兼容）取 orig 口径；结论请读 layer4_M1_fixed
    _orig_hits = m1_scan("first")[1]
    m1_msgs_unique = {msg_key(r) for r, _ in _orig_hits}
    m1_entities = {eid for _, ms in _orig_hits for eid, _k, _w in ms}
    m1_by_entity = Counter(eid for _, ms in _orig_hits for eid, _k, _w in ms)
    dup_mentions = sum(v - 1 for v in m1_by_entity.values() if v > 1)
    win_pairs_default = m1_scan(args.m1_attribution)[0]   # 窗口重叠会让 (msg,entity) 对数 > msg 数
    denom_m1 = m1_fixed["denom_msgs"]

    # ---------- ④b 真引用（world_ctx.refs）—— 结构事实，与 M-1 文本代理分列、不得相加 ----------
    # B 臂实现给 MSG payload 追加 `world_ctx`（含 refs/kinds/scarcity/prompted）；
    # A 臂（开关关）不写该键 ⇒ 应恒为 0。refs 正常应是 directive_id 或世界事件 seq，
    # 这里两种都匹配，避免实现细节差异把真引用漏算。
    entity_ids = set(entity_meta)
    world_ctx_present = []
    real_ref_msgs = []
    real_ref_entities = set()
    for r in msgs:
        p = r.get("payload") or {}
        wc = p.get("world_ctx")
        if not isinstance(wc, dict):
            continue
        world_ctx_present.append(r)
        refs = wc.get("refs") or []
        hit = set()
        for x in refs:
            xs = str(x)
            if xs in entity_ids:
                hit.add(xs)
            elif xs.isdigit() and int(xs) in seq_to_entity:
                hit.add(seq_to_entity[int(xs)])
        if hit:
            real_ref_msgs.append(r)
            real_ref_entities |= hit

    # ---------- L-2 旁白率（定义同 tools/d5/dialogue_metrics.py:453）----------
    narr = sum(1 for m in msgs if body_of(m).lstrip()[:1] in ("（", "(")) if msgs else 0
    l2 = (narr / len(msgs)) if msgs else 0.0

    # ---------- 词表 sha ----------
    lex = json.dumps(KIND_WORDS, ensure_ascii=False, sort_keys=True).encode()
    lex_sha8 = hashlib.sha256(lex).hexdigest()[:8]

    # ---------- 零的性质 ----------
    def zero_nature():
        """零的性质必须由**调用方声明的臂状态**决定，不能由日志反推。

        理由（防自动化陷阱）：日志里"没有记录"既可能是"白名单未开 ⇒ 结构上不可能"
        （A 臂），也可能是"白名单开了但确实没人观测到"（B 臂）。两者文本相同、性质相反，
        若由脚本自动判定，两臂会得到同一个标签 ⇒ 结论失真。
        因此 `--whitelist {on,off,unknown}` 必须由跑批者按该臂实际代码/开关显式传入。
        """
        if n_world == 0:
            return "不可判(N_world=0)"
        wl = (args.whitelist or "unknown").lower()
        if m0_dedup == 0:
            if wl == "off":
                return "结构性(白名单未开:WORLD_* 不在 _SALIENT_EVENTS ⇒ 结构上不可能沉淀)"
            if wl == "on":
                return "未观测到(白名单已开:事件可被沉淀,但本批无人观测到)"
            return "未判定(需传 --whitelist on|off;脚本不替调用方猜)"
        if m0w_dedup > m0_dedup:
            return "仅窗口外(见 M-0_windowed)"
        return "非零"

    result = {
        "arm": args.label,
        "log": args.log,
        "source_tag": "[真跑]",
        "N_world": n_world,
        "world_entities": {k: v for k, v in sorted(entity_meta.items())},
        "world_seqs": sorted(W),
        "world_records": len(occurrences),
        "world_rejected": len(rejected),
        "n_born_agents": n_born,
        "n_alive_agents": n_alive,
        "n_died_agents": len(died_at),
        "denom_basis": "born（默认；死亡时序不同不改变分母，两臂可比）",
        "layer1_occur": n_world,
        "layer2_visible_recomputed": visible_recomputed,
        "layer3_M0_raw": m0_raw,
        "layer3_M0_dedup": m0_dedup,
        "layer3_M0_denom": denom_m0,
        "layer3_M0_denom_alive_end": denom_m0_alive_end,
        "layer3_M0_denom_window": denom_m0_window,
        "alive_in_window": alive_in_window,
        "layer3_M0_windowed_dedup": m0w_dedup,
        "layer3_M0_windowed_tag": "[后处理推演:日志后处理值,非运行时实测;若时间窗未修,运行时实际值会高于此]",
        "layer3_M0w_triples": len(m0w_triples),
        "layer3_M0w_denom": denom_m0w,
        "layer3_M0w_upper_num": m0w_upper_num,
        "layer3_M0w_upper_bound": (round(m0w_upper_num / denom_m0w, 4) if denom_m0w else None),
        "layer3_M0w_note": "三元组口径 (agent,directive,round)，上界 1.0 但窗口覆盖 3/6；与 M-0(entity 口径,上界1.0) 不得互相代入",
        "perception_coverage_rounds": percep_cover,
        "layer3_observation_world_hits": len(obs_world),
        "layer4_M1_num_msgs": len(m1_msgs_unique),
        "layer4_M1_num_entities": len(m1_entities),
        "layer4_M1_denom_msgs": denom_m1,
        "layer4_M1_dup_mentions_same_directive": dup_mentions,
        # ↓↓↓ R9（2026-10-21，metrics-dev 修正 M-1 归属缺陷）：两列并存，禁止合并、禁止只报一列 ↓↓↓
        "layer4_M1_flat_keys_note": ("上方 layer4_M1_* 四个 flat 字段仍为 **orig（脚本原样口径）** 值，语义未被静默修改；"
                                    "作结论请用 layer4_M1_fixed"),
        "layer4_M1_attribution_default": args.m1_attribution,
        "layer4_M1_win_pairs": {
            "default_attribution": args.m1_attribution,
            "pairs": len(win_pairs_default),
            "msgs": m1_fixed["denom_msgs"],
            "note": "pairs>msgs 即窗口重叠发生；固定先发窗口（orig）时 pairs==msgs",
        },
        "layer4_M1_orig": dict(m1_orig, **{
            "tag": "口径缺陷，不可作结论",
            "rule": ("R2 原样：每个 msg 只归入 issued_round 最早的覆盖窗口（首个命中即 break）；"
                     "窗口重叠时后发事件（如 edict [14,20)）被先发事件（visitor [12,18)）抢走归属"),
        }),
        "layer4_M1_fixed": dict(m1_fixed, **{
            "tag": "visitor 词表未覆盖 ⇒ 下界（真实值 ≥ 本列）",
            "rule": ("修正：一条 msg 属于全部覆盖它的窗口；任一覆盖实体的 kind 词表命中即算命中；"
                     "分母仍为窗口内 MSG_* 去重条数（per-message）"),
        }),
        "layer4_M1_lexicon_coverage": {
            "kinds_in_batch": kinds_all,
            "kinds_with_lexicon": [k for k in kinds_all if words.get(k)],
            "kinds_without_lexicon": kinds_no_lex,
            "declaration": ("visitor 类世界事件本批首次启用，冻结词表只覆盖 tension/edict/festival ⇒ "
                            "凡仅落在 visitor 窗口内、且措辞不含其他 kind 词的 msg 一律漏计；"
                            "因此 layer4_M1_fixed 是**下界**，不是点估计。此处显式声明，不得默认忽略。"),
            "stats": cov_stats,
        },
        "layer4_world_ctx_present_msgs": len(world_ctx_present),
        "layer4_real_ref_msgs": len(real_ref_msgs),
        "layer4_real_ref_entities": len(real_ref_entities),
        "layer4_real_ref_rule": "真引用=MSG.payload.world_ctx.refs 命中世界事件实体（结构事实，可复算）；与 M-1 词表代理并列、不得相加、不得互相替代",
        "layer4_M1_rule": "剔除括号旁白后命中冻结词表；分母=窗口内 MSG_* 条数（per-message，R2 唯一归属）",
        "layer4_M1_reporting_rule": ("分母<30 只报事件数（判据卡）；本批分母 %d %s" % (
            denom_m1,
            "亦按'只报事件数、比率仅作参考'处理（leader 抬档）" if denom_m1 < 100 else "可按率报")),
        "L2_narration_rate_proxy": l2,
        "L2_denom": len(msgs),
        "lexicon_sha8": lex_sha8,
        "neg_control": bool(args.neg_control),
        "zero_nature": zero_nature(),
        "card": args.card,
    }
    try:
        with open(args.card, "rb") as f:
            result["card_sha16"] = hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        result["card_sha16"] = "MISSING"

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[out] {args.out_json}")


if __name__ == "__main__":
    main()
