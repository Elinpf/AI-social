"""个体决策节拍：确定性唤醒集 W1–W10（T265；08 §1.2 S / §3.2）。

**世界结算节拍 = 回合，不变**（84 回合/周、每回合结算全部保留）。本模块只回答一件事：
**本轮哪些 Agent 进入 Phase 2 DECIDE**；其余的「安静」（不决策）。

契约：
- **纯函数**：输入 `(state, round_no, config)` → `{agent_id: {reason, all_reasons, source_event_seq}}`；
  只读 `state.agents` / `state.groups` / `state.event_index`；**无墙钟、无随机、无 LLM**。
- **可复算**：唤醒集是 `(state, log, round)` 的确定性函数 → 落 `WAKE` 事件后可离线复算、可审计。
- **不做可见性判定**（不引入第四份 `visible_events` 口径）：只按事件的目标字段
  （from/to/members/borrower/agent_id/place）与「同场所共处」判定。

开关（policy.wake，T8/08 §5.8）：`enabled` **默认 False（行为不变）**；每个触发器
`triggers.{W1..W10}` 独立开关（供消融）。

reason 枚举 = 08 §3.2 的 **W1–W10**（单一真源）：
  W1 定时 / W2 消息 / W3 状态 / W4 市场 / W5 债务 / W6 邻居(共处) /
  W7 计划到期 / W8 需求触发 / W9 周相位 / W10 邀请相遇
"""

from __future__ import annotations

from .time import derive_time

# 08 §3.2 的 W1–W10（单一真源；本模块只做映射，不新造词）
W_REASONS = ("W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10")

# 一轮多因时的主因优先级（高→低）：安全/债务/社交/市场优先，定时兜底最低
_PRIORITY = ("W3", "W5", "W2", "W4", "W10", "W6", "W7", "W8", "W9", "W1")

DEFAULT_WAKE = {
    "enabled": False,
    "base_cadence_rounds": 12,          # W1 定时兜底：至少每 12 回合（=1 仿真日）醒一次
    "triggers": {w: True for w in W_REASONS},
}


def wake_config(config) -> dict:
    """读取并规整 policy.wake（缺失→默认全关）。缺键保守=默认。"""
    pol = (config or {}).get("policy", {}) if isinstance(config, dict) else {}
    w = pol.get("wake", {}) if isinstance(pol, dict) else {}
    if not isinstance(w, dict):
        w = {}
    triggers = dict(DEFAULT_WAKE["triggers"])
    raw_tr = w.get("triggers", {})
    if isinstance(raw_tr, dict):
        for k, v in raw_tr.items():
            if k in triggers:
                triggers[k] = bool(v)
    return {
        "enabled": bool(w.get("enabled", DEFAULT_WAKE["enabled"])),
        "base_cadence_rounds": int(w.get("base_cadence_rounds", DEFAULT_WAKE["base_cadence_rounds"])),
        "triggers": triggers,
    }


def enabled(config) -> bool:
    return wake_config(config)["enabled"]


def _history(state) -> tuple[dict, dict]:
    """从已提交日志折叠每 Agent 的「上次唤醒」：{aid: last_wake_seq} / {aid: last_wake_round}。"""
    last_seq: dict[str, int] = {}
    last_round: dict[str, int] = {}
    from .event_acc import recs_of_type  # T295：读路径增量聚合
    for rec in recs_of_type(state, "WAKE"):
        aid = (rec.get("payload") or {}).get("agent_id")
        if not aid:
            continue
        s = int(rec.get("seq", 0) or 0)
        if s > last_seq.get(aid, 0):
            last_seq[aid] = s
        r = int(rec.get("round", 0) or 0)
        if r >= last_round.get(aid, -1):
            last_round[aid] = r
    return last_seq, last_round


