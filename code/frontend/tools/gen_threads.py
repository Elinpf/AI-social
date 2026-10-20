#!/usr/bin/env python3
"""gen_threads.py — 从真源 run.jsonl 派生「对话线程」页面数据（只读，不写世界）。

用途
    把一个（可能上百 MB 的）事件日志裁剪/聚合成页面可直接 fetch 的 threads.json：
      * 只保留对话事件 MSG_DM / MSG_PUBLIC / MSG_GROUP
      * 以及**这些消息的语境因果证据**：RELATION_CHANGE / NEED_UPDATE /
        RELATION_ENCOUNTER / GROUP_CREATED（`--keep-context`，默认开，不许关）
      * 其余事件（MEMORY_*/OBSERVATION/LLM_CALL/METABOLISM/...）一律丢弃
    被丢弃的事件**不参与任何展示字段**，页面显示的每一列都能回指到 threads.json 里
    带 seq 的原始事件（`provenance.events[].seq`）。

线程口径（真源，不在前端推断）
    D2 之后的新格式日志在 MSG_* 的 payload 里带线程字段：
        thread_id / turn_index / reply_to / participants / ctx
    本脚本只**原样搬运**这些键；日志里没有的键就是没有，页面显示「日志未记录」。
    旧格式（无 thread_id）→ 每条消息单独成一条 threads（turns=1），并标 legacy=True；
    这是**空态标记**，不是前端猜出来的线程。

用法
    cd code
    python frontend/tools/gen_threads.py \
        --log /root/t271/runs/<B>/run.jsonl \
        --meta /root/t271/runs/<B>/meta.json \
        --out frontend/sample/dialogue_<B>/threads.json

    # 只要一份最小自检（不写文件）
    python frontend/tools/gen_threads.py --log frontend/sample/run_p1_final_n20_llm.jsonl --summary

输出 schema: hitt.dialogue.threads/1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

FRONTEND = Path(__file__).resolve().parents[1]
DEFAULT_PERSONAS = FRONTEND / "data" / "personas.json"
DEFAULT_PLACES = FRONTEND / "data" / "places.json"

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
CONTEXT_TYPES = ("RELATION_CHANGE", "NEED_UPDATE", "RELATION_ENCOUNTER", "GROUP_CREATED")

SCHEMA = "hitt.dialogue.threads/1"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(p: Path) -> Any:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load_personas(p: Path) -> dict:
    raw = load_json(p)
    out = {}
    for x in raw.get("personas", []):
        out[x["persona_id"]] = {
            "name": x.get("display_name") or x["persona_id"],
            "role": x.get("role_id"),
            "age": x.get("age"),
            "speech_style": x.get("speech_style") or {},
        }
    return out


def load_places(p: Path) -> dict:
    raw = load_json(p)
    return {x["place_id"]: x.get("name_cn") or x["place_id"] for x in raw.get("places", [])}


def msg_view(rec: dict) -> dict | None:
    """把一条 MSG_* 事件摊平成页面视图；字段全部来自 payload 原文。"""
    t = rec.get("type")
    if t not in MSG_TYPES:
        return None
    pl = rec.get("payload") or {}
    body = pl.get("body")
    if body is None:                     # 长文本走 body_ref 侧存储：如实标注，不猜
        body = None
    if t == "MSG_DM":
        channel = "dm"
        sender = pl.get("from")
        to = pl.get("to")
        participants = pl.get("participants") or ([sender, to] if sender and to else [sender])
    elif t == "MSG_PUBLIC":
        channel = "public"
        sender = pl.get("author") or pl.get("from")
        to = None
        participants = pl.get("participants") or ([sender] if sender else [])
    else:                                # MSG_GROUP
        channel = "group"
        sender = pl.get("from") or pl.get("author")
        to = pl.get("group_id")
        participants = pl.get("participants") or ([sender] if sender else [])

    return {
        "seq": rec.get("seq"),
        "round": rec.get("round"),
        "type": t,
        "channel": channel,
        "msg_id": pl.get("msg_id"),
        "from": sender,
        "to": to,
        "group_id": pl.get("group_id"),
        "body": body,
        "body_ref": pl.get("body_ref"),
        # ---- D2 线程字段：原样搬运，缺就是缺 ----
        "thread_id": pl.get("thread_id"),
        "turn_index": pl.get("turn_index"),
        "reply_to": pl.get("reply_to"),
        "participants": participants,
        "ctx": pl.get("ctx"),
        # ---- 时间/地点：日志里已有的键 ----
        "day": pl.get("day"),
        "slot": pl.get("slot"),
        "place": pl.get("place") or (pl.get("group_id") or "").removeprefix("place:") or None,
        "topic": pl.get("topic"),
        "tag_hints": pl.get("tag_hints") or [],
        "refs": pl.get("refs") or [],
    }


class ContextIndex:
    """按 seq 前进的语境索引：取**该消息之前**最近一条真实记录。绝不外推。"""

    def __init__(self) -> None:
        self.relation: dict[tuple, dict] = {}   # (from,to,dim) -> latest change
        self.needs: dict[str, dict[str, dict]] = {}
        self.encounter: dict[tuple, dict] = {}
        self.groups: dict[str, dict] = {}

    def feed(self, rec: dict) -> None:
        t = rec.get("type")
        pl = rec.get("payload") or {}
        seq = rec.get("seq")
        if t == "RELATION_CHANGE":
            key = (pl.get("from"), pl.get("to"), pl.get("dim"))
            self.relation[key] = {
                "from": pl.get("from"), "to": pl.get("to"), "dim": pl.get("dim"),
                "before": pl.get("before"), "after": pl.get("after"),
                "cause": pl.get("cause"), "seq": seq, "round": rec.get("round"),
            }
        elif t == "NEED_UPDATE":
            a = pl.get("agent_id")
            dim = pl.get("dim")
            if a and dim:
                self.needs.setdefault(a, {})[dim] = {
                    "dim": dim, "before": pl.get("before"), "after": pl.get("after"),
                    "cause": pl.get("cause"), "seq": seq, "round": rec.get("round"),
                }
        elif t == "RELATION_ENCOUNTER":
            key = tuple(sorted([pl.get("a") or "", pl.get("b") or ""]))
            self.encounter[key] = {
                "a": pl.get("a"), "b": pl.get("b"), "place": pl.get("place"),
                "duration_ticks": pl.get("duration_ticks"), "seq": seq, "round": rec.get("round"),
            }
        elif t == "GROUP_CREATED":
            gid = pl.get("group_id")
            if gid:
                self.groups[gid] = {"group_id": gid, "members": pl.get("members") or [],
                                    "seq": seq, "round": pl.get("created_round")}

    def snapshot(self, m: dict) -> dict:
        """为一消息收集**已发生**的语境证据（每条带 seq，可回指原始日志）。"""
        people = [p for p in (m.get("participants") or []) if p]
        rels = []
        seen = set()
        for a in people:
            for b in people:
                if a == b:
                    continue
                for dim in ("affinity", "trust", "familiarity", "respect"):
                    r = self.relation.get((a, b, dim))
                    if r and (a, b, dim) not in seen:
                        seen.add((a, b, dim))
                        rels.append(r)
        # 只挑最新的一条 encounter（参与者两两之间）
        enc = None
        for i, a in enumerate(people):
            for b in people[i + 1:]:
                e = self.encounter.get(tuple(sorted([a, b])))
                if e and (enc is None or (e.get("seq") or 0) > (enc.get("seq") or 0)):
                    enc = e
        needs = {a: list(self.needs.get(a, {}).values()) for a in people if self.needs.get(a)}
        grp = None
        gid = m.get("group_id")
        if gid and gid in self.groups:
            grp = self.groups[gid]
        return {
            "relation": rels,
            "needs": needs,
            "encounter": enc,
            "group": grp,
            "ctx_snapshot": m.get("ctx"),      # D2 生成时快照（可能为 None）
        }


def build(log_path: Path, meta_path: Path | None, personas: dict, places: dict,
          keep_context: bool = True) -> dict:
    events = 0
    msgs: list[dict] = []
    ctx = ContextIndex()
    order: list[tuple] = []          # (seq, msg_view)
    first_round = None
    last_round = None
    provider = None

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            events += 1
            t = rec.get("type")
            rnd = rec.get("round")
            if rnd is not None:
                first_round = rnd if first_round is None else min(first_round, rnd)
                last_round = rnd if last_round is None else max(last_round, rnd)
            if t == "LLM_CALL" and provider is None:
                provider = (rec.get("payload") or {}).get("provider")
            if t in CONTEXT_TYPES:
                if keep_context:
                    ctx.feed(rec)
                continue
            mv = msg_view(rec)
            if mv is None:
                continue
            mv["context"] = ctx.snapshot(mv)
            order.append((mv["seq"], mv))
            msgs.append(mv)

    # ---- 聚合线程：有 thread_id 按其分组；否则每条单发（legacy 标记）----
    groups: dict[str, list[dict]] = {}
    threaded = 0
    legacy = 0
    for _, m in order:
        tid = m.get("thread_id")
        if tid:
            threaded += 1
            key = str(tid)
        else:
            legacy += 1
            # 旧格式 msg_id 会撞（如 D-6-0 在同一 round 被多人复用）→ 以全序 seq 为唯一键，
            # 每条旧格式消息各自成一条单发线程（不推断、不合并）
            key = f"legacy:{m.get('seq')}"
        groups.setdefault(key, []).append(m)

    threads = []
    for key, items in groups.items():
        if key.startswith("legacy:"):
            items.sort(key=lambda x: (x.get("seq") or 0))
        else:
            items.sort(key=lambda x: (
                x["turn_index"] if isinstance(x.get("turn_index"), int) else 10 ** 9,
                x.get("seq") or 0,
            ))
        is_legacy = key.startswith("legacy:")
        parts: list[str] = []
        for m in items:
            for p in (m.get("participants") or []):
                if p and p not in parts:
                    parts.append(p)
        places_ = [m.get("place") for m in items if m.get("place")]
        rounds = [m.get("round") for m in items if m.get("round") is not None]
        turns = len(items)
        threads.append({
            "thread_id": None if is_legacy else key,
            "legacy": is_legacy,
            "channel": items[0].get("channel"),
            "participants": parts,
            "place": places_[0] if places_ else None,
            "places": sorted(set(places_)),
            "start_round": min(rounds) if rounds else None,
            "end_round": max(rounds) if rounds else None,
            "turns": turns,
            "multi_turn": turns > 1,
            "messages": items,
        })

    threads.sort(key=lambda t: (
        t["start_round"] if t["start_round"] is not None else 10 ** 9,
        t["messages"][0].get("seq") or 0,
    ))

    multi = [t for t in threads if t["multi_turn"]]
    deep = [t for t in threads if t["turns"] >= 3]
    meta = {}
    if meta_path and Path(meta_path).exists():
        try:
            meta = load_json(Path(meta_path))
        except Exception as e:  # noqa: BLE001 — 元信息坏了就如实标注，不阻塞
            meta = {"_error": f"meta.json 解析失败: {e}"}

    return {
        "schema": SCHEMA,
        "generated_by": "frontend/tools/gen_threads.py",
        "generator_sha256": sha256_file(Path(__file__)),
        "source": {
            "run_jsonl": str(log_path),
            "run_sha256": sha256_file(log_path),
            "run_bytes": Path(log_path).stat().st_size,
            "events_total_in_log": events,
            "round_range": [first_round, last_round],
            "llm_provider_in_log": provider,
            "meta_json": meta or None,
            "meta_path": str(meta_path) if meta_path else None,
        },
        "prune_rule": (
            "保留 MSG_DM/MSG_PUBLIC/MSG_GROUP + 语境因果事件"
            "(RELATION_CHANGE/NEED_UPDATE/RELATION_ENCOUNTER/GROUP_CREATED)；"
            "其余事件丢弃且不参与任何展示字段"
            if keep_context else
            "保留 MSG_*；语境事件被显式关闭（--no-keep-context），展开视图将显示空态"
        ),
        "field_contract": {
            "thread_id": "D2 新格式 payload 键；旧格式缺失 ⇒ legacy=true 单发线程",
            "turn_index": "线程内序号，0=发起",
            "reply_to": "上一条 msg_id",
            "participants": "[agent_id]",
            "ctx": "{relation,mood,need,topic} 生成时快照，缺键即未记录",
        },
        "agents": personas,
        "places": places,
        "stats": {
            "messages": len(msgs),
            "threads": len(threads),
            "multi_turn_threads": len(multi),
            "threads_ge3_turns": len(deep),
            "legacy_threads": sum(1 for t in threads if t["legacy"]),
            "threaded_messages": threaded,
            "legacy_messages": legacy,
            "participants": len({p for m in msgs for p in (m.get("participants") or [])}),
            "max_turns": max((t["turns"] for t in threads), default=0),
        },
        "threads": threads,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="run.jsonl → 对话线程页面数据（只读派生）")
    ap.add_argument("--log", required=True, help="真源事件日志 run.jsonl")
    ap.add_argument("--meta", default=None, help="同目录 meta.json（provider/model/seed/sha）")
    ap.add_argument("--out", default=None, help="输出 threads.json")
    ap.add_argument("--personas", default=str(DEFAULT_PERSONAS))
    ap.add_argument("--places", default=str(DEFAULT_PLACES))
    ap.add_argument("--no-keep-context", action="store_true",
                    help="**不推荐**：丢弃语境事件（展开视图变空态）")
    ap.add_argument("--summary", action="store_true", help="只打印统计，不写文件")
    a = ap.parse_args()

    log_path = Path(a.log)
    if not log_path.exists():
        print(f"[gen_threads] 找不到日志: {log_path}", file=sys.stderr)
        return 2
    personas = load_personas(Path(a.personas))
    places = load_places(Path(a.places))
    data = build(log_path, Path(a.meta) if a.meta else None, personas, places,
                 keep_context=not a.no_keep_context)

    st = data["stats"]
    print(f"[gen_threads] events={data['source']['events_total_in_log']} "
          f"messages={st['messages']} threads={st['threads']} "
          f"multi_turn={st['multi_turn_threads']} ge3={st['threads_ge3_turns']} "
          f"legacy_msgs={st['legacy_messages']}", file=sys.stderr)
    if st["messages"] == 0:
        print("[gen_threads] 警告：日志里没有任何 MSG_* 事件 → 页面将显示空态", file=sys.stderr)

    if a.summary:
        print(json.dumps(data["stats"], ensure_ascii=False, indent=2))
        return 0
    if not a.out:
        print("[gen_threads] 需要 --out 或 --summary", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[gen_threads] wrote {out} ({out.stat().st_size} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
