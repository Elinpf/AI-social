"""side 存储分档的 **freeze 侧契约**（T228）。

分工（Leader 裁定）：**life 侧** `SideStore` 负责"写不写 `.vec`"（`persist_vec`，默认 True）；
**freeze 侧**负责：① "可产 / 可不产 `.vec`"的**嵌入能力**；② **检索降级标记的 schema 约定**；
③ 把开关**折进 `engine_version` 指纹**。

背景：`side/mem/<agent>/<id>.txt`（#10 数据资产，**必留**）与 `<id>.vec`（可重算，**可关/懒算**）。
`N=20` → ≈95k 文件、`N=50` → ≈187k，**inode 元凶**。

**开关**：env **`N50_VEC`**（obs 已挂 `N50_VEC=0` 等）；`"0"/"false"/"no"/"off"` → 关；缺省 → **True（行为不变）**。

**降级标记（不得静默变差）**：挂 **`MEMORY_RETRIEVE`（08 §1.2 E）** 的**可选字段**——
`vec_available: bool`（+ 可选 `retrieval_mode ∈ {"vector","lexical"}`）。**只增字段、不改语义（X1）**，
依据 08 §1.2 E（`MEMORY_RETRIEVE` schema 权威）→ **无需新登记**。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

#: 开关环境变量名（obs-stats-dev 已在 N=50 跑批侧标记 N50_VEC=0 等待）。
PERSIST_VEC_ENV = "N50_VEC"
_FALSEY = {"0", "false", "no", "off", "none", ""}

#: 降级标记字段（挂 `MEMORY_RETRIEVE` 载荷，只增字段）。
VEC_AVAILABLE_FIELD = "vec_available"
RETRIEVAL_MODE_FIELD = "retrieval_mode"
RETRIEVAL_MODES: Sequence[str] = ("vector", "lexical")


def resolve_persist_vec(default: bool = True) -> bool:
    """解析 `persist_vec` 开关：缺省 = ``default``（True=行为不变）。"""
    raw = os.environ.get(PERSIST_VEC_ENV)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSEY


def side_fingerprint(persist_vec: bool) -> Dict[str, object]:
    """side 分档的指纹片段（供折进 `engine_version`）。"""
    return {"persist_vec": bool(persist_vec)}


def degradation_marker(*, vec_available: bool,
                       retrieval_mode: Optional[str] = None) -> Dict[str, object]:
    """构造挂到 `MEMORY_RETRIEVE` 的**显式降级标记**（非静默）。

    - `vec_available=True` → 向量检索可用（`retrieval_mode` 缺省 "vector"）。
    - `vec_available=False` → `.vec` 未落/缺失，检索**已降级**（应为 "lexical"）。
    """
    if not vec_available and retrieval_mode is None:
        retrieval_mode = "lexical"
    if vec_available and retrieval_mode is None:
        retrieval_mode = "vector"
    if retrieval_mode is not None and retrieval_mode not in RETRIEVAL_MODES:
        raise ValueError(f"retrieval_mode 必须是 {RETRIEVAL_MODES} 之一，得到 {retrieval_mode!r}")
    return {VEC_AVAILABLE_FIELD: bool(vec_available), RETRIEVAL_MODE_FIELD: retrieval_mode}


@dataclass
class SideEmbedResult:
    """life 落 `.vec` 时用：`vector=None` 表示"本次不产 `.vec`"。"""

    vector: Optional[list]
    vec_available: bool
    retrieval_mode: str


def embed_for_side(text: str, provider, *, persist_vec: bool) -> SideEmbedResult:
    """freeze 侧「可产 / 可不产 `.vec`」的嵌入能力。

    - `persist_vec=True` → 正常产出向量（`vec_available=True`）。
    - `persist_vec=False` → **不产 `.vec`**（`vector=None`），检索降级到词法（`retrieval_mode="lexical"`），
      由 life 在 `MEMORY_RETRIEVE` 上落 `degradation_marker`。
    """
    if not persist_vec:
        return SideEmbedResult(vector=None, vec_available=False, retrieval_mode="lexical")
    vec = provider.embed(text)
    return SideEmbedResult(vector=list(vec), vec_available=True, retrieval_mode="vector")
