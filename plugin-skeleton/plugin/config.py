"""配置组合（Cordis 的 layered patch / overlay → Python）。

- `entries`：基础条目表 `[{id?, name, config?}, ...]`（对应 cordis.yml）。
- `overlays`：若干补丁层，每层是操作列表：
    * `{"id": <eid>, "config": {...}}` -> **整体替换**该 id 条目的 config（非深合并，同 Cordis）
    * `{"id": <eid>, <field>: ...}`    -> 覆盖该条目的其它字段（如 disabled）
    * `{"insert": [entry, ...]}`       -> 追加新条目（可选 `after: <eid>` 定位）
- 层**按序叠加**（base → overlay1 → overlay2 ...）；不修改入参，返回新列表。
"""
from __future__ import annotations

from typing import Any

from .context import PluginError


def compose(entries: list[dict], *overlays: list[dict]) -> list[dict]:
    out = [dict(e) for e in entries]
    for layer in overlays:
        for op in layer:
            if "insert" in op:
                seats = [dict(e) for e in op["insert"]]
                anchor = op.get("after")
                if anchor is None:
                    out.extend(seats)
                else:
                    idx = _index(out, anchor)
                    out[idx + 1: idx + 1] = seats
                continue
            eid = op.get("id")
            if not eid:
                raise PluginError("非 insert 的补丁必须带 id")
            idx = _index(out, eid)
            for k, v in op.items():
                if k == "id":
                    continue
                out[idx][k] = v        # config 整体替换（不深合并）
    return out


def _index(entries: list[dict], eid: str) -> int:
    for i, e in enumerate(entries):
        if e.get("id") == eid:
            return i
    raise PluginError(f"补丁目标不存在：{eid!r}")
