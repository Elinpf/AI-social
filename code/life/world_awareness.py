"""D8「世界事件 → 居民可见 → 对话提及」上下文机制（**默认关，纯上下文层**）。

诊断（本分支 `v2/evidence/D8-branch-impl.md`）：世界层的 `WORLD_DIRECTIVE` /
`WORLD_GROUP_EVENT` 在 `config/perception_scope.json` 里是 `global` 可见类 ⇒ **居民确实
`visible_events()` 里能读到**，但 life 层的两条消费链都是断的：
  1. `_observe()` 只认 `_SALIENT_EVENTS` 白名单（不含 `WORLD_*`）⇒ 世界事件**不进记忆**、
     不产生 `OBSERVATION`（"被看到"在账本里无痕）；
  2. `_dialogue_prompt()` / `_reply_prompt()` 只拼人格 + 关系 + 情绪 + 线程历史 ⇒ 世界事件
     **不进对话上下文**，措辞里自然也不会提；
  3. `world_params.market_scarcity_bp` 只在 `_read_world_params()` 里被读、**无任何消费点**。

本模块把这三处**最小**接通，形态与 `life/dialogue_repair.py`（R6-T2）同构：

  * **纯上下文层**：本模块不生成/不改写任何正文，只产出"最近的镇上的事"这一句处境；
    措辞仍由 LLM 自己写（与 08 §"生命层只给处境、不下笔"一致）。
  * **默认关闭**（`config/world_awareness.json` 的 `enabled=false`）⇒ 与基线 `2090287`
    **逐项等价**：不改提示词、不写记忆、不发事件、payload 不多一个键。
  * **不进 `state_hash`**：只作用于 agent-local 上下文 + MSG payload 的追加键
    （`SOCIAL_THREAD_FIELDS` 同级的 `world_ctx`），与 D2/D5 同一分层约定。
  * **有界**：窗口 `window_rounds`、条数 `max_lines`、kind 数 `max_kinds` 三重上限；
    同 `directive_ref` 去重（取最近一次）。

可复算证据链（供 A/B 计数）：
  * 世界事件发生数：账本 `WORLD_GROUP_EVENT` / `WORLD_DIRECTIVE` 条数；
  * 被居民观察到数：`OBSERVATION.payload.target_event_seq` 指向上述事件 `seq` 的条数
    （本模块打开后才会出现；关闭时 0）；
  * 被对话上下文带到的条数：`MSG_*.payload.world_ctx.refs` 非空的 MSG 条数；
  * 措辞真的提及（弱判据）：MSG body 里出现 kind 关键词（由上层脚本判，本模块不判）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

#: 世界层事件的两种落账类型（`engine/hooks/world_director.py` 产出；均为 `global` 可见类）
WORLD_EVENT_TYPES = ("WORLD_GROUP_EVENT", "WORLD_DIRECTIVE")

#: D8 开关的 env 逃生口（与 `HITT_DIALOGUE_REPAIR` 同一约定）
ENV_SWITCH = "HITT_WORLD_AWARENESS"
#: ① / ② 的独立逃生口（未设 = 用 config 文件里的值）
ENV_OBSERVE = "HITT_WORLD_AWARENESS_OBSERVE"
ENV_DIALOGUE = "HITT_WORLD_AWARENESS_DIALOGUE"

DEFAULTS = {
    "enabled": False,          # 总开关（默认关 = 基线语义不变）
    # ① 与 ② **各自独立可切**（Leader 裁决：便于把副作用定位到具体层）
    "observe_enabled": True,   # ① 世界事件进记忆 + 发 OBSERVATION（"被看到"有账本痕迹）
    "dialogue_enabled": True,  # ② 把"最近的镇上的事"放进对话提示词（发起 + 回复都放）
    # ③ 本轮**不默认开**：`market_scarcity_bp` → 一句物价情境（只给情境、不给结论；
    #    不碰定价/`_scarcity_index`，避免与 ①② 混批导致 A/B 归因失效）
    "scarcity_in_prompt": False,
    "window_rounds": 24,       # 只提 N 回合内的世界事件（旧事不再刷屏）
    "max_lines": 2,            # 提示词里最多 N 条
    "max_kinds": 3,            # 同一条 brief 里最多 N 种 kind
    "scarcity_min_bp": 1000,   # `market_scarcity_bp` ≥ 该值才算"贵了"（bp，整数）
    "importance_min": 4,       # 世界事件写记忆时的确定性重要性下限（1–10）
}

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "world_awareness.json"

#: kind → 中文短句（**只描述情境，不含金额/胜负/个体指令**；R5/R6 口径不变）
KIND_ZH = {
    "season": "换季了",
    "festival": "镇上在办节庆",
    "opportunity": "有了新机会",
    "public_works": "镇里在修公共设施",
    "supply_shock": "集市供货有点紧",
    "scarcity": "东西不太好买",
    "tension": "镇上气氛有点紧张",
    "incident": "出了点小乱子",
    "disaster": "遭了点灾",
    "epidemic": "闹了场病",
    "visitor": "来了外乡人",
    "edict": "镇里发了新通告",
    "agenda": "大家在议一件事",
    "mass_event": "有场大活动",
}

PLACE_ZH = {
    "hall": "礼堂", "plaza": "广场", "market": "集市", "park": "公园",
    "school": "学校", "kitchen": "厨房", "residence": "住处", "clinic": "诊所",
}

_cache: dict | None = None
_override: dict | None = None


def load_params(path: str | Path | None = None) -> dict:
    """读 `config/world_awareness.json`（缺省值 → 默认**关**）；支持 env 逃生口。

    env：`HITT_WORLD_AWARENESS=1|true|on` → 打开；`=0|false|off` → 关闭（消融/回退用）。
    **本文件不进 `engine_version` 指纹**（默认关 ⇒ 旧日志 fingerprint 不受影响）。
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
    env = os.environ.get(ENV_SWITCH)
    if env is not None:
        out["enabled"] = env.strip().lower() in ("1", "true", "on", "yes")
    for key, env_name in (("observe_enabled", ENV_OBSERVE), ("dialogue_enabled", ENV_DIALOGUE)):
        env_v = os.environ.get(env_name)
        if env_v is not None:
            out[key] = env_v.strip().lower() in ("1", "true", "on", "yes")
    out["enabled"] = bool(out["enabled"])
    for k in ("observe_enabled", "dialogue_enabled", "scarcity_in_prompt"):
        out[k] = bool(out[k])
    for k in ("window_rounds", "max_lines", "max_kinds", "scarcity_min_bp", "importance_min"):
        out[k] = int(out[k])
    if path is None:
        _cache = dict(out)
    return out


