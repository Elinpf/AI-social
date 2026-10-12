"""T333：情感/漂移候选判定的**单一真源**（T332 08 口径）。

判定对象：`MEMORY_WRITE kind=="reflection"` 正文。判定式（确定性、可复核）：
    sign(text) = +1 if 命中 POS；-1 if 命中 NEG；else 结构信号按极性表兜底；else 0（不产）

两档（一等可消融键 `persona_drift.criterion ∈ {strict, natural}`，默认 `natural`）：
  * `strict`  ⟺ **现 26 显式子串逐字节等价**（消融基线；结构与极性兜底**关闭**）；
  * `natural` = 扩后判据：**扩词表（含隐性线索） + 结构信号正则 + 极性表兜底**。

⚠️ 调用方（`life/agent.py`）与 `tools/t271/emotion_probe.py` **都必须复用** `emotion_sign`，
   不得另写一份（否则"新判据命中率"不可信）。结构与极性方向标 **【未验证】**（08 §）。
"""
from __future__ import annotations

import re

# (a) 显式 26 子串 = strict 基线（**逐字节等价现状**，顺序/优先级不可改）
STRICT_POS = ("帮助", "成长", "喜悦", "连接", "感谢", "陪伴", "温暖", "成功",
              "support", "growth", "joy", "connect", "thanks")
STRICT_NEG = ("冲突", "失败", "孤独", "失去", "争吵", "痛苦", "挫折", "焦虑",
              "conflict", "loss", "lonely", "fail", "struggle")

# (a+) natural 扩展的**隐性线索**（代码级单一真源；08 登记）（标【未验证】）
NATURAL_POS_EXTRA = ("欣慰", "释然", "牵挂", "踏实", "期待", "感激", "佩服", "心疼",
                     "舍不得", "安心", "开心", "满足", "感动", "温暖", "陪伴", "惦念")
NATURAL_NEG_EXTRA = ("担心", "遗憾", "无奈", "疲惫", "憋屈", "抱歉", "后悔", "难过",
                     "不安", "委屈", "失落", "落寞", "空落", "叹气", "苦笑", "没劲")

NATURAL_POS = STRICT_POS + NATURAL_POS_EXTRA
NATURAL_NEG = STRICT_NEG + NATURAL_NEG_EXTRA

# (b) 结构信号（正则）——动作括号 / 语气让步 / 省略号 / 破折号 / 第一人称评价 / 句末[？！]
STRUCT_NEG_RE = re.compile(
    r"（[^）]*）|\([^)]*\)|……|\.{3}|—{2}|--|啊|吧|呢|嘛|罢了|算了|也罢|也是|随它|"
    r"我觉得|我倒|我想|大概|或许|[？！]"
)
# 积极语气（结构兜底里的**正**向；【未验证】）
STRUCT_POS_RE = re.compile(r"明白了|懂了|有道理|不错|挺好|还行|值了")


def emotion_sign(text: str, *, criterion: str = "natural",
                 lexicon: tuple[tuple[str, ...], tuple[str, ...]] | None = None) -> int:
    """返回 `+1/-1/0`（0=不产候选）。`lexicon=(pos,neg)` 供探针复用同一函数。"""
    low = (text or "").lower()
    if lexicon is not None:
        pos, neg = lexicon
    elif criterion == "strict":
        pos, neg = STRICT_POS, STRICT_NEG
    else:  # natural
        pos, neg = NATURAL_POS, NATURAL_NEG
    # 显式词表优先，且保持"先 POS 后 NEG"的现状优先级（strict 逐字节等价）
    if any(k in low for k in pos):
        return 1
    if any(k in low for k in neg):
        return -1
    if criterion == "natural" and lexicon is None:
        # (c) 结构信号兜底：积极语气→正；否则结构命中→负；无→0（方向标【未验证】）
        if STRUCT_POS_RE.search(low):
            return 1
        if STRUCT_NEG_RE.search(low):
            return -1
    return 0


def emotion_hit(text: str, **kw) -> bool:
    return emotion_sign(text, **kw) != 0
