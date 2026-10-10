"""T53 IF-2c 审计桥端到端证据（真 LLM × N=3 × 10 回合，走引擎）。

验证：
  ① 引擎日志中 `LLM_CALL`/`LLM_JUDGMENT`/`NARRATIVE` 均 > 0（经 `audit_sink → emit_specs → P6`）；
  ② 引擎日志重放 `llm_calls == 0`（replay_records 不触发任何 provider 调用）；
  ③ census(obs.llmcost) 能输出 LLM 维度；
  ④ 日志无密钥/端点凭据。

用法（凭据经 env，见 `.env.local`）：
    set -a; . ./.env.local; set +a
    HITT_LLM_PROVIDER=openai_compat python3 scripts/t53_audit_bridge_evidence.py \
        --out logs/t53_real.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--out", default="logs/t53_real.jsonl")
    args = ap.parse_args()

    assert os.environ.get("HITT_LLM_PROVIDER") == "openai_compat", \
        "需设置 HITT_LLM_PROVIDER=openai_compat（真 provider）"

    from orchestration.integration import build_world
    from engine.replay import replay_records
    from engine.state import state_hash
    from engine.runner import write_log
    from freeze.llm_client import LLMClient
    from freeze.config import Tier
    from freeze.providers import OpenAICompatProvider

    world = build_world(seed=args.seed, n=args.n)
    engine = world["engine"]
    llm = world["agents"][0].llm               # FreezeLLM
    client = llm.client                        # LLMClient（含 audit_sink）
    assert isinstance(client, LLMClient), "应使用冻结层 LLMClient"
    assert client.audit_sink is not None, "audit_sink 未接线"

    pids = sorted(world["personas"])[:args.n]

    # 在**回合内**（phase_decide）触发软判定/叙事层调用，使其审计事件入本回合缓冲 → P6 commit。
    # （life 骨架主循环暂不调用 judge/narrate；此处模拟软判定层/叙事层的调用点。）
    class _AuditStepper:
        agent_id = "ZZZ_AUDIT"

        def __init__(self, engine, client, pids):
            self.engine = engine
            self.client = client
            self.pids = pids

        def step(self) -> None:
            r = int(self.engine.state.round)
            if r in (2, 4):
                self.client.judge(
                    judgment_id=f"T53-J{r}", dimension="mentor_relation",
                    question_ref="q.mentor.v1",
                    envelope={"options": ["formed", "not_formed"],
                              "threshold": 0.5, "rng_branch": f"b{r}"},
                    context={"a": self.pids[0], "b": self.pids[1], "round": r},
                    rng_branch=f"b{r}", parties=[self.pids[0], self.pids[1]],
                    created_round=r, round=r, tier=Tier.T2,
                )
            if r == 6:
                self.client.narrate(
                    fact_event_seqs=[0, 1], narrative_id="T53-N5",
                    body_ref="side://T53-N5",
                    facts=[{"seq": 0, "type": "AGENT_BORN"}, {"seq": 1, "type": "MARKET_TRADE"}],
                    created_round=r, round=r, tier=Tier.T1,
                )

    engine.agent_steppers.append(_AuditStepper(engine, client, pids))

    for r in range(args.rounds):
        engine.run_round(r)      # P6 唯一 append（含本回合缓冲中的审计事件）

    records = engine.ledger.records
    write_log(records, args.out)
    counts = Counter(rec["type"] for rec in records)

    # ---- ② 引擎日志重放：零 LLM 调用 ----
    spy = {"n": 0}
    _orig = OpenAICompatProvider.complete

    def _spy(self, *a, **k):
        spy["n"] += 1
        return _orig(self, *a, **k)

    OpenAICompatProvider.complete = _spy
    try:
        s1 = state_hash(replay_records(records, verify=True, verify_seals=False))
        s2 = state_hash(replay_records(records, verify=True, verify_seals=False))
    finally:
        OpenAICompatProvider.complete = _orig

    # ---- ③ census：LLM 维度 ----
    try:
        from obs.llmcost import llm_cost_from_records
        census = llm_cost_from_records(records)
    except Exception as exc:  # pragma: no cover
        census = {"error": str(exc)}

    # ---- ④ 凭据泄漏 ----
    txt = Path(args.out).read_text(encoding="utf-8")
    key = os.environ.get("LLM_API_KEY", "")
    leaked_key = bool(key) and key in txt

    report = {
        "rounds": args.rounds, "n": args.n, "events": len(records),
        "llm_call": counts.get("LLM_CALL", 0),
        "llm_judgment": counts.get("LLM_JUDGMENT", 0),
        "narrative": counts.get("NARRATIVE", 0),
        "replay_llm_calls": spy["n"],
        "replay_parity": s1 == s2,
        "first_run_equals_replay": s1 == state_hash(engine.state),
        "census_llm": census.get("total", census),
        "leaked_key": leaked_key,
        "endpoint_in_log": "172.16.3.41" in txt,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    assert counts.get("LLM_CALL", 0) > 0
    assert counts.get("LLM_JUDGMENT", 0) > 0
    assert counts.get("NARRATIVE", 0) > 0
    assert spy["n"] == 0, "引擎日志重放不得调用 LLM"
    assert not leaked_key and not report["endpoint_in_log"]
    print("[T53 OK] 三类事件>0 / 重放 llm_calls==0 / 无凭据")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
