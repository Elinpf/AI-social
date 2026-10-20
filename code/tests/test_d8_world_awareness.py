"""D8「世界事件 → 居民可见 → 对话提及」单测（纯函数 + 契约时间窗 + agent 接线 + 离线 mock）。

覆盖（对应用户/Leader 验收口径）：
  A. 纯函数：`life/world_awareness.py::brief_lines / prompt_context / scarcity_line`
     —— 有界、确定性、**只给情境不给结论**；关闭时返回空（提示词逐字不变）。
  B. 契约时间窗：`contracts/visibility.py::world_event_in_window` 与两条可见性路径
     （契约 `visible_events` / 索引 `VisibilityIndex.visible`）——**同一个 seq 在
     `issued+slots` 之后不再出现在任何 agent 的 visible_events**；开关关 = 旧行为。
  C. agent 接线：
     - ① 关（默认）= 世界事件**不**产生 MEMORY_WRITE/OBSERVATION，与基线等价；
     - ① 开 = 对世界事件 seq 精确产生 MEMORY_WRITE + OBSERVATION（`target_event_seq`）；
     - ② 关 = 提示词逐字不含世界行；② 开 = 含世界行且出现 MSG payload `world_ctx`。
  D. 离线 mock 端到端：开关关 ⇒ 日志里没有任何 `world_ctx` 键；开 ⇒ 可跑可重放。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from contracts.visibility import visible_events as contract_visible, world_event_in_window
from life import world_awareness as WA
from life.agent import LifeLayerAgent
from life.llm import LLMResult
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.ports import EventView

CODE_DIR = Path(__file__).resolve().parents[1]
CONFIG = CODE_DIR / "config"


# ---------------------------------------------------------------- helpers
def _params(**kw) -> dict:
    p = dict(WA.DEFAULTS)
    p.update({"enabled": True})
    p.update(kw)
    return p


def _world_ev(seq: int, rnd: int, kind: str = "tension", place: str | None = None,
              start: int | None = None, end: int | None = None,
              ref: str | None = None, typ: str = "WORLD_GROUP_EVENT") -> EventView:
    payload = {
        "group_event_id": f"GE-{rnd}-wd.{kind}",
        "directive_ref": ref or f"D-{rnd}-wd.{kind}",
        "kind": kind, "scope": {"level": "global", "place": place},
        "params": {"scarcity_bp": 2000, "slots": 6},
        "start_round": rnd if start is None else start,
        "end_round": (rnd + 6) if end is None else end,
        "directed": True, "place": place,
    }
    return EventView(seq=seq, round=rnd, phase=4, actor="DIRECTOR", type=typ, payload=payload)


class _StubKernel:
    def __init__(self) -> None:
        self.intents = []

    def submit_intent(self, agent_id, intent):
        self.intents.append((agent_id, intent))
        return SimpleNamespace(ok=True, reason=None, event_seqs=(len(self.intents),))


class _StubLLM:
    name = "stub"

    def __init__(self, text: str) -> None:
        self.text = text
        self.prompts: list = []

    def call(self, purpose, prompt, *, model=None, meta=None):
        self.prompts.append(prompt)
        return LLMResult(text=self.text)


def _agent(tmp: Path, llm_text: str = "（mock）听说镇上有点动静。"):
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    persona = load_personas(CONFIG / "personas.json")["P003"]
    kernel = _StubKernel()
    llm = _StubLLM(llm_text)
    agent = LifeLayerAgent("P003", persona, kernel, llm=llm,
                           side_store=SideStore(tmp / "side"),
                           embedding=HashEmbeddingModel(), places=places,
                           peer_names={"P002": "老周"})
    return agent, kernel, llm


def _wv(round_no: int, evs: list):
    return SimpleNamespace(round=round_no, visible_events=tuple(evs), llm_permit=True,
                           time=SimpleNamespace(day_of_week=0, slot="morning"),
                           day=0, slot="morning", location="residence")


# ---------------------------------------------------------------- A. 纯函数
def test_brief_lines_bounded_dedup_and_deterministic():
    p = _params()
    evs = [_world_ev(10, 30, "tension"), _world_ev(11, 31, "festival", place="hall"),
           _world_ev(12, 32, "tension")]     # 同 kind 的第二条不与第一条重复占位
    rows = WA.brief_lines(evs, 33, p)
    assert len(rows) <= p["max_lines"]
    assert all(r[1] in ({e.payload["kind"] for e in evs}) for r in rows)
    assert WA.brief_lines(evs, 33, p) == rows            # 确定性
    # 同 ref 去重取最近一条
    a = _world_ev(20, 30, "tension", ref="D-x")
    b = _world_ev(21, 31, "tension", ref="D-x")
    rows2 = WA.brief_lines([a, b], 31, p)
    assert len(rows2) == 1 and rows2[0][2] == 21


def test_brief_lines_empty_when_off_or_out_of_window():
    evs = [_world_ev(10, 30, "tension")]
    assert WA.brief_lines(evs, 31, dict(WA.DEFAULTS)) == []          # 总闸关
    assert WA.brief_lines(evs, 31, _params(dialogue_enabled=False)) == []   # ② 关
    far = 30 + int(WA.DEFAULTS["window_rounds"]) + 5
    assert WA.brief_lines(evs, far, _params()) == []                 # 超窗


def test_prompt_context_is_situation_only():
    """只给情境：不得出现金额/胜负/指令性措辞（R5/R6 同口径）。"""
    p = _params()
    ctx = WA.prompt_context([_world_ev(10, 30, "tension", place="market")], 31, params=p)
    assert ctx["text"].startswith("\n最近镇上的事：")
    assert ctx["refs"] == ["D-30-wd.tension"]
    for banned in ("你该", "必须", "建议", "mu", "价格", "赢", "输", "死亡"):
        assert banned not in ctx["text"]


def test_scarcity_line_consumes_market_scarcity_bp():
    wp = {"market_scarcity_bp": {"global": 2000}}
    assert WA.scarcity_line(wp, params=_params(scarcity_in_prompt=False)) == ""   # ③ 默认不做
    assert "贵" in WA.scarcity_line(wp, params=_params(scarcity_in_prompt=True))
    assert WA.scarcity_line({"market_scarcity_bp": {"global": 10}},
                            params=_params(scarcity_in_prompt=True)) == ""        # 低于阈值


def test_memory_text_is_human_no_internal_tokens():
    """世界事件写入记忆的正文必须是**人话**：不含内部 token / id（否则检索会漏机器文本）。"""
    banned = ("WORLD_", "DIRECTIVE", "GROUP_EVENT", "wd.", "_bp", "D-30", "GE-", "seq:")
    for typ in ("WORLD_DIRECTIVE", "WORLD_GROUP_EVENT"):
        for kind in ("tension", "festival", "edict", "scarcity", "supply_shock"):
            txt = WA.describe_event(typ, kind, "market")
            assert not any(b in txt for b in banned), (typ, kind, txt)
            assert "集市" in txt or "market" not in txt
            # 只给情境，不给结论
            for word in ("你该", "必须", "建议", "所以", "价格", "赢", "输"):
                assert word not in txt, (kind, word, txt)


def test_two_world_event_types_use_distinct_templates():
    """两种事件类型的记忆正文必须不同（否则 M-1 词表判据会集中撞同一个词）。"""
    a = WA.describe_event("WORLD_DIRECTIVE", "tension", "market")
    b = WA.describe_event("WORLD_GROUP_EVENT", "tension", "market")
    assert a != b
    assert "通告" in a and "通告" not in b
    assert "街坊" in b and "街坊" not in a


def test_describe_event_not_fallback_for_world_types(monkeypatch, tmp_path):
    """`_describe_event()` 对两个 WORLD 类型走**显式分支**，不是兜底 f-string。"""
    monkeypatch.setattr(WA, "load_params", lambda path=None: _params())
    agent, _kernel, _llm = _agent(tmp_path)
    for typ in ("WORLD_DIRECTIVE", "WORLD_GROUP_EVENT"):
        ev = _world_ev(9, 30, "tension", place="market", typ=typ)
        text = agent._describe_event(ev)
        fallback = f"{ev.actor} 的 {ev.type} 事件。"
        assert text != fallback
        assert text == WA.describe_event(typ, "tension", "market")
        assert "WORLD" not in text and "DIRECTOR" not in text


def test_prompts_byte_identical_to_baseline_when_off(monkeypatch, tmp_path):
    """开关全关 ⇒ 两个提示词与基线公式**逐字相等**（逐字 diff，不是结构对比）。"""
    monkeypatch.setattr(WA, "load_params", lambda path=None: dict(WA.DEFAULTS))
    agent, _kernel, _llm = _agent(tmp_path)
    agent._scan_world(_wv(31, [_world_ev(9, 30)]))
    cfg = agent._dlg_cfg()
    parts = ["P003", "P002"]
    # 基线公式（2090287 原样，逐字复写）：人格 + 场景/对象/情绪 + 收尾句
    others = agent._relation_line(parts[1:]) or "(独自)"
    expected_d = (agent.persona.compressed_profile(agent._current_goal())
                  + f"\n场景：ice_break；对象：{others}。{agent._mood_line()}。"
                  + "\n请用一句话自然地说点什么。")
    assert agent._dialogue_prompt("ice_break", parts, cfg,
                                  world_line=agent._world_prompt_line()) == expected_d
    history = [("P002", "老周：今天怎么样？")]
    lines = "\n".join(x[1] for x in history)
    expected_r = (agent.persona.compressed_profile(agent._current_goal())
                  + f"\n你正在和老周聊「闲聊」。{agent._mood_line()}。"
                  + f"\n刚才的对话：\n{lines}" + "\n请接着说一句。")
    assert agent._reply_prompt("P002", "闲聊", history, cfg,
                               world_line=agent._world_prompt_line()) == expected_r


# ---------------------------------------------------------------- B. 契约时间窗
def _rec(seq, rnd, typ="WORLD_GROUP_EVENT", start=None, end=None):
    ev = _world_ev(seq, rnd, start=start, end=end, typ=typ)
    return {"seq": seq, "round": rnd, "phase": 4, "actor": "DIRECTOR", "type": typ,
            "payload": dict(ev.payload)}


def test_world_event_in_window_predicate():
    rec = _rec(1, 30, start=30, end=36)
    assert world_event_in_window(rec, 30) is True
    assert world_event_in_window(rec, 35) is True
    assert world_event_in_window(rec, 36) is False       # 过期
    assert world_event_in_window(rec, 29) is False       # 未生效
    # DIRECTIVE 用 effective_from_round/expires_round
    d = {"seq": 2, "round": 30, "type": "WORLD_DIRECTIVE", "actor": "DIRECTOR",
         "payload": {"effective_from_round": 30, "expires_round": 33, "directed": True}}
    assert world_event_in_window(d, 32) is True
    assert world_event_in_window(d, 33) is False
    # 缺时间字段 ⇒ 视为在窗内（旧日志保守可读）
    assert world_event_in_window({"seq": 3, "round": 1, "type": "WORLD_GROUP_EVENT",
                                  "payload": {}}, 999) is True


def test_contract_visible_events_clips_expired_world_events():
    scope = json.loads((CONFIG / "perception_scope.json").read_text(encoding="utf-8"))
    recs = [_rec(1, 30, start=30, end=36), _rec(2, 35, "MSG_PUBLIC")]
    recs[1]["payload"] = {"body": "hi"}
    # 开关关（默认）= 基线：过期世界事件仍可见
    on_off = contract_visible(recs, "P003", 40, scope_table=scope["scope"],
                              default_cls=scope.get("default_visibility_class", "place_local"))
    assert any(r["type"] == "WORLD_GROUP_EVENT" for r in on_off)
    # 开关开：过期即不可见（同一个 seq 不再出现）
    on_on = contract_visible(recs, "P003", 40, scope_table=scope["scope"],
                             default_cls=scope.get("default_visibility_class", "place_local"),
                             world_event_window=True)
    assert not any(r["type"] == "WORLD_GROUP_EVENT" for r in on_on)
    assert any(r["type"] == "MSG_PUBLIC" for r in on_on)     # 非世界事件不受影响


def test_overlay_does_not_narrow_the_real_2round_window():
    """回归保护：真实路径 `window_rounds=2` 之上再叠 [start,end) 裁剪，可见回合仍是 30/31/32。

    真实跑批路径 = `visibility_index.visible(window_rounds=2)`（`integration.py:276`
    `VISIBLE_WINDOW_ROUNDS=2`）。tension 那条 `start=30, end=36`：
      - t=30/31/32：窗口内 ∩ 生效窗内 ⇒ 可见（与基线同）；
      - t=33 起：滑窗 `[t-2, t]` 已排除 30 ⇒ 不可见（与基线同，**不是**时间窗带来的）。
    """
    from orchestration.visibility_index import VisibilityIndex
    scope = json.loads((CONFIG / "perception_scope.json").read_text(encoding="utf-8"))
    idx = VisibilityIndex(scope["scope"], scope.get("default_visibility_class", "place_local"))
    idx.rebuild([_rec(1, 30, start=30, end=36)])
    seen_on, seen_off = [], []
    for t in (30, 31, 32, 33, 34, 35, 36, 40):
        seen_off.append(bool(idx.visible("P003", t, window_rounds=2)))
        seen_on.append(bool(idx.visible("P003", t, window_rounds=2, world_event_window=True)))
    assert seen_off == [True, True, True, False, False, False, False, False]
    assert seen_on == seen_off, (seen_on, seen_off)      # 叠加后窗口**不变**（3 回合）


def test_visibility_index_clips_expired_world_events():
    from orchestration.visibility_index import VisibilityIndex
    scope = json.loads((CONFIG / "perception_scope.json").read_text(encoding="utf-8"))
    idx = VisibilityIndex(scope["scope"], scope.get("default_visibility_class", "place_local"))
    recs = [_rec(1, 30, start=30, end=36)]
    idx.rebuild(recs)
    assert any(r["seq"] == 1 for r in idx.visible("P003", 35))
    assert not any(r["seq"] == 1 for r in idx.visible("P003", 36,
                                                    world_event_window=True))
    assert any(r["seq"] == 1 for r in idx.visible("P003", 36))    # 默认关 = 旧行为


# ---------------------------------------------------------------- C. agent 接线
def test_observe_off_writes_nothing_for_world_events(monkeypatch, tmp_path):
    """① 关（默认）：世界事件不产生世界事件专属记忆（= 基线语义等价）。"""
    monkeypatch.setattr(WA, "load_params", lambda path=None: dict(WA.DEFAULTS))
    agent, kernel, _llm = _agent(tmp_path)
    rep = SimpleNamespace(round=31, perceived=0, observed=0, accepted=[], rejected=[])
    agent._observe(_wv(31, [_world_ev(9, 30)]), rep)
    assert rep.observed == 0
    assert not [i for _a, i in kernel.intents if i.intent_class == "INTENT.OBSERVE"]


def test_observe_on_writes_memory_and_observation(monkeypatch, tmp_path):
    """① 开：世界事件 → MEMORY_WRITE + OBSERVATION（target_event_seq 精确指向该 seq）。"""
    monkeypatch.setattr(WA, "load_params", lambda path=None: _params(observe_enabled=True,
                                                                    dialogue_enabled=False))
    agent, kernel, _llm = _agent(tmp_path)
    rep = SimpleNamespace(round=31, perceived=0, observed=0, accepted=[], rejected=[])
    agent._observe(_wv(31, [_world_ev(9, 30)]), rep)
    assert rep.observed == 1
    kinds = [i.intent_class for _a, i in kernel.intents]
    assert "INTENT.MEMORY" in kinds and "INTENT.OBSERVE" in kinds
    obs = [i for _a, i in kernel.intents if i.intent_class == "INTENT.OBSERVE"][-1]
    assert obs.payload["target_event_seq"] == 9
    mem = [i for _a, i in kernel.intents if i.intent_class == "INTENT.MEMORY"][-1]
    assert mem.payload["importance"] >= int(WA.DEFAULTS["importance_min"])


def test_dialogue_prompt_untouched_when_off(monkeypatch, tmp_path):
    monkeypatch.setattr(WA, "load_params", lambda path=None: dict(WA.DEFAULTS))
    agent, _kernel, _llm = _agent(tmp_path)
    agent._scan_world(_wv(31, [_world_ev(9, 30)]))
    base = agent._dialogue_prompt("ice_break", ["P003", "P002"], agent._dlg_cfg())
    assert "最近镇上的事" not in base
    assert agent._world_prompt_line() == ""
    assert agent._world_ctx_payload() is None


def test_dialogue_prompt_has_world_line_and_payload(monkeypatch, tmp_path):
    monkeypatch.setattr(WA, "load_params", lambda path=None: _params())
    agent, kernel, llm = _agent(tmp_path)
    wv = _wv(31, [_world_ev(9, 30, "tension", place="market")])
    agent._scan_world(wv)
    prompt = agent._dialogue_prompt("ice_break", ["P003", "P002"], agent._dlg_cfg(),
                                    world_line=agent._world_prompt_line())
    assert "最近镇上的事" in prompt and "气氛" in prompt
    assert agent._wa_prompted == 1
    ctx = agent._world_ctx_payload()
    assert ctx["v"] == "d8/1" and ctx["refs"] == ["D-30-wd.tension"]
    # 回复路径同样带行
    ev = EventView(seq=12, round=31, phase=2, actor="P002", type="MSG_DM", payload={
        "msg_id": "D-31-1", "msg_uid": "7:12", "from": "P002", "to": "P003",
        "body": "今天怎么样？", "thread_id": "TH-P002-P003-31", "topic": "闲聊",
        "turn_index": 0, "day": 0, "slot": "morning", "tag_hints": ["闲聊"]})
    agent._scan_world(_wv(31, [ev, _world_ev(9, 30)]))
    assert agent._send_reply(wv, ev, agent._dlg_cfg(), "day0-morning") is True
    assert "最近镇上的事" in llm.prompts[-1]
    assert kernel.intents[-1][1].payload.get("world_ctx", {}).get("v") == "d8/1"


# ---------------------------------------------------------------- D. 端到端（离线 mock）
def _run_world(n: int = 6, rounds: int = 40, seed: int = 7):
    from engine.integration import build_world
    from engine.replay import replay_records
    from engine.state import state_hash
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    recs = list(eng.ledger.records)
    ok = state_hash(replay_records(recs)) == state_hash(eng.state)
    return recs, ok


def test_gate_off_no_world_ctx_offline_mock(monkeypatch):
    monkeypatch.setattr(WA, "load_params", lambda path=None: dict(WA.DEFAULTS))
    recs, replay_ok = _run_world()
    msgs = [r for r in recs if r["type"] in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")]
    assert not [m for m in msgs if "world_ctx" in (m["payload"] or {})]
    assert replay_ok is True


def test_gate_on_runs_and_replays_offline_mock(monkeypatch):
    monkeypatch.setattr(WA, "load_params", lambda path=None: _params())
    recs, replay_ok = _run_world()
    assert replay_ok is True
    for m in recs:
        if m["type"] not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            continue
        c = (m["payload"] or {}).get("world_ctx")
        if c is None:
            continue
        assert c["v"] == "d8/1" and isinstance(c["refs"], list)
        assert isinstance(c["scarcity"], bool) and isinstance(c["prompted"], bool)
