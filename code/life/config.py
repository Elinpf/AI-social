"""life 直读配置的**运行时注入 hook**（T297b）。

背景：`switch_mode: override`（运行时 config-dict 覆盖）只够到**引擎级**键；而
`config/life_v2.json`（`sleep.enabled` / `forgetting.enabled` / `persona_drift`）由 life
层**直接读盘** ⇒ 覆盖够不到，只能 `file` 模式（改文件 ⇒ 进 `engine_version` 指纹 ⇒
cache 全 miss ⇒ 对照不干净）。

本模块提供一个与引擎侧**同机制**的注入点：组合根把 `config["life_v2"]`（来自
`run_override.py --override life_v2.*=...`）**注入到 life**，life 读盘后**就地合并**覆盖。
**不改文件、不动指纹**；**不注入时行为与现状逐字节一致**。
"""
from __future__ import annotations

import copy

_OVERRIDE: dict | None = None


def set_override(d: dict | None) -> None:
    """注入 life 配置覆盖（`None` = 清除，回到纯读盘）。仅本进程内存，**不落盘**。"""
    global _OVERRIDE
    if d is not None and not isinstance(d, dict):
        raise ValueError(f"life config override must be a dict or None, got {type(d).__name__}")
    _OVERRIDE = copy.deepcopy(d) if d else None


def clear_override() -> None:
    set_override(None)


def override_for(section: str) -> dict | None:
    """返回 `section` 的覆盖。当前 hook 只承载 `life_v2`（存的就是该段内容）。"""
    if section != "life_v2" or not _OVERRIDE:
        return None
    return _OVERRIDE


def _deep_merge(dst: dict, src: dict, path: str) -> None:
    # 未知键 / 类型冲突 ⇒ fail loud（不静默忽略）
    for k, v in src.items():
        if k not in dst:
            raise ValueError(f"unknown life config key: {path}{k}")
        if isinstance(v, dict) or isinstance(dst[k], dict):
            if not (isinstance(v, dict) and isinstance(dst[k], dict)):
                raise ValueError(
                    f"life config type conflict at {path}{k}: "
                    f"{type(dst[k]).__name__} vs {type(v).__name__}")
            _deep_merge(dst[k], v, f"{path}{k}.")
        else:
            dst[k] = copy.deepcopy(v)


def apply(section: str, base: dict) -> dict:
    """把 `section` 的覆盖深合并到 `base` 上（不改 `base`；无覆盖则原样返回）。

    未知键 / 类型冲突 ⇒ `ValueError`（fail loud）。
    """
    ov = override_for(section)
    if not ov:
        return base
    out = copy.deepcopy(base)
    _deep_merge(out, ov, f"{section}.")
    return out
