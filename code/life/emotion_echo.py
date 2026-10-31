"""F-3「情绪呼应」（empathic echo）——让回应方**接住对方的情绪**，而不只是各说各的。

问题（侦察事实）：`life/emotion.py` 只做「生成时表达**自己**的情绪」与反思极性判定，
仓库里**没有任何**「回应方识别并回应**对话对象**情绪」的机制
（`grep -rniE "empath|echo|呼应|共情" code/life/*.py` 零命中）。

本模块补齐这一条，并且**只放在措辞/上下文层**（与 `dialogue_threads.py` /
`dialogue_repair.py` 同一分层约定）：
  * **不产生事件类型、不改世界态、不进 `state_hash`**；
  * **不调用 LLM、不由 LLM 决定任何数值**——判定与强度是纯函数（无墙钟/随机/网络）；
  * 只做两件事：① 确定性判定「对方此刻是什么情绪、多强」；② 把结论作为一句
    **处境提示**插进回复提示词（+ 一个只追加的审计字段），措辞仍由 LLM 自己产出。

判据（三条确定性来源，优先级固定）：
  1. **语面极性** `life/emotion.emotion_sign(对方上一句)`（**单一真源复用**，不另写一份）
     → `+1 / -1 / 0`；
  2. **处境情绪** 入站消息 `payload["ctx"]["mood"]`（发送方生成时由
     `dialogue_threads.mood_label(其自身 needs)` 算出的确定性标签）→ 查表得极性与严重度。
  3. **对话语域线索**（R38 新增，`DIALOGUE_NEG_CUES` / `DIALOGUE_POS_CUES`）——**只在 ① 判 0 时**才看。
     存在原因有实测依据：`emotion.NATURAL_*` 是给 reflection 正文写的**抽象心理词表**，而真实对话是
     "盐放多了有点发苦 / 手都磨出泡了 / 孩子这两天咳得厉害"这类**具体口述**，① 在对话上几乎恒 0
     ⇒ 只能靠 ②，而 ② 一旦是「平和」就彻底不产（实测 7 次机会里 4 次如此，见 `v2/evidence/r38_f3/`）。
     整表可消融：`config/emotion_echo.json::dialogue_cues=false` ⇒ 逐字节退回 R14 行为。
  合成规则：**语面有极性则语面优先**（"ta 刚说的这句话"比"ta 的处境"更贴近当下），
  其次对话线索，其次处境情绪；全为 0 → 不呼应（宁缺毋滥）。
  强度：语面命中 ⇒ `text_hit_intensity + mood_severity // mood_bonus_div`；线索命中 ⇒
  `cue_hit_intensity + mood_severity // mood_bonus_div`；仅处境 ⇒ 严重度；
  再与 `min_intensity` 比，**低于阈值不产**。

开关（单 env 开关 + 单配置文件，沿用 `code/config/dialogue_repair.json` 先例）：
  * `config/emotion_echo.json::enabled`（默认 **false**）；
  * env 逃生口/消融口 `HITT_DIALOGUE_EMOTION_ECHO` ∈ {1,true,on,yes} → 开，
    **其它任何取值（含 0/false/off/no/空字符串/拼错）→ 关**。
  本文件**不进** `engine/version.py::FINGERPRINT_FILES` ⇒ 开/关都不改 engine_version 指纹。
  **关闭（默认）时**：`plan()` 永不产出、`prompt_line()` 恒空串、agent 侧不写
  `dialogue_echo` 字段 ⇒ 提示词与事件 payload 与接入前**逐字节一致**。

结构化可观测信号（只追加，写进 MSG payload 的 `ctx` 段，与 `ctx.memory_refs` /
`ctx.dequp` 同一先例；`orchestration/integration.py::_thread_fields` 对顶层新键有白名单，
而 `ctx` 是整体透传的 ⇒ **本轮不动 orchestration** 也能落进日志）：
    payload["ctx"]["echo"] = {
      "v": "f3/1",
      "sign": -1 | 1,          # 呼应方向（负=安抚，正=顺着高兴劲儿接）
      "intensity": int,        # 0..100（确定性推导，见上）
      "tier": "轻" | "明显" | "很强",
      "kind": "soothe" | "cheer",
      "source": "text" | "mood" | "text+mood",
      "mood": str | None,      # 对方 ctx.mood 原值（无则 None）
      "prompted": True,        # 本条是否真把处境提示放进了提示词（与 prompt_line 一致）
    }
  关闭 / 不产（sign=0 或低于阈值）时日志里**一条都没有**。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import emotion as E

#: 单 env 开关（消融/逃生口）：{1,true,on,yes} → 开；其它任何值（含空串/拼错）→ 关。
ECHO_ENV = "HITT_DIALOGUE_EMOTION_ECHO"

#: 信号版本（写进 payload，便于按版本复算）
VERSION = "f3/2"

#: 对话语域线索（**R38 新增的第三来源，只在 `emotion.emotion_sign` 判 0 时才用**）。
#:
#: 为什么需要它（可复算的实测缺口，见 `v2/evidence/r38_f3/BEFORE_f3_offline_replay.json`）：
#: `life/emotion.py::NATURAL_*` 的词表是为 **`MEMORY_WRITE kind=="reflection"`** 正文设计的
#: ——里面是「担心/遗憾/疲惫/委屈」这类**抽象心理词**；而对话正文是**具体的市井口述**
#: （"盐放多了有点发苦"、"手都磨出泡了"、"孩子这两天咳得厉害"），一个抽象心理词都不含。
#: 于是 `emotion_sign` 在真实对话上退回 0 ⇒ F-3 的语面通道几乎恒空，只能靠 `ctx.mood` 兜底，
#: 而 `ctx.mood` 一旦是「平和」就彻底不产（emo-off 语料 7 次机会里 4 次如此）。
#:
#: 纪律（三条，缺一不可）：
#:   1. **不碰 `life/emotion.py`**：那是 reflection 判定的单一真源，alter 它会让 R/T333
#:      历史读数不可比。本表是**对话语域的补充**，只在本模块生效、可整表消融（`dialogue_cues`）；
#:   2. **方向语义与 `emotion_sign` 一致**（−1 负向需安抚 / +1 正向可顺着接），不引入第三极性；
#:   3. **只在 `emotion_sign == 0` 时启用**（不覆盖单一真源的任何判断），且线索**只取具体搭配**
#:      （不收「累/苦/病」这类单字，避免"说话不带情绪"被误判成有事）。
#: 【未验证】：本表未经人工标注集校验，只由 `tools/f3/f3_offline_replay.py` 做落点覆盖回放。
DIALOGUE_NEG_CUES: tuple[str, ...] = (
    # 身体/病痛
    "咳得", "咳嗽", "发烧", "发热", "头晕", "腰酸", "腿软", "喘不上", "磨出泡", "起了泡",
    "睡不着", "没睡好", "熬了", "撑不住", "直打颤", "手抖", "犯了病", "疼得", "肿了",
    # 劳作/亏损/不顺
    "发苦", "发涩", "馊了", "坏了", "烂了", "漏了", "赔了", "亏了", "砸了", "白忙",
    "欠着", "不够使", "漏雨", "散了架", "找不着",
    # 情绪外显（口述）
    "犯愁", "发愁", "心急", "发慌", "难受", "心里堵", "没了主意",
)
DIALOGUE_POS_CUES: tuple[str, ...] = (
    # 正向线索只收**陈述式**结果（"顺当"在"还顺当吗？"里是对别人的问候、不是自身好事，故不收）
    "办成了", "办妥", "卖完了", "卖出", "找着了", "考中", "添丁", "夸你", "高兴",
    "痛快", "妥了", "赚了", "修好了", "说定了",
)

#: 情绪标签 → (极性, 严重度)。标签来源限定为 `dialogue_threads.mood_label` 的枚举
#: （六个最匮乏需求维度的映射 + 平和），**未知标签一律 (0, 0) = 不呼应**。
MOOD_PROFILE: dict[str, tuple[int, int]] = {
    "疲惫": (-1, 45),
    "饥饿": (-1, 55),
    "孤单": (-1, 60),
    "低落": (-1, 55),
    "浮躁": (-1, 40),
    "紧绷": (-1, 40),
    "平和": (0, 0),
}

DEFAULTS = {
    "enabled": False,          # 总开关（默认关 = 既有路径逐字节不变）
    "criterion": "natural",    # `emotion.emotion_sign` 的判据档（单一真源，不另写词表）
    "min_intensity": 30,       # 强度阈值：低于此值不呼应（宁缺毋滥）
    "text_hit_intensity": 60,  # 语面命中情感词的基础强度
    "mood_bonus_div": 2,       # 语面命中时，处境严重度按此除数作加成
    "tier_cuts": [45, 70],     # 强度分档切点（→ 轻 / 明显 / 很强）；只用于文案，不进数值判定
    # R38：对话语域线索（第三来源，只在 emotion_sign==0 时用；`False` ⇒ 逐字节退回 R14 行为）
    "dialogue_cues": True,
    "cue_hit_intensity": 45,   # 线索命中的基础强度（≥ min_intensity 才会真产）
}

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "emotion_echo.json"
_cache: dict | None = None
_override: dict | None = None


# ---------------------------------------------------------------- 开关/参数
def load_params(path: str | Path | None = None) -> dict:
    """读 `config/emotion_echo.json`（缺省值 → 默认**关**）；支持 env 逃生口。

    env：`HITT_DIALOGUE_EMOTION_ECHO=1|true|on|yes` → 打开；
    **其余任何取值（含 `0|false|off|no|`空串|拼写错误）→ 关闭**（消融/回退用）。
    本文件不进 engine_version 指纹（默认关 ⇒ 旧日志 fingerprint 不受影响）。
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
    env = os.environ.get(ECHO_ENV)
    if env is not None:
        out["enabled"] = env.strip().lower() in ("1", "true", "on", "yes")
    out["enabled"] = bool(out["enabled"])
    out["criterion"] = str(out["criterion"])
    out["min_intensity"] = int(out["min_intensity"])
    out["text_hit_intensity"] = int(out["text_hit_intensity"])
    out["mood_bonus_div"] = max(1, int(out["mood_bonus_div"]))
    out["dialogue_cues"] = bool(out["dialogue_cues"])
    out["cue_hit_intensity"] = max(0, min(100, int(out["cue_hit_intensity"])))
    cuts = [int(x) for x in (out["tier_cuts"] or DEFAULTS["tier_cuts"])]
    out["tier_cuts"] = cuts[:2] if len(cuts) >= 2 else list(DEFAULTS["tier_cuts"])
    if path is None:
        _cache = dict(out)
    return out


