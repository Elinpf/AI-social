"""T323: 人格漂移候选【发射 + restore 重建】—— **合成单元测试**（机制正确性）。

⚠️ **合成场景（必须贴标签）**：这里**手工注入**一个"含情感词的 reflection 节点"来驱动
`_reflection_drift_events`；因为**当前 mock 反思文本不含情感词** ⇒ 真实配置下候选恒空、
**e2e 触发仍待上游（mock 保真度）**。本测试**只**证明"发射 + 逐维 restore 重建"机制正确，
**结论限定在合成场景**。
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from life import persona_drift as PD
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, MemoryNode, SideStore
from life.persona import load_personas
from life.ports import IntentResult

CONFIG = Path(__file__).resolve().parents[2] / "config"


class StubKernel:
    """只捕获 intent（不需要真账本）；无 `round_events` ⇒ 走回退全扫。"""

    def __init__(self) -> None:
        self.intents = []

    def submit_intent(self, agent_id, intent):
        self.intents.append(intent)
        return IntentResult(ok=True, event_seqs=(0,))

    def current_round(self):
        return 0

    def derive_time(self, r):
        return {}


def _agent(tmp_path):
    personas = load_personas(CONFIG / "personas.json")
    pid = sorted(personas)[0]
    k = StubKernel()
    a = LifeLayerAgent(pid, personas[pid], k, side_store=SideStore(tmp_path / "s", persist_vec=False),
                       embedding=HashEmbeddingModel(), places={}, peers=[])
    return a, k, pid


def _inject_reflection(a, mid="M-%s-000000", text="我帮助了朋友，感到成长"):
    aid = a.agent_id
    n = MemoryNode(mem_id=mid % aid, agent_id=aid, kind="reflection", text=text,
                   importance=8, day=0, slot="night", embed=[])
    a.memory.nodes[n.mem_id] = n
    dim = PD.BIG5_DIMS[int(__import__("hashlib").sha256(n.mem_id.encode()).hexdigest()[:8], 16)
                       % len(PD.BIG5_DIMS)]
    return n.mem_id, dim


PARAMS = {"persona_drift": {"min_importance": 7, "min_windows": 2, "delta_max": 1}}


def test_emit_candidate_and_drift_over_two_windows(tmp_path):
    a, k, _aid = _agent(tmp_path)
    mid, dim = _inject_reflection(a)

    evs1 = a._reflection_drift_events(PARAMS, day=1, slot="night", window=1)
    assert evs1 == [] and a._drift_streak[dim] == 1          # 单窗=抖动，不发
    c1 = [i for i in k.intents if i.payload.get("op") == "drift_candidate"]
    assert len(c1) == 1 and c1[0].payload["dim"] == dim
    assert c1[0].payload["reached_threshold"] is False and c1[0].payload["window"] == 1

    evs2 = a._reflection_drift_events(PARAMS, day=2, slot="night", window=2)
    assert len(evs2) == 1 and evs2[0]["dim"] == dim          # 连续 2 窗 ⇒ 发 PERSONA_DRIFT
    assert a._drift_streak[dim] == 0                          # 发出后清零
    c2 = [i for i in k.intents if i.payload.get("op") == "drift_candidate"][-1]
    assert c2.payload["reached_threshold"] is True


def test_restore_rebuilds_drift_streak_per_dim(tmp_path):
    a, _k, aid = _agent(tmp_path)
    mid, dim = _inject_reflection(a)
    state = SimpleNamespace(agents={aid: {"memories": [], "observed_event_seqs": []}})

    def cand(w, reached):
        return {"type": "PERSONA_DRIFT_CANDIDATE", "round": w * 10,
                "payload": {"agent_id": aid, "dim": dim, "sign": 1, "window": w,
                            "mem_id": mid, "reached_threshold": reached, "day": w, "slot": "night"}}

    rec_w1 = [{"type": "SLEEP_STARTED", "round": 10, "payload": {"agent_id": aid, "day": 1, "slot": "night"}},
              cand(1, False)]
    # 截止窗1：live 应为 1 ⇒ restore 也必须 =1
    a.restore(state, rec_w1)
    assert a._drift_streak.get(dim) == 1

    # 到窗2（reached）：live 清零 ⇒ restore 也必须 =0
    a.restore(state, rec_w1 + [{"type": "SLEEP_STARTED", "round": 20,
                                "payload": {"agent_id": aid, "day": 2, "slot": "night"}}, cand(2, True)])
    assert a._drift_streak.get(dim) == 0


def test_keys_are_read_not_hardcoded(tmp_path):
    """`min_windows` 真被读：设 1 ⇒ 单窗即发（vs 默认 2 不发）。"""
    a, k, _aid = _agent(tmp_path)
    _inject_reflection(a)
    evs = a._reflection_drift_events({"persona_drift": {"min_windows": 1, "min_importance": 7}},
                                     day=1, slot="night", window=1)
    assert len(evs) == 1, "min_windows=1 should emit on the first window"
