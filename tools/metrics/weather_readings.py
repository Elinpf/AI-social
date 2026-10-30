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
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
from pathlib import Path

# ---------------------------------------------------------------- 口径（改这里＝改尺子）
#: 天气**现象**词（严格口径）：雨/雪/晴/阴/云/风/日头/晒/雾/霜/雷/潮/湿。
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

    out: dict = {"ruler": {"weather_phenomena": list(WEATHER_PHENOMENA),
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
            print(f"  {label}: msgs={d['n_msgs']} bodies={d['n_bodies']} "
                  f"weather_strict={ws['count']}/{ws['n']}={rate_txt} "
                  f"ctx_weather={d['ctx_weather']['msgs_with_ctx_weather']} "
                  f"l7_dup={d['l7_first_clause']['dup_rate']}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
