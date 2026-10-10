"""相关度工具：余弦相似度与记忆检索排序（确定性、纯函数）。

记忆流检索三因子之一 `relevance` 的**当前实现**为**确定性词法相关度**
（`frozen://lexical-relevance-v1`，见 :class:`freeze.providers.LexicalProvider`）。

⚠️ **真语义相关性未验证；当前为词法近似**（词面/词袋；同义改写不命中）。
本模块只提供确定性的向量运算与排序，不做任何 LLM 调用。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """余弦相似度（确定性、纯函数）。零向量返回 0.0。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@dataclass
class Ranked:
    index: int
    score: float
    text: str


class RelevanceRanker:
    """按相关度对记忆条目排序（top-k）。

    ``embed`` 为文本→向量的确定性函数（如 ``LexicalProvider.embed`` 或
    真嵌入模型的 ``embed``）。排序对**同分**用 index 升序做全序 tie-break，
    保证逐位可复现。
    """

    def __init__(self, embed: Callable[[str], Sequence[float]]) -> None:
        self.embed = embed
        self._cache: Dict[str, List[float]] = {}

    def _vec(self, text: str) -> List[float]:
        if text not in self._cache:
            self._cache[text] = list(self.embed(text))
        return self._cache[text]

    def rank(self, query: str, items: Sequence[str], top_k: Optional[int] = None) -> List[Ranked]:
        qv = self._vec(query)
        scored = [
            Ranked(index=i, score=cosine(qv, self._vec(t)), text=t)
            for i, t in enumerate(items)
        ]
        # 分数降序，index 升序 tie-break（确定性）
        scored.sort(key=lambda r: (-r.score, r.index))
        return scored[:top_k] if top_k is not None else scored


def lexical_overlap(query: str, text: str) -> float:
    """词面重叠率（Jaccard，基于 LexicalProvider 的分词）——**仅用于审计/解释**。"""
    from .providers import LexicalProvider

    a = set(LexicalProvider._tokens(query))
    b = set(LexicalProvider._tokens(text))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
