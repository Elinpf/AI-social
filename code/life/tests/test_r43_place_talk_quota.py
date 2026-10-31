"""R43 单测：公共场所说话配额（`MAX_PER_PLACE_PER_SLOT`）必须是**一道**真闸。

## 这一组测的是什么（对应 R41V-C4 判不成立）

`reports/R41b-public-talk-verify.md` §2.3 实测越界四种粒度：`round×day×slot×place`=3、
`day×slot×place`=5、`place×slot`(忽略 day)=9、只数接话=4。根因两条（代码可复算）：

  * **首发不走闸**：`orchestration/integration.py::_do_social()` 的 `scope=="global"` 分支
    原先只有 `public_per_agent_per_round` / `public_global_per_round`，没有场所配额；
  * **闸对着决策时点可见集判**：`life/agent.py::_pick_reply_target()` 用
    `wv.visible_events`，而同轮他人刚落的消息还在 arbiter 缓冲里
    （`engine/kernel.py::emit_specs` 只 emit 不 commit）⇒ 多个接话者各看到「1 < 2」，
    各自放行，聚合才越界。

R43 把判定收敛成**唯一函数** `life.public_talk.place_quota_gate()`、
**唯一强制点** `integration._do_social()`（写入口、串行、含本回合缓冲的 `state.event_index`）。

## 三条硬门的承接关系（谁承担哪条，写清以免"自证循环"）

| 用例 | 承接 | 说明 |
|---|---|---|
| `test_do_social_caps_third_public_message_at_same_place` | **(c) 代码摘除对照** | **只用 diff 之前就存在的入口**（`KernelAdapter._do_social` + `PT.ENV`），不 import 任何 R43 新符号 ⇒ 在基线树上应 `failed`（**断言级**），不是 `error` |
| `test_do_social_*`（阈值/跨 round/跨天/OFF） | (a) 阈值探针 | 同样走真实入口，靠行为断言（不是恒绿：改阈值/改语义就变色） |
| `test_rollback_probe_*` | **(b) 语义回滚探针** | 把生产闸 monkeypatch 回「决策时点可见集」旧语义 ⇒ 断言变红 |
| `test_real_violating_groups_are_capped_at_two` / `test_old_architecture_reproduces_the_violation` | 真实证据回归 | 从 `v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl` 摘出的四组越界（seq/作者/turn 照抄，**字面量内联，不读盘**） |

不依赖 LLM、不依赖网络、不依赖真实证据文件（内联字面量），fixture 全部自建。
"""
from __future__ import annotations

import os

import pytest

from life import public_talk as PT

IG = pytest.importorskip("orchestration.integration")

#: 真实越界组（seq / author / round / day / slot / place / turn / reply_to 全部照抄 ON 臂日志）。
#: 组内顺序 = seq 升序 = 落账顺序。
REAL_VIOLATIONS = {
    ("day0", "morning", "farm"): [          # round1：2 条接话 + 1 条首发 = 3 (>2)
        (487, "P001", 1, 0, "morning", "farm", 1, "42:189"),
        (613, "P003", 1, 0, "morning", "farm", 1, "42:189"),
        (1515, "P015", 1, 0, "morning", "farm", 0, None),
    ],
    ("day0", "morning", "school"): [        # round1：2 条接话 + 1 条首发 = 3 (>2)
        (760, "P006", 1, 0, "morning", "school", 1, "42:167"),
        (1270, "P012", 1, 0, "morning", "school", 1, "42:167"),
        (1332, "P013", 1, 0, "morning", "school", 0, None),
    ],
    ("day0", "afternoon", "bank"): [        # round3：3 条**首发**（首发原先完全不走闸）
        (2225, "P005", 3, 0, "afternoon", "bank", 0, None),
        (2250, "P008", 3, 0, "afternoon", "bank", 0, None),
        (2339, "P013", 3, 0, "afternoon", "bank", 0, None),
    ],
    ("day1", "morning", "school"): [        # round13：2 条接话 + 1 条首发 = 3 (>2)
        (20551, "P004", 13, 1, "morning", "school", 1, "42:19241"),
        (20626, "P005", 13, 1, "morning", "school", 0, None),
        (21419, "P016", 13, 1, "morning", "school", 1, "42:19241"),
    ],
}


