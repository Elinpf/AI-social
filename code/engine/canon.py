"""规范 JSON 与哈希工具（确定性序列化的唯一入口）。

约束（P1 / §6.1）：
  - 键排序（字典序），无多余空格；
  - 浮点仅最终格式化，统一 round(x, 6)；
  - 布尔先于 int 判定（Python 中 bool 是 int 子类）；
  - 禁止 NaN/Infinity（allow_nan=False）。

哈希：SHA-256，输出统一带 "sha256:" 前缀。
"""

from __future__ import annotations

import hashlib
import json

FLOAT_ROUND = 6

# 哈希链的创世前驱（第 0 条记录的 prev_hash）
GENESIS_HASH = "sha256:" + ("0" * 64)


def _canon(obj):
    """递归归一到可规范序列化的结构：排序键、四舍五入浮点。"""
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        # 浮点禁入账务；此处仅作展示/兼容，统一 6 位
        return round(obj, FLOAT_ROUND)
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return {str(k): _canon(obj[k]) for k in sorted(obj.keys(), key=lambda x: str(x))}
    if isinstance(obj, (list, tuple)):
        return [_canon(x) for x in obj]
    # 其他类型（dataclass 等）要求调用方先 to_dict
    raise TypeError(f"canonical_json 不支持的类型: {type(obj)!r}")


def canonical_json(obj) -> str:
    """规范 JSON 字符串：键排序、紧凑分隔符、浮点 6 位。"""
    return json.dumps(
        _canon(obj),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def canonical_bytes(obj) -> bytes:
    return canonical_json(obj).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_obj(obj) -> str:
    """对任意对象求规范哈希，返回 'sha256:<hex>'。"""
    return "sha256:" + sha256_hex(canonical_bytes(obj))
