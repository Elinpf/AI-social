"""处境锚（scene-anchor）臂：把「此刻是什么时段 / 你在哪儿 / 手上正做什么」写进对话提示词。

一句话：让台词带上生活坐标（「这会儿天快黑了，你还在市集守着摊子」），
而不是只知道自己"在跟谁聊什么、关系多少、饿不饿"。

单变量约束（沿用 `agent.py` 里 G-1 / F-6 / F-4 / L-7 / R19 的开关先例）：
  * 开关 = 环境变量 `LIFE_PROMPT_SCENE`（∈ {1,true,yes,on}），**默认 OFF**；
  * OFF ⇒ 本模块 `render()` 恒返回空串、`audit()` 恒返回 None，
    调用方 `agent.py` 拼进提示词的仍是空串 ⇒ **两条提示词与接入前逐字节一致**，
    `ctx.scene` 键不出现 ⇒ MSG payload 也与接入前逐字节一致。

素材纪律（本轮的立身之本，也是防回归的三条硬线）：
  1. **只用已有事实**：`WorldView.time.slot`（时段）、`WorldView.location`（场所 id）、
     `WorldView.current_activity`（进行中的活动，`time.ongoing.enabled=true` 时非 None）。
     **不新增真相源、不读墙钟、不发事件、不改 state_hash、不写记忆** ⇒ 防 F-7（越界编造）。
  2. **只递人话，不递内部 id**：场所一律走 `config/places.json::name_cn`（如「市集」「农场」）；
     `name_cn` 缺项或查不到时**该片段不写**（宁缺不写 id），防 `L-8c` / `L-13` token 泄漏。
  3. **确定性**：时段/活动的具体措辞由 `sha256(agent_id|round|slot|kind)` 从固定词表里选，
     不含随机数、不含墙钟 ⇒ 同一 run 重放逐字节一致（R1 §2.1 可复现纪律）。

剂量与长度：每次装配**只插一行**（+30~50 字符），避免 L-1 长度分布整体漂移。
"""
from __future__ import annotations

import hashlib
import os

#: 臂开关（env `LIFE_PROMPT_SCENE`）；默认关。
SCENE_ENV = "LIFE_PROMPT_SCENE"

#: R52 / B-8 修复开关（env `HITT_SCENE_FRESH`）；默认关。
#: 关 ⇒ 处境锚仍取 `WorldView` 快照（本轮 perceive 阶段取定，可能是**上一站**）；
#: 开 ⇒ 在装配这一条消息的时点重新 perceive，取与 `_do_social` 落盘 `payload.place`
#: 同一真相源的**当轮实时**场所/活动。仅在 `LIFE_PROMPT_SCENE` 打开时才有意义。
FRESH_ENV = "HITT_SCENE_FRESH"

#: 时段 → 人话措辞候选（固定词表；改词表＝改行为，须重新冻结 sha256，见 runbook §3.97）
SLOT_WORDS: dict[str, tuple[str, ...]] = {
    "morning": ("一大早", "这会儿天刚亮", "上午这会儿"),
    "afternoon": ("午后这会儿", "下午", "晌午刚过"),
    "evening": ("这会儿天快黑了", "傍晚", "擦黑这会儿"),
    "night": ("夜里", "这会儿夜深了", "灯都点上了"),
}

#: 进行中活动（`activity_type`，见 `constants.ACTIVITY_TYPES`）→ 人话措辞候选。
#: 词表里**不出现任何英文 token / 内部 id**（只写人话），漏项 ⇒ 该片段不写。
ACTIVITY_WORDS: dict[str, tuple[str, ...]] = {
    "work": ("正忙着手上的活", "还在赶活", "手头的事正到劲儿上"),
    "learn": ("在看书琢磨", "正学着东西", "手上摊着书"),
    "socialize": ("正跟人搭话", "在外头和人唠着", "跟邻居凑在一处"),
    "leisure": ("正闲逛", "在松快松快", "出来透口气"),
    "self_care": ("正拾掇自己", "刚收拾利索", "在照看自己"),
    "civic": ("正张罗镇上的事", "在忙公事", "替大伙跑腿"),
    "trade": ("正张罗买卖", "守着摊子", "在盘算价钱"),
    "rest": ("正歇着", "刚坐下歇口气", "在缓一缓"),
}

