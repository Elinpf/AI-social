"""F-4「误会与和解」上下文机制（**主臂：只给处境，不下笔**）。

设计口径（Leader 裁决，R6-T2）：
  * **词表层是唯一可进结论的证据层**：张力/修复一律由
    `tools/d5/dialogue_metrics.py` 的既有规则从 `body` 复算。
  * 本模块**不生成、不追加、不改写任何正文**。它只做两件事：
      ① **只读识别**：把「别人对我说过的、按词表判为负向的话」记成 pair 级
         「未了结的不愉快」（rift），并在同线程出现修复词时判为已和解、注销；
      ② **只给处境**：把「你和 X 上次那句话还没说开（约 N 回合前，话题 T）」
         作为**可感知的记忆**放进提示词上下文，并给**选项工具箱**
         （解释 / 道歉 / 岔开 / 先放着），**不给任何固定句式**；措辞由 LLM 自己产出。
  * 另有**提高发生机会**的一条干预：回复时**优先挑「有旧账的线程」**
    （`reply_priority`）。这是「相遇/回复优先级」层面的干预，不是造事件；
    报告须如实披露为「干预了回复优先级」，与「居民自发冲突」区分表述。
  * **默认关闭**（`config/dialogue_repair.json` 的 `enabled=false`，且该文件**不进**
    `engine/version.py::FINGERPRINT_FILES`）⇒ v0 / anchor 旧日志的 fingerprint 校验与
    语义**零扰动**；关闭时本模块不产出任何事件字段、不改任何提示词。

结构化可观测信号（**只做追溯，不替代词表层证据**；命名为 `dialogue_rift`，与既有
`thread_id` / `turn_index` / `ctx` 同级、只追加）：
    payload["dialogue_rift"] = {
      "v": "f4/1",
      "open": int,              # 本条消息生成时，我的未了结 rift 数
      "with": [peer_id, ...],   # 涉及的对端（升序）
      "threads": [thread_id],   # 涉及线程（升序；可追溯到具体哪条线程）
      "route": "reply_priority" | "initiate" | "reply",
      "age_rounds": [int, ...], # 各 rift 的年龄（回合）
      "prompted": bool,         # 本条是否把 rift 处境放进了提示词
    }
    只在 `enabled` 且确有未了结 rift 时出现；关闭时日志中**一条都没有**。

**不进 state_hash**：纯措辞/上下文层，不产生事件类型、不改世界态（与
`dialogue_threads.py` 同一分层约定）。

词表来源（**镜像不发明**）：`NEG_WORDS` / `REPAIR_WORDS` 是
`tools/d5/emotion_lexicon.txt`（-1 行）与 `tools/d5/repair_lexicon.txt` 的**子集镜像**；
`code/tests/test_dialogue_repair.py::test_lexicon_mirror_is_subset` 守住"不漂移"
（镜像里的每个词都必须在上游词表里；上游新增词不会自动进镜像，属已知保守方向）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")

DEFAULTS = {
    "enabled": False,             # 总开关（默认关 = v0 语义不变）
    "gripe_context": True,        # 把「未了结的不愉快」放进提示词上下文（+ 选项工具箱）
    "reply_priority": True,       # 回复时优先挑「有旧账的线程」（提高和解发生机会）
    "window_msgs": 8,             # 与 F-4 同口径：张力后 8 条同线程内出现修复词 = 和解
    "max_open": 3,                # 每个 agent 同时最多记 N 条 rift（防上下文膨胀）
    "max_age_rounds": 84,         # 超过 N 回合仍未了结 → 自然淡忘（= 一个模拟周）
    "context_max_age_rounds": 24, # 只有 N 回合内的旧账进提示词（更老的只计数不叙述）
    # T-RIFT-EVENTS（最小移植）：把 rift 的生命周期**落成事件**（RIFT_OPEN / RIFT_CLOSE），
    # 并让 `dialogue_rift` 快照带 `rift_ids`。默认 False ⇒ 不产任何新事件、不多任何键。
    # 注：另有与"DR 可分离化"相关的三项开关**不在本次移植范围**（它们属另一条线）。
    "rift_events": False,
}

#: 选项工具箱（**只给选项，不给句子**；不得含任何现成道歉句式）
TOOLBOX = "你可以解释、道个歉、岔开话题，或者先放着——怎么做由你决定。"

#: 负向情绪词镜像（子集于 tools/d5/emotion_lexicon.txt 的 -1 行）
NEG_WORDS = (
    "难过", "难受", "生气", "烦", "累", "怕", "担心", "委屈", "后悔", "失望",
    "吵", "凭什么", "你什么意思", "别这样", "算了", "倒霉", "疼", "苦",
)

#: 修复/缓和词镜像（子集于 tools/d5/repair_lexicon.txt）
REPAIR_WORDS = (
    "对不起", "抱歉", "我不是那个意思", "别生气", "别往心里去", "误会", "我错了",
    "是我不好", "没事", "不要紧", "消消气", "我理解", "我懂", "慢慢来",
)

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "dialogue_repair.json"
_cache: dict | None = None
_override: dict | None = None

# ---- T-RIFT-EVENTS（最小移植）：`RIFT_CLOSE.reason` 的**取值域**（封闭集，禁拼写/大小写变体）----
#: 三种**已知**关闭原因（由 `ingest` 的注销分支与 `_prune` 分支产生）
RIFT_CLOSE_REASONS = frozenset({"repair", "expire", "prune"})
#: 允许出现但不参与 D4-2 分子的**显式未知**值：调用点忘传 reason 时用它，**绝不默认成 `repair`**
#: （默认成 repair 会把未知关闭静默算进"和解"，直接抬高 D4-2 分子 —— 对结论有利，最危险）
RIFT_CLOSE_UNKNOWN = "unknown"
RIFT_CLOSE_REASONS_ALLOWED = RIFT_CLOSE_REASONS | {RIFT_CLOSE_UNKNOWN}

#: 开关 env（与既有 `HITT_DIALOGUE_REPAIR` 同风格）
RIFT_EVENTS_ENV = "HITT_DR_RIFT_EVENTS"

_TRUTHY = ("1", "true", "on", "yes")
_FALSEY = ("0", "false", "off", "no")


def _bool(raw, current=None) -> bool:
    """env 字符串 → bool；`raw is None` ⇒ 沿用 config 值（`current`），再缺省 False。"""
    if raw is None:
        return bool(current) if current is not None else False
    v = str(raw).strip().lower()
    if v in _TRUTHY:
        return True
    if v in _FALSEY:
        return False
    return bool(current) if current is not None else False


# ---------------------------------------------------------------- 开关/参数
def load_params(path: str | Path | None = None) -> dict:
    """读 `config/dialogue_repair.json`（缺省值 → 默认**关**）；支持 env 逃生口。

    env：`HITT_DIALOGUE_REPAIR=1|true|on` → 打开；`=0|false|off` → 关闭（消融/回退用）。
    **本文件不进 engine_version 指纹**（默认关 ⇒ v0 旧日志 fingerprint 不受影响）。
    """
    global _cache
    if _override is not None:
        return dict(_override)
    if _cache is not None and path is None:
        return dict(_cache)
    p = Path(path) if path else _CFG_PATH
    out = dict(DEFAULTS)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        if isinstance(data, dict):
            for k in out:
                if k in data:
                    out[k] = data[k]
    env = os.environ.get("HITT_DIALOGUE_REPAIR")
    if env is not None:
        out["enabled"] = env.strip().lower() in ("1", "true", "on", "yes")
    out["enabled"] = bool(out["enabled"])
    out["window_msgs"] = int(out["window_msgs"])
    out["max_open"] = int(out["max_open"])
    out["max_age_rounds"] = int(out["max_age_rounds"])
    out["context_max_age_rounds"] = int(out["context_max_age_rounds"])
    # T-RIFT-EVENTS（最小移植）：env 优先于 config
    out["rift_events"] = _bool(os.environ.get(RIFT_EVENTS_ENV), out.get("rift_events"))
    if path is None:
        _cache = dict(out)
    return out


def set_override(d: dict | None) -> None:
    """Test/ablation hook：强制参数（None 清除）。不落盘、不改指纹。"""
    global _override
    _override = dict(d) if d else None


def _cfg() -> dict:
    return load_params()


# ---------------------------------------------------------------- 只读判据
def polarity(body: str) -> int:
    """与 F-4 同口径的极性（子串包含计数；正词表不在镜像内 ⇒ 只判负向）。"""
    return -1 if any(w in (body or "") for w in NEG_WORDS) else 0


def is_gripe(body: str) -> bool:
    """这句话按词表判为负向 ⇒ 听者记一笔「不愉快」。"""
    return polarity(body) < 0


def has_repair(body: str) -> bool:
    """这句话里出现修复/缓和词 ⇒ 同线程未了结的 rift 视为和解（与 F-4 分子同规则）。"""
    return any(w in (body or "") for w in REPAIR_WORDS)


def rift_id(thread_id: str | None, msg_uid: str | None, seq: int | None = None) -> str:
    """确定性 rift id（同一事件重放恒等）。"""
    return f"R|{thread_id or '-'}|{msg_uid or seq}"


# ---------------------------------------------------------------- rift 台账（纯函数）
def ingest(rifts: dict, seen: set, events, agent_id: str, params: dict,
           round_no: int | None = None, observer=None) -> dict:
    """增量吸收可见事件 → 更新 rift 台账（**纯读日志，不写世界**）。

    * 别人对我说的、或我听到的负向话 ⇒ 记一条 rift（`with` = 说话人）；
    * 同一线程后续消息出现修复词 ⇒ 该线程内**更早**的 rift 全部注销（和解）；
    * `max_open` / `max_age_rounds` 做有界化（超龄即淡忘）。
    返回入参 `rifts`（就地更新，便于调用方持有同一 dict）。

    `observer`（T-RIFT-EVENTS 最小移植，默认 `None` ⇒ 行为逐字节不变）：
    `observer("open", rift_dict)` / `observer("close", {"rift_id", "reason": "repair"|"expire"|"prune", …})`
    —— 只在开关开时由调用方传入，用于把 rift 生命周期落成事件。
    """
    if not params.get("enabled"):
        return rifts
    msgs = [ev for ev in events
            if getattr(ev, "type", None) in MSG_TYPES and getattr(ev, "seq", None) not in seen]
    for ev in sorted(msgs, key=lambda e: int(e.seq)):
        before = set(rifts)
        ingest_one(rifts, seen, int(ev.seq), getattr(ev, "type", None),
                   getattr(ev, "payload", None) or {}, int(getattr(ev, "round", 0) or 0),
                   agent_id, params)
        if observer is not None:
            after = set(rifts)
            for rid in sorted(after - before):
                observer("open", dict(rifts[rid]))
            for rid in sorted(before - after):
                observer("close", {"rift_id": rid, "reason": "repair"})
    # 有界化：区分"超龄淡忘(expire)"与"超 max_open 截断(prune)"
    before2 = {k: dict(v) for k, v in rifts.items()}
    _prune(rifts, params, round_no)
    if observer is not None:
        age_max = int(params.get("max_age_rounds", 84))
        for rid in sorted(set(before2) - set(rifts)):
            v = before2[rid]
            expired = (round_no is not None
                       and int(round_no) - int(v.get("round", 0)) > age_max)
            _why = "expire" if expired else "prune"
            assert _why in RIFT_CLOSE_REASONS, _why      # 防拼写漂移（封闭集断言）
            observer("close", {"rift_id": rid, "reason": _why,
                               "thread_id": v.get("thread_id"), "with": v.get("with"),
                               "trigger_seq": v.get("seq"), "round": v.get("round")})
    return rifts


def ingest_one(rifts: dict, seen: set, seq: int, etype: str | None, payload: dict,
               round_no: int, agent_id: str, params: dict) -> None:
    """单条事件的台账更新（`ingest` 与 `restore()` 共用同一条规则，保证续跑等价）。"""
    if not params.get("enabled") or etype not in MSG_TYPES or seq in seen:
        return
    seen.add(int(seq))
    p = payload or {}
    author = p.get("from") or p.get("author")
    thread_id = p.get("thread_id") or f"legacy:{p.get('msg_id')}"
    body = p.get("body") or ""
    # ① 新的不愉快（只记"别人说的"，自己的话不算旧账）
    if author and author != agent_id and is_gripe(body):
        rid = rift_id(thread_id, p.get("msg_uid") or p.get("msg_id"), seq)
        rifts[rid] = {
            "rift_id": rid,
            "with": author,
            "thread_id": thread_id,
            "msg_uid": p.get("msg_uid") or p.get("msg_id"),
            "seq": int(seq),
            "round": int(round_no),
            "day": p.get("day"),
            "slot": p.get("slot"),
            "topic": p.get("topic") or (p.get("tag_hints") or [None])[0],
        }
    # ② 和解：同线程内出现修复词 ⇒ 注销**更早**的 rift（不含本条自身）
    if has_repair(body):
        for rid in [k for k, v in rifts.items()
                    if v["thread_id"] == thread_id and v["seq"] < int(seq)]:
            rifts.pop(rid, None)


def prune(rifts: dict, params: dict, round_no: int | None = None) -> None:
    """有界化（超龄淡忘 + `max_open` 截断）。公开别名供 `restore()` 复用。"""
    _prune(rifts, params, round_no)


def _prune(rifts: dict, params: dict, round_no: int | None = None) -> None:
    if round_no is not None:
        age_max = int(params.get("max_age_rounds", 84))
        for rid in [k for k, v in rifts.items() if int(round_no) - v["round"] > age_max]:
            rifts.pop(rid, None)
    max_open = int(params.get("max_open", 3))
    if len(rifts) > max_open:                       # 只留最近 max_open 条（确定：按 seq 取大）
        keep = sorted(rifts.values(), key=lambda v: (-v["seq"], v["rift_id"]))[:max_open]
        rifts.clear()
        for v in keep:
            rifts[v["rift_id"]] = v


def threads_with_open_rift(rifts: dict, peer: str | None = None) -> set:
    """有未了结旧账的线程集合（`peer` 给定时只算与该对端相关的）。"""
    return {v["thread_id"] for v in rifts.values() if peer is None or v["with"] == peer}


def peers_with_open_rift(rifts: dict) -> list:
    return sorted({v["with"] for v in rifts.values() if v.get("with")})


def context_line(rifts: dict, peer: str | None, round_no: int, name: str | None = None,
                 params: dict | None = None) -> str | None:
    """「处境」上下文（**不含任何现成句子**）：事实 + 选项工具箱。

    无相关 rift / 超龄 / 关闭 ⇒ `None`（提示词逐字节不变）。
    """
    params = params or _cfg()
    if not params.get("enabled") or not params.get("gripe_context") or not peer:
        return None
    rows = [v for v in rifts.values() if v.get("with") == peer]
    if not rows:
        return None
    oldest = min(rows, key=lambda v: v["seq"])
    age = max(0, int(round_no) - int(oldest["round"]))
    if age > int(params.get("context_max_age_rounds", 24)):
        return None
    who = name or peer
    topic = oldest.get("topic") or "上次那句话"
    return (f"\n心里还有件事没说开：{who}上次在「{topic}」上说了句让你不好受的话"
            f"（约 {age} 个回合前），你还没放下。{TOOLBOX}")


def audit_fields(rifts: dict, round_no: int, route: str,
                 peers: list | None = None) -> dict | None:
    """结构化可观测字段（无 rift ⇒ `None`，日志里一条都不产生）。"""
    if not rifts:
        return None
    rows = [v for v in rifts.values() if not peers or v.get("with") in peers]
    if not rows:
        return None
    out = {
        "v": "f4/1",
        "open": len(rows),
        "with": sorted({v["with"] for v in rows if v.get("with")}),
        "threads": sorted({v["thread_id"] for v in rows if v.get("thread_id")}),
        "route": route,
        "age_rounds": sorted(max(0, int(round_no) - int(v["round"])) for v in rows),
        "prompted": bool(rows and _prompted(rows, round_no)),
    }
    # T-RIFT-EVENTS（最小移植）：快照带 `rift_ids`（与 `threads`/`with` 同源，供 D4 分母精确化）
    if _cfg().get("rift_events"):
        out["rift_ids"] = sorted({v["rift_id"] for v in rows if v.get("rift_id")})
    return out


def repair_ask(rifts: dict, thread_id: str, peer: str | None, round_no: int,
               params: dict | None = None) -> str | None:
    """R13 / F-4 修复闭环：**在旧账所在线程里**要求这一句把话说开（只提要求，不给句式）。

    与 `context_line()` 的分工：
      * `context_line()` 是「处境」——告诉你心里还压着什么事（按对端，可跨线程）；
      * `repair_ask()` 是本回合的**动作要求**——只在本条要回复的线程里确有未了结旧账时出现，
        明确要求「这一句就把话说开」，从而让「张力 → 和解」在**同一线程内**可达。
    关闭 / 本线程无旧账 / 超龄 ⇒ `None`（提示词逐字节不变）。
    """
    params = params or _cfg()
    if not params.get("enabled") or not thread_id:
        return None
    rows = [v for v in rifts.values()
            if v.get("thread_id") == thread_id and (peer is None or v.get("with") == peer)]
    if not rows:
        return None
    oldest = min(rows, key=lambda v: v["seq"])
    if int(round_no) - int(oldest["round"]) > int(params.get("context_max_age_rounds", 24)):
        return None
    return ("\n你俩刚才这话没说痛快，这一句可以把话往开处带一带：别扭着、也别含糊过去，"
            "也别硬顶着认错——挑一个你愿意的法子，一句家常话把台阶递出去就行。")


def repair_audit(rifts: dict, thread_id: str, peer: str | None, round_no: int,
                 prompted: bool) -> dict | None:
    """R13 / F-4 结构化**可审计**信号（不做任何词表匹配，只记录台账事实）。

    每条记录都能被下游逐条点开复核：
        rift_id     → 台账主键（`R|<thread>|<msg_uid|seq>`）
        trigger_seq → 触发这条旧账的原句在日志里的 `seq`
        thread      → 旧账所在线程
        reply_seq   → **本条回复本身的 seq 由调用方落盘**（事件记录自带），与 trigger_seq 配对
    本线程无旧账 / 关闭 ⇒ `None`（不产生任何键）。
    """
    if not thread_id:
        return None
    rows = [v for v in rifts.values()
            if v.get("thread_id") == thread_id and (peer is None or v.get("with") == peer)]
    if not rows:
        return None
    rows = sorted(rows, key=lambda v: (v["seq"], v["rift_id"]))
    return {
        "v": "f4/repair/1",
        "thread": thread_id,
        "rift_ids": [v["rift_id"] for v in rows],
        "trigger_seqs": [int(v["seq"]) for v in rows],
        "peers": sorted({v["with"] for v in rows if v.get("with")}),
        "age_rounds": [max(0, int(round_no) - int(v["round"])) for v in rows],
        "prompted": bool(prompted),
    }


def _prompted(rows: list, round_no: int) -> bool:
    params = _cfg()
    if not params.get("gripe_context"):
        return False
    oldest = min(rows, key=lambda v: v["seq"])
    return (int(round_no) - int(oldest["round"])) <= int(params.get("context_max_age_rounds", 24))
