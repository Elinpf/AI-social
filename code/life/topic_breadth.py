"""R19 话题宽度臂（TB / topic-breadth）：让一条对话线程能自然岔到第二个话题上。

## 问题（本轮要治什么）

CYCLE-03 的两条 F 维读数是**结构性的 0**，不是噪声：

  * `F-2_topic_drift.drift_rate = 0.0`（480 个相邻对，CYCLE-03:126）
  * `F-2b multi_topic_thread_ratio = 0.0`（206 条线程；硬证据：每线程 tag 种数 = `{1: 206}`，CYCLE-03:131）

根因有两层，都在 `life/agent.py`：

  1. **提示词把内部 token 原样喂给模型**：`你正在和{who}聊「{topic}」`（R13:409），
     `topic` 就是 `whisper` / `combat_training` 这类模板 id ⇒ 模型偶尔照抄，
     形成 **L-13 token 泄漏 6/686**（CYCLE-03:113，实测样本见证据目录）。
  2. **一条线程只许一个 tag**：回复的 `tag_hints` 直接复制入站消息的
     `tag_hints`，发起消息的 `tag_hints=[template_id]` ⇒ 线程内 tag 恒定 ⇒
     `tag 种数` 恒为 1，F-2b 与 F-2 在数学上**不可能**大于 0。

## 机制（生成前下发 + 生成后内容门控，零额外 LLM 调用）

  * ① **人话化**：`label(topic)` 把模板 id 映射成中文说法（`whisper` → 「说悄悄话」），
    两个提示词都用人话，不再把内部 token 递给模型 ⇒ 直接压 L-13。
  * ② **岔题**：`turn_index ≥ 1` 的回复，按
    `sha256(agent|thread|round|turn)` 确定性地挑一个**相邻话题**，提示词里加一句
    「聊着聊着可以自然带到 X」，**不硬拐、只说一句**。
  * ③ **内容门控（关键，防刷指标）**：只有当**生成出来的正文**命中该话题的
    关键词表（`TOPIC_KEYWORDS`）时，才在 `tag_hints` 里**追加**第二个 tag。
    ⇒ 模型没落地就**不加 tag**，F-2b 不会因为「我们提示过」而虚增。
    这是本臂与「按意图打标」的区别，也是唯一能自证诚实的设计。

## 纪律（对齐 L-7 / F-3 / F-6 的既有先例）

  * 开关：env `LIFE_PROMPT_TOPIC_BREADTH`，**默认 OFF**；关闭时
    `label()` 原样返回、`render()` 空串、`plan()` 不参与、`tag_hints` 与提示词
    **逐字节不变**。
  * 确定性：岔题指派只由 sha256 与 (agent, thread, round, turn, base) 决定；
    门控只读生成的正文 ⇒ 同一 run replay 逐字节可复现。
  * 不改 `engine_version` 指纹、不进 `state_hash`、不产生世界态后果；
    只在开启时往已整体透传的 `ctx` 追加审计键 `ctx.topic_breadth`（additive）。
  * **不碰事务性 tag**（`scarce_buy` / `counter_propose` / `polite_reject` /
    `select_location` 在 `tools/d5/task_tags.txt` 里），避免把 F-1 闲聊率读数
    从后门改掉；`ADJACENT` 表里已把它们排除在岔题候选外。
"""
from __future__ import annotations

import hashlib
import os
import re

#: 话题宽度臂开关（**默认 OFF**；`1/true/yes/on` 打开）
BREADTH_ENV = "LIFE_PROMPT_TOPIC_BREADTH"
_ON = {"1", "true", "yes", "on"}

#: 模板/话题 id → 人话（用于提示词，替代原样 token；L-13 的正解）
TOPIC_LABELS = {
    "skill_practice": "练手艺",
    "mentorship": "向人请教手艺",
    "job_choice": "打听活计",
    "combat_training": "练功",
    "academic_collab": "一起读书",
    "creative_collab": "搭伙琢磨新东西",
    "scarce_buy": "抢着买紧俏货",
    "savings": "攒钱",
    "polite_reject": "婉言推掉",
    "counter_propose": "讨价还价",
    "gift": "送点东西",
    "rel_maintain": "走动人情",
    "whisper": "说悄悄话",
    "ice_break": "搭话认识",
    "rel_accept": "应下人情",
    "power_conflict": "为镇上的事争几句",
    "contest": "比试高下",
    "group_proposal": "张罗大家办点事",
    "select_location": "商量去哪儿",
}