#: 词表指纹（报告/runbook 侧要冻结的"尺子"身份；只由上面两张表的内容决定）。
LEXICON_VERSION = "scene-anchor-v1"


def enabled() -> bool:
    """臂开关（env `LIFE_PROMPT_SCENE` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(SCENE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def fresh_enabled() -> bool:
    """R52 修复开关（env `HITT_SCENE_FRESH` ∈ {1,true,yes,on}）；默认关。

    关 ⇒ 取 `WorldView` 快照场所（改动前行为，逐字节等价）；
    开 ⇒ 取「装配这条消息时点」的实时场所（与 `_do_social` 落盘 `payload.place` 同源）。
    """
    return os.environ.get(FRESH_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pick(seed: str, options: tuple[str, ...]) -> str:
    """确定性选词：同一 (agent, round, slot, kind) 恒得同一措辞；不同组合会变化。"""
    if not options:
        return ""
    return options[int(_sha(seed)[:8], 16) % len(options)]


def lexicon_sha256() -> str:
    """词表指纹：两张词表 + 版本号的规范化拼接 sha256（改动词表即可被检出）。"""
    rows = [LEXICON_VERSION]
    for slot in sorted(SLOT_WORDS):
        rows.append(f"slot:{slot}=" + "|".join(SLOT_WORDS[slot]))
    for act in sorted(ACTIVITY_WORDS):
        rows.append(f"act:{act}=" + "|".join(ACTIVITY_WORDS[act]))
    return _sha("\n".join(rows))


def render(agent_id: str, round_no: int, slot: str, place_name: str | None,
           activity_type: str | None) -> str:
    """渲染插入提示词的那一行处境；素材不足以成句时返回空串（宁缺不写）。

    `place_name` 必须是**人话名**（调用方从 `places.json::name_cn` 取），本函数不再做 id 映射。
    """
    if not enabled():
        return ""
    slot_word = _pick(f"{agent_id}|{round_no}|{slot}|slot", SLOT_WORDS.get(str(slot), ()))
    act_word = _pick(f"{agent_id}|{round_no}|{slot}|act",
                     ACTIVITY_WORDS.get(str(activity_type or ""), ()))
    name = (place_name or "").strip()
    bits: list[str] = []
    if slot_word:
        bits.append(slot_word)
    if name:
        bits.append(f"你在{name}")
    if act_word:
        bits.append(act_word)
    if not bits:
        return ""
    tail = "（这些只是你眼下的底子：顺口带一句就够，别生硬地报地名，也别在这上面多解释；说不着就不提。）"
    return "\n你眼下的光景：" + "，".join(bits) + "。" + tail


def audit(slot: str, place_id: str | None, activity_type: str | None,
          line: str | None = None, place_src: str | None = None) -> dict:
    """审计快照（写进 MSG payload 的 `ctx.scene`；**只在开关打开时产**）。

    与 `ctx.topic` 同口径：机器侧记的是 id（`place` / `activity`），不是人话；
    另记 `line_sha256`，便于报告侧证明"模型看到的那一行"确实是它。

    `place_src`（R52 新增，**仅 `HITT_SCENE_FRESH=1` 时由调用方传入**）：
      * 传 `"live"` ⇒ 本条场所取自「装配消息时点」的实时状态（与 `_do_social` 同源）；
      * 不传（`None`）⇒ 该键**不出现** ⇒ 改动前/修复关闭态的 `ctx.scene` 逐字节不变。
    """
    out: dict = {"slot": str(slot)}
    if place_id:
        out["place"] = str(place_id)
    if activity_type:
        out["activity"] = str(activity_type)
    if line:
        out["line_sha256"] = _sha(line.strip())   # 不含前导换行：与提示词里那一行文本对齐
    if place_src:
        out["place_src"] = str(place_src)
    return out
