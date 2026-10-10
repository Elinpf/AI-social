"""测试辅助：构造**哈希链合法**的合成事件日志（仅供 tests 使用）。

生产代码不依赖本模块。使用内核 `engine.ledger.Ledger` 落账以生成合法
`prev_hash`/`hash` 链（观测层只读消费）。
"""

from __future__ import annotations

from engine.ledger import Ledger

PHASE_ROUTE = 0
PHASE_DECIDE = 2
PHASE_COMMUNICATE = 3
PHASE_LIFE = 35
PHASE_ARBITRATE = 4
PHASE_LIFECYCLE = 5
PHASE_COMMIT = 6


class LogBuilder:
    """按序追加事件，生成合法哈希链日志。"""

    def __init__(self, seed: int = 1, engine_version: str = "v1.1-test"):
        self.seed = seed
        self.engine_version = engine_version
        self.ledger = Ledger(engine_version=engine_version)
        self.ledger.append(0, PHASE_ROUTE, "SYSTEM", "WORLD_INIT",
                           {"seed": seed, "engine_version": engine_version})

    def add(self, round_no, phase, actor, type_, payload=None):
        return self.ledger.append(round_no, phase, actor, type_, payload or {})

    def born(self, aid, round_no=0, endow=10000):
        self.add(round_no, PHASE_ROUTE, "SYSTEM", "AGENT_BORN",
                 {"agent_id": aid, "birth_round": round_no})
        self.add(round_no, PHASE_ROUTE, "SYSTEM", "INIT_ENDOW",
                 {"agent_id": aid, "amount": endow})
        self.add(round_no, PHASE_ROUTE, "SYSTEM", "MONEY_MINTED",
                 {"amount": endow, "reason": "genesis"})
        return self

    def records(self):
        return self.ledger.records


def build_log(seed=1, agents=("A000", "A001", "A002"), endow=10000, engine_version="v1.1-test"):
    lb = LogBuilder(seed=seed, engine_version=engine_version)
    for a in agents:
        lb.born(a, 0, endow)
    return lb


def kernel_shell_log(rounds=20, seed=12345, agents=("A000", "A001", "A002"),
                     endow=10000, engine_version="v1.1-skeleton"):
    """构造与内核空世界等价的「内核外壳」日志：创世 + 每回合 TURN_SEAL。

    仅依赖 `engine.ledger`（哈希链稳定契约），与内核 kernel/runner 的重构解耦；
    用于在内核重构期间离线验证观测层。日志格式与内核一致（事件外壳 08 §1.1）。
    """
    lb = LogBuilder(seed=seed, engine_version=engine_version)
    for a in agents:
        lb.born(a, 0, endow)
    for r in range(int(rounds)):
        lb.add(r, 6, "SYSTEM", "TURN_SEAL", {
            "round": r, "last_seq": len(lb.records()),
            "last_hash": lb.ledger.last_hash(),
        })
    return lb.records()

