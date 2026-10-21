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

判据（两条确定性来源，优先级固定）：
  1. **语面极性** `life/emotion.emotion_sign(对方上一句)`（**单一真源复用**，不另写一份）
     → `+1 / -1 / 0`；
  2. **处境情绪** 入站消息 `payload["ctx"]["mood"]`（发送方生成时由
     `dialogue_threads.mood_label(其自身 needs)` 算出的确定性标签）→ 查表得极性与严重度。
  合成规则：**语面有极性则语面优先**（"ta 刚说的这句话"比"ta 的处境"更贴近当下），
  否则用处境情绪；两者都为 0 → 不呼应（宁缺毋滥）。
  强度：语面命中 ⇒ `text_hit_intensity + mood_severity // mood_bonus_div`；仅处境 ⇒ 严重度；
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
VERSION = "f3/1"

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
    if sign_txt != 0:
        sign = sign_txt
        source = "text+mood" if m_sev > 0 else "text"
        intensity = int(p["text_hit_intensity"]) + (m_sev // int(p["mood_bonus_div"]))
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
