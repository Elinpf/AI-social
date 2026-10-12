"""重放：replay = reduce(apply, EventLog, InitialState)（§6.2 / 08 §5.3）。

关键契约：
  - 重放**不重跑 hook**，只按日志折叠事件（I2 / X5）；
  - apply_event 是唯一的状态折叠入口，与首跑经中央裁决器落账的语义一致；
  - 遇到未注册的事件类型立即报错（X4），绝不静默忽略。

因此「首跑最终状态」与「重放最终状态」逐位一致（同一份日志）。
"""

from __future__ import annotations

from .ledger import verify_chain  # re-export（供 engine.__init__ / 外部校验）
from .state import WorldState, initial_state
from contracts.errors import UnknownEventType

# 事件类型 -> 折叠器(state, record, payload)
_APPLIERS: dict = {}


def register(type_: str):
    def deco(fn):
        _APPLIERS[type_] = fn
        return fn
    return deco


def registered_types() -> set:
    return set(_APPLIERS)


def _get_cash(state: WorldState, agent_id: str) -> int:
    return int(state.cash.get(agent_id, 0))


def _set_cash(state: WorldState, agent_id: str, value: int) -> None:
    state.cash[agent_id] = int(value)


# ---------------- 创世 / 世界 ----------------

@register("WORLD_INIT")
def _apply_world_init(state, rec, p):
    state.seed = int(p.get("seed", state.seed))


@register("AGENT_BORN")
def _apply_agent_born(state, rec, p):
    aid = p["agent_id"]
    a = state.ensure_agent(
        aid,
        birth_round=int(p.get("birth_round", rec["round"])),
        location=str(p.get("home_place", "residence")),
        needs=dict(p.get("needs_init", {})),
    )
    a["status"] = "alive"
    a["death_round"] = None
    state.observed.setdefault(aid, [])


@register("INIT_ENDOW")
def _apply_init_endow(state, rec, p):
    aid = p["agent_id"]
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) + int(p["amount"])


# ---------------- 货币发行 / 销毁 ----------------

@register("MONEY_MINTED")
def _apply_minted(state, rec, p):
    state.money_minted_total += int(p["amount"])


@register("MONEY_BURNED")
def _apply_burned(state, rec, p):
    state.money_burned_total += int(p["amount"])


# ---------------- 经济：原子转账 / 成交 ----------------

@register("TRANSFER")
def _apply_transfer(state, rec, p):
    frm, to = p["from"], p["to"]
    amount = int(p["amount"])
    fee = int(p.get("fee", 0))
    state.ensure_agent(frm)
    state.ensure_agent(to)
    state.cash[frm] = _get_cash(state, frm) - amount - fee
    state.cash[to] = _get_cash(state, to) + amount
    if fee:
        state.money_burned_total += fee  # 手续费销毁（骨架口径，可被 econ 层扩展）


@register("MARKET_TRADE")
def _apply_market_trade(state, rec, p):
    buyer, seller = p["buyer"], p["seller"]
    amount = int(p["amount"])
    fee = int(p.get("fee", 0))
    state.ensure_agent(buyer)
    state.ensure_agent(seller)
    state.cash[buyer] = _get_cash(state, buyer) - amount - fee
    state.cash[seller] = _get_cash(state, seller) + amount
    if fee:
        state.money_burned_total += fee


# ---------------- 经济：税 / UBI / 代谢 / 罚没 / 利息 ----------------

@register("TAX_LEVIED")
def _apply_tax(state, rec, p):
    aid = p["agent_id"]
    amt = int(p["amount"])
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) - amt
    state.tax_pool += amt


@register("UBI_PAID")
def _apply_ubi(state, rec, p):
    aid = p["agent_id"]
    amt = int(p["amount"])
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) + amt
    state.tax_pool -= amt


@register("METABOLISM")
def _apply_metabolism(state, rec, p):
    aid = p["agent_id"]
    amt = int(p["amount"])
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) - amt
    state.money_burned_total += amt  # 代谢消耗 -> 销毁


