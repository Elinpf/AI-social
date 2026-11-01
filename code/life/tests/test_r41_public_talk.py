"""R41 公开面接话臂单测：开关语义 / OFF 逐字节等价 / ON 四条有界判据 / 配额与频道映射。

覆盖六条硬要求（对应 `round-impl-notes.md` §设计）：
  1. **开关**：只有 {1,true,yes,on} 算开；空串/`0`/`off`/拼错一律关；
  2. **OFF 等价**：`_thread_max_turn` / `_pick_reply_target` / `_thread_history` 三处
     白名单退回 `("MSG_DM","MSG_GROUP")` ⇒ 公开消息既挑不到、也进不了历史与轮数；
  3. **ON 的四条有界判据**：作者非我 / 在场者非空 / 同 place / 双配额，
     任何一条不成立都必须 `continue`（宁缺毋滥）；
  4. **配额常量**：每 agent 每 slot ≤1、同 place 同 slot ≤2（写死在 `life.public_talk`）；
  5. **频道映射**：回公开消息 ⇒ `global`（落 `MSG_PUBLIC`），不是 `place_group`；
  6. **place 注入**：`integration._r41_public_place` 在臂关闭时恒为 `None`
     （⇒ `MSG_PUBLIC.payload.place` 与接入前一致）。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import dialogue_threads as DT
from life import public_talk as PT
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.ports import EventView
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"


def _places() -> dict:
    return {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}


def _build(tmp: Path):
    places = _places()
    personas = load_personas(CONFIG / "personas.json")
    kernel = MiniKernel(seed=7, places=places)
    for pid in ("P003", "P007"):
        kernel._emit("AGENT_BORN", {"agent_id": pid, "home_place": personas[pid].home_place,
                                    "needs_init": personas[pid].needs_init}, phase=0, actor="SYSTEM")
    agent = LifeLayerAgent("P003", personas["P003"], kernel, side_store=SideStore(tmp / "side"),
                           embedding=HashEmbeddingModel(), places=places,
                           peer_names={"P007": "阿禾"})
    return kernel, agent


def _wv(events=(), *, location="market", slot="morning", day=1, rnd=12, slot_of_day="day3-morning"):
    return SimpleNamespace(round=rnd, visible_events=tuple(events), location=location,
                           current_activity=None, inventory=(), cash=100,
                           time=SimpleNamespace(slot=slot, day_of_week=3, day=day),
                           slot_id=slot_of_day)


def _pub(seq=10, *, author="P007", place="market", body="今儿集上人真多。",
         thread="TH-P007-PUB-1-0", turn=0, slot="morning", participants=None):
    return EventView(seq=seq, round=12, phase=4, actor=author, type="MSG_PUBLIC",
                     payload={"author": author, "body": body, "place": place,
                              "thread_id": thread, "turn_index": turn, "reply_to": None,
                              "participants": participants or [author], "topic": "闲聊",
                              "slot": slot, "msg_uid": f"42:{seq}", "msg_id": f"P-{seq}-0"})


def _arrived(seq, who="P007", *, place="market", slot="morning", day=1):
    return EventView(seq=seq, round=12, phase=3, actor=who, type="PLACE_ARRIVED",
                     payload={"agent_id": who, "place": place, "slot": slot, "day": day})


# ---------------------------------------------------------------- 1) 开关
def test_switch_default_off(monkeypatch):
    monkeypatch.delenv(PT.ENV, raising=False)
    assert PT.enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "on", "yes", " on "])
def test_switch_env_on(monkeypatch, val):
    monkeypatch.setenv(PT.ENV, val)
    assert PT.enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "2", "enable", "pub"])
def test_switch_env_off(monkeypatch, val):
    monkeypatch.setenv(PT.ENV, val)
    assert PT.enabled() is False


# ---------------------------------------------------------------- 4) 配额常量
def test_quota_constants_are_bounded():
    assert PT.MAX_PER_AGENT_PER_SLOT == 1
    assert PT.MAX_PER_PLACE_PER_SLOT == 2
    assert PT.MAX_PER_PLACE_PER_SLOT >= PT.MAX_PER_AGENT_PER_SLOT


def test_agent_quota_counts_by_slot():
    counter: dict = {}
    assert PT.agent_quota_ok(counter, "day3-morning") is True
    counter["day3-morning"] = 1
    assert PT.agent_quota_ok(counter, "day3-morning") is False
    assert PT.agent_quota_ok(counter, "day3-afternoon") is True


def test_place_quota_counts_visible_public_in_same_place():
    evs = [_pub(1), _pub(2, author="P005")]
    assert PT.public_count_at(evs, "market", "day3-morning") == 2
    assert PT.place_quota_ok(evs, "market", "day3-morning") is False
    assert PT.place_quota_ok(evs, "park", "day3-morning") is True
    assert PT.place_quota_ok([_pub(1)], "market", "day3-morning") is True


# ---------------------------------------------------------------- 5) 频道映射
@pytest.mark.parametrize("etype,scope", [("MSG_PUBLIC", "global"),
                                         ("MSG_DM", "private"),
                                         ("MSG_GROUP", "place_group")])
def test_reply_scope_mapping(etype, scope):
    assert PT.reply_scope(etype) == scope


# ---------------------------------------------------------------- 3) 四条有界判据
def test_is_replyable_public_requires_all_four_conditions():
    p = {"author": "P007", "place": "market"}
    # 全满足
    assert PT.is_replyable_public(p, "P003", "market", ["P007"]) is True
    # ① 作者是我自己
    assert PT.is_replyable_public(p, "P007", "market", ["P007"]) is False
    # ② 没有在场者（独处）
    assert PT.is_replyable_public(p, "P003", "market", []) is False
    # ③ 不同处
    assert PT.is_replyable_public(p, "P003", "park", ["P007"]) is False
    # ③' place 为 null（旧日志）⇒ 保守不接
    assert PT.is_replyable_public({"author": "P007", "place": None}, "P003", "market",
                                  ["P007"]) is False


# ---------------------------------------------------------------- 2) OFF 逐字节等价
def test_off_public_never_replyable_by_agent(monkeypatch, tmp_path):
    monkeypatch.delenv(PT.ENV, raising=False)
    _, agent = _build(tmp_path)
    wv = _wv([_arrived(1), _pub(2)])
    assert agent._pick_reply_target(wv, dict(DT.DEFAULTS)) is None
    assert agent._thread_history(wv, "TH-P007-PUB-1-0", dict(DT.DEFAULTS)) == []
    assert agent._thread_max_turn(wv, "TH-P007-PUB-1-0") == -1


def test_on_public_becomes_reply_target(monkeypatch, tmp_path):
    monkeypatch.delenv(PT.ENV, raising=False)
    _, agent = _build(tmp_path)
    wv = _wv([_arrived(1), _pub(2)])
    monkeypatch.setenv(PT.ENV, "1")
    target = agent._pick_reply_target(wv, dict(DT.DEFAULTS))
    assert target is not None and target.type == "MSG_PUBLIC"
    hist = agent._thread_history(wv, "TH-P007-PUB-1-0", dict(DT.DEFAULTS))
    assert len(hist) == 1
    assert agent._thread_max_turn(wv, "TH-P007-PUB-1-0") == 0


def test_on_but_alone_public_not_replyable(monkeypatch, tmp_path):
    """独处时（无 PLACE_ARRIVED 在场者）不接公开话 —— Leader 约束②。"""
    monkeypatch.setenv(PT.ENV, "1")
    _, agent = _build(tmp_path)
    wv = _wv([_pub(2)])          # 没有 PLACE_ARRIVED ⇒ co_present 为空
    assert agent._pick_reply_target(wv, dict(DT.DEFAULTS)) is None


def test_on_but_different_place_not_replyable(monkeypatch, tmp_path):
    monkeypatch.setenv(PT.ENV, "1")
    _, agent = _build(tmp_path)
    wv = _wv([_arrived(1, place="park"), _pub(2, place="park")])   # 我在 market
    assert agent._pick_reply_target(wv, dict(DT.DEFAULTS)) is None


def test_on_but_place_quota_exhausted(monkeypatch, tmp_path):
    """R44 口径变更后的断言（**有意改断言**，依据 `v2/refs/prereg-r44-public-reply-inbound.md` §2 D-2）：

    R41/R43 单桶时：同 place 同 slot 已有 2 条**开场白** ⇒ 接话也被挡（旧断言 `is None`）。
    R44 分桶后：2 条开场白只占满**开场白桶**，**接话桶**仍空 ⇒ 接话被允许；
               接话桶自己满（2 条）时才挡（见 `test_r44_reply_bucket_has_its_own_cap`）。
    """
    monkeypatch.setenv(PT.ENV, "1")
    _, agent = _build(tmp_path)
    wv = _wv([_arrived(1), _pub(2), _pub(3, author="P005", thread="TH-P005-PUB-1-1")])
    target = agent._pick_reply_target(wv, dict(DT.DEFAULTS))
    assert target is not None and target.type == "MSG_PUBLIC"


# ---------------------------------------------------------------- 6) place 注入
def test_integration_place_injection_off_is_none(monkeypatch):
    from orchestration import integration as IG
    monkeypatch.delenv(PT.ENV, raising=False)
    st = SimpleNamespace(agents={"P003": {"location": "market"}})
    assert IG._r41_public_place("P003", st) is None


def test_integration_place_injection_on_uses_agent_location(monkeypatch):
    from orchestration import integration as IG
    monkeypatch.setenv(PT.ENV, "1")
    st = SimpleNamespace(agents={"P003": {"location": "market"}})
    assert IG._r41_public_place("P003", st) == "market"
    # 未知 agent ⇒ None（不抛错，不崩批）
    assert IG._r41_public_place("P999", st) is None


# ---------------------------------------------------------------- 7) R44 配额分桶
def test_r44_kind_of_classifies_opener_and_reply():
    """`kind_of` 唯一分类：reply_to 非空 或 turn_index>0 ⇒ reply；其余 ⇒ opener。"""
    assert PT.kind_of({"reply_to": "42:189", "turn_index": 1}) == "reply"
    assert PT.kind_of({"reply_to": "42:189", "turn_index": 0}) == "reply"
    assert PT.kind_of({"reply_to": None, "turn_index": 3}) == "reply"
    assert PT.kind_of({"reply_to": None, "turn_index": 0}) == "opener"
    assert PT.kind_of({"reply_to": "", "turn_index": "0"}) == "opener"
    assert PT.kind_of({}) == "opener"
    assert PT.kind_of({"reply_to": None, "turn_index": "abc"}) == "opener"   # 非法值不抛错


def test_r44_bucket_caps_are_independent_constants():
    assert PT.MAX_PER_PLACE_PER_SLOT == 2           # 开场白上限：数值不变（R41V-C4 同阈值）
    assert PT.MAX_PLACE_REPLIES_PER_SLOT == 2       # 接话上限：独立桶
    assert PT.cap_for("opener") == 2
    assert PT.cap_for("reply") == 2
    assert PT.cap_for("不存在") == PT.MAX_PER_PLACE_PER_SLOT   # 非法 kind ⇒ 按更严的 opener
    assert PT.GATE_VERSION == "r44/1"


def test_r44_opener_bucket_full_does_not_block_reply_bucket():
    """**本轮核心机制**：同 place 同 slot 已有 2 条开场白 ⇒ 开场白桶满，但接话桶仍放行。"""
    evs = [_pub(1), _pub(2, author="P005", thread="TH-P005-PUB-1-1")]
    # 开场白桶已满
    assert PT.place_slot_count(evs, "market", 1, "morning", kind="opener") == 2
    assert PT.place_quota_gate(evs, "market", 1, "morning", kind="opener") == (False, 2)
    # 接话桶空 ⇒ 放行（R43 的单桶口径下这里是 False，接话会被丢掉）
    assert PT.place_slot_count(evs, "market", 1, "morning", kind="reply") == 0
    assert PT.place_quota_gate(evs, "market", 1, "morning", kind="reply") == (True, 0)
    # 兼容口径：kind=None ⇒ 总数（老语义不变）
    assert PT.place_slot_count(evs, "market", 1, "morning") == 2


def test_r44_reply_bucket_has_its_own_cap():
    """接话桶自己也会满（≤2），防「一个场所无限对答」。"""
    base = [_pub(1), _pub(2, author="P005", thread="TH-P005-PUB-1-1")]
    replies = [_pub(3 + i, author=f"P00{6 + i}", thread="TH-P007-PUB-1-0", turn=1)
               for i in range(2)]
    for r in replies:                       # 只有 reply 桶成员带 reply_to
        r.payload["reply_to"] = "42:1"
    evs = base + replies
    assert PT.place_slot_count(evs, "market", 1, "morning", kind="reply") == 2
    assert PT.place_quota_gate(evs, "market", 1, "morning", kind="reply") == (False, 2)


def test_r44_agent_prefilter_uses_reply_bucket(monkeypatch):
    """决策侧预过滤必须按接话桶判，否则分桶在写入口永远用不上（改动退化成空转）。"""
    monkeypatch.setenv(PT.ENV, "1")
    _, agent = _build(Path("/tmp/r44_agent_prefilter"))
    # 同处一条 PLACE_ARRIVED + 两条开场白（占满开场白桶）
    wv = _wv([_arrived(1), _pub(2), _pub(3, author="P005", thread="TH-P005-PUB-1-1")])
    target = agent._pick_reply_target(wv, dict(DT.DEFAULTS))
    assert target is not None, "开场白桶满不应再挡掉接话（R44 分桶的核心效果）"
    assert target.type == "MSG_PUBLIC"
