"""世界状态（权威，函数式风格：折叠产生新 state 或就地确定性更新）。

P2：State = reduce(apply, EventLog, InitialState)。
只有中央裁决器 Arbiter 通过 apply_event 修改本状态；hook 不得直写。

状态同时承载：
  - 货币/生命周期（内核所有）：cash/deposits/loans/tax_pool/bank_reserve/money_*...
  - 生活层派生（非货币，life 层只读、内核折叠）：agents[*].{location,schedule,
    started_slots,current_activity,needs,memories,observed_event_seqs}、
    memory_index/event_index/observed/rejected。

为让 life 层能以 duck-typed 映射读写（`state["agents"]`、`state.setdefault(...)`），
WorldState 实现受限的映射协议；未知键存入 `_extra`。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .canon import hash_obj

# status 白名单（6 值，v1 §5.9 式(5)）
STATUS_WHITELIST = ("alive", "warning", "near_death", "dead", "revived", "terminated")

# 合法状态迁移边（非法转换 -> SYSTEM_ERROR）
LEGAL_STATUS_EDGES = {
    ("alive", "warning"), ("alive", "near_death"), ("alive", "dead"), ("alive", "terminated"),
    ("warning", "near_death"), ("warning", "alive"), ("warning", "dead"), ("warning", "terminated"),
    ("near_death", "dead"), ("near_death", "warning"), ("near_death", "alive"), ("near_death", "terminated"),
    ("dead", "revived"), ("dead", "terminated"),
    ("revived", "alive"), ("revived", "terminated"),
}

# 映射协议暴露的属性键
_ATTR_KEYS = frozenset({
    "round", "seed", "agents", "cash", "deposits", "loans", "tax_pool", "bank_reserve",
    "money_minted_total", "money_burned_total", "judgments", "pending_intents",
    "audit_violations", "memory_index", "event_index", "observed", "rejected",
    "relations", "encounters", "tags", "norms", "groups", "inventory", "budget_level",
    "events_by_round", "seqs_by_type", "acc_n", "acc_trusted",
})


def new_agent_dict(agent_id: str, *, status: str = "alive", birth_round: int = 0,
                   location: str = "residence", needs: dict | None = None) -> dict:
    """一只 Agent 的完整状态字典（货币字段另存于 state.cash）。"""
    return {
        "agent_id": agent_id,
        "status": status,
        "birth_round": int(birth_round),
        "death_round": None,
        # ---- 生活层派生（内核折叠，life 只读）----
        "location": location,
        "schedule": [],
        "started_slots": [],
        "current_activity": None,
        "needs": dict(needs or {}),
        "goals": {},
        "encounters": {},
        "memories": [],
        "observed_event_seqs": [],
    }


@dataclass
class WorldState:
    round: int = 0
    seed: int = 0
    agents: dict = field(default_factory=dict)       # agent_id -> agent dict
    cash: dict = field(default_factory=dict)         # agent_id -> mu
    deposits: dict = field(default_factory=dict)     # agent_id -> mu
    loans: dict = field(default_factory=dict)        # loan_id -> loan dict
    tax_pool: int = 0                                # 税池
    bank_reserve: int = 0                            # 银行库存
    money_minted_total: int = 0
    money_burned_total: int = 0
    judgments: dict = field(default_factory=dict)    # judgment_id -> decision（冻结 LLM 判定）
    pending_intents: list = field(default_factory=list)
    audit_violations: list = field(default_factory=list)
    # ---- 生活层派生索引 ----
    memory_index: dict = field(default_factory=dict)  # mem_id -> memory ref
    event_index: dict = field(default_factory=dict)   # seq -> event record（不入 state_hash）
    # T295：读路径增量聚合（派生缓存，不入 state_hash；可由日志重建，续跑由 replay 恢复）
    # round -> {type -> [seq,...]}（seq 升序）
    events_by_round: dict = field(default_factory=dict)
    # type -> [seq,...]（全局，seq 升序）
    seqs_by_type: dict = field(default_factory=dict)
    # 累加器已索引条数（自愈标记：与 len(event_index) 不一致 ⇒ 重建）
    acc_n: int = 0
    # T295：累加器是否可信 —— 仅 Engine / replay_records 产出的状态为 True；
    # 手工构造/直接注入 event_index 的状态为 False（读取时按全扫等价重建）。
    acc_trusted: bool = False
    observed: dict = field(default_factory=dict)      # agent_id -> [target_event_seq,...]
    rejected: list = field(default_factory=list)      # INTENT_REJECTED 摘要
    # ---- M3 关系 / M7 目标 / 传播（life 折叠，纳入 state_hash）----
    relations: dict = field(default_factory=dict)     # from -> to -> dim -> int
    encounters: list = field(default_factory=list)    # RELATION_ENCOUNTER 记录
    tags: list = field(default_factory=list)          # TAG_EMITTED 记录
    norms: dict = field(default_factory=dict)         # norm_id -> {...}
    groups: dict = field(default_factory=dict)        # group_id -> {group_id, members:[...], created_round}
    inventory: dict = field(default_factory=dict)     # owner_id -> good_id -> qty:int（v2 物理层）
    budget_level: int = 0                             # M6 当前降级级位 L0–L3（单调不减；由 DEGRADE 折叠）
    _extra: dict = field(default_factory=dict)        # 未知映射键

    # ---- 便捷访问 ----
    def ensure_agent(self, agent_id: str, **kw) -> dict:
        birth_round = int(kw.pop("birth_round", self.round))
        if agent_id not in self.agents:
            self.agents[agent_id] = new_agent_dict(agent_id, birth_round=birth_round, **kw)
        else:
            a = self.agents[agent_id]
            for k, v in new_agent_dict(agent_id, birth_round=a.get("birth_round", birth_round)).items():
                a.setdefault(k, v)
        self.cash.setdefault(agent_id, 0)
        self.deposits.setdefault(agent_id, 0)
        return self.agents[agent_id]

    def agent(self, agent_id: str) -> dict:
        return self.agents[agent_id]

    def net_worth(self, agent_id: str) -> int:
        """净财富 = 现金 + 存款 − 贷款未偿本金。整数 mu。"""
        liab = 0
        for loan in self.loans.values():
            if loan.get("borrower") == agent_id and loan.get("status") in ("active", "overdue"):
                liab += int(loan.get("outstanding", 0))
        return int(self.cash.get(agent_id, 0)) + int(self.deposits.get(agent_id, 0)) - liab

    def alive_agents(self) -> list[str]:
        return sorted(a for a, st in self.agents.items()
                      if st.get("status") not in ("dead", "terminated"))

    # ---- 映射协议（life 层 duck-typing 用）----
    def __getitem__(self, key):
        if key in _ATTR_KEYS:
            return getattr(self, key)
        return self._extra[key]

    def __setitem__(self, key, value):
        if key in _ATTR_KEYS:
            setattr(self, key, value)
        else:
            self._extra[key] = value

    def __contains__(self, key):
        return key in _ATTR_KEYS or key in self._extra

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        if key in _ATTR_KEYS:
            return getattr(self, key)
        return self._extra.setdefault(key, default)

    # ---- 规范视图 ----
    def to_dict(self) -> dict:
        """state_hash 投影。

        排除由日志可重建的重集合（`memory_index`/`observed`/`event_index`/每 Agent
        `memories`/全局 `encounters`）与瞬时队列（`pending_intents`）——它们已由哈希链
        上的事件保证完整；保留会影响后续确定性命中与生活语义的字段
        （status/location/schedule/needs/goals/relations/encounters(dict)/tags/norms）。
        """
        agents = {}
        for k in sorted(self.agents):
            agents[k] = {kk: vv for kk, vv in self.agents[k].items() if kk != "memories"}
        return {
            "round": self.round,
            "seed": self.seed,
            "agents": agents,
            "cash": {k: self.cash[k] for k in sorted(self.cash)},
            "deposits": {k: self.deposits[k] for k in sorted(self.deposits)},
            "loans": {k: self.loans[k] for k in sorted(self.loans)},
            "tax_pool": self.tax_pool,
            "bank_reserve": self.bank_reserve,
            "money_minted_total": self.money_minted_total,
            "money_burned_total": self.money_burned_total,
            "judgments": {k: self.judgments[k] for k in sorted(self.judgments)},
            "relations": {a: {b: dims for b, dims in self.relations[a].items() if dims}
                          for a in sorted(self.relations) if any(self.relations[a].values())},
            "tags": list(self.tags),
            "norms": {k: self.norms[k] for k in sorted(self.norms)},
            "groups": {k: self.groups[k] for k in sorted(self.groups)},
            "inventory": {o: {g: self.inventory[o][g] for g in sorted(self.inventory[o])}
                          for o in sorted(self.inventory)},
            "rejected": list(self.rejected),
        }


def initial_state(seed: int) -> WorldState:
    """创世初始状态 = 空世界（无 agent、无货币、无生活派生）。

    出生/初始注入以事件形式在 Phase 0 落账（AGENT_BORN / INIT_ENDOW / MONEY_MINTED），
    使 replay 从同一空状态折叠日志即可复现（P2）。
    """
    return WorldState(round=0, seed=int(seed))


def state_hash(state: WorldState) -> str:
    """状态规范哈希（'sha256:<hex>'）。同状态逐位一致。"""
    return hash_obj(state.to_dict())


def money_total(state: WorldState) -> int:
    """在流通货币总量 M = Σ cash + Σ deposits + 税池 + 银行库存。"""
    return (sum(state.cash.values())
            + sum(state.deposits.values())
            + state.tax_pool
            + state.bank_reserve)
