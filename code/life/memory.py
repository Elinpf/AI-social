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

    def read_body(self, ref: str) -> str:
        return self._resolve(ref, ".txt").read_text(encoding="utf-8")

    def read_embed(self, ref: str) -> list[float] | None:
        """Return the frozen vector, or **None** if absent (persist_vec off / missing).

        `None` is an explicit signal to the retrieval call site to degrade
        (lexical/recomputed) and mark `vec_available=false` — never a silent failure.
        """
        p = self._resolve(ref, ".vec")
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

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
        body_ref, embed_ref = self.side.write(self.agent_id, mem_id, text, vec)
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
        self._next_seq = max(self._next_seq, int(mem_id.rsplit("-", 1)[-1]) + 1)
        if node.kind == "observation" and not node.reflected:
            self._unreflected_importance += node.importance
        return node

    # ---- three-factor retrieval (06 §3.4) ---------------------------------
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
        scored: list[tuple[MemoryNode, float]] = []
        degraded = False
        for node in self.nodes.values():
            recency = decay ** max(0, now_tick - node.last_access)
            importance = node.importance / 10.0
            if node.embed:
                relevance = cosine(q, node.embed)
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
