"""涌现层指标（D 类，`metrics.emergence`，07 §1 / 08 §4.3–4.8）。

只读日志、纯函数、确定性；`llm_judged_metric_count == 0`（拒绝 LLM 判定输入）。
社区发现：确定性贪心模块度（主）+ 连通分量/k-core（基线对照）。
"""

from __future__ import annotations

from math import log as _ln, sqrt as _sqrt

from .folds import affinity, agents, alive_agents, familiarity, relation_weights
from .params import EmergenceParams, DEFAULT_PARAMS


# ─────────────────────────── 关系网络 ───────────────────────────

def _directed_edges(records, wmap=None) -> dict:
    wmap = wmap if wmap is not None else relation_weights(records)
    return wmap


def relation_metrics(records, params: EmergenceParams) -> dict:
    wmap = relation_weights(records)
    nodes = agents(records)
    alive = set(alive_agents(records))
    # 有向边（按 dim 汇总存在性）
    directed: set[tuple] = set()
    strong: set[tuple] = set()
    weak: set[tuple] = set()
    for (a, b, dim), v in wmap.items():
        if a is None or b is None or a == b:
            continue
        directed.add((a, b))
        if abs(v) >= params.epsilon_strong:
            strong.add((a, b))
        if abs(v) >= params.epsilon:
            weak.add((a, b))

    # 互惠（dim 维度聚合：双向都存在即计）
    undirected = {tuple(sorted(e)) for e in directed}
    recip_pairs = {p for p in undirected if (p[0], p[1]) in directed and (p[1], p[0]) in directed}
    reciprocity = round(len(recip_pairs) / len(undirected), 6) if undirected else 0.0

    # 全序 tie-break 的 PageRank（G_rel，无向对称权重 = max 双向 affinity）
    pr = _pagerank(nodes, wmap, params)

    # 建边/衰减（以 seq 序时间线判定跨阈）
    formation, decay = _tie_flux(records, params)

    out_deg: dict[str, int] = {}
    for (a, b) in directed:
        out_deg[a] = out_deg.get(a, 0) + 1
    mean_degree = round(sum(out_deg.values()) / len(nodes), 6) if nodes else 0.0
    isolation = len([n for n in nodes if out_deg.get(n, 0) == 0 and
                     not any(e[1] == n for e in directed)])

    return {
        "n_nodes": len(nodes),
        "n_directed_edges": len(directed),
        "n_weak_edges": len(weak),
        "n_strong_edges": len(strong),
        "reciprocity": reciprocity,
        "tie_formation_rate": formation,
        "tie_decay_rate": decay,
        "mean_degree": mean_degree,
        "isolation_rate": round(isolation / len(nodes), 6) if nodes else 0.0,
        "pagerank_top": pr,
    }


def _tie_flux(records, params: EmergenceParams) -> tuple:
    """建边/衰减：跨 ε_strong 的升/降次数 / alive_count。"""
    prev: dict[tuple, float] = {}
    prev_strong: set[tuple] = set()
    formation = 0
    decay = 0
    for r in sorted(records, key=lambda x: x["seq"]):
        if r["type"] != "RELATION_CHANGE":
            continue
        p = r.get("payload") or {}
        if p.get("after") is None:
            continue
        key = (p.get("from"), p.get("to"), p.get("dim"))
        after = abs(float(p["after"]))
        was_strong = key in prev_strong
        now_strong = after >= params.epsilon_strong
        if now_strong and not was_strong:
            formation += 1
            prev_strong.add(key)
        elif not now_strong and was_strong and after < params.epsilon:
            decay += 1
            prev_strong.discard(key)
        prev[key] = after
    n = max(1, len(set(a for (a, b, d) in prev) | set(b for (a, b, d) in prev)))
    return record_div(formation, n), record_div(decay, n)


def record_div(a: int, b: int) -> float:
    return round(a / b, 6) if b else 0.0


