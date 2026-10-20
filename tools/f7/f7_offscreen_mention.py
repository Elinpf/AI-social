#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-7 越界提及/编造 统一口径复算器（零 LLM 成本，纯脚本）。

判据卡（唯一口径来源）: v2/refs/F7-offscreen-criteria.md

用法（单臂复算）:
    python3 tools/f7/f7_offscreen_mention.py \
        --log v2/evidence/run_d2_before_n16_seed42/run.jsonl \
        --out-json v2/evidence/f7_v0anchor.json

用法（两臂对照，生成对照 md）:
    python3 tools/f7/f7_offscreen_mention.py --compare \
        v2/evidence/f7_v0anchor.json v2/evidence/f7_a0.json \
        --out-md v2/evidence/f7_compare.md

可选参数:
    --personas PATH   名字表（默认 code/config/personas.json）
    --boot N          bootstrap 次数（默认 2000，种子固定 42，输出可逐字节复现）
    --seed N          bootstrap 种子（默认 42）

设计约束（与任务书一致）:
  * 同一脚本、同一名字表、同一分母定义算两臂；**脚本内不存在任何按臂名分支的硬编码**（臂名只从日志路径派生并原样回显）。
  * 不联网、不调用 LLM、不写日志；同一输入两次运行输出逐字节相等（bootstrap 种子固定）。
  * 只读 run.jsonl 与 personas.json。

退出码:
    0 成功
    2 输入不可用（日志缺失/无消息事件/名字表缺失）
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "f7-offscreen/1.0"

# ---------------------------------------------------------------- 判据常量（写死，改则换版本号）

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
PLACE_TYPES = ("PLACE_ARRIVED", "PLACE_MOVE")
PERSONA_PREFIX = "青溪镇·"

# 名字表：display_name 去前缀后的主干名（与 tools/d5/dialogue_metrics.py::load_personas 同源同算法）
# 裸 ID：P + 3 位数字，后瞻防 4 位；与 dialogue_metrics.py::AGENT_ID_RE 完全一致
AGENT_ID_RE = re.compile(r"P\d{3}(?!\d)")
# 旁白：中英文括号整段。**不设长度上限**（旧口径 PAREN_ANY_RE 限 120 字符，超长旁白会漏剔，
# 这是旧口径的一处已知缺口，见判据卡 §6）；[^）]* 天然在第一个右括号处截止，不会跨段吞正文。
PAREN_NARRATION_RE = re.compile(r"(?:（[^）]*）|\([^)]*\))")

DEFAULTS = {
    "narration": "exclude",   # exclude = 括号旁白内提及不计入（主判据）
    "identity": "names+id",   # names = 只认主干名；names+id = 主干名 + 裸 P0xx
    "channel": "all",         # all = DM+PUBLIC+GROUP
    "addressee": "exclude",   # exclude = 收件人（payload.to）不算“越界”
    "presence": "pit",        # pit = 消息 seq 时刻的位置；round_last = 同 round 最后一条位置事件（旧口径）
}

# 称呼层（P2）：token 后紧跟的呼语标点 / 前置呼语引导词（纯启发式，见判据卡 §6）
VOC_PUNCT = set("，,、！!？?啊呀呢吧——…~～")
VOC_CALL_RE = re.compile(r"(?:喂|哎|嘿|嗨|哟|唉)[，,、]?\s*$")


# ---------------------------------------------------------------- 基础工具


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_names(path: str) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """返回 {pid: 主干名} 与来源信息（含 sha256、name_table_sha256）。

    字段来源：personas[].persona_id + personas[].display_name（去「青溪镇·」前缀）。
    不做别名扩展：personas.json 无 alias 字段，硬造别名会引入不可复算的主观判断。
    """
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
    info["names"] = dict(sorted(names.items()))
    info["name_table_sha256"] = hashlib.sha256(canon(dict(sorted(names.items()))).encode("utf-8")).hexdigest()
    info["field"] = "personas[].persona_id + personas[].display_name（strip '青溪镇·'）"
    # 子串碰撞自检：任一主干名是另一主干名的子串时，子串匹配会同时命中两人，必须显式记录
    collisions = [{"inner": a, "inner_name": na, "outer": b, "outer_name": nb}
                  for a, na in names.items() for b, nb in names.items()
                  if a != b and na and na in nb]
    info["name_collision_check"] = {"ok": not collisions, "collisions": collisions}
    return names, info


