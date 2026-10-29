"""天气/季节臂（weather）：把「今儿天怎么样」写进对话提示词。

一句话：居民现在只知道「一天四时段」「我在哪儿、手上做什么」，但**不知道外头的天**——
所以一百句台词里没有一句「今天阴着」「风大得很」「日头毒，别在外头站着」。
本臂给每个回合补一条**世界级**的天候事实，让开口能自然带出对天的感知。

单变量约束（沿用 `scene_anchor` / `calendar` / `topic_breadth` / `l7_structural` 的先例）：
  * 开关 = 环境变量 `HITT_WEATHER`（∈ {1,true,yes,on}），**默认 OFF**；
  * OFF ⇒ `render()` 恒返回空串、`audit()` 恒返回 None，`agent.py` 拼进提示词的仍是空串
    ⇒ **两条提示词与接入前逐字节一致**，`ctx.weather` 键不出现
    ⇒ MSG payload 也与接入前逐字节一致（证据：`tools/weather/off_equiv_prompts.py`）。

素材纪律（防回归的三条硬线）：
  1. **确定性派生、零新真相源**：天气只由 `(world_seed, day)` 经 `sha256` 纯函数推出，
     季节只由 `day` 推出。**不读墙钟、不引随机源、不发事件、不改 state_hash、不写记忆、
     不碰 `code/config/*.json`** ⇒ 同 seed 同 day 恒得同天气（可 replay）。
     `world_seed` 取环境变量 `HITT_WORLD_SEED`（缺省 `"0"`）：跑批脚本把它设成 run seed，
     天气就随 seed 变化；不设时全批次恒为 seed 0 的一套天气，**仍然确定性**。
  2. **只递人话，不递内部 token**：`clear/rain/...`、`spring/...` 一律只出现在审计里，
     提示词里只写「阴着天」「开春了」这类人话（防 L-8c / L-13 token 泄漏）。
  3. **季节与天气自洽**：词表按季给权重（冬天不下雨下雪、夏天不飘雪），
     晴天在夏天用「日头毒」一类措辞。权重表即行为，改表＝改行为，须重冻结 `lexicon_sha256()`。

剂量：每次装配**只插一行**（约 +35~55 字符），避免 L-1 长度分布整体漂移；
措辞由 `sha256(agent_id|round|weather)` 从固定词表里选 ⇒ 同一天不同人、不同回合说法不同，
直接服务于 L-7（开口句式重复）的抑制。
"""
from __future__ import annotations

import hashlib
import os

#: 臂开关（env `HITT_WEATHER`）；默认关。未设置 == OFF。
WEATHER_ENV = "HITT_WEATHER"

#: 世界种子（env `HITT_WORLD_SEED`，缺省 `"0"`）：跑批时设成 run seed，天气随 seed 变。
WORLD_SEED_ENV = "HITT_WORLD_SEED"

#: 一季的天数（压缩历法：1 周 = 1 季）。改这个常数＝改季节节奏，须重冻结词表指纹。
DAYS_PER_SEASON = 7

#: 四季（顺序即 `day // DAYS_PER_SEASON % 4` 的取值序）。
SEASONS: tuple[str, ...] = ("spring", "summer", "autumn", "winter")

#: 季 → 人话措辞候选（固定词表）。
SEASON_WORDS: dict[str, tuple[str, ...]] = {
    "spring": ("开春了", "春天了", "这天回暖了"),
    "summer": ("入夏了", "天热起来了", "夏天了"),
    "autumn": ("入秋了", "秋天了", "天见凉了"),
    "winter": ("入冬了", "冬天了", "天冷透了"),
}

#: 六种天气（内部 key；**只出现在审计里，不进提示词**）。
WEATHER_KINDS: tuple[str, ...] = ("clear", "cloudy", "overcast", "windy", "rain", "snow")

#: 天气 → 人话措辞候选（固定词表）。
WEATHER_WORDS: dict[str, tuple[str, ...]] = {
    "clear": ("日头挺好", "天晴着", "晴得透亮"),
    "cloudy": ("云彩不少", "半阴半晴", "天上有云"),
    "overcast": ("阴着天", "天阴沉沉的", "乌沉沉的一天"),
    "windy": ("风大", "风刮得紧", "外头有风"),
    "rain": ("下着雨", "雨丝不断", "落雨了"),
    "snow": ("下着雪", "飘雪", "雪粒子打脸"),
}

#: 季节性措辞覆盖（季, 天气）→ 专用措辞；命中则**取代** `WEATHER_WORDS`（更贴季）。
SEASON_WEATHER_WORDS: dict[tuple[str, str], tuple[str, ...]] = {
    ("summer", "clear"): ("日头毒", "晒得厉害", "大晴天毒日头"),
    ("summer", "rain"): ("闷热过后下着雨", "雷雨刚过还在落", "热雨一天"),
    ("winter", "windy"): ("北风刮得紧", "风又冷又硬", "冷风直往脖子里钻"),
    ("winter", "clear"): ("冷晴冷晴的", "日头亮可天冷", "晴天也冻手"),
    ("autumn", "windy"): ("秋风扫得紧", "风里带凉", "秋风吹落叶"),
}