@register("PENALTY_APPLIED")
def _apply_penalty(state, rec, p):
    aid = p["agent_id"]
    amt = int(p["amount"])
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) - amt
    state.money_burned_total += amt


@register("REVIVE_FEE_PAID")
def _apply_revive_fee(state, rec, p):
    aid = p["agent_id"]
    amt = int(p["amount"])
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) - amt
    state.bank_reserve += amt  # 入复活/续命池（骨架口径）


@register("INTEREST_CHARGED")
def _apply_interest_charged(state, rec, p):
    aid = p["borrower"]
    amt = int(p["amount"])
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) - amt
    state.tax_pool += amt


@register("INTEREST_PAID")
def _apply_interest_paid(state, rec, p):
    aid = p["agent_id"]
    amt = int(p["amount"])
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) + amt
    state.bank_reserve -= amt


# ---- 银行：现金↔存款科目转移（08 §1.2 L / T14-C3；与 obs/econ.fold_economy 同口径）----

@register("DEPOSIT")
def _apply_deposit(state, rec, p):
    aid = p["agent_id"]
    amt = int(p["amount"])
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) - amt
    state.deposits[aid] = int(state.deposits.get(aid, 0)) + amt


@register("WITHDRAW")
def _apply_withdraw(state, rec, p):
    aid = p["agent_id"]
    amt = int(p["amount"])
    state.ensure_agent(aid)
    state.cash[aid] = _get_cash(state, aid) + amt
    state.deposits[aid] = int(state.deposits.get(aid, 0)) - amt


# ---------------- 借贷台账 ----------------

@register("LOAN_ISSUED")
def _apply_loan_issued(state, rec, p):
    lid = p["loan_id"]
    lender = p.get("lender")
    borrower = p["borrower"]
    principal = int(p["principal"])
    state.ensure_agent(borrower)
    if lender is not None:
        state.ensure_agent(lender)
        state.cash[lender] = _get_cash(state, lender) - principal
    else:
        state.money_minted_total += principal  # 系统续命贷：发行
    state.cash[borrower] = _get_cash(state, borrower) + principal
    state.loans[lid] = {
        "loan_id": lid, "lender": lender, "borrower": borrower,
        "principal": principal, "outstanding": principal,
        "rate_bp": int(p.get("rate_bp", 0)), "due_round": int(p.get("due_round", 0)),
        "status": "active", "repaid_total": 0,
    }


@register("LOAN_REPAY")
def _apply_loan_repay(state, rec, p):
    lid = p["loan_id"]
    amt = int(p["amount"])
    loan = state.loans.get(lid)
    if loan is not None:
        loan["outstanding"] = int(loan.get("outstanding", 0)) - amt
        loan["repaid_total"] = int(loan.get("repaid_total", 0)) + amt
        if loan["outstanding"] <= 0:
            loan["status"] = "repaid"
    payer = p.get("payer")
    if payer is not None:
        state.ensure_agent(payer)
        state.cash[payer] = _get_cash(state, payer) - amt


@register("LOAN_DEFAULT")
def _apply_loan_default(state, rec, p):
    lid = p["loan_id"]
    loan = state.loans.get(lid)
    if loan is not None:
        loan["status"] = "written_off"
        loan["outstanding"] = int(p.get("outstanding", loan.get("outstanding", 0)))


# ---------------- 生命周期 ----------------

@register("STATE_CHANGE")
def _apply_state_change(state, rec, p):
    aid = p["agent_id"]
    state.ensure_agent(aid)
    state.agents[aid]["status"] = p["to"]


@register("AGENT_DIED")
def _apply_agent_died(state, rec, p):
    aid = p["agent_id"]
    state.ensure_agent(aid)
    state.agents[aid]["status"] = "dead"
    state.agents[aid]["death_round"] = int(p.get("death_round", rec["round"]))


