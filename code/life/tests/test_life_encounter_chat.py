"""同场偶遇搭话臂（`LIFE_PROMPT_ENCOUNTER_CHAT`）的回归测试。

三条硬约束，各由一组断言钉住：
1. **OFF 默认**：开关不设/非法值 ⇒ 不启用；`_initiate_encounter` 立刻返回 False（零事件）。
2. **确定性**：门率/选人只由 `sha256(seed|agent|slot[|peer])` 决定 ⇒ 同输入同输出、
   与候选顺序无关、与墙钟/random 无关（`replay` 可复现）。
3. **边界**：`night` 不搭话；同一 `(agent, slot)` 至多一次；同场判据只认
   `PLACE_ARRIVED` 的 `place/day/slot`（不把 `ACTIVITY_STARTED.participants` 的「同活动」混进来）。

另有一条离线端到端（mini kernel + `RuleBasedLLM`，**零网络、零 LLM 费用**）：
ON 臂必须新增 DM，OFF 臂必须一条都不新增。这是 02-dimension.md 里 dry-run 的机器化形式。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import agent as A
from life.run_demo import build

CODE_DIR = Path(__file__).resolve().parents[2]
ENV_ON = A.ENCOUNTER_ENV
ENV_RATE = A.ENCOUNTER_RATE_ENV


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ON, raising=False)
    monkeypatch.delenv(ENV_RATE, raising=False)
    yield


# ---------------------------------------------------------------- 1. OFF 默认


def test_flag_defaults_off(monkeypatch):
    assert A.encounter_enabled() is False
    assert A.encounter_rate() == A.ENCOUNTER_RATE_DEFAULT
    for raw in ("0", "off", "false", "no", "", "  "):
        monkeypatch.setenv(ENV_ON, raw)
        assert A.encounter_enabled() is False
    for raw in ("1", "true", "YES", " on "):
        monkeypatch.setenv(ENV_ON, raw)
        assert A.encounter_enabled() is True


def test_rate_parsing_clamped_and_defaulted(monkeypatch):
    assert A.encounter_rate() == 50
    monkeypatch.setenv(ENV_RATE, "0")
    assert A.encounter_rate() == 0
    monkeypatch.setenv(ENV_RATE, "100")
    assert A.encounter_rate() == 100
    monkeypatch.setenv(ENV_RATE, "-5")
    assert A.encounter_rate() == 0
    monkeypatch.setenv(ENV_RATE, "250")
    assert A.encounter_rate() == 100
    monkeypatch.setenv(ENV_RATE, "abc")
    assert A.encounter_rate() == 50


def _fake_wv(location="plaza", day=0, slot="evening", events=(), rnd=4):
    evs = tuple(SimpleNamespace(type=t, payload=p, seq=i, round=rnd)
                for i, (t, p) in enumerate(events))
    return SimpleNamespace(agent_id="P001", round=rnd, location=location,
                           time=SimpleNamespace(day=day, slot=slot, day_type="workday"),
                           visible_events=evs, cash=0, inventory=())


def test_off_returns_false_and_emits_nothing(monkeypatch):
    """OFF 下即使同处者齐备、门率拉满，也必须一个事件都不发。"""
    monkeypatch.setenv(ENV_RATE, "100")
    calls = []

    class _K:
        def submit_intent(self, aid, intent):
            calls.append(intent)
            return SimpleNamespace(ok=True, reason="", event_seqs=())

        def submit_audit(self, *a, **k):
            return 0

    class _L:
        def call(self, purpose, prompt, **k):
            calls.append(("llm", purpose))
            return SimpleNamespace(text="（闲聊）嗯。")

    a = object.__new__(A.LifeLayerAgent)
    a.agent_id, a.kernel, a.llm = "P001", _K(), _L()
    a._slot_msgs, a._enc_slots, a._comm_slot, a._peer_names, a._rel_cache = {}, set(), None, {}, {}
    a._rifts, a._scene, a._weather, a._mem_refs = {}, None, None, []
    wv = _fake_wv(events=[("PLACE_ARRIVED", {"agent_id": "P002", "place": "plaza",
                                             "day": 0, "slot": "evening"})])
    assert a._initiate_encounter(wv, {"enabled": True}, "day0-evening") is False
    assert calls == []
    assert a._enc_slots == set()


# ---------------------------------------------------------------- 2. 确定性


def test_decision_is_deterministic_and_order_free(monkeypatch):
    monkeypatch.setenv(ENV_ON, "1")
    monkeypatch.setenv(ENV_RATE, "100")
    peer_sets = [["P002", "P003", "P004"], ["P004", "P002", "P003"], ["P003", "P004", "P002"]]
    out = {A.encounter_decision("P001", "day0-evening", ps) for ps in peer_sets}
    assert len(out) == 1, "候选顺序不得影响选人（否则等价于『谁先到谁被选中』）"
    picked = out.pop()
    assert picked in {"P002", "P003", "P004"}
    # 同输入重复调用恒定
    assert A.encounter_decision("P001", "day0-evening", peer_sets[0]) == picked


def test_decision_rate_bounds(monkeypatch):
    monkeypatch.setenv(ENV_ON, "1")
    monkeypatch.setenv(ENV_RATE, "0")
    assert A.encounter_decision("P001", "day0-evening", ["P002"]) is None
    monkeypatch.setenv(ENV_RATE, "100")
    assert A.encounter_decision("P001", "day0-evening", ["P002"]) == "P002"
    # 没有同处者 ⇒ 永远 None（连门都不掷）
    assert A.encounter_decision("P001", "day0-evening", []) is None
    assert A.encounter_decision("P001", "day0-evening", ["P001"]) is None


def test_decision_seed_sensitive(monkeypatch):
    monkeypatch.setenv(ENV_ON, "1")
    monkeypatch.setenv(ENV_RATE, "50")
    monkeypatch.setenv("HITT_WORLD_SEED", "0")
    seq0 = [A.encounter_decision(f"P{i:03d}", "day0-evening", ["P900", "P901"]) for i in range(40)]
    monkeypatch.setenv("HITT_WORLD_SEED", "7")
    seq7 = [A.encounter_decision(f"P{i:03d}", "day0-evening", ["P900", "P901"]) for i in range(40)]
    assert seq0 != seq7, "换 seed 必须换序列（否则等于写死一批结果）"
    assert any(x is None for x in seq0) and any(x for x in seq0), "50% 门率下两个分支都应出现"


# ---------------------------------------------------------------- 3. 边界


def test_copresent_filtering():
    a = object.__new__(A.LifeLayerAgent)
    a.agent_id = "P001"
    evs = [
        ("PLACE_ARRIVED", {"agent_id": "P002", "place": "plaza", "day": 0, "slot": "evening"}),
        ("PLACE_ARRIVED", {"agent_id": "P003", "place": "market", "day": 0, "slot": "evening"}),
        ("PLACE_ARRIVED", {"agent_id": "P004", "place": "plaza", "day": 1, "slot": "evening"}),
        ("PLACE_ARRIVED", {"agent_id": "P005", "place": "plaza", "day": 0, "slot": "morning"}),
        ("PLACE_ARRIVED", {"agent_id": "P001", "place": "plaza", "day": 0, "slot": "evening"}),
        ("ACTIVITY_STARTED", {"agent_id": "P006", "place": "plaza", "day": 0,
                              "slot": "evening", "participants": ["P006", "P001"]}),
    ]
    assert a._co_present_peers(_fake_wv(events=evs)) == ["P002"]


def test_night_slot_skipped(monkeypatch):
    monkeypatch.setenv(ENV_ON, "1")
    monkeypatch.setenv(ENV_RATE, "100")
    a = object.__new__(A.LifeLayerAgent)
    a.agent_id = "P001"
    wv = _fake_wv(slot="night", location="residence",
                  events=[("PLACE_ARRIVED", {"agent_id": "P002", "place": "residence",
                                             "day": 0, "slot": "night"})])
    assert a._co_present_peers(wv) == ["P002"]
    assert a._initiate_encounter(wv, {"enabled": True}, "day0-night") is False


def _real_agent():
    """取一个**真实装配**的 agent（真 persona / 真提示词装配），只把 kernel/llm 换成探针。

    比手搓 `object.__new__` 更稳：`_dialogue_prompt` 会用到 persona 压缩画像、关系行、
    L-7 结构行、收尾指令等一串东西，缺一个就 AttributeError（那证明不了本臂逻辑）。
    """
    with tempfile.TemporaryDirectory() as d:
        kernel, agents = build(7, Path(d))
    return agents["P001"]


def test_at_most_once_per_slot(monkeypatch):
    monkeypatch.setenv(ENV_ON, "1")
    monkeypatch.setenv(ENV_RATE, "100")
    sent = []

    class _K:
        def submit_intent(self, aid, intent):
            sent.append(intent)
            return SimpleNamespace(ok=True, reason="", event_seqs=())

        def submit_audit(self, *a, **k):
            return 0

    class _L:
        def call(self, purpose, prompt, **k):
            return SimpleNamespace(text="吃了没？")

    a = _real_agent()
    a.kernel, a.llm = _K(), _L()
    a._slot_msgs, a._enc_slots = {}, set()
    wv = _fake_wv(events=[("PLACE_ARRIVED", {"agent_id": "P002", "place": "plaza",
                                             "day": 0, "slot": "evening"})])
    assert a._initiate_encounter(wv, {"enabled": True}, "day0-evening") is True
    assert a._initiate_encounter(wv, {"enabled": True}, "day0-evening") is False
    assert len(sent) == 1
    payload = sent[0].payload
    assert payload["scope"] == "private" and payload["to"] == "P002"
    assert payload["ctx"]["trigger"] == "encounter"
    assert payload["ctx"]["initiator"] == "P001"
    assert payload["tag_hints"] == []              # 不污染 20 类模板普查
    assert payload["topic"] == A.ENCOUNTER_TOPIC   # 人话，不是内部 token（L-13）
    assert payload["thread_id"].startswith("TH-P001-P002-")
    assert a._slot_msgs["day0-evening"] == 1


# ------------------------------------------------- 4. 离线端到端（零网络/零费用）


def _run(rounds=28, seed=7):
    with tempfile.TemporaryDirectory() as d:
        kernel, agents = build(seed, Path(d))
        for _ in range(rounds):
            kernel.tick(agents)
        blob = json.dumps(kernel.ledger, sort_keys=True, ensure_ascii=False)
        dms = [e for e in kernel.ledger if e["type"] == "MSG_DM"]
        return blob, dms


def test_off_arm_adds_no_dm_and_is_replay_stable(monkeypatch):
    blob1, dms1 = _run()
    blob2, dms2 = _run()
    assert blob1 == blob2, "OFF 臂必须逐事件确定（同 seed 两次跑账本完全相同）"
    assert dms1 == [], f"OFF 臂不得新增任何 DM（实测 {len(dms1)} 条）"


def test_on_arm_emits_encounter_dm(monkeypatch):
    # 先跑 OFF（env 未设）再开 ON：`encounter_enabled()` 是**调用时读 env**，
    # 顺序颠倒会把「OFF 臂」也跑成 ON（本测试第一版就是这么错的，已修）。
    blob_off, dms_off = _run()
    monkeypatch.setenv(ENV_ON, "1")
    blob_on, dms_on = _run()
    assert dms_off == [], f"OFF 臂不得有 DM（实测 {len(dms_off)} 条）"
    assert dms_on, "ON 臂必须真的发出偶遇搭话（否则机制没接上）"
    assert all((e["payload"].get("body") or "").strip() for e in dms_on)
    assert blob_on != blob_off
    # 条数上界：每 (agent, slot) 至多 1 条 ⇒ ≤ 20 agents × slot 数
    assert len(dms_on) <= 20 * 28
