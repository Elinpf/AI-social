"""orchestration —— 组合根（唯一允许同时依赖 engine / life / freeze 的入口层）。

依据 `v1.2/01-implementation-architecture.md` §1.2/§1.3 规则 7：orchestration 是
唯一允许同时依赖多个下层包的入口层，且不得被任何下层依赖。

`integration.py`：engine × life 交接层（IF-1/IF-2 适配、Phase 3.5 注册、端到端装配）。
"""

from .integration import (
    KernelAdapter, build_world, run_e2e, load_places, load_life_personas,
    expand_personas, register_life_hooks,
)

__all__ = [
    "KernelAdapter", "build_world", "run_e2e", "load_places", "load_life_personas",
    "expand_personas", "register_life_hooks",
]