@register("AGENT_REVIVED")
def _apply_agent_revived(state, rec, p):
    aid = p["agent_id"]
    state.ensure_agent(aid)
    state.agents[aid]["status"] = "revived"
    state.agents[aid]["death_round"] = None


# ---------------- 软判定冻结（重放绝不重问 LLM，IF-6） ----------------

@register("LLM_JUDGMENT")
def _apply_llm_judgment(state, rec, p):
    jid = p["judgment_id"]
    state.judgments[jid] = p.get("decision")


# ---------------- 生活层派生（非货币，life 层只读；内核折叠） ----------------

DEFAULT_ACTIVITY_DURATION = 3  # = ROUNDS_PER_SLOT（一个时段）


@register("SCHEDULE_PLANNED")
def _apply_schedule_planned(state, rec, p):
    a = state.ensure_agent(p["agent_id"])
    a["schedule"] = list(p.get("slots", []))
    a["started_slots"] = []


@register("SCHEDULE_REVISED")
def _apply_schedule_revised(state, rec, p):
    state.ensure_agent(p["agent_id"])  # 计划微调：骨架仅确保 agent 存在


@register("ACTIVITY_STARTED")
def _apply_activity_started(state, rec, p):
    a = state.ensure_agent(p["agent_id"])
    a["started_slots"].append(p["slot_id"])
    a["current_activity"] = {
        "activity_id": p["activity_id"],
        "activity_type": p["activity_type"],
        "place": p["place"],
        "slot_id": p["slot_id"],
        "start_tick": int(p["start_tick"]),
        "duration_ticks": int(p.get("duration_ticks", DEFAULT_ACTIVITY_DURATION)),
    }


@register("ACTIVITY_COMPLETED")
def _apply_activity_completed(state, rec, p):
    state.ensure_agent(p["agent_id"])["current_activity"] = None


@register("ACTIVITY_INTERRUPTED")
def _apply_activity_interrupted(state, rec, p):
    state.ensure_agent(p["agent_id"])["current_activity"] = None


@register("NEED_UPDATE")
def _apply_need_update(state, rec, p):
    a = state.ensure_agent(p["agent_id"])
    a["needs"][p["dim"]] = int(p["after"])


@register("PLACE_MOVE")
def _apply_place_move(state, rec, p):
    state.ensure_agent(p["agent_id"])["location"] = p["to_place"]


@register("PLACE_ARRIVED")
def _apply_place_arrived(state, rec, p):
    state.ensure_agent(p["agent_id"])["location"] = p["place"]


@register("MEMORY_WRITE")
def _apply_memory_write(state, rec, p):
    a = state.ensure_agent(p["agent_id"])
    ref = {
        "mem_id": p["mem_id"], "kind": p["kind"], "body_ref": p["body_ref"],
        "embed_ref": p["embed_ref"], "importance": int(p["importance"]),
        "day": int(p["day"]), "slot": p["slot"], "subject": p.get("subject"),
        "source_event_seq": p.get("source_event_seq"),
        "last_access": rec["round"], "access_count": 0,
    }
    a["memories"].append(ref)
    state.memory_index[p["mem_id"]] = ref


@register("MEMORY_RETRIEVE")
def _apply_memory_retrieve(state, rec, p):
    for mid in p.get("selected_mem_ids", []):
        ref = state.memory_index.get(mid)
        if ref is not None:
            ref["last_access"] = rec["round"]
            ref["access_count"] = int(ref.get("access_count", 0)) + 1


# ---- T233 / 08 §1.2 S：睡眠 / 记忆整合遗忘 / 人格漂移 --------------------------
# Fork B 口径：按「可审计」折叠（纯确定性、无墙钟/浮点/环境）。指针/审计类
# （SLEEP_*/PERSONA_DRIFT）为 identity fold，不引入状态突变；记忆整合/遗忘折叠进
# `memory_index`/`agents[*].memories`（两者本就不入 state_hash，见 state.to_dict）。