#: 季 → 天气权重（0 = 该季不出现）。表即行为：改权重＝改天气分布。
WEATHER_WEIGHTS: dict[str, dict[str, int]] = {
    "spring": {"clear": 30, "cloudy": 25, "overcast": 15, "windy": 15, "rain": 15, "snow": 0},
    "summer": {"clear": 30, "cloudy": 20, "overcast": 8, "windy": 12, "rain": 30, "snow": 0},
    "autumn": {"clear": 28, "cloudy": 22, "overcast": 15, "windy": 20, "rain": 15, "snow": 0},
    "winter": {"clear": 22, "cloudy": 20, "overcast": 18, "windy": 15, "rain": 5, "snow": 20},
}

#: 词表指纹（报告/runbook 侧要冻结的"尺子"身份；只由上面几张表 + 版本号决定）。
LEXICON_VERSION = "weather-v1"


def enabled() -> bool:
    """臂开关（env `HITT_WEATHER` ∈ {1,true,yes,on}）；未设置 == OFF。"""
    return os.environ.get(WEATHER_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def world_seed() -> int:
    """世界种子（env `HITT_WORLD_SEED`，缺省 0）。非法/缺失 ⇒ 0（不抛、不读墙钟）。"""
    raw = os.environ.get(WORLD_SEED_ENV, "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pick(seed: str, options: tuple[str, ...]) -> str:
    """确定性选词：同一 seed 串恒得同一措辞。"""
    if not options:
        return ""
    return options[int(_sha(seed)[:8], 16) % len(options)]


def season_of_day(day: int) -> str:
    """`day`（`engine/time.py::derive_time` 派生）→ 季 key；确定性、无墙钟。"""
    try:
        d = int(day)
    except (TypeError, ValueError):
        d = 0
    return SEASONS[(d // DAYS_PER_SEASON) % len(SEASONS)]


def weather_of_day(day: int, seed: int | None = None) -> str:
    """`(seed, day)` → 天气 key。**纯函数**：同 seed 同 day 恒得同一结果。

    做法：`h = sha256("<seed>|<day>|weather-v1")` → 取前 8 位十六进制 → 对当季权重和取模
    → 落到累计权重区间。没有 `random`、没有时间、没有进程状态。
    """
    s = world_seed() if seed is None else int(seed)
    season = season_of_day(day)
    table = WEATHER_WEIGHTS.get(season) or {}
    total = sum(int(w) for w in table.values())
    if total <= 0:
        return ""
    x = int(_sha(f"{s}|{int(day)}|{LEXICON_VERSION}")[:8], 16) % total
    acc = 0
    for kind in WEATHER_KINDS:                     # 固定顺序 ⇒ 结果可复算
        w = int(table.get(kind, 0))
        if w <= 0:
            continue
        acc += w
        if x < acc:
            return kind
    return ""                                      # 理论上不可达；宁缺不写


def lexicon_sha256() -> str:
    """词表指纹：季词表 + 天气词表 + 季节覆盖 + 权重表 + 版本号 + 季节天数。"""
    rows = [LEXICON_VERSION, f"days_per_season:{DAYS_PER_SEASON}"]
    for season in SEASONS:
        rows.append(f"season:{season}=" + "|".join(SEASON_WORDS.get(season, ())))
    for kind in WEATHER_KINDS:
        rows.append(f"weather:{kind}=" + "|".join(WEATHER_WORDS.get(kind, ())))
    for (season, kind) in sorted(SEASON_WEATHER_WORDS):
        rows.append(f"override:{season}/{kind}=" + "|".join(SEASON_WEATHER_WORDS[(season, kind)]))
    for season in SEASONS:
        table = WEATHER_WEIGHTS.get(season, {})
        rows.append(f"weights:{season}=" + ",".join(f"{k}:{int(table.get(k, 0))}"
                                                    for k in WEATHER_KINDS))
    return _sha("\n".join(rows))


def render(agent_id: str, round_no: int, day: int, seed: int | None = None) -> str:
    """渲染插入提示词的那一行「今儿天怎么样」；素材不足以成句时返回空串（宁缺不写）。

    `day` 取 `WorldView.time.day`（或 `WorldView.day`）。天气**与 agent 无关**（是世界事实），
    只有措辞随 `(agent_id, round)` 变 —— 同一天里不同人、不同回合说法不同。
    """
    if not enabled():
        return ""
    season = season_of_day(day)
    kind = weather_of_day(day, seed)
    if not kind:
        return ""
    season_word = _pick(f"{agent_id}|{round_no}|{season}|season", SEASON_WORDS.get(season, ()))
    words = SEASON_WEATHER_WORDS.get((season, kind)) or WEATHER_WORDS.get(kind, ())
    weather_word = _pick(f"{agent_id}|{round_no}|{kind}|weather", words)
    bits = [b for b in (season_word, weather_word) if b]
    if not bits:
        return ""
    tail = ("（心里有个数就成：顺口带一句，别当成报天气，也别每条都提；说不着就不提。）")
    return "\n今儿天怎么样：" + "，".join(bits) + "。" + tail


def audit(day: int, season: str, weather: str, seed: int, line: str | None = None) -> dict:
    """审计快照（写进 MSG payload 的 `ctx.weather`；**只在开关打开时产**）。

    机器侧记的是 key（`weather` / `season` / `day` / `seed`），不是人话；
    另记 `line_sha256`，便于报告侧证明「模型看到的那一行」确实是它。
    """
    out: dict = {"day": int(day), "season": str(season), "weather": str(weather),
                 "seed": int(seed)}
    if line:
        out["line_sha256"] = _sha(line.strip())    # 不含前导换行：与提示词里那一行文本对齐
    return out