def read_records(path: str) -> List[dict]:
    recs = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            recs.append(json.loads(ln))
    return recs


# ---------------------------------------------------------------- 主体


class Arm:
    def __init__(self, recs: List[dict], names: Dict[str, str], arm_label: str):
        self.names = names
        self.arm_label = arm_label
        self.msgs: List[dict] = []
        self.place_chain: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        self.round_last: Dict[Tuple[Any, str], str] = {}
        for r in recs:
            t = r.get("type")
            if t in MSG_TYPES:
                p = r.get("payload") or {}
                self.msgs.append({
                    "seq": r.get("seq"),
                    "round": r.get("round"),
                    "actor": str(r.get("actor")),
                    "event_type": t,
                    "channel": t,
                    "from": str(p.get("from") or r.get("actor")),
                    "to": str(p.get("to") or ""),
                    "body": p.get("body") or p.get("text") or "",
                    "place": p.get("place"),
                    "msg_id": p.get("msg_id"),
                })
            elif t in PLACE_TYPES:
                p = r.get("payload") or {}
                aid = p.get("agent_id")
                plc = p.get("place") or p.get("to_place")
                if aid and plc:
                    self.place_chain[str(aid)].append((r.get("seq"), plc))
                    self.round_last[(r.get("round"), str(aid))] = plc
        for aid in self.place_chain:
            self.place_chain[aid].sort()
        self.seqs_by_agent = {a: [s for s, _ in c] for a, c in self.place_chain.items()}

    def place_at(self, seq: int, aid: str) -> Optional[str]:
        c = self.place_chain.get(aid)
        if not c:
            return None
        i = bisect.bisect_right(self.seqs_by_agent[aid], seq) - 1
        return c[i][1] if i >= 0 else None

    def text_of(self, msg: dict, narration: str) -> str:
        text = msg["body"] or ""
        if narration == "exclude":
            text = PAREN_NARRATION_RE.sub("", text)
        return text

    def mentions(self, msg: dict, narration: str, identity: str) -> Dict[str, List[str]]:
        """返回 {pid: [命中的字面 token]}。token 是实际出现在正文里的字符（主干名或裸 ID），
        供称呼层判定使用（两种 token 的称呼形态不同）。"""
        text = self.text_of(msg, narration)
        me = msg["from"]
        found: Dict[str, List[str]] = defaultdict(list)
        if identity in ("names", "names+id"):
            for pid, nm in self.names.items():
                if pid != me and nm and nm in text and nm not in found[pid]:
                    found[pid].append(nm)
        if identity == "names+id":
            for pid in AGENT_ID_RE.findall(text):
                if pid != me and pid in self.names and pid not in found[pid]:
                    found[pid].append(pid)
        return dict(found)

    @staticmethod
    def is_vocative(text: str, token: str) -> bool:
        """称呼层（P2）：token 后紧跟呼语标点，或前面是呼语引导词。

        - 后接 VOC_PUNCT 之一（，、！？啊呀呢吧——…~～）⇒ 当作直接称呼；
        - 前缀（≤6 字内）以 VOC_CALL_RE 结尾 ⇒ 当作呼唤。
        这只是启发式代理，不测语气与指代，见判据卡 §6 局限。
        """
        for mt in re.finditer(re.escape(token), text):
            i, j = mt.start(), mt.end()
            if j < len(text) and text[j] in VOC_PUNCT:
                return True
            if VOC_CALL_RE.search(text[max(0, i - 6):i]):
                return True
        return False

    def evaluate(self, narration: str, identity: str, channel: str,
                 addressee: str, presence: str, vocative: str = "any") -> Dict[str, Any]:
        """返回逐臂逐变体的分子分母 + raw hits。vocative='vocative' 时只统计称呼型提及（P2）。"""
        pos_msg = elig_msg = 0
        pos_men = elig_men = 0
        n_msgs_scope = 0
        n_msgs_with_mention = 0
        uncheckable_men = 0
        raw_hits: List[Dict[str, Any]] = []
        for m in self.msgs:
            if channel == "public_group" and m["channel"] not in ("MSG_PUBLIC", "MSG_GROUP"):
                continue
            if channel == "dm_group" and m["channel"] not in ("MSG_DM", "MSG_GROUP"):
                continue
            n_msgs_scope += 1
            found = self.mentions(m, narration, identity)
            if not found:
                continue
            n_msgs_with_mention += 1
            text = self.text_of(m, narration)
            if vocative == "vocative":
                found = {p: toks for p, toks in found.items()
                         if any(self.is_vocative(text, t) for t in toks)}
                if not found:
                    continue
            base = m["place"]
            checked = 0
            off_pids: List[str] = []
            for pid in sorted(found):
                if addressee == "exclude" and m["channel"] == "MSG_DM" and pid == m["to"]:
                    continue
                if presence == "pit":
                    plc = self.place_at(m["seq"], pid)
                else:
                    plc = self.round_last.get((m["round"], pid))
                if plc is None:
                    uncheckable_men += 1
                    continue
                checked += 1
                if base and plc != base:
                    off_pids.append(pid)
            if checked == 0:
                continue
            elig_msg += 1
            elig_men += checked
            if off_pids:
                pos_msg += 1
                pos_men += 1
                raw_hits.append({
                    "seq": m["seq"],
                    "round": m["round"],
                    "channel": m["channel"],
                    "from": m["from"],
                    "to": m["to"],
                    "sender_place": base,
                    "mentioned": [{"pid": p, "name": self.names.get(p),
                                   "tokens": found[p],
                                   "vocative": any(self.is_vocative(text, t) for t in found[p]),
                                   "peer_place": (self.place_at(m["seq"], p) if presence == "pit"
                                                  else self.round_last.get((m["round"], p)))}
                                  for p in off_pids],
                    "body_excerpt": (m["body"] or "")[:160].replace("\n", " "),
                })
        return {
            "n_msgs_scope": n_msgs_scope,
            "n_msgs_with_mention": n_msgs_with_mention,
            "per_message": {"pos": pos_msg, "den": elig_msg},
            "per_mention": {"pos": pos_men, "den": elig_men},
            "uncheckable_mentions": uncheckable_men,
            "raw_hits": raw_hits,
        }