@register("MEMORY_FORGET")
def _apply_memory_forget(state, rec, p):
    mid = p.get("mem_id")
    ref = state.memory_index.get(mid)
    if ref is not None and p.get("level") == "drop":
        state.memory_index.pop(mid, None)
        a = state.ensure_agent(p["agent_id"])
        a["memories"] = [m for m in a.get("memories", []) if m.get("mem_id") != mid]
    elif ref is not None:
        ref["forgotten_level"] = p.get("level")


@register("MEMORY_CONSOLIDATE")
def _apply_memory_consolidate(state, rec, p):
    a = state.ensure_agent(p["agent_id"])
    src = set(p.get("source_mem_ids") or [])
    for m in a.get("memories", []):
        if m.get("mem_id") in src:
            m["consolidated"] = True
    pid = p.get("produced_mem_id")
    if pid and pid not in state.memory_index:
        agent_id = p["agent_id"]
        ref = {"mem_id": pid, "kind": "semantic",
               "body_ref": f"side://mem/{agent_id}/{pid}.txt",
               "embed_ref": f"side://mem/{agent_id}/{pid}.vec",
               "importance": int(p.get("importance", 6)), "day": p.get("day"),
               "slot": p.get("slot"), "subject": p.get("subject"),
               "source_event_seq": None, "last_access": rec["round"], "access_count": 0}
        a.setdefault("memories", []).append(ref)
        state.memory_index[pid] = ref


@register("SLEEP_STARTED")
def _apply_sleep_started(state, rec, p):
    # 审计/指针事件：identity fold（观测层只读日志取用；不改状态）
    return None


@register("SLEEP_COMPLETED")
def _apply_sleep_completed(state, rec, p):
    # 审计事件：identity fold（payload 含 pf0/pf_t/drift_permille 供 obs 只读）
    return None


@register("PERSONA_DRIFT")
def _apply_persona_drift(state, rec, p):
    # 审计事件：identity fold（单事件单维；表达层向量由 life 侧维护）
    return None


@register("OBSERVATION")
def _apply_observation(state, rec, p):
    observer = p["observer"]
    state.observed.setdefault(observer, []).append(p["target_event_seq"])
    state.ensure_agent(observer)["observed_event_seqs"].append(p["target_event_seq"])


@register("INTENT_REJECTED")
def _apply_intent_rejected(state, rec, p):
    state.rejected.append({
        "agent_id": p.get("agent_id"), "intent_class": p.get("intent_class"),
        "reason": p.get("reason"),
    })


# ---------------- M3 关系 / M7 目标 / 传播（折叠进 state，纳入 state_hash） ----------------

@register("RELATION_CHANGE")
def _apply_relation_change(state, rec, p):
    state.relations.setdefault(p["from"], {}).setdefault(p["to"], {})[p["dim"]] = int(p["after"])


@register("RELATION_ENCOUNTER")
def _apply_relation_encounter(state, rec, p):
    a, b = p.get("a"), p.get("b")
    state.encounters.append({
        "a": a, "b": b, "place": p.get("place"),
        "day": p.get("day"), "slot": p.get("slot"),
        "duration_ticks": int(p.get("duration_ticks", 0)),
    })
    # 每 Agent 的 encounters 为「对方 agent_id -> 次数」字典（life L5 读取口径）
    for aid, other in ((a, b), (b, a)):
        if aid is not None and other is not None:
            enc = state.ensure_agent(aid).setdefault("encounters", {})
            enc[other] = int(enc.get(other, 0)) + 1


