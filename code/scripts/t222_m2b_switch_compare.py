"""T222 证据脚本：M2b 开关对照（默认关 vs 判别式开），离线、确定性、无网络。

跑两遍（generative / discriminative），比较：
  * 重放一致性 / 守恒 / 未知名事件（两侧都必须干净）
  * LLM_JUDGMENT 的 method 直方图 + obs 唯一口径 judge_method_rates（escape/fallback/inert）

用法：
  cd code && python scripts/t222_m2b_switch_compare.py --n 10 --rounds 84 --seed 7
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import life.policy as P  # noqa: E402


def _run(mode: str, n: int, rounds: int, seed: int) -> dict:
    from orchestration.integration import build_world
    from engine.state import state_hash
    from engine.replay import replay_records
    from engine import conservation
    from obs.admission import judge_method_rates

    cfg = {"judge_mode": mode, "importance_mode": mode, "fallback": "none", "margin_theta": 0.0}
    P.set_m2b_config(None if mode == "generative" else cfg)
    side = tempfile.mkdtemp(prefix=f"t222_{mode}_")
    try:
        w = build_world(seed=seed, n=n, side_root=side)
        eng = w["engine"]
        for r in range(rounds):
            eng.run_round(r)
        recs = eng.ledger.records
        h = state_hash(eng.state)
        r1 = state_hash(replay_records(recs, verify=True, verify_seals=True,
                                       expected_fingerprint=getattr(eng, "fingerprint", None)))
        method_hist: dict[str, int] = {}
        for rec in recs:
            if rec["type"] == "LLM_JUDGMENT":
                m = rec["payload"].get("method")
                method_hist[str(m)] = method_hist.get(str(m), 0) + 1
        return {
            "mode": mode, "events": len(recs),
            "final_state_hash": h, "replay_parity": (r1 == h), "seals_ok": True,
            "conservation_ok": (conservation.check_conservation(eng.state, eng.config) == []),
            "judgment_events": sum(1 for rec in recs if rec["type"] == "LLM_JUDGMENT"),
            "method_hist": method_hist,
            "judge_method_rates": judge_method_rates(recs),
        }
    finally:
        P.set_m2b_config(None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    off = _run("generative", a.n, a.rounds, a.seed)
    on = _run("discriminative", a.n, a.rounds, a.seed)
    print(json.dumps({"off_generative": off, "on_discriminative": on}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