def _pagerank(nodes: list[str], wmap: dict, params: EmergenceParams) -> list[dict]:
    """确定性 PageRank（无向对称权重；节点按 agent_id 升序；固定 K 次迭代）。"""
    if not nodes:
        return []
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    # 对称权重：max(affinity(a,b), affinity(b,a))
    adj = [[0.0] * n for _ in range(n)]
    for (a, b, dim), v in wmap.items():
        if a not in idx or b not in idx or a == b:
            continue
        w = abs(float(v))
        i, j = idx[a], idx[b]
        adj[i][j] = max(adj[i][j], w)
        adj[j][i] = max(adj[j][i], w)
    out_w = [sum(row) for row in adj]
    r = [1.0 / n] * n
    d = params.pagerank_d
    for _ in range(params.pagerank_k):
        nr = [(1.0 - d) / n] * n
        for i in range(n):
            if out_w[i] == 0:
                # 悬挂节点均分
                share = d * r[i] / n
                for j in range(n):
                    nr[j] += share
            else:
                for j in range(n):
                    if adj[i][j] > 0:
                        nr[j] += d * r[i] * adj[i][j] / out_w[i]
        r = nr
    order = sorted(range(n), key=lambda i: (-r[i], nodes[i]))
    rank = {i: k + 1 for k, i in enumerate(order)}
    return [{"agent_id": nodes[i], "score": round(r[i], 6), "rank": rank[i]}
            for i in sorted(range(n), key=lambda i: nodes[i])]


# ─────────────────────────── 圈层 / 社区 ───────────────────────────

def _sym_graph(records) -> tuple:
    wmap = relation_weights(records)
    nodes = agents(records)
    edges: dict[tuple, float] = {}
    for (a, b, dim), v in wmap.items():
        if a not in nodes or b not in nodes or a == b:
            continue
        key = tuple(sorted((a, b)))
        edges[key] = max(edges.get(key, 0.0), abs(float(v)))
    return nodes, edges


def community_metrics(records, params: EmergenceParams) -> dict:
    nodes, edges = _sym_graph(records)
    labels = _greedy_modularity(nodes, edges)
    groups: dict[int, list] = {}
    for node, lab in labels.items():
        groups.setdefault(lab, []).append(node)
    comms = sorted((sorted(v) for v in groups.values()), key=lambda g: (-len(g), g))
    q = _modularity(nodes, edges, labels)
    comps = _connected_components(nodes, edges)
    return {
        "n_communities": len(comms),
        "community_sizes": sorted((len(c) for c in comms), reverse=True),
        "modularity_q": round(q, 6),
        "communities": comms,
        "n_connected_components": len(comps),
        "isolation_rate": round(
            len([n for n in nodes if not any(n in e for e in edges)]) / len(nodes), 6
        ) if nodes else 0.0,
    }


def _connected_components(nodes, edges):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b) in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    groups: dict[str, list] = {}
    for n in nodes:
        groups.setdefault(find(n), []).append(n)
    return sorted((sorted(v) for v in groups.values()), key=lambda g: (-len(g), g))


def _modularity(nodes, edges, labels) -> float:
    m = sum(edges.values())
    if m <= 0:
        return 0.0
    deg: dict[str, float] = {n: 0.0 for n in nodes}
    for (a, b), w in edges.items():
        deg[a] += w
        deg[b] += w
    from collections import defaultdict
    comm_w = defaultdict(float)
    for (a, b), w in edges.items():
        if labels.get(a) == labels.get(b):
            comm_w[labels[a]] += w
    comm_deg = defaultdict(float)
    for n in nodes:
        comm_deg[labels[n]] += deg[n]
    q = 0.0
    for c in set(labels.values()):
        q += comm_w.get(c, 0.0) / m - (comm_deg.get(c, 0.0) / (2 * m)) ** 2
    return q


def _greedy_modularity(nodes, edges) -> dict:
    """确定性贪心模块度（从单节点出发，反复合并增益最大的社区对）。

    全序 tie-break：增益相同取 (min_label, max_label) 字典序最小者。
    """
    labels = {n: i for i, n in enumerate(sorted(nodes))}
    if not edges:
        return labels

    def q_of(lab):
        return _modularity(nodes, edges, lab)

    improved = True
    cur_q = q_of(labels)
    while improved and len(set(labels.values())) > 1:
        improved = False
        best = None
        best_q = cur_q
        comms = sorted(set(labels.values()))
        for i in range(len(comms)):
            for j in range(i + 1, len(comms)):
                ci, cj = comms[i], comms[j]
                cand = dict(labels)
                for n in cand:
                    if cand[n] == cj:
                        cand[n] = ci
                q = q_of(cand)
                if q > best_q + 1e-12:
                    best_q = q
                    best = cand
        if best is not None:
            labels = best
            cur_q = best_q
            improved = True
    # 重新编号为连续 id（按成员字典序）
    groups = {}
    for n in sorted(nodes):
        groups.setdefault(labels[n], []).append(n)
    ordered = sorted(groups.values(), key=lambda g: g)
    remap = {}
    for k, g in enumerate(ordered):
        for n in g:
            remap[n] = k
    return remap


