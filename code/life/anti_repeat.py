"""L-7 去重臂（DEQUP）：把「记住的事」变成「说出来不一样的话」。

背景（可复算锚点，见 `reports/R12-l7-dequp.md` §2 与 `v2/evidence/l7_baseline_recount.json`）：
R11 的 F-6 臂（跨天记忆进提示词）把 F-6 从 19/510 拉到 57/510，同时把 L-7
（8-gram 近重复率）从 181/510=0.354902 拉到 332/510=0.65098。零跑批复算显示：
ON 臂 412 条消息共 824 次记忆引用，去重后只有 128 个不同 `mem_id`（均值 6.44 次），
且 332 条近重复消息里 315 条带 `ctx.memory_refs` ⇒ 注入内容高度集中 + 台词互相照抄。

本模块只做三件**有界**的事（全部由单一 env 开关控制，默认 OFF）：
  ① **注入加权**：同一 `mem_id` 在本批内被反复注入后降权（`mem_usage`），让"想起来的事"
     不要总落在同几条上（不改检索权重、不 touch 记忆、不改 access_count）；
  ② **反照抄提示**：把最近若干条已经说出口的台词放进提示词，明确要求换说法
     （零额外 LLM 调用）；
  ③ **8-gram 撞车重试**：新台词若与最近窗口内的台词有 8-gram 重合 ⇒ **一次**重生成，
     把撞车的那句回给模型让它换说法（上限 1 次，不会级联）。

**纪律**：
  * 默认 OFF ⇒ `enabled()` 为 False，`prompt_line()` 返回空串、`collide()` 恒 None、
    `remember()` 也只在开启时才记账 —— 提示词与 payload 与接入前逐字节一致；
  * 不改配置、不改世界态、不新增事件类型、不进 `state_hash`；只在开启时往
    `ctx.dequp` 追加一个审计字段（additive）；
  * 8-gram 口径**镜像** `tools/d5/dialogue_metrics.py::normalize_body`（不发明新口径），
    由 `code/tests/test_anti_repeat.py::test_normalize_mirror` 守住不漂移。

**统计口径**：本模块只影响「台词怎么生成」，不改变指标定义；L-7 仍由官方脚本复算。
"""
from __future__ import annotations

import os
import re
from collections import Counter, deque

#: 去重臂开关（默认 OFF）——与 F-6 的 `LIFE_PROMPT_MEMORY_F6` 正交，可单独打开
DEQUP_ENV = "LIFE_PROMPT_MEMORY_F6_DEQUP"

#: 与官方 L-7 一致的 shingle 长度（`dialogue_metrics.py` 用 8）
NGRAM = 8
#: 最近窗口：参与「撞车判定」与「反照抄提示」的台词条数
RECENT_MAX = 40
#: 反照抄提示最多列几条（控 token）
PROMPT_LINES = 3
#: 单条提示/回喂的截断长度
LINE_CHARS = 50

#: 进程内状态（单进程跑批；`reset()` 供测试与重放使用）
_STATE: dict = {
    "recent": deque(maxlen=RECENT_MAX),
    "mem_use": Counter(),
    "stats": {"messages": 0, "retries": 0, "collisions": 0},
}


def enabled() -> bool:
    """env `LIFE_PROMPT_MEMORY_F6_DEQUP` ∈ {1,true,yes,on}；默认关。"""
    return os.environ.get(DEQUP_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def reset() -> None:
    _STATE["recent"].clear()
    _STATE["mem_use"].clear()
    _STATE["stats"] = {"messages": 0, "retries": 0, "collisions": 0}


def normalize(body: str) -> str:
    """**镜像** `tools/d5/dialogue_metrics.py::normalize_body`（改这里必须同步改那边）。"""
    s = (body or "").strip().lower()
    s = s.replace("（", "(").replace("）", ")")
    return re.sub(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)\[\]【】]", "", s)


def shingles(body: str) -> set[str]:
    t = normalize(body)
    return {t[i:i + NGRAM] for i in range(max(0, len(t) - NGRAM + 1))}


# ---- ① 注入加权 -------------------------------------------------------------
def mem_usage(mem_id: str) -> int:
    """该 `mem_id` 在本批内已被注进提示词的次数（0 = 还没用过）。"""
    return int(_STATE["mem_use"].get(str(mem_id), 0))


def note_memory(mem_ids) -> None:
    if not enabled():
        return
    for mid in mem_ids or ():
        _STATE["mem_use"][str(mid)] += 1


# ---- ② 反照抄提示 -----------------------------------------------------------
def prompt_line() -> str:
    """把最近说出口的几句话摆给模型看，要求换说法。关闭时返回空串。"""
    if not enabled():
        return ""
    recent = [b for b in list(_STATE["recent"])[-PROMPT_LINES:] if b]
    if not recent:
        return ""
    items = " / ".join(f"「{b[:LINE_CHARS]}」" for b in recent)
    return (f"\n镇上刚有人这么说：{items}"
            "\n（别照搬这些说法，也别用一样的句式；说你自己这会儿真想说的一句话。）")


# ---- ③ 8-gram 撞车重试 ------------------------------------------------------
def collide(body: str) -> str | None:
    """与最近窗口内的台词有任意 8-gram 重合 ⇒ 返回撞车的那句（供回喂），否则 None。"""
    if not enabled() or not body:
        return None
    new = shingles(body)
    if not new:
        return None
    for prior in reversed(list(_STATE["recent"])):
        if new & shingles(prior):
            _STATE["stats"]["collisions"] += 1
            return prior
    return None


def retry_suffix(hit: str) -> str:
    """撞车后追加到提示词的**一次性**重写要求。"""
    return (f"\n（你刚想说「{hit[:LINE_CHARS]}」，这句跟镇上已经说过的撞了；"
            "换个说法重说一句，别再用那些字眼。）")


def remember(body: str) -> None:
    """记账：本条台词进入最近窗口（关闭时不动任何状态）。"""
    if not enabled() or not body:
        return
    _STATE["recent"].append(body[:120])
    _STATE["stats"]["messages"] += 1


def note_retry() -> None:
    if enabled():
        _STATE["stats"]["retries"] += 1


def audit() -> dict:
    """开启时追加进 `ctx.dequp` 的审计字段（关闭时不产生）。"""
    s = _STATE["stats"]
    return {
        "v": "l7-dequp/1",
        "retries": int(s["retries"]),
        "collisions": int(s["collisions"]),
        "messages": int(s["messages"]),
        "mem_used": len(_STATE["mem_use"]),
        "top_mem": [{"mem_id": k, "n": v} for k, v in _STATE["mem_use"].most_common(3)],
    }
