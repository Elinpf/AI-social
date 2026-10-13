"""T361 端到端自证：judge 的 `LLM_CALL` 经 `judgment_id` → `LLM_JUDGMENT.parties` → **真落到居民**。

⚠️ 口径（`§1.2 G-lg/G-lg-1`，Leader 13:39 冻结 `43b725b`）：
- judge **成本归属恒为 `null`**（`agent_id` 缺省）；**任何按居民聚合成本/调用数不得摊 judge**；
- `judgment_id` **只用于可见性/追溯**，**不得反推成本**（两条查询口径不得互相污染）。

本测试证明"**推过去了 ≠ 真被消费**"这条：给出**真链路** + **负例**（反查不到必须为红）。
"""
from __future__ import annotations

import tempfile

from orchestration.integration import build_world


def _world(seed: int = 7, n: int = 3, rounds: int = 12):
    w = build_world(seed=seed, n=n, side_root=tempfile.mkdtemp(prefix="t361e2e_"))
    e = w["engine"]
    for r in range(rounds):
        e.run_round(r)
    return e.ledger.records


def _judgment_parties(records) -> dict:
    out = {}
    for r in records:
        if r["type"] == "LLM_JUDGMENT":
            p = r["payload"]
            out[p["judgment_id"]] = list(p.get("parties") or [])
    return out


def trace_llm_calls_for_agent(records, resident: str):
    """「居民 `R` 的 AI 调用轨迹」（可见性口径，**不用于成本**）：

    = {LLM_CALL: agent_id==R} ∪ {LLM_CALL: judgment_id ∈ {LLM_JUDGMENT: R ∈ parties}}
    """
    jp = _judgment_parties(records)
    out = []
    for r in records:
        if r["type"] != "LLM_CALL":
            continue
        p = r["payload"]
        if p.get("agent_id") == resident:
            out.append(("direct", r))
        elif p.get("judgment_id") in jp and resident in jp[p["judgment_id"]]:
            out.append(("judge_link", r))
    return out


def test_judge_linkage_e2e_and_negative():
    recs = _world()
    jp = _judgment_parties(recs)

    # 找一条"带 judgment_id 的 judge LLM_CALL"
    judge_calls = [r for r in recs if r["type"] == "LLM_CALL"
                   and r["payload"].get("purpose") == "judge"]
    linked = [r for r in judge_calls if r["payload"].get("judgment_id") in jp]
    assert linked, "应存在带 judgment_id 的 judge LLM_CALL（端到端链路的前提）"
    call = linked[0]
    jid = call["payload"]["judgment_id"]
    parties = jp[jid]
    assert parties, "对应 LLM_JUDGMENT 应有 parties"

    # ---- 真链路：parties[0] 的轨迹**包含**这条 judge 调用 ----
    resident = parties[0]
    hits = trace_llm_calls_for_agent(recs, resident)
    judge_hits = [r for kind, r in hits if kind == "judge_link" and r["seq"] == call["seq"]]
    assert judge_hits, f"居民 {resident} 的轨迹应含这条 judge 调用（seq={call['seq']}, jid={jid}）"

    # ---- 成本口径：judge 的 LLM_CALL **不得**有 agent_id（不摊到居民）----
    assert call["payload"].get("agent_id") is None, "judge 成本归属必须缺省（不摊居民）"

    # ---- 负例：不在 parties 的居民**反查不到**这条 judge 调用（必须为红）----
    all_residents = sorted({r["payload"].get("agent_id") for r in recs
                            if r["type"] == "LLM_CALL" and r["payload"].get("agent_id")})
    outsider = next((x for x in all_residents if x not in parties), None)
    assert outsider is not None, "应存在一个不在 parties 的居民用于负例"
    neg = [r for kind, r in trace_llm_calls_for_agent(recs, outsider)
           if kind == "judge_link" and r["seq"] == call["seq"]]
    assert neg == [], f"负例失败（假绿）：非 party 居民 {outsider} 竟能反查到该 judge 调用"

    # 打印（供证据）
    print(f"[CHAIN] LLM_CALL seq={call['seq']} purpose=judge agent_id=None judgment_id={jid}")
    print(f"        -> LLM_JUDGMENT jid={jid} parties={parties}")
    print(f"        -> resident {resident} 轨迹命中 judge_link ✓（成本归属仍为 null）")
    print(f"[NEGATIVE] 非 party 居民 {outsider} 反查该 judge 调用 -> 无命中 ✓（防假绿）")


def test_unattributed_llm_call_is_not_attributed_to_anyone():
    """反向负例（T307-③）：**无 `agent_id` 且无 `judgment_id`** 的 `LLM_CALL` **不得**归属任何居民。

    若某消费方把"缺省"当成某居民（"假装是某人"）⇒ 本断言必红。
    """
    recs = [
        {"seq": 0, "type": "LLM_CALL", "payload": {"purpose": "plan"}},            # 无任何归属键
        {"seq": 1, "type": "LLM_JUDGMENT", "payload": {"judgment_id": "JX", "parties": ["P001"]}},
    ]
    for resident in ("P001", "P002", "P003"):
        assert trace_llm_calls_for_agent(recs, resident) == [], \
            f"无归属键的 LLM_CALL 被错误归属到 {resident}（假绿）"
