#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D5 对话质量客观指标复算器（唯一口径来源：D5-指标定义-定稿v1.0.md）。

一条命令从 run.jsonl 复算全部客观指标，输出规范 JSON + Markdown 表。
不联网、不调用 LLM、不改日志；两次运行输出**逐字节相等**。

用法:
    python3 artifacts/code/dialogue_metrics.py \
        --log v2/evidence/run_xxx/run.jsonl \
        [--meta v2/evidence/run_xxx/meta.json] \
        --out-json v2/evidence/metrics_xxx.json \
        --out-md   v2/evidence/metrics_xxx.md

退出码:
    0  成功（含 meta 准入检查 FAIL 但指标已算出——准入结论在 JSON 里显式给出）
    2  输入不可用（日志缺失/行不可解析/无消息事件）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCHEMA_VERSION = "d5-metrics/1.0"
HERE = os.path.dirname(os.path.abspath(__file__))

MSG_TYPES = {"MSG_DM": "dm", "MSG_PUBLIC": "public", "MSG_GROUP": "group"}
DEFAULT_LEXICON = os.path.join(HERE, "backref_lexicon.txt")
DEFAULT_TEMPLATES = os.path.join(HERE, "template_patterns.txt")
DEFAULT_PERSONAS = os.path.join(
    HERE, "..", "..", "code", "config", "personas.json"
)
DEFAULT_EMOTION = os.path.join(HERE, "emotion_lexicon.txt")
DEFAULT_REPAIR = os.path.join(HERE, "repair_lexicon.txt")
DEFAULT_TIMEREF = os.path.join(HERE, "timeref_lexicon.txt")
DEFAULT_TASK_TAGS = os.path.join(HERE, "task_tags.txt")
DEFAULT_F8_LEXICON = os.path.join(HERE, "f8_lexicon.json")
DEFAULT_PLACES = os.path.join(HERE, "..", "..", "code", "config", "places.json")
EMPATHY_MARKERS = ("我懂", "我也", "别难过", "恭喜", "辛苦", "真惨", "太好了", "确实", "是啊", "可不是")

PAREN_LEAD_RE = re.compile(r"^\s*(?:（[^）]{0,120}）|\([^)]{0,120}\))")
PAREN_ANY_RE = re.compile(r"(?:（[^）]{0,120}）|\([^)]{0,120}\))")
AGENT_ID_RE = re.compile(r"P\d{3}(?!\d)")  # 后瞻仅防未来 4 位 ID；与 P\d{3} 在当前数据上等价
PERSONA_PREFIX = "青溪镇·"

STOP_CHARS = set(
    "的了呢吧啊呀吗嘛就都也还你我他她它是不在有和与这那个些一什么怎么"
    "很太更最又再才被把让给对说着过起去来到得地么哦噢哎喂嗯"
)


# ---------------------------------------------------------------- 基础工具


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def r6(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    return round(float(x), 6)


def pct(vals: List[float], q: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return r6(s[0])
    pos = (len(s) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(s) - 1)
    frac = pos - lo
    return r6(s[lo] + (s[hi] - s[lo]) * frac)


def dist(vals: List[float]) -> Dict[str, Any]:
    if not vals:
        return {"n": 0, "min": None, "p10": None, "p50": None, "p90": None,
                "max": None, "mean": None, "stdev": None}
    return {
        "n": len(vals),
        "min": r6(min(vals)),
        "p10": pct(vals, 0.10),
        "p50": pct(vals, 0.50),
        "p90": pct(vals, 0.90),
        "max": r6(max(vals)),
        "mean": r6(sum(vals) / len(vals)),
        "stdev": r6(st.pstdev(vals)) if len(vals) > 1 else 0.0,
    }


def rate(num: int, den: int) -> Optional[float]:
    return None if den == 0 else r6(num / den)


def normalize_body(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("（", "(").replace("）", ")")
    return re.sub(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)\[\]【】]", "", s)


def strip_paren(s: str) -> str:
    return PAREN_ANY_RE.sub("", s).strip()


def content_bigrams(s: str) -> set:
    t = strip_paren(s)
    t = AGENT_ID_RE.sub("", t)
    t = re.sub(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)]", "", t)
    chars = [c for c in t if c not in STOP_CHARS]
    if len(chars) < 2:
        return set()
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def load_lines(path: str) -> List[str]:
    return [ln.strip() for ln in open(path, encoding="utf-8") if ln.strip()]


def load_personas(path: str) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """返回 {pid: 主干名} + 来源信息。"""
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
    info["derived"] = canon(names)
    info["derived_sha256"] = sha256_text(canon(names))
    return names, info


# ---------------------------------------------------------------- 日志读取


def read_run(path: str) -> Tuple[List[dict], Dict[str, Any]]:
    bad = []
    recs: List[dict] = []
    with open(path, encoding="utf-8") as f:
        for i, ln in enumerate(f, 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                recs.append(json.loads(ln))
            except Exception as e:  # noqa: BLE001
                bad.append({"line": i, "error": str(e), "head": ln[:120]})
    return recs, {"bad_lines": bad, "n_bad": len(bad)}


def check_chain(recs: List[dict]) -> Dict[str, Any]:
    prev = "sha256:" + "0" * 64
    seq_ok = True
    link_ok = True
    last_seq = None
    for r in recs:
        if last_seq is not None and r.get("seq") != last_seq + 1:
            seq_ok = False
        if r.get("prev_hash") not in (None, prev):
            link_ok = False
        prev = r.get("hash") or prev
        last_seq = r.get("seq")
    return {"seq_dense": seq_ok, "hash_links_ok": link_ok, "n": len(recs)}


# ---------------------------------------------------------------- 指标主体


def extract_messages(recs: List[dict]) -> List[dict]:
    msgs = []
    for r in recs:
        t = r.get("type")
        if t not in MSG_TYPES:
            continue
        p = r.get("payload") or {}
        body = p.get("body") or p.get("text") or ""
        ctx = p.get("ctx") if isinstance(p.get("ctx"), dict) else {}
        msgs.append({
            "seq": r.get("seq"),
            "round": r.get("round"),
            "actor": r.get("actor"),
            "channel": MSG_TYPES[t],
            "event_type": t,
            "from": p.get("from") or r.get("actor"),
            "to": p.get("to"),
            "body": body,
            "msg_id": p.get("msg_id"),
            "msg_uid": p.get("msg_uid"),
            "reply_to": p.get("reply_to"),
            "refs": p.get("refs") or [],
            "thread_id": p.get("thread_id"),
            "turn_index": p.get("turn_index"),
            "participants": p.get("participants"),
            "ctx_topic": (p.get("ctx") or {}).get("topic") if isinstance(p.get("ctx"), dict) else None,
            "scene": ctx.get("scene") if isinstance(ctx.get("scene"), dict) else None,
            "day": p.get("day"),
            "slot": p.get("slot"),
            "place": p.get("place"),
            "tags": p.get("tag_hints") or [],
        })
    msgs.sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                             m["seq"] if m["seq"] is not None else -1))
    return msgs


def group_threads(msgs: List[dict]) -> Tuple[Dict[str, List[dict]], str]:
    explicit = any(m["thread_id"] for m in msgs)
    threads: Dict[str, List[dict]] = defaultdict(list)
    for m in msgs:
        if m["thread_id"]:
            key = "T:" + str(m["thread_id"])
        else:
            pair = tuple(sorted({str(m["from"]), str(m["to"])}))
            key = "L:%s|%s|%s" % (m["day"], m["channel"], "-".join(pair))
        threads[key].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))
    schema = "explicit" if explicit else "legacy"
    return dict(threads), schema


def pointer_of(m: dict) -> Tuple[Optional[str], int]:
    """返回 (指针目标, 原始指针数)。v0 用 refs 列表，D2 用 reply_to。"""
    if m.get("reply_to"):
        return str(m["reply_to"]), 1
    refs = m.get("refs") or []
    if refs:
        return str(refs[0]), len(refs)
    return None, 0


# ------------------------------------------------- F-8 处境锚定率（尺子）

SCENE_TAIL = ("\n你眼下的光景：", "（这些只是你眼下的底子：顺口带一句就够，别生硬地报地名，也别在这上面多解释；说不着就不提。）")


def wilson_ci(x: int, n: int, z: float) -> Optional[Dict[str, Any]]:
    """标准 Wilson score interval（双侧、不做连续性修正）。n=0 ⇒ None（不填 0）。"""
    if n <= 0:
        return None
    p = x / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4.0 * n * n))
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return {"method": "wilson_score_no_cc", "z": z, "confidence": 0.95, "two_sided": True,
            "x": x, "n": n, "p": r6(p), "lo": r6(lo), "hi": r6(hi)}


