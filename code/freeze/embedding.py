"""嵌入冻结（对齐 00 §5.3/AR-C5 与 08 §5.4 D7-6）。

规则：
- 嵌入结果**落盘冻结**，缓存键含 **嵌入模型名 + 模型版本 + engine_version +
  文本哈希**，重放**不重算**。
- 统计/重放路径永不调用嵌入模型。
- ``embed_calls`` 计数器供断言（重放应为 0）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .canonical import digest
from .cache import FrozenStore
from .config import Mode


@dataclass
class EmbeddingResult:
    vector: List[float]
    cache_key: str
    model: str
    version: str
    cached: bool


class EmbeddingFreezer:
    """嵌入结果的冻结器。"""

    def __init__(
        self,
        *,
        store: FrozenStore,
        provider: Any,
        engine_version: str,
        mode: Mode = Mode.RUN,
        model: Optional[str] = None,
        version: str = "v1",
    ) -> None:
        self.store = store
        self.provider = provider
        self.engine_version = engine_version
        self.mode = Mode(mode) if isinstance(mode, str) else mode
        self.model = model or getattr(provider, "embed_model", "unknown-embed")
        self.version = version
        self.embed_calls = 0

    def make_cache_key(self, text: str, model: Optional[str] = None) -> str:
        """缓存键：嵌入模型名 + 版本 + engine_version + 文本哈希。"""
        return digest(
            {
                "cache_schema": "freeze-embed-v1",
                "kind": "embedding",
                "engine_version": self.engine_version,
                "model": model or self.model,
                "version": self.version,
                "text_hash": digest({"text": text}),
            }
        )

    def embed(self, text: str, *, model: Optional[str] = None) -> EmbeddingResult:
        resolved = model or self.model
        key = self.make_cache_key(text, resolved)

        hit = self.store.get_embedding(key)
        if hit is not None:
            return EmbeddingResult(
                vector=list(hit["vector"]),
                cache_key=key,
                model=hit["model"],
                version=hit.get("version", self.version),
                cached=True,
            )

        if self.mode == Mode.REPLAY:
            raise KeyError(f"嵌入缓存未命中（replay 不重算）：{key}")

        vector = self.provider.embed(text, model=resolved)
        self.embed_calls += 1
        record: Dict[str, Any] = {
            "cache_key": key,
            "vector": list(vector),
            "model": resolved,
            "version": self.version,
            "engine_version": self.engine_version,
            "text_hash": digest({"text": text}),
        }
        self.store.put_embedding(key, record)
        return EmbeddingResult(
            vector=list(vector),
            cache_key=key,
            model=resolved,
            version=self.version,
            cached=False,
        )