def compute_wake_set(state, round_no: int, config=None) -> dict:
    """计算本轮唤醒集（确定性）。返回 {agent_id: {reason, all_reasons, source_event_seq}}。"""
    cfg = wake_config(config)
    if not cfg["enabled"]:
        return {}
    trg = cfg["triggers"]
    agents = getattr(state, "agents", None) or {}
    if not agents:
        return {}

    last_seq, last_round = _history(state)
    floor = min(last_seq.values(), default=0)

    # 场所 → Agent 倒排（W6 共处；一次构建，避免逐事件 O(N)）
    agents_by_place: dict[str, list[str]] = {}
    for a in agents:
        place = agents[a].get("location")
        if place:
            agents_by_place.setdefault(place, []).append(a)
    group_members = {
        gid: set((g or {}).get("members", []) or [])
        for gid, g in (getattr(state, "groups", {}) or {}).items()
    }

    aff: dict[str, dict] = {}

    def add(aid, reason, seq):
        if not aid or aid not in agents or not trg.get(reason, True):
            return
        aff.setdefault(aid, {}).setdefault(reason, seq)

    from .event_acc import seqs_of_round  # T312：按 round 取（替代跨全历史扫）
    # floor 所在回合（floor=0 或无对应记录 → 0 ⇒ 退化为从回合 0 起，语义不变）
    fr = int((state.event_index.get(floor) or {}).get("round", 0)) if floor else 0
    _cand: list = []
    for rd in range(fr, int(round_no) + 1):
        _cand.extend(s for s in seqs_of_round(state, rd) if s > floor)
    for _seq in _cand:
        rec = state.event_index[_seq]
        t = rec.get("type")
        p = rec.get("payload") or {}
        if t == "MSG_DM":
            add(p.get("from"), "W2", rec["seq"]); add(p.get("to"), "W2", rec["seq"])
        elif t == "MSG_GROUP":
            for m in group_members.get(p.get("group_id"), ()):
                add(m, "W2", rec["seq"])
            add(p.get("from"), "W2", rec["seq"])
        elif t == "MARKET_TRADE":
            add(p.get("buyer"), "W4", rec["seq"]); add(p.get("seller"), "W4", rec["seq"])
        elif t == "OFFER_CREATED":
            for a in (p.get("to") or []):
                add(a, "W10", rec["seq"])
            add(p.get("from"), "W4", rec["seq"])
        elif t in ("OFFER_ACCEPTED", "OFFER_REJECTED", "OFFER_COUNTERED", "OFFER_EXPIRED"):
            add(p.get("from"), "W4", rec["seq"])
            for a in (p.get("to") or []):
                add(a, "W4", rec["seq"])
        elif t in ("LOAN_ISSUED", "LOAN_REPAY", "LOAN_DEFAULT", "INTEREST_CHARGED"):
            add(p.get("borrower"), "W5", rec["seq"])
            add(p.get("lender"), "W5", rec["seq"])
            add(p.get("payer"), "W5", rec["seq"])
        elif t in ("PLACE_ARRIVED", "PLACE_MOVE", "ACTIVITY_STARTED",
                   "ACTIVITY_COMPLETED", "RELATION_ENCOUNTER"):
            place = p.get("place") or p.get("to_place")
            actor = rec.get("actor") or p.get("agent_id")
            if place:
                for a in agents_by_place.get(place, ()):
                    if a != actor:
                        add(a, "W6", rec["seq"])
        elif t in ("SCHEDULE_PLANNED", "SCHEDULE_REVISED"):
            add(p.get("agent_id"), "W7", rec["seq"])
        elif t == "NEED_UPDATE":
            add(p.get("agent_id"), "W8", rec["seq"])
        elif t == "STATE_CHANGE":
            if p.get("to") in ("warning", "near_death"):
                add(p.get("agent_id"), "W3", rec["seq"])

    # W9 周相位：一周开始（day_of_week==0 且 morning 且 tick0）→ 全体醒
    tcfg = config.get("time_config") if isinstance(config, dict) else None
    ti = derive_time(int(round_no), tcfg)
    if trg.get("W9", True) and ti["day_of_week"] == 0 and ti["slot"] == "morning" \
            and ti["tick_in_slot"] == 0:
        for a in agents:
            add(a, "W9", None)

    # W1 定时兜底：距上次唤醒 ≥ cadence（未唤醒过者立即计入）→ 保证 liveness
    cad = cfg["base_cadence_rounds"]
    if trg.get("W1", True) and cad > 0:
        for a in agents:
            lr = last_round.get(a)
            if lr is None or (int(round_no) - lr) >= cad:
                add(a, "W1", None)

    out = {}
    for aid, reasons in aff.items():
        chosen = next((r for r in _PRIORITY if r in reasons), None)
        if chosen is None:
            continue
        out[aid] = {
            "reason": chosen,
            "all_reasons": [r for r in _PRIORITY if r in reasons],
            "source_event_seq": reasons.get(chosen),
        }
    return out


__all__ = ["W_REASONS", "DEFAULT_WAKE", "wake_config", "enabled", "compute_wake_set"]
