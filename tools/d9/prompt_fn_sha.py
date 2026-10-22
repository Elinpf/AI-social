#!/usr/bin/env python3
"""prompt_fn_sha.py — 提示词「接线」预检：同一段代码在开关两态下必须渲染出**不同的 prompt**。

用途（D12-B §6-①）：证明 `HITT_D12_PREFWORD` 真的接进了提示词，而不是只在源码里多了一个分支。
**起跑前**跑，比等 60 秒 `arm_state_check` 更早、更便宜。

判定：
- 若两态 `dialogue_prompt_sha256`（或 `reply_prompt_sha256`）**相同** ⇒ 开关没接进提示词 ⇒ **exit 3**；
- 若不同 ⇒ exit 0，并打印两态 sha。

用法：
  python3 tools/d9/prompt_fn_sha.py --code-root <worktree>/code [--env-var HITT_D12_PREFWORD]
退出码：0 接线成功；2 导入/渲染失败；3 两态相同（未接线）。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import os
import sys


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render(code_root: str) -> dict:
    """在给定代码树里渲染两条提示词的 开关关 / 开关开 两态。"""
    sys.path.insert(0, code_root)
    for m in [k for k in list(sys.modules) if k.split(".")[0] in ("life", "engine", "orchestration")]:
        sys.modules.pop(m, None)

    from life.agent import LifeLayerAgent            # noqa: E402
    from life.persona import load_personas           # noqa: E402
    from pathlib import Path                          # noqa: E402
    from life.dialogue_threads import DEFAULTS as DT_DEFAULTS  # noqa: E402

    personas = load_personas(Path(code_root) / "config" / "personas.json")
    pid = sorted(personas)[0]
    other = sorted(personas)[1] if len(personas) > 1 else pid
    names = {pid: "老周", other: "秀娘"}

    def _mk():
        a = object.__new__(LifeLayerAgent)
        a.agent_id = pid
        a.persona = personas[pid]
        a.peers = [other]
        a._peer_names = names
        a._rel_cache = {(other, "familiarity"): 20, (other, "affinity"): 5}
        a.needs = {"energy": 55, "satiety": 60, "social": 40, "esteem": 50, "mastery": 50, "leisure": 45}
        a._rifts = {}
        a._rifts_seen = set()
        a._thread_replied_turn = {}
        a._goals_set_weeks = set()
        a._peer_names = names
        return a

    cfg = dict(DT_DEFAULTS)
    history = [(other, f"{names[other]}：show me")]

    out = {}
    for state in ("off", "on"):
        if state == "on":
            os.environ["HITT_D12_PREFWORD"] = "1"
        else:
            os.environ.pop("HITT_D12_PREFWORD", None)
        a = _mk()
        d = a._dialogue_prompt("rel_maintain", [pid, other], cfg)
        r = a._reply_prompt(other, "rel_maintain", history, cfg)
        out[state] = {
            "dialogue_prompt": d,
            "reply_prompt": r,
            "dialogue_prompt_sha256": _sha(d),
            "reply_prompt_sha256": _sha(r),
        }
    os.environ.pop("HITT_D12_PREFWORD", None)

    src = (
        inspect.getsource(LifeLayerAgent._dialogue_prompt)
        + inspect.getsource(LifeLayerAgent._reply_prompt)
        + inspect.getsource(LifeLayerAgent._d12_prefword_line)
    )
    out["prompt_fn_source_sha256"] = _sha(src)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-root", required=True)
    ap.add_argument("--exit-on-same", action="store_true", default=True)
    a = ap.parse_args(argv)
    try:
        res = _render(os.path.abspath(a.code_root))
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] 渲染失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(f"prompt_fn_source_sha256 = {res['prompt_fn_source_sha256']}  (两态相同，属预期：源码含分支)")
    print(f"OFF dialogue_prompt_sha256 = {res['off']['dialogue_prompt_sha256']}")
    print(f"ON  dialogue_prompt_sha256 = {res['on']['dialogue_prompt_sha256']}")
    print(f"OFF reply_prompt_sha256    = {res['off']['reply_prompt_sha256']}")
    print(f"ON  reply_prompt_sha256    = {res['on']['reply_prompt_sha256']}")
    same_d = res["off"]["dialogue_prompt_sha256"] == res["on"]["dialogue_prompt_sha256"]
    same_r = res["off"]["reply_prompt_sha256"] == res["on"]["reply_prompt_sha256"]
    if same_d or same_r:
        print("[FAIL] 开关两态渲染出的 prompt 相同 ⇒ 开关**没有**接进提示词", file=sys.stderr)
        return 3
    print("[PASS] 两态 prompt 不同 ⇒ 开关已接进提示词")
    print("---- OFF dialogue_prompt ----")
    print(res["off"]["dialogue_prompt"][-160:])
    print("---- ON  dialogue_prompt ----")
    print(res["on"]["dialogue_prompt"][-220:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
