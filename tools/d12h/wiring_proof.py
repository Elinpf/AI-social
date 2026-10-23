#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-H 接线证明之二：**6 次调用 ⇒ 6 个不同 `cache_key`、`cached=false`**（`sample_index` 0–5）。

- (a) 六次调用按运行期真实形态：k=0/1/2 用 ON prompt、k=3/4/5 用 OFF prompt；
- (b) 同 prompt 六次、仅 `sample_index` 不同 ⇒ 6 个不同 key（证明 `sample_index` 进了 cache_key；
      `LLM_CALL` payload 不落 `params`，这是唯一可观测证据）；
- (c) 重采路径：同 prompt + 同 `sample_index` + 不同 `resample_index` ⇒ key 也不同
      （否则重采会命中同一缓存拿回同一条文本，等于没重采）。

用法（在 `code/` 下）：
    LIFE_PROMPT_D12C_SPECIFIC=1 LIFE_PROMPT_D12E_BESTOF=3 LIFE_PROMPT_D12H_PAIR=3 \
        PYTHONPATH=. python3 ../tools/d12h/wiring_proof.py
退出码：0 = 全过；3 = 任一不过。
"""
from __future__ import annotations

import json
import sys
import tempfile


def render() -> dict:
    from orchestration.integration import build_world
    from life.agent import LifeLayerAgent as A

    w = build_world(seed=42, n=2)
    ag = w["agents"][0]
    pid = ag.agent_id
    partner = [p for p in ag.peers if p != pid][0]
    dlg0 = ag._dialogue_prompt("gift", [pid, partner])
    rep0 = ag._reply_prompt(partner, "gift", [(partner, f"{partner}：来，尝尝这个。")])
    return {
        "d12h_on": A._d12h_on(),
        "on_prompt": dlg0 + A.D12H_ON_SUFFIX,
        "off_prompt": dlg0,
        "on_reply": rep0 + A.D12H_ON_SUFFIX,
        "off_reply": rep0,
        "retry_max": A.D12H_RETRY_MAX,
    }


def cache_selftest(prompts: dict) -> dict:
    from freeze.config import FreezeConfig, Mode, ThinkingPolicy
    from freeze.events import EventLog
    from freeze.llm_client import LLMClient
    from freeze.providers import MockProvider

    tmp = tempfile.mkdtemp(prefix="d12h_wiring_")
    cfg = FreezeConfig(engine_version="d12h-wiring", mode=Mode.RUN, cache_dir=tmp,
                       thinking_policy=ThinkingPolicy(default=False, true_purposes=frozenset(),
                                                      true_tiers=frozenset()))
    log = EventLog(time_unit=cfg.time_unit)
    client = LLMClient(cfg, provider=MockProvider(), event_log=log)

    def _keys():
        ks, cs = [], []
        for ev in log.records:
            p = ev.get("payload") or {}
            if p.get("purpose") != "dialogue":
                continue
            ks.append(p.get("cache_key"))
            cs.append(bool(p.get("cached")))
        return ks, cs

    # (a) 运行期真实形态
    for k in range(6):
        client.complete(purpose="dialogue",
                        user=prompts["on"] if k < 3 else prompts["off"],
                        params_extra={"sample_index": k})
    k_a, c_a = _keys()

    # (b) 同 prompt、sample_index 0..5
    same = "固定 prompt：请说一句话。"
    for k in range(6):
        client.complete(purpose="dialogue", user=same, params_extra={"sample_index": k})
    all_k, all_c = _keys()
    k_b, c_b = all_k[len(k_a):], all_c[len(c_a):]

    # (c) 重采：同 sample_index、不同 resample_index
    for r in (1, 2):
        client.complete(purpose="dialogue", user=same,
                        params_extra={"sample_index": 0, "resample_index": r})
    all_k2, all_c2 = _keys()
    k_c, c_c = all_k2[len(k_a) + len(k_b):], all_c2[len(c_a) + len(c_b):]

    return {
        "a_runtime_6": {"cache_keys": k_a, "n_unique_keys": len(set(k_a)),
                        "cached_flags": c_a, "all_not_cached": all(x is False for x in c_a)},
        "b_same_prompt_6": {"cache_keys": k_b, "n_unique_keys": len(set(k_b)),
                            "cached_flags": c_b, "all_not_cached": all(x is False for x in c_b)},
        "c_resample_keys": {"cache_keys": k_c, "n_unique_keys": len(set(k_c)),
                            "distinct_from_original": len(set(k_c) - set(k_b)) == len(k_c),
                            "cached_flags": c_c},
        "note": "LLM_CALL payload 不含 params；sample_index/resample_index 进 cache_key 的证据是 (b)(c) 的 key 不同",
    }


def main() -> int:
    r = render()
    st = cache_selftest({"on": r["on_prompt"], "off": r["off_prompt"]})
    res = {"render": {k: v for k, v in r.items()}, "cache_selftest": st}
    print(json.dumps(res, ensure_ascii=False, indent=2))

    a, b, c = st["a_runtime_6"], st["b_same_prompt_6"], st["c_resample_keys"]
    ok1 = a["n_unique_keys"] == 6 and a["all_not_cached"]
    ok2 = b["n_unique_keys"] == 6 and b["all_not_cached"]
    ok3 = c["n_unique_keys"] == 2 and c["distinct_from_original"] and not any(c["cached_flags"][1:])
    print(f"[{'PASS' if ok1 else 'FAIL'}] ① 运行期 6 次（ON×3+OFF×3）⇒ 6 个不同 key、全 cached=false"
          f"（unique={a['n_unique_keys']}）", file=sys.stderr)
    print(f"[{'PASS' if ok2 else 'FAIL'}] ② 同 prompt、sample_index 0–5 ⇒ 6 个不同 key"
          f"（unique={b['n_unique_keys']}）", file=sys.stderr)
    print(f"[{'PASS' if ok3 else 'FAIL'}] ③ 重采 key 与原 key 不同（unique={c['n_unique_keys']}，"
          f"cached={c['cached_flags']}）", file=sys.stderr)
    return 0 if (ok1 and ok2 and ok3) else 3


if __name__ == "__main__":
    sys.exit(main())