def bootstrap_ci(binary: List[int], boot: int, seed: int) -> Tuple[Optional[float], Optional[float]]:
    """对分母内的 0/1 记录做 bootstrap（有放回重采样），返回 95% 百分位区间。"""
    n = len(binary)
    if n == 0:
        return None, None
    rnd = random.Random(seed)
    rates = []
    for _ in range(boot):
        s = 0
        for _ in range(n):
            s += binary[rnd.randrange(n)]
        rates.append(s / n)
    rates.sort()
    lo = rates[int(0.025 * (boot - 1))]
    hi = rates[int(0.975 * (boot - 1))]
    return round(lo, 6), round(hi, 6)


def binary_vector(arm: Arm, narration: str, identity: str, channel: str,
                  addressee: str, presence: str, vocative: str = "any") -> List[int]:
    """复算的 0/1 向量（用于 CI；与 evaluate 同一逻辑，逐条消息一个元素）。"""
    out = []
    for m in arm.msgs:
        if channel == "public_group" and m["channel"] not in ("MSG_PUBLIC", "MSG_GROUP"):
            continue
        if channel == "dm_group" and m["channel"] not in ("MSG_DM", "MSG_GROUP"):
            continue
        found = arm.mentions(m, narration, identity)
        if not found:
            continue
        if vocative == "vocative":
            text = arm.text_of(m, narration)
            found = {p: toks for p, toks in found.items()
                     if any(arm.is_vocative(text, t) for t in toks)}
            if not found:
                continue
        base = m["place"]
        checked = 0
        off = 0
        for pid in sorted(found):
            if addressee == "exclude" and m["channel"] == "MSG_DM" and pid == m["to"]:
                continue
            plc = arm.place_at(m["seq"], pid) if presence == "pit" else arm.round_last.get((m["round"], pid))
            if plc is None:
                continue
            checked += 1
            if base and plc != base:
                off = 1
        if checked:
            out.append(off)
    return out