def set_override(d: dict | None) -> None:
    """Test/ablation hook：强制参数（None 清除）。不落盘、不改指纹。"""
    global _override
    _override = dict(d) if d else None


def enabled(params: dict | None = None) -> bool:
    """总开关（默认 False）。"""
    return bool((params or load_params()).get("enabled", False))


def observe_on(params: dict | None = None) -> bool:
    """① 记忆/观测层开关 = 总开关 ∧ `observe_enabled`。"""
    p = params or load_params()
    return bool(p.get("enabled")) and bool(p.get("observe_enabled", True))


def dialogue_on(params: dict | None = None) -> bool:
    """② 提示词层开关 = 总开关 ∧ `dialogue_enabled`。"""
    p = params or load_params()
    return bool(p.get("enabled")) and bool(p.get("dialogue_enabled", True))


def _field(ev, key, default=None):
    if isinstance(ev, dict):
        return ev.get(key, default)
    return getattr(ev, key, default)


def _zh(kind: str, place: str | None) -> str:
    """kind → 人话情境（**不含内部 id/token**；未知 place 名一律省略，不回落原始 place_id）。"""
    base = KIND_ZH.get(str(kind or "").lower(), "出了件事")
    pz = PLACE_ZH.get(place or "", "")
    return f"{base}（{pz}）" if pz else base