@register("GOAL_SET")
def _apply_goal_set(state, rec, p):
    a = state.ensure_agent(p["agent_id"])
    if "goal_id" not in p:  # 兼容旧批式 {agent_id, goals:[...]}
        for g in p.get("goals", []):
            gid = g["goal_id"]
            entry = dict(g)
            entry.setdefault("status", "active")
            entry.setdefault("progress", 0)
            a["goals"][gid] = entry
        return
    # 扁平式（08 §1.2-C）：单目标一条
    gid = p["goal_id"]
    entry = {
        "goal_id": gid, "agent_id": p.get("agent_id"), "kind": p.get("kind"),
        "layer": p.get("layer"), "priority": p.get("priority"),
        "description_ref": p.get("description_ref"),
        "target_metric": p.get("target_metric"), "deadline_week": p.get("deadline_week"),
        "status": "active", "progress": 0,
    }
    a["goals"][gid] = entry


@register("GOAL_PROGRESS")
def _apply_goal_progress(state, rec, p):
    a = state.ensure_agent(p["agent_id"])
    g = a["goals"].get(p.get("goal_id"))
    if g is not None:
        g["progress"] = p.get("after", p.get("progress", g.get("progress")))


@register("GOAL_ACHIEVED")
def _apply_goal_achieved(state, rec, p):
    a = state.ensure_agent(p["agent_id"])
    g = a["goals"].get(p.get("goal_id"))
    if g is not None:
        g["status"] = "achieved"


@register("GOAL_ABANDON")
def _apply_goal_abandon(state, rec, p):
    a = state.ensure_agent(p["agent_id"])
    g = a["goals"].get(p.get("goal_id"))
    if g is not None:
        g["status"] = "abandoned"
        g["abandon_reason"] = p.get("reason")


@register("TAG_EMITTED")
def _apply_tag_emitted(state, rec, p):
    state.tags.append({
        "agent_id": p.get("agent_id"), "tag": p.get("tag"),
        "valence": p.get("valence"), "source_msg_id": p.get("source_msg_id"),
    })


@register("NORM_PROPOSED")
def _apply_norm_proposed(state, rec, p):
    nid = p["norm_id"]
    state.norms[nid] = {
        "norm_id": nid, "proposer": p.get("proposer"), "status": "proposed",
        "rule_ref": p.get("rule_ref"), "support_count": int(p.get("support_count", 0)),
        "threshold": p.get("threshold"), "day": p.get("day"),
    }


@register("NORM_ADOPTED")
def _apply_norm_adopted(state, rec, p):
    nid = p["norm_id"]
    n = state.norms.setdefault(nid, {"norm_id": nid})
    n["status"] = "adopted"
    n["adopters"] = list(p.get("adopters", []))
    n["adopted_day"] = p.get("adopted_day")


@register("NORM_VIOLATED")
def _apply_norm_violated(state, rec, p):
    nid = p["norm_id"]
    n = state.norms.setdefault(nid, {"norm_id": nid})
    n.setdefault("violations", []).append({
        "violator": p.get("violator"), "day": p.get("day"), "severity": p.get("severity")})


# ---------------- 群组生命周期（v2 社会层：MSG_GROUP 可见性按时点重算） ----------------

@register("GROUP_CREATED")
def _apply_group_created(state, rec, p):
    gid = p["group_id"]
    state.groups[gid] = {
        "group_id": gid,
        "members": sorted(p.get("members", [])),
        "created_round": int(p.get("created_round", rec["round"])),
    }


@register("GROUP_JOINED")
def _apply_group_joined(state, rec, p):
    g = state.groups.setdefault(p["group_id"], {
        "group_id": p["group_id"], "members": [], "created_round": rec["round"]})
    if p["agent_id"] not in g["members"]:
        g["members"] = sorted(g["members"] + [p["agent_id"]])


@register("GROUP_LEFT")
def _apply_group_left(state, rec, p):
    g = state.groups.get(p["group_id"])
    if g and p["agent_id"] in g["members"]:
        g["members"] = [m for m in g["members"] if m != p["agent_id"]]


# ---------------- v2 物理层（T90）：库存增减/折旧（商品式；入 state_hash） ----------------