# ---------------------------------------------------------------- 真实入口 harness
def _adapter(*, day=0, slot="morning", rnd=1, agents=("P001", "P002", "P003"),
             place="farm"):
    """**真实** `KernelAdapter` 实例（只补 `_do_social` 需要的几个属性，不改任何判定逻辑）。

    状态/账本/裁决器/事件折叠全部用引擎真件（`Ledger` / `Arbiter` / `initial_state` /
    `apply_event`），因此「本回合缓冲是否已进 `event_index`」这件事是**真行为**，
    不是测试替身假设出来的。
    """
    from engine.arbiter import Arbiter
    from engine.ledger import Ledger
    from engine.state import initial_state

    state = initial_state(42)
    state.round = int(rnd)
    state.agents = {a: {"location": place, "status": "alive"} for a in agents}
    ledger = Ledger(time_unit=1000, engine_version="v0.1-skeleton")
    arbiter = Arbiter(ledger)

    class _Eng:                                  # 只做 `_do_social` 用到的三个入口
        pass

    eng = _Eng()
    eng.state, eng.ledger, eng.arbiter = state, ledger, arbiter
    eng.emit_specs = lambda specs: arbiter.emit(state, specs)[1]
    eng.derive_time = lambda r, _d=day, _s=slot: {
        "week": 0, "day": _d, "day_of_week": _d % 7, "day_type": "work",
        "slot": _s, "tick_in_slot": 0}

    k = object.__new__(IG.KernelAdapter)
    k.engine, k._social = eng, {"caps": {}}
    return k


def _public(k, agent_id, body):
    """通过**既有入口** `_do_social` 提交一条公开消息意图。"""
    return k._do_social(agent_id, {"scope": "global", "body": body,
                                   "tag_hints": ["skill_practice"]})


def _emitted(k):
    return [v for _s, v in sorted(k.engine.state.event_index.items())]


# ---------------------------------------------------------------- (c) 承重点：真实入口行为
def test_do_social_caps_third_public_message_at_same_place(monkeypatch):
    """**(c) 代码摘除对照的承重点**：同 place×day×slot 的第 3 条公开消息必须被写入口拒掉。

    只用 diff 之前就存在的名字（`KernelAdapter._do_social` / `PT.ENV` / `PT.MAX_PER_PLACE_PER_SLOT`），
    **不 import 任何 R43 新符号** ⇒ 在基线代码树上本条以 `AssertionError` 失败（断言级红），
    不是 `ImportError`/`collection error`。
    """
    monkeypatch.setenv(PT.ENV, "1")
    k = _adapter()
    r1 = _public(k, "P001", "谷子晒了两天，正好。")
    r2 = _public(k, "P002", "这风吹得人想打盹。")
    r3 = _public(k, "P003", "谁家的鸡又跑出来了。")
    assert (r1.ok, r2.ok) == (True, True), "前 2 条必须放行（上限=2）"
    assert r3.ok is False, "同 place×day×slot 的第 3 条必须被写入口拒掉"
    assert r3.reason == "quota_place"
    dropped = [e for e in _emitted(k) if e["type"] == "DROPPED"]
    assert [d["payload"]["reason"] for d in dropped] == ["quota_place"]
    assert dropped[0]["payload"]["place"] == "farm"
    assert dropped[0]["payload"]["slot"] == "morning"
    assert dropped[0]["payload"]["n_place"] == 2
    pubs = [e for e in _emitted(k) if e["type"] == "MSG_PUBLIC"]
    assert len(pubs) == 2 and all(p["payload"]["place"] == "farm" for p in pubs)


def test_do_social_threshold_moves_with_constant(monkeypatch):
    """(a) 行为级阈值探针：把上限改成 1 ⇒ 第 2 条就撞闸（探针随阈值变色，不是恒绿）。"""
    monkeypatch.setenv(PT.ENV, "1")
    monkeypatch.setattr(PT, "MAX_PER_PLACE_PER_SLOT", 1)
    k = _adapter()
    assert _public(k, "P001", "先去井边打水。").ok is True
    r2 = _public(k, "P002", "井绳该换了。")
    assert r2.ok is False and r2.reason == "quota_place"


