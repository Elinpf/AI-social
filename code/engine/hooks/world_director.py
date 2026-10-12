"""Phase 4 首项：世界 AI 导演（WD）hook —— 按机制表 + 剂量曲线产出世界级事件。

- **保底 (b) 消融**：总开关 `config["world_director"]["enabled"]=false` → 直接 `[]`（0 事件）。
- **登记门控**：`"WORLD_DIRECTIVE" not in EVENT_TYPES` → 只产 draft 但不 emit（不自造 schema）；
  T238 登记后自动激活真实 emit。
- **保底 (a)**：每次介入落 `WORLD_DIRECTIVE`（带 `directed=true`）+ `WORLD_GROUP_EVENT`（`directive_ref` 溯源）。
- 违 R1–R6 → 落 `WORLD_DIRECTIVE_REJECTED`（`severity=reject`）；`scope.level=agents` 且规模<K → `warn`。
- 纯函数、无 I/O、RNG 经 `(seed,"world_director",round,idx)`；不改金额/死亡/结算。
"""

from __future__ import annotations

from ..constants import PHASE_ARBITRATE
from ..events import EVENT_TYPES, spec
from ..world_director import cfg_of, plan_directives, validate_directive


def apply_world_director(state, round_no: int, ctx):
    cfg = cfg_of(getattr(ctx, "config", None))
    if not cfg.get("enabled", False):
        return []  # 保底 (b)：消融，关闭 → 零事件
    mech_index = {mid: i for i, mid in enumerate(sorted(cfg.get("mechanisms", {}) or {}))}
    plans = plan_directives(state, round_no, ctx, cfg, mech_index)
    if "WORLD_DIRECTIVE" not in EVENT_TYPES:
        return []  # 登记门控：未登记不自造 schema（drafts 丢弃）
    specs = []
    for mid, d in plans:
        v = validate_directive(d, cfg)
        did = f"D-{round_no}-{mid}"
        if not v["ok"]:
            specs.append(spec(round_no, PHASE_ARBITRATE, "SYSTEM", "WORLD_DIRECTIVE_REJECTED", {
                "directive_id": did, "round": round_no, "phase": PHASE_ARBITRATE,
                "reason": v["reason"], "severity": "reject"}))
            continue
        specs.append(spec(round_no, PHASE_ARBITRATE, "DIRECTOR", "WORLD_DIRECTIVE", {
            "directive_id": did, "mechanism_id": mid, "kind": d["kind"], "scope": d["scope"],
            "params": d["params"], "dose": d["dose"], "dose_curve": d["dose_curve"],
            "issued_round": d["issued_round"], "effective_from_round": d["effective_from_round"],
            "expires_round": d["expires_round"], "rng_branch": d["rng_branch"],
            "directed": True, "place": d["scope"].get("place")}))
        if v["severity"] == "warn":
            specs.append(spec(round_no, PHASE_ARBITRATE, "SYSTEM", "WORLD_DIRECTIVE_REJECTED", {
                "directive_id": did, "round": round_no, "phase": PHASE_ARBITRATE,
                "reason": "scope_below_K", "severity": "warn"}))
        specs.append(spec(round_no, PHASE_ARBITRATE, "DIRECTOR", "WORLD_GROUP_EVENT", {
            "group_event_id": f"GE-{round_no}-{mid}", "directive_ref": did, "kind": d["kind"],
            "scope": d["scope"], "params": d["params"], "start_round": round_no,
            "end_round": d["expires_round"], "affected_scope_count": 0,
            "directed": True, "place": d["scope"].get("place")}))
    return specs
