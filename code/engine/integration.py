"""兼容 shim —— 交接层已迁至组合根 `orchestration.integration`（T35 / 蓝图 §1.3 规则 7）。

保留本模块仅用于**向后兼容**（前端 / 观测 / 证据包等外部调用 `engine.integration`）。
内核核心（engine 其余模块）不依赖 life/orchestration；本 shim 的依赖边已登记在
`.importlinter` 的 `ignore_imports`（组合根例外）。

规范入口：`python -m orchestration run --life ...`
"""

from __future__ import annotations

from orchestration.integration import (  # noqa: F401
    KernelAdapter,
    build_world,
    expand_personas,
    load_life_personas,
    load_places,
    register_life_hooks,
    run_e2e,
)

__all__ = [
    "KernelAdapter", "build_world", "run_e2e", "load_places", "load_life_personas",
    "expand_personas", "register_life_hooks",
]