def load_f8_inputs(lex_path: str, places_path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """读外部化词表（唯一真源）+ places.json；含一致性断言，漂移即报错。"""
    lex = json.load(open(lex_path, encoding="utf-8"))
    narrow = lex["time"]["narrow"]
    # 自洽性：narrow 至少要有 slot_agnostic 或 by_slot 之一；两版都不得为空
    if not narrow.get("slot_agnostic") and not narrow.get("by_slot"):
        raise SystemExit("[FAIL] f8_lexicon.json: time.narrow 既无 slot_agnostic 也无 by_slot（词表为空 ⇒ 判定无意义）")
    for key in ("slot_words_full", "wide_reference"):
        if not (lex["time"].get(key) or {}):
            raise SystemExit("[FAIL] f8_lexicon.json: time.%s 缺失（宽版/渲染镜像必须可复算）" % key)
    places = {"path": places_path, "exists": os.path.exists(places_path),
              "id2name": {}, "names": [], "short_map": {}, "sha256": None}
    if places["exists"]:
        raw = json.load(open(places_path, encoding="utf-8"))
        items = raw.get("places", raw) if isinstance(raw, dict) else raw
        for it in items:
            pid, nm = it.get("place_id") or it.get("id"), it.get("name_cn")
            if pid and nm:
                places["id2name"][str(pid)] = str(nm)
        places["names"] = list(dict.fromkeys(places["id2name"].values()))
        places["sha256"] = sha256_file(places_path)
    short_map = dict(((lex.get("place") or {}).get("short_names") or {}).get("map") or {})
    places["short_map"] = {k: list(v) for k, v in short_map.items()}
    f8 = {"lexicon": {"path": os.path.abspath(lex_path), "sha256": sha256_file(lex_path),
                      "version": lex.get("version"), "frozen_at": lex.get("frozen_at"),
                      "sources": lex.get("sources", {})},
          "places": places, "raw": lex}
    return f8, lex


def _recover_injected_line(scene: Dict[str, Any], lex: Dict[str, Any],
                           id2name: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """反解 ctx.scene.line_sha256 ⇒ 模型实际看到的措辞（slot 措辞 / 活动措辞）。

    只在开关 ON 时 ctx.scene 才有 line_sha256；反解不出就返回 None（不猜）。
    """
    want = scene.get("line_sha256")
    if not want:
        return None
    slot = str(scene.get("slot") or "")
    act = str(scene.get("activity") or "")
    name = id2name.get(str(scene.get("place") or ""), "")
    slot_words = lex["time"]["slot_words_full"]["by_slot"].get(slot, [])
    act_words = (lex["activity"].get("render_by_type") or {}).get(act, [])
    for sw in (slot_words or [""]):
        for aw in (act_words or [""]):
            bits = [x for x in (sw, ("你在" + name) if name else "", aw) if x]
            if not bits:
                continue
            line = SCENE_TAIL[0] + "，".join(bits) + "。" + SCENE_TAIL[1]
            if sha256_text(line.strip()) == want or sha256_text(line.strip()) == "sha256:" + want:
                return {"slot_word": sw, "activity_word": aw, "place_name": name,
                        "line": line.strip()}
    return None


def compute_f8(msgs: List[dict], f8: Dict[str, Any]) -> Dict[str, Any]:
    """F-8 处境锚定率（per-message）+ 三分解，分子/分母/率/CI 逐项分列。

    判定口径（prereg §2 + Amendment 1 + leader 02:22 覆盖矩阵方法论）：
      * F-8t 时段：判定词表 = time.narrow，scope = 本人当回合 slot（泛词只在本档生效，避免全局膨胀）
      * F-8p 地点：只认 places.json::name_cn（含可接受简称），分子要求「本人 place」；内部 id 命中走守卫
      * F-8a 活动：渲染措辞 ∪ 语义等价项，且只在 ctx.scene.activity 存在时可算；缺失 ⇒ not_applicable（不填 0）
    """
    raw = f8["raw"]
    z = float(raw["thresholds"]["wilson_z_95_two_sided"])
    tn = raw["time"]["narrow"]
    agn = list(tn.get("slot_agnostic") or [])
    by_slot = {k: list(v) for k, v in (tn.get("by_slot") or {}).items()}
    narrow_flat = list(dict.fromkeys(agn + [t for v in by_slot.values() for t in v]))
    broad_slot = {k: list(v) for k, v in ((raw["time"].get("slot_scoped_broad") or {}).get("by_slot") or {}).items()}
    sf = raw["time"].get("slot_words_full") or {}
    echo = list(sf.get("echo_tokens") or [])
    sens_add = list((raw["time"].get("narrow_sensitivity_add") or {}).get("tokens") or [])
    wr = raw["time"].get("wide_reference") or {}
    wide = list(wr.get("tokens") or [])
    ck = raw["time"].get("ckpt_reference") or {}
    ckpt_narrow = list(ck.get("narrow_tokens") or [])
    ckpt_wide = list(dict.fromkeys(ckpt_narrow + list(ck.get("wide_extra_tokens") or [])))
    act = raw.get("activity") or {}
    act_render = {k: list(v) for k, v in (act.get("render_by_type") or {}).items()}
    act_sem = {k: list(v) for k, v in ((act.get("semantic_equivalents") or {}).get("by_type") or {}).items()}
    id2name = f8["places"]["id2name"]
    place_names = f8["places"]["names"]
    short_map = f8["places"].get("short_map") or {}
    aliases = list(((raw.get("place") or {}).get("alias_provisional") or {}).get("tokens") or [])
    th = raw["thresholds"]

    def anyhit(body: str, toks: List[str]) -> bool:
        return any(t and t in body for t in toks)

    keys = ("F-8t_own_slot", "F-8t_broad_scoped", "F-8t_open_any", "F-8t_sens_add", "F-8t_wide",
            "F-8t_ckpt_narrow", "F-8t_ckpt_wide", "F-8t_echo", "F-8p_own_place", "F-8p_short_only",
            "F-8p_public_cn", "F-8p_open_any_cn", "F-8a", "F-8a_render_only",
            "F-8a_exact", "F-8t_exact", "place_id_in_body", "place_alias_hit", "F-8_union")
    hits = {k: 0 for k in keys}
    den = {"F-8t_own_slot": 0, "F-8p_own_place": 0, "F-8p_public_cn": 0, "F-8a": 0}
    n_slot_missing = n_scene_present = n_scene_activity = n_line_recovered = 0
    per_slot_hits = Counter()
    per_slot_den = Counter()
    act_den_by_type = Counter()
    samples: List[Dict[str, Any]] = []

    for m in msgs:
        body = m.get("body") or ""
        slot = str(m.get("slot") or "")
        scene = m.get("scene") or {}
        if scene:
            n_scene_present += 1
        # ---- 时段（F-8t）：一律按本人当回合 slot 限定
        if slot:
            den["F-8t_own_slot"] += 1
            per_slot_den[slot] += 1
            t_judge = anyhit(body, agn + (by_slot.get(slot) or []))
            t_broad = anyhit(body, agn + (broad_slot.get(slot) or []))
            if t_judge:
                per_slot_hits[slot] += 1
        else:
            n_slot_missing += 1
            t_judge = t_broad = False
        t_open = anyhit(body, narrow_flat)
        t_sens = anyhit(body, narrow_flat + sens_add)
        t_echo = anyhit(body, echo)
        # ---- 地点（F-8p）
        pl = m.get("place")
        own_name = id2name.get(str(pl)) if pl else None
        own_toks = ([own_name] if own_name else []) + list(short_map.get(own_name or "", []))
        p_hit = anyhit(body, own_toks)
        p_canonical = bool(own_name) and own_name in body
        if own_name:
            den["F-8p_own_place"] += 1
        if m.get("channel") == "public":
            den["F-8p_public_cn"] += 1
            if anyhit(body, place_names):
                hits["F-8p_public_cn"] += 1
        id_leak = any(re.search(r"(?<![A-Za-z_])" + re.escape(pid) + r"(?![A-Za-z_])", body)
                      for pid in id2name) if id2name else False
        alias_hit = anyhit(body, aliases)
        # ---- 活动（F-8a）
        act_type = str(scene.get("activity") or "") if scene else ""
        a_hit = a_render = False
        if act_type and (act_type in act_render or act_type in act_sem):
            den["F-8a"] += 1
            n_scene_activity += 1
            act_den_by_type[act_type] += 1
            a_render = anyhit(body, act_render.get(act_type) or [])
            a_hit = a_render or anyhit(body, act_sem.get(act_type) or [])
        # ---- 精确通道（反解 line_sha256）
        rec = _recover_injected_line(scene, raw, id2name) if scene else None
        t_exact = a_exact = False
        if rec:
            n_line_recovered += 1
            t_exact = bool(rec["slot_word"]) and rec["slot_word"] in body
            a_exact = bool(rec["activity_word"]) and rec["activity_word"] in body
        # ---- 记账
        hits["F-8t_own_slot"] += int(t_judge)
        hits["F-8t_broad_scoped"] += int(t_broad)
        hits["F-8t_open_any"] += int(t_open)
        hits["F-8t_sens_add"] += int(t_sens)
        hits["F-8t_echo"] += int(t_echo)
        hits["F-8t_wide"] += int(anyhit(body, wide))
        hits["F-8t_ckpt_narrow"] += int(anyhit(body, ckpt_narrow))
        hits["F-8t_ckpt_wide"] += int(anyhit(body, ckpt_wide))
        hits["F-8p_own_place"] += int(p_hit)
        hits["F-8p_short_only"] += int(p_hit and not p_canonical)
        hits["F-8p_open_any_cn"] += int(anyhit(body, place_names))
        hits["F-8a"] += int(a_hit)
        hits["F-8a_render_only"] += int(a_render)
        hits["F-8a_exact"] += int(a_exact)
        hits["F-8t_exact"] += int(t_exact)
        hits["place_id_in_body"] += int(id_leak)
        hits["place_alias_hit"] += int(alias_hit)
        if t_judge or p_hit or a_hit:
            hits["F-8_union"] += 1
        if (t_judge or p_hit or a_hit) and len(samples) < 8:
            samples.append({"seq": m.get("seq"), "round": m.get("round"),
                            "type": m.get("event_type"), "slot": slot or None, "place": pl,
                            "time_hit": t_judge, "place_hit": p_hit, "activity_hit": a_hit,
                            "body": body[:60]})

    def blk(num, d, rule: str, not_applicable_if_zero: str = None,
            reason_code: str = None, reason: str = None, **kw: Any) -> Dict[str, Any]:
        is_na = (not_applicable_if_zero is not None) and d == 0
        out = {"numerator": (None if is_na else num), "denominator": (None if is_na else d),
               "num": (None if is_na else num), "den": (None if is_na else d),
               "ratio": None if is_na else rate(num, d),
               "rate": None if is_na else rate(num, d),
               "rate_pct": (None if is_na or d == 0 else r6(100.0 * num / d)),
               "wilson95": (None if is_na else wilson_ci(num, d, z)),
               "denominator_rule": rule}
        if is_na:
            out.update({"status": "not_applicable", "reason": reason_code or not_applicable_if_zero,
                        "reason_detail": reason or "分母为 0 ⇒ 该指标无从计算（不填 0、不出率）"})
        out.update(kw)
        return out

    n_msg = len(msgs)
    out: Dict[str, Any] = {
        "unit": "per-message",
        "arm": None,
        "F-8": blk(hits["F-8_union"], n_msg,
                   "num=命中本人当回合处境（时段/自身地点/活动 任一）的 MSG_* 条数；den=全部 MSG_*；"
                   "各分项按自己的分母计入（F-8p 用有 place 的 167、F-8a 用有 activity 的 n）"),
        "F-8t_time": blk(hits["F-8t_own_slot"], den["F-8t_own_slot"],
                         "判定词表=time.narrow（Amendment 1：不含 刚/早上/下午/晚上/昨晚/今天/今儿）；"
                         "scope=本人当回合 slot；den=有 slot 的 MSG_*",
                         lexicon="narrow", scope="own_slot", n_slot_missing=n_slot_missing,
                         hits_by_slot=dict(sorted(per_slot_hits.items())),
                         den_by_slot=dict(sorted(per_slot_den.items()))),
        "F-8p_place": blk(hits["F-8p_own_place"], den["F-8p_own_place"],
                          "只认 places.json::name_cn（含 place.short_names 可接受简称）；"
                          "num=正文含「本人 place」名称的条数；den=有 payload.place 的 MSG_*"),
        "F-8p_public": blk(hits["F-8p_public_cn"], den["F-8p_public_cn"],
                           "仅覆盖说明、不作判定：MSG_PUBLIC 无 place 字段，den=MSG_PUBLIC 条数，"
                           "num=正文命中任一 name_cn 条数"),
        "F-8a_activity": blk(hits["F-8a"], den["F-8a"],
                             "num=正文命中「本人 ctx.scene.activity」的渲染措辞或语义等价项；"
                             "den=含 ctx.scene.activity 的 MSG_*",
                             not_applicable_if_zero="no_ctx_scene",
                             reason=("本臂 MSG payload 无 ctx.scene.activity（%d/%d 条缺该键）⇒ 分母不适用；"
                                     "不等于『模型没做活动锚定』" % (n_msg - n_scene_activity, n_msg)),
                             hits_by_activity=dict(sorted(act_den_by_type.items())),
                             activity_lexicon="render ∪ semantic_equivalents"),
        "guard": {
            "place_id_in_body": blk(hits["place_id_in_body"], n_msg,
                                    "守卫（对应 L-8c）：正文出现 places.json::place_id 内部 id 的条数；>0 ⇒ 硬失败"),
            "place_alias_hit": blk(hits["place_alias_hit"], n_msg,
                                   "归因抽样用（provisional 别名），不参与判定"),
        },
        "diagnostics": {
            "F-8a_render_only": blk(hits["F-8a_render_only"], den["F-8a"],
                                    "严格口径：只认渲染措辞原文（不认语义等价项）；den 同 F-8a",
                                    not_applicable_if_zero="no_ctx_scene",
                                    reason="本臂无 ctx.scene.activity ⇒ 无从计算"),
            "F-8p_short_only": blk(hits["F-8p_short_only"], den["F-8p_own_place"],
                                   "其中只靠简称命中（如 广场/面包铺）的条数，用于说明简称扩表的贡献"),
            "F-8t_broad_scoped": blk(hits["F-8t_broad_scoped"], den["F-8t_own_slot"],
                                     "Amendment 2 候选（未批准，仅敏感性）：把渲染词 下午/上午/早上/晚上 加进对应档，仍按本回合 slot 限定",
                                     lexicon="slot_scoped_broad", scope="own_slot"),
            "F-8t_open_any": blk(hits["F-8t_open_any"], n_msg,
                                 "敏感性：narrow 词表不按 slot 限定；den=全部 MSG_*"),
            "F-8t_render_echo": blk(hits["F-8t_echo"], n_msg,
                                    "回声通道（防系统性判漏）：命中渲染词表 SLOT_WORDS 的可指认词元任一（含 下午/上午/午后）；不参与判定"),
            "F-8t_ckpt_narrow": blk(hits["F-8t_ckpt_narrow"], n_msg,
                                    "复现跑前 checkpoint 窄表读数（time.ckpt_reference.narrow_tokens，不按 slot 限定）；"
                                    "仅核对工具一致性，不参与判定"),
            "F-8t_narrow_plus_jinr": blk(hits["F-8t_sens_add"], n_msg,
                                         "敏感性：当前 narrow 词表 ∪ {今儿}，不按 slot 限定；不参与判定"),
            "F-8t_wide_reference": blk(hits["F-8t_wide"], n_msg,
                                       "仅参考、不参与判定（Amendment 1）"),
            "F-8t_ckpt_wide": blk(hits["F-8t_ckpt_wide"], n_msg,
                                  "复现跑前 checkpoint 宽表读数（ckpt_reference.narrow_tokens ∪ {刚}，不按 slot 限定）；"
                                  "仅核对工具一致性，不参与判定"),
            "F-8p_open_any_cn": blk(hits["F-8p_open_any_cn"], n_msg,
                                    "敏感性：正文命中任一 name_cn（不看本人位置）；den=全部 MSG_*"),
            "F-8t_exact_injected_word": blk(hits["F-8t_exact"], n_line_recovered,
                                            "仅当 ctx.scene.line_sha256 可反解：num=正文含「模型实际看到的那一 slot 措辞」",
                                            not_applicable_if_zero="no_line_sha256",
                                            reason="本臂无 ctx.scene.line_sha256（OFF 臂/老批预期）⇒ 无从反解"),
            "F-8a_exact_injected_word": blk(hits["F-8a_exact"], n_line_recovered,
                                            "同上口径的活动措辞",
                                            not_applicable_if_zero="no_line_sha256",
                                            reason="本臂无 ctx.scene.line_sha256 ⇒ 无从反解"),
        },
        "coverage": {"n_msg": n_msg, "n_scene_present": n_scene_present,
                     "n_scene_activity": n_scene_activity, "n_line_sha_recovered": n_line_recovered,
                     "n_slot_missing": n_slot_missing,
                     "note": "ctx.scene 只在开关 ON 时出现 ⇒ OFF 臂/老批 n_scene_present=0 属预期，非实现缺陷"},
        "denominator_ledger": {
            "F-8": n_msg, "F-8t_time": den["F-8t_own_slot"], "F-8p_place": den["F-8p_own_place"],
            "F-8p_public": den["F-8p_public_cn"], "F-8a_activity": den["F-8a"],
            "note": "四个分项分母互不相同，逐个标明；不得共用总分母",
        },
        "unavailable_ledger": [],
        "lexicon": f8["lexicon"],
        "places": {"path": f8["places"]["path"], "sha256": f8["places"]["sha256"],
                   "n_places": len(id2name), "names": place_names,
                   "short_names": short_map},
        "known_gap": (raw["time"].get("narrow") or {}).get("known_gap"),
        "thresholds": th,
        "samples": samples,
    }
    if den["F-8a"] == 0:
        out["unavailable_ledger"].append({"item": "F-8a_activity", "status": "not_applicable",
                                          "reason": "no_ctx_scene",
                                          "detail": out["F-8a_activity"].get("reason_detail"),
                                          "den": None, "num": None})
    if den["F-8t_own_slot"] < n_msg:
        out["unavailable_ledger"].append({"item": "F-8t_time",
                                          "reason": "%d 条 MSG 无 slot 字段，已从该分项分母剔除（未填 0）"
                                                    % n_slot_missing,
                                          "den": den["F-8t_own_slot"], "num": hits["F-8t_own_slot"]})
    if den["F-8p_own_place"] < n_msg:
        out["unavailable_ledger"].append({"item": "F-8p_place",
                                          "reason": "%d 条 MSG（MSG_PUBLIC）无 payload.place，已从分母剔除，"
                                                    "另在 F-8p_public 单列覆盖（不作判定）"
                                                    % (n_msg - den["F-8p_own_place"]),
                                          "den": den["F-8p_own_place"], "num": hits["F-8p_own_place"]})
    out["degenerate_d1"] = {
        "rule": ("OFF 臂 F-8 分子 ≤ %s ⇒ C1/两比例检验不适用，只报 ON 臂 x/n + 标准 Wilson 95%% CI"
                 % th.get("degenerate_off_num_le")),
        "off_num_le": th.get("degenerate_off_num_le"),
        "d2_min_abs_effect_X": th.get("D2_min_abs_effect_X"),
        "note": "单臂输出只给数值；退化判定需两臂 json 对照",
    }
    return out


def compute(msgs: List[dict], lexicon: List[str], templates: List[re.Pattern],
            names: Dict[str, str], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    threads, schema = group_threads(msgs)
    n_msg = len(msgs)
    uids = [m.get("msg_uid") for m in msgs if m.get("msg_uid")]
    ids_ = [m.get("msg_id") for m in msgs if m.get("msg_id")]
    out["assertions"] = {
        "msg_uid_unique": (len(set(uids)) == len(uids)) if uids else None,
        "msg_uid_n": len(uids),
        "msg_id_unique": (len(set(ids_)) == len(ids_)) if ids_ else None,
        "msg_id_n": len(ids_),
        "note": "D2 起指针目标 = msg_uid(<seed>:<seq>)，全局唯一；msg_id 为展示标签（legacy 格式可能重复，不作指针目标）",
    }
    out["meta"] = {"n_messages": n_msg, "n_threads": len(threads),
                   "thread_schema": schema,
                   "channels": dict(Counter(m["channel"] for m in msgs))}

    # ---------------- S-1 turns / S-2 thread scale / S-3 longest chain
    turns_a, turns_b, chain_alt, chain_ptr, lens, nspk = [], [], [], [], [], []
    single_msg = 0
    single_spk = 0
    multi_turn = 0
    for key in sorted(threads):
        th = threads[key]
        speakers = [str(m["from"]) for m in th]
        ta = 1 + sum(1 for i in range(1, len(speakers)) if speakers[i] != speakers[i - 1])
        tb = sum(1 for m in th if pointer_of(m)[0])
        turns_a.append(ta)
        turns_b.append(tb)
        lens.append(len(th))
        nspk.append(len(set(speakers)))
        if len(th) == 1:
            single_msg += 1
        if len(set(speakers)) == 1:
            single_spk += 1
        if ta >= 3:
            multi_turn += 1
        # 交替链
        best = 1
        cur = 1
        for i in range(1, len(speakers)):
            if speakers[i] != speakers[i - 1]:
                cur += 1
                best = max(best, cur)
            else:
                cur = 1
        chain_alt.append(best)
        # 指针链（沿 reply_to 反查本方最长回复深度）
        by_id = {}
        for i, m in enumerate(th):
            if m.get("msg_uid"):
                by_id[m["msg_uid"]] = i
            if m["msg_id"]:
                by_id.setdefault(m["msg_id"], i)
        depth = [1] * len(th)
        for i, m in enumerate(th):
            tgt, _ = pointer_of(m)
            if tgt and tgt in by_id and by_id[tgt] < i:
                depth[i] = depth[by_id[tgt]] + 1
        chain_ptr.append(max(depth) if depth else 0)

    out["S-1_turns_per_thread"] = {
        "A_speaker_turns": dist(turns_a),
        "B_roundtrips": dist(turns_b),
        "B_note": "v0 无指针字段时恒为 0（字段缺失，非缺陷）；B 不参与前后差",
    }
    # S-1C 轮数（turn_index 去重）——与「说话人交替段」严格区分
    ti_counts = []
    for key in sorted(threads):
        th = threads[key]
        tis = [m["turn_index"] for m in th if m.get("turn_index") is not None]
        if tis:
            ti_counts.append(len(set(tis)))
    out["S-1C_turns_by_turn_index"] = {
        "definition": "轮数 = 线程内 turn_index 去重后的个数（群聊同轮多人并发只计 1 轮）；无 turn_index 的 legacy 批次为 null",
        "dist": dist(ti_counts) if ti_counts else {"n": 0},
        "note": "计轮请用本字段；S-1A 是「说话人交替段数」，不等于轮数；chain_by_pointer 只作可解析性辅助",
    }

    out["S-2_thread_scale"] = {
        "msgs_per_thread": dist(lens),
        "single_msg_thread_ratio": rate(single_msg, len(threads)),
        "single_speaker_thread_ratio": rate(single_spk, len(threads)),
        "multi_turn_thread_ratio": rate(multi_turn, len(threads)),
        "multi_turn_threshold": "turns_A >= 3",
        "speakers_per_thread": dist(nspk),
    }
    out["S-3_longest_chain"] = {
        "chain_by_alternation": dist(chain_alt),
        "chain_by_pointer": dist(chain_ptr),
    }

    # ---------------- S-4 reply pointer coverage
    ptr_ok = ptr_empty = ptr_cross = ptr_forward = ptr_dangling = denom = 0
    # 指针目标解析：优先 msg_uid（D2 起为 "<seed>:<seq>"，全局唯一）；legacy 回退 msg_id
    all_ids = {m.get("msg_uid") or m["msg_id"] for m in msgs if (m.get("msg_uid") or m["msg_id"])}
    all_ids |= {m["msg_id"] for m in msgs if m["msg_id"]}
    for key in sorted(threads):
        th = threads[key]
        ids = {}
        for i, m in enumerate(th):
            if m.get("msg_uid"):
                ids[m["msg_uid"]] = i
            if m["msg_id"]:
                ids.setdefault(m["msg_id"], i)
        for i, m in enumerate(th):
            is_first = (m["turn_index"] == 0) if m["turn_index"] is not None else (i == 0)
            if is_first:
                continue
            denom += 1
            tgt, _ = pointer_of(m)
            if not tgt:
                ptr_empty += 1
            elif tgt not in all_ids:
                ptr_dangling += 1          # 指向不存在的 msg_id（脏指针）
            elif tgt in ids and ids[tgt] < i:
                ptr_ok += 1
            elif tgt in ids and ids[tgt] > i:
                ptr_forward += 1           # 指向同线程未来消息
            else:
                ptr_cross += 1             # 指向其它线程的消息
    out["S-4_reply_pointer_coverage"] = {
        "rate": rate(ptr_ok, denom),
        "denominator_nonfirst_msgs": denom,
        "ptr_ok": ptr_ok, "ptr_empty": ptr_empty,
        "ptr_cross_thread": ptr_cross, "ptr_forward": ptr_forward,
        "ptr_dangling": ptr_dangling,
        "classify": "empty=未填 / dangling=指向不存在的 msg_id / forward=指向同线程未来 / cross_thread=指向别线程 / ok=指向同线程前序",
    }

    # ---------------- S-5 orphan
    with_tid = sum(1 for m in msgs if m["thread_id"])
    out["S-5_orphan_msg_rate"] = rate(n_msg - with_tid, n_msg) if schema == "explicit" else None
    out["S-5_orphan_msg_rate_note"] = (
        "legacy schema（无 thread_id）时不适用，报 null" if schema == "legacy" else "ok")

    # ---------------- K-1 topic continuation（三列独立 + 分项，不出合成数）
    def cont_stats(group_key_fn):
        th: Dict[str, List[dict]] = {}
        for m in msgs:
            th.setdefault(group_key_fn(m), []).append(m)
        for k in th:
            th[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                      m["seq"] if m["seq"] is not None else -1))
        pairs = or_tag = or_backref = or_lexical = 0
        same = same_den = 0
        for k in sorted(th):
            seq = th[k]
            for i in range(1, len(seq)):
                prev, cur = seq[i - 1], seq[i]
                pairs += 1
                or_tag += bool(set(prev["tags"]) & set(cur["tags"]))
                or_backref += any(w in cur["body"] for w in lexicon)
                or_lexical += bool(content_bigrams(prev["body"]) & content_bigrams(cur["body"]))
                if cur["ctx_topic"] or prev["ctx_topic"]:
                    same_den += 1
                    same += bool(cur["ctx_topic"] and cur["ctx_topic"] == prev["ctx_topic"])
        return {
            "denominator_adjacent_pairs": pairs,
            "cont_same_topic": ("N/A" if same_den == 0 else rate(same, same_den)),
            "cont_same_topic_denominator": same_den,
            "cont_backref": rate(or_backref, pairs),
            "cont_lexical": rate(or_lexical, pairs),
            "tag_overlap_rate_reference": rate(or_tag, pairs),
        }

    narrow = cont_stats(lambda m: "n:%s|%s|%s" % (
        m["day"], m["channel"], "-".join(sorted({str(m["from"]), str(m["to"])})))) 
    wide = cont_stats(lambda m: "w:%s|%s" % (m["day"], m["channel"]))

    def mixed_key(m):
        if m.get("thread_id"):
            return "m:T|%s" % m["thread_id"]
        if m["channel"] == "dm":
            k = "-".join(sorted({str(m["from"]), str(m["to"])}))
        elif m["channel"] == "public":
            k = "-"
        else:
            k = str(m.get("place") or "-")
        return "m:%s|%s|%s" % (m["day"], m["channel"], k)

    mixed = cont_stats(mixed_key)
    mixed["grouping"] = ("mixed = channel 感知：dm 按无序对、public 按 (day) 合流、group 按 group_id/day；"
                         "与 prompt-linguist 的 D3 口径一致（t300 分母 68）")
    narrow["grouping"] = "narrow = (day, channel, {from,to})：同一天同一对参与者的会话线（与 S-1/S-2 的 legacy 线程一致）"
    wide["grouping"] = "wide = (day, channel)：同一天同一渠道内按 (round,seq) 相邻（口径更宽，分母更大）"
    narrow["composite"] = "leader 裁决：不出合成数；如需派生指标须另行登记，不得作为判据"
    wide["composite"] = narrow["composite"]
    out["K-1_topic_continuation"] = mixed
    out["K-1b_topic_continuation_wide"] = wide
    out["K-1c_topic_continuation_pair"] = narrow

    # ---------------- L 系列
    lens_all = [len(m["body"].strip()) for m in msgs]
    lens_x = [len(strip_paren(m["body"])) for m in msgs]
    narr = sum(1 for m in msgs if m["body"].lstrip()[:1] in ("（", "("))
    paren_any = sum(1 for m in msgs if PAREN_ANY_RE.search(m["body"]))
    third = 0
    for m in msgs:
        own = names.get(str(m["from"]))
        if not own:
            continue
        lead = PAREN_LEAD_RE.match(m["body"])
        block = lead.group(0) if lead else ""
        rest = m["body"][len(block):] if block else m["body"]
        if own in block or rest.lstrip().startswith(own):
            third += 1
    tpl_hits = []
    for m in msgs:
        hit = None
        for idx, rx in enumerate(templates):
            if rx.search(m["body"]):
                hit = idx
                break
        tpl_hits.append(hit)
    n_tpl = sum(1 for h in tpl_hits if h is not None)
    norm = [normalize_body(m["body"]) for m in msgs]
    uniq = len(set(norm))
    # 8-gram 近重复
    shingles = []
    for t in norm:
        shingles.append({t[i:i + 8] for i in range(max(0, len(t) - 7))})
    sh_index: Dict[str, List[int]] = defaultdict(list)
    for i, sh in enumerate(shingles):
        for g in sh:
            sh_index[g].append(i)
    dup_msgs = set()
    for g, idxs in sh_index.items():
        if len(idxs) > 1:
            dup_msgs.update(idxs)
    leak = sum(1 for m in msgs if AGENT_ID_RE.search(m["body"]))
    # L-8b：裸 ID 只出现在括号（旁白）块内、台词本体无 ID
    # 定义（写死）：括号块 = re.findall(r"（[^（）]*）|\([^()]*\)", body)（不嵌套、全半角都算）；
    # 移除括号块后的余串若仍含未闭合的左括号「（」或「(」，则从该处到结尾整体视为旁白；
    # 若余串仍匹配 AGENT_ID_RE ⇒ 归「台词本体命中」（只计入 L-8，不计入 L-8b）。
    PAREN_BLOCK_RE = re.compile(r"（[^（）]*）|\([^()]*\)")
    paren_leak = 0
    body_leak = 0
    for m in msgs:
        body = m["body"]
        if not AGENT_ID_RE.search(body):
            continue
        rest = PAREN_BLOCK_RE.sub("", body)
        for ch in ("（", "("):
            pos = rest.find(ch)
            if pos >= 0:
                rest = rest[:pos]        # 未闭合左括号：其后全算旁白
        if AGENT_ID_RE.search(rest):
            body_leak += 1
        else:
            paren_leak += 1
    meta_rx = re.compile(r"作为(一个)?(AI|人工智能|语言模型|助手)|我是一个语言模型|作为一个?AI")
    meta_hit = sum(1 for m in msgs if meta_rx.search(m["body"]))
    # L-10 自称错误
    cand = 0
    self_err = 0
    for m in msgs:
        own = names.get(str(m["from"]))
        has_self = ("我" in m["body"]) or ("俺" in m["body"]) or ("咱" in m["body"])
        others = [(pid, nm) for pid, nm in names.items()
                  if pid != str(m["from"]) and nm and nm in m["body"]]
        if has_self or others:
            cand += 1
        for pid, nm in others:
            if re.search(r"我[，,]?\s*(?:是|叫|乃|就是)?\s*" + re.escape(nm), m["body"]):
                self_err += 1
                break
    directed = [m for m in msgs if m["channel"] in ("dm", "group")]
    second = sum(1 for m in directed if re.search(r"[你您]", m["body"]))
    # L-12 拆两口径（2026-10-20 与 prompt-linguist 对齐后定稿）：
    #  L-12a 提及：正文出现「对方」名字（DM: to；GROUP: 任一其他 participants；排除说话者自己）
    #  L-12b 称呼：名字以称呼语形式出现（名字后紧跟 标点/语气词，或名字后为句末）
    ADDR_TAIL = "，、！？：；—…~～啊呀哦呢哈嘛吧"
    def peer_names(m):
        out = []
        to = m.get("to")
        if to and str(to) in names:
            out.append(names[str(to)])
        for pid in (m.get("participants") or []):
            pid = str(pid)
            if pid != str(m["from"]) and pid in names:
                out.append(names[pid])
        # 去重、排除说话者自己的名字
        own = names.get(str(m["from"]))
        return [x for x in dict.fromkeys(out) if x and x != own]
    peer_hit = 0
    addr_hit = 0
    for m in msgs:
        if m["channel"] not in ("dm", "group"):
            continue
        body = m["body"]
        pn = peer_names(m)
        if any(n in body for n in pn):
            peer_hit += 1
        for n in pn:
            idx = body.find(n)
            while idx >= 0:
                nxt = body[idx + len(n): idx + len(n) + 1]
                if nxt == "" or nxt in ADDR_TAIL:
                    addr_hit += 1
                    break
                idx = body.find(n, idx + 1)
            else:
                continue
            break

    # L-13 内部 token 泄漏：ctx.topic 原字符串直接出现在正文（模板/token 未人话化）
    leak_msgs = []
    for m in msgs:
        t = m.get("ctx_topic")
        if t and t in (m.get("body") or ""):
            leak_msgs.append({"seq": m.get("seq"), "topic": t, "body": (m["body"])[:80]})
    token_leak = len(leak_msgs)
    out["L-13_token_leak"] = {
        "token_leak_rate": rate(token_leak, n_msg),
        "n": token_leak,
        "by_topic": dict(sorted(Counter(x["topic"] for x in leak_msgs).items())),
        "samples": leak_msgs[:5],
        "rule": "分母 = 全部 MSG；分子 = `ctx.topic` 原字符串（内部 token）直接出现在 body 的消息数。只测「token 未人话化」，不测语义正确性",
    }

    out["L_wording"] = {
        "L-1_len": {"all": dist(lens_all), "excl_paren": dist(lens_x)},
        "L-2_narration_rate_proxy": rate(narr, n_msg),
        "L-3_paren_block_any": rate(paren_any, n_msg),
        "L-4_third_person_self_rate": rate(third, n_msg),
        "L-5_template_hit_rate": rate(n_tpl, n_msg),
        "L-5_template_hit_by_pattern": {str(i): sum(1 for h in tpl_hits if h == i)
                                        for i in sorted({h for h in tpl_hits if h is not None})},
        "L-6_dup_exact_rate": rate(n_msg - uniq, n_msg),
        "L-7_dup_ngram8_rate": rate(len(dup_msgs), n_msg),
        "L-8_agent_id_leak_rate": rate(leak, n_msg),
        "L-8b_paren_only_id_rate": rate(paren_leak, n_msg),
        "L-8c_body_leak_rate": rate(body_leak, n_msg),
        "L-8_invariant": {
            "identity": "L-8 == L-8b + L-8c（消息级，互斥分类）",
            "counts": {"L-8": leak, "L-8b": paren_leak, "L-8c": body_leak},
            "holds": (leak == paren_leak + body_leak),
        },
        "L-8b_definition": ("括号块=re.findall(r\"（[^（）]*）|\\([^()]*\\)\")（不嵌套、全半角都算）；"
                            "移除括号块后余串若含未闭合左括号，则其后全算旁白；余串仍含 ID ⇒ 记「本体命中」(L-8c)，否则记 L-8b。"
                            "同一句既有括号块又有括号外 ID ⇒ 归本体（只进 L-8/L-8c，不进 L-8b）"),
        "L-8_definition": ("分子=body（仅正文，不含 msg_id/body_ref）命中 re 正则 `P\\d{3}(?!\\d)`（不加 \\b；后瞻仅防未来 4 位 ID，与 `P\\d{3}` 在当前数据上等价）；"
                           "括号内 ID 也计入（另给 L-8b 只统计括号内）；分母=全部 MSG 条数"),
        "L-9_meta_talk_rate": rate(meta_hit, n_msg),
        "L-10_self_address_error_rate": rate(self_err, cand),
        "L-10_denominator": cand,
        "L-11_second_person_rate_dm_group": rate(second, len(directed)),
        "L-11_note": "only dm+group; MSG_PUBLIC 单列（本行不含）",
        "L-12_peer_mention_rate": rate(peer_hit, len(directed)),
        "L-12b_peer_address_rate": rate(addr_hit, len(directed)),
        "L-12_definitions": {
            "L-12a_mention": "正文出现对方名字（DM: to；GROUP: 任一其他 participants；排除说话者自己、排除自己名字）",
            "L-12b_address": "名字以称呼语形式出现：名字后紧跟 [，、！？：；—…~～啊呀哦呢哈嘛吧] 或已到句末",
            "denominator": "DM+GROUP 消息条数（不含 PUBLIC）",
            "judgement": "判定用 L-12b（称呼）；L-12a 作描述性提及率",
        },
        "denominators": {"per_message": n_msg, "dm_group": len(directed), "threads": len(threads)},
    }

    # ---------------- E 系列
    rounds = {m["round"] for m in msgs if m["round"] is not None}
    agents = {str(m["from"]) for m in msgs}
    out["E_efficiency"] = {
        "E-1_msg_per_agent_round": r6(n_msg / (len(agents) * len(rounds))) if rounds else None,
        "n_agents": len(agents),
        "n_rounds": len(rounds),
    }

    # ---------------- F 系列：生活气息（可复算代理指标）
    ex = extra or {}
    emo: Dict[str, int] = ex.get("emotion", {})
    repair: List[str] = ex.get("repair", [])
    timeref: List[str] = ex.get("timeref", [])
    task_tags = set(ex.get("task_tags", []))
    TRANS_RX = re.compile(r"多少钱|价钱|买|卖|记账|按流程|付钱|工钱|便宜点|划算|合同")

    def polarity(body: str) -> int:
        pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
        neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
        if pos > neg:
            return 1
        if neg > pos:
            return -1
        return 0

    func = 0
    for m in msgs:
        if set(m["tags"]) & task_tags or TRANS_RX.search(m["body"]):
            func += 1
    out["F-1_chatter"] = {
        "nonfunctional_chatter_rate": rate(n_msg - func, n_msg),
        "functional_msgs": func,
        "rule": "功能性 = tag_hints∩task_tags 非空 或 正文命中事务正则；闲聊率 = 1 − 功能性占比",
    }

    threads_mixed: Dict[str, List[dict]] = {}
    for m in msgs:
        threads_mixed.setdefault(mixed_key(m), []).append(m)
    for k2 in threads_mixed:
        threads_mixed[k2].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                              m["seq"] if m["seq"] is not None else -1))

    drift_pairs = pairs_cnt = 0
    multi_tag_threads = 0
    # --- R19 尺子修复（口径变更，保留旧口径对照） -------------------------------
    # 死尺子事实（board-scout `r19-f2-recheck.md` §1/§2，构造正例 PASS）：
    #   新结构下 `tag_hints` 在同一线程内**恒为常量**（发起=模板 id，回复原样继承），
    #   于是旧 F-2 的「tag 无交集」否决项恒 False、旧 F-2b 的「union≥2」恒不成立
    #   ⇒ 两指标在真实数据上**数学不可能 >0**；而内容层实测 66~73% 相邻对 jaccard<0.10。
    # 修法：把「机制侧（tag 是否变）」与「内容侧（相邻消息是否换话头）」拆成两列，
    #       内容侧不再被 tag 一票否决；旧口径原样保留输出（键名不变），供跨报告对照。
    content_drift_pairs = 0          # 内容侧：jaccard < 0.10（不看 tag）
    tag_switch_pairs = 0             # 机制侧：相邻对 tag 集合不相等（= tag_added + tag_replaced）
    tag_added_pairs = 0              # 机制侧：旧 tag 集是新 tag 集的**真子集**（多挂一个，原话题没丢）
    tag_replaced_pairs = 0           # 机制侧：两集合**无交集**（真换话题）
    switch_jacs: List[float] = []    # 发生 tag 切换的相邻对的 jaccard 分布
    all_jacs: List[float] = []       # 全部相邻对的 jaccard 分布
    for key in sorted(threads_mixed):
        th = threads_mixed[key]
        tagsets = [set(m["tags"]) for m in th]
        if len(set().union(*tagsets)) >= 2 if tagsets else False:
            multi_tag_threads += 1
        for i in range(1, len(th)):
            pairs_cnt += 1
            a, b = content_bigrams(th[i - 1]["body"]), content_bigrams(th[i]["body"])
            jac = (len(a & b) / len(a | b)) if (a | b) else 0.0
            all_jacs.append(jac)
            if jac < 0.10:
                content_drift_pairs += 1
            prev_tags, cur_tags = set(th[i - 1]["tags"]), set(th[i]["tags"])
            if prev_tags != cur_tags:
                tag_switch_pairs += 1
                switch_jacs.append(jac)
                if prev_tags and prev_tags < cur_tags:
                    tag_added_pairs += 1          # 话题展开（原有话题保留）
                elif not (prev_tags & cur_tags):
                    tag_replaced_pairs += 1       # 真换话题（R19 主判据）
            if not (set(th[i - 1]["tags"]) & set(th[i]["tags"])) and jac < 0.10:
                drift_pairs += 1
    out["F-2_topic_drift"] = {
        "drift_rate": rate(drift_pairs, pairs_cnt),
        "multi_topic_thread_ratio": rate(multi_tag_threads, len(threads)),
        "rule": "相邻消息 tag 无交集 且 char-bigram Jaccard<0.10 记一次话题转移；漂移率=转移/相邻对",
        "denominator_adjacent_pairs": pairs_cnt,
        "status": "LEGACY_DEAD_RULER",
        "status_note": ("R19：本键保留原口径仅作跨报告对照。新结构下 tag_hints 线程内恒定 ⇒ "
                        "「tag 无交集」恒 False ⇒ 该读数结构性恒 0，不得作为效果判据；"
                        "请读 F-2_content_drift / F-2_tag_switch（口径变更依据 "
                        "team-workspace/r19-f2-recheck.md）。"),
    }
    out["F-2_content_drift"] = {
        "drift_rate": rate(content_drift_pairs, pairs_cnt),
        "denominator_adjacent_pairs": pairs_cnt,
        "rule": ("内容侧话题漂移：相邻消息 char-bigram Jaccard<0.10 记一次换话头；"
                 "**不以 tag 作否决项**（tag 恒定是引擎构造，不是对话事实）"),
        "jaccard_all": dist(all_jacs),
        "jaccard_switched": dist(switch_jacs),
    }
    out["F-2_tag_switch"] = {
        "switch_rate": rate(tag_switch_pairs, pairs_cnt),
        "switch_pairs": tag_switch_pairs,
        "denominator_adjacent_pairs": pairs_cnt,
        "rule": ("机制侧话题切换：相邻消息 tag 集合不相等即记一次（含「回复追加第二个 tag」）；"
                 "本列测「引擎是否承认话题变了」，**不得单独作为效果判据**"),
    }
    out["F-2_tag_change_split"] = {
        "tag_added": tag_added_pairs,
        "tag_added_rate": rate(tag_added_pairs, pairs_cnt),
        "tag_replaced": tag_replaced_pairs,
        "tag_replaced_rate": rate(tag_replaced_pairs, pairs_cnt),
        "denominator_adjacent_pairs": pairs_cnt,
        "rule": ("R19 拆分（board-scout 要求）：「多挂一个 tag、原话题保留」记 tag_added（话题展开）；"
                 "「两集合无交集」记 tag_replaced（真换话题，**主判据**）。"
                 "两者互斥，和 = F-2_tag_switch.switch_pairs（仅当 prev 非空时；空 tag 集不计入任一侧）"),
    }
    out["F-2b_multi_topic_threads"] = {
        "multi_topic_thread_ratio": rate(multi_tag_threads, len(threads_mixed)),
        "n_multi_topic_threads": multi_tag_threads,
        "denominator_threads": len(threads_mixed),
        "denominator_threads_group": len(threads),
        "rule": ("线程内 tag 种数≥2 的线程数 / 线程数；R19 起**分子分母统一到 mixed_key 线程口径**，"
                 "并同时打印两个分母（旧版分子 mixed_key、分母 group_threads，v0 批 136 vs 172 不一致）"),
    }

    echo_den = echo_ok = 0
    for key in sorted(threads_mixed):
        th = threads_mixed[key]
        for i in range(1, len(th)):
            p_prev = polarity(th[i - 1]["body"])
            if p_prev == 0:
                continue
            echo_den += 1
            p_cur = polarity(th[i]["body"])
            if p_cur == p_prev or any(w in th[i]["body"] for w in EMPATHY_MARKERS):
                echo_ok += 1
    out["F-3_emotion_echo"] = {
        "echo_rate": rate(echo_ok, echo_den),
        "denominator": echo_den,
        "rule": "上一句极性≠0 时，下一句极性相同 或 含共情标记 → 呼应",
    }

    tension = closed = 0
    lags = []
    for key in sorted(threads_mixed):
        th = threads_mixed[key]
        for i in range(1, len(th)):
            prev_neg = polarity(th[i - 1]["body"]) < 0
            cur_neg = polarity(th[i]["body"]) < 0
            conflict = (polarity(th[i - 1]["body"]) * polarity(th[i]["body"]) < 0) or cur_neg
            if not conflict:
                continue
            tension += 1
            for j in range(i + 1, min(i + 9, len(th))):
                if any(w in th[j]["body"] for w in repair):
                    closed += 1
                    lags.append(j - i)
                    break
    out["F-4_tension_repair"] = {
        "closed_loop_rate": rate(closed, tension),
        "tension_events": tension,
        "repaired": closed,
        "mean_lag_msgs": r6(sum(lags) / len(lags)) if lags else None,
        "rule": "张力 = 相邻极性相反 或 当前句极性为负；其后 8 条同线程内出现修复词 = 闭环",
    }

    habit_days: Dict[tuple, set] = defaultdict(set)
    for m in msgs:
        if m["day"] is None:
            continue
        habit_days[(str(m["from"]), m["slot"], m["place"])].add(m["day"])
    best: Dict[str, int] = defaultdict(int)
    for (pid, _slot, _place), days in habit_days.items():
        best[pid] = max(best[pid], len(days))
    agents_all = {str(m["from"]) for m in msgs}
    strong = sum(1 for a in agents_all if best.get(a, 0) >= 3)
    out["F-5_habit_repetition"] = {
        "habit_strength": rate(strong, len(agents_all)),
        "max_repeat_days_mean": r6(sum(best.get(a, 0) for a in agents_all) / len(agents_all)) if agents_all else None,
        "rule": "习惯 = 同一 agent 在同一 (slot, place) 出现 ≥3 天；强度 = 有习惯的 agent / agent 总数",
    }

    tref = sum(1 for m in msgs if any(w in m["body"] for w in timeref))
    out["F-6_crossday_memory"] = {
        "timeref_rate": rate(tref, n_msg),
        "rule": "正文命中时间回指词表（昨天/前天/上次…）即计入；只测「提到过去」，不测「引用是否正确」（后者需人工或 D2 ctx）",
    }
    # F-7a 越界提及（提及当时不在场的角色）
    names_map = names or {}
    id_by_name = {v: k for k, v in names_map.items() if v}
    agent_place: Dict[tuple, str] = {}
    seq_by_round: Dict[Any, List[int]] = defaultdict(list)
    for r in (extra or {}).get("records", []):
        pass  # records 未传入时跳过（见下方 events 参数）
    events = (extra or {}).get("events", [])
    for r in events:
        if r.get("type") not in ("PLACE_ARRIVED", "PLACE_MOVE"):
            continue
        p_ = r.get("payload") or {}
        aid = p_.get("agent_id")
        plc = p_.get("place") or p_.get("to_place")
        if aid and plc:
            agent_place[(r.get("round"), aid)] = plc
    unknown = 0
    off = 0
    for m in msgs:
        peers = [nm for nm in names_map.values() if nm and nm in m["body"] and nm != names_map.get(str(m["from"]))]
        if not peers:
            continue
        base = m.get("place")
        checked = 0
        for nm in peers:
            pid = id_by_name.get(nm)
            if not pid:
                continue
            plc = agent_place.get((m["round"], pid))
            if plc is None:
                unknown += 1
                continue
            checked += 1
            if base and plc != base:
                off += 1
                break
        if checked == 0:
            unknown += 1
    out["F-7a_offscreen_mention"] = {
        "offscreen_mention_rate": rate(off, n_msg),
        "applicability": ("v0 因裸 ID 不可判（正文直呼 P0xx、人名可检样本≈0）；"
                          "D2 注入显示名后恢复计算，届时以 L-12 peer_name_address_rate>0 为前提"
                          if off == 0 and unknown == 0 else "ok"),
        "denominator": n_msg,
        "unknown_place_lookups": unknown,
        "rule": ("提及他人名字（persona 主干名）时，若该角色在同一 round 的 PLACE_ARRIVED 位置 ≠ 本条消息 place，"
                 "记为越界提及；只测「引用不可能在场的人」，不测「引用不可能知道的事件」（后者需 judge，F-7b）"),
    }

    out["F_lexicons"] = {
        "emotion_sha256": ex.get("emotion_sha"), "repair_sha256": ex.get("repair_sha"),
        "timeref_sha256": ex.get("timeref_sha"), "task_tags_sha256": ex.get("task_tags_sha"),
    }

    # ---------------- F-8 处境锚定率（三分解并列；词表来自外部文件）
    if ex.get("f8"):
        f8blk = compute_f8(msgs, ex["f8"])
        f8blk["arm"] = ex.get("arm")
        out["F-8_scene_anchor"] = f8blk

    return out