#: 话题 → 可用于内容门控的关键词（正文命中 ≥1 才算「真的岔过去了」）
TOPIC_KEYWORDS = {
    # 收紧版 v3（R19）：**正则**门控。理由是子串法两头不讨好——
    #   太松：「给你/拿着/尝/留了/听说/力气/教/存/一定」这类高频子串零区分度
    #         （board-scout 在 off 基线实测旧词表 66/686=9.6% 白送）；
    #   太紧：只剩多字短语后召回掉到 0.58%（2/342，见 off_gate_fp_n16r84.txt）。
    # 正则用「动作 + 对象/方向」的短语结构，既排除无差别子串，又能覆盖多种说法。
    # ⚠️ 每次调整都必须用同一版本词表在 off 基线重算假阳性率并落盘。
    "skill_practice": r"(手艺|琢磨|练手|做工|活计|针脚|刀口|打磨|下料|这活儿)",
    "mentorship": r"(教我|指点|跟着学|请教|学两手|教一手|带我|领我)",
    "job_choice": r"(找活|差事|营生|做短工|找个营生|找点活)",
    "combat_training": r"(练功|出拳|招式|对练|拳脚|扎马步|练把式)",
    "academic_collab": r"(读书|认字|书本|学问|念书|算盘|字帖)",
    "creative_collab": r"(搭伙|花样|捣鼓|琢磨个|新鲜玩意儿|出个主意)",
    "scarce_buy": r"(抢|紧俏|存货|剩|买)",
    "savings": r"(攒钱|攒着|存钱|攒下|积蓄|钱罐|攒几个)",
    "polite_reject": r"(改天|不巧|推不了|难为|实在不行|下回吧)",
    "counter_propose": r"(价钱|还价|便宜|折算|换个价)",
    "gift": r"((捎|带|送|拿)(给|回|过)(你|去|来)|这点心|留了一包|尝个鲜|送你|拿回去)",
    "rel_maintain": r"(串门|走动|常来|来看看|顺路看|问个好|坐坐)",
    "whisper": r"(悄悄话|别声张|私下|传话|压低声|小声说|风声)",
    "ice_break": r"(头回|头一回|生面孔|搭话|认得|没见过你)",
    "rel_accept": r"(应下|说定了|记着|就这么办|包在我身上)",
    "power_conflict": r"(镇长|规矩|说不通|公道|评理|上头)",
    "contest": r"(比一比|谁赢|较量|赛一场|试试身手|分个高下)",
    "group_proposal": r"(凑人|张罗|提议|约齐|大家一块|招呼大家)",
    "select_location": r"(去哪儿|地点|改到|挪到|约在)",
}

#: 每个话题的「典型说法」（只用于单测构造命中句与文档示例，不参与门控）
SAMPLE_PHRASES = {
    "skill_practice": "这手艺得慢慢琢磨",
    "mentorship": "你教我一手指点指点",
    "job_choice": "听说有差事可做",
    "combat_training": "每天练功出拳",
    "academic_collab": "一起念书认字",
    "creative_collab": "咱们搭伙出个主意",
    "scarce_buy": "这货快被抢光了",
    "savings": "慢慢攒钱",
    "polite_reject": "今儿不巧改天吧",
    "counter_propose": "这价钱还价吧",
    "gift": "捎给你一包点心",
    "rel_maintain": "常来串门坐坐",
    "whisper": "小声说句悄悄话",
    "ice_break": "头回搭话认识一下",
    "rel_accept": "应下说定了",
    "power_conflict": "找镇长评理",
    "contest": "比一比谁赢",
    "group_proposal": "张罗凑人",
    "select_location": "改到哪儿",
}

