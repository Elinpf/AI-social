"""v2 社会面板指标（`metrics.social.*`，D 类）——T105（T101 社会半侧）。

口径权威：`v2/02-social-v2.md §5`、`v2/evidence/_prep_t95_metrics_spec.md`；
事件字段权威：`v1.1/08-engine-stats-extension.md`（v2 登记：MSG_*、GROUP_CREATED、NORM_*、
VOTE_CAST、PUBLIC_REACTION、OFFER_*/CONTRACT_* 等）——**不臆造字段**。

四个块：
  - `network`      沟通图 G_comm / 组织图 G_org 的结构指标
  - `group_heat`   公开板 / 群聊热度与三通道份额
  - `issues`       议题/舆论（TAG_EMITTED 聚合 + PUBLIC_REACTION + 声誉）
  - `institutions` 组织/规范/契约/投票存量与漏斗

硬要求：**全 D 类**、纯函数折叠、只读日志、`llm_calls==0`、`llm_judged_metric_count==0`；
F 类（respect/affection 等）走 `social_soft`（单列、出门禁）。两次重算字节相等
（规范 JSON：键排序 + 浮点 round(...,6) + 全序 tie-break）。
"""

from __future__ import annotations

from math import log as _ln

from .econ import gini
from .emergence import _pagerank
from .folds import agents, alive_agents
from .params import DEFAULT_PARAMS


# ─────────────────────────── 通用 ───────────────────────────

def _msg_events(records, types):
    return [r for r in records if r["type"] in types]


def _sender(r):
    p = r.get("payload") or {}
    return p.get("from")


def _owner_map(records):
    """msg_id -> sender（仅 MSG_*）。"""
    m = {}
    for r in records:
        if r["type"] in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            p = r.get("payload") or {}
            if p.get("msg_id"):
                m[p["msg_id"]] = p.get("from")
    return m


def _group_members(records):
    """group_id -> sorted(members)（GROUP_CREATED；默认不可变）。"""
    g = {}
    for r in records:
        if r["type"] == "GROUP_CREATED":
            p = r.get("payload") or {}
            g[p.get("group_id")] = sorted(p.get("members") or [])
    return g


def _comm_edges(records):
    """沟通图有向边：{(a,b): count}（DM from→to；GROUP from→成员；PUBLIC 引用闭包 from→引用者）。"""
    edges: dict[tuple, int] = {}
    members = _group_members(records)
    owner = _owner_map(records)

    def add(a, b):
        if a and b and a != b:
            edges[(a, b)] = edges.get((a, b), 0) + 1

    for r in records:
        t = r["type"]
        p = r.get("payload") or {}
        if t == "MSG_DM":
            add(p.get("from"), p.get("to"))
        elif t == "MSG_GROUP":
            gid = p.get("group_id")
            mem = members.get(gid, [])
            frm = p.get("from")
            if mem:
                for m in mem:
                    add(frm, m)
            elif p.get("to"):
                add(frm, p.get("to"))
        elif t == "MSG_PUBLIC":
            pass  # PUBLIC 通过 refs 贡献边（见下）
    # PUBLIC 被引用 → 引用者
    for r in records:
        if r["type"] in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            p = r.get("payload") or {}
            by = p.get("from")
            for ref in (p.get("refs") or []):
                src = owner.get(ref)
                if src:
                    add(src, by)
    return {k: edges[k] for k in sorted(edges)}


def _msg_type_counts(records):
    c = {"DM": 0, "PUBLIC": 0, "GROUP": 0}
    for r in records:
        if r["type"] == "MSG_DM":
            c["DM"] += 1
        elif r["type"] == "MSG_PUBLIC":
            c["PUBLIC"] += 1
        elif r["type"] == "MSG_GROUP":
            c["GROUP"] += 1
    return c


# ─────────────────────────── network ───────────────────────────

