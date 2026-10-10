"""日志折叠基础（D 类，供 emergence / census / wellbeing 复用）。

全部只读、纯函数、确定性（全序 tie-break）。
"""

from __future__ import annotations


def relation_weights(records) -> dict:
    """折叠 RELATION_CHANGE：{(from,to,dim): last_after}（按 seq 升序取最后一笔）。"""
    w: dict[tuple, float] = {}
    for r in sorted(records, key=lambda x: x["seq"]):
        if r["type"] != "RELATION_CHANGE":
            continue
        p = r.get("payload") or {}
        if p.get("after") is None:
            continue
        w[(p.get("from"), p.get("to"), p.get("dim"))] = float(p["after"])
    return w


def affinity(wmap: dict, a: str, b: str) -> float:
    """a→b 的 affinity 边权（缺省 0）。"""
    return float(wmap.get((a, b, "affinity"), 0.0))


def familiarity(wmap: dict, a: str, b: str) -> float:
    """熟悉度代理：双向 affinity 的最大值（07 §1.2 折叠口径）。"""
    return max(affinity(wmap, a, b), affinity(wmap, b, a))


def skill_levels(records) -> dict:
    """折叠 SKILL_LEVEL_UP：{(agent,skill): last_level_after}。"""
    lv: dict[tuple, float] = {}
    for r in sorted(records, key=lambda x: x["seq"]):
        p = r.get("payload") or {}
        if r["type"] == "SKILL_LEVEL_UP" and p.get("level_after") is not None:
            lv[(p.get("agent_id"), p.get("skill_id"))] = float(p["level_after"])
        elif r["type"] == "SKILL_PRACTICE" and p.get("skill_before") is not None:
            lv.setdefault((p.get("agent_id"), p.get("skill_id")), float(p["skill_before"]))
    return lv


def same_skill(lv: dict, a: str, b: str) -> bool:
    """a,b 是否共享同一技能（任一方在该技能上有等级记录）。"""
    return bool(skills_of(lv, a) & skills_of(lv, b))


def _iter_ids(v):
    """统一取 str id：标量 str 或 str 列表（如 `OFFER_CREATED.to[]`，08 §1.2-K）皆可。"""
    if v is None:
        return
    if isinstance(v, (list, tuple, set)):
        for x in v:
            if isinstance(x, str) and x:
                yield x
    elif isinstance(v, str) and v:
        yield v


def skills_of(lv: dict, a: str) -> set:
    return {s for (ag, s) in lv if ag == a}


def agents(records) -> list[str]:
    """全部出现过的 agent（AGENT_BORN 并集，字典序）。"""
    out = set()
    for r in records:
        p = r.get("payload") or {}
        if r["type"] == "AGENT_BORN":
            out.update(_iter_ids(p.get("agent_id")))
        for k in ("from", "to", "a", "b", "agent_id", "observer", "buyer", "seller"):
            out.update(_iter_ids(p.get(k)))
        for k in ("participants", "parties", "adopters"):
            out.update(_iter_ids(p.get(k)))
    return sorted(x for x in out if x)


def alive_agents(records) -> list[str]:
    dead = set()
    revived = set()
    born = set()
    for r in records:
        p = r.get("payload") or {}
        t = r["type"]
        if t == "AGENT_BORN":
            born.add(p.get("agent_id"))
        elif t == "AGENT_DIED":
            dead.add(p.get("agent_id"))
        elif t == "AGENT_REVIVED":
            revived.add(p.get("agent_id"))
    return sorted(a for a in born if a and (a not in dead or a in revived))


def distinct_agents_in(records, type_: str, *fields) -> dict:
    """type_ 事件中按字段取 distinct agent 集合。"""
    out: dict[str, set] = {}
    for r in records:
        if r["type"] != type_:
            continue
        p = r.get("payload") or {}
        for f in fields:
            for v in _iter_ids(p.get(f)):
                out.setdefault(f, set()).add(v)
    return out


def last_value_by(records, type_, key_fields, value_field):
    """通用折叠：{(key...): last value}（按 seq 升序）。"""
    out: dict[tuple, float] = {}
    for r in sorted(records, key=lambda x: x["seq"]):
        if r["type"] != type_:
            continue
        p = r.get("payload") or {}
        if p.get(value_field) is None:
            continue
        out[tuple(p.get(k) for k in key_fields)] = float(p[value_field])
    return out


__all__ = [
    "relation_weights", "affinity", "familiarity", "skill_levels", "same_skill",
    "skills_of", "agents", "alive_agents", "distinct_agents_in", "last_value_by",
]