def brief_lines(visible_events, round_no: int, params: dict | None = None) -> list[tuple]:
    """把可见世界事件折成**有界**的处境清单（纯函数）。

    返回 `[(ref, kind, seq, round, line)]`，按 `seq` 升序；同 `ref` 去重取最近一条。
    关闭/无候选 ⇒ `[]`（调用方据此保持提示词逐字不变）。
    """
    p = params or load_params()
    if not dialogue_on(p):
        return []
    window = int(p.get("window_rounds", 24))
    by_ref: dict[str, tuple] = {}
    for ev in visible_events or ():
        t = _field(ev, "type")
        if t not in WORLD_EVENT_TYPES:
            continue
        r = int(_field(ev, "round", 0) or 0)
        if r < int(round_no) - window:
            continue
        pay = _field(ev, "payload", {}) or {}
        if not pay.get("directed", False):
            continue                       # 与 world_params 同口径：无 directed 不传导
        ref = pay.get("directive_ref") or pay.get("directive_id") or f"seq:{_field(ev, 'seq', 0)}"
        scope = pay.get("scope") or {}
        place = scope.get("place") or pay.get("place")
        kind = str(pay.get("kind", "")).lower()
        seq = int(_field(ev, "seq", 0) or 0)
        row = (str(ref), kind, seq, r, _zh(kind, place))
        prev = by_ref.get(str(ref))
        if prev is None or seq >= prev[2]:
            by_ref[str(ref)] = row
    rows = sorted(by_ref.values(), key=lambda x: (x[2], x[0]))
    # kind 上限：按 ref 顺序保留前 max_kinds 个不同 kind
    max_kinds = int(p.get("max_kinds", 3))
    kept, kinds = [], set()
    for row in rows:
        if row[1] not in kinds and len(kinds) >= max_kinds:
            continue
        kinds.add(row[1])
        kept.append(row)
    return kept[-int(p.get("max_lines", 2)):] if kept else []


def scarcity_line(world_params: dict | None, params: dict | None = None) -> str:
    """消费 `market_scarcity_bp`：≥ 阈值 ⇒ 返回一句"东西贵了"的处境（否则空串）。"""
    p = params or load_params()
    if not dialogue_on(p) or not p.get("scarcity_in_prompt"):
        return ""
    bp = (world_params or {}).get("market_scarcity_bp") or {}
    if not bp:
        return ""
    thr = int(p.get("scarcity_min_bp", 1000))
    if any(int(v) >= thr for v in bp.values()):
        return "最近镇上东西贵了些"
    return ""


def prompt_context(visible_events, round_no: int, world_params: dict | None = None,
                   params: dict | None = None) -> dict:
    """生成一次「世界处境」上下文快照（纯函数、有界、确定性）。

    返回 `{"lines": [str], "refs": [str], "kinds": [str], "scarcity": bool,
           "text": str}`；`text` 为空串 ⇒ 提示词/ payload 都**保持原样**。
    """
    p = params or load_params()
    if not dialogue_on(p):
        return {"lines": [], "refs": [], "kinds": [], "scarcity": False, "text": ""}
    rows = brief_lines(visible_events, round_no, p)
    lines = [r[4] for r in rows]
    sc = scarcity_line(world_params, p)
    if sc:
        lines.append(sc)
    text = ""
    if lines:
        text = "\n最近镇上的事：" + "；".join(lines) + "。"
    return {
        "lines": lines,
        "refs": [r[0] for r in rows],
        "kinds": [r[1] for r in rows],
        "scarcity": bool(sc),
        "text": text,
    }


def describe_event(typ: str, kind: str, place: str | None = None) -> str:
    """世界事件写进记忆时的**人话描述**（确定性；只给情境、不给结果）。

    - 两种类型**各用一句不同模板**（`WORLD_DIRECTIVE` = 公告/官方口吻，`WORLD_GROUP_EVENT`
      = 街坊口耳相传），避免 M-1 短语集中撞到同一个词上导致词表判据失真；
    - **绝不**带 `WORLD_*` / `wd.*` / directive_id / `*_bp` 等内部 token（否则记忆里会
      出现机器文本，被检索原样带进 prompt ⇒ 假"提及"）；
    - 只说"发生了什么"，不说"你该怎么想/该怎么做"（R4 §3.2 / world_params 红线）。
    """
    line = _zh(kind, place)
    if typ == "WORLD_DIRECTIVE":
        return f"镇上贴出了一份新通告：{line}。"
    return f"街坊们都在传：{line}。"
