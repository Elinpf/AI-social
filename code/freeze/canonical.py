"""规范 JSON 与哈希工具。

与 ``engine/canon.py`` **保持同一规范**，确保冻结层记录的事件与本征引擎账本
逐位一致（可被 Arbiter 无损落账）：

- 键排序（字典序）、紧凑分隔符、``allow_nan=False``；
- 浮点仅最终格式化，统一 ``round(x, 6)``；
- 布尔先于 int 判定（Python 中 bool 是 int 子类）；
- 哈希统一带 ``sha256:`` 前缀，创世前驱为 ``sha256:000...0``。

所有缓存键、上下文摘要（``context_digest``）、事件哈希链都基于此处的
**规范序列化**，保证「同日志逐位一致」。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

FLOAT_ROUND = 6

#: 哈希链的创世前驱（第 0 条记录的 prev_hash）——与 engine/canon.py 一致。
GENESIS_HASH = "sha256:" + ("0" * 64)


def _canon(obj: Any) -> Any:
    """递归归一到可规范序列化的结构：排序键、浮点 6 位、禁 NaN/Infinity。"""
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        return round(obj, FLOAT_ROUND)
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return {str(k): _canon(obj[k]) for k in sorted(obj.keys(), key=lambda x: str(x))}
    if isinstance(obj, (list, tuple)):
        return [_canon(x) for x in obj]
    raise TypeError(f"canonical_json 不支持的类型: {type(obj)!r}")


def canonical_json(obj: Any) -> str:
    """规范 JSON：key 排序、紧凑分隔符、保留非 ASCII、禁 NaN。"""
    return json.dumps(
        _canon(obj),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def canonical_bytes(obj: Any) -> bytes:
    return canonical_json(obj).encode("utf-8")


def sha256_hex(text: str) -> str:
    """纯 hex（无前缀）——用于缓存键 / mock 文本派生等内部用途。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_obj(obj: Any) -> str:
    """规范哈希，返回 ``sha256:<hex>``（与引擎账本一致）。"""
    return "sha256:" + hashlib.sha256(canonical_bytes(obj)).hexdigest()


def digest(obj: Any) -> str:
    """对任意可序列化对象做规范 JSON 后的 SHA-256（带 ``sha256:`` 前缀）。"""
    return hash_obj(obj)
