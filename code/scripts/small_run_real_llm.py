"""T43 第二步：N=3 × 10 回合小规模真跑（真实 provider）。

产出证据（**不含密钥/URL 凭据**）：
  - `LLM_CALL` 实例（model/tier/tokens_in/out/thinking/cached/degraded）；
  - `LLM_JUDGMENT` 四要素实例；
  - `NARRATIVE` 实例（若触发）；
  - 重放态 `llm_calls == 0`；
  - 实测 token / 耗时；与 rule-based（离线确定性）的行为差异抽样。

用法（端点/密钥经环境变量注入）：

    FREEZE_LLM_BASE_URL=... FREEZE_LLM_API_KEY=... FREEZE_LLM_MODEL=DeepSeek-Flash \
    python3 scripts/small_run_real_llm.py --cache-dir ./.run_cache --out ../v1.2/real-llm-evidence.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from freeze import EventLog, FreezeConfig, LLMBudget, LLMClient, Mode, Tier  # noqa: E402
from freeze.providers import MockProvider, provider_from_env  # noqa: E402

AGENTS = ["alice", "bob", "carol"]
ROUNDS = 10


def build_workload() -> List[Dict[str, Any]]:
    """确定性生成 3×10 回合的 LLM 工作项（run 与 replay 必须逐项一致）。"""
    items: List[Dict[str, Any]] = []
    for r in range(ROUNDS):
        for i, a in enumerate(AGENTS):
            other = AGENTS[(i + 1) % len(AGENTS)]
            if r % 3 == 0:
                items.append({
                    "kind": "plan", "round": r, "agent": a, "tier": Tier.T1,
                    "system": "你是青溪镇居民，用一到两句话给出今日安排。",
                    "user": f"[第{r}天] {a} 的今日计划：请简要说明上午做什么。",
                })
            else:
                items.append({
                    "kind": "dialogue", "round": r, "agent": a, "tier": Tier.T1,
                    "system": "你是青溪镇居民，用一句话进行日常寒暄。",
                    "user": f"[第{r}天] {a} 对 {other} 说一句话（家常寒暄）。",
                })
        # 社交事件软判定（世界侧高质量判断）
        if r in (3, 7):
            items.append({
                "kind": "judge", "round": r, "agents": [AGENTS[0], AGENTS[1]],
                "dimension": "mentor_relation",
                "question_ref": "q.mentor.v1",
                "envelope": {"options": ["formed", "not_formed"],
                             "threshold": 0.5, "rng_branch": f"branch#{r}"},
                "context": {"a": AGENTS[0], "b": AGENTS[1],
                            "shared_activity": "craft_workshop", "round": r},
                "rng_branch": f"branch#{r}",
            })
    # 叙事层（把已定事实叙述成情节）
    items.append({
        "kind": "narrate", "round": 9,
        "fact_event_seqs": [0, 1, 2],
        "facts": [{"seq": 0, "type": "AGENT_BORN", "actor": "alice"},
                  {"seq": 1, "type": "MARKET_TRADE", "actor": "bob"},
                  {"seq": 2, "type": "RELATION_CHANGE", "actor": "carol"}],
    })
    return items


def execute(client: LLMClient, items: List[Dict[str, Any]], collect_text: bool):
    times: List[float] = []
    texts: List[Dict[str, Any]] = []
    for it in items:
        t0 = time.perf_counter()
        if it["kind"] == "judge":
            fj = client.judge(
                judgment_id=f"J-r{it['round']}",
                dimension=it["dimension"], question_ref=it["question_ref"],
                envelope=it["envelope"], context=it["context"],
                rng_branch=it["rng_branch"], parties=it["agents"],
                created_round=it["round"], round=it["round"], tier=Tier.T2,
            )
            if collect_text:
                texts.append({"kind": "judge", "round": it["round"], "decision": fj.decision})
        elif it["kind"] == "narrate":
            txt = client.narrate(
                fact_event_seqs=it["fact_event_seqs"], narrative_id=f"N-r{it['round']}",
                body_ref=f"side://N-r{it['round']}", facts=it["facts"],
                created_round=it["round"], round=it["round"], tier=Tier.T1,
            )
            if collect_text:
                texts.append({"kind": "narrate", "round": it["round"], "text": txt[:200]})
        else:
            resp = client.complete(
                purpose=it["kind"], system=it["system"], user=it["user"],
                tier=it["tier"], round=it["round"], meta={"agent_id": it["agent"]},
            )
            if collect_text:
                texts.append({"kind": it["kind"], "round": it["round"],
                              "agent": it["agent"], "text": resp.text[:200]})
        times.append(time.perf_counter() - t0)
    return times, texts


def summarize_calls(log: EventLog) -> Dict[str, Any]:
    calls = log.of_type("LLM_CALL")
    tin = sum(e["payload"]["tokens_in"] for e in calls)
    tout = sum(e["payload"]["tokens_out"] for e in calls)
    by_purpose: Dict[str, Dict[str, int]] = {}
    for e in calls:
        p = e["payload"]["purpose"]
        d = by_purpose.setdefault(p, {"n": 0, "tin": 0, "tout": 0})
        d["n"] += 1
        d["tin"] += e["payload"]["tokens_in"]
        d["tout"] += e["payload"]["tokens_out"]
    return {"n_calls": len(calls), "tokens_in": tin, "tokens_out": tout,
            "by_purpose": by_purpose}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="./.run_cache")
    ap.add_argument("--out", default="../v1.2/real-llm-evidence.json")
    ap.add_argument("--engine-version", default="v1.1-rim-run")
    args = ap.parse_args()

    base_ev = args.engine_version
    # 把 thinking 策略指纹折进 engine_version（复现口径）
    cfg_probe = FreezeConfig(engine_version=base_ev)
    ev = cfg_probe.engine_version_with_policy()

    items = build_workload()
    provider = provider_from_env(prefer="openai")
    run_cfg = FreezeConfig(engine_version=ev, mode=Mode.RUN, cache_dir=args.cache_dir)
    run_log = EventLog()
    run_client = LLMClient(run_cfg, provider=provider, event_log=run_log,
                           budget=LLMBudget(limit=None))
    t0 = time.perf_counter()
    run_times, run_texts = execute(run_client, items, collect_text=True)
    wall = time.perf_counter() - t0

    run_calls = summarize_calls(run_log)
    judgments = [{"decision": e["payload"]["decision"], "model": e["payload"]["model"],
                  "context_digest": e["payload"]["context_digest"],
                  "frozen": e["payload"]["frozen"]} for e in run_log.of_type("LLM_JUDGMENT")]
    narratives = [{"narrative_id": e["payload"]["narrative_id"],
                   "affects_state": e["payload"]["affects_state"]}
                  for e in run_log.of_type("NARRATIVE")]

    # ---- 重放：同 cache_dir + engine_version，绝不重调 LLM ----
    replay_provider = provider_from_env(prefer="openai")
    replay = LLMClient(
        FreezeConfig(engine_version=ev, mode=Mode.REPLAY, cache_dir=args.cache_dir),
        provider=replay_provider, event_log=EventLog())
    _replay_times, _ = execute(replay, items, collect_text=False)

    # ---- 对照：rule-based（离线确定性模板，镜像 life.llm.RuleBasedLLM） ----
    def _rule_responder(system: str, user: str, extra: Dict[str, Any]) -> str:
        purpose = (extra or {}).get("purpose")
        if purpose == "judge":
            return "formed"
        if purpose == "plan":
            return "（计划）按作息工作、休息，留出社交与休闲时间。"
        if purpose == "dialogue":
            return "（寒暄）今天天气不错，一切都好。"
        if purpose == "describe":
            return "（叙述）小镇平静地度过了一天。"
        return "（内容）略。"

    mock_cfg = FreezeConfig(engine_version=ev + "-rulebased", mode=Mode.RUN,
                            cache_dir=args.cache_dir + "-rule")
    mock_log = EventLog()
    mock_client = LLMClient(mock_cfg, provider=MockProvider(responder=_rule_responder),
                            event_log=mock_log, budget=LLMBudget(limit=None))
    t0 = time.perf_counter()
    mock_times, mock_texts = execute(mock_client, items, collect_text=True)
    mock_wall = time.perf_counter() - t0

    evidence = {
        "engine_version": ev,
        "model": getattr(provider, "model", "?"),
        "endpoint": getattr(provider, "base_url", "?"),  # 端点（非凭据）
        "thinking_policy": cfg_probe.thinking_policy.fingerprint(),
        "workload": {"agents": AGENTS, "rounds": ROUNDS, "n_items": len(items)},
        "real_run": {
            "provider_calls": getattr(provider, "calls", None),
            "http_attempts": getattr(provider, "http_attempts", None),
            "llm_calls_counter": run_client.llm_calls,
            **run_calls,
            "wall_seconds": round(wall, 3),
            "mean_call_seconds": round(sum(run_times) / len(run_times), 3),
            "max_call_seconds": round(max(run_times), 3),
        },
        "real_judgments": judgments,
        "real_narratives": narratives,
        "replay": {
            "llm_calls": replay.llm_calls,
            "provider_calls": getattr(replay_provider, "calls", None),
        },
        "rulebased_run": {
            "llm_calls_counter": mock_client.llm_calls,
            **summarize_calls(mock_log),
            "wall_seconds": round(mock_wall, 3),
            "mean_call_seconds": round(sum(mock_times) / len(mock_times), 6),
        },
        "behavior_samples_real": run_texts[:6],
        "behavior_samples_rulebased": mock_texts[:6],
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, ensure_ascii=False, indent=2)

    # 打印关键结论
    print(f"[real] calls={run_calls['n_calls']} tokens_in={run_calls['tokens_in']} "
          f"tokens_out={run_calls['tokens_out']} wall={wall:.2f}s "
          f"mean={sum(run_times)/len(run_times):.2f}s")
    print(f"[replay] llm_calls={replay.llm_calls} provider_calls={getattr(replay_provider,'calls',None)}")
    print(f"[rulebased] calls={mock_client.llm_calls} wall={mock_wall:.4f}s")
    print(f"[evidence] {args.out}")
    assert replay.llm_calls == 0, "重放必须 llm_calls==0"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