def _network(records, params) -> dict:
    # 图节点 = 全部出现过的 Agent（确定性；使 density/degree 定义在自身节点集上成立）
    nodes = sorted(agents(records))
    edges = _comm_edges(records)
    n = len(nodes)
    undirected = {tuple(sorted(k)) for k in edges}
    recip = {p for p in undirected if (p[0], p[1]) in edges and (p[1], p[0]) in edges}
    outdeg: dict[str, int] = {}
    for (a, b) in edges:
        outdeg[a] = outdeg.get(a, 0) + 1

    # PageRank over G_comm（复用 emergence._pagerank 的无向对称风格；构造对称权重）
    wmap = {}
    for (a, b), w in edges.items():
        wmap[(a, b, "comm")] = float(w)
        wmap[(b, a, "comm")] = float(w)
    pr = _pagerank(nodes, wmap, params)

    groups = _group_members(records)
    org_sizes = sorted(len(v) for v in groups.values())
    member_groups: dict[str, int] = {}
    for gid, mem in groups.items():
        for m in mem:
            member_groups[m] = member_groups.get(m, 0) + 1
    org_overlap = sum(1 for m, k in member_groups.items() if k > 1)

    # cross_group_edge_ratio：跨群连接占比（仅当消息带 group 归属时）
    return {
        "n_nodes": n,
        "comm_directed_edges": len(edges),
        "comm_undirected_edges": len(undirected),
        "comm_density": round(len(undirected) / (n * (n - 1) / 2), 6) if n > 1 else 0.0,
        "comm_degree_mean": round(sum(outdeg.values()) / n, 6) if n else 0.0,
        "comm_reciprocity": round(len(recip) / len(undirected), 6) if undirected else 0.0,
        "comm_pagerank_topK": pr[:10],
        "n_groups": len(groups),
        "org_size_dist": org_sizes,
        "org_overlap_agents": org_overlap,
        "channel_counts": _msg_type_counts(records),
    }


# ─────────────────────────── group_heat ───────────────────────────

def _group_heat(records, params) -> dict:
    alive = len(alive_agents(records)) or 1
    tc = _msg_type_counts(records)
    members = _group_members(records)
    per_group_msgs: dict[str, int] = {}
    per_group_parts: dict[str, set] = {}
    for r in records:
        if r["type"] == "MSG_GROUP":
            p = r.get("payload") or {}
            gid = p.get("group_id")
            if gid is None:
                continue
            per_group_msgs[gid] = per_group_msgs.get(gid, 0) + 1
            per_group_parts.setdefault(gid, set()).add(p.get("from"))
    per_group = {}
    for gid in sorted(per_group_msgs):
        cnt = per_group_msgs[gid]
        parts = len(per_group_parts.get(gid, ()))
        n_mem = len(members.get(gid, [])) or parts or 1
        per_group[gid] = {
            "msg_count": cnt,
            "participants": parts,
            "msgs_per_member": round(cnt / n_mem, 6),
        }
    heat_vals = [per_group[g]["msg_count"] for g in per_group]
    total = sum(tc.values())
    # DROPPED / INTENT_REJECTED（配额/去重）
    dropped_quota = sum(1 for r in records if r["type"] == "DROPPED"
                        and (r.get("payload") or {}).get("reason") in ("quota", "dup"))
    intent_rej_quota = sum(1 for r in records if r["type"] == "INTENT_REJECTED"
                           and (r.get("payload") or {}).get("reason") in ("quota", "quota_agent"))
    attempted = total + dropped_quota
    return {
        "n_msg_dm": tc["DM"], "n_msg_public": tc["PUBLIC"], "n_msg_group": tc["GROUP"],
        "public_post_rate": round(tc["PUBLIC"] / alive, 6),
        "group_msg_rate": round(tc["GROUP"] / alive, 6),
        "active_groups": len([g for g in per_group_msgs]),
        "per_group": per_group,
        "heat_gini": gini(heat_vals),
        "public_vs_group_vs_dm_ratio": {
            "public": round(tc["PUBLIC"] / total, 6) if total else 0.0,
            "group": round(tc["GROUP"] / total, 6) if total else 0.0,
            "dm": round(tc["DM"] / total, 6) if total else 0.0,
        },
        "dropped_quota": dropped_quota,
        "intent_rejected_quota": intent_rej_quota,
        "spam_drop_rate": round(dropped_quota / attempted, 6) if attempted else 0.0,
    }


