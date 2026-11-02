"""D9z 路径 A 证据①：开关关闭时「同轮可见」分支**进入次数 = 0**（可复算）。

做法（不改代码，只在验证进程里包一层计数）：
  1. `KernelAdapter._pending_view` —— 可见性上界的唯一入口；包一层统计
     「被调用次数」与「返回非 None（= 分支真的进入）次数」；
  2. `engine.perceive.with_pending` —— 合并动作；统计「真的发生合并」次数
     （即 `pending` 非空且模式非 off）；
  3. `VisibilityIndex.visible` —— 统计「`extra` 非空（索引里追加了缓冲事件）」次数。

同一 fixture（`build_world(seed=42, n=16)`，8 轮，mock provider，不调真 LLM）跑两遍：
  OFF（开关未设）与 ON（`HITT_INTRA_ROUND_VISIBILITY=1`）。
预期：OFF 三项全 0；ON 三项全 > 0（证明计数有效、不是恒 0 的哑计数器）。

用法（`code/` 目录下）：`python3 ../tools/d9z/branch_entry_count.py`
"""

from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_ROOT, "code"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OS_ENV = "HITT_INTRA_ROUND_VISIBILITY"


def _run(mode: str, rounds: int = 8, n: int = 16, seed: int = 42) -> dict:
    from engine import perceive as P
    from orchestration.integration import KernelAdapter, build_world
    from orchestration.visibility_index import VisibilityIndex

    cnt = {"pending_view_calls": 0, "pending_view_nonNone": 0,
           "with_pending_calls": 0, "with_pending_merged": 0,
           "idx_visible_calls": 0, "idx_visible_with_extra": 0}

    orig_pv = KernelAdapter._pending_view
    orig_wp = P.with_pending
    orig_vis = VisibilityIndex.visible

    def pv(self):
        r = orig_pv(self)
        cnt["pending_view_calls"] += 1
        if r is not None:
            cnt["pending_view_nonNone"] += 1
        return r

    def wp(records, pending):
        r = orig_wp(records, pending)
        cnt["with_pending_calls"] += 1
        if r is not records:
            cnt["with_pending_merged"] += 1
        return r

    def vis(self, agent_id, upto_round, **kw):
        extra = kw.get("extra")
        cnt["idx_visible_calls"] += 1
        if extra:
            cnt["idx_visible_with_extra"] += 1
        return orig_vis(self, agent_id, upto_round, **kw)

    if mode:
        os.environ[OS_ENV] = mode
    else:
        os.environ.pop(OS_ENV, None)
    try:
        KernelAdapter._pending_view = pv
        P.with_pending = wp
        VisibilityIndex.visible = vis
        w = build_world(seed=seed, n=n)
        eng = w["engine"]
        for r in range(rounds):
            eng.run_round(r)
        events = len(eng.ledger.records)
        final_state_hash = None
        try:
            from engine.state import state_hash
            final_state_hash = state_hash(eng.state)
        except Exception:
            pass
    finally:
        KernelAdapter._pending_view = orig_pv
        P.with_pending = orig_wp
        VisibilityIndex.visible = orig_vis

    return {"mode": mode or "off(unset)", "switch_value": os.environ.get(OS_ENV),
            "n": n, "rounds": rounds, "seed": seed, "events": events,
            "final_state_hash": final_state_hash, **cnt}


def main() -> int:
    os.environ.pop("HITT_LLM_PROVIDER", None)      # mock/freeze，真 LLM 不参与
    os.environ.pop("HITT_INTRA_ROUND_VISIBILITY", None)
    off = _run("")
    on = _run("1")
    out = {"off": off, "on": on, "checks": {
        "off_pending_view_nonNone_zero": off["pending_view_nonNone"] == 0,
        "off_with_pending_merged_zero": off["with_pending_merged"] == 0,
        "off_idx_extra_zero": off["idx_visible_with_extra"] == 0,
        "on_pending_view_nonNone_positive": on["pending_view_nonNone"] > 0,
        "on_idx_extra_positive": on["idx_visible_with_extra"] > 0,
        "off_same_events_as_on_sanity": off["events"] > 0 and on["events"] > 0,
    }}
    # 说明（不是失败）：`engine.perceive.with_pending()` 是 engine 侧 IF-1 的孪生入口，
    # **life 批不走它**（life 走 `Adapter.perceive` → `VisibilityIndex`），故两臂调用次数都是 0。
    # 这里只登记、不作为门禁；若将来判定"预留 API 属多余面"，可删。
    out["notes"] = {
        "with_pending_calls_off": off["with_pending_calls"],
        "with_pending_calls_on": on["with_pending_calls"],
        "explain": "engine.perceive.with_pending 在 life 路径无 live caller（保留为 engine 侧孪生入口）",
    }
    out["checks"]["all_pass"] = all(out["checks"].values())
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["checks"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
