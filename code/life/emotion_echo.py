"""F-3「情绪呼应」（empathic echo）——让回应方**接住对方的情绪**，而不只是各说各的。

## R31 改了什么（本轮=「改指令形态」，不是改开关）

R14 的读数（`reports/R14-f3-emotion-echo.md` §0.1）：ON 臂 295 条触发里「确实接住」
仅 37 条 = **12.54%**，且 L-7 8-gram 重复率被击穿（+9.72pp）。R31 的离线诊断
（`reports/r31-impl-note.md` §2，脚本 `tools/f3/r31_diagnose.py`）把 12.54% 归成两条：

  ① **触发口径失真（分母污染）**：295 条里 **273 条（92.54%）**被回复的那一句
     **不含任何情绪词**——触发来自发送方自己的处境标签 `ctx.mood`
     （`source=mood` 252 条中 235 条无文本证据）。提示词说"对方现在低落"，
     而模型看到的对话文本里没有这句依据 ⇒ 提示与可见文本**互相矛盾**，模型只能忽略。
  ② **指令形态太软**：`prompt_line` 是插在对话正文前的**一句散文式要求**，
     既没有把"证据"摆出来，也没有把"这一句必须做到什么"结构化，更没有可校验的产出。

于是本轮把「一句追加」换成**结构化硬约束块**，并加两道确定性闸门：

  * **证据门控**（`require_text_evidence`，默认 true）：只有**对方那句话本身**确有
    情绪证据（`emotion_sign != 0`，即 `source ∈ {text, text+mood}`）才产提示；
    仅处境标签（`source == "mood"`）不再触发（这正是 92.54% 的噪声来源）。
    置 false 可复现 R14 旧口径（消融用，不参与默认行为）。
  * **结构块**（`prompt_line`）：显式「情绪标注行 + 证据原话 + 三条硬要求 +
    确定性轮转的回应形态」，仍**不给现成句式**（措辞由 LLM 产出，与 F-4 口径一致）。

并且**不引入新的自由文本自由度**：要求是**结构**约束（第一分句必须先接住情绪、
第一分句里要有对对方的指称、应声之后不许直接转话题），不是句式模板；
模型**不需要输出任何标签/标记**（拒绝让标记进台词：L-13 内部 token 泄漏守卫与
OFF 逐字节等价都会被破坏）。"可校验"改为**生成后确定性自检** `verify()`，
结果只落 `ctx.echo.verify`（只追加的审计字段，不是报告口径）。

## N-05：生成侧「第一分句线索」闸门（`cue_repair`，默认 True，**只在开关打开时生效**）

R31 把触发口径收紧了，但 CYCLE-34 ON 臂读数显示瓶颈换到了生成侧：`echo_msgs=107` 里
`verify_has_cue=7`、`verify_ack_then_switch=66`——即 **大多数回复第一分句根本没接住**，
应一声就转话题。N-05 只修这件事，**不加 echo 强度**（阈值/强度/触发口径一条没动）：

  * 提示词侧（`prompt_line` 硬要求 1）：补一句"第一分句里要出现一个表露情绪回应的字眼"；
  * **生成后闸门**：`verify()` 判 `need_rewrite()` 为真 ⇒ 用 `rewrite_line()` 追加一次
    重写要求，**最多重写一次**；重写结果 `rewrite_ok()` 为真才替换正文，否则**保留原文**
    （⇒ 结果**不劣于**修正前，不是"多喊几遍"）。记账只追加 `ctx.echo.verify.rewrite`。
  * OFF 臂（未设 `HITT_DIALOGUE_EMOTION_ECHO`）：`enabled()==False` ⇒ `plan()` 不产 ⇒
    agent 侧 `echo_audit is None` ⇒ **整段闸门不执行**，不多一次 LLM 调用、不改提示词/ payload。

## 分层与开关（与 R14 一致，未改）

  * **不产生事件类型、不改世界态、不进 `state_hash`**；
  * **不调用 LLM、不由 LLM 决定任何数值**——判定/强度/形态指派全是纯函数
    （无墙钟/随机/网络，哈希用 sha256 不用内置 hash）；
  * 开关：`config/emotion_echo.json::enabled`（默认 **false**）+
    env 消融口 `HITT_DIALOGUE_EMOTION_ECHO` ∈ {1,true,on,yes} → 开，其它任何取值 → 关；
  * 本文件**不进** `engine/version.py::FINGERPRINT_FILES` ⇒ 开/关都不改 engine_version 指纹；
  * **关闭（默认）时**：`plan()` 永不产出、`prompt_line()` 恒空串、agent 侧不写
    `ctx.echo` ⇒ 提示词与事件 payload 与接入前**逐字节一致**。

判据（两条确定性来源，优先级固定，**未改**）：
  1. **语面极性** `life/emotion.emotion_sign(对方上一句)`（**单一真源复用**，不另写一份）
     → `+1 / -1 / 0`；
  2. **处境情绪** 入站消息 `payload["ctx"]["mood"]`（发送方生成时由
     `dialogue_threads.mood_label(其自身 needs)` 算出的确定性标签）→ 查表得极性与严重度。
  合成规则：**语面有极性则语面优先**（"ta 刚说的这句话"比"ta 的处境"更贴近当下），
  否则用处境情绪；两者都为 0 → 不呼应（宁缺毋滥）。
  强度：语面命中 ⇒ `text_hit_intensity + mood_severity // mood_bonus_div`；仅处境 ⇒ 严重度；
  再与 `min_intensity` 比，**低于阈值不产**。

结构化可观测信号（只追加，写进 MSG payload 的 `ctx` 段，与 `ctx.memory_refs` /
`ctx.dequp` 同一先例；`orchestration/integration.py::_thread_fields` 对顶层新键有白名单，
而 `ctx` 是整体透传的 ⇒ **不动 orchestration** 也能落进日志）：
    payload["ctx"]["echo"] = {
      "v": "f3/2",             # R31 起为 f3/2（多了 form / verify 两个只追加子键）
      "sign": -1 | 1,          # 呼应方向（负=安抚，正=顺着高兴劲儿接）
      "intensity": int,        # 0..100（确定性推导，见上）
      "tier": "轻" | "明显" | "很强",
      "kind": "soothe" | "cheer",
      "source": "text" | "text+mood",   # R31：`mood` 已被证据门控挡掉，不再出现
      "mood": str | None,      # 对方 ctx.mood 原值（仅供参考，不再单独触发）
      "form": str | None,      # 本条实际下发的回应形态名（L-7 结构臂开启时让位 ⇒ None）
      "prompted": True,        # 本条是否真把约束块放进了提示词（与 prompt_line 一致）
      "verify": {...},         # 生成后确定性自检（verify()），仅审计、**不是**报告口径
    }
  关闭 / 不产（sign=0、低于阈值、或被证据门控挡掉）时日志里**一条都没有**。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from . import emotion as E

#: 单 env 开关（消融/逃生口）：{1,true,on,yes} → 开；其它任何值（含空串/拼错）→ 关。
ECHO_ENV = "HITT_DIALOGUE_EMOTION_ECHO"

#: 信号版本（写进 payload，便于按版本复算）。R31：`f3/1` → `f3/2`
#: （触发口径收紧 + 多两个只追加子键 ⇒ 旧读数可按 v 分桶，不与 R14 混账）。
VERSION = "f3/2"

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
    # R31 新增（默认值即本轮处理臂；关掉即回到 R14 口径，供消融）
    "require_text_evidence": True,  # 只认「对方那句话本身」有情绪证据；仅处境标签不触发
    "form_rotation": True,          # 下发确定性轮转的「回应形态」，避免同句式（L-7 守卫）
    # N-05 新增（**只在开关打开时才有意义**；OFF 时本键不被任何路径读到）
    "cue_repair": True,             # 生成后第一分句缺回应线索 / 应声就转话题 ⇒ 重写一次
}

#: 「回应形态」——**结构**而非句式（模型仍自由造句，**不提供任何例句**）。
#: 与 `l7_structural.OPEN_FORMS` 同构（同样默认轮转、同样 sha256 指派），条目互不重复。
#: L-7 结构臂（`LIFE_PROMPT_L7_STRUCT`，默认 ON）已指派**开口方式** ⇒ 两者同时下发会打架；
#: agent 侧在 L-7 开启时把 `form_ins` 置 None（让位给 L-7），此时本模块只下发**内容**约束。
ECHO_FORMS = (
    ("接过对方话里的那个词", "第一分句先把对方刚说过的某个词接过来，再表态"),
    ("先说一句短的体谅", "第一分句只说一句很短的体谅，不解释理由"),
    ("先问一句对方此刻怎样", "第一分句用一个问句问对方此刻的状态"),
    ("先替对方把难处说破", "第一分句把对方的难处具体说破（一两件事），再表态"),
    ("先应一声再立刻接住", "第一分句先应一声（不超过三个字），紧接着在同一个小句里接住情绪"),
)

#: 生成后自检用：对「对方」的指称（**审计闭集**，不参与任何报告口径）
REF_TOKENS = ("你", "您", "妳")
#: 生成后自检用：情绪回应线索词（**审计闭集**；只做结构自检，不当"接住"的评选尺）
CUE_TOKENS = (
    "累", "辛苦", "难", "急", "烦", "愁", "慌", "怕", "委屈", "难受", "不容易",
    "歇", "别", "慢", "心疼", "担", "熬", "受", "宽心", "踏实", "高兴",
    "顺", "恭喜", "厉害", "羡慕", "惦记", "放心", "甭", "缓", "松快",
)
#: 第一分句的切分（中文标点 + 常用半角）
_CLAUSE_RE = re.compile(r"[，。！？!?；;、,.~～\n]")
#: 「应声词」——只用来判定「应了一声之后有没有接住」，不是禁令（与 L-7 的开口方式不冲突）
_ACK_RE = re.compile(r"^(嗯+|唉+|哎+|哦+|哟+|啊+|唔+)[，,、]?")

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
    out["require_text_evidence"] = bool(out["require_text_evidence"])
    out["form_rotation"] = bool(out["form_rotation"])
    out["cue_repair"] = bool(out["cue_repair"])
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


def _h(*parts) -> int:
    """稳定哈希（不用内置 hash，避免 PYTHONHASHSEED 影响可复现性）。"""
    key = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:12], 16)


def assign_form(agent_id: str | None, thread_id: str | None, turn: int | None,
                round_no: int | None) -> int:
    """确定性指派「回应形态」序号（同一组入参恒等；跨 agent 近似均匀）。

    与 `l7_structural.assign` 同构（sha256），但键空间不同（前缀 `f3`）⇒ 两者不相关，
    不会把「开口方式」与「回应形态」锁成同一周期。**不读墙钟/随机**。
    """
    return _h("f3", agent_id or "", thread_id or "", turn, round_no) % len(ECHO_FORMS)


def plan(mood_label: str | None, partner_text: str | None,
         params: dict | None = None, *,
         agent_id: str | None = None, thread_id: str | None = None,
         turn: int | None = None, round_no: int | None = None) -> dict | None:
    """呼应计划：开关关 / sign==0 / 强度低于阈值 / **无文本证据** → `None`（零副作用）。

    证据门控（R31）：`require_text_evidence=True` 时，只有 `detect()` 的 `source`
    含 `text`（即**对方那一句本身**确有情绪证据）才产。`source == "mood"`（仅发送方
    处境标签）不再触发——R14 的 295 条触发里 273 条属于这一类，正是提示与可见文本
    互相矛盾的来源（诊断见 `reports/r31-impl-note.md` §2）。置 false ⇒ 退回 R14 行为。
    """
    p = params or load_params()
    if not p["enabled"]:
        return None
    d = detect(mood_label, partner_text, p)
    if d["sign"] == 0 or int(d["intensity"]) < int(p["min_intensity"]):
        return None
    if p["require_text_evidence"] and d["source"] == "mood":
        return None
    d["evidence"] = (partner_text or "").strip() or None
    d["agent_id"] = agent_id
    d["thread_id"] = thread_id
    d["turn"] = turn
    d["round_no"] = round_no
    if p["form_rotation"] and agent_id is not None:
        fi = assign_form(agent_id, thread_id, turn, round_no)
        d["form"] = ECHO_FORMS[fi][0]
        d["form_ins"] = ECHO_FORMS[fi][1]
    else:
        d["form"] = None
        d["form_ins"] = None
    return d


def evidence_quote(partner_text: str | None, limit: int = 26) -> str:
    """把对方那句原话截成一段**可核对的证据**（去空白/去引号；超长截断加省略号）。"""
    t = re.sub(r"\s+", "", (partner_text or "")).strip()
    for ch in ("「", "」", "\"", "“", "”"):
        t = t.replace(ch, "")
    if not t:
        return ""
    return t if len(t) <= limit else t[:limit] + "…"


def prompt_line(plan_dict: dict | None, name: str | None = None) -> str:
    """把呼应计划渲染成**一段结构化硬约束**（关闭/无计划 ⇒ 空串，提示词逐字节不变）。

    形态（R31）：情绪标注行 + 证据原话 + 三条硬要求（第一分句先接住 / 带指称 /
    应声后不许直接转话题）+ 确定性轮转的回应形态 + 一句"不要把标记抄进台词"。
    **不给任何现成句式**：所有要求都是结构（哪一分句做什么），措辞由 LLM 产出。
    """
    if not plan_dict:
        return ""
    who = name or "对方"
    tier = plan_dict.get("tier") or "轻"
    mood = plan_dict.get("mood")
    if plan_dict.get("kind") == "soothe":
        what = f"{mood}" if mood else "情绪不大好"
        direction = "负向，需要安抚"
    else:
        what = "心情不错"
        direction = "正向，可以顺着这份劲儿接"
    quote = evidence_quote(plan_dict.get("evidence"))
    lines = [
        "\n【情绪呼应·本条硬约束】",
        f"情绪标注：{who}刚才这句话里有情绪——{what}（{tier}，{direction}）。",
    ]
    if quote:
        lines.append(f"证据（{who}原话）：「{quote}」")
    lines += [
        "这一条必须做到（按顺序，缺一条就算没做到）：",
        f"1) 第一分句先接住这份情绪（承认/关心/顺着接），不许第一分句就只讲自己的事；"
        "第一分句里要出现一个表露情绪回应的字眼（累/辛苦/难/别/心疼/放心这类），不能只复述事实；",
        f"2) 第一分句里要出现对{who}的指称（「你」或ta的名字）；",
        "3) 可以先应一声（嗯/哎/唉），但应完必须在同一句里接住这份情绪，不许应一声就转话题。",
    ]
    if plan_dict.get("form_ins"):
        lines.append(f"回应形态（只约束第一分句的做法，措辞你自己写）：{plan_dict['form_ins']}。")
    lines.append("上面这些是给你看的要求，不要把「情绪标注」「证据」这些字或方括号抄进台词。")
    return "\n".join(lines)


def first_clause(body: str) -> str:
    """第一分句（按中文标点切）。空正文 ⇒ 空串。"""
    return _CLAUSE_RE.split((body or "").strip(), maxsplit=1)[0].strip()


def verify(body: str, plan_dict: dict | None) -> dict:
    """生成后**确定性自检**（只写审计，不改台词、不新增 LLM 调用、**不是报告口径**）。

    四条断言（纯函数、可单测）：
      * `has_ref`：第一分句里出现对对方的指称（你/您/妳 或对方显示名）；
      * `has_cue`：第一分句里出现情绪回应线索（闭集 `CUE_TOKENS`）；
      * `ack_then_switch`：以应声词起头、且除应声外没有别的回应线索（= 应一声就转话题）；
      * `adopted` = has_ref and has_cue and not ack_then_switch（**结构合规**，非"效果好"）。
    `form_ok`：按本条指派的形态做一次结构检测（形态未指派 ⇒ None）。
    """
    plan_dict = plan_dict or {}
    fc = first_clause(body)
    name = str(plan_dict.get("name") or "").strip()
    has_ref = any(t in fc for t in REF_TOKENS) or bool(name and name in fc)
    has_cue = any(t in fc for t in CUE_TOKENS)
    ack = _ACK_RE.match(fc) is not None
    rest = _ACK_RE.sub("", fc)
    ack_then_switch = bool(ack) and not any(t in rest for t in CUE_TOKENS)
    out = {
        "v": "f3-verify/1",
        "first_clause": fc,
        "has_ref": bool(has_ref),
        "has_cue": bool(has_cue),
        "ack_then_switch": bool(ack_then_switch),
        "adopted": bool(has_ref and has_cue and not ack_then_switch),
        "form_ok": None,
    }
    form = plan_dict.get("form")
    if form:
        ev = str(plan_dict.get("evidence") or "")
        if form == ECHO_FORMS[0][0]:      # 接过对方话里的那个词
            out["form_ok"] = any((c in ev) for c in fc if c not in "，。！？、,. ")
        elif form == ECHO_FORMS[1][0]:    # 一句短的体谅
            out["form_ok"] = len(_CLAUSE_RE.sub("", fc)) <= 12
        elif form == ECHO_FORMS[2][0]:    # 问句
            out["form_ok"] = bool(re.search(r"[？?]|吗|呢|怎么|是不是", fc))
        elif form == ECHO_FORMS[3][0]:    # 说破难处
            out["form_ok"] = bool(set(fc) & set(ev))
        elif form == ECHO_FORMS[4][0]:    # 先应一声再立刻接住
            out["form_ok"] = bool(ack and has_cue)
    return out


def audit(plan_dict: dict | None) -> dict | None:
    """只追加的审计字段（无计划 ⇒ None ⇒ payload 不多键）。"""
    if not plan_dict:
        return None
    return {"v": VERSION, "sign": int(plan_dict["sign"]),
            "intensity": int(plan_dict["intensity"]), "tier": plan_dict["tier"],
            "kind": plan_dict["kind"], "source": plan_dict["source"],
            "mood": plan_dict.get("mood"), "form": plan_dict.get("form"),
            "prompted": True}


# ---------------------------------------------------------------- N-05 生成侧闸门
def cue_repair() -> bool:
    """N-05 重写闸开关（读 `cue_repair`，默认 True）。**只在 echo 开关打开时被调用**。"""
    return bool(load_params()["cue_repair"])


def need_rewrite(ver: dict | None) -> bool:
    """生成侧闸门判据（纯函数）：第一分句**缺回应线索** 或 **应一声就转话题** ⇒ 需重写一次。

    这正是 CYCLE-34 ON 臂 107 条 echo 里 `verify_has_cue=7` / `ack_then_switch=66` 的
    那个瓶颈：不是呼应不够强，而是第一分句根本没接住。判据只读 `verify()` 的确定性输出。
    """
    v = ver or {}
    return (not bool(v.get("has_cue"))) or bool(v.get("ack_then_switch"))


def rewrite_ok(ver: dict | None) -> bool:
    """重写结果是否**可以替换原文**（纯函数）：第一分句有线索，且不是应声即转话题。

    只看这两条（不看 `has_ref`）：N-05 只修「第一分句有没有接住」，指称是 R31 原有要求；
    多一条门槛会让替换更难成立，反而保证不了「不劣于修正前」。
    """
    v = ver or {}
    return bool(v.get("has_cue")) and not bool(v.get("ack_then_switch"))


def _fail_reason(ver: dict | None) -> str:
    """把 `verify()` 的失败项翻成一句给模型看的话（确定性、无随机）。"""
    v = ver or {}
    bits = []
    if not v.get("has_cue"):
        bits.append("第一分句里没有任何回应情绪的字眼")
    if v.get("ack_then_switch"):
        bits.append("只应了一声就转到自己的事上")
    return "；".join(bits) or "第一分句没有真正接住这份情绪"


def rewrite_line(plan_dict: dict | None, ver: dict | None,
                 name: str | None = None) -> str:
    """N-05：把「第一分句不合格」渲染成一次**重写要求**（追加在提示词尾部，不改原有块）。

    **不给现成句式**（与 F-4 / R31 口径一致）：只说结构要求（第一分句要有线索字眼、
    要有指称、应声不许超过三个字），措辞仍由 LLM 产出；也不要求模型输出任何标记。
    """
    if not plan_dict:
        return ""
    who = name or plan_dict.get("name") or "对方"
    fc = str((ver or {}).get("first_clause") or "").strip()
    lines = [
        "\n【情绪呼应·第一分句重写】",
        f"你上一条没做到：{_fail_reason(ver)}。",
    ]
    if fc:
        lines.append(f"上一条的第一分句：「{fc}」")
    lines += [
        "只重写这一条台词，按顺序满足：",
        f"1) 第一分句就接住{who}这份情绪，且出现一个表露情绪回应的字眼（累/辛苦/难/别/心疼/放心这类），"
        "不能只复述事实、不能只讲自己的事；",
        f"2) 第一分句里要有对{who}的指称（「你」或ta的名字）；",
        "3) 应声词最多三个字，而且必须在同一个小句里接住情绪，不许应一声就转话题。",
        "只输出台词本身：不要解释、不要说你在改、不要把上面这些字或方括号抄进去。",
    ]
    return "\n".join(lines)

