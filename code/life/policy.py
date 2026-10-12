"""B-line policy reads for the life layer (T115): the one-stop social on/off switch.

`policy.social.enabled` (config/policy.json, default **true**) controls whether the
life layer produces the **v2 social-voice channel as a whole**:

    INTENT.SOCIAL -> MSG_DM / MSG_PUBLIC / MSG_GROUP  (+ GROUP_CREATED)

When off, the channel is **short-circuited at the generation side** (no intent is
submitted, no group is materialised), so there are *no* MSG_*/GROUP_CREATED events,
*no* `LLM_CALL(purpose=dialogue)` and the quota/dedup logic is never reached.

Scope note: in v1 the DM body was a hard-coded template (superseded by the v2 LLM
generation), so turning DM off together with PUBLIC/GROUP does not mix old/new
variables — off == "no v2 social voice at all".

The life layer never imports `engine`; it reads the shared config file directly.
An env override `SOCIAL_ENABLED=0|false` is supported for ablation runs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "policy.json"

_config_cache: bool | None = None
_override: bool | None = None


def _read() -> bool:
    env = os.environ.get("SOCIAL_ENABLED")
    if env is not None:
        return env.strip().lower() not in ("0", "false", "off", "no", "")
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return bool(data.get("social", {}).get("enabled", True))
    except Exception:
        return True  # default on (行为不变)


def social_enabled() -> bool:
    global _config_cache
    if _override is not None:
        return _override
    if _config_cache is None:
        _config_cache = _read()
    return _config_cache


def set_social_enabled(value: bool | None) -> None:
    """Test/ablation hook: force the flag (None clears and re-reads config)."""
    global _override, _config_cache
    _override = value
    if value is None:
        _config_cache = None


# ---- exchange switch (T131/T133): agent<->agent trade primitives --------------
_exchange_cache: bool | None = None
_exchange_override: bool | None = None


def _read_exchange() -> bool:
    env = os.environ.get("EXCHANGE_ENABLED")
    if env is not None:
        return env.strip().lower() not in ("0", "false", "off", "no", "")
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return bool(data.get("exchange", {}).get("enabled", True))
    except Exception:
        return True


def exchange_enabled() -> bool:
    """True (default) -> life may produce `INTENT.ECON.*`; off -> produce none."""
    global _exchange_cache
    if _exchange_override is not None:
        return _exchange_override
    if _exchange_cache is None:
        _exchange_cache = _read_exchange()
    return _exchange_cache


def set_exchange_enabled(value: bool | None) -> None:
    global _exchange_override, _exchange_cache
    _exchange_override = value
    if value is None:
        _exchange_cache = None


# ---- M2b 判别式开关（T222）: judge / importance 走「受限选择」还是旧生成式 ------
# **默认 `generative` = 走旧路径，行为与现状逐项一致**（新路径默认关）。
# 新键进 engine_version 指纹（Leader ③：不复用旧键）。
#   policy.m2b.judge.mode      ∈ {generative, discriminative}   默认 generative
#   policy.m2b.importance.mode ∈ {generative, discriminative}   默认 generative
#   policy.m2b.judge.fallback  ∈ {none, margin}                 默认 none（保守，不触发）
#   policy.m2b.judge.margin_theta   float                       默认 0.0（<0 才升级 → 恒不触发）
_M2B_DEFAULT: dict = {"judge_mode": "generative", "importance_mode": "generative",
                      "fallback": "none", "margin_theta": 0.0}
_m2b_cache: dict | None = None
_m2b_override: dict | None = None


def _read_m2b() -> dict:
    cfg = dict(_M2B_DEFAULT)
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        m = data.get("m2b") or {}
        j = m.get("judge") or {}
        im = m.get("importance") or {}
        if j.get("mode") is not None:
            cfg["judge_mode"] = str(j["mode"])
        if im.get("mode") is not None:
            cfg["importance_mode"] = str(im["mode"])
        if j.get("fallback") is not None:
            cfg["fallback"] = str(j["fallback"])
        if j.get("margin_theta") is not None:
            cfg["margin_theta"] = float(j["margin_theta"])
    except Exception:
        pass
    env = os.environ.get("M2B_MODE")  # ablation override: discriminative|generative
    if env is not None:
        v = env.strip().lower()
        if v in ("discriminative", "on", "1", "true"):
            cfg["judge_mode"] = cfg["importance_mode"] = "discriminative"
        elif v in ("generative", "off", "0", "false", ""):
            cfg["judge_mode"] = cfg["importance_mode"] = "generative"
    return cfg


def m2b_config() -> dict:
    global _m2b_cache
    if _m2b_override is not None:
        return dict(_m2b_override)
    if _m2b_cache is None:
        _m2b_cache = _read_m2b()
    return dict(_m2b_cache)


def m2b_judge_mode() -> str:
    return m2b_config()["judge_mode"]


def m2b_importance_mode() -> str:
    return m2b_config()["importance_mode"]


def m2b_fallback() -> str:
    return m2b_config()["fallback"]


def m2b_margin_theta() -> float:
    return float(m2b_config()["margin_theta"])


def set_m2b_config(cfg: dict | None) -> None:
    """Test/ablation hook: force the M2b config (None clears and re-reads config)."""
    global _m2b_override, _m2b_cache
    _m2b_override = cfg
    if cfg is None:
        _m2b_cache = None


# ---- T228: side storage `.vec` 落盘开关（默认 True=行为不变）------------------
#   policy.life.memory.persist_vec  (config/policy.json, 默认 true)
#   env N50_VEC=0|false|no|off  -> 关（oversight override，与 freeze.side 同语义）
# 关时 SideStore 不写 `<mem_id>.vec`（省 inode）；检索调用点显式降级并打标记（不静默）。
_pv_cache: bool | None = None
_pv_override: bool | None = None


def _read_persist_vec() -> bool:
    env = os.environ.get("N50_VEC")
    if env is not None:
        return env.strip().lower() not in ("0", "false", "off", "no", "")
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return bool(((data.get("life") or {}).get("memory") or {}).get("persist_vec", True))
    except Exception:
        return True


def persist_vec_enabled() -> bool:
    global _pv_cache
    if _pv_override is not None:
        return _pv_override
    if _pv_cache is None:
        _pv_cache = _read_persist_vec()
    return _pv_cache


def set_persist_vec(value: bool | None) -> None:
    """Test/ablation hook: force the flag (None clears and re-reads config)."""
    global _pv_override, _pv_cache
    _pv_override = value
    if value is None:
        _pv_cache = None


# ---- T234: 叙事正文落盘开关（T228 分档体系；可关，关时不写）------------------
#   policy.life.narrative.persist_body  (config/policy.json, 默认 true=行为不变)
#   env N50_NARR_BODY=0|false|no|off  -> 关（oversight override）
# 关时：`_maybe_narrate` **不写** `side/narrative/<agent>/<nid>.txt`（省 inode）；
# `NARRATIVE.body_ref` 仍发射（与 `.vec` 关时同语义：指针在、正文可缺，导出侧显式计 missing）。
_nb_cache: bool | None = None
_nb_override: bool | None = None


def _read_narrative_persist() -> bool:
    env = os.environ.get("N50_NARR_BODY")
    if env is not None:
        return env.strip().lower() not in ("0", "false", "no", "off", "")
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return bool(((data.get("life") or {}).get("narrative") or {}).get("persist_body", True))
    except Exception:
        return True


def narrative_persist_enabled() -> bool:
    """True（默认）-> life 写叙事正文到 side；False -> 不写（可关/消融）。"""
    global _nb_cache
    if _nb_override is not None:
        return _nb_override
    if _nb_cache is None:
        _nb_cache = _read_narrative_persist()
    return _nb_cache


def set_narrative_persist(value: bool | None) -> None:
    """Test/ablation hook: force the flag (None clears and re-reads config)."""
    global _nb_override, _nb_cache
    _nb_override = value
    if value is None:
        _nb_cache = None

