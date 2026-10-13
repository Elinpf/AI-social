"""T353 / `D3` 口径②：`WorldParams` —— 世界层参数的**可重建派生视图**。

- **纯函数**：`f(已提交的 WORLD_GROUP_EVENT/WORLD_DIRECTIVE 的 [start,end) ∩ t, 静态 config)`；
  **不入 `state_hash`、不入事件语义**（同 §5.9 口径）。
- **三保底**：每项**可溯源到 `directive_ref`**（`directed=true` 才生效）；**只对未来**（`[start,end)`）；
  剂量由 `world_director.json` 的 `dose` 决定；总开关 `world_director.propagate.enabled`（默认 true）。
- **只给"情境参数"，不给个体结果**（不给对手/胜负/价格）。
"""

from __future__ import annotations

DEFAULT_PROPAGATE = True


def propagate_enabled(config: dict | None) -> bool:
    wd = (config or {}).get("world_director", {}) or {}
    return bool((wd.get("propagate", {}) or {}).get("enabled", DEFAULT_PROPAGATE))


def world_params(records: list, round_no: int, config: dict | None = None) -> dict:
    """返回 `t=round_no` 生效的世界层参数（派生、只读）。

    形状：`{"activity_weight": {place: int}, "resource_factor_bp": {good|place: int},
           "market_scarcity_bp": {good: int}, "active": [directive_ref,...]}`。
    空 ⇒ 各 dict 为空、`active=[]`（= 无世界层影响）。
    """
    out = {"activity_weight": {}, "resource_factor_bp": {}, "market_scarcity_bp": {}, "active": []}
    if not propagate_enabled(config):
        return out
    t = int(round_no)
    for rec in records:
        ty = rec.get("type")
        if ty not in ("WORLD_GROUP_EVENT", "WORLD_DIRECTIVE"):
            continue
        p = rec.get("payload", {}) or {}
        if not p.get("directed", False):
            continue                       # 保底(a)：无 directed 不传导
        start = int(p.get("start_round", p.get("effective_from_round", rec.get("round", 0))) or 0)
        end = int(p.get("end_round", p.get("expires_round", start + 1)) or (start + 1))
        if not (start <= t < end):         # 保底(c)：只对未来 [start,end)
            continue
        kind = str(p.get("kind", "")).lower()
        ref = p.get("directive_ref") or p.get("directive_id")
        if ref:
            out["active"].append(ref)
        scope = p.get("scope", {}) or {}
        place = scope.get("place") or p.get("place")
        params = p.get("params", {}) or {}
        if kind in ("festival", "mass_event"):
            if place:
                out["activity_weight"][place] = out["activity_weight"].get(place, 0) + int(params.get("capacity", 40))
        elif kind in ("supply_shock", "disaster"):
            amp = int(params.get("amp_bp", params.get("severity", 0)) or 0)
            key = place or "global"
            out["resource_factor_bp"][key] = out["resource_factor_bp"].get(key, 0) - abs(amp)
        elif kind in ("tension", "edict", "scarcity"):
            sc = int(params.get("scarcity_bp", 0) or 0)
            g = params.get("good_id") or "global"
            out["market_scarcity_bp"][g] = out["market_scarcity_bp"].get(g, 0) + sc
    return out
