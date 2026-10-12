"""确定性内核 Engine：驱动回合，编排 P0–P6 与 hook 链。

- 唯一状态写入口 = 中央裁决器 Arbiter；
- 六阶段顺序固定（v1 §1.2）：0 ROUTE → 1 PERCEIVE → 2 DECIDE → 3 COMMUNICATE
  → 4 ARBITRATE → 5 LIFECYCLE → 6 COMMIT；v1.1 在 3 与 4 间插入 Phase 3.5 LIFE。
- Phase 6 追加日志 + 守恒校验 + turn_seal。
"""

from __future__ import annotations

from .arbiter import Arbiter
from .constants import (
    PHASE_ROUTE, PHASE_PERCEIVE, PHASE_DECIDE, PHASE_COMMUNICATE,
    PHASE_LIFE, PHASE_ARBITRATE, PHASE_LIFECYCLE, PHASE_COMMIT,
)
from . import conservation
from . import hooks as hook_registry
from . import scheduling
from . import wake
from .events import spec
from .ledger import Ledger
from .rng import Ctx
from .state import WorldState, initial_state, money_total, state_hash


class Engine:
    def __init__(self, seed: int, config: dict):
        self.seed = int(seed)
        self.config = config
        self.engine_version = config.get("engine_version", "v0.1-skeleton")
        self.time_unit = int(config.get("time_config", {}).get("TIME_UNIT", 1000))
        self.ledger = Ledger(time_unit=self.time_unit, engine_version=self.engine_version)
        self.arbiter = Arbiter(self.ledger)
        # 早失败：复现输入配置一致性（缺失/版本不匹配 -> ConfigError）
        from . import version as _version
        _version.assert_version_consistency()
        # 启动时捕获指纹（run 内固定用此值，避免运行期间配置被并发修改导致假不匹配）
        self.fingerprint = _fingerprint()
        # fail-loud：经济启用却未挂载 apply_production -> 直接报错（防生产静默停摆）
        from .hooks import assert_production_available, assert_exchange_available
        assert_production_available(config)
        # fail-loud：economy+exchange 启用却未挂载 apply_exchange -> 直接报错（防交易静默失效）
        assert_exchange_available(config)
        self.state = initial_state(self.seed)
        self.ctx = Ctx(self.seed, config, 0, 0)
        # 生活层驱动：每回合在 Phase 2 DECIDE 调用 agent.step()（注入，不 import life）
        self.agent_steppers: list = []
        # T265：本轮唤醒集（{agent_id: {...}}）；wake.enabled=False 时恒为 None（不解算）
        self._wake_set: dict | None = None
        # T253：通用「emit 后监听」扩展点 —— read-only 观察者，仅 **run 模式**在 P6 唯一
        # append 之后回调（replay 不经 run_round，故天然不回调）。engine 只提供注册+触发，
        # **不认识 life/side 格式**（谁注册、写什么由上层决定）。注册回调默认无 → 零影响。
        self.emit_observers: list = []

    # ---- T253：emit 后监听（read-only 观察者）----
    def register_emit_observer(self, fn) -> None:
        """注册「emit 后监听」回调 `fn(records: list[dict])`。

        - **run-only**：仅在 `run_round` 的 P6 唯一 append 之后触发；**replay 不触发**。
        - **read-only**：回调收到的是**本轮已提交事件的浅拷贝**，**不得改事件/世界**；
          契约由调用方遵守（engine 不 enforce，但传入拷贝以阻断对账本记录的原地修改）。
        - engine **不认识**回调写什么（格式/落盘全归注册方），也不 import 上游包。
        """
        if fn not in self.emit_observers:
            self.emit_observers.append(fn)

    def unregister_emit_observer(self, fn) -> None:
        try:
            self.emit_observers.remove(fn)
        except ValueError:
            pass

    def _notify_emit_observers(self, records: list) -> None:
        if not records or not self.emit_observers:
            return
        # 浅拷贝：阻止观察者原地改账本记录（payload 嵌套仍为引用，契约要求不写）
        snapshot = [dict(r) for r in records]
        for fn in list(self.emit_observers):
            fn(snapshot)

    # ---- 内部：写入本回合待提交缓冲区（D1：不落盘）----
    def _emit(self, specs: list) -> None:
        if specs:
            self.state, _ = self.arbiter.emit(self.state, specs)

    def emit_specs(self, specs: list) -> list[int]:
        """供端口（IF-2 / IF-2c）调用：入缓冲区并返回临时 seq（P6 才真正落盘）。"""
        self.state, seqs = self.arbiter.emit(self.state, specs)
        return seqs

    def _direct_append(self, specs: list) -> None:
        """直接落盘（仅用于创世 / P6 审计事件 / turn_seal，不属于回合缓冲）。"""
        if specs:
            self.state, _ = self.arbiter.emit(self.state, specs)
            self.state, _ = self.arbiter.commit(self.state)

    def load_prefix(self, records: list, round_no: int | None = None) -> None:
        """T276：从一份**已 flush 的完整前缀日志**恢复世界，续跑。

        - **原地替换** `ledger.records`（`records[:]=`）以保持 list 身份不变 —— 已注册的
          emit 观察者 / 可见性索引按 `id(records)` 绑定，替换身份会使其失联；
        - `replay_records(verify=True, verify_seals=True)` 重建状态并**断言指纹一致**
          （配置变更 → 旧前缀拒绝续跑，报错明说）；
        - `round_no` 显式给出时以它为准（否则取日志末回合）。
        **不动任何语义**：续跑与一次性跑同源。
        """
        from .replay import replay_records
        self.ledger.records[:] = [dict(r) for r in records]
        self.arbiter.discard()
        self.state = replay_records(self.ledger.records, verify=True, verify_seals=True,
                                    expected_fingerprint=self.fingerprint)
        r = int(round_no) if round_no is not None else int(self.state.round)
        self.state.round = r
        self.ctx = self.ctx.at(r, 0)

    def _restore_from_ledger(self, round_no: int) -> None:
        """回滚：丢弃本回合缓冲，用已提交日志重建状态（D1）。"""
        self.arbiter.discard()
        from .replay import replay_records
        self.state = replay_records(self.ledger.records, verify=False, verify_seals=False)
        self.state.round = int(round_no)

    # ---- 创世：空世界 + 出生/初始注入 ----
    def genesis(self, personas: dict | None = None) -> None:
        """personas: {agent_id: {"home_place":..., "needs_init":{...}}}（life 模式）。
        为 None 时按 config.genesis.agent_count 生成编号 Agent（空世界模式）。"""
        genesis_cfg = self.config.get("genesis", {})
        endow = int(genesis_cfg.get("initial_endowment_mu", 0))

        specs = [spec(0, PHASE_ROUTE, "SYSTEM", "WORLD_INIT", {
            "seed": self.seed,
            "engine_version": self.engine_version,
            "fingerprint": self.fingerprint,
            "config_components": _config_components(),
            "config_digest": _digest(self.config),
        })]
        born: list[tuple[str, str, dict]] = []
        if personas:
            for pid in sorted(personas):
                pinfo = personas[pid] or {}
                born.append((pid, pinfo.get("home_place", "residence"),
                             dict(pinfo.get("needs_init", {}))))
        else:
            for i in range(int(genesis_cfg.get("agent_count", 0))):
                born.append((f"A{i:03d}", "residence", {}))

        total = 0
        for aid, home, needs in born:
            specs.append(spec(0, PHASE_ROUTE, "SYSTEM", "AGENT_BORN",
                              {"agent_id": aid, "birth_round": 0,
                               "home_place": home, "needs_init": needs}))
            specs.append(spec(0, PHASE_ROUTE, "SYSTEM", "INIT_ENDOW",
                              {"agent_id": aid, "amount": endow}))
            total += endow
        if total:
            specs.append(spec(0, PHASE_ROUTE, "SYSTEM", "MONEY_MINTED",
                              {"amount": total, "reason": "genesis"}))
        self._direct_append(specs)  # 创世属已提交日志（不属于任何回合缓冲）

    # ---- 六个主阶段（骨架，产 EventSpec）----
    def phase_route(self, round_no: int) -> None:
        # P0：个体决策节拍（T265）—— 计算本轮唤醒集 W1–W10（确定性纯函数）。
        # **默认 wake.enabled=False → 不解算、零行为变化**（保 T236 基线）。
        self._wake_set = None
        if not wake.enabled(self.config):
            return
        ws = wake.compute_wake_set(self.state, round_no, self.config)
        self._wake_set = ws
        specs = []
        for aid in sorted(ws):
            info = ws[aid]
            specs.append(spec(round_no, PHASE_ROUTE, aid, "WAKE", {
                "agent_id": aid, "round": round_no,
                "reason": info["reason"],
                "source_event_seq": info["source_event_seq"],
                "all_reasons": list(info["all_reasons"]),
            }))
        total = len(self.state.agents)
        woken = len(ws)
        by_reason = {w: 0 for w in wake.W_REASONS}
        for info in ws.values():
            by_reason[info["reason"]] = by_reason.get(info["reason"], 0) + 1
        specs.append(spec(round_no, PHASE_ROUTE, "SYSTEM", "IDLE", {
            "round": round_no, "total_agents": total,
            "woken": woken, "idle": total - woken, "by_reason": by_reason,
        }))
        self._emit(specs)

    def phase_perceive(self, round_no: int) -> None:
        # P1：为被唤醒 Agent 构造只读 world_view（IF-1），无副作用、不产事件。
        return None

    def phase_decide(self, round_no: int) -> None:
        # P2：T0/T1/T2 决策。life 模式下调用被注入的 agent.step()（经 IF-2 即时入缓冲）。
        # T265：wake.enabled 时**仅被唤醒的 Agent** 进入 DECIDE；其余安静（不 step）。
        if not self.agent_steppers:
            return
        steppers = sorted(self.agent_steppers, key=lambda a: a.agent_id)
        if wake.enabled(self.config) and self._wake_set is not None:
            woken = set(self._wake_set)
            for agent in steppers:
                if agent.agent_id in woken:
                    agent.step()
        else:
            for agent in steppers:
                agent.step()

    def phase_communicate(self, round_no: int) -> None:
        # P3：三通道消息（配额/惩罚约束）。
        return None

    def phase_life(self, round_no: int) -> None:
        # P3.5：L1–L7（顺序固定）。**逐 hook 即时折叠**——后续 hook 必须看到前面 hook
        # 产出的（已入缓冲并折叠的）事件（如 L7 读 L3 的 ACTIVITY_COMPLETED）。
        for fn in hook_registry.get_phase35_hooks():
            raw = fn(self.state, round_no, self.ctx)
            if raw:
                self._emit(_coerce_specs(round_no, raw))

    def phase_arbitrate(self, round_no: int) -> None:
        # P4：hook 链 4.1–4.8（顺序冻结，X2）。同样逐 hook 即时折叠。
        for fn in hook_registry.get_phase4_hooks():
            raw = fn(self.state, round_no, self.ctx)
            if raw:
                self._emit(raw)

    def phase_lifecycle(self, round_no: int) -> None:
        # P5：STATE_CHANGE / AGENT_DIED / AGENT_REVIVED 的终局提交阶段。
        return None

    def _seal(self, round_no: int) -> None:
        payload = {
            "round": round_no,
            "last_seq": len(self.ledger.records),
            "last_hash": self.ledger.last_hash(),
            "state_hash": state_hash(self.state),
            "money_supply": money_total(self.state),
            "money_minted_total": self.state.money_minted_total,
            "money_burned_total": self.state.money_burned_total,
        }
        self._direct_append([spec(round_no, PHASE_COMMIT, "SYSTEM", "TURN_SEAL", payload)])

    # ---- 单个回合（D1：emit 入缓冲，P6 唯一 append，异常/守恒→整回合回滚）----
    def run_round(self, round_no: int) -> None:
        self.state.round = round_no
        self.ctx = self.ctx.at(round_no, 0)
        self.arbiter.discard()  # 回合起始：清空待提交缓冲区

        try:
            self.phase_route(round_no)
            self.phase_perceive(round_no)
            self.phase_decide(round_no)
            self.phase_communicate(round_no)
            self.phase_life(round_no)
            self.phase_arbitrate(round_no)
            self.phase_lifecycle(round_no)
        except Exception as exc:  # 任一 hook 抛异常 -> 整回合回滚
            self._restore_from_ledger(round_no)
            self._direct_append([spec(round_no, PHASE_COMMIT, "SYSTEM", "SYSTEM_ERROR",
                                      {"where": "run_round", "detail": repr(exc)})])
            self._seal(round_no)
            return

        # P6 COMMIT：守恒校验 → 唯一 append
        committed: list = []
        viols = conservation.check_all(self.state, self.config)
        if viols:
            self._restore_from_ledger(round_no)  # 丢弃整个缓冲（含 P2 LLM_CALL）
            self._direct_append([
                spec(round_no, PHASE_COMMIT, "SYSTEM", "ECONOMY_INVARIANT_VIOLATION", v)
                for v in viols
            ])
        else:
            # M6：级位上升时发 DEGRADE（可观测，禁止静默；入本回合缓冲随 P6 commit）
            self._emit(scheduling.degrade_specs(self.state, round_no, self.config))
            # M4：本轮未被调度许可的 agent 也要显式落 DEGRADE（不静默）
            skip = scheduling.schedule_skip_spec(self.state, round_no, self.config,
                                                 priority=_status_pri(self.state))
            if skip is not None:
                self._emit([skip])
            self.state, committed = self.arbiter.commit(self.state)
        self._seal(round_no)
        # T253：仅成功提交的回合触发「emit 后监听」（含 TURN_SEAL 之前的本回合事件）；
        # 回滚/异常路径不触发（观察者只看"已真正落盘的世界事件"）。
        self._notify_emit_observers(committed)

    # ---- IF-1/IF-2 端口辅助（Adapter 也复用）----
    def current_round(self) -> int:
        return self.state.round

    # ---- M4/M6（T215）----
    @property
    def llm_budget_level(self) -> int:
        return int(getattr(self.state, "budget_level", 0) or 0)

    def schedule_llm(self, agents, round_no: int | None = None, priority=None) -> list:
        """M4 峰值削平：返回本回合允许调用 LLM 的 agent_id 列表（≤ Kc）。"""
        kc = int(scheduling._budget_cfg(self.config).get("max_concurrency_kc", 0) or 0)
        r = self.state.round if round_no is None else round_no
        return scheduling.schedule_llm_agents(agents, r, kc, priority=priority)

    def derive_time(self, round_no: int | None = None) -> dict:
        from .time import derive_time as _derive
        r = self.state.round if round_no is None else round_no
        tcfg = self.config.get("time_config") if isinstance(self.config, dict) else None
        return _derive(r, tcfg)

    # ---- 主循环 ----
    def run(self, rounds: int, personas: dict | None = None) -> WorldState:
        self.genesis(personas)
        for r in range(int(rounds)):
            self.run_round(r)
        return self.state


def _status_pri(state):
    """M4 调度优先级：濒死 > 预警 > 复活缓冲 > 常规（关键路径优先）。"""
    def pri(aid):
        return {"near_death": 3, "warning": 2, "revived": 1}.get(
            state.agents.get(aid, {}).get("status"), 0)
    return pri


def _coerce_specs(round_no: int, raw: list) -> list:
    """把 hook 返回的事件规格（可能是 life 层的 EventSpec）归一为 engine.EventSpec。"""
    from .events import EventSpec
    out = []
    for s in raw:
        if isinstance(s, EventSpec):
            out.append(s)
        else:
            out.append(spec(round_no, getattr(s, "phase", 0), getattr(s, "actor", "SYSTEM"),
                            getattr(s, "type"), getattr(s, "payload", {}) or {}))
    return out


def _digest(config: dict) -> str:
    from .canon import hash_obj
    return hash_obj(config)


def _fingerprint() -> str:
    from . import version
    return version.compute_fingerprint()


def _config_components() -> dict:
    from . import version
    return version.component_digests()