# ─────────────────────────── 标签 / 观点 ───────────────────────────

def tag_metrics(records, params: EmergenceParams) -> dict:
    freq: dict[str, int] = {}
    valve: dict[str, list] = {}
    emitters: dict[str, set] = {}
    for r in records:
        if r["type"] != "TAG_EMITTED":
            continue
        p = r.get("payload") or {}
        tag = p.get("tag")
        if tag is None:
            continue
        freq[tag] = freq.get(tag, 0) + 1
        if p.get("valence") is not None:
            valve.setdefault(tag, []).append(int(p["valence"]))
        emitters.setdefault(tag, set()).add(p.get("agent_id"))
    total = sum(freq.values())
    alive = len(alive_agents(records)) or 1
    tags = {}
    for tag in sorted(freq):
        share = freq[tag] / total if total else 0.0
        tags[tag] = {
            "freq": freq[tag],
            "share": round(share, 6),
            "adoption": round(len(emitters.get(tag, ())) / alive, 6),
            "valence_mean": round(sum(valve.get(tag, [0])) / len(valve[tag]), 6)
            if valve.get(tag) else 0.0,
        }
    shares = [t["share"] for t in tags.values()]
    entropy = 0.0
    for s in shares:
        if s > 0:
            entropy -= s * _ln(s)
    hhi = round(sum(s * s for s in shares), 6)
    return {
        "n_tags": len(freq),
        "freq_total": total,
        "entropy": round(entropy, 6),
        "hhi": hhi,
        "by_tag": tags,
    }


# ─────────────────────────── 规范 ───────────────────────────

def norm_metrics(records, params: EmergenceParams) -> dict:
    proposed = [r for r in records if r["type"] == "NORM_PROPOSED"]
    adopted = [r for r in records if r["type"] == "NORM_ADOPTED"]
    violated = [r for r in records if r["type"] == "NORM_VIOLATED"]
    alive = len(alive_agents(records)) or 1
    adopters = set()
    for r in adopted:
        for a in ((r.get("payload") or {}).get("adopters") or []):
            adopters.add(a)
    coverage = round(len(adopters) / alive, 6) if alive else 0.0
    n_adopted = len(adopted)
    violation_rate = round(len(violated) / (n_adopted * alive), 6) if n_adopted else 0.0
    return {
        "n_norms_proposed": len(proposed),
        "n_norms_adopted": n_adopted,
        "n_norms_violated": len(violated),
        "adoption_success_rate": round(n_adopted / len(proposed), 6) if proposed else 0.0,
        "norm_coverage": coverage,
        "norm_violation_rate": violation_rate,
    }


# ─────────────────────────── 职业 / 身份 ───────────────────────────

def role_metrics(records, params: EmergenceParams) -> dict:
    changes = [r for r in records if r["type"] == "ROLE_CHANGE"]
    current: dict[str, str] = {}
    transition: dict[str, dict] = {}
    for r in sorted(changes, key=lambda x: x["seq"]):
        p = r.get("payload") or {}
        aid = p.get("agent_id")
        frm, to = p.get("from_role"), p.get("to_role")
        if frm is not None and to is not None:
            transition.setdefault(frm, {})
            transition[frm][to] = transition[frm].get(to, 0) + 1
        if to is not None:
            current[aid] = to
    alive = len(alive_agents(records)) or 1
    dist: dict[str, int] = {}
    for role in current.values():
        dist[role] = dist.get(role, 0) + 1
    total = sum(dist.values())
    entropy = 0.0
    for v in dist.values():
        p = v / total
        if p > 0:
            entropy -= p * _ln(p)
    switch_rate = round(len(changes) / alive, 6) if alive else 0.0
    return {
        "n_role_changes": len(changes),
        "switch_rate": switch_rate,
        "role_entropy": round(entropy, 6),
        "role_distribution": {k: dist[k] for k in sorted(dist)},
        "transition_matrix": {k: {kk: transition[k][kk] for kk in sorted(transition[k])}
                              for k in sorted(transition)},
    }


# ─────────────────────────── 传播级联 ───────────────────────────