def legacy_compat(arm: Arm) -> Dict[str, Any]:
    """复现 tools/d5/dialogue_metrics.py::F-7a 的旧口径（用于说明 1.07% / 15.6% 的来源）。

    旧口径 = 只认主干名、旁白不剔除、含收件人、位置取「同 round 最后一条位置事件」、分母 = 全部消息。
    """
    names = arm.names
    id_by_name = {v: k for k, v in names.items() if v}
    unknown = 0
    off = 0
    n = 0
    raw = []
    for m in arm.msgs:
        n += 1
        peers = [nm for nm in names.values() if nm and nm in m["body"] and nm != names.get(m["from"])]
        if not peers:
            continue
        base = m["place"]
        checked = 0
        hit_pids = []
        for nm in peers:
            pid = id_by_name.get(nm)
            if not pid:
                continue
            plc = arm.round_last.get((m["round"], pid))
            if plc is None:
                unknown += 1
                continue
            checked += 1
            if base and plc != base:
                off += 1
                hit_pids.append(pid)
                break
        if checked == 0:
            unknown += 1
        if hit_pids:
            raw.append({
                "seq": m["seq"], "round": m["round"], "channel": m["channel"],
                "sender_place": base,
                "mentioned": [{"pid": p, "name": names.get(p),
                               "peer_place_round_last": arm.round_last.get((m["round"], p))} for p in hit_pids],
                "body_excerpt": (m["body"] or "")[:160].replace("\n", " "),
            })
    return {
        "rule": "tools/d5/dialogue_metrics.py::F-7a（主干名 / 旁白不剔除 / 含收件人 / 同 round 最后位置 / 分母=全部消息）",
        "pos": off, "den": n,
        "rate": round(off / n, 6) if n else None,
        "unknown_place_lookups": unknown,
        "raw_hits": raw,
    }


def variant_id(cfg: Dict[str, str]) -> str:
    return "nar=%s|id=%s|ch=%s|addr=%s|pres=%s" % (
        cfg["narration"], cfg["identity"], cfg["channel"], cfg["addressee"], cfg["presence"])


def build_variants(arm: Arm, boot: int, seed: int) -> List[Dict[str, Any]]:
    out = []
    for narration in ("exclude", "include"):
        for identity in ("names+id", "names"):
            for channel in ("all", "public_group", "dm_group"):
                for addressee in ("exclude", "include"):
                    for presence in ("pit", "round_last"):
                        cfg = dict(narration=narration, identity=identity, channel=channel,
                                   addressee=addressee, presence=presence)
                        ev = arm.evaluate(**cfg)
                        vec = binary_vector(arm, **cfg)
                        lo, hi = bootstrap_ci(vec, boot, seed)
                        is_primary = all(cfg[k] == DEFAULTS[k] for k in DEFAULTS)
                        out.append({
                            "variant_id": variant_id(cfg),
                            "config": cfg,
                            "primary": is_primary,
                            "n_msgs_scope": ev["n_msgs_scope"],
                            "n_msgs_with_mention": ev["n_msgs_with_mention"],
                            "per_message": {
                                "pos": ev["per_message"]["pos"], "den": ev["per_message"]["den"],
                                "rate": (round(ev["per_message"]["pos"] / ev["per_message"]["den"], 6)
                                         if ev["per_message"]["den"] else None),
                                "ci95": [lo, hi],
                            },
                            "per_mention": {
                                "pos": ev["per_mention"]["pos"], "den": ev["per_mention"]["den"],
                                "rate": (round(ev["per_mention"]["pos"] / ev["per_mention"]["den"], 6)
                                         if ev["per_mention"]["den"] else None),
                            },
                            "uncheckable_mentions": ev["uncheckable_mentions"],
                            "_raw_hits": ev["raw_hits"],
                        })
    return out


