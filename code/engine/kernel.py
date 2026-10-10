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
        from .hooks import assert_production_available
        assert_production_available(config)
        self.state = initial_state(self.seed)
        self.ctx = Ctx(self.seed, config, 0, 0)
        # 生活层驱动：每回合在 Phase 2 DECIDE 调用 agent.step()（注入，不 import life）
        self.agent_steppers: list = []

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
        # P0：事件队列出队到点事件；计算唤醒集合（按 agent_id 升序，W1–W6）。
        return None

    def phase_perceive(self, round_no: int) -> None:
        # P1：为被唤醒 Agent 构造只读 world_view（IF-1），无副作用、不产事件。
        return None

    def phase_decide(self, round_no: int) -> None:
        # P2：T0/T1/T2 决策。life 模式下调用被注入的 agent.step()（经 IF-2 即时入缓冲）。
        if self.agent_steppers:
            for agent in sorted(self.agent_steppers, key=lambda a: a.agent_id):
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
        viols = conservation.check_all(self.state, self.config)
        if viols:
            self._restore_from_ledger(round_no)  # 丢弃整个缓冲（含 P2 LLM_CALL）
            self._direct_append([
                spec(round_no, PHASE_COMMIT, "SYSTEM", "ECONOMY_INVARIANT_VIOLATION", v)
                for v in viols
            ])
        else:
            self.state, _ = self.arbiter.commit(self.state)
        self._seal(round_no)

    # ---- IF-1/IF-2 端口辅助（Adapter 也复用）----
    def current_round(self) -> int:
        return self.state.round

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
