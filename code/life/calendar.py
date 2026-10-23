"""日历臂（calendar）：把「今天是什么日子」写进对话提示词。

一句话：居民现在只知道「一天四时段」和「我在哪儿、手上做什么」（后者还要开
`LIFE_PROMPT_SCENE`），但**不知道今天是工作日还是周末、是周几**——
`engine/time.py::derive_time` 早就算出了 `day_type` / `day_of_week`，
`life/ports.py::TimeCoord` 也已透传，只是从未进过任何一条提示词。

单变量约束（沿用 `scene_anchor` / `topic_breadth` / `l7_structural` 的开关先例）：
  * 开关 = 环境变量 `LIFE_PROMPT_CALENDAR`（∈ {1,true,yes,on}），**默认 OFF**；
  * OFF ⇒ `render()` 恒返回空串、`audit()` 恒返回 None，调用方 `agent.py` 拼进提示词的
    仍是空串 ⇒ **两条提示词与接入前逐字节一致**，`ctx.calendar` 键不出现
    ⇒ MSG payload 也与接入前逐字节一致。

素材纪律：
  1. **只读已有事实**：`WorldView.time.day_type` / `WorldView.time.day_of_week`
     （由 `code/engine/time.py::derive_time` 确定性派生）。**不新增真相源、不读墙钟、
     不发事件、不改 state_hash、不写记忆、不碰 `code/config/*.json`**。
  2. **只递人话，不递内部 token**：`workday` / `weekend` / 数字 `day_of_week`
     一律映射成「上工/歇着」「周几」；词表缺项 ⇒ 该片段不写（宁缺不写）。
  3. **确定性**：工作日/周末的措辞由 `sha256(agent_id|round|calendar)` 从固定词表里选，
     不含随机数、不含墙钟 ⇒ 同一 run 重放逐字节一致（R1 §2.1 可复现纪律）。

`day_of_week → 周几` 的映射依据：`CODE_TIME_CONFIG['DAY_TYPES'] = ["workday"]*5 + ["weekend"]*2`
⇒ 下标 0..4 是上工日、5..6 是歇日，故按 0=周一 … 6=周日 命名。这是**命名层**的常量，
不是新增真相源；若将来 `DAY_TYPES` 顺序变化，本模块与词表须同步（`lexicon_sha256` 可检出）。

剂量：每次装配**只插一行**（约 +30~45 字符），避免 L-1 长度分布整体漂移。
"""
from __future__ import annotations

import hashlib
import os

#: 臂开关（env `LIFE_PROMPT_CALENDAR`）；默认关。
CALENDAR_ENV = "LIFE_PROMPT_CALENDAR"

#: 日子类型（`derive_time.day_type`）→ 人话措辞候选（固定词表；改词表＝改行为）。
DAY_TYPE_WORDS: dict[str, tuple[str, ...]] = {
    "workday": ("今儿是上工的日子", "今天得干活", "今儿个不是歇的日子"),
    "weekend": ("今儿是歇着的日子", "今天不用上工", "今儿个是歇班天"),
}

#: `day_of_week`（0..6）→ 周几人话（依据见模块 docstring 的 `DAY_TYPES` 下标约定）。
WEEKDAY_WORDS: dict[int, str] = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日",
}

#: 词表指纹（报告/runbook 侧要冻结的"尺子"身份；只由上面两张表的内容决定）。
LEXICON_VERSION = "calendar-v1"


def enabled() -> bool:
    """臂开关（env `LIFE_PROMPT_CALENDAR` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(CALENDAR_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pick(seed: str, options: tuple[str, ...]) -> str:
    """确定性选词：同一 (agent, round) 恒得同一措辞。"""
    if not options:
        return ""
    return options[int(_sha(seed)[:8], 16) % len(options)]


def lexicon_sha256() -> str:
    """词表指纹：两张词表 + 版本号的规范化拼接 sha256（改动词表即可被检出）。"""
    rows = [LEXICON_VERSION]
    for dt in sorted(DAY_TYPE_WORDS):
        rows.append(f"day_type:{dt}=" + "|".join(DAY_TYPE_WORDS[dt]))
    for dow in sorted(WEEKDAY_WORDS):
        rows.append(f"dow:{dow}={WEEKDAY_WORDS[dow]}")
    return _sha("\n".join(rows))


def render(agent_id: str, round_no: int, day_of_week, day_type) -> str:
    """渲染插入提示词的那一行「今天是什么日子」；素材不足以成句时返回空串（宁缺不写）。

    `day_of_week` / `day_type` 直接取 `WorldView.time` 的两个字段；缺失或非法时
    对应片段省略（两个都没有 ⇒ 返回空串，等价于没开工）。
    """
    if not enabled():
        return ""
    try:
        dow = int(day_of_week)
    except (TypeError, ValueError):
        dow = None
    weekday = WEEKDAY_WORDS.get(dow) if dow is not None else ""
    dt_key = str(day_type or "").strip()
    dt_word = _pick(f"{agent_id}|{round_no}|calendar", DAY_TYPE_WORDS.get(dt_key, ()))
    bits: list[str] = []
    if weekday:
        bits.append(weekday)
    if dt_word:
        bits.append(dt_word)
    if not bits:
        return ""
    tail = "（这只是你心里有数的一件事：顺口带一句就够，别当成报日期，也别每条都提；说不着就不提。）"
    return "\n今儿是什么日子：" + "，".join(bits) + "。" + tail


def audit(day_of_week, day_type, line: str | None = None) -> dict:
    """审计快照（写进 MSG payload 的 `ctx.calendar`；**只在开关打开时产**）。

    机器侧记的是原始字段（`day_of_week` / `day_type`），另记 `line_sha256`，
    便于报告侧证明"模型看到的那一行"确实是它。
    """
    out: dict = {}
    try:
        out["day_of_week"] = int(day_of_week)
    except (TypeError, ValueError):
        pass
    if day_type:
        out["day_type"] = str(day_type)
    if line:
        out["line_sha256"] = _sha(line.strip())   # 不含前导换行：与提示词里那一行文本对齐
    return out