# ---------------------------------------------------------------- 对照模式


def fmt_rate(v: Optional[float]) -> str:
    return "—" if v is None else "%.2f%%" % (v * 100)


def fmt_ci(ci) -> str:
    if not ci or ci[0] is None:
        return "—"
    return "[%.2f%%, %.2f%%]" % (ci[0] * 100, ci[1] * 100)


def verdict(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """可比性裁决（全族纪律：分母差 >30% 或任一侧分母 0 ⇒ 不可比）。"""
    da, db = a["per_message"]["den"], b["per_message"]["den"]
    if da == 0 or db == 0:
        return {"comparable": False, "reason": "分母为 0（%s=%d, %s=%d）：该口径下至少一臂没有可判定样本，"
                                               "只能报事件级事实，不能报百分比" % (a["arm"], da, b["arm"], db)}
    diff = abs(da - db) / max(da, db)
    small = min(da, db)
    if diff > 0.30:
        return {"comparable": False,
                "reason": "分母差 %.1f%%（%s=%d vs %s=%d），超过 30%% 阈值" % (diff * 100, a["arm"], da, b["arm"], db),
                "denominator_diff_pct": round(diff * 100, 2)}
    if small < 30:
        return {"comparable": True, "note": "分母差 %.1f%% ≤30%%，但较小分母 %d <30：只写「X/Y 条消息」事件级事实，不写百分比"
                % (diff * 100, small), "denominator_diff_pct": round(diff * 100, 2)}
    return {"comparable": True, "note": "分母差 %.1f%% ≤30%%，可报百分比" % (diff * 100),
            "denominator_diff_pct": round(diff * 100, 2)}


def write_compare(paths: List[str], out_md: str) -> int:
    arms = [json.load(open(p, encoding="utf-8")) for p in paths]
    if len(arms) != 2:
        print("--compare 需要恰好 2 个 json", file=sys.stderr)
        return 2
    a, b = arms
    vmap_a = {v["variant_id"]: v for v in a["variants"]}
    vmap_b = {v["variant_id"]: v for v in b["variants"]}
    lines: List[str] = []
    lines.append("# F-7 越界提及 · 两臂同口径对照（脚本自动生成）\n")
    lines.append("- 脚本：`tools/f7/f7_offscreen_mention.py`（schema `%s`）" % SCHEMA_VERSION)
    lines.append("- 判据卡：`v2/refs/F7-offscreen-criteria.md`")
    lines.append("- 名字表：`%s` sha256 `%s`（n=%d，name_table_sha256 `%s`）"
                 % (a["inputs"]["personas_path"], a["inputs"]["personas_sha256"],
                    a["inputs"]["n_personas"], a["inputs"]["name_table_sha256"]))
    lines.append("- 臂 A：`%s`（%s）log sha256 `%s`" % (a["arm"], a["inputs"]["log_path"], a["inputs"]["log_sha256"]))
    lines.append("- 臂 B：`%s`（%s）log sha256 `%s`\n" % (b["arm"], b["inputs"]["log_path"], b["inputs"]["log_sha256"]))

    lines.append("## 1. 主判据（P1）读数\n")
    lines.append("P1 = 旁白剔除 · 主干名+裸ID · 全渠道 · 收件人不算越界 · 消息时刻位置（point-in-time）\n")
    lines.append("| 臂 | 可判定消息（分母） | 越界命中消息（分子） | per-message 率 | 95% CI | per-mention 率 | 不可判定提及 |")
    lines.append("|---|---|---|---|---|---|---|")
    for arm in arms:
        p = arm["primary"]
        lines.append("| %s | %d | %d | %s | %s | %s | %d |" % (
            arm["arm"], p["per_message"]["den"], p["per_message"]["pos"],
            fmt_rate(p["per_message"]["rate"]), fmt_ci(p["per_message"]["ci95"]),
            fmt_rate(p["per_mention"]["rate"]), p["uncheckable_mentions"]))
    v = verdict(a["primary"] | {"arm": a["arm"]}, b["primary"] | {"arm": b["arm"]})
    lines.append("\n**可比性裁决**：%s —— %s%s" % (
        "可比" if v["comparable"] else "**不可比**", v["reason"], ("；" + v["note"]) if v.get("note") else ""))
    lines.append("")

    lines.append("## 2. 称呼层（P2）读数——更接近「对不在场者说话」的一层\n")
    lines.append("P2 = P1 的提及集合里只保留称呼型（token 后接呼语标点，或前接 喂/哎/嘿/嗨/哟/唉）。"
                 "**启发式代理，非人工标注；与 P1 不得相加或互相代入。**\n")
    lines.append("| 臂 | 可判定消息（分母） | 越界称呼命中（分子） | per-message 率 | 95% CI | per-mention 率 | 旁白计入时 分子/分母 |")
    lines.append("|---|---|---|---|---|---|---|")
    for arm in arms:
        p = arm["vocative_layer"]
        na = p["narration_included_recheck"]["per_message"]
        lines.append("| %s | %d | %d | %s | %s | %s | %d/%d |" % (
            arm["arm"], p["per_message"]["den"], p["per_message"]["pos"],
            fmt_rate(p["per_message"]["rate"]), fmt_ci(p["per_message"]["ci95"]),
            fmt_rate(p["per_mention"]["rate"]), na["pos"], na["den"]))
    v2 = verdict(a["vocative_layer"] | {"arm": a["arm"]}, b["vocative_layer"] | {"arm": b["arm"]})
    lines.append("\n**可比性裁决（P2）**：%s —— %s%s" % (
        "可比" if v2["comparable"] else "**不可比**", v2["reason"], ("；" + v2["note"]) if v2.get("note") else ""))
    lines.append("")

    lines.append("## 3. 消息量与提及面（口径为何不成立的结构原因）\n")
    lines.append("| 臂 | 总消息 | DM | PUBLIC | GROUP | 含他人指称的消息 | 其中 DM | 其中 PUBLIC | 其中 GROUP |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for arm in arms:
        ch = arm["units"]["n_msgs_by_channel"]
        mt = arm["units"]["msgs_with_mention_by_channel"]
        lines.append("| %s | %d | %d | %d | %d | %d | %d | %d | %d |" % (
            arm["arm"], arm["units"]["n_msgs"], ch.get("MSG_DM", 0), ch.get("MSG_PUBLIC", 0),
            ch.get("MSG_GROUP", 0), sum(mt.values()), mt.get("MSG_DM", 0), mt.get("MSG_PUBLIC", 0),
            mt.get("MSG_GROUP", 0)))
    lines.append("")

    lines.append("## 4. 旧口径（legacy_compat）与 P1 的差\n")
    lines.append("| 臂 | 旧口径读数（分子/分母） | 旧口径不可判定位置查询数 | P1 读数 | P1 不可判定提及 |")
    lines.append("|---|---|---|---|---|")
    for arm in arms:
        lg = arm["legacy_compat"]
        p = arm["primary"]
        lines.append("| %s | %d/%d = %s | %d | %d/%d = %s | %d |" % (
            arm["arm"], lg["pos"], lg["den"], fmt_rate(lg["rate"]), lg["unknown_place_lookups"],
            p["per_message"]["pos"], p["per_message"]["den"], fmt_rate(p["per_message"]["rate"]),
            p["uncheckable_mentions"]))
    lines.append("")
    lines.append("> 说明：旧口径不可判定位置查询数远大于 0 时，其分子只在极小可查子集上取值、分母却是全部消息，"
                 "两个单位混用 ⇒ 该读数**不可解释**。P1 用消息时刻位置（point-in-time）把不可判定压到最小，并"
                 "把分母换成「真的有可判定提及的消息」。\n")

    keys = sorted(set(vmap_a) & set(vmap_b))
    lines.append("## 5. 全变体矩阵（%d 个变体，两臂并列）\n" % len(keys))
    lines.append("| 变体 | %s 分子/分母 | %s 率 | %s 分子/分母 | %s 率 | 分母差 | 裁决 |" % (a["arm"], a["arm"], b["arm"], b["arm"]))
    lines.append("|---|---|---|---|---|---|---|")
    for k in keys:
        va, vb = vmap_a[k], vmap_b[k]
        da, db = va["per_message"]["den"], vb["per_message"]["den"]
        diff = "—" if (da == 0 or db == 0) else "%.1f%%" % (abs(da - db) / max(da, db) * 100)
        ok = (da > 0 and db > 0 and abs(da - db) / max(da, db) <= 0.30)
        mark = "P1" if va.get("primary") else ""
        lines.append("| `%s` %s | %d/%d | %s | %d/%d | %s | %s | %s |" % (
            k, mark, va["per_message"]["pos"], da, fmt_rate(va["per_message"]["rate"]),
            vb["per_message"]["pos"], db, fmt_rate(vb["per_message"]["rate"]), diff,
            "可比" if ok else "不可比"))
    lines.append("")
    txt = "\n".join(lines) + "\n"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(txt)
    print("wrote", out_md)
    return 0


# ---------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F-7 越界提及统一口径复算器")
    ap.add_argument("--log")
    ap.add_argument("--personas", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                      "..", "..", "code", "config", "personas.json"))
    ap.add_argument("--out-json")
    ap.add_argument("--compare", nargs=2, default=None, help="两个臂 json，生成对照 md")
    ap.add_argument("--out-md")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    if args.compare:
        if not args.out_md:
            print("--compare 需要 --out-md", file=sys.stderr)
            return 2
        return write_compare(args.compare, args.out_md)
    if not args.log:
        print("需要 --log", file=sys.stderr)
        return 2

    names, pinfo = load_names(os.path.normpath(args.personas))
    if not names:
        print("名字表不可用: %s" % args.personas, file=sys.stderr)
        return 2
    recs = read_records(args.log)
    arm_label = os.path.basename(os.path.dirname(os.path.abspath(args.log))) or "arm"
    arm = Arm(recs, names, arm_label)
    if not arm.msgs:
        print("日志中无消息事件", file=sys.stderr)
        return 2

    variants = build_variants(arm, args.boot, args.seed)
    primary = next(v for v in variants if v["primary"])
    raw_hits = primary.pop("_raw_hits")
    for v in variants:
        v.pop("_raw_hits", None)

    ch_counter = Counter(m["channel"] for m in arm.msgs)
    mt_counter: Counter = Counter()
    for m in arm.msgs:
        if arm.mentions(m, DEFAULTS["narration"], DEFAULTS["identity"]):
            mt_counter[m["channel"]] += 1

    # 称呼层（P2）：同一套判据 + 只保留称呼型提及；启发式代理，单列不许与 P1 相加
    voc_ev = arm.evaluate(vocative="vocative", **DEFAULTS)
    voc_vec = binary_vector(arm, vocative="vocative", **DEFAULTS)
    voc_lo, voc_hi = bootstrap_ci(voc_vec, args.boot, args.seed)
    voc_net02 = arm.evaluate(vocative="vocative", **{**DEFAULTS, "narration": "include"})
    vocative_layer = {
        "definition_id": "P2",
        "config": {**DEFAULTS, "vocative": "vocative"},
        "rule": "P1 的提及集合里，只保留称呼型：token 后紧跟 " + "".join(sorted(VOC_PUNCT)) +
                " 之一，或前 ≤6 字以 " + VOC_CALL_RE.pattern + " 结尾",
        "n_msgs_with_mention": voc_ev["n_msgs_with_mention"],
        "per_message": {"pos": voc_ev["per_message"]["pos"], "den": voc_ev["per_message"]["den"],
                        "rate": (round(voc_ev["per_message"]["pos"] / voc_ev["per_message"]["den"], 6)
                                 if voc_ev["per_message"]["den"] else None),
                        "ci95": [voc_lo, voc_hi]},
        "per_mention": {"pos": voc_ev["per_mention"]["pos"], "den": voc_ev["per_mention"]["den"],
                        "rate": (round(voc_ev["per_mention"]["pos"] / voc_ev["per_mention"]["den"], 6)
                                 if voc_ev["per_mention"]["den"] else None)},
        "uncheckable_mentions": voc_ev["uncheckable_mentions"],
        "narration_included_recheck": {
            "per_message": {"pos": voc_net02["per_message"]["pos"], "den": voc_net02["per_message"]["den"]},
            "note": "同一 P2 在「旁白计入」下的读数，用于量化旁白隔离的影响",
        },
        "raw_hits": voc_ev["raw_hits"],
    }

    pre = {k: primary[k] for k in ("variant_id", "config", "n_msgs_scope", "n_msgs_with_mention",
                                   "per_message", "per_mention", "uncheckable_mentions")}
    out = {
        "schema_version": SCHEMA_VERSION,
        "arm": arm_label,
        "inputs": {
            "log_path": args.log,
            "log_sha256": sha256_file(args.log),
            "n_records": len(recs),
            "personas_path": os.path.normpath(args.personas),
            "personas_sha256": pinfo.get("sha256"),
            "n_personas": pinfo.get("n"),
            "name_table_sha256": pinfo.get("name_table_sha256"),
            "name_field": pinfo.get("field"),
            "name_collision_check": pinfo.get("name_collision_check"),
            "script_sha256": sha256_file(os.path.abspath(__file__)),
            "bootstrap": {"n": args.boot, "seed": args.seed, "method": "percentile-95"},
        },
        "rules": {
            "channel_scope": "MSG_DM|MSG_PUBLIC|MSG_GROUP（与 tools/d5/dialogue_metrics.py 消息类型集合一致）",
            "name_source": "code/config/personas.json → personas[].display_name 去前缀「青溪镇·」；无别名扩展",
            "name_regex": "主干名直接子串匹配（names 表见 inputs.name_table_sha256）；裸 ID 正则 " + AGENT_ID_RE.pattern,
            "narration_regex": PAREN_NARRATION_RE.pattern + "（P1 先剔除再匹配）",
            "presence_rule": "P1：该居民在消息 seq 之前最后一条 PLACE_ARRIVED/PLACE_MOVE 的 place；无任何位置事件 ⇒ 不可判定",
            "offscreen_rule": "sender payload.place ≠ 被提及者消息时刻 place ⇒ 该消息记 1 次越界命中（per-message）；"
                              "per-mention 按被提及者逐个计",
            "excluded_mentions": "DM 收件人（payload.to）不算越界（点名说话 ≠ 越界；其不在场是 DM 通道属性，不是叙事错误）",
        },
        "units": {
            "n_msgs": len(arm.msgs),
            "n_msgs_by_channel": dict(sorted(ch_counter.items())),
            "msgs_with_mention_by_channel": dict(sorted(mt_counter.items())),
        },
        "primary": pre,
        "vocative_layer": vocative_layer,
        "variants": variants,
        "legacy_compat": legacy_compat(arm),
        "raw_hits": raw_hits,
        "notes": [
            "本脚本零 LLM 成本：只读 run.jsonl 与 personas.json。",
            "bootstrap 种子固定，同输入两次运行输出逐字节相等。",
            "脚本不按臂名分支：臂名只从日志目录名派生并回显。",
            "P1（提及层）与 P2（称呼层）是两层，禁止相加或互相代入；P2 是正则启发式，非人工标注。",
        ],
    }
    txt = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            f.write(txt + "\n")
        print("wrote", args.out_json)
        print("P1: %d/%d = %s  CI %s" % (pre["per_message"]["pos"], pre["per_message"]["den"],
                                         fmt_rate(pre["per_message"]["rate"]), fmt_ci(pre["per_message"]["ci95"])))
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
