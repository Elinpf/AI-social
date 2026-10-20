"""D8 剂量复算（**零 LLM**）：`wd.tension` 在 N 回合里的期望触发次数 / 期望生效回合数。

背景（本轮诊断，`v2/evidence/D8-branch-impl.md`）：A0 真跑 84 回合里 `tension` 只触发 1 次、
生效 6 回合，怀疑"剂量太小 / 阈值太高"。这里用**纯函数**复算，不做任何 LLM 调用：

  trigger 期望次数 = Σ_{t=0..N-1} P(roll < prob_bp)，P = prob_bp/10000
                    （`engine/world_director.py::plan_directives` 的判定是
                     `roll = draw_u64(...) % 10000; if roll >= prob: continue`）
  = N * prob_bp / 10000          （每回合独立同分布；不考虑"已生效则不再触发"的抑制，
                                  因为当前实现**没有**这种抑制，同一 kind 可叠加）

用法（在仓库根或本目录均可）：
    python3 v2/evidence/d8_tension_dose_recompute.py
    python3 v2/evidence/d8_tension_dose_recompute.py --rounds 60 --curve conservative

输出：改前（master 2090287 的 `config/world_director.json`）与若干候选剂量下的期望值对照。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CODE = REPO / "code"
sys.path.insert(0, str(CODE))

from engine.world_director import DOSE_CURVES, resolve_dose  # noqa: E402


def expected(prob_bp: int, rounds: int) -> float:
    """N 回合内触发次数的期望（纯算术，无 RNG、无 LLM）。"""
    return rounds * prob_bp / 10000.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=84, help="回合数（A/B 现用 60）")
    ap.add_argument("--config", default=str(CODE / "config" / "world_director.json"))
    ap.add_argument("--mech", default="wd.tension")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    mech = (cfg.get("mechanisms") or {}).get(args.mech) or {}
    base_dose = dict(mech.get("dose") or {})
    print(f"== {args.mech} ==")
    print(f"config      : {args.config}")
    print(f"enabled     : {mech.get('enabled')}   kind={mech.get('kind')}")
    print(f"base dose   : {json.dumps(base_dose, ensure_ascii=False)}")
    print(f"dose_curve  : {cfg.get('dose_curve')}   (curves={list(DOSE_CURVES)})")
    print(f"slots(时长) : {base_dose.get('slots')} 回合/次")
    print(f"rounds      : {args.rounds}")
    print()

    rows = []
    for curve in DOSE_CURVES:
        c = dict(cfg)
        c["dose_curve"] = curve
        d = resolve_dose(c, args.mech)
        prob = int(d.get("prob_bp", 0))
        rows.append((curve, prob, expected(prob, args.rounds),
                     expected(prob, args.rounds) * int(base_dose.get("slots", 1))))

    # 候选：显式 prob_bp 覆盖（不改文件，只做算术对照）
    for cand in (200, 400, 800, 1200):
        rows.append((f"prob_bp={cand}", cand, expected(cand, args.rounds),
                     expected(cand, args.rounds) * int(base_dose.get("slots", 1))))

    cur = cfg.get("dose_curve")
    print(f"{'curve/prob':<16}{'prob_bp':>9}{'E[触发]':>10}{'E[生效回合]':>13}")
    for name, prob, trig, eff in rows:
        mark = "  <== 当前" if name == cur else ""
        print(f"{name:<16}{prob:>9}{trig:>10.3f}{eff:>13.3f}{mark}")
    print()
    print("说明：")
    print("  · 期望按『每回合独立判定、同 kind 不抑制』计算（当前实现即如此，无冷却）。")
    cur_trig = expected(int(resolve_dose(cfg, args.mech).get("prob_bp", 0)), args.rounds)
    print(f"  · 当前配置下 E[触发]={cur_trig:.3f}（{args.rounds} 回合）⇒ 观测到 0 或 1 次都在正常波动内")
    print("    （Poisson λ=0.336 时 P(≥1)=28.5%；84 回合观测到 1 次不构成『机制坏了』的证据）。")
    print("    所以本轮**不建议**为了『多触发』改阈值：改剂量=改世界层，会与 D8 的上下文接通混批，A/B 归因失效。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