# ─────────────────────────── issues ───────────────────────────

def _issues(records, params) -> dict:
    alive = len(alive_agents(records)) or 1
    freq: dict[str, int] = {}
    emitters: dict[str, set] = {}
    valences: dict[str, list] = {}
    first: dict[str, int] = {}
    last: dict[str, int] = {}
    peak: dict[str, tuple] = {}
    places: dict[str, set] = {}
    groups: dict[str, set] = {}
    for r in records:
        if r["type"] != "TAG_EMITTED":
            continue
        p = r.get("payload") or {}
        tag = p.get("tag")
        if tag is None:
            continue
        f = (p.get("source_msg_id") or "")
        freq[tag] = freq.get(tag, 0) + 1
        emitters.setdefault(tag, set()).add(p.get("agent_id"))
        if p.get("valence") is not None:
            valences.setdefault(tag, []).append(int(p["valence"]))
        rd = int(r["round"])
        first[tag] = min(first.get(tag, rd), rd)
        last[tag] = max(last.get(tag, rd), rd)
        if p.get("place"):
            places.setdefault(tag, set()).add(p["place"])
    # peak（按 round 计数）
    per_round: dict[tuple, int] = {}
    for r in records:
        if r["type"] == "TAG_EMITTED":
            p = r.get("payload") or {}
            if p.get("tag") is not None:
                k = (p["tag"], int(r["round"]))
                per_round[k] = per_round.get(k, 0) + 1
    for (tag, rd), c in per_round.items():
        cur = peak.get(tag)
        if cur is None or c > cur[0] or (c == cur[0] and rd < cur[1]):
            peak[tag] = (c, rd)
    total = sum(freq.values())
    tags = {}
    for tag in sorted(freq):
        share = freq[tag] / total if total else 0.0
        tags[tag] = {
            "freq": freq[tag],
            "share": round(share, 6),
            "adoption": round(len(emitters.get(tag, ())) / alive, 6),
            "valence_mean": round(sum(valences.get(tag, [0])) / len(valences[tag]), 6)
            if valences.get(tag) else 0.0,
            "lifespan": last.get(tag, 0) - first.get(tag, 0),
            "peak_freq": peak.get(tag, (0, 0))[0],
            "peak_round": peak.get(tag, (0, 0))[1] if tag in peak else None,
            "n_places": len(places.get(tag, ())),
            "participants": len(emitters.get(tag, ())),
        }
    shares = [t["share"] for t in tags.values()]
    entropy = 0.0
    for s in shares:
        if s > 0:
            entropy -= s * _ln(s)
    # reactions（仅 POLICY 允许的 boycott 落事件；其余派生暂不落）
    reactions: dict[str, int] = {}
    boycott_pairs = []
    for r in records:
        if r["type"] == "PUBLIC_REACTION":
            p = r.get("payload") or {}
            k = str(p.get("kind"))
            reactions[k] = reactions.get(k, 0) + 1
            if k == "boycott":
                tgt = p.get("target") or {}
                boycott_pairs.append([p.get("agent_id"), tgt.get("kind"), tgt.get("ref")])
    boycott_pairs.sort(key=lambda x: [str(v) for v in x])
    return {
        "n_topics": len(freq),
        "freq_total": total,
        "entropy": round(entropy, 6),
        "hhi": round(sum(s * s for s in shares), 6),
        "by_tag": tags,
        "reaction_counts": {k: reactions[k] for k in sorted(reactions)},
        "boycott_pairs": boycott_pairs,
    }


