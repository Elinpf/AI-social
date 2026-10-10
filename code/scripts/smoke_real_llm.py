"""T43 冒烟测试：真实 provider 接线验证（**≤ 2 次真实调用**）。

目的：验证管道没接错——不是规模实验。检查项：
  1) `LLM_CALL` 事件产生（含 tier/model/tokens_in/out）；
  2) provider 协议 / 超时 / 重试通路正常（能拿到真实响应）；
  3) `LLM_JUDGMENT` 落四要素 decision/model/context_digest/frozen=true；
  4) **重放态 `llm_calls == 0`**（冻结机制在真 provider 上成立）。

用法（端点/密钥经环境变量注入，不硬编码）：

    FREEZE_LLM_BASE_URL=http://172.16.3.41:31809/v1 \
    FREEZE_LLM_API_KEY=... FREEZE_LLM_MODEL=DeepSeek-Flash \
    python3 scripts/smoke_real_llm.py --cache-dir ./.smoke_cache

真实调用次数由 `provider.calls` 观测，脚本自身断言 == 2。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from freeze import EventLog, FreezeConfig, LLMBudget, LLMClient, Mode, Tier  # noqa: E402
from freeze.providers import provider_from_env, OpenAICompatProvider  # noqa: E402


def _print_llm_call(ev: dict) -> dict:
    p = ev["payload"]
    return {
        "purpose": p["purpose"],
        "model": p["model"],
        "tier": p["tier"],
        "tokens_in": p["tokens_in"],
        "tokens_out": p["tokens_out"],
        "cached": p["cached"],
        "degraded": p["degraded"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="./.smoke_cache")
    ap.add_argument("--engine-version", default="v1.1-rim-smoke")
    args = ap.parse_args()

    provider = provider_from_env(prefer="openai")
    assert isinstance(provider, OpenAICompatProvider), "冒烟需真实 OpenAI 兼容 provider"
    print(f"[provider] {provider.name} base={provider.base_url} model={provider.model} "
          f"timeout={provider.timeout} max_retries={provider.max_retries}")

    cfg = FreezeConfig(engine_version=args.engine_version, mode=Mode.RUN,
                       cache_dir=args.cache_dir)
    log = EventLog()
    client = LLMClient(cfg, provider=provider, event_log=log, budget=LLMBudget(limit=None))

    # ---- 真实调用 1：普通补全（plan） ----
    r_plan = client.complete(
        purpose="plan",
        system="你是小镇居民，用一句话给出今日计划。",
        user="今天是工作日，请给出你的上午计划（一句话）。",
        tier=Tier.T1,
    )
    # ---- 真实调用 2：软判定（IF-2b） ----
    fj = client.judge(
        judgment_id="SMOKE-J1",
        dimension="mentor_relation",
        question_ref="q.mentor.v1",
        envelope={"options": ["formed", "not_formed"],
                  "threshold": 0.5, "rng_branch": "branch#0"},
        context={"a": "alice", "b": "bob", "shared_activity": "craft_workshop"},
        rng_branch="branch#0",
        parties=["alice", "bob"],
        tier=Tier.T2,
    )

    real_calls = provider.calls
    print(f"\n[run] provider.calls (真实调用次数) = {real_calls}")
    assert real_calls <= 2, f"冒烟测试不得 >2 次真实调用，实际 {real_calls}"

    llm_calls_events = [_print_llm_call(e) for e in log.of_type("LLM_CALL")]
    judgments = log.of_type("LLM_JUDGMENT")

    print("\n[LLM_CALL 事件]")
    print(json.dumps(llm_calls_events, ensure_ascii=False, indent=2))

    assert judgments, "缺少 LLM_JUDGMENT 事件"
    jp = judgments[0]["payload"]
    four = {k: jp[k] for k in ("decision", "model", "context_digest", "frozen")}
    print("\n[LLM_JUDGMENT 四要素]")
    print(json.dumps(four, ensure_ascii=False, indent=2))
    assert four["frozen"] is True
    assert all(four[k] for k in ("decision", "model", "context_digest"))

    print(f"\n[plan text] {r_plan.text[:120]!r}")
    print(f"[judgment] decision={fj.decision!r} model={fj.model!r}")

    # ---- 重放：同 cache_dir + engine_version，绝不重调 LLM ----
    replay_provider = provider_from_env(prefer="openai")
    replay = LLMClient(
        FreezeConfig(engine_version=args.engine_version, mode=Mode.REPLAY,
                     cache_dir=args.cache_dir),
        provider=replay_provider,
        event_log=EventLog(),
    )
    r_plan2 = replay.complete(
        purpose="plan",
        system="你是小镇居民，用一句话给出今日计划。",
        user="今天是工作日，请给出你的上午计划（一句话）。",
        tier=Tier.T1,
    )
    fj2 = replay.judge(
        judgment_id="SMOKE-J1",
        dimension="mentor_relation",
        question_ref="q.mentor.v1",
        envelope={"options": ["formed", "not_formed"]},
        context={},
    )
    print(f"\n[replay] llm_calls = {replay.llm_calls}  "
          f"(provider.calls = {replay_provider.calls})  plan.cached={r_plan2.cached}")
    print(f"[replay] judgment.decision = {fj2.decision!r}")
    assert replay.llm_calls == 0, "重放必须零 LLM 调用"
    assert replay_provider.calls == 0, "重放不得触发 provider"
    assert r_plan2.cached is True
    assert fj2.decision == fj.decision

    print("\n[SMOKE OK] LLM_CALL 产生 / LLM_JUDGMENT 四要素齐全 / 重放 llm_calls==0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
