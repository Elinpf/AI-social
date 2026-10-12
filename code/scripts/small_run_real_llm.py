"""T43 第二步：N=3 × 10 回合小规模真跑（真实 provider）。

三类跑（**各自独立进程**，仪表纪律：同配置多跑对比必须分进程）：
  - `real`：真实 provider（首跑，落盘缓存 + `LLM_CALL`/`LLM_JUDGMENT`/`NARRATIVE`）；
  - `replay`：同 cache_dir + engine_version，读缓存、**零 LLM 调用**（复用 real 的缓存）；
  - `rulebased`：离线确定性模板（对照），独立 cache。

> 本脚本 driver 用 `subprocess` 分别拉起 `--one real|replay|rulebased`，**不在同一进程里连跑三跑**
> （旧版曾同进程连跑 ⇒ 命中「同进程连续跑 ⇒ 假分叉」规矩）。装置前提写入证据。

产出证据（**不含密钥/URL 凭据**）。用法：
    FREEZE_LLM_BASE_URL=... FREEZE_LLM_API_KEY=... FREEZE_LLM_MODEL=DeepSeek-Flash \
    python3 scripts/small_run_real_llm.py --cache-dir ./.run_cache --out ../v1.2/real-llm-evidence.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from freeze import EventLog, FreezeConfig, LLMBudget, LLMClient, Mode, Tier  # noqa: E402
from freeze.providers import MockProvider, provider_from_env  # noqa: E402

AGENTS = ["alice", "bob", "carol"]
ROUNDS = 10


def build_workload() -> List[Dict[str, Any]]:
    """确定性生成 3×10 回合的 LLM 工作项（real 与 replay 必须逐项一致）。"""
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
        if r in (3, 7):
            items.append({
                "kind": "judge", "round": r, "agents": [AGENTS[0], AGENTS[1]],
                "dimension": "mentor_relation", "question_ref": "q.mentor.v1",
                "envelope": {"options": ["formed", "not_formed"],
                             "threshold": 0.5, "rng_branch": f"branch#{r}"},
                "context": {"a": AGENTS[0], "b": AGENTS[1],
                            "shared_activity": "craft_workshop", "round": r},
                "rng_branch": f"branch#{r}",
            })
    items.append({
        "kind": "narrate", "round": 9, "fact_event_seqs": [0, 1, 2],
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
                judgment_id=f"J-r{it['round']}", dimension=it["dimension"],
                question_ref=it["question_ref"], envelope=it["envelope"], context=it["context"],
                rng_branch=it["rng_branch"], parties=it["agents"],
                created_round=it["round"], round=it["round"], tier=Tier.T2)
            if collect_text:
                texts.append({"kind": "judge", "round": it["round"], "decision": fj.decision})
        elif it["kind"] == "narrate":
            txt = client.narrate(
                fact_event_seqs=it["fact_event_seqs"], narrative_id=f"N-r{it['round']}",
                body_ref=f"side://N-r{it['round']}", facts=it["facts"],
                created_round=it["round"], round=it["round"], tier=Tier.T1)
            if collect_text:
                texts.append({"kind": "narrate", "round": it["round"], "text": txt[:200]})
        else:
            resp = client.complete(
                purpose=it["kind"], system=it["system"], user=it["user"],
                tier=it["tier"], round=it["round"], meta={"agent_id": it["agent"]})
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
    return {"n_calls": len(calls), "tokens_in": tin, "tokens_out": tout, "by_purpose": by_purpose}


def _ev(base: str) -> str:
    return FreezeConfig(engine_version=base).engine_version_with_policy()


def _rule_responder(system: str, user: str, extra: Dict[str, Any]) -> str:
    purpose = (extra or {}).get("purpose")
    return {"judge": "formed",
            "plan": "（计划）按作息工作、休息，留出社交与休闲时间。",
            "dialogue": "（寒暄）今天天气不错，一切都好。",
            "describe": "（叙述）小镇平静地度过了一天。"}.get(purpose, "（内容）略。")


def _run_one(which: str, cache_dir: str, base_ev: str, out_dump: str) -> None:
    ev = _ev(base_ev)
    items = build_workload()
    dump: Dict[str, Any] = {"which": which, "engine_version": ev}

    if which == "real":
        provider = provider_from_env(prefer="openai")
        log = EventLog()
        client = LLMClient(FreezeConfig(engine_version=ev, mode=Mode.RUN, cache_dir=cache_dir),
                           provider=provider, event_log=log, budget=LLMBudget(limit=None))
        t0 = time.perf_counter()
        times, texts = execute(client, items, collect_text=True)
        wall = time.perf_counter() - t0
        dump.update({
            "provider_calls": getattr(provider, "calls", None),
            "http_attempts": getattr(provider, "http_attempts", None),
            "llm_calls_counter": client.llm_calls, **summarize_calls(log),
            "wall_seconds": round(wall, 3),
            "mean_call_seconds": round(sum(times) / len(times), 3),
            "max_call_seconds": round(max(times), 3),
            "model": getattr(provider, "model", "?"),
            "endpoint": getattr(provider, "base_url", "?"),
            "judgments": [{"decision": e["payload"]["decision"], "model": e["payload"]["model"],
                           "context_digest": e["payload"]["context_digest"],
                           "frozen": e["payload"]["frozen"]} for e in log.of_type("LLM_JUDGMENT")],
            "narratives": [{"narrative_id": e["payload"]["narrative_id"],
                            "affects_state": e["payload"]["affects_state"]}
                           for e in log.of_type("NARRATIVE")],
            "samples": texts[:6],
        })
    elif which == "replay":
        provider = provider_from_env(prefer="openai")
        log = EventLog()
        client = LLMClient(FreezeConfig(engine_version=ev, mode=Mode.REPLAY, cache_dir=cache_dir),
                           provider=provider, event_log=log)
        execute(client, items, collect_text=False)
        calls = log.of_type("LLM_CALL")
        dump.update({"llm_calls": client.llm_calls, "provider_calls": getattr(provider, "calls", None),
                     "n_llm_call_events": len(calls),
                     "n_cached": sum(1 for e in calls if e["payload"].get("cached"))})
    else:  # rulebased
        log = EventLog()
        client = LLMClient(FreezeConfig(engine_version=ev + "-rulebased", mode=Mode.RUN,
                                        cache_dir=cache_dir + "-rule"),
                           provider=MockProvider(responder=_rule_responder), event_log=log,
                           budget=LLMBudget(limit=None))
        t0 = time.perf_counter()
        times, texts = execute(client, items, collect_text=True)
        wall = time.perf_counter() - t0
        dump.update({"llm_calls_counter": client.llm_calls, **summarize_calls(log),
                     "wall_seconds": round(wall, 3),
                     "mean_call_seconds": round(sum(times) / len(times), 6),
                     "samples": texts[:6]})

    Path(out_dump).write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")


def _spawn(which: str, cache_dir: str, base_ev: str, dump: str) -> None:
    """独立子进程跑一类（仪表纪律：分进程）。"""
    subprocess.run([sys.executable, os.path.abspath(__file__),
                    "--one", which, "--cache-dir", cache_dir, "--engine-version", base_ev,
                    "--dump", dump], check=True, env=dict(os.environ))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=None)
    ap.add_argument("--out", default="../v1.2/real-llm-evidence.json")
    ap.add_argument("--engine-version", default="v1.1-rim-run")
    ap.add_argument("--one", choices=["real", "replay", "rulebased"], default=None,
                    help="内部：只跑一类并 dump（由 driver 以子进程调用）")
    ap.add_argument("--dump", default=None)
    args = ap.parse_args()

    if args.one:
        _run_one(args.one, args.cache_dir, args.engine_version, args.dump)
        return 0

    base_ev = args.engine_version
    ev = _ev(base_ev)
    tmp_root = None
    if args.cache_dir:
        cache_dir = args.cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    else:
        tmp_root = tempfile.mkdtemp(prefix="t043_small_")
        cache_dir = os.path.join(tmp_root, "run_cache")

    dumps = tempfile.mkdtemp(prefix="t043_dumps_")
    try:
        # real → replay（共享 real 的 cache）→ rulebased；各自独立进程，顺序执行
        for which in ("real", "replay", "rulebased"):
            _spawn(which, cache_dir, base_ev, os.path.join(dumps, f"{which}.json"))
        real = json.loads(Path(dumps, "real.json").read_text(encoding="utf-8"))
        replay = json.loads(Path(dumps, "replay.json").read_text(encoding="utf-8"))
        rule = json.loads(Path(dumps, "rulebased.json").read_text(encoding="utf-8"))

        evidence = {
            "engine_version": ev,
            "model": real.get("model"),
            "endpoint": real.get("endpoint"),
            "thinking_policy": FreezeConfig(engine_version=base_ev).thinking_policy.fingerprint(),
            "workload": {"agents": AGENTS, "rounds": ROUNDS, "n_items": len(build_workload())},
            "instrument": {
                "multi_run_isolation": "separate_process",
                "note": "real / replay / rulebased 各在独立子进程运行（团队 harness 规矩：多跑对比必须分进程）；"
                        "replay 复用 real 的 cache_dir（同 engine_version）",
            },
            "real_run": {k: v for k, v in real.items()
                         if k not in ("which", "judgments", "narratives", "samples")},
            "real_judgments": real.get("judgments", []),
            "real_narratives": real.get("narratives", []),
            "replay": replay,
            "rulebased_run": {k: v for k, v in rule.items() if k not in ("which", "samples")},
            "behavior_samples_real": real.get("samples", []),
            "behavior_samples_rulebased": rule.get("samples", []),
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(evidence, fh, ensure_ascii=False, indent=2)

        rr = evidence["real_run"]
        print(f"[real] calls={rr['n_calls']} tokens_in={rr['tokens_in']} tokens_out={rr['tokens_out']} "
              f"wall={rr['wall_seconds']}s mean={rr['mean_call_seconds']}s")
        print(f"[replay] llm_calls={replay['llm_calls']} provider_calls={replay['provider_calls']} "
              f"cached={replay.get('n_cached')}/{replay.get('n_llm_call_events')}")
        print(f"[rulebased] calls={rule['n_calls']} wall={rule['wall_seconds']}s")
        print(f"[evidence] {args.out}")
        assert replay["llm_calls"] == 0, "重放必须 llm_calls==0"
        return 0
    finally:
        shutil.rmtree(dumps, ignore_errors=True)
        if tmp_root:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
