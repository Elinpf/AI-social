"""T-RIFT-EVENTS：RIFT_OPEN / RIFT_CLOSE 事件 + `dialogue_rift.rift_ids`（默认关）。

覆盖：
1. **默认关**：`ingest` 的 observer 不传 ⇒ 台账变化不产事件；`audit_fields` 不多 `rift_ids` 键；
2. **开关开**：observer 收到 `open`/`close` 且 `rift_id` 与 `dialogue_repair.rift_ids` 同格式；
3. **`enabled=0`**：开关无论怎么设都不产任何东西；
4. **rift_id 复用**：`DR.rift_id()` 生成值与真实批 `dialogue_repair.rift_ids` 的样例同格式
   （`R|<thread>|<msg_uid>`），不另造格式。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

import life.dialogue_repair as DR

_REAL_SLICE = (Path(__file__).resolve().parents[2]
               / "v2" / "evidence" / "d4-rates-slices" / "run_f4_on_n16r60_seed42.json")


def _p(**kw) -> dict:
    p = dict(DR.DEFAULTS)
    p["enabled"] = True
    p.update(kw)
    return p


# ---- 1. rift_id 复用现有函数（格式与真实样例一致）-------------------------
def test_rift_id_format_matches_real_samples():
    """新增事件用的 rift_id 必须与真实批 `dialogue_repair.rift_ids` 同形（R|<thread>|<msg_uid>）。"""
    got = DR.rift_id("dm:P001:P002:r5", "abc123")
    assert got == "R|dm:P001:P002:r5|abc123"
    assert re.fullmatch(r"R\|[^|]+\|[^|]+", got)
    # 真实样例（若切片存在则取真实值比对形状；切片缺失则跳过该断言，不伪造成立）
    if _REAL_SLICE.exists():
        data = json.loads(_REAL_SLICE.read_text(encoding="utf-8"))
        samples = [rid for row in data.get("rows", [])
                   for rid in (((row.get("dialogue_repair") or {}).get("rift_ids")) or [])]
        assert samples, "真实切片里应当有 rift_ids 样例"
        for rid in samples[:20]:
            assert re.fullmatch(r"R\|[^|]+\|[^|]+", rid), rid
        # 同格式：用真实样例拆出的 (thread, msg_uid) 回代，能重建原 id
        rid = samples[0]
        _, th, mid = rid.split("|", 2)
        assert DR.rift_id(th, mid) == rid


# ---- 2. 默认关：observer 不传 ⇒ 零事件；audit_fields 无 rift_ids ----------
def test_default_off_no_observer_without_switch():
    assert DR.load_params()["rift_events"] is False
    p = _p()                                   # enabled=True，但 rift_events 默认 False
    assert p["rift_events"] is False
    rifts, seen = {}, set()
    events = [type("E", (), {"type": "MSG_DM", "seq": 1, "round": 0,
                             "payload": {"from": "P009", "to": "P002",
                                         "body": "你什么意思，我很生气",
                                         "thread_id": "T1", "msg_uid": "m1"}})()]
    DR.ingest(rifts, seen, events, "P002", p, 0)          # 不传 observer
    assert len(rifts) == 1                                 # 台账照样登记
    # 默认关时 audit_fields 不带 rift_ids
    assert "rift_ids" not in DR.audit_fields(rifts, 0, "reply", peers=["P009"])


# ---- 3. 开关开：observer 收到 open / close --------------------------------
def test_observer_receives_open_and_close(monkeypatch):
    monkeypatch.setenv(DR.RIFT_EVENTS_ENV, "1")
    monkeypatch.setenv("HITT_DIALOGUE_REPAIR", "1")     # 总开关也要开（config 默认 false）
    DR._cache = None
    calls = []
    p = DR.load_params()
    assert p["rift_events"] is True and p["enabled"] is True
    rifts, seen = {}, set()

    def mk(seq, frm, body, mid):
        return type("E", (), {"type": "MSG_DM", "seq": seq, "round": 0,
                              "payload": {"from": frm, "to": "P002", "body": body,
                                          "thread_id": "T1", "msg_uid": mid}})()

    DR.ingest(rifts, seen, [mk(1, "P009", "你什么意思，我很生气", "m1")],
              "P002", p, 0, observer=lambda k, d: calls.append((k, d)))
    assert calls and calls[0][0] == "open"
    assert calls[0][1]["rift_id"] == DR.rift_id("T1", "m1")

    calls.clear()
    DR.ingest(rifts, seen, [mk(2, "P002", "对不起，我不是那个意思", "m2")],
              "P002", p, 0, observer=lambda k, d: calls.append((k, d)))
    assert calls and calls[0][0] == "close"
    assert calls[0][1]["reason"] == "repair"
    assert rifts == {}
    DR._cache = None


# ---- 4. enabled=0：开关怎么设都无效果 ------------------------------------
def test_disabled_makes_switch_inert(monkeypatch):
    monkeypatch.setenv(DR.RIFT_EVENTS_ENV, "1")
    DR._cache = None
    calls = []
    p = DR.load_params()
    p["enabled"] = False                       # 总开关关
    rifts, seen = {}, set()
    ev = type("E", (), {"type": "MSG_DM", "seq": 1, "round": 0,
                        "payload": {"from": "P009", "to": "P002", "body": "烦死了",
                                    "thread_id": "T1", "msg_uid": "m1"}})()
    DR.ingest(rifts, seen, [ev], "P002", p, 0, observer=lambda k, d: calls.append(k))
    assert calls == [] and rifts == {}
    assert DR.audit_fields({}, 0, "reply", peers=["P009"]) is None
    DR._cache = None


# ---- 5. 缺省 reason **不得** 默认成 repair（T-RIFT-EVENTS-FIX 必改一）------
def test_close_reason_default_is_unknown_not_repair():
    """调用点忘传 reason ⇒ 必须落 `unknown`。**绝不能是 `repair`**（那会把未知关闭算进和解）。"""
    import os
    os.environ.pop("HITT_LLM_PROVIDER", None)
    os.environ["HITT_DIALOGUE_REPAIR"] = "1"
    DR._cache = None
    from orchestration.integration import build_world
    w = build_world(seed=42, n=3)
    eng, ad = w["engine"], w["adapter"]
    eng.run_round(0)
    ad._do_rift("P002", {"op": "close", "rift_id": "R|T1|m1", "thread_id": "T1"})   # 不传 reason
    eng.state, _ = eng.arbiter.commit(eng.state)     # 直接调 adapter ⇒ 手动落账（run_round 会 discard）
    closes = [r for r in eng.ledger.records if r.get("type") == "RIFT_CLOSE"]
    assert closes, "应当产生一条 RIFT_CLOSE"
    assert closes[-1]["payload"]["reason"] == DR.RIFT_CLOSE_UNKNOWN
    assert closes[-1]["payload"]["reason"] != "repair"
    DR._cache = None


# ---- 6. reason 取值域封闭集：任何变体立即拒绝（必改三）--------------------
@pytest.mark.parametrize("bad", ["Repair", "REPAIR", "repaird", "pruned", "expired", "unknown2", ""])
def test_close_reason_rejects_variants(bad):
    import os
    os.environ.pop("HITT_LLM_PROVIDER", None)
    os.environ["HITT_DIALOGUE_REPAIR"] = "1"
    DR._cache = None
    from orchestration.integration import build_world
    w = build_world(seed=42, n=3)
    eng, ad = w["engine"], w["adapter"]
    eng.run_round(0)
    res = ad._do_rift("P002", {"op": "close", "rift_id": "R|T1|m1", "reason": bad})
    eng.state, _ = eng.arbiter.commit(eng.state)
    assert res.ok is False, f"非法 reason {bad!r} 必须被拒"
    rej = [r for r in eng.ledger.records
           if r.get("type") == "INTENT_REJECTED"
           and str(r["payload"].get("reason", "")).startswith("invalid_reason")]
    assert rej, f"应留 INTENT_REJECTED(invalid_reason)，实际 {bad!r}"
    DR._cache = None


def test_close_reason_domain_constants():
    assert DR.RIFT_CLOSE_REASONS == frozenset({"repair", "expire", "prune"})
    assert DR.RIFT_CLOSE_REASONS_ALLOWED == frozenset({"repair", "expire", "prune", "unknown"})


@pytest.mark.parametrize("good", ["repair", "expire", "prune", "unknown"])
def test_close_reason_accepts_closed_set(good):
    import os
    os.environ.pop("HITT_LLM_PROVIDER", None)
    os.environ["HITT_DIALOGUE_REPAIR"] = "1"
    DR._cache = None
    from orchestration.integration import build_world
    w = build_world(seed=42, n=3)
    eng, ad = w["engine"], w["adapter"]
    eng.run_round(0)
    assert ad._do_rift("P002", {"op": "close", "rift_id": "R|T1|m1", "reason": good}).ok is True
    DR._cache = None