# ─────────────────────────── institutions ───────────────────────────

def _institutions(records, params) -> dict:
    groups = _group_members(records)
    alive_set = set(alive_agents(records))
    # 组织类型：按 group_id 去重（GROUP_CREATED 可能重复/幂等）
    gid_kind = {}
    for r in records:
        if r["type"] == "GROUP_CREATED":
            p = r.get("payload") or {}
            gid_kind[p.get("group_id")] = str(p.get("kind", "chat"))
    kinds: dict[str, int] = {}
    for k in gid_kind.values():
        kinds[k] = kinds.get(k, 0) + 1
    norm_prop = [r for r in records if r["type"] == "NORM_PROPOSED"]
    norm_adopt = [r for r in records if r["type"] == "NORM_ADOPTED"]
    norm_viol = [r for r in records if r["type"] == "NORM_VIOLATED"]
    adopters = set()
    for r in norm_adopt:
        for a in ((r.get("payload") or {}).get("adopters") or []):
            adopters.add(a)
    alive = len(alive_set) or 1
    # 契约
    cc = [r for r in records if r["type"] == "CONTRACT_CREATED"]
    by_kind: dict[str, int] = {}
    for r in cc:
        k = str((r.get("payload") or {}).get("kind", "?"))
        by_kind[k] = by_kind.get(k, 0) + 1
    fulfilled = sum(1 for r in records if r["type"] == "CONTRACT_FULFILLED")
    violated = sum(1 for r in records if r["type"] == "CONTRACT_VIOLATED")
    expired = sum(1 for r in records if r["type"] == "CONTRACT_EXPIRED")
    n_cc = len(cc)
    # 发行决策 / 公共品（预留经济半侧字段，缺失即 0；不臆造）
    votes = sum(1 for r in records if r["type"] == "VOTE_CAST")
    return {
        "n_groups": len(groups),
        "group_kinds": {k: kinds[k] for k in sorted(kinds)},
        "norm_proposed": len(norm_prop),
        "norm_adopted": len(norm_adopt),
        "norm_violated": len(norm_viol),
        "adoption_success_rate": round(len(norm_adopt) / len(norm_prop), 6) if norm_prop else 0.0,
        "norm_coverage": round(len(adopters & alive_set) / alive, 6),
        "n_contracts": n_cc,
        "contract_kinds": {k: by_kind[k] for k in sorted(by_kind)},
        "contract_fulfilled": fulfilled,
        "contract_violated": violated,
        "contract_expired": expired,
        "contract_fulfillment_rate": round(fulfilled / n_cc, 6) if n_cc else 0.0,
        "employment_contracts": by_kind.get("EMPLOYMENT", 0),
        "loan_contracts": by_kind.get("LOAN", 0),
        "n_votes": votes,
    }


# ─────────────────────────── 汇总 ───────────────────────────

def social_metrics(records, params=None) -> dict:
    params = params or DEFAULT_PARAMS.emergence
    return {
        "network": _network(records, params),
        "group_heat": _group_heat(records, params),
        "issues": _issues(records, params),
        "institutions": _institutions(records, params),
        "llm_judged_metric_count": 0,
    }


def social_soft(records) -> dict:
    """F 类：仅读冻结 LLM_JUDGMENT（respect/affection），单列、出门禁。"""
    from .census import soft_judgment_counts
    soft = soft_judgment_counts(records)
    dec = soft["decisions_by_dimension"]
    return {
        "basis": "F",
        "source": "frozen_llm",
        "respect": dec.get("respect_score", {}),
        "affection": dec.get("affection_score", {}),
        "contains_llm_judgment": soft["contains_llm_judgment"],
        "frozen_ref": soft["frozen_ref"],
    }


__all__ = ["social_metrics", "social_soft"]