#: 岔题邻接表（base → 允许岔入的话题；已排除事务性 tag，见模块 docstring）
ADJACENT = {
    "skill_practice": ("mentorship", "creative_collab", "savings", "job_choice"),
    "mentorship": ("skill_practice", "academic_collab", "job_choice"),
    "job_choice": ("savings", "skill_practice", "rel_maintain"),
    "combat_training": ("contest", "mentorship", "rel_maintain"),
    "academic_collab": ("mentorship", "skill_practice", "creative_collab"),
    "creative_collab": ("skill_practice", "group_proposal", "contest"),
    "scarce_buy": ("savings", "rel_maintain", "gift"),
    "savings": ("job_choice", "scarce_buy", "rel_maintain"),
    "polite_reject": ("rel_maintain", "rel_accept", "gift"),
    "counter_propose": ("savings", "rel_maintain", "scarce_buy"),
    "gift": ("rel_maintain", "rel_accept", "whisper"),
    "rel_maintain": ("gift", "whisper", "rel_accept"),
    "whisper": ("rel_maintain", "power_conflict", "gift"),
    "ice_break": ("rel_maintain", "skill_practice", "whisper"),
    "rel_accept": ("rel_maintain", "gift", "group_proposal"),
    "power_conflict": ("whisper", "group_proposal", "rel_maintain"),
    "contest": ("combat_training", "skill_practice", "rel_maintain"),
    "group_proposal": ("creative_collab", "rel_maintain", "power_conflict"),
    "select_location": ("group_proposal", "rel_maintain", "creative_collab"),
}
_DEFAULT_ADJ = ("rel_maintain", "skill_practice", "whisper")

#: 事务性 tag（`tools/d5/task_tags.txt` 中的话题类项）——岔题永远不选它们
_TRANSACTIONAL = {"scarce_buy", "counter_propose", "polite_reject", "select_location"}


def enabled() -> bool:
    """开关是否为开（默认 OFF）。"""
    return os.environ.get(BREADTH_ENV, "").strip().lower() in _ON


def label(topic: str | None) -> str:
    """模板 id → 人话；未知 id 原样返回（不臆造中文，也不静默丢弃信息）。"""
    if not topic:
        return topic or ""
    return TOPIC_LABELS.get(topic, topic)


def _digest(agent_id: str, thread_id: str, rnd: int, turn: int, base: str) -> int:
    raw = f"tb|{agent_id}|{thread_id}|{int(rnd)}|{int(turn)}|{base}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def plan(agent_id: str, thread_id: str, rnd: int, turn: int, base_topic: str | None) -> dict | None:
    """确定性挑选「本条回复可以岔入的相邻话题」。

    仅对 `turn >= 1`（线程第二条回复起）生效；`sha256 % 3 == 0` 的 1/3 条**不岔**，
    让线程里既有延续也有转折，避免「每条都在拐弯」的机械感。
    """
    if not base_topic:
        return None
    if int(turn) < 1:
        return None
    base = str(base_topic)
    h = _digest(agent_id, thread_id, rnd, turn, base)
    if h % 3 == 0:
        return None
    cands = tuple(t for t in ADJACENT.get(base, _DEFAULT_ADJ) if t not in _TRANSACTIONAL)
    if not cands:
        cands = tuple(t for t in _DEFAULT_ADJ if t != base)
    shift = cands[(h // 3) % len(cands)]
    if shift == base:
        return None
    return {"v": "tb/1", "base": base, "shift": shift, "turn": int(turn)}


def render(p: dict | None) -> str:
    """把岔题提示渲染成一句插入提示词的中文（不硬拐、只说一句）。"""
    if not p:
        return ""
    return (f"\n聊着聊着，可以顺带把话带到「{label(p['shift'])}」上；"
            "别硬拐，一句就够，主要还是接着眼前的话说。")


def confirm(body: str | None, shift: str | None, base: str | None = None) -> bool:
    """内容门控（双条件 + 正则）：正文命中 **shift** 的话题短语，且**不**命中 **base**。

    收紧理由（board-scout 2026-10-22 预警）：单条件子串法在 off 基线上有 9.6% 白送命中，
    集中在 `gift`（「给你/拿着/尝/留了」）。双条件把「本来就在说这个话题」的句子排除掉，
    正则则用「动作 + 对象/方向」的结构替代无差别子串。`base` 省略时退化为单条件（仅排查用）。
    """
    if not body or not shift:
        return False
    pat = TOPIC_KEYWORDS.get(shift)
    if not pat or not re.search(pat, body):
        return False
    if base:
        bpat = TOPIC_KEYWORDS.get(base)
        if bpat and re.search(bpat, body):
            return False
    return True


def audit(p: dict | None, landed: bool | None = None) -> dict | None:
    """审计字段（写进 `ctx.topic_breadth`）：本条实际下发了什么、是否真的落地。"""
    if not p:
        return None
    out = {"v": p.get("v"), "base": p.get("base"), "shift": p.get("shift"),
           "turn": p.get("turn")}
    if landed is not None:
        out["landed"] = bool(landed)
    return out
