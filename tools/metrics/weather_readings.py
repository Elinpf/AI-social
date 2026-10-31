#!/usr/bin/env python3
"""天气/季节臂读数器（纯读 run.jsonl，**零 LLM**）。

回答的问题：
  1. 对话里到底有没有带上「天」——天气现象提及率、体感提及率、季节提及率（各带 Wilson95）；
  2. 天气臂是否真的接上了——`ctx.weather` 出现条数、逐日天气分布、季节分布
     （OFF 臂恒为 0，因为代码构造上不产该键，见预登记卡 §3）；
  3. 句式是否自然/是否撞 L-7——首分句重复率（跨线程开口撞车）与高频首分句 Top-N；
  4. 提示词是否泄漏进正文——正文里出现标记行「今儿天怎么样」的条数（应为 0）。

用法（可直接复制）：

    # 单臂
    python3 tools/metrics/weather_readings.py v2/evidence/run_weather_on_n16r60_seed42/run.jsonl

    # 两臂对照（OFF 先、ON 后；标签自带即可）
    python3 tools/metrics/weather_readings.py \\
        --arm off=v2/evidence/run_weather_off_n16r60_seed42/run.jsonl \\
        --arm on=v2/evidence/run_weather_on_n16r60_seed42/run.jsonl \\
        --json v2/evidence/weather_readings.json

判据阈值**不在本脚本里**——脚本只输出读数，判定口径见 `v2/refs/W-1-weather-prereg.md`。

口径版本（2026-11-01 起并列两套，**旧字段名与旧数值均未改**）：
  * **v1 / LEGACY**（`weather_mention_strict`，`WEATHER_PHENOMENA` 子串命中）：历史口径，含已知假阳性
    （晒干/晒场/湿泥/云手/风箱/防风/糖霜 等），在 191 条样本上假阳性率 46%~50%（CYCLE-43 §5.4 P0）。
  * **v2**（`weather_mention_strict_v2`，词组级上下文约束）：5 个单字弱词（晒/湿/云/风/霜）改为
    「天气义词组白名单 ∧ ¬非天气复合词黑名单」判定，强词沿用子串命中。规则与判据见
    `v2/refs/W-1-lexicon-v2.md`；v2 是 v1 的**子集**（脚本输出 `v2_guard.v2_subset_of_v1` 自证）。
  * 两臂对照块 `contrast_on_minus_off_v2` 给出 Δ 与 **Newcombe95**（`newcombe95()`），
    v1 与 v2 必须并列、不得混用。
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
from pathlib import Path

# ---------------------------------------------------------------- 口径（改这里＝改尺子）
#: 天气**现象**词（严格口径 **v1 / LEGACY**，子串命中即算，不做上下文约束）。
#: ⚠️ **本元组是历史口径，不得修改**（改它会让历史批次读数不可比）。
#: v1 已知缺陷：`晒/湿/云/风/霜` 五个单字词是 BOTH 天气词与工艺/器物/招式/药材构词成分
#: （晒干/晒场/湿布/云手/风箱/防风/糖霜），纯子串匹配在 191 条样本上产生 46%~50% 假阳性
#: （CYCLE-43 §5.4 P0）。修复走下方 v2 口径，v1 原样保留并列输出。
WEATHER_PHENOMENA = ("下雨", "雨天", "落雨", "雨丝", "雨点", "雨", "晴", "日头", "晒",
                     "风大", "刮风", "有风", "风里", "起风", "风", "阴天", "阴着", "阴沉",
                     "天阴", "云", "雪", "雾", "霜", "雷", "潮气", "湿")

#: 天气**体感**词（宽松口径）：冷/热/凉/闷/燥/冻。单独报，避免和「心凉」这类情绪词混算。
WEATHER_FEEL = ("冷", "热", "凉", "闷", "燥", "冻", "晒")

#: 季节词。
SEASON_WORDS = ("春天", "春天", "开春", "入夏", "夏天", "秋", "入秋", "冬天", "入冬", "冬")

#: 提示词标记行（若出现在**正文**里，说明提示词泄漏，属硬缺陷）。
PROMPT_MARK = "今儿天怎么样"

# ---------------------------------------------------------------- 情境一致性三分法（CYCLE-28）
# 口径唯一出处：v2/evidence/weather_c28_adjudication_rules.md（**先固化后看 ON**，2026-10-29T20:39）。
# 三分法：direction_consistent / direction_inconsistent / undetermined_direction
#         （另单列 non_weather 留痕、unclassified 例外；二者不进主判据）
DIRECTION_GROUPS: dict[str, tuple[str, ...]] = {
    "rain": ("下雨", "雨天", "落雨", "雨丝", "雨点", "雨"),
    "clear": ("晴", "日头"),
    "cloudy": ("阴天", "阴着", "阴沉", "天阴", "云"),
    "snow": ("雪",),
    "wind": ("风大", "刮风", "有风", "起风", "风里", "风"),
}

#: 非方向现象/体感（kind 不决定对错 ⇒ undetermined_direction，不判对错）
UNDETERMINED_WORDS: tuple[str, ...] = ("雾", "霜", "雷", "潮气", "湿", "晒")

#: 去噪：命中词若落在这些**非天气构词**的字符跨度内，该次命中作废（物件缺陷/工艺/社交比喻）
NON_WEATHER_PATTERNS: tuple[str, ...] = ("漏风", "带风", "风一吹", "风干", "晒干", "通风",
                                        "风头", "跟风", "风气", "风味", "风凉话")

#: 当天 weather kind → 方向组（唯一可判对错的映射）
KIND_TO_GROUP: dict[str, str] = {"clear": "clear", "cloudy": "cloudy", "overcast": "cloudy",
                                 "windy": "wind", "rain": "rain", "snow": "snow"}


# ================================================================ 口径 v2（词组级上下文约束）
# 冻结件：v2/refs/W-1-lexicon-v2.md（2026-11-01 冻结，先定规则后重算已冻结日志）。
# 设计原则：v1 里 5 个单字弱词（晒/湿/云/风/霜）改为**词组级**判定 ——
#   只有出现「天气义词组」（V2_PHRASES）且不落在「非天气复合词」（V2_WEAK_DENY）跨度内才算命中；
#   v1 里本就没有歧义的强词（雨/晴/日头/阴天/阴沉/天阴/雪/雾/雷/潮气）沿用子串命中。
# 单调性（可机械验证）：v2 命中集合 ⊆ v1 命中集合 ⇒ 每个批次的 v2 计数不可能超过 v1。

#: 无歧义强词：出现即算（v1 的同名子集，语义未改）
V2_STRONG_WORDS: tuple[str, ...] = ("下雨", "雨天", "落雨", "雨丝", "雨点", "雨", "晴", "日头",
                                    "阴天", "阴着", "阴沉", "天阴", "雪", "雾", "雷", "潮气")

#: 弱词的「天气义词组」白名单：命中其中任一短语才算天气提及
V2_PHRASES: dict[str, tuple[str, ...]] = {
    # 晒：天气义 = 日晒/晒到人/晾晒对象是"晒不晒得着"这件事，而非作物/药材的加工工艺
    "晒": ("日头", "太阳", "太晒", "好晒", "晒得人", "晒得慌", "晒得发懒", "晒不着", "晒不到",
           "晒进来", "晒东西", "晒货", "晒衣裳", "晒被子", "晒被褥", "晒蔫", "晒死", "晒化",
           "晒黑", "晒成", "晒得难受", "晒得烫"),
    # 湿：天气义 = 空气/天气的湿度，而非某个物件的潮湿状态
    "湿": ("湿气", "潮湿", "湿冷", "湿得", "太湿", "好湿", "很湿", "湿透", "湿漉", "湿了"),
    # 云：天气义 = 天上的云，而非招式/食物/人名
    "云": ("云彩", "乌云", "云层", "云压", "云低", "云厚", "云散", "云开", "云影", "云头"),
    # 风：天气义 = 风本身（大小/方向/吹在身上的感觉），而非器物/药材/疾病/社交比喻
    "风": ("风大", "刮风", "起风", "有风", "风里", "风一刮", "风刮", "风吹", "风扯", "风还是",
           "风往", "风能", "风从", "风压", "阵风", "寒风", "热风", "风沙"),
    # 霜：裸字即天气义，只需排除食物/盐析出的"霜"
    "霜": ("霜",),
}

#: 弱词的「非天气复合词」黑名单：命中跨度内的白名单短语作废（工艺/器物/招式/药材/场所）
V2_WEAK_DENY: dict[str, tuple[str, ...]] = {
    "晒": ("晒干", "晒场", "晒谷场", "晒盐", "晒台", "晒席", "晒网", "晒的", "晒好",
           "晒了一半", "晒晒", "晒得干爽", "晒得皮都", "晒得皮起", "晒得很干"),
    "湿": ("湿布", "湿泥", "湿面", "湿柴", "湿衣", "湿手", "湿巾", "湿土", "湿抹布", "风湿"),
    "云": ("云手", "云吞", "云鬓", "云集", "云游", "云纹", "云锦"),
    "风": ("风箱", "风门", "风干", "防风", "风头", "跟风", "风气", "风味", "风凉话", "漏风",
           "带风", "挡风", "避风", "风车", "风铃", "风灯", "风镜", "风湿", "风衣", "风帽", "风袋"),
    "霜": ("糖霜", "柿霜", "盐霜", "霜糖"),
}

#: 边界条目：命中这些短语的样本会计入 v2 主口径，但同时单列 `_no_borderline` 变体供敏感性核对
V2_BORDERLINE_PHRASES: tuple[str, ...] = ("晒不着", "晒不到")


def _spans(text: str, pats: tuple[str, ...]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for pat in pats:
        for m in re.finditer(re.escape(pat), text):
            out.append(m.span())
    return out


def classify_v2(text: str) -> dict:
    """口径 v2：把一条正文判定为「天气提及 / 非天气提及」，并逐词留痕。

    返回：kept_words（计入的弱词）、kept_strong（计入的强词）、kept_phrases（命中的词组）、
         dropped（被排除的词及规则依据）、is_weather、borderline_only（仅靠边界短语成立）。
    """
    kept_strong = [w for w in V2_STRONG_WORDS if w in text]
    kept_words: list[str] = []
    kept_phrases: list[str] = []
    dropped: list[dict] = []
    borderline_only = False
    for word, phrases in V2_PHRASES.items():
        deny = _spans(text, V2_WEAK_DENY[word])
        hit = None
        for ph in phrases:
            for m in re.finditer(re.escape(ph), text):
                s, e = m.span()
                if any(a <= s and e <= b for a, b in deny):
                    continue
                hit = ph
                break
            if hit:
                break
        if hit:
            kept_words.append(word)
            kept_phrases.append(hit)
        elif word in text:
            matched = [p for p in V2_WEAK_DENY[word] if p in text]
            dropped.append({"word": word,
                            "reason": "denylist_compound" if matched else "no_weather_phrase",
                            "matched": matched})
    is_weather = bool(kept_strong or kept_words)
    if is_weather:
        non_border = [p for p in kept_phrases if p not in V2_BORDERLINE_PHRASES]
        borderline_only = bool(kept_phrases) and not kept_strong and not non_border
    return {"kept_strong": kept_strong, "kept_words": kept_words, "kept_phrases": kept_phrases,
            "dropped": dropped, "is_weather": is_weather, "borderline_only": borderline_only}


def newcombe95(k1: int, n1: int, k2: int, n2: int, z: float = 1.96) -> list[float] | None:
    """两独立比例的差值 95% 区间（Newcombe 1998 method 10，基于 Wilson score 区间）。

    CI = (d - l, d + u)，l = sqrt((p1 - l1)^2 + (u2 - p2)^2)，u = sqrt((u1 - p1)^2 + (p2 - l2)^2)。
    任一分母为 0 ⇒ None（不报假区间）。
    """
    if n1 <= 0 or n2 <= 0:
        return None
    w1 = wilson(k1, n1, z)
    w2 = wilson(k2, n2, z)
    if not w1 or not w2:
        return None
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = w1
    l2, u2 = w2
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return [max(-1.0, lo), min(1.0, hi)]


#: 首分句切分符（L-7 口径：第一个实质分句）。
CLAUSE_SEPS = re.compile(r"[，。！？；、,.!?;\n（）()「」“”\"'…—~]+")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson 95% 区间。n=0 ⇒ None（不报假区间）。"""
    if n <= 0:
        return None
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def _open(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, encoding="utf-8")