def compute_llm(recs: List[dict], n_msg: int) -> Dict[str, Any]:
    tokens_out = 0
    n_dialogue_calls = 0
    degraded = 0
    n_calls = 0
    by_model = Counter()
    for r in recs:
        if r.get("type") != "LLM_CALL":
            continue
        p = r.get("payload") or {}
        n_calls += 1
        if p.get("degraded"):
            degraded += 1
        by_model[(p.get("provider"), p.get("model"))] += 1
        if p.get("purpose") == "dialogue":
            n_dialogue_calls += 1
            tokens_out += int(p.get("tokens_out") or 0)
    return {
        "llm_calls": n_calls,
        "dialogue_calls": n_dialogue_calls,
        "degraded_calls": degraded,
        "degraded_ratio": rate(degraded, n_calls),
        "E-2_tokens_out_per_dialogue_call": r6(tokens_out / n_dialogue_calls) if n_dialogue_calls else None,
        "E-2_tokens_out_per_message": r6(tokens_out / n_msg) if n_msg else None,
        "provider_models": [{"provider": k[0], "model": k[1], "calls": v}
                            for k, v in sorted(by_model.items(), key=lambda kv: (-kv[1], str(kv[0])))],
    }


# ---------------------------------------------------------------- 准入检查


def admission_check(meta: Optional[dict], recs: List[dict], msgs: List[dict],
                    parse: Dict[str, Any], chain: Dict[str, Any],
                    wording: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    m = meta or {}
    legacy_manifest = bool(m) and ("events" not in m)
    checks["B-7_files"] = {"pass": meta is not None, "detail": "meta.json 存在" if meta else "无 meta.json → 非证据级"}
    checks["B-8_parse"] = {"pass": parse["n_bad"] == 0, "detail": parse["bad_lines"][:5]}
    ev = m.get("events")
    if legacy_manifest:
        checks["B-9_event_count"] = {
            "pass": True,
            "detail": {"meta.events": None, "actual_lines": len(recs),
                       "note": "legacy manifest 无 events 字段，改以 wc -l 为准（须人工核对）"},
        }
    else:
        checks["B-9_event_count"] = {
            "pass": (ev is not None and int(ev) == len(recs)),
            "detail": {"meta.events": ev, "actual_lines": len(recs)},
        }
    prov = (m.get("provider") or "").strip()
    checks["B-10_provider"] = {"pass": bool(prov) and "mock" not in prov.lower(), "detail": prov or "<empty>"}
    n_dlg = sum(1 for r in recs if r.get("type") == "LLM_CALL" and (r.get("payload") or {}).get("purpose") == "dialogue")
    checks["B-11_real_calls"] = {"pass": n_dlg > 0, "detail": {"dialogue_calls": n_dlg}}
    n_calls = sum(1 for r in recs if r.get("type") == "LLM_CALL")
    deg = sum(1 for r in recs if r.get("type") == "LLM_CALL" and (r.get("payload") or {}).get("degraded"))
    dr = (deg / n_calls) if n_calls else 0.0
    checks["B-12_degraded_ratio"] = {"pass": dr <= 0.05, "detail": {"ratio": r6(dr), "degraded": deg, "calls": n_calls}}
    types = {r.get("type") for r in recs}
    need = ["WORLD_INIT", "MSG_DM", "LLM_CALL", "TURN_SEAL"]
    checks["B-13_event_families"] = {"pass": all(t in types for t in need),
                                     "detail": {"missing": [t for t in need if t not in types]}}
    pairs = {(mm["day"], tuple(sorted({str(mm["from"]), str(mm["to"])})))
             for mm in msgs if mm["channel"] == "dm"}
    n_dm = sum(1 for mm in msgs if mm["channel"] == "dm")
    checks["B-15_msg_volume"] = {"pass": len(msgs) >= 150 and n_dm >= 100 and len(pairs) >= 12,
                                 "detail": {"msg_dm": n_dm, "messages": len(msgs),
                                            "dm_threads": len(pairs),
                                            "floor": "MSG>=150 且 MSG_DM>=100 且 DM 会话线>=12（v1.2）"}}
    # v1.1：manifest 必须记录实际生效的 rounds / ROUNDS_PER_SLOT
    re_ = m.get("rounds_effective")
    rps = m.get("rounds_per_slot_effective")
    checks["B-2b_manifest_effective"] = {
        "pass": (re_ is not None and rps is not None) or legacy_manifest,
        "detail": {"rounds_effective": re_, "rounds_per_slot_effective": rps,
                   "note": ("legacy manifest：以 meta.cmd 中的 --rounds 为准，须人工核对"
                            if legacy_manifest else "")},
    }
    req = ["from", "to", "body", "msg_id", "day", "slot", "place", "tag_hints"]
    miss = [mm.get("msg_id") or f"seq{mm['seq']}" for mm in msgs
            if not mm["body"].strip()]
    checks["B-15_msg_fields"] = {"pass": not miss, "detail": {"empty_body": miss[:5],
                                                              "required_keys": req}}
    rounds = sorted({r.get("round") for r in recs if r.get("round") is not None})
    dense = bool(rounds) and rounds == list(range(rounds[0], rounds[0] + len(rounds)))
    checks["B-16_round_dense"] = {"pass": dense, "detail": {"min": rounds[0] if rounds else None,
                                                            "max": rounds[-1] if rounds else None,
                                                            "n": len(rounds)}}
    checks["B-17_hash_chain"] = {"pass": chain["hash_links_ok"] and chain["seq_dense"],
                                 "detail": chain}
    # ---- v1.1 三层真跑判据（核验方要求，2026-10-20）
    prov_dist: Dict[str, int] = {}
    model_set = set()
    for r in recs:
        if r.get("type") != "LLM_CALL":
            continue
        p = r.get("payload") or {}
        pv = str(p.get("provider") or "<none>")
        prov_dist[pv] = prov_dist.get(pv, 0) + 1
        if p.get("model"):
            model_set.add(str(p.get("model")))
    checks["B-19_provider_distribution"] = {
        "pass": bool(prov_dist) and all(k.lower() == "openai_compat" for k in prov_dist),
        "detail": {"providers": prov_dist, "rule": "全部 LLM_CALL.provider 必须为 openai_compat"},
    }
    checks["B-20_model_no_mock"] = {
        "pass": bool(model_set) and not any("mock" in m.lower() for m in model_set),
        "detail": {"models": sorted(model_set), "rule": "model 去重集合不得含 mock"},
    }
    w = wording or {}
    tpl = w.get("L-5_template_hit_rate")
    dup = w.get("L-6_dup_exact_rate")
    checks["B-21_body_not_template"] = {
        "pass": (tpl is not None and tpl < 0.5 and (dup is None or dup < 0.5)),
        "detail": {"L-5_template_hit_rate": tpl, "L-6_dup_exact_rate": dup,
                   "rule": "模板命中率<50% 且 完全重复率<50%；另需人工抽样双查"},
    }
    verdict = all(c["pass"] for c in checks.values())
    return {"verdict": "ADMITTED" if verdict else "REJECTED", "checks": checks,
            "manifest_profile": "legacy" if legacy_manifest else ("strict" if m else "none"),
            "evidence_level": "evidence" if verdict else "probe"}


# ---------------------------------------------------------------- 输出


def to_markdown(res: Dict[str, Any], log_path: str) -> str:
    lines = []
    A = lines.append
    A("# 对话质量客观指标读数（D5 复算器自动生成）\n")
    A(f"- 输入日志: `{log_path}`")
    A(f"- run.jsonl sha256: `{res['inputs']['run_sha256']}`")
    A(f"- 脚本 sha256: `{res['inputs']['script_sha256']}`")
    A(f"- 口径版本: `{res['schema_version']}` / thread_schema=`{res['meta']['thread_schema']}`")
    adm = res.get("admission") or {}
    A(f"- 准入结论: **{adm.get('verdict', 'NO_META')}** / evidence_level=`{adm.get('evidence_level', 'probe')}`\n")
    A(f"消息数 {res['meta']['n_messages']}，线程数 {res['meta']['n_threads']}，"
      f"channel={res['meta']['channels']}\n")

    def tbl(title, rows):
        A(f"### {title}\n")
        A("| 指标 | 值 |")
        A("|---|---|")
        for k, v in rows:
            A(f"| `{k}` | {v} |")
        A("")

    s1 = res["S-1_turns_per_thread"]
    tbl("S-1 线程结构（per-thread；**轮数请用 S-1C**）", [
        ("S-1C 轮数(turn_index 去重) p50/p90/max",
         f"{res.get('S-1C_turns_by_turn_index', {}).get('dist', {}).get('p50')} / "
         f"{res.get('S-1C_turns_by_turn_index', {}).get('dist', {}).get('p90')} / "
         f"{res.get('S-1C_turns_by_turn_index', {}).get('dist', {}).get('max')}"),
        ("S-1A 说话人交替段数 p50/p90/max",
         f"{s1['A_speaker_turns']['p50']} / {s1['A_speaker_turns']['p90']} / {s1['A_speaker_turns']['max']}"),
        ("S-1B 往复对数(指针) p50/max", f"{s1['B_roundtrips']['p50']} / {s1['B_roundtrips']['max']}"),
    ])
    s2 = res["S-2_thread_scale"]
    tbl("S-2 线程规模（per-thread）", [
        ("msgs_per_thread p50/p90/max", f"{s2['msgs_per_thread']['p50']} / {s2['msgs_per_thread']['p90']} / {s2['msgs_per_thread']['max']}"),
        ("single_msg_thread_ratio", s2["single_msg_thread_ratio"]),
        ("single_speaker_thread_ratio", s2["single_speaker_thread_ratio"]),
        ("multi_turn_thread_ratio (turns_A>=3)", s2["multi_turn_thread_ratio"]),
    ])
    s3 = res["S-3_longest_chain"]
    tbl("S-3 最长链（per-thread）", [
        ("chain_by_alternation p50/max", f"{s3['chain_by_alternation']['p50']} / {s3['chain_by_alternation']['max']}"),
        ("chain_by_pointer max", s3["chain_by_pointer"]["max"]),
    ])
    s4 = res["S-4_reply_pointer_coverage"]
    tbl("S-4 回复指针完整率（per-message，条件分母）", [
        ("rate", s4["rate"]), ("denominator_nonfirst_msgs", s4["denominator_nonfirst_msgs"]),
        ("ptr_ok", s4["ptr_ok"]), ("ptr_empty", s4["ptr_empty"]),
        ("ptr_cross_thread", s4["ptr_cross_thread"]), ("ptr_forward", s4["ptr_forward"]),
        ("ptr_dangling", s4.get("ptr_dangling")),
    ])
    k1 = res["K-1_topic_continuation"]
    k1w = res.get("K-1b_topic_continuation_wide", {})
    tbl("K-1b 话题承接·宽口径（day+channel 相邻，分母更大）", [
        ("cont_backref", k1w.get("cont_backref")),
        ("cont_lexical", k1w.get("cont_lexical")),
        ("tag_overlap_rate_reference", k1w.get("tag_overlap_rate_reference")),
        ("denominator_adjacent_pairs", k1w.get("denominator_adjacent_pairs")),
    ])
    k1p = res.get("K-1c_topic_continuation_pair", {})
    tbl("K-1c 话题承接·对端口径（day+channel+对端；与 S-1/S-2 legacy 线程一致）", [
        ("cont_backref", k1p.get("cont_backref")),
        ("cont_lexical", k1p.get("cont_lexical")),
        ("denominator_adjacent_pairs", k1p.get("denominator_adjacent_pairs")),
    ])
    tbl("K-1 话题承接·主口径 mixed（dm 按对、public 按日、group 按组；三列独立，不出合成数）", [
        ("cont_same_topic", k1["cont_same_topic"]),
        ("cont_backref", k1["cont_backref"]),
        ("cont_lexical", k1["cont_lexical"]),
        ("tag_overlap_rate_reference", k1["tag_overlap_rate_reference"]),
        ("denominator_adjacent_pairs", k1["denominator_adjacent_pairs"]),
    ])
    L = res["L_wording"]
    tbl("L 措辞层（per-message）", [
        ("L-1_len.p50 / p90", f"{L['L-1_len']['all']['p50']} / {L['L-1_len']['all']['p90']}"),
        ("L-1_len_excl_paren.p50", L["L-1_len"]["excl_paren"]["p50"]),
        ("L-2_narration_rate_proxy", L["L-2_narration_rate_proxy"]),
        ("L-3_paren_block_any", L["L-3_paren_block_any"]),
        ("L-4_third_person_self_rate", L["L-4_third_person_self_rate"]),
        ("L-5_template_hit_rate", L["L-5_template_hit_rate"]),
        ("L-6_dup_exact_rate", L["L-6_dup_exact_rate"]),
        ("L-7_dup_ngram8_rate", L["L-7_dup_ngram8_rate"]),
        ("L-8_agent_id_leak_rate（分母=全MSG n=%d）" % L["denominators"]["per_message"], L["L-8_agent_id_leak_rate"]),
        ("L-9_meta_talk_rate", L["L-9_meta_talk_rate"]),
        ("L-10_self_address_error_rate", L["L-10_self_address_error_rate"]),
        ("L-11_second_person_rate（分母=dm+group n=%d）" % L["denominators"]["dm_group"], L["L-11_second_person_rate_dm_group"]),
        ("L-12a 对端提及率（分母=dm+group n=%d）" % L["denominators"]["dm_group"], L.get("L-12_peer_mention_rate")),
        ("L-12b 对端称呼率（分母=dm+group n=%d，判定用）" % L["denominators"]["dm_group"], L.get("L-12b_peer_address_rate")),
        ("L-8b_paren_only_id_rate（分母=全MSG n=%d；仅旁白内ID）" % L["denominators"]["per_message"], L.get("L-8b_paren_only_id_rate")),
        ("L-8c_body_leak_rate（分母=全MSG n=%d；台词本体ID）" % L["denominators"]["per_message"], L.get("L-8c_body_leak_rate")),
    ])
    F = {k: res[k] for k in res if k.startswith("F-")}
    if F.get("F-1_chatter"):
        tbl("F 生活气息（proxy，per-message / per-adjacent-pair）", [
            ("F-1 非功能性闲聊占比", F["F-1_chatter"]["nonfunctional_chatter_rate"]),
            ("F-2 话题漂移率", F["F-2_topic_drift"]["drift_rate"]),
            ("F-2b 多话题线程占比", F["F-2_topic_drift"]["multi_topic_thread_ratio"]),
            ("F-3 情绪呼应率", F["F-3_emotion_echo"]["echo_rate"]),
            ("F-3 分母", F["F-3_emotion_echo"]["denominator"]),
            ("F-4 修复闭环率", F["F-4_tension_repair"]["closed_loop_rate"]),
            ("F-4 张力事件数", F["F-4_tension_repair"]["tension_events"]),
            ("F-5 习惯强度", F["F-5_habit_repetition"]["habit_strength"]),
            ("F-6 跨天记忆引用率", F["F-6_crossday_memory"]["timeref_rate"]),
            ("F-7a 越界提及率", F.get("F-7a_offscreen_mention", {}).get("offscreen_mention_rate")),
        ])
    f8 = res.get("F-8_scene_anchor")
    if f8:
        def fx(b: Dict[str, Any]) -> str:
            if not b:
                return "-"
            if b.get("status") == "not_applicable":
                return "not_applicable（%s）" % (b.get("reason") or "-")
            ci = b.get("wilson95") or {}
            return "%d/%d = %s%%  Wilson95[%s%%, %s%%]" % (
                b["num"], b["den"],
                ("%.2f" % b["rate_pct"]) if b.get("rate_pct") is not None else "-",
                ("%.2f" % (100 * ci["lo"])) if ci else "-",
                ("%.2f" % (100 * ci["hi"])) if ci else "-")
        A("### F-8 处境锚定率（per-message，三分项并列；词表外部冻结 sha256=%s）\n"
          % f8["lexicon"]["sha256"])
        A("| 项 | 分子/分母/率 | 分母口径 |")
        A("|---|---|---|")
        for name, b in (("F-8（总：任一项命中）", f8["F-8"]),
                        ("F-8t 时段词（narrow，本回合 slot）", f8["F-8t_time"]),
                        ("F-8p 地点中文名（本人 place）", f8["F-8p_place"]),
                        ("F-8a 活动人话名", f8["F-8a_activity"]),
                        ("F-8p_public（仅覆盖说明，不判定）", f8["F-8p_public"]),
                        ("守卫：正文出现内部 place_id", f8["guard"]["place_id_in_body"])):
            A("| %s | %s | %s |" % (name, fx(b), b.get("denominator_rule", "")))
        A("")
        A("**仅参考、不参与判定 / 敏感性通道**\n")
        A("| 项 | 分子/分母/率 |")
        A("|---|---|")
        D = f8["diagnostics"]
        for name, b in (("F-8t 宽版词表", D["F-8t_wide_reference"]),
                        ("F-8t 复现 checkpoint 窄表(7/191)", D["F-8t_ckpt_narrow"]),
                        ("F-8t 复现 checkpoint 宽表(74/191)", D["F-8t_ckpt_wide"]),
                        ("F-8t narrow∪{今儿}（不按 slot 限定）", D["F-8t_narrow_plus_jinr"]),
                        ("F-8t slot-scoped broad（Amendment 2 候选）", D["F-8t_broad_scoped"]),
                        ("F-8t 渲染词表回声通道", D["F-8t_render_echo"]),
                        ("F-8t 不限本回合 slot", D["F-8t_open_any"]),
                        ("F-8p 任一中文地名", D["F-8p_open_any_cn"]),
                        ("F-8p 其中只靠简称命中", D["F-8p_short_only"]),
                        ("F-8a 严格口径（只认渲染原文）", D["F-8a_render_only"]),
                        ("F-8t 命中模型实际看到的措辞", D["F-8t_exact_injected_word"]),
                        ("F-8a 命中模型实际看到的措辞", D["F-8a_exact_injected_word"])):
            A("| %s | %s |" % (name, fx(b)))
        A("")
        A("**分母不适用清单**：%s\n" % (json.dumps(f8["unavailable_ledger"], ensure_ascii=False)
                                        if f8["unavailable_ledger"] else "无"))
    e = res["E_efficiency"]
    tbl("E 效率层", [
        ("E-1_msg_per_agent_round", e["E-1_msg_per_agent_round"]),
        ("E-2_tokens_out_per_message", res["llm"]["E-2_tokens_out_per_message"]),
        ("dialogue_calls", res["llm"]["dialogue_calls"]),
        ("degraded_ratio", res["llm"]["degraded_ratio"]),
    ])
    if adm:
        A("### 准入检查明细\n")
        A("| 编号 | 通过 | 细节 |")
        A("|---|---|---|")
        for k, v in adm["checks"].items():
            A(f"| {k} | {'✅' if v['pass'] else '❌'} | {json.dumps(v['detail'], ensure_ascii=False)[:200]} |")
        A("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D5 对话质量客观指标复算器")
    ap.add_argument("--log", required=True, help="run.jsonl 路径")
    ap.add_argument("--meta", default=None, help="meta.json 路径（可选）")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--lexicon", default=DEFAULT_LEXICON)
    ap.add_argument("--templates", default=DEFAULT_TEMPLATES)
    ap.add_argument("--personas", default=DEFAULT_PERSONAS)
    ap.add_argument("--emotion", default=DEFAULT_EMOTION)
    ap.add_argument("--repair", default=DEFAULT_REPAIR)
    ap.add_argument("--timeref", default=DEFAULT_TIMEREF)
    ap.add_argument("--task-tags", default=DEFAULT_TASK_TAGS)
    ap.add_argument("--f8-lexicon", default=DEFAULT_F8_LEXICON,
                    help="F-8 词表（外部化唯一真源；缺则该块不输出）")
    ap.add_argument("--places", default=DEFAULT_PLACES, help="places.json（F-8p 词源）")
    ap.add_argument("--arm", default=None, help="臂标签（OFF/ON），写进 F-8 块便于两臂对照")
    ap.add_argument("--prefix-rounds", type=int, default=None,
                    help="只统计 round < N 的前缀子集（用于同窗口对照；此时准入按子集标注）")
    args = ap.parse_args(argv)

    if not os.path.exists(args.log):
        print(f"[FAIL] 日志不存在: {args.log}", file=sys.stderr)
        return 2
    recs, parse = read_run(args.log)
    subset_note = None
    if args.prefix_rounds is not None:
        n0 = len(recs)
        recs = [r for r in recs if (r.get("round") is None) or int(r.get("round")) < args.prefix_rounds]
        subset_note = {"prefix_rounds": args.prefix_rounds, "records_before": n0, "records_after": len(recs),
                       "note": "前缀子集：只含 round < prefix_rounds；准入判据按子集说明，不与完整批的 meta.events 比较"}
    msgs = extract_messages(recs)
    if not msgs:
        print("[FAIL] 日志中没有 MSG_DM/MSG_PUBLIC/MSG_GROUP 消息事件", file=sys.stderr)
        return 2

    lexicon = load_lines(args.lexicon) if os.path.exists(args.lexicon) else []
    tmpl_raw = load_lines(args.templates) if os.path.exists(args.templates) else []
    templates = [re.compile(t) for t in tmpl_raw if not t.startswith("#")]
    names, pinfo = load_personas(args.personas)

    def load_words(path: str) -> List[str]:
        if not os.path.exists(path):
            return []
        return [ln.strip() for ln in open(path, encoding="utf-8")
                if ln.strip() and not ln.strip().startswith("#")]

    emotion: Dict[str, int] = {}
    for ln in load_words(args.emotion):
        parts = ln.split()
        if len(parts) >= 2:
            try:
                emotion[" ".join(parts[1:])] = int(parts[0])
            except ValueError:
                continue
    repair_words = load_words(args.repair)
    timeref_words = load_words(args.timeref)
    task_tags = load_words(args.task_tags)
    extra = {
        "events": recs,
        "emotion": emotion, "repair": repair_words, "timeref": timeref_words,
        "task_tags": task_tags,
        "emotion_sha": sha256_file(args.emotion) if os.path.exists(args.emotion) else None,
        "repair_sha": sha256_file(args.repair) if os.path.exists(args.repair) else None,
        "timeref_sha": sha256_file(args.timeref) if os.path.exists(args.timeref) else None,
        "task_tags_sha": sha256_file(args.task_tags) if os.path.exists(args.task_tags) else None,
    }
    f8_inputs = None
    if args.f8_lexicon and os.path.exists(args.f8_lexicon):
        f8_inputs, _ = load_f8_inputs(args.f8_lexicon, args.places)
        extra["f8"] = f8_inputs
        extra["arm"] = args.arm
    meta = json.load(open(args.meta, encoding="utf-8")) if args.meta and os.path.exists(args.meta) else None

    chain = check_chain(recs)
    res: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "log": os.path.abspath(args.log),
            "run_sha256": sha256_file(args.log),
            "meta": os.path.abspath(args.meta) if args.meta else None,
            "meta_sha256": sha256_file(args.meta) if args.meta and os.path.exists(args.meta) else None,
            "script": os.path.abspath(__file__),
            "script_sha256": sha256_file(os.path.abspath(__file__)),
            "lexicon": {"path": os.path.abspath(args.lexicon),
                        "sha256": sha256_file(args.lexicon) if os.path.exists(args.lexicon) else None,
                        "n": len(lexicon)},
            "templates": {"path": os.path.abspath(args.templates),
                          "sha256": sha256_file(args.templates) if os.path.exists(args.templates) else None,
                          "n": len(templates)},
            "personas": pinfo,
            "f_lexicons": {k: v for k, v in extra.items() if k.endswith("_sha")},
            "f8_lexicon": ({"path": f8_inputs["lexicon"]["path"], "sha256": f8_inputs["lexicon"]["sha256"],
                            "version": f8_inputs["lexicon"]["version"]} if f8_inputs else None),
            "f8_places": ({"path": f8_inputs["places"]["path"], "sha256": f8_inputs["places"]["sha256"],
                           "n": len(f8_inputs["places"]["id2name"])} if f8_inputs else None),
            "log_parse": parse,
            "subset": subset_note,
            "rounds_max": (max((r.get("round") or 0) for r in recs) + 1) if recs else None,
            "seed": next((int((r.get("payload") or {}).get("seed")) for r in recs
                          if r.get("type") == "WORLD_INIT"), None),
            "chain": chain,
        },
    }
    res.update(compute(msgs, lexicon, templates, names, extra))
    res["llm"] = compute_llm(recs, len(msgs))
    res["admission"] = admission_check(meta, recs, msgs, parse, chain, res["L_wording"])

    txt = json.dumps(res, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    md = to_markdown(res, args.log)
    if args.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8") as f:
            f.write(txt + "\n")
    if args.out_md:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
        with open(args.out_md, "w", encoding="utf-8") as f:
            f.write(md + "\n")
    if not args.out_json:
        print(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True))
    summary = {
        "messages": res["meta"]["n_messages"],
        "threads": res["meta"]["n_threads"],
        "thread_schema": res["meta"]["thread_schema"],
        "v0_reply_pointer_rate": res["S-4_reply_pointer_coverage"]["rate"],
        "v0_single_msg_thread_ratio": res["S-2_thread_scale"]["single_msg_thread_ratio"],
        "v0_agent_id_leak_rate": res["L_wording"]["L-8_agent_id_leak_rate"],
        "admission": res["admission"]["verdict"],
        "out_json": args.out_json, "out_md": args.out_md,
    }
    if res.get("F-8_scene_anchor"):
        g = res["F-8_scene_anchor"]
        summary["F-8"] = {"arm": g.get("arm"), "total": "%d/%d" % (g["F-8"]["num"], g["F-8"]["den"]),
                          "F-8t": "%d/%d" % (g["F-8t_time"]["num"], g["F-8t_time"]["den"]),
                          "F-8p": "%d/%d" % (g["F-8p_place"]["num"], g["F-8p_place"]["den"]),
                          "F-8a": ("not_applicable" if g["F-8a_activity"].get("status") == "not_applicable"
                                   else "%d/%d" % (g["F-8a_activity"]["num"], g["F-8a_activity"]["den"])),
                          "lexicon_sha256": g["lexicon"]["sha256"]}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