@register("PRODUCE")
def _apply_produce(state, rec, p):
    o, g, q = p["agent_id"], p["good_id"], int(p["qty"])
    state.inventory.setdefault(o, {})
    state.inventory[o][g] = int(state.inventory[o].get(g, 0)) + q


@register("CONSUME")
def _apply_consume(state, rec, p):
    o, g, q = p["agent_id"], p["good_id"], int(p["qty"])
    state.inventory.setdefault(o, {})
    state.inventory[o][g] = int(state.inventory[o].get(g, 0)) - q


@register("DEPRECIATE")
def _apply_depreciate(state, rec, p):
    o, a, d = p["agent_id"], p["asset_id"], int(p["delta_mu"])  # 对商品资产承载「损失单位数」
    state.inventory.setdefault(o, {})
    state.inventory[o][a] = max(0, int(state.inventory[o].get(a, 0)) - d)


@register("PRODUCE_OVERFLOW")
def _apply_produce_overflow(state, rec, p):
    return None  # 纯审计（库存未增；溢出量记于事件）


# ---------------- v2 交易原语（T131）：EXCHANGE_SETTLED（双边、原子、零和） ----------------

@register("EXCHANGE_SETTLED")
def _apply_exchange_settled(state, rec, p):
    legs = p.get("legs", {}) or {}
    for leg in legs.get("goods", []):
        f, t, g, q = leg["from"], leg["to"], leg["good_id"], int(leg["qty"])
        state.inventory.setdefault(f, {})
        state.inventory.setdefault(t, {})
        state.inventory[f][g] = int(state.inventory[f].get(g, 0)) - q
        state.inventory[t][g] = int(state.inventory[t].get(g, 0)) + q
    for leg in legs.get("money", []):
        f, t, m = leg["from"], leg["to"], int(leg["mu"])
        state.ensure_agent(f)
        state.ensure_agent(t)
        state.cash[f] = int(state.cash.get(f, 0)) - m
        state.cash[t] = int(state.cash.get(t, 0)) + m
    # 零和：不改 minted/burned（守恒式与商品总量式均不受影响）


# ---------------- 审计 / 无状态折叠 ----------------

@register("DEGRADE")
def _apply_degrade(state, rec, p):
    # M6 降级：单调记录当前级位（可观测；不改钱/货）
    lvl = int(p.get("level", 0) or 0)
    if lvl > state.budget_level:
        state.budget_level = lvl

@register("ECONOMY_INVARIANT_VIOLATION")
def _apply_violation(state, rec, p):
    # 纯审计事件：恒等折叠，**不改变世界状态**（保证 D1 回滚后状态不变）。
    return None


@register("SYSTEM_ERROR")
def _apply_system_error(state, rec, p):
    # 纯审计事件：恒等折叠，不改变世界状态。
    return None


# 纯输出 / 审计 / 时间锚点类：恒等折叠（不改变世界状态）
_NOOP_TYPES = [
    "TIME_MARK", "TURN_SEAL", "NARRATIVE",
    "MSG_PUBLIC", "MSG_DM", "MSG_GROUP", "LLM_CALL",
    "PLACE_MOVE", "PLACE_ARRIVED",
    "SCHEDULE_PLANNED", "SCHEDULE_REVISED",
    "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "ACTIVITY_INTERRUPTED",
    "NEED_UPDATE", "GOAL_SET", "GOAL_PROGRESS", "GOAL_ACHIEVED", "GOAL_ABANDON",
    "RELATION_CHANGE", "RELATION_ENCOUNTER",
    "MEMORY_WRITE", "MEMORY_RETRIEVE", "MEMORY_REFLECT",
    "OBSERVATION", "SEED_EVENT", "TAG_EMITTED", "ROLE_CHANGE",
    "NORM_PROPOSED", "NORM_ADOPTED", "NORM_VIOLATED",
    "SKILL_PRACTICE", "SKILL_LEVEL_UP", "SKILL_OUTPUT",
    "OFFER_CREATED", "OFFER_ACCEPTED", "OFFER_REJECTED", "OFFER_COUNTERED", "OFFER_EXPIRED",
    "SCORE_POSTED", "RANKING_EMITTED", "CONFLICT_STARTED", "CONFLICT_RESOLVED",
    "VOTE_CAST",
    "CONTRACT_CREATED", "CONTRACT_FULFILLED", "CONTRACT_VIOLATED", "CONTRACT_EXPIRED",
    "ORDER_CANCEL",
    "SERVICE_DELIVERED",  # T278/08 §1.2 V：服务即时交付 → inventory-neutral（noop 折叠，不改库存/现金）
    # 世界导演/事件制造机（Fork B：审计折叠，不改世界状态；replay 遇之不报错）
    "WORLD_DIRECTIVE", "WORLD_GROUP_EVENT", "WORLD_DIRECTIVE_REJECTED", "FORGE_FIRED",
    "INTENT_REJECTED", "DROPPED",
    # T265 个体决策节拍（08 §1.2 S）：唤醒/静默为审计事件，不改世界状态（no-op 折叠）
    "WAKE", "IDLE",
]
for _t in _NOOP_TYPES:
    _APPLIERS.setdefault(_t, lambda state, rec, p: None)


