"""插件清单 / 版本指纹（用户 #8「可复用资产」的可追溯面）。

`describe(ctx)` 把已挂载插件导出为**可版本绑定的清单**；`fingerprint(...)` 给出稳定指纹，
供「证据绑版本（sha + 命令）」纪律使用（与内核 `engine.version` 同思路，但**零业务依赖**）。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PluginInfo:
    id: str
    name: str
    provides: tuple = ()       # 该插件提供的服务名（由 ctx.services 归属推断）
    injects: tuple = ()        # 该插件声明的依赖
    state: str = "PENDING"


def describe(ctx: Any) -> list[PluginInfo]:
    """从已挂载记录导出插件清单（按 id 升序，稳定）。"""
    infos: list[PluginInfo] = []
    for rec in ctx.plugins():
        fn = rec["fn"]
        infos.append(PluginInfo(
            id=rec["id"],
            name=rec.get("name", rec["id"]),
            injects=tuple(getattr(fn, "inject", []) or ()),
            state=rec["fiber"].state,
        ))
    return sorted(infos, key=lambda p: p.id)


def fingerprint(infos: list[PluginInfo]) -> str:
    """插件清单的稳定指纹：`sha256:<hex>`（键排序、无空格）。"""
    payload = [{"id": p.id, "name": p.name, "injects": list(p.injects)} for p in infos]
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()