def _first_clause(body: str) -> str:
    for piece in CLAUSE_SEPS.split(body or ""):
        piece = piece.strip()
        if len(piece) >= 2:
            return piece
    return (body or "").strip()


def _hits(text: str, words: tuple[str, ...]) -> list[str]:
    out = []
    for w in words:
        if w and w in text:
            out.append(w)
    return out


def _denoise_spans(text: str) -> list[tuple[int, int]]:
    return [m.span() for pat in NON_WEATHER_PATTERNS
            for m in re.finditer(re.escape(pat), text)]


def _valid_hit(text: str, word: str, spans: list[tuple[int, int]]) -> bool:
    """至少有一次 word 的出现**不落**在任何去噪构词的跨度内。"""
    for m in re.finditer(re.escape(word), text):
        s, e = m.span()
        if not any(a <= s and e <= b for a, b in spans):
            return True
    return False


def _load_weather_module(path: Path):
    """离线反推当天真值：code/life/weather.py 为纯函数模块（仅 import hashlib/os），无副作用。"""
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location("c28_weather_for_readings", str(path))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify_situational(body: str, day: int | None, kind: str | None) -> dict:
    """按研判规则（v2/evidence/weather_c28_adjudication_rules.md）给一条 MSG 定性。"""
    spans = _denoise_spans(body)
    said_groups: set[str] = set()
    hit_words: list[str] = []
    for group, words in DIRECTION_GROUPS.items():
        for w in words:
            if _valid_hit(body, w, spans):
                said_groups.add(group)
                hit_words.append(w)
    undet_words = [w for w in UNDETERMINED_WORDS if _valid_hit(body, w, spans)]
    if day is None or not kind:
        return {"verdict": "unclassified", "said_groups": sorted(said_groups),
                "hit_words": hit_words, "undetermined_words": undet_words,
                "expected_group": None}
    expected = KIND_TO_GROUP.get(kind)
    if said_groups:
        if expected is not None and expected in said_groups:
            verdict = "direction_consistent"
        else:
            verdict = "direction_inconsistent"
    elif undet_words:
        verdict = "undetermined_direction"
    else:
        verdict = "non_weather"
    return {"verdict": verdict, "said_groups": sorted(said_groups), "hit_words": hit_words,
            "undetermined_words": undet_words, "expected_group": expected}