def test_do_social_accumulates_across_rounds_of_same_slot(monkeypatch):
    """`round` 不进键：同一 day×slot 前一 round 已开口的，仍要占用本轮额度。"""
    monkeypatch.setenv(PT.ENV, "1")
    k = _adapter(rnd=1)
    assert _public(k, "P001", "一。").ok is True
    assert _public(k, "P002", "二。").ok is True
    k.engine.state.round = 2                      # 下一 round，仍是 day0-morning
    r3 = _public(k, "P003", "三。")
    assert r3.ok is False and r3.reason == "quota_place"


def test_do_social_day_is_part_of_the_key(monkeypatch):
    """`day` 进键：换一天、同 place 同 slot 不占额（判据是「同一时段」= day+slot）。"""
    monkeypatch.setenv(PT.ENV, "1")
    k = _adapter(rnd=1, day=0)
    assert _public(k, "P001", "头一天。").ok is True
    assert _public(k, "P002", "还是头一天。").ok is True
    k.engine.derive_time = lambda r: {"week": 0, "day": 1, "day_of_week": 1,
                                      "day_type": "work", "slot": "morning",
                                      "tick_in_slot": 0}
    assert _public(k, "P003", "次日同处。").ok is True


def test_do_social_off_arm_never_blocks(monkeypatch):
    """OFF 等价性护栏：臂关闭 ⇒ 写入口不加任何场所限制（事件流与接入前一致）。"""
    monkeypatch.delenv(PT.ENV, raising=False)
    k = _adapter(agents=("P001", "P002", "P003", "P004"))
    for i, pid in enumerate(("P001", "P002", "P003", "P004")):
        assert _public(k, pid, f"第{i}句。").ok is True
    assert len([e for e in _emitted(k) if e["type"] == "MSG_PUBLIC"]) == 4


# ---------------------------------------------------------------- 闸函数单元（(a) 细粒度）
def _rec(seq, author, *, place="farm", day=0, slot="morning", rnd=1):
    return {"seq": seq, "round": rnd, "phase": 3, "actor": author, "type": "MSG_PUBLIC",
            "payload": {"author": author, "body": f"b{seq}", "place": place, "day": day,
                        "slot": slot, "msg_uid": f"42:{seq}"}}


def _st(records, *, rnd=1):
    from types import SimpleNamespace
    return SimpleNamespace(event_index={r["seq"]: r for r in records}, round=rnd)


def test_threshold_probe_2_allowed_3_blocked():
    """(a) 阈值探针（纯函数级，口径写死：入参 = **已存在**的条数）。

    上限 2 ⇒ 已存在 0/1 条时放行（可放下一条），已存在 2 条时拒（第 3 条不放）。
    即「2 条可用、第 3 条被拒」；把上限改成 3 时同一输入会变绿（见行为级探针与
    `test_threshold_probe_moves_with_constant`）。
    """
    assert PT.MAX_PER_PLACE_PER_SLOT == 2
    three = [_rec(1, "P001"), _rec(2, "P002"), _rec(3, "P003")]
    assert PT.place_quota_gate([], "farm", 0, "morning") == (True, 0)
    assert PT.place_quota_gate(three[:1], "farm", 0, "morning") == (True, 1)
    assert PT.place_quota_gate(three[:2], "farm", 0, "morning") == (False, 2)
    assert PT.place_quota_gate(three, "farm", 0, "morning") == (False, 3)


def test_threshold_probe_moves_with_constant(monkeypatch):
    """同一输入的判定随 `MAX_PER_PLACE_PER_SLOT` 变化（探针不是恒绿）。"""
    three = [_rec(1, "P001"), _rec(2, "P002"), _rec(3, "P003")]
    assert PT.place_quota_gate(three[:2], "farm", 0, "morning")[0] is False
    monkeypatch.setattr(PT, "MAX_PER_PLACE_PER_SLOT", 3)
    assert PT.place_quota_gate(three[:2], "farm", 0, "morning")[0] is True
    assert PT.place_quota_gate(three, "farm", 0, "morning")[0] is False