def cascade_metrics(records, params: EmergenceParams) -> dict:
    """种子事件 → 自主传播（07 §2 / 08 §4.4）。"""
    seq_to_round = {int(r["seq"]): int(r["round"]) for r in records}
    obs = {}
    for r in records:
        if r["type"] == "OBSERVATION":
            p = r.get("payload") or {}
            tgt = p.get("target_event_seq")
            if tgt is not None:
                obs.setdefault(int(tgt), set()).add((p.get("observer"), int(r["seq"])))
    # msg refs: msg seq -> refs（refs 可为 int 事件 seq，或 str msg_id——08 R4；两者都解析为 seq）
    msg_id_to_seq = {}
    for r in records:
        if r["type"] in ("MSG_PUBLIC", "MSG_DM", "MSG_GROUP"):
            p = r.get("payload") or {}
            if p.get("msg_id") is not None:
                msg_id_to_seq[str(p["msg_id"])] = int(r["seq"])
    msg_refs = {}
    msg_owner = {}
    for r in records:
        if r["type"] in ("MSG_PUBLIC", "MSG_DM", "MSG_GROUP"):
            p = r.get("payload") or {}
            resolved = set()
            for x in (p.get("refs") or []):
                if isinstance(x, bool):
                    continue
                if isinstance(x, int):
                    resolved.add(int(x))
                else:
                    s = msg_id_to_seq.get(str(x))
                    if s is not None:
                        resolved.add(s)
            msg_refs[int(r["seq"])] = resolved
            msg_owner[int(r["seq"])] = p.get("from") or p.get("agent_id")

    seeds = [r for r in records if r["type"] == "SEED_EVENT"]
    results = {}
    for s in seeds:
        sid = (s.get("payload") or {}).get("seed_id", "seed@%d" % int(s["seq"]))
        results[sid] = _cascade_one(s, obs, msg_refs, msg_owner, seq_to_round, records, params)
    return results


def _cascade_one(seed, obs, msg_refs, msg_owner, seq_to_round, records, params) -> dict:
    seed_seq = int(seed["seq"])
    # 从 seed 出发，沿「OBSERVATION 锚点」与「msg.refs」反向扩散
    # 边 u->v：存在 OBSERVATION(observer=v, target=u) 或 msg(v).refs ∋ u 的 msg_id
    # 简化：以事件 seq 为节点，建立被引用关系
    children: dict[int, set] = {}
    for tgt, observers in obs.items():
        for (who, obs_seq) in observers:
            children.setdefault(tgt, set()).add(obs_seq)
    for mseq, refs in msg_refs.items():
        for r in refs:
            children.setdefault(r, set()).add(mseq)

    # BFS
    from collections import deque
    dist = {seed_seq: 0}
    q = deque([seed_seq])
    while q:
        u = q.popleft()
        for v in sorted(children.get(u, ())):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    # 参与 agent
    involved = set()
    for node in dist:
        if node == seed_seq:
            who = (seed.get("payload") or {}).get("injected_by")
            if who:
                involved.add(who)
        else:
            who = msg_owner.get(node)
            if who:
                involved.add(who)
        # observation 的观察者
        for (ob, obs_seq) in obs.get(node, ()):
            if obs_seq in dist:
                involved.add(ob)
    involved = {w for w in involved if w}
    alive = len(alive_agents(records)) or 1
    depth = max(dist.values()) if dist else 0
    # breadth = 各层级节点数最大值
    level_count: dict[int, int] = {}
    for node, d in dist.items():
        level_count[d] = level_count.get(d, 0) + 1
    breadth = max(level_count.values()) if level_count else 0
    # R0 = 传播者平均出度
    spreaders = [n for n in dist if children.get(n)]
    r0 = round(sum(len(children.get(n, ())) for n in spreaders) / len(spreaders), 6) if spreaders else 0.0
    return {
        "seed_id": seed_seq,
        "cascade_size": len(dist),
        "depth": depth,
        "breadth": breadth,
        "R0": r0,
        "reach_ratio": round(len(involved) / alive, 6) if alive else 0.0,
        "n_agents_reached": len(involved),
    }


# ─────────────────────────── 汇总 ───────────────────────────

def emergence_metrics(records, params: EmergenceParams | None = None) -> dict:
    params = params or DEFAULT_PARAMS.emergence
    return {
        "relation": relation_metrics(records, params),
        "community": community_metrics(records, params),
        "tag": tag_metrics(records, params),
        "norm": norm_metrics(records, params),
        "role": role_metrics(records, params),
        "cascade": cascade_metrics(records, params),
        "observer_injection_count": sum(1 for r in records if r["type"] == "SEED_EVENT"),
        "llm_judged_metric_count": 0,
    }


__all__ = [
    "emergence_metrics", "relation_metrics", "community_metrics", "tag_metrics",
    "norm_metrics", "role_metrics", "cascade_metrics",
]