def read_arm(path: Path, wx_mod=None, world_seed: int = 42) -> dict:
    """读一条 run.jsonl（或 .gz），只认 MSG_DM / MSG_PUBLIC / MSG_GROUP 的 payload.body。"""
    n_msgs = 0
    n_bodies = 0
    phen_hit = felt_hit = season_hit = 0
    phen_words: dict[str, int] = {}
    felt_words: dict[str, int] = {}
    season_words: dict[str, int] = {}
    # —— 口径 v2（词组级上下文约束）——
    phen_hit_v2 = 0
    phen_hit_v2_no_borderline = 0
    phen_words_v2: dict[str, int] = {}
    v2_fp_rows: list[dict] = []
    v2_only_hits = 0          # v1 未命中但 v2 命中（单调性守卫，应恒为 0）
    v2_dropped_total = 0
    ctx_weather_msgs = 0
    ctx_weather_dist: dict[str, int] = {}
    ctx_season_dist: dict[str, int] = {}
    ctx_seed: set = set()
    by_day: dict[int, dict] = {}
    first_clauses: dict[str, int] = {}
    mark_leak = 0
    chars = 0
    # —— 情境一致性三分法（CYCLE-28）——
    sit = {"direction_consistent": 0, "direction_inconsistent": 0,
           "undetermined_direction": 0, "non_weather": 0, "unclassified": 0}
    sit_examples: dict[str, list] = {k: [] for k in sit}
    sit_pairs: dict[str, int] = {}
    sit_by_day: dict[int, dict] = {}
    derived_mismatch = 0

    with _open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
                continue
            n_msgs += 1
            p = ev.get("payload") or {}
            body = (p.get("body") or "").strip()
            ctx = p.get("ctx") or {}
            day = p.get("day")
            try:
                day_i = int(day) if day is not None else -1
            except (TypeError, ValueError):
                day_i = -1
            slot = by_day.setdefault(day_i, {"msgs": 0, "phen_hit": 0, "weather": None,
                                             "season": None})
            slot["msgs"] += 1

            wx = ctx.get("weather") if isinstance(ctx, dict) else None
            if isinstance(wx, dict) and wx.get("weather"):
                ctx_weather_msgs += 1
                slot["weather"] = wx.get("weather")
                slot["season"] = wx.get("season")
                if wx.get("weather"):
                    ctx_weather_dist[str(wx["weather"])] = ctx_weather_dist.get(str(wx["weather"]), 0) + 1
                if wx.get("season"):
                    ctx_season_dist[str(wx["season"])] = ctx_season_dist.get(str(wx["season"]), 0) + 1
                if wx.get("seed") is not None:
                    ctx_seed.add(wx.get("seed"))

            if not body:
                continue
            n_bodies += 1
            chars += len(body)
            if PROMPT_MARK in body:
                mark_leak += 1
            ph = _hits(body, WEATHER_PHENOMENA)
            ft = _hits(body, WEATHER_FEEL)
            sn = _hits(body, SEASON_WORDS)
            if ph:
                phen_hit += 1
                slot["phen_hit"] += 1
                for w in ph:
                    phen_words[w] = phen_words.get(w, 0) + 1
            # —— 口径 v2：判一次，逐词留痕 ——
            v2 = classify_v2(body)
            if v2["is_weather"]:
                phen_hit_v2 += 1
                if not v2["borderline_only"]:
                    phen_hit_v2_no_borderline += 1
                for w in v2["kept_words"] + v2["kept_strong"]:
                    phen_words_v2[w] = phen_words_v2.get(w, 0) + 1
            if v2["is_weather"] and not ph:
                v2_only_hits += 1
            if ph:
                # 只对「v1 命中」的样本留归因行：v2 的每一次排除都必须能回到原文
                v2_dropped_total += len(v2["dropped"])
                v2_fp_rows.append({
                    "msg_uid": p.get("msg_uid"),
                    "day": day_i if day_i >= 0 else None,
                    "legacy_words": ph,
                    "v2_is_weather": v2["is_weather"],
                    "v2_kept_strong": v2["kept_strong"],
                    "v2_kept_words": v2["kept_words"],
                    "v2_kept_phrases": v2["kept_phrases"],
                    "v2_dropped": v2["dropped"],
                    "v2_borderline_only": v2["borderline_only"],
                    "body": body,
                })
            if ft:
                felt_hit += 1
                for w in ft:
                    felt_words[w] = felt_words.get(w, 0) + 1
            if sn:
                season_hit += 1
                for w in sn:
                    season_words[w] = season_words.get(w, 0) + 1
            fc = _first_clause(body)
            if fc:
                first_clauses[fc] = first_clauses.get(fc, 0) + 1

            # —— 情境一致性三分法（当日真值走离线派生；ON 臂另与 ctx.weather 交叉核对）——
            if wx_mod is not None:
                kind = wx_mod.weather_of_day(day_i, world_seed) if day_i >= 0 else ""
                if isinstance(wx, dict) and wx.get("weather") and kind and str(wx["weather"]) != kind:
                    derived_mismatch += 1
                cls = classify_situational(body, day_i if day_i >= 0 else None, kind or None)
                v = cls["verdict"]
                sit[v] += 1
                dslot = sit_by_day.setdefault(day_i, {"msgs": 0, "derived_kind": kind or None,
                                                     "direction_consistent": 0,
                                                     "direction_inconsistent": 0,
                                                     "undetermined_direction": 0})
                dslot["msgs"] += 1
                if v in dslot:
                    dslot[v] += 1
                if v in ("direction_consistent", "direction_inconsistent"):
                    for g in cls["said_groups"]:
                        k = f"expected={cls['expected_group']}->said={g}"
                        sit_pairs[k] = sit_pairs.get(k, 0) + 1
                if len(sit_examples[v]) < 5:
                    sit_examples[v].append({
                        "day": day_i if day_i >= 0 else None, "msg_uid": p.get("msg_uid"),
                        "derived_kind": kind or None, "expected_group": cls["expected_group"],
                        "said_groups": cls["said_groups"], "hit_words": cls["hit_words"],
                        "undetermined_words": cls["undetermined_words"], "body": body[:80],
                    })

    uniq_fc = len(first_clauses)
    top_fc = sorted(first_clauses.items(), key=lambda kv: (-kv[1], kv[0]))[:10]

    def _rate(k: int) -> dict:
        lo_hi = wilson(k, n_bodies)
        return {"count": k, "n": n_bodies,
                "rate": (k / n_bodies) if n_bodies else None,
                "wilson95": list(lo_hi) if lo_hi else None}

    return {
        "run": str(path),
        "n_msgs": n_msgs,
        "n_bodies": n_bodies,
        "body_chars_avg": round(chars / n_bodies, 2) if n_bodies else None,
        "weather_mention_strict": _rate(phen_hit),
        # —— 口径 v2（词组级上下文约束；旧字段名与旧数值均未改）——
        "weather_mention_strict_v2": _rate(phen_hit_v2),
        "weather_mention_strict_v2_no_borderline": _rate(phen_hit_v2_no_borderline),
        "v2_guard": {
            "v2_only_hits": v2_only_hits,
            "v2_subset_of_v1": v2_only_hits == 0,
            "v2_dropped_hits_total": v2_dropped_total,
            "v1_hit_bodies": phen_hit,
            "v2_hit_bodies": phen_hit_v2,
        },
        "weather_words_top_v2": sorted(phen_words_v2.items(), key=lambda kv: (-kv[1], kv[0]))[:10],
        "v2_fp_attribution": v2_fp_rows,
        "weather_mention_feel": _rate(felt_hit),
        "season_mention": _rate(season_hit),
        "weather_words_top": sorted(phen_words.items(), key=lambda kv: (-kv[1], kv[0]))[:10],
        "feel_words_top": sorted(felt_words.items(), key=lambda kv: (-kv[1], kv[0]))[:10],
        "season_words_top": sorted(season_words.items(), key=lambda kv: (-kv[1], kv[0]))[:10],
        "ctx_weather": {
            "msgs_with_ctx_weather": ctx_weather_msgs,
            "share_of_msgs": (ctx_weather_msgs / n_msgs) if n_msgs else None,
            "weather_dist": dict(sorted(ctx_weather_dist.items())),
            "season_dist": dict(sorted(ctx_season_dist.items())),
            "seeds": sorted(s for s in ctx_seed if s is not None),
        },
        "l7_first_clause": {
            "unique": uniq_fc,
            "total": n_bodies,
            "dup_rate": (1 - uniq_fc / n_bodies) if n_bodies else None,
            "top10": [{"clause": c, "n": n} for c, n in top_fc],
        },
        "prompt_mark_leak_in_body": mark_leak,
        "situational_consistency": {
            "rules_doc": "v2/evidence/weather_c28_adjudication_rules.md（先固化后看 ON，2026-10-29T20:39）",
            "world_seed": world_seed,
            "direction_consistent": sit["direction_consistent"],
            "direction_inconsistent": sit["direction_inconsistent"],
            "undetermined_direction": sit["undetermined_direction"],
            "non_weather": sit["non_weather"],
            "unclassified": sit["unclassified"],
            "denominator_direction_claims": sit["direction_consistent"] + sit["direction_inconsistent"],
            "denominator_bodies": n_bodies,
            "consistency_rate_among_direction_claims": (
                sit["direction_consistent"] / (sit["direction_consistent"] + sit["direction_inconsistent"])
                if (sit["direction_consistent"] + sit["direction_inconsistent"]) else None),
            "said_vs_expected_pairs": dict(sorted(sit_pairs.items())),
            "derived_vs_ctx_mismatch": derived_mismatch,
            "by_day": {str(k): v for k, v in sorted(sit_by_day.items())},
            "examples": sit_examples,
        },
        "by_day": {str(k): v for k, v in sorted(by_day.items())},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="天气/季节臂读数器（纯读 run.jsonl，零 LLM）")
    ap.add_argument("runs", nargs="*", help="run.jsonl 路径（可多个，标签自动取父目录名）")
    ap.add_argument("--arm", action="append", default=[],
                    metavar="LABEL=PATH", help="带标签的臂，如 --arm on=path/to/run.jsonl")
    ap.add_argument("--json", default=None, help="读数输出路径（缺省打印到 stdout）")
    ap.add_argument("--world-seed", type=int, default=42,
                    help="情境一致性用的 HITT_WORLD_SEED（两臂必须同值；缺省 42）")
    ap.add_argument("--no-situational", action="store_true",
                    help="跳过情境一致性三分法（只出 strict/feel 等原始计数）")
    args = ap.parse_args()

    arms: dict[str, Path] = {}
    for spec in args.arm:
        if "=" not in spec:
            raise SystemExit(f"--arm 需要 LABEL=PATH 形式，收到：{spec}")
        label, path = spec.split("=", 1)
        arms[label.strip()] = Path(path.strip())
    for r in args.runs:
        p = Path(r)
        arms[p.parent.name or str(p)] = p
    if not arms:
        raise SystemExit("至少给一个 run.jsonl（位置参数或 --arm LABEL=PATH）")

    wx_mod = None
    if not args.no_situational:
        wpy = Path(__file__).resolve().parents[2] / "code" / "life" / "weather.py"
        if wpy.exists():
            wx_mod = _load_weather_module(wpy)

    out: dict = {"ruler": {"ruler_version": 2,
                           "ruler_doc_v2": "v2/refs/W-1-lexicon-v2.md（词组级上下文约束，2026-11-01 冻结）",
                           "weather_phenomena": list(WEATHER_PHENOMENA),
                           "weather_phenomena_v2_strong": list(V2_STRONG_WORDS),
                           "weather_phenomena_v2_phrases": {k: list(v) for k, v in V2_PHRASES.items()},
                           "weather_phenomena_v2_deny": {k: list(v) for k, v in V2_WEAK_DENY.items()},
                           "v2_borderline_phrases": list(V2_BORDERLINE_PHRASES),
                           "weather_feel": list(WEATHER_FEEL),
                           "season_words": list(SEASON_WORDS),
                           "prompt_mark": PROMPT_MARK,
                           "direction_groups": {k: list(v) for k, v in DIRECTION_GROUPS.items()},
                           "undetermined_words": list(UNDETERMINED_WORDS),
                           "non_weather_patterns": list(NON_WEATHER_PATTERNS),
                           "kind_to_group": dict(KIND_TO_GROUP),
                           "situational_enabled": wx_mod is not None,
                           "world_seed": args.world_seed},
                 "arms": {}}
    for label, path in arms.items():
        if not path.exists():
            out["arms"][label] = {"run": str(path), "error": "file not found"}
            continue
        out["arms"][label] = read_arm(path, wx_mod=wx_mod, world_seed=args.world_seed)

    # 两臂对照摘要（存在 off/on 时给差值；差值不做判定，只给读数）
    a = out["arms"].get("off") or {}
    b = out["arms"].get("on") or {}
    if a.get("n_bodies") and b.get("n_bodies"):
        def _delta(key):
            ra = (a.get(key) or {}).get("rate")
            rb = (b.get(key) or {}).get("rate")
            return None if ra is None or rb is None else round(rb - ra, 6)
        out["contrast_on_minus_off"] = {
            "weather_mention_strict": _delta("weather_mention_strict"),
            "weather_mention_feel": _delta("weather_mention_feel"),
            "season_mention": _delta("season_mention"),
            "l7_dup_rate": (None if a["l7_first_clause"]["dup_rate"] is None
                            or b["l7_first_clause"]["dup_rate"] is None
                            else round(b["l7_first_clause"]["dup_rate"]
                                       - a["l7_first_clause"]["dup_rate"], 6)),
            "note": "差值仅供判定件引用，阈值与可判/不可判口径见 v2/refs/W-1-weather-prereg.md",
        }
        # —— 口径 v2（主判据用这一套；Δ 的区间一律 Newcombe95）——
        def _ci(key):
            ra, rb = a.get(key) or {}, b.get(key) or {}
            if not ra.get("n") or not rb.get("n"):
                return None
            return newcombe95(rb["count"], rb["n"], ra["count"], ra["n"])
        as_v2 = a.get("weather_mention_strict_v2") or {}
        bs_v2 = b.get("weather_mention_strict_v2") or {}
        out["contrast_on_minus_off_v2"] = {
            "weather_mention_strict_v2": {
                "off": as_v2, "on": bs_v2,
                "delta_pp": (None if not as_v2.get("n") or not bs_v2.get("n")
                             else round((bs_v2["rate"] - as_v2["rate"]) * 100, 4)),
                "newcombe95_pp": (None if not _ci("weather_mention_strict_v2")
                                  else [round(x * 100, 4) for x in _ci("weather_mention_strict_v2")]),
                "crosses_zero": (None if not _ci("weather_mention_strict_v2")
                                 else _ci("weather_mention_strict_v2")[0] <= 0 <= _ci("weather_mention_strict_v2")[1]),
            },
            "weather_mention_strict_v2_no_borderline": {
                "off": a.get("weather_mention_strict_v2_no_borderline"),
                "on": b.get("weather_mention_strict_v2_no_borderline"),
                "delta_pp": (None if not (a.get("weather_mention_strict_v2_no_borderline") or {}).get("n")
                             or not (b.get("weather_mention_strict_v2_no_borderline") or {}).get("n")
                             else round(((b["weather_mention_strict_v2_no_borderline"]["rate"]
                                          - a["weather_mention_strict_v2_no_borderline"]["rate"]) * 100), 4)),
            },
            "weather_mention_strict_v1_legacy": {
                "off": a.get("weather_mention_strict"), "on": b.get("weather_mention_strict"),
                "delta_pp": (None if not _ci("weather_mention_strict")
                             else round((b["weather_mention_strict"]["rate"]
                                         - a["weather_mention_strict"]["rate"]) * 100, 4)),
                "newcombe95_pp": (None if not _ci("weather_mention_strict")
                                  else [round(x * 100, 4) for x in _ci("weather_mention_strict")]),
            },
            "season_mention": {
                "delta_pp": (None if not _ci("season_mention")
                             else round((b["season_mention"]["rate"] - a["season_mention"]["rate"]) * 100, 4)),
                "newcombe95_pp": (None if not _ci("season_mention")
                                  else [round(x * 100, 4) for x in _ci("season_mention")]),
            },
            "weather_mention_feel": {
                "delta_pp": (None if not _ci("weather_mention_feel")
                             else round((b["weather_mention_feel"]["rate"] - a["weather_mention_feel"]["rate"]) * 100, 4)),
                "newcombe95_pp": (None if not _ci("weather_mention_feel")
                                  else [round(x * 100, 4) for x in _ci("weather_mention_feel")]),
            },
            "note": "v1 与 v2 是两把尺子，必须并列、不得混用；主判据口径见 v2/refs/W-1-lexicon-v2.md §5",
        }

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8")
        print(f"[weather-readings] wrote {args.json}")
        for label, d in out["arms"].items():
            if "error" in d:
                print(f"  {label}: ERROR {d['error']}")
                continue
            ws = d["weather_mention_strict"]
            rate_txt = "n/a" if ws["rate"] is None else f"{ws['rate']:.3f}"
            v2 = d["weather_mention_strict_v2"]
            v2txt = "n/a" if v2["rate"] is None else f"{v2['rate']:.3f}"
            print(f"  {label}: msgs={d['n_msgs']} bodies={d['n_bodies']} "
                  f"weather_strict={ws['count']}/{ws['n']}={rate_txt} "
                  f"weather_strict_v2={v2['count']}/{v2['n']}={v2txt} "
                  f"(subset_ok={d['v2_guard']['v2_subset_of_v1']}) "
                  f"ctx_weather={d['ctx_weather']['msgs_with_ctx_weather']} "
                  f"l7_dup={d['l7_first_clause']['dup_rate']}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
