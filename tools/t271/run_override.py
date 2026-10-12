#!/usr/bin/env python3
"""T292 override 模式跑批 —— 把消融开关作为【runtime config-dict 覆盖】传给 run_e2e，
副本配置文件【不动】⇒ engine_version 指纹不变 ⇒ cache_key 不变 ⇒ 共享 freeze_cache 可命中。

只支持【引擎级】配置键（default_config() 里的：world_director / policy / economy / time_config / genesis）。
⚠️ life_v2(sleep/forgetting/persona_drift) 由 life 层【直接读盘】消费，此途径【不覆盖】它 —— 需 file 模式或 life 层 hook。

用法（在 copy/<code> 为 cwd 下由 host_batch 调起）：
  run_override.py --seed 42 --agents 20 --rounds 84 --out OUT --side-root SIDE \
      --flush-every 12 [--resume-from P --target-round N] \
      --override world_director.enabled=false --override policy.wake.enabled=true
"""
from __future__ import annotations
import argparse, json, os, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--agents", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--out", default=None)
    ap.add_argument("--side-root", default=None)
    ap.add_argument("--flush-every", type=int, default=0)
    ap.add_argument("--resume-from", default=None)
    ap.add_argument("--target-round", type=int, default=None)
    ap.add_argument("--override", action="append", default=[])
    a = ap.parse_args()

    sys.path.insert(0, os.getcwd())  # cwd = copy/code（host_batch 的 --workdir）
    from engine.runner import default_config
    from orchestration.integration import run_e2e

    cfg = default_config()
    applied = []
    for spec in a.override:
        loc, _, val = spec.partition("=")
        keys = loc.strip().split(".")
        node = cfg
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        try:
            v = json.loads(val)
        except Exception:
            v = val
        node[keys[-1]] = v
        applied.append(f"{loc}={v}")
    print("[override-run] 开关（运行时 cfg，不改文件）:", "; ".join(applied) or "(无)", flush=True)

    rep = run_e2e(seed=a.seed, rounds=a.rounds, n=a.agents, config=cfg, out_path=a.out,
                  side_root=a.side_root, flush_every=a.flush_every,
                  resume_from=a.resume_from, target_round=a.target_round)
    print("[override-run] done:", {k: rep.get(k) for k in ("rounds", "events", "start_round", "resumed_from")})
    ok = (rep.get("chain_ok") and rep.get("replay_parity") and rep.get("conservation_ok")
          and not rep.get("unknown_event_types"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