def set_override(d: dict | None) -> None:
    """Test/ablation hook：强制参数（None 清除并重读）。不落盘、不改指纹。"""
    global _override, _cache
    _override = dict(d) if d else None
    if d is None:
        _cache = None


def reload() -> None:
    """清进程内配置缓存（改了 json / env 后让下一次 `load_params()` 真读盘）。"""
    global _cache
    _cache = None


def enabled() -> bool:
    """单开关：True 才做情绪呼应；默认 False（既有路径逐字节不变）。"""
    return bool(load_params()["enabled"])


# ---------------------------------------------------------------- 确定性判定
def tier_of(intensity: int, cuts: list[int]) -> str:
    """强度 → 文案分档（只影响提示词语气，不参与数值判定）。"""
    lo, hi = int(cuts[0]), int(cuts[1])
    n = int(intensity)
    if n < lo:
        return "轻"
    if n < hi:
        return "明显"
    return "很强"


def detect(mood_label: str | None, partner_text: str | None,
           params: dict | None = None) -> dict:
    """判定对方情绪：返回 {sign, intensity, tier, source, mood, kind}（纯函数、确定性）。

    `sign`：−1=负向（需安抚）/ +1=正向（可顺着接）/ 0=不判（→ 不呼应）。
    优先级：语面极性（`emotion.emotion_sign` 单一真源）> 处境情绪（`ctx.mood` 查表）。
    """
    p = params or load_params()
    mood = (mood_label or "").strip() or None
    m_sign, m_sev = MOOD_PROFILE.get(mood or "", (0, 0))
    sign_txt = int(E.emotion_sign(partner_text or "", criterion=p["criterion"]))
    cue_sign = 0
    if sign_txt == 0 and p.get("dialogue_cues", True):
        # 第三来源（R38）：对话语域线索，**只在单一真源判 0 时**兜底；不覆盖任何既有判断。
        # 负向线索优先判（"发苦还笑了一下"这类混合句按需安抚处理，宁缺毋滥）。
        low = (partner_text or "").lower()
        if any(c in low for c in DIALOGUE_NEG_CUES):
            cue_sign = -1
        elif any(c in low for c in DIALOGUE_POS_CUES):
            cue_sign = 1
    if sign_txt != 0:
        sign = sign_txt
        source = "text+mood" if m_sev > 0 else "text"
        intensity = int(p["text_hit_intensity"]) + (m_sev // int(p["mood_bonus_div"]))
    elif cue_sign != 0:
        sign = cue_sign
        source = "cue+mood" if m_sev > 0 else "cue"
        intensity = int(p["cue_hit_intensity"]) + (m_sev // int(p["mood_bonus_div"]))
    elif m_sign != 0:
        sign = m_sign
        source = "mood"
        intensity = m_sev
    else:
        sign, source, intensity = 0, "none", 0
    intensity = max(0, min(100, int(intensity)))
    return {"sign": sign, "intensity": intensity, "source": source, "mood": mood,
            "tier": tier_of(intensity, p["tier_cuts"]),
            "kind": ("soothe" if sign < 0 else "cheer") if sign else "none"}


def plan(mood_label: str | None, partner_text: str | None,
         params: dict | None = None) -> dict | None:
    """呼应计划：开关关 / sign==0 / 强度低于阈值 → `None`（不产，调用方零副作用）。"""
    p = params or load_params()
    if not p["enabled"]:
        return None
    d = detect(mood_label, partner_text, p)
    if d["sign"] == 0 or int(d["intensity"]) < int(p["min_intensity"]):
        return None
    return d


def prompt_line(plan_dict: dict | None, name: str | None = None) -> str:
    """把呼应计划转成**一句处境提示**（关闭/无计划 ⇒ 空串，提示词逐字节不变）。

    只给「对方现在怎样」这一事实 + 一条做法要求（先接住情绪、别转话题到自己身上），
    **不给任何现成句式**（措辞由 LLM 产出，与 F-4 口径一致）。
    """
    if not plan_dict:
        return ""
    who = name or "对方"
    tier = plan_dict.get("tier") or "轻"
    mood = plan_dict.get("mood")
    if plan_dict.get("kind") == "soothe":
        what = f"{mood}" if mood else "情绪不大好"
        return (f"\n{who}这会儿{what}（{tier}）。先接住这份情绪再说自己的事："
                "用一句家常话回应ta的感受，别讲道理、别急着转到自己身上。")
    return (f"\n{who}这会儿心情不错（{tier}）。顺着这份劲儿接一句，别扫兴，"
            "也别把话头抢回自己身上。")


def audit(plan_dict: dict | None) -> dict | None:
    """只追加的审计字段（无计划 ⇒ None ⇒ payload 不多键）。"""
    if not plan_dict:
        return None
    return {"v": VERSION, "sign": int(plan_dict["sign"]),
            "intensity": int(plan_dict["intensity"]), "tier": plan_dict["tier"],
            "kind": plan_dict["kind"], "source": plan_dict["source"],
            "mood": plan_dict.get("mood"), "prompted": True}
