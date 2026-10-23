#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-I 接线证明：三候选 prompt = T1 逐字节 / `S_ext(4g)` 校验 / 3+5 个不同 `cache_key`。

闸（对应任务卡「交付 2」1/2/3）：
- ① `prompt_fn_sha256` 必须 = **`effc14db…`**（三候选 prompt 全 = T1，本臂不加任何结构提示）；
- ② `S_ext(4g)` 加载时 **`content_sha256` 校验通过**，并打印该值（供 `switch_proof` 引用）；
      另做**负例**：篡改后的 S_ext 必须**抛错**（不静默回退）；
- ③ 3 个 `cache_key`（`sample_index` 0/1/2）两两不同且 `cached=false`；
      另加**重采 key**：同 `sample_index`、`resample_index=1..5` ⇒ 5 个新 key、全 miss
      （否则重采命中同一缓存拿回同一条，等于没重采）。

用法（在 `code/` 下）：
    LIFE_PROMPT_D12C_SPECIFIC=1 LIFE_PROMPT_D12E_BESTOF=3 LIFE_PROMPT_D12I_ALIGN=3 \
        PYTHONPATH=. python3 ../tools/d12i/wiring_proof.py
退出码：0 全过 / 3 任一不过。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import types

T1 = "effc14dbffdb6865aa52d9d8adab9db269ab3b92ae9a1a230a22cab6c0ed73f5"


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def render() -> dict:
    from orchestration.integration import build_world
    from life.agent import LifeLayerAgent as A

    w = build_world(seed=42, n=2)
    ag = w["agents"][0]
    pid = ag.agent_id
    partner = [p for p in ag.peers if p != pid][0]
    dlg = ag._dialogue_prompt("gift", [pid, partner])
    rep = ag._reply_prompt(partner, "gift", [(partner, f"{partner}：来，尝尝这个。")])
    return {
        "d12i_on": A._d12i_on(),
        "dialogue_prompt": dlg, "reply_prompt": rep,
        "sha256_dialogue": _sha(dlg), "sha256_reply": _sha(rep),
        "prompt_fn_sha256": _sha(dlg + "\n===\n" + rep),
    }


def ext_check() -> dict:
    """② `S_ext(4g)` 校验 + 负例（篡改必抛错）。"""
    from life.agent import LifeLayerAgent as A

    A._D12I_EXT = None                      # 强制重新加载
    ext = A._d12i_ext_ref()
    neg_ok, neg_msg = False, ""
    path = ext["path"]
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        d["shingles"] = d["shingles"][:-1]           # 篡改：删一个 shingle ⇒ content_sha 必不匹配
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(d, tmp, ensure_ascii=False)
        tmp.close()
        os.environ["LIFE_PROMPT_D12I_EXT"] = tmp.name
        A._D12I_EXT = None
        try:
            A._d12i_ext_ref()
            neg_ok, neg_msg = False, "篡改后未抛错"
        except ValueError as e:
            neg_ok, neg_msg = True, str(e)[:120]
        finally:
            A._D12I_EXT = None
            os.environ.pop("LIFE_PROMPT_D12I_EXT", None)
            A._d12i_ext_ref()                        # 恢复正确缓存
    except Exception as e:                            # 负例自身出错也要暴露
        neg_ok, neg_msg = False, f"{type(e).__name__}: {e}"
    return {"path": path, "n_shingles": ext["n"], "content_sha256": ext["content_sha256"],
            "tamper_rejected": neg_ok, "tamper_message": neg_msg}


def cache_selftest(prompt: str) -> dict:
    from freeze.config import FreezeConfig, Mode, ThinkingPolicy
    from freeze.events import EventLog
    from freeze.llm_client import LLMClient
    from freeze.providers import MockProvider

    tmp = tempfile.mkdtemp(prefix="d12i_wiring_")
    cfg = FreezeConfig(engine_version="d12i-wiring", mode=Mode.RUN, cache_dir=tmp,
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

    for k in range(3):                                     # 三候选：只差 sample_index
        client.complete(purpose="dialogue", user=prompt, params_extra={"sample_index": k})
    k_a, c_a = _keys()

    for r in range(1, 6):                                  # 重采：sample_index=0 + resample_index 1..5
        client.complete(purpose="dialogue", user=prompt,
                        params_extra={"sample_index": 0, "resample_index": r})
    all_k, all_c = _keys()
    k_b, c_b = all_k[len(k_a):], all_c[len(c_a):]

    return {
        "three_samples": {"cache_keys": k_a, "n_unique_keys": len(set(k_a)),
                          "cached_flags": c_a, "all_not_cached": all(x is False for x in c_a)},
        "resample_keys": {"cache_keys": k_b, "n_unique_keys": len(set(k_b)),
                          "all_new_vs_samples": len(set(k_b) - set(k_a)) == len(k_b),
                          "cached_flags": c_b, "all_not_cached": all(x is False for x in c_b)},
        "note": "LLM_CALL payload 不含 params；sample_index/resample_index 进 cache_key 的证据是 key 不同",
    }


def main() -> int:
    r = render()
    e = ext_check()
    c = cache_selftest(r["dialogue_prompt"])
    out = {"render": r, "ext": e, "cache_selftest": c}
    print(json.dumps(out, ensure_ascii=False, indent=2))

    a, b = c["three_samples"], c["resample_keys"]
    ok1 = r["prompt_fn_sha256"] == T1
    ok2 = (e["tamper_rejected"] and e["n_shingles"] > 0 and len(e["content_sha256"]) == 64)
    ok3 = (a["n_unique_keys"] == 3 and a["all_not_cached"]
           and b["n_unique_keys"] == 5 and b["all_new_vs_samples"] and b["all_not_cached"])
    print(f"[{'PASS' if ok1 else 'FAIL'}] ① 三候选 prompt = T1（prompt_fn_sha256={r['prompt_fn_sha256']}）",
          file=sys.stderr)
    print(f"[{'PASS' if ok2 else 'FAIL'}] ② S_ext(4g) 校验通过（n={e['n_shingles']}、"
          f"content_sha256={e['content_sha256'][:16]}…）+ 篡改负例被拒={e['tamper_rejected']}", file=sys.stderr)
    print(f"[{'PASS' if ok3 else 'FAIL'}] ③ 3 采三 key + 重采 5 key 全不同且全 miss"
          f"（{a['n_unique_keys']} / {b['n_unique_keys']}）", file=sys.stderr)
    return 0 if (ok1 and ok2 and ok3) else 3


if __name__ == "__main__":
    sys.exit(main())
