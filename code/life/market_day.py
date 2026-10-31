"""镇历/集日臂（market_day）：把「今儿是不是镇上的集日」写进对话提示词。

一句话：居民现在知道「一天四时段」（`scene_anchor`）、知道「外头的天」（`weather`），
但**不知道今天在镇子的日子里是哪一天**——所以台词里没有「今儿逢集，摊子摆到街口」
「集上东西贵了两文」这种**按日子过日子**的话。本臂给集日补一条**镇级**的日历事实，
让开口能自然带出「赶集」这条生活线索。

单变量约束（沿用 `scene_anchor` / `weather` / `topic_breadth` 的开关先例）：
  * 开关 = 环境变量 `HITT_MARKET_DAY`（∈ {1,true,yes,on}），**默认 OFF**；
  * OFF ⇒ `render()` 恒返回空串、`audit()` 恒返回 None，`agent.py` 拼进提示词的仍是空串
    ⇒ **两条提示词与接入前逐字节一致**，`ctx.market` 键不出现
    ⇒ MSG payload 也与接入前逐字节一致。
  * **ON 且非集日**同样返回空串 ⇒ ON 臂与 OFF 臂在非集日的提示词**逐字节相等**
    （这是本臂「不外溢」的结构性保证：集日差一行，其余日子零差异）。

素材纪律（防回归的三条硬线）：
  1. **确定性派生、零新真相源**：集日只由 `day` 推出（`day % MARKET_PERIOD_DAYS == 0`），
     `day` 取 `WorldView.time.day`（`engine/time.py::derive_time` 已确定性派生）。
     **不读墙钟、不引随机源、不发事件、不改 state_hash、不写记忆、不碰 `code/config/*.json`**
     ⇒ 同一天恒为同一种日子，可 replay。镇上的「集」是既有世界事实
     （`code/config/places.json` 有 `market`/市集，`affordances=[work,trade]`），本臂只补
     「今天逢不逢集」这条**日历**，不新增场所、不改营业时段、不改日程。
  2. **只递人话，不递内部 token**：`market_day` / `day` 只出现在审计里，提示词里只写
     「今儿逢集」这类人话（防 L-8c / L-13 token 泄漏）。
  3. **剂量约束写在 render 里（宁可不提，不要硬提）**：每次集日只插**一行**（约 +45~60 字符），
     行尾显式要求「顺带一句就够、说不着就别提、别每条都提、别当成报日子」——
     否则集日会退化成复读机，反而更不像过日子。措辞由 `sha256(agent_id|round|day)`
     从固定词表里选 ⇒ 同一天不同人、不同回合说法不同（顺带抑制 L-7 开口句式重复）。

周期：`MARKET_PERIOD_DAYS = 3`（合小镇「逢三、六、九赶集」）。**不是** 7：
`engine/time.py::DEFAULT_TIME_CONFIG` 的 `DAYS_PER_WEEK=7` 把 weekend 放在 day5/day6，
而可负担的验证批次（r24=2 天、r48=4 天）根本覆盖不到，7 天周期在批次内测不到对照。
周期 3 让 r24 批次内天然有「集日 day0 / 非集日 day1」、r48 有「集日 day0+day3」对照。
改这个常数＝改日历节奏，须重冻结 `lexicon_sha256()`。
"""
from __future__ import annotations

import hashlib
import os

#: 臂开关（env `HITT_MARKET_DAY`）；默认关。未设置 == OFF。
MARKET_ENV = "HITT_MARKET_DAY"

#: 几天一集（`day % MARKET_PERIOD_DAYS == 0` 为集日）：逢三、六、九赶集。
MARKET_PERIOD_DAYS = 3

#: 集日 → **提示词措辞**候选（固定表；只写人话，不出现内部 token）。
#: ⚠ 这里**不是判据词表**：主判据 `R_B` / 探针 `R_A` 的正则唯一真源在
#: `tools/metrics/market_day_readings.py`（由 T1b 词表审计定稿），两臂共用同一把尺子，
#: 改尺子不必改两遍。本表只管"给模型看的那一句怎么说"。
#: 措辞纪律：只表达**背景/感知**（"今儿逢三，镇上赶集"），**不得**写成行动指令
#: （"该去赶集""去摆摊"）——`places.json::market.open_slots` 每天照开，本臂不改可达性，
#: 若提示词暗示"今天应该去"，就会产出自相矛盾叙述（见预登记 §3.1）。
MARKET_WORDS: tuple[str, ...] = (
    "今儿逢三，镇上赶集",
    "今儿是镇上的集日",
    "今儿逢集日，街上热闹",
    "今儿逢三六九里的日子，镇上赶集",
)

#: 词表指纹（报告/runbook 侧要冻结的"尺子"身份；只由词表 + 周期 + 版本号决定）。
LEXICON_VERSION = "market-day-v1"


def enabled() -> bool:
    """臂开关（env `HITT_MARKET_DAY` ∈ {1,true,yes,on}）；未设置 == OFF。"""
    return os.environ.get(MARKET_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pick(seed: str, options: tuple[str, ...]) -> str:
    """确定性选词：同一 seed 串恒得同一措辞。"""
    if not options:
        return ""
    return options[int(_sha(seed)[:8], 16) % len(options)]


def is_market_day(day: int) -> bool:
    """`day` → 是否集日；纯函数，非法输入按 day=0 处理（即集日）。"""
    try:
        d = int(day)
    except (TypeError, ValueError):
        d = 0
    return d % MARKET_PERIOD_DAYS == 0


def lexicon_sha256() -> str:
    """词表指纹：周期 + 集日词表 + 版本号 + 剂量尾句。"""
    rows = [LEXICON_VERSION, f"period:{MARKET_PERIOD_DAYS}",
            "words:" + "|".join(MARKET_WORDS), "tail:" + _TAIL]
    return _sha("\n".join(rows))


#: 剂量约束尾句（写进提示词那一行；改它＝改行为，须重冻结 `lexicon_sha256()`）。
_TAIL = "（这只是镇上的背景，不用你张罗什么：用得着就顺口带半句集上的事；说不着就别提，" \
        "也别每条都提，更别当成报日子。）"


def render(agent_id: str, round_no: int, day: int) -> str:
    """渲染插入提示词的那一行「今儿镇上的日子」；**非集日恒返回空串**（宁缺不写）。

    `day` 取 `WorldView.time.day`。集日是世界事实，只有措辞随 `(agent_id, round)` 变
    —— 同一天里不同人、不同回合说法不同。
    """
    if not enabled():
        return ""
    if not is_market_day(day):
        return ""                                  # 非集日：一行都不加（ON 与 OFF 逐字节相等）
    word = _pick(f"{agent_id}|{round_no}|{int(day)}|market", MARKET_WORDS)
    if not word:
        return ""
    return "\n今儿镇上的日子：" + word + "。" + _TAIL


def audit(day: int, line: str | None = None) -> dict:
    """审计快照（写进 MSG payload 的 `ctx.market`；**只在开关打开且为集日时产**）。

    机器侧记的是 key（`is_market_day` / `day` / `period`），不是人话；
    另记 `line_sha256`，便于报告侧证明「模型看到的那一行」确实是它。
    """
    out: dict = {"day": int(day), "is_market_day": bool(is_market_day(day)),
                 "period": int(MARKET_PERIOD_DAYS)}
    if line:
        out["line_sha256"] = _sha(line.strip())    # 不含前导换行：与提示词里那一行文本对齐
    return out
