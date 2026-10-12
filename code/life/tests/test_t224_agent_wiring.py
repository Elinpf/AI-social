"""T224 挂载点接线测试：睡眠离线窗在 `agent.step()` 内触发（mini_kernel 端到端，life 级）。

验证：默认关=无睡眠事件；开=night 产生 SLEEP_STARTED/COMPLETED + MEMORY_FORGET/CONSOLIDATE；
**保护记忆只 demote**。（引擎级接线另属 T224 待办，此处用 test-double。）
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life import sleep_window as SW
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"


def _places() -> dict:
    return {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}


def _build(tmp: Path):
    places = _places()
    persona = load_personas(CONFIG / "personas.json")["P003"]
    kernel = MiniKernel(seed=7, places=places)
    kernel._emit("AGENT_BORN", {"agent_id": "P003", "home_place": persona.home_place,
                                "needs_init": persona.needs_init}, phase=0, actor="SYSTEM")
    agent = LifeLayerAgent("P003", persona, kernel, side_store=SideStore(tmp / "side"),
                           embedding=HashEmbeddingModel(), places=places)
    return kernel, agent


def _inject_old_memories(agent: LifeLayerAgent) -> tuple[str, str]:
    ids = []
    for imp, subj in ((9, "P007"), (1, None)):
        payload = agent.memory.prepare_write(kind="observation", text=f"关于{subj}的事",
                                             importance=imp, day=0, slot="evening", tick=0,
                                             subject=subj)
        agent.memory.commit_write(payload)
        ids.append(payload["mem_id"])
    for n in agent.memory.nodes.values():
        n.last_access = -5000            # 极旧 → 触发遗忘候选
    return ids[0], ids[1]


def _run_to_night(kernel, agent, rounds: int = 12):
    for _ in range(rounds):
        kernel.tick({"P003": agent})


def test_disabled_default_no_sleep_events():
    with tempfile.TemporaryDirectory() as d:
        kernel, agent = _build(Path(d))
        _run_to_night(kernel, agent, rounds=12)
        types = [e["type"] for e in kernel.ledger]
        assert "SLEEP_STARTED" not in types          # 默认关 → 零副作用


def test_enabled_sleep_window_wires_events(monkeypatch):
    enabled = SW.load_params()
    enabled["sleep"]["enabled"] = True
    enabled["forgetting"]["enabled"] = True
    monkeypatch.setattr(SW, "load_params", lambda path=None: enabled)

    with tempfile.TemporaryDirectory() as d:
        kernel, agent = _build(Path(d))
        keep_id, old_id = _inject_old_memories(agent)
        # 直接驱动挂载点（night），避免自然检索刷新 last_access 掩盖"老化"
        wv = SimpleNamespace(time=SimpleNamespace(slot="night", day=0), round=11)
        n = agent._maybe_sleep_window(wv)
        kernel.commit_round()
        types = [e["type"] for e in kernel.ledger]
        assert n > 0
        assert "SLEEP_STARTED" in types and "SLEEP_COMPLETED" in types
        assert "MEMORY_FORGET" in types
        forgets = {e["payload"]["mem_id"]: e["payload"] for e in kernel.ledger
                   if e["type"] == "MEMORY_FORGET"}
        # 硬要求：保护记忆只 demote，未被 drop/merge
        assert forgets.get(keep_id, {}).get("level") == "demote"
        assert forgets.get(old_id, {}).get("level") in ("drop", "merge", "demote")
        # 事件可审计：payload 完整
        assert "retention_permille" in forgets[keep_id]
        # 同一天再调用不重复（幂等）
        assert agent._maybe_sleep_window(wv) == 0


def test_enabled_sleep_window_is_idempotent_per_day(monkeypatch):
    enabled = SW.load_params()
    enabled["sleep"]["enabled"] = True
    enabled["forgetting"]["enabled"] = True
    monkeypatch.setattr(SW, "load_params", lambda path=None: enabled)
    with tempfile.TemporaryDirectory() as d:
        kernel, agent = _build(Path(d))
        _run_to_night(kernel, agent, rounds=12)
        n = sum(1 for e in kernel.ledger if e["type"] == "SLEEP_STARTED")
        assert n == 1                                # 每模拟日只睡一次
