"""Python 插件运行时 v1 —— 借 Cordis 五概念（**零业务依赖，可复用到其他项目**）。

设计来源：`v2/refs/python-plugin-architecture.md`（T214）。Cordis 五概念 → Python 落地：
  1. 可逆副作用（effect/dispose）  -> `Context.effect()` + `Fiber.dispose()`（逆序撤销）
  2. 服务注入（inject）            -> `Context.provide()/get()` + 函数插件 `.inject=[...]` 声明式等待
  3. 类型化事件（emit/waterfall）  -> `Context.on()/emit()/waterfall()`（字符串事件名 + 约定）
  4. 配置组合（layered patch）     -> `plugin.config.compose()`（按 id 覆盖 / insert 追加）
  5. 插件清单/版本                 -> `plugin.manifest.describe()`

**边界铁律**：本包只依赖 stdlib（+ 可选 contracts 纯类型）；**不得** import
engine/life/freeze/obs/narrative/orchestration/frontend —— 由 import-linter 契约
`plugin-pure` 机器强制。

**渐进接入**：本包是**新增隔离层**，老代码无需改动即可跑；新代码可逐步 `ctx.plugin(...)` 挂载。
"""
from __future__ import annotations

from .context import Context, Fiber, Effect, PluginError, ServiceNotFound
from .config import compose
from .manifest import PluginInfo, describe, fingerprint

__all__ = [
    "Context", "Fiber", "Effect", "PluginError", "ServiceNotFound",
    "compose",
    "PluginInfo", "describe", "fingerprint",
]
