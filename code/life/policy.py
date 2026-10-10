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