# ---------------- 折叠入口 ----------------

def apply_event(state: WorldState, record: dict) -> WorldState:
    type_ = record["type"]
    fn = _APPLIERS.get(type_)
    if fn is None:
        raise UnknownEventType(
            f"重放遇到未注册的事件类型: {type_!r}（X4：必须立即报错，禁止静默忽略）")
    r = int(record["round"])
    # round 单调不减：迟到/审计事件不得把 world round 回退（防 T55：审计事件带 stale round 污染 seal）
    if r >= state.round:
        state.round = r
    state.event_index[record["seq"]] = record  # 事件索引（OBSERVATION 锚点校验等）
    fn(state, record, record.get("payload", {}))
    return state


def replay_records(records: list, seed: int | None = None, verify: bool = True,
                   verify_seals: bool = True, expected_fingerprint: str | None = None) -> WorldState:
    """从事件日志重放得到最终状态。

    seed 省略时从 WORLD_INIT 事件读取。`expected_fingerprint` 显式给出时用于指纹断言
    （run 内应传启动时捕获的指纹，避免运行期间配置并发修改导致假不匹配）。
    """
    if verify:
        ok, err = _verify(records)
        if not ok:
            raise ValueError(f"日志校验失败，拒绝重放：{err}")
        from . import version as _version
        _version.assert_version_consistency()      # 版本声明一致性
        _version.assert_log_fingerprint(records, expected=expected_fingerprint)  # 指纹一致性
    if seed is None:
        seed = _seed_from_records(records)
    state = initial_state(seed)
    for rec in records:
        apply_event(state, rec)
    if verify_seals:
        _verify_seals(records)
    return state


def _verify(records: list) -> tuple[bool, str | None]:
    from .ledger import verify_chain
    return verify_chain(records)


def _seed_from_records(records: list) -> int:
    for rec in records:
        if rec["type"] == "WORLD_INIT":
            return int(rec["payload"]["seed"])
    raise ValueError("日志缺少 WORLD_INIT，无法确定 seed")


def _verify_seals(records: list) -> None:
    """校验每回合 TURN_SEAL 提交的 state_hash 与逐步重放一致（加固门禁）。"""
    from .state import initial_state, state_hash
    # 重新逐步折叠，遇 seal 即比对
    seed = _seed_from_records(records)
    state = initial_state(seed)
    for rec in records:
        apply_event(state, rec)
        if rec["type"] == "TURN_SEAL":
            committed = rec["payload"].get("state_hash")
            actual = state_hash(state)
            if committed is not None and committed != actual:
                raise ValueError(
                    f"TURN_SEAL 状态哈希不一致：round={rec['round']} "
                    f"committed={committed} actual={actual}"
                )
