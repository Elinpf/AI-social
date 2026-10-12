"""M2 — memory stream (06 §3).

Implements the Generative Agents memory stream *structure* (translated to our
deterministic, log-anchored world):
  * `MemoryNode`      — type/importance/keywords/embedding reference + recency
  * three-factor retrieval: recency * importance * relevance (weights configurable)
  * total order tie-break (score desc, last_access desc, mem_id asc)  [06 §3.4]
  * reflection trigger by accumulated importance >= theta_reflect      [06 §3.5]

Determinism & "no bypass" discipline:
  * Bodies and embeddings live in **side storage** (agent-private); the main
    ledger only stores `body_ref` / `embed_ref` (06 §3.2, AR-C4).
  * The local store is a *cache rebuilt from the log* (`sync_from_refs`), never
    an authoritative writer. Writes/retrievals are emitted as Intent
    (`INTENT.MEMORY`) and become events only after the arbiter accepts them.
  * Embeddings are computed once with a **frozen** model and stored; replay never
    recomputes them (08 §5.4, C4).

GA is Apache-2.0; `AssociativeMemory` is an adapted reimplementation (see NOTICE).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Protocol

from .constants import (
    IMPORTANCE_MAX, IMPORTANCE_MIN, MEMORY_KINDS, RETRIEVAL_DEFAULTS, R_MAX_PER_WEEK, THETA_REFLECT,
)
from .ports import MemoryRef
from .util import sha256_hex

try:  # optional vectorized relevance (T264-adjacent perf, T265-approved ②); off if absent
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None

# Default ON (Leader-approved ②, `d2f9007`), with a fallback to the scalar path.
#
# ⚠️ RISK / RECALIBRATION: the only observable risk of the numpy path is a
#    changed *tie order* — pairwise summation differs from Python's sequential
#    `sum` at the ULP level, and exact ties are broken by (last_access, mem_id).
#    This was pressure-tested with **duplicate vectors** in
#    `life/tests/test_t265_memory_perf_equiv.py`. If anyone changes the sort key,
#    the retrieval precision, or the embedding, **re-run that test** (and the
#    engine `state_hash`/replay parity) before trusting the numpy path again.
#    A cheap revert is `USE_NUMPY_RELEVANCE = False` (keeps ①/④).
USE_NUMPY_RELEVANCE = _np is not None


# ---- embedding model (frozen, offline, deterministic) ------------------------
class EmbeddingModel(Protocol):
    version: str
    dim: int

    def embed(self, text: str) -> list[float]: ...


def load_embedding_version(path: str | Path | None = None) -> str:
    """Read the frozen embedding id from `config/engine_version.json` (single source).

    Strict: missing file / missing key -> hard error (T41/R2 discipline; no silent
    fallback, so the id can never drift from the config).
    """
    p = Path(path) if path else (Path(__file__).resolve().parents[1] / "config" /
                                 "engine_version.json")
    if not p.exists():
        raise RuntimeError(f"embedding 单一来源缺失：{p}（不得静默回退）")
    data = json.loads(p.read_text(encoding="utf-8"))
    model = (data.get("embedding") or {}).get("model")
    if not model:
        raise RuntimeError(f"engine_version.json 缺少 embedding.model：{p}")
    return str(model)


class HashEmbeddingModel:
    """Deterministic embedding (frozen id recorded in `engine_version`).

    Leader (T48) ruled the embedding is a **deterministic lexical-relevance**
    approximation (`frozen://lexical-relevance-v1`) — lexical/bag-of-words, NOT
    semantic (paraphrases do not match). Replay never recomputes embeddings: the
    selected `mem_id`s are logged in `MEMORY_RETRIEVE` (freeze layer guarantees it).
    """

    version = load_embedding_version()
    dim = 64

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _tokenize(text):
            h = sha256_hex(tok)
            idx = int(h[:8], 16) % self.dim
            sign = 1.0 if int(h[8:10], 16) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def _tokenize(text: str) -> list[str]:
    out, cur = [], []
    for ch in text:
        if ch.isalnum() or "\u4e00" <= ch <= "\u9fff":
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = sum(a[i] * a[i] for i in range(n)) ** 0.5
    nb = sum(b[i] * b[i] for i in range(n)) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    # map [-1,1] -> [0,1] so relevance is 0..1 like 06 §3.4
    return (dot / (na * nb) + 1.0) / 2.0


# ---- side storage ------------------------------------------------------------
class SideStore:
    """Agent-private append-only side storage: memory bodies + frozen embeddings.

    Layout (06 §3.2): side/mem/<agent_id>/<mem_id>.txt  and  .../<mem_id>.vec
    """

    def __init__(self, root: str | Path, persist_vec: bool | None = None) -> None:
        self.root = Path(root)
        # T228：关掉 `.vec` 落盘（默认 True=行为不变）。persist_vec=None -> 读 policy
        # （config/policy.json `life.memory.persist_vec` / env `N50_VEC`）。
        if persist_vec is None:
            from . import policy
            persist_vec = policy.persist_vec_enabled()
        self.persist_vec = bool(persist_vec)
        # T268: in-memory object caches so all nodes sharing a ref share ONE
        # str / list object (cuts retained RSS from O(#nodes) to O(#unique sources)).
        self._body_cache: dict[str, str] = {}
        self._vec_cache: dict[str, list] = {}

    def _body_path(self, agent_id: str, mem_id: str) -> Path:
        return self.root / "mem" / agent_id / f"{mem_id}.txt"

    def _vec_path(self, agent_id: str, mem_id: str) -> Path:
        return self.root / "mem" / agent_id / f"{mem_id}.vec"

    @staticmethod
    def body_ref(agent_id: str, mem_id: str) -> str:
        return f"side://mem/{agent_id}/{mem_id}.txt"

    @staticmethod
    def embed_ref(agent_id: str, mem_id: str) -> str:
        return f"side://mem/{agent_id}/{mem_id}.vec"

    def write(self, agent_id: str, mem_id: str, text: str, vec: list[float]) -> tuple[str, str]:
        bp = self._body_path(agent_id, mem_id)
        bp.parent.mkdir(parents=True, exist_ok=True)
        bp.write_text(text, encoding="utf-8")
        if self.persist_vec:
            self._vec_path(agent_id, mem_id).write_text(
                json.dumps([round(v, 9) for v in vec]), encoding="utf-8")
        return self.body_ref(agent_id, mem_id), self.embed_ref(agent_id, mem_id)

    # ---- T268: shared immutable source hub ---------------------------------
    # "each agent keeps its own copy" -> "one shared immutable source + a per-agent
    # pointer". Bodies are content-addressed by sha256(text); the per-agent
    # `mem_id` (and the MEMORY_WRITE event fields) stay unchanged — only `body_ref`
    # now points at the shared blob, so N observers of one source event share ONE
    # disk file and ONE in-memory str/list object (see read caches below).
    def _src_path(self, digest: str, suffix: str) -> Path:
        return self.root / "src" / f"{digest}{suffix}"

    @staticmethod
    def shared_body_ref(digest: str) -> str:
        return f"side://src/{digest}.txt"

    @staticmethod
    def shared_embed_ref(digest: str) -> str:
        return f"side://src/{digest}.vec"

    def write_shared(self, text: str, vec: list[float]) -> tuple[str, str]:
        """Write the body once to a content-addressed blob; return shared refs."""
        digest = sha256_hex(text)
        bp = self._src_path(digest, ".txt")
        if not bp.exists():
            bp.parent.mkdir(parents=True, exist_ok=True)
            bp.write_text(text, encoding="utf-8")
        if self.persist_vec:
            vp = self._src_path(digest, ".vec")
            if not vp.exists():
                vp.write_text(json.dumps([round(v, 9) for v in vec]), encoding="utf-8")
        return self.shared_body_ref(digest), self.shared_embed_ref(digest)

    def read_body(self, ref: str) -> str:
        # T288: `body_ref` may be None（MEMORY_CONSOLIDATE 的派生记忆无正文）→ 空正文，
        # 节点仍在 memory_index 中、可检索，按既有 lexical 降级路径计分（不抛、不静默）。
        if ref is None:
            return ""
        cached = self._body_cache.get(ref)
        if cached is not None:
            return cached
        text = self._resolve(ref, ".txt").read_text(encoding="utf-8")
        self._body_cache[ref] = text
        return text

    def read_embed(self, ref: str) -> list[float] | None:
        """Return the frozen vector, or **None** if absent (persist_vec off / missing).

        `None` is an explicit signal to the retrieval call site to degrade
        (lexical/recomputed) and mark `vec_available=false` — never a silent failure.
        """
        # T288: `embed_ref` may be None（派生记忆无向量）→ 同样按 None 降级。
        if ref is None:
            return None
        if ref in self._vec_cache:
            return self._vec_cache[ref]
        p = self._resolve(ref, ".vec")
        if not p.exists():
            return None
        vec = json.loads(p.read_text(encoding="utf-8"))
        self._vec_cache[ref] = vec
        return vec

    def _resolve(self, ref: str, suffix: str) -> Path:
        # ref form: side://mem/<agent>/<mem>.txt|.vec
        rel = ref.split("side://", 1)[1]
        return self.root / rel

    # ---- T234: narrative body side storage (IF-7 `NARRATIVE.body_ref` writer) ----
    # 与记忆同处一个 side root（`<root>/narrative/<agent>/<nid>.txt`），**只补 writer**，
    # 路径与 `life/agent.py` 的 `body_ref = side://narrative/<agent>/<nid>.txt` **一致**。
    # 开关走 T228 分档体系（`policy.narrative_persist_enabled`）：**关时不写**（不落文件）。
    def _narrative_path(self, agent_id: str, narrative_id: str) -> Path:
        return self.root / "narrative" / agent_id / f"{narrative_id}.txt"

    @staticmethod
    def narrative_ref(agent_id: str, narrative_id: str) -> str:
        """叙事正文的 side 引用（单一来源；`NARRATIVE.body_ref` 即此值）。"""
        return f"side://narrative/{agent_id}/{narrative_id}.txt"

    def write_narrative(self, agent_id: str, narrative_id: str, text: str) -> str:
        """写入叙事正文，返回可解析的 `body_ref`。"""
        p = self._narrative_path(agent_id, narrative_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return self.narrative_ref(agent_id, narrative_id)

    def read_narrative(self, ref: str) -> str:
        """按 `side://narrative/<agent>/<nid>.txt` 读回正文（供导出/S4）。"""
        rel = ref.split("side://", 1)[1]
        return (self.root / rel).read_text(encoding="utf-8")

    # ---- T247: SKILL_OUTPUT 正文 side storage（`SKILL_OUTPUT.output_ref` writer）----
    # 与 `life/settlement.py` 的 `output_ref = f"side://skill/{aid}/{skill_id}"` **一字对齐**
    # （无扩展名）。开关走 T228 分档体系（`policy.skill_persist_enabled`）：**关时不写**。
    def _skill_path(self, agent_id: str, skill_id: str) -> Path:
        return self.root / "skill" / agent_id / f"{skill_id}"

    @staticmethod
    def skill_ref(agent_id: str, skill_id: str) -> str:
        """技能正文的 side 引用（单一来源；`SKILL_OUTPUT.output_ref` 即此值）。"""
        return f"side://skill/{agent_id}/{skill_id}"

    def write_skill(self, agent_id: str, skill_id: str, text: str) -> str:
        """写入技能产出正文，返回可解析的 `output_ref`。"""
        p = self._skill_path(agent_id, skill_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return self.skill_ref(agent_id, skill_id)

    def read_skill(self, ref: str) -> str:
        """按 `side://skill/<agent>/<skill_id>` 读回正文（供导出/S2 roundtrip）。"""
        rel = ref.split("side://", 1)[1]
        return (self.root / rel).read_text(encoding="utf-8")


# ---- memory node & stream ----------------------------------------------------
@dataclass
class MemoryNode:
    mem_id: str
    agent_id: str
    kind: str
    text: str
    importance: int
    day: int
    slot: str
    embed: list[float]
    refs: list[str] = field(default_factory=list)
    subject: str | None = None
    body_ref: str = ""
    embed_ref: str = ""
    source_event_seq: int | None = None
    last_access: int = 0
    access_count: int = 0
    reflected: bool = False

    @property
    def keywords(self) -> list[str]:
        return _tokenize(self.text)[:8]


class AssociativeMemory:
    def __init__(self, agent_id: str, embedding: EmbeddingModel, side: SideStore,
                 params: dict | None = None) -> None:
        self.agent_id = agent_id
        self.embedding = embedding
        self.side = side
        p = dict(RETRIEVAL_DEFAULTS)
        if params:
            p.update(params)
        self.params = p
        self.nodes: dict[str, MemoryNode] = {}
        self._next_seq = 0
        self._unreflected_importance = 0
        self._reflections_by_week: dict[int, int] = {}
        # perf caches (T265-approved ①②④). None of these change the ranking:
        #  _norm_cache   ① avoids recomputing an unchanged node-vector norm
        #  _rel_cache    ④ avoids recomputing relevance for the same (mem_id, query)
        #  _vec_rows     ② optional numpy batch dot over the same float64 values
        self._norm_cache: dict[str, float] = {}
        self._rel_cache: dict[tuple[str, str], float] = {}
        self._vec_ids: list[str] = []
        self._vec_rows: list[list[float]] = []
        self._vec_pos: dict[str, int] = {}
        self._mat = None

    # ---- rebuild cache from the (authoritative) log refs ------------------
    def sync_from_refs(self, refs: Iterable[MemoryRef]) -> None:
        for r in refs:
            if r.mem_id in self.nodes:
                node = self.nodes[r.mem_id]
                node.last_access = r.last_access
                node.access_count = r.access_count
                continue
            self._load_ref(r)
        # keep the seq counter ahead of anything seen in the log
        for mem_id in self.nodes:
            tail = mem_id.rsplit("-", 1)[-1]
            if tail.isdigit():
                self._next_seq = max(self._next_seq, int(tail) + 1)

    def _load_ref(self, r: MemoryRef) -> MemoryNode:
        try:
            text = self.side.read_body(r.body_ref)
            vec = self.side.read_embed(r.embed_ref)
        except FileNotFoundError:
            text, vec = "", []
        vec = vec or []
        node = MemoryNode(
            mem_id=r.mem_id, agent_id=self.agent_id, kind=r.kind, text=text,
            importance=r.importance, day=r.day, slot=r.slot, embed=vec,
            subject=r.subject, body_ref=r.body_ref, embed_ref=r.embed_ref,
            source_event_seq=r.source_event_seq, last_access=r.last_access,
            access_count=r.access_count,
        )
        self.nodes[r.mem_id] = node
        self._register(node)
        return node

    # ---- writes (prepare payload -> arbiter -> commit locally) ------------
    def next_mem_id(self) -> str:
        return f"M-{self.agent_id}-{self._next_seq:06d}"

    def prepare_write(self, kind: str, text: str, importance: int, day: int, slot: str,
                      tick: int, subject: str | None = None, refs: list[str] | None = None,
                      source_event_seq: int | None = None) -> dict:
        """Write body+embedding to side storage; return the MEMORY_WRITE payload."""
        if kind not in MEMORY_KINDS:
            raise ValueError(f"bad memory kind: {kind}")
        importance = max(IMPORTANCE_MIN, min(IMPORTANCE_MAX, int(importance)))
        mem_id = self.next_mem_id()
        vec = self.embedding.embed(text)
        # T268: content-addressed shared source; mem_id stays per-agent (log unchanged
        # apart from body_ref now pointing at the shared blob).
        body_ref, embed_ref = self.side.write_shared(text, vec)
        return {
            "op": "write",
            "mem_id": mem_id,
            "kind": kind,
            "importance": importance,
            "day": day,
            "slot": slot,
            "tick": tick,
            "subject": subject,
            "body_ref": body_ref,
            "embed_ref": embed_ref,
            "refs": list(refs or []),
            "source_event_seq": source_event_seq,
        }

    def commit_write(self, payload: dict) -> MemoryNode:
        """Called only after the arbiter accepted the MEMORY_WRITE intent."""
        mem_id = payload["mem_id"]
        if mem_id in self.nodes:
            return self.nodes[mem_id]
        vec = self.side.read_embed(payload["embed_ref"]) or []
        node = MemoryNode(
            mem_id=mem_id, agent_id=self.agent_id, kind=payload["kind"], text="",
            importance=payload["importance"], day=payload["day"], slot=payload["slot"],
            embed=vec, subject=payload.get("subject"), body_ref=payload["body_ref"],
            embed_ref=payload["embed_ref"], source_event_seq=payload.get("source_event_seq"),
            refs=list(payload.get("refs", [])), last_access=payload.get("tick", 0),
        )
        try:
            node.text = self.side.read_body(payload["body_ref"])
        except FileNotFoundError:
            node.text = ""
        self.nodes[mem_id] = node
        self._register(node)
        self._next_seq = max(self._next_seq, int(mem_id.rsplit("-", 1)[-1]) + 1)
        if node.kind == "observation" and not node.reflected:
            self._unreflected_importance += node.importance
        return node

    # ---- three-factor retrieval (06 §3.4) ---------------------------------
    # ---- perf helpers (T265-approved ①/②/④; ranking-preserving) -----------
    def _register(self, node: MemoryNode) -> None:
        """Index a node's frozen embedding for the optional numpy batch path."""
        emb = node.embed
        if emb and node.mem_id not in self._vec_pos:
            self._vec_pos[node.mem_id] = len(self._vec_ids)
            self._vec_ids.append(node.mem_id)
            self._vec_rows.append(emb)
            self._mat = None

    def _node_norm(self, node: MemoryNode, n: int | None = None) -> float:
        """① Cached L2 norm of an immutable node vector (recomputed at most once)."""
        v = self._norm_cache.get(node.mem_id)
        if v is None:
            b = node.embed
            m = len(b) if n is None else min(n, len(b))
            v = sum(b[i] * b[i] for i in range(m)) ** 0.5
            self._norm_cache[node.mem_id] = v
        return v

    def _relevance(self, node: MemoryNode, q: list[float], qn: float,
                   q_digest: str) -> float:
        """Scalar path: byte-for-byte the same arithmetic as `cosine(q, node.embed)`."""
        key = (node.mem_id, q_digest)
        cached = self._rel_cache.get(key)
        if cached is not None:
            return cached
        b = node.embed
        n = min(len(q), len(b))
        dot = sum(q[i] * b[i] for i in range(n))
        na = sum(q[i] * q[i] for i in range(n)) ** 0.5
        nb = sum(b[i] * b[i] for i in range(n)) ** 0.5
        val = 0.0 if (na == 0 or nb == 0) else (dot / (na * nb) + 1.0) / 2.0
        self._rel_cache[key] = val
        return val

    def _batched_relevance(self, q: list[float], qn: float) -> dict[str, float]:
        """② Optional numpy batch dot over the same float64 values.

        Only active when `USE_NUMPY_RELEVANCE`. Falls back to the scalar path on
        any shape mismatch, so it can never change *which* nodes are scored.
        """
        if not USE_NUMPY_RELEVANCE or not self._vec_ids:
            return {}
        if self._mat is None:
            try:
                self._mat = _np.asarray(self._vec_rows, dtype=_np.float64)
            except Exception:  # pragma: no cover - ragged rows -> scalar path
                return {}
        if self._mat.ndim != 2 or self._mat.shape[1] != len(q):
            return {}
        dots = self._mat @ _np.asarray(q, dtype=_np.float64)
        norms = _np.asarray([self._node_norm(self.nodes[i]) for i in self._vec_ids],
                            dtype=_np.float64)
        denom = qn * norms
        with _np.errstate(divide="ignore", invalid="ignore"):
            rel = _np.where(denom == 0.0, 0.0, (dots / denom + 1.0) / 2.0)
        return {mid: float(rel[i]) for i, mid in enumerate(self._vec_ids)}

    def score_and_rank(self, query_text: str, now_tick: int, top_k: int | None = None,
                       weights: dict | None = None) -> tuple[list[tuple[MemoryNode, float]], dict]:
        w = {"w_rec": self.params["w_rec"], "w_imp": self.params["w_imp"],
             "w_rel": self.params["w_rel"]}
        if weights:
            w.update(weights)
        top_k = int(top_k if top_k is not None else self.params["top_k"])
        decay = self.params["decay"]
        q = self.embedding.embed(query_text)
        q_tokens = set(_tokenize(query_text))
        qn = sum(v * v for v in q) ** 0.5          # ① query norm computed once
        q_digest = sha256_hex(query_text)          # ④ cache key component
        batched = self._batched_relevance(q, qn)   # ② optional vectorized relevance
        scored: list[tuple[MemoryNode, float]] = []
        degraded = False
        for node in self.nodes.values():
            recency = decay ** max(0, now_tick - node.last_access)
            importance = node.importance / 10.0
            if node.embed:
                relevance = batched.get(node.mem_id)
                if relevance is None:
                    relevance = self._relevance(node, q, qn, q_digest)
            else:
                # T228 降级：无向量 → 词面重叠（lexical），并显式标记（不静默）
                degraded = True
                nt = set(_tokenize(node.text))
                relevance = (len(q_tokens & nt) / len(q_tokens)) if q_tokens else 0.0
            s = w["w_rec"] * recency + w["w_imp"] * importance + w["w_rel"] * relevance
            scored.append((node, s))
        # total order tie-break: score desc, last_access desc, mem_id asc
        scored.sort(key=lambda t: (-t[1], -t[0].last_access, t[0].mem_id))
        debug = {"weights": w, "top_k": top_k, "decay": decay,
                 "tie_order": ["score_desc", "last_access_desc", "mem_id_asc"],
                 # T228：检索降级标记（additive，进 MEMORY_RETRIEVE payload）
                 "vec_available": not degraded,
                 "retrieval_mode": "lexical" if degraded else "vector"}
        return scored[:top_k], debug

    def touch(self, mem_ids: Iterable[str], now_tick: int) -> None:
        """Mirror what apply_event(MEMORY_RETRIEVE) does on the kernel side."""
        for mid in mem_ids:
            node = self.nodes.get(mid)
            if node:
                node.last_access = now_tick
                node.access_count += 1

    # ---- reflection trigger (06 §3.5) -------------------------------------
    def reflection_due(self, week: int, force_weekly: bool = False) -> bool:
        if self._reflections_by_week.get(week, 0) >= R_MAX_PER_WEEK:
            return False
        if force_weekly:
            return True
        return self._unreflected_importance >= THETA_REFLECT

    def take_reflection_input(self) -> tuple[list[str], int]:
        """Return (source observation ids, importance_sum) and reset the accumulator."""
        src = [n.mem_id for n in self.nodes.values()
               if n.kind == "observation" and not n.reflected]
        for n in self.nodes.values():
            if n.kind == "observation":
                n.reflected = True
        total = self._unreflected_importance
        self._unreflected_importance = 0
        return src, total

    def note_reflection(self, week: int) -> None:
        self._reflections_by_week[week] = self._reflections_by_week.get(week, 0) + 1

    def summary_for_prompt(self, mem_ids: Iterable[str], max_chars: int = 800) -> str:
        parts = []
        for mid in mem_ids:
            n = self.nodes.get(mid)
            if n:
                parts.append(f"[{n.kind}|imp{n.importance}] {n.text}")
        text = "\n".join(parts)
        return text[:max_chars]