def test_gate_key_is_day_slot_place():
    two = [_rec(1, "P001"), _rec(2, "P002")]
    assert PT.place_quota_gate(two, "farm", 0, "morning")[0] is False
    assert PT.place_quota_gate(two, "farm", 1, "morning") == (True, 0)
    assert PT.place_quota_gate(two, "farm", 0, "afternoon") == (True, 0)
    assert PT.place_quota_gate(two, "school", 0, "morning") == (True, 0)
    assert PT.place_slot_count([_rec(1, "P001", place=None)], None, 0, "morning") == 0


# ---------------------------------------------------------------- 真实证据回归
def test_real_violating_groups_are_capped_at_two(monkeypatch):
    """四组真实越界用例串行过闸后每组 ≤2，且被丢的是最后到的那条。"""
    monkeypatch.setenv(PT.ENV, "1")
    for key, rows in REAL_VIOLATIONS.items():
        day = 0 if key[0] == "day0" else 1
        accepted, dropped = [], []
        for seq, author, rnd, _day, slot, place, turn, reply_to in rows:
            ok, _n = IG._r43_place_gate(_st(accepted, rnd=rnd), place, day, slot)
            rec = _rec(seq, author, place=place, day=day, slot=slot, rnd=rnd)
            rec["payload"]["turn_index"], rec["payload"]["reply_to"] = turn, reply_to
            (accepted if ok else dropped).append(rec)
        assert len(accepted) == 2, (key, [r["seq"] for r in accepted])
        assert len(dropped) == 1 and dropped[0]["seq"] == max(r[0] for r in rows), key


def test_old_architecture_reproduces_the_violation():
    """对照组（不是被测对象）：同一批输入在「决策时点各判一次」下 3 条全放行。

    数据源换成每个 agent 自己的可见集 —— 同轮他人刚落的消息**不在**里面
    （`engine/kernel.py::emit_specs` 只 emit 不 commit）⇒ 三个候选都看到「0 < 2」。
    """
    rows = REAL_VIOLATIONS[("day0", "afternoon", "bank")]     # 3 条纯首发
    accepted = []
    for _row in rows:
        ok, _n = PT.place_quota_gate([], "bank", 0, "afternoon")   # 可见集为空
        if ok:
            accepted.append(_row)
    assert len(accepted) == 3          # ⇒ 聚合结果 3 > 2 = R41V-C4 的「越界」


# ---------------------------------------------------------------- (b) 语义回滚探针
def _old_gate_decision_time_visible(st, place, day, slot):
    """R41 旧语义：数据源换回「决策时点可见集」（本回合未 commit 的消息不可见），
    且**不区分 day**（R41 版 `public_count_at` 只比 place 与 slot）。"""
    visible = [r for r in st.event_index.values() if int(r.get("round", 0)) < int(st.round)]
    return PT.place_quota_gate(visible, place, None, slot)


def test_rollback_probe_blocks_third_even_when_others_invisible(monkeypatch):
    """**(b) 语义回滚探针**。

    正常态：生产闸 `IG._r43_place_gate()` 读 `event_index`（含本回合已放行的 2 条）⇒ 第 3 条被拒。
    `R43_ROLLBACK=1`：把生产闸退回 `_old_gate_decision_time_visible`（旧语义）⇒
    同一断言拿到 `True` ⇒ **本测试变红**。断言写在外层生产函数上，语义被回滚它就红。
    """
    monkeypatch.setenv(PT.ENV, "1")
    if os.environ.get("R43_ROLLBACK") == "1":
        monkeypatch.setattr(IG, "_r43_place_gate", _old_gate_decision_time_visible)
    st = _st([_rec(487, "P001"), _rec(613, "P003")], rnd=1)   # 2 条都在本 round
    ok, n = IG._r43_place_gate(st, "farm", 0, "morning")
    assert ok is False, f"同 day×slot×place 第 3 条必须被拒（ok={ok}, n={n}）"
    assert n == 2
